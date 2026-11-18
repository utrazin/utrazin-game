"""Vegetação densa da Fase 1 v3 (agente Densidade, Etapa 6): calcula FORA da Unreal onde vai cada planta/pedra.

Uso (Python com numpy + scipy + Pillow; não precisa do Blender):
  blender -b --python tools/blender/gen_l01_v3.py -- assets/work/levels/L01     (gera l01_preview_v3.npz = relevo)
  python tools/blender/scatter_l01_v3.py assets/work/levels/L01
Entradas:
  l01_preview_v3.npz   relevo exato (H, grade de 4 m, o mesmo do L01_Terrain_v3.fbx), estrada, rio, trilhas
  l01_layout_v3.json   zonas, POIs, portões, saltos, baús, itens...
  assets/work/tripo/tripo_processed.json   medidas dos modelos do usuário (Tripo)
  tools/unreal/l01_user_dressing.py        plano dos modelos do usuário (para não plantar em cima deles)
Saídas (assets/work/levels/L01):
  l01_scatter_v3.bin           registros float32 little-endian: x, y, z (cm, Unreal), qx, qy, qz, qw, escala_xy, escala_z
                               (cabeçalho de 16 bytes: "JRSC", versão 1, 9 floats por registro, total de registros)
  l01_scatter_v3.json          índice: malhas, lotes por pedaço de 250 m (início, quantidade, corte, colisão, sombra), contagens
  l01_scatter_v3_preview.png   vista de cima (1 px = 1 m)
Lido por tools/unreal/scatter_l01.py (AJRInstancedScatter::AddBatchFromFile, um ator por pedaço de 250 m).

Camadas (densidade = instâncias por 100 m2):
  chao      grama/trevo/samambaia/pétalas/pedrinhas Quaternius recoloridas (faixa de ~35 m das rotas e POIs),
            sem colisão nem sombra, some a ~60 m
  detalhe   grupinhos de cogumelos, flores, pedrinhas e cristais pequenos (modelos do usuário)
  arbustos  arbustos/tentáculos na altura da cintura (3 a 8 por 100 m2 perto das rotas)
  arvores   árvores em bosques com clareiras (perto: corte 450 m; morros longe: corte 1000 m)
  pedras    pedras médias espalhadas + pedras grandes e penhascos nas encostas
Regras: tudo no relevo (mesma triangulação do FBX), árvores em pé e afundadas 10 a 40 cm abaixo do ponto mais
baixo do tronco, nada de árvore em encosta > 30 graus, plantas pequenas inclinadas com o chão; longe das estradas,
trilhas, áreas planas dos POIs, saltos, portões, rio, lago, baús e itens. Ajustes: bloco AJUSTES abaixo.
Coordenadas internas: Blender (X leste, Y norte, metros). Unreal: x = X*100, y = -Y*100, z = Z*100.
"""
import json
import os
import struct
import sys

import numpy as np
from scipy import ndimage
from scipy.spatial import cKDTree

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
_ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
OUT = os.path.abspath(_ARGS[0]) if _ARGS else os.path.join(REPO, "assets", "work", "levels", "L01")
NPZ = os.path.join(OUT, "l01_preview_v3.npz")
LAYOUT = os.path.join(OUT, "l01_layout_v3.json")
PROCESSED = os.path.join(REPO, "assets", "work", "tripo", "tripo_processed.json")
SEED = 6061

# ============================================================================ AJUSTES (tunáveis)
HALF, STEP = 1000.0, 4.0          # relevo do gen_l01_v3.py
EDGE = 985.0                      # parede invisível da borda
CHUNK = 250.0                     # um ator AJRInstancedScatter por pedaço de 250 m
# distância mínima (m) do EIXO das rotas, por camada: (principal, terra, trilha)
CLEAR = {"chao": (7.0, 4.6, 2.4), "detalhe": (8.0, 5.5, 2.6), "arbustos": (9.0, 6.0, 3.0),
         "arvores": (11.0, 7.5, 4.0), "pedras": (11.0, 7.5, 4.0)}
RIVER_CLEAR, LAKE_CLEAR, JUMP_CLEAR = 24.0, 54.0, 30.0
BAND_FULL, BAND_END = 22.0, 34.0  # faixa do chão: cheio até 22 m da borda da rota, some até 34 m
# densidade por bioma (floresta, misto, deserto), por 100 m2
D_CHAO = (420.0, 320.0, 150.0)
D_DETALHE = (0.9, 0.7, 0.6)       # grupos (3 a 7 peças cada) perto das rotas
D_ARBUSTOS = (7.5, 5.5, 4.5)      # perto das rotas (faixa de 55 m)
D_ARBUSTOS_LONGE = (3.0, 1.5, 0.5)
D_ARVORES = (1.9, 0.5, 0.06)    # 40 a 260 m das rotas (cinturão); perto = 70%, morros longe = D_ARVORES_LONGE
D_ARVORES_LONGE = (0.2, 0.07, 0.02)
D_PEDRAS = (0.05, 0.10, 0.22)     # pedras médias
D_PEDRAS_ENCOSTA = 0.22           # pedras grandes em encosta > 24 graus
MAX_SLOPE = {"chao": 0.84, "detalhe": 0.7, "arbustos": 0.7, "arvores": 0.577, "pedras": 9.0}
# corte por distância (m): (início do fade, fim)
CULL = {"chao": (38, 60), "detalhe": (45, 70), "arbustos": (110, 150), "arvores": (380, 450),
        "arvores_longe": (900, 1000), "pedras": (500, 600), "pedras_grandes": (900, 1000)}
# estilo de cada zona: pesos (floresta, misto, deserto). Pedido: 0-1 deserto esparso, 3-5 floresta densa, 6-7 misto
ZONE_STYLE = {0: (0.0, 0.3, 0.7), 1: (0.0, 0.0, 1.0), 2: (0.0, 0.5, 0.5), 3: (1.0, 0.0, 0.0), 4: (1.0, 0.0, 0.0),
              5: (0.85, 0.15, 0.0), 6: (0.25, 0.75, 0.0), 7: (0.0, 0.6, 0.4)}

# [A-077] mapa "bem preenchido" (pedido do usuário): --denso (ou JR_DENSO=1) engrossa o cinturão e os morros longe
# (árvores x1,4 perto / x2,5 longe, arbustos longe x2, pedras x1,5) e alarga a faixa de chão (22 -> 30 m).
# Sem a flag o resultado é idêntico ao de antes. Custo: mais instâncias (ver contagens no índice e reports/).
DENSO = ("--denso" in sys.argv) or (os.environ.get("JR_DENSO") == "1")
if DENSO:
    D_ARVORES = tuple(round(v * 1.4, 4) for v in D_ARVORES)
    D_ARVORES_LONGE = tuple(round(v * 2.5, 4) for v in D_ARVORES_LONGE)
    D_ARBUSTOS_LONGE = tuple(round(v * 2.0, 4) for v in D_ARBUSTOS_LONGE)
    D_PEDRAS = tuple(round(v * 1.5, 4) for v in D_PEDRAS)
    D_DETALHE = tuple(round(v * 1.4, 4) for v in D_DETALHE)
    BAND_FULL, BAND_END = 30.0, 44.0

# áreas planas dos POIs (as mesmas do gen_l01_v3.py; Blender, m)
PADS = [((-700, -770), 48, "Acampamento"), ((-700, -705), 14, "Buggy"), ((-785, -805), 26, "NaveQueda"),
        ((255, -690), 42, "Posto"), ((330, -722), 12, "TorreRadio"), ((222, -722), 10, "SalaTrancada"),
        ((215, -255), 22, "ArvoreMae"), ((520, -60), 16, "MargemLago"), ((628, -86), 17, "IlhaColmeia"),
        ((-395, 655), 58, "Vila"), ((-470, 745), 30, "DiscoVoador"), ((262, 905), 18, "PortaoNorte")]
LAKE_C, LAKE_R = np.array([628.0, -86.0]), 50.0

# ============================================================================ malhas
# kind: "user" = modelo do usuário (/Game/Environment/User/<Categoria>/SM_<nome>), "q" = Quaternius (quaternius_lib)
# dims = tamanho nominal (m) usado aqui; a Unreal corrige pela caixa real da malha (scale_mul no índice)
Q_DIMS = {"Grass_Common_Short": (0.64, 0.74, 1.33), "Grass_Common_Tall": (0.9, 0.99, 1.87),
          "Grass_Wispy_Short": (1.32, 1.21, 1.07), "Grass_Wispy_Tall": (1.54, 1.59, 1.67),
          "Clover_1": (0.8, 0.76, 1.14), "Clover_2": (0.85, 0.84, 1.26), "Fern_1": (9.05, 8.49, 2.69),
          "Petal_1": (0.46, 0.45, 0.24), "Petal_2": (0.67, 0.63, 0.24), "Petal_3": (0.62, 0.61, 0.19),
          "Pebble_Round_1": (0.5, 0.37, 0.1), "Pebble_Round_3": (0.45, 0.48, 0.1), "Pebble_Square_1": (0.43, 0.44, 0.13),
          "Plant_7": (1.05, 0.96, 0.25)}
# cor (tint) das MIs de recolor da grama Quaternius: paleta alienígena (azul-petróleo, violeta, magenta)
Q_TINT = {"Grass_Common_Short": (0.10, 0.62, 0.62), "Grass_Common_Tall": (0.12, 0.50, 0.66),
          "Grass_Wispy_Short": (0.50, 0.30, 0.85), "Grass_Wispy_Tall": (0.58, 0.26, 0.80),
          "Clover_1": (0.16, 0.52, 0.72), "Clover_2": (0.36, 0.28, 0.82), "Fern_1": (0.70, 0.22, 0.70),
          "Petal_1": (1.00, 0.25, 0.72), "Petal_2": (0.95, 0.35, 0.95), "Petal_3": (0.35, 0.95, 0.95),
          "Pebble_Round_1": (0.62, 0.36, 0.26), "Pebble_Round_3": (0.55, 0.40, 0.42), "Pebble_Square_1": (0.50, 0.32, 0.30),
          "Plant_7": (0.20, 0.70, 0.60)}
Q_GLOW = {"Petal_1": 0.6, "Petal_2": 0.5, "Petal_3": 0.6}


def mesh_table():
    proc = json.load(open(PROCESSED, encoding="utf-8")) if os.path.exists(PROCESSED) else {}
    T = {}
    for n in ("NAT_Arvore1", "NAT_Arvore2", "NAT_Arvore3", "NAT_Arvore4", "NAT_Cogumelo", "NAT_Cogumelos", "NAT_Flor",
              "NAT_Flor2", "NAT_Arbusto1", "NAT_Arbusto2", "NAT_Arbusto3", "NAT_Tentaculo", "NAT_Pedra1", "NAT_Pedra2",
              "NAT_Pedra3", "NAT_Penhasco", "NAT_Tronco", "MRC_Cristal"):
        d = (proc.get(n) or {}).get("dims_m") or [1, 1, 1]
        T[n] = {"kind": "user", "name": n, "dims": [float(v) for v in d], "tris": (proc.get(n) or {}).get("tris"),
                "category": (proc.get(n) or {}).get("category", "Natureza")}
    for n, d in Q_DIMS.items():
        T["Q_" + n] = {"kind": "q", "ref": "Nature/" + n, "dims": list(d), "tint": list(Q_TINT[n]),
                       "glow": Q_GLOW.get(n, 0.0)}
    return T


MESH = mesh_table()

# ============================================================================ relevo
Z = np.load(NPZ)
H = Z["H"].astype(np.float64)          # H[i, j]: X = -HALF + i*STEP, Y = -HALF + j*STEP
N = H.shape[0]


def height(X, Y):
    """Altura exata do terreno (mesma diagonal escolhida pelo gen_l01_v3.py em cada quadrado)."""
    X = np.asarray(X, float)
    Y = np.asarray(Y, float)
    fi = (X + HALF) / STEP
    fj = (Y + HALF) / STEP
    i0 = np.clip(np.floor(fi).astype(int), 0, N - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, N - 2)
    tx = np.clip(fi - i0, 0, 1)
    ty = np.clip(fj - j0, 0, 1)
    h00, h10, h11, h01 = H[i0, j0], H[i0 + 1, j0], H[i0 + 1, j0 + 1], H[i0, j0 + 1]
    diag = np.abs(h00 - h11) <= np.abs(h10 - h01)
    # diagonal 00-11: triângulos (00,10,11) e (00,11,01)
    a = np.where(tx >= ty, h00 + tx * (h10 - h00) + ty * (h11 - h10), h00 + ty * (h01 - h00) + tx * (h11 - h01))
    # diagonal 10-01: triângulos (00,10,01) e (10,11,01)
    b = np.where(tx + ty <= 1, h00 + tx * (h10 - h00) + ty * (h01 - h00),
                 h11 + (1 - tx) * (h01 - h11) + (1 - ty) * (h10 - h11))
    return np.where(diag, a, b)


def normal(X, Y, e=1.0):
    dx = (height(X + e, Y) - height(X - e, Y)) / (2 * e)
    dy = (height(X, Y + e) - height(X, Y - e)) / (2 * e)
    n = np.stack([-dx, -dy, np.ones_like(dx)], -1)
    return n / np.linalg.norm(n, axis=-1, keepdims=True), np.hypot(dx, dy)


# ============================================================================ campos de distância (grade de 1 m)
G = 2001                               # -1000..1000 m


def raster_polys(polys, step=0.4):
    m = np.zeros((G, G), bool)
    for p in polys:
        p = np.asarray(p, float)
        for a, b in zip(p[:-1], p[1:]):
            n = max(2, int(np.linalg.norm(b - a) / step) + 1)
            t = np.linspace(0, 1, n)[:, None]
            q = a[None] * (1 - t) + b[None] * t
            ii = np.clip(np.round(q[:, 0] + HALF).astype(int), 0, G - 1)
            jj = np.clip(np.round(q[:, 1] + HALF).astype(int), 0, G - 1)
            m[ii, jj] = True
    return m


def dist_field(mask):
    return ndimage.distance_transform_edt(~mask).astype(np.float32)


def at(field, X, Y):
    ii = np.clip(np.round(np.asarray(X) + HALF).astype(int), 0, G - 1)
    jj = np.clip(np.round(np.asarray(Y) + HALF).astype(int), 0, G - 1)
    return field[ii, jj]


def bl(p_ue):
    """Unreal (cm) -> Blender (m), só x/y."""
    return np.array([p_ue[0] / 100.0, -p_ue[1] / 100.0])


L = json.load(open(LAYOUT, encoding="utf-8"))
road = Z["road"]
alts = [Z[k] for k in sorted(Z.files) if k.startswith("alt_")]
trails = [Z[k] for k in sorted(Z.files) if k.startswith("trail_")]
D_MAIN = dist_field(raster_polys([road]))
D_DIRT = dist_field(raster_polys(alts))
D_TRAIL = dist_field(raster_polys(trails))
D_RIVER = dist_field(raster_polys([Z["river"]]))

# bloqueios redondos (peças dos POIs, modelos do usuário, baús, itens, checkpoints, portões, saltos)
blocks = []          # (X, Y, raio_m, so_chao)  so_chao=False: vale para todas as camadas


def piece_radius(e):
    s = e.get("scale", 1.0)
    s = max(s[0], s[1]) if isinstance(s, list) else float(s)
    r = e.get("q") or e.get("mesh") or e.get("engine") or ""
    base = 0.5 if r in ("Cube", "Cone", "Cylinder", "Sphere") else (1.6 if "/" in r else 2.5)
    return base * s


for poi in L["pois"]:
    for e in poi["pieces"]:
        blocks.append((*bl(e["loc"]), piece_radius(e) + 1.0))
try:
    sys.path.insert(0, os.path.join(REPO, "tools", "unreal"))
    import l01_user_dressing as UD  # noqa: E402
    PLAN = UD.plan_v3(L)
    for p in PLAN["place"]:
        d = UD.dims_m(p["name"]) or [2, 2, 2]
        s = p["scale"]
        s = max(s[:2]) if isinstance(s, list) else float(s)
        blocks.append((p["x"] / 100.0, -p["y"] / 100.0, 0.5 * max(d[0], d[1]) * s + 1.0))
    for c in list(PLAN["chests"].values()) + list(PLAN["pickups"].values()):
        blocks.append((c["x"] / 100.0, -c["y"] / 100.0, 2.5))
    USER_PLAN = len(PLAN["place"])
    PLAN_REG = PLAN.get("registry")
except Exception as exc:  # noqa: BLE001
    print("aviso: plano do usuário não lido:", exc)
    USER_PLAN = 0
    PLAN_REG = None
for key in ("chests", "pickups", "checkpoints", "enemies"):
    for e in L.get(key, []):
        blocks.append((*bl(e["loc"]), 2.5 if key != "checkpoints" else 4.0))
for g in L["gates"]:
    ext = g.get("block_extent_cm", [300, 800])
    blocks.append((*bl(g["loc"]), max(ext[0], ext[1]) / 100.0 + 6.0))
for b in L.get("barricades", []):
    blocks.append((*bl(b["loc"]), b["width_cm"] / 200.0 + 4.0))
for p in L["horde"]["spawn_points"]:
    blocks.append((*bl(p), 3.0))
blocks.append((*bl(L["vehicle_start"]["loc"]), 6.0))
BLK = np.zeros((G, G), np.float32) + 1e6     # distância até a borda do bloqueio mais próximo
_gx = np.arange(G) - HALF
for X0, Y0, r in blocks:
    i0, i1 = int(max(0, X0 - r - 2 + HALF)), int(min(G, X0 + r + 3 + HALF))
    j0, j1 = int(max(0, Y0 - r - 2 + HALF)), int(min(G, Y0 + r + 3 + HALF))
    if i1 <= i0 or j1 <= j0:
        continue
    xx, yy = np.meshgrid(_gx[i0:i1], _gx[j0:j1], indexing="ij")
    BLK[i0:i1, j0:j1] = np.minimum(BLK[i0:i1, j0:j1], np.hypot(xx - X0, yy - Y0) - r)
JUMPS = [bl(j[k]["loc"]) for j in L["jumps"] for k in ("ramp", "landing")]
PAD_C = np.array([c for c, r, n in PADS], float)
PAD_R = np.array([r for c, r, n in PADS], float)


def pad_dist(X, Y):
    d = np.hypot(X[:, None] - PAD_C[None, :, 0], Y[:, None] - PAD_C[None, :, 1]) - PAD_R[None]
    return d.min(1)


def edge_dist(X, Y):
    """Distância (m) até a BORDA da rede jogável (estrada, terra, trilha, áreas planas)."""
    return np.minimum.reduce([at(D_MAIN, X, Y) - 6.0, at(D_DIRT, X, Y) - 4.0, at(D_TRAIL, X, Y) - 2.0,
                              pad_dist(X, Y)])


def clear_ok(X, Y, layer, radius=0.0):
    cm, cd, ct = CLEAR[layer]
    ok = (at(D_MAIN, X, Y) > cm + radius) & (at(D_DIRT, X, Y) > cd + radius) & (at(D_TRAIL, X, Y) > ct + radius)
    ok &= at(D_RIVER, X, Y) > RIVER_CLEAR + radius
    ok &= np.hypot(X - LAKE_C[0], Y - LAKE_C[1]) > LAKE_CLEAR + radius
    ok &= (np.abs(X) < EDGE - 3) & (np.abs(Y) < EDGE - 3)
    for jx, jy in JUMPS:
        ok &= np.hypot(X - jx, Y - jy) > JUMP_CLEAR + radius
    ok &= at(BLK, X, Y) > (0.3 if layer == "chao" else radius + 0.5)
    pd = pad_dist(X, Y)
    if layer == "chao":
        ok &= pd > -1e9          # chão pode entrar nas áreas planas (com menos densidade), longe das peças
    else:
        ok &= pd > 4.0 + radius
    return ok


# ============================================================================ biomas e ruído
rng = np.random.default_rng(SEED)
xs4 = np.linspace(-HALF, HALF, N)
GX, GY = np.meshgrid(xs4, xs4, indexing="ij")


def noise(cell_m, seed, octaves=3):
    """Ruído suave 0..1 na grade de 4 m (soma de oitavas de ruído branco borrado)."""
    r = np.random.default_rng(seed)
    acc = np.zeros((N, N))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        s = cell_m / (2 ** o) / STEP
        g = ndimage.gaussian_filter(r.standard_normal((N, N)), s, mode="wrap")
        acc += amp * g / (g.std() + 1e-9)
        tot += amp
        amp *= 0.5
    acc /= tot
    return 0.5 + 0.5 * np.tanh(acc * 1.3)


def grid_at(F, X, Y):
    fi = (np.asarray(X) + HALF) / STEP
    fj = (np.asarray(Y) + HALF) / STEP
    return ndimage.map_coordinates(F, [fi, fj], order=1, mode="nearest")


# zona de cada ponto = zona do ponto de estrada mais perto (ou zona a pé, se dentro do raio)
rz = Z["road_zone"]
tree_road = cKDTree(road)
_, ki = tree_road.query(np.stack([GX.ravel(), GY.ravel()], 1))
zone = rz[ki].reshape(N, N)
for zd in L["zones"]:
    if zd["mode"] == "foot":
        c = bl(zd["center"])
        zone = np.where(np.hypot(GX - c[0], GY - c[1]) < zd["radius_cm"] / 100.0 * 1.3, zd["id"], zone)
STY = np.zeros((N, N, 3))
for z, w in ZONE_STYLE.items():
    STY[zone == z] = w
STY = np.stack([ndimage.gaussian_filter(STY[..., c], 60 / STEP) for c in range(3)], -1)
STY /= STY.sum(-1, keepdims=True) + 1e-9
# a máscara do gen (R floresta, G esparso, B deserto) dá a variação local dentro de cada zona
veg = Z["veg"].astype(float)
vs = veg.sum(-1, keepdims=True)
vfill = np.stack([ndimage.gaussian_filter(veg[..., c], 6) for c in range(3)], -1)
vfill /= vfill.sum(-1, keepdims=True) + 1e-6
STY = 0.8 * STY + 0.2 * np.stack([vfill[..., 0], vfill[..., 1], vfill[..., 2]], -1)
STY /= STY.sum(-1, keepdims=True)

N_CLUMP = noise(70, SEED + 1)          # bosques x clareiras
N_PATCH = noise(18, SEED + 2)          # manchas de grama
N_SPEC = [noise(45, SEED + 10 + k) for k in range(6)]   # espécie dominante por região
N_FINE = noise(9, SEED + 3, 2)
SLOPE_G = np.hypot(*np.gradient(H, STEP))


# ============================================================================ amostragem
def sample_poisson(dens_grid, cell=STEP, mask_grid=None):
    """Pontos com densidade dens_grid (por 100 m2) na grade de 4 m (Poisson por célula, posição uniforme)."""
    lam = dens_grid * (cell * cell) / 100.0
    if mask_grid is not None:
        lam = lam * mask_grid
    n = rng.poisson(lam)
    ii, jj = np.nonzero(n)
    cnt = n[ii, jj]
    ii = np.repeat(ii, cnt)
    jj = np.repeat(jj, cnt)
    X = xs4[ii] + rng.uniform(-cell / 2, cell / 2, len(ii))
    Y = xs4[jj] + rng.uniform(-cell / 2, cell / 2, len(jj))
    return X, Y


def thin(X, Y, rmin, prio=None):
    """Distância mínima entre pontos (gulosa)."""
    if len(X) == 0:
        return np.zeros(0, bool)
    order = np.argsort(prio if prio is not None else rng.random(len(X)))
    keep = np.zeros(len(X), bool)
    grid = {}
    cs = float(np.max(rmin)) if np.ndim(rmin) else rmin
    rr = np.broadcast_to(rmin, X.shape)
    for k in order:
        gx, gy = int(X[k] // cs), int(Y[k] // cs)
        bad = False
        for a in (gx - 1, gx, gx + 1):
            for b in (gy - 1, gy, gy + 1):
                for m in grid.get((a, b), ()):
                    if (X[k] - X[m]) ** 2 + (Y[k] - Y[m]) ** 2 < max(rr[k], rr[m]) ** 2:
                        bad = True
                        break
                if bad:
                    break
            if bad:
                break
        if not bad:
            keep[k] = True
            grid.setdefault((gx, gy), []).append(k)
    return keep


def pick(weights_rows, names):
    """weights_rows: (n, k) -> índice escolhido por linha."""
    w = np.maximum(weights_rows, 0) + 1e-9
    c = np.cumsum(w, 1)
    r = rng.random(len(w))[:, None] * c[:, -1:]
    return np.array(names, dtype=object)[(c < r).sum(1)]


INST = []   # (layer, cull_key, mesh, X, Y, Zbase, qb(w,x,y,z) Blender, sxy, sz, collision, shadows)


def quat_align(nb, yaw):
    """Quaternion (Blender, w x y z): gira o yaw em Z e depois inclina o 'cima' para a normal nb."""
    n = len(yaw)
    qy = np.stack([np.cos(yaw / 2), np.zeros(n), np.zeros(n), np.sin(yaw / 2)], 1)
    up = np.array([0.0, 0.0, 1.0])
    ax = np.cross(np.broadcast_to(up, nb.shape), nb)
    s = np.linalg.norm(ax, axis=1)
    c = np.clip(nb[:, 2], -1, 1)
    ang = np.arctan2(s, c)
    ax = np.where(s[:, None] > 1e-9, ax / np.maximum(s, 1e-9)[:, None], np.array([1.0, 0, 0]))
    qa = np.concatenate([np.cos(ang / 2)[:, None], ax * np.sin(ang / 2)[:, None]], 1)
    return qmul(qa, qy)


def qmul(a, b):
    w1, x1, y1, z1 = a.T
    w2, x2, y2, z2 = b.T
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], 1)


def add(layer, cull_key, names, X, Y, target_h, target_w=None, align=0.0, tilt_deg=0.0, sink=(0.0, 0.0),
        foot_frac=0.0, collision=False, shadows=False, sink_frac=0.0):
    """Coloca as instâncias. target_h/target_w = (min, max) em metros (w None = proporcional).
    align = 0 (em pé) .. 1 (inclinado com o chão); foot_frac = raio do pé (fração da largura) para afundar
    abaixo do ponto MAIS BAIXO do pé (árvores e pedras não ficam voando no morro)."""
    if len(X) == 0:
        return
    names = np.asarray(names, dtype=object)
    for nm in np.unique(names):
        sel = names == nm
        x, y = X[sel], Y[sel]
        m = MESH[nm]
        dw = max(m["dims"][0], m["dims"][1])
        dh = m["dims"][2]
        h = rng.uniform(*target_h, len(x))
        sz = h / dh
        if target_w is None:
            sxy = sz * rng.uniform(0.92, 1.08, len(x))
        else:
            sxy = rng.uniform(*target_w, len(x)) / dw
        nb, slope = normal(x, y)
        yaw = rng.uniform(0, 2 * np.pi, len(x))
        up = np.array([0.0, 0.0, 1.0])
        nn = up[None] * (1 - align) + nb * align
        if tilt_deg:
            t = np.radians(rng.uniform(0, tilt_deg, len(x)))
            a = rng.uniform(0, 2 * np.pi, len(x))
            nn = nn + np.stack([np.sin(t) * np.cos(a), np.sin(t) * np.sin(a), np.zeros(len(x))], 1)
        nn /= np.linalg.norm(nn, axis=1, keepdims=True)
        q = quat_align(nn, yaw)
        z = height(x, y)
        if foot_frac > 0:
            r = foot_frac * dw * sxy
            for k in range(6):
                ang = k * np.pi / 3
                z = np.minimum(z, height(x + r * np.cos(ang), y + r * np.sin(ang)))
        z = z - rng.uniform(*sink, len(x)) - sink_frac * h
        INST.append((layer, cull_key, nm, x, y, z, q, sxy, sz, collision, shadows))


def filt(X, Y, layer, radius=0.0, slope_max=None):
    ok = clear_ok(X, Y, layer, radius)
    _, sl = normal(X, Y, 1.5)
    ok &= sl < (slope_max if slope_max is not None else MAX_SLOPE[layer])
    return X[ok], Y[ok]


# ---- distância à borda da rede (grade de 4 m) e faixas
E4 = edge_dist(GX.ravel(), GY.ravel()).reshape(N, N)
BAND = 1.0 - np.clip((E4 - BAND_FULL) / (BAND_END - BAND_FULL), 0, 1)
PADIN = (pad_dist(GX.ravel(), GY.ravel()).reshape(N, N) < 0)
F, M, D = STY[..., 0], STY[..., 1], STY[..., 2]


def by_biome(t):
    return t[0] * F + t[1] * M + t[2] * D


# ============================================================================ 1) árvores (bosques + clareiras)
clump = np.clip((N_CLUMP - 0.32) / 0.3, 0, 1) ** 1.2 * 1.6
near = np.clip(E4 / 40.0, 0, 1)
f_dist = np.where(E4 < 40, 0.55 + 0.45 * near, np.where(E4 < 260, 1.0, 0.0))
dens_t = by_biome(D_ARVORES) * f_dist * clump
dens_far = by_biome(D_ARVORES_LONGE) * (E4 >= 260) * (0.4 + clump)
X, Y = sample_poisson(dens_t)
Xf, Yf = sample_poisson(dens_far)
isfar = np.r_[np.zeros(len(X), bool), np.ones(len(Xf), bool)]
X, Y = np.r_[X, Xf], np.r_[Y, Yf]
ok = clear_ok(X, Y, "arvores", 1.0)
_, sl = normal(X, Y, 2.0)
ok &= sl < MAX_SLOPE["arvores"]
X, Y, isfar = X[ok], Y[ok], isfar[ok]
k = thin(X, Y, 4.5)
X, Y, isfar = X[k], Y[k], isfar[k]
f, m_, d = grid_at(F, X, Y), grid_at(M, X, Y), grid_at(D, X, Y)
sp = [grid_at(N_SPEC[i], X, Y) for i in range(6)]
W = np.stack([
    f * (0.2 + sp[0]) * 1.0 + m_ * 0.25,           # NAT_Arvore1 espiral roxa
    f * (0.2 + sp[1]) * 0.7 + m_ * 0.15,           # NAT_Arvore2 guarda-chuva (copa de 13 m)
    f * (0.2 + sp[2]) * 1.0 + m_ * 0.3,            # NAT_Arvore4 bioluminescente
    f * (0.15 + sp[3]) * 0.8 + m_ * 0.15,          # NAT_Cogumelo gigante
    d * 0.75 + m_ * 0.25 + f * 0.02,               # NAT_Arvore3 morta
    d * 0.30 + m_ * 0.05,                          # MRC_Cristal
], 1)
names = pick(W, ["NAT_Arvore1", "NAT_Arvore2", "NAT_Arvore4", "NAT_Cogumelo", "NAT_Arvore3", "MRC_Cristal"])
HT = {"NAT_Arvore1": (8.5, 13.5), "NAT_Arvore2": (9.0, 14.0), "NAT_Arvore4": (8.5, 13.0), "NAT_Cogumelo": (4.0, 8.5),
      "NAT_Arvore3": (6.0, 10.0), "MRC_Cristal": (2.5, 6.5)}
for far in (False, True):
    for nm in HT:
        s = (names == nm) & (isfar == far)
        cul = "arvores_longe" if far else "arvores"
        add("arvores", cul, [nm] * int(s.sum()), X[s], Y[s], HT[nm], align=0.0 if nm != "MRC_Cristal" else 0.5,
            tilt_deg=3.0 if nm != "MRC_Cristal" else 12.0, sink=(0.12, 0.38), foot_frac=0.06,
            collision=True, shadows=True)
TREES = (X, Y)

# troncos caídos (só floresta, chão quase plano)
X, Y = sample_poisson(0.035 * F * (E4 > 12) * (E4 < 220))
X, Y = filt(X, Y, "arvores", 4.5, 0.25)
add("pedras", "pedras", ["NAT_Tronco"] * len(X), X, Y, (1.4, 2.2), (5.5, 8.5), align=1.0, sink=(0.2, 0.35),
    collision=True, shadows=True)

# ============================================================================ 2) pedras
X, Y = sample_poisson(by_biome(D_PEDRAS) * (0.5 + N_FINE))
X, Y = filt(X, Y, "pedras", 1.2)
add("pedras", "pedras", ["NAT_Pedra2"] * len(X), X, Y, (0.9, 2.6), align=0.7, tilt_deg=12, sink=(0.1, 0.3),
    foot_frac=0.25, collision=True, shadows=True)
# encostas: pedras grandes (24 graus ou mais) e penhascos (40 graus ou mais), longe das rotas
steep = np.clip((SLOPE_G - 0.45) / 0.3, 0, 1)
X, Y = sample_poisson(D_PEDRAS_ENCOSTA * steep * (E4 > 15))
X, Y = filt(X, Y, "pedras", 3.0)
k = thin(X, Y, 7.0)
X, Y = X[k], Y[k]
nb, sl = normal(X, Y, 3.0)
cliff = (sl > 0.85) & (grid_at(E4, X, Y) > 60) & (rng.random(len(X)) < 0.35)
add("pedras", "pedras_grandes", ["NAT_Penhasco"] * int(cliff.sum()), X[cliff], Y[cliff], (7.0, 13.0), align=0.25,
    sink=(0.8, 1.5), foot_frac=0.3, collision=True, shadows=True)
X, Y = X[~cliff], Y[~cliff]
big = rng.random(len(X)) < 0.55
add("pedras", "pedras_grandes", ["NAT_Pedra3"] * int(big.sum()), X[big], Y[big], (2.5, 6.0), align=0.6, tilt_deg=10,
    sink=(0.25, 0.6), foot_frac=0.3, collision=True, shadows=True)
add("pedras", "pedras", ["NAT_Pedra2"] * int((~big).sum()), X[~big], Y[~big], (1.5, 3.2), align=0.7, tilt_deg=15,
    sink=(0.15, 0.4), foot_frac=0.25, collision=True, shadows=True)

# ============================================================================ 3) arbustos (cintura)
near_s = 1.0 - np.clip((E4 - 55) / 15.0, 0, 1)
dens_s = by_biome(D_ARBUSTOS) * near_s * (0.45 + 1.1 * N_PATCH) + by_biome(D_ARBUSTOS_LONGE) * (1 - near_s) * (E4 < 260)
dens_s = dens_s * np.where(PADIN, 0.0, 1.0)
X, Y = sample_poisson(dens_s)
X, Y = filt(X, Y, "arbustos", 0.6)
if len(TREES[0]):
    dtree, _ = cKDTree(np.stack(TREES, 1)).query(np.stack([X, Y], 1))
    X, Y = X[dtree > 1.3], Y[dtree > 1.3]
f, m_, d = grid_at(F, X, Y), grid_at(M, X, Y), grid_at(D, X, Y)
W = np.stack([f * 0.9 + m_ * 0.5,              # NAT_Arbusto1 bioluminescente
              f * 0.5 + m_ * 0.5 + d * 0.6,      # NAT_Arbusto2 espinhos de cristal
              f * 1.4 + m_ * 0.8 + d * 0.1,      # NAT_Arbusto3 roxo (4,7 mil triângulos: o mais barato)
              f * 0.25 + m_ * 0.35 + d * 0.9,    # NAT_Tentaculo
              f * 0.5 + m_ * 0.35 + d * 0.05],   # Q_Fern_1 (samambaia grande recolorida)
             1)
names = pick(W, ["NAT_Arbusto1", "NAT_Arbusto2", "NAT_Arbusto3", "NAT_Tentaculo", "Q_Fern_1"])
SH = {"NAT_Arbusto1": ((0.8, 1.3), (1.2, 2.0)), "NAT_Arbusto2": ((0.8, 1.4), None),
      "NAT_Arbusto3": ((0.9, 1.6), None), "NAT_Tentaculo": ((1.2, 2.4), None), "Q_Fern_1": ((0.7, 1.2), (1.8, 3.0))}
for nm, (th, tw) in SH.items():
    s = names == nm
    add("arbustos", "arbustos", [nm] * int(s.sum()), X[s], Y[s], th, tw, align=0.5, tilt_deg=5, sink=(0.05, 0.12),
        foot_frac=0.2, shadows=True)

# ============================================================================ 4) detalhe (grupinhos)
X, Y = sample_poisson(by_biome(D_DETALHE) * BAND * np.where(PADIN, 0.3, 1.0))
X, Y = filt(X, Y, "detalhe", 1.5)
f, m_, d = grid_at(F, X, Y), grid_at(M, X, Y), grid_at(D, X, Y)
kind = pick(np.stack([f * 1.0 + m_ * 0.5, f * 0.7 + m_ * 0.7 + d * 0.15, d * 1.0 + m_ * 0.4, d * 0.5 + m_ * 0.2], 1),
            ["cogumelos", "flores", "pedrinhas", "cristais"])
GROUP = {"cogumelos": (["NAT_Cogumelos", "NAT_Cogumelos", "NAT_Flor"], (0.35, 0.9)),
         "flores": (["NAT_Flor", "NAT_Flor2", "NAT_Flor2", "NAT_Cogumelos"], (0.5, 1.1)),
         "pedrinhas": (["NAT_Pedra1", "NAT_Pedra1", "NAT_Pedra1"], (0.25, 0.7)),
         "cristais": (["MRC_Cristal", "NAT_Pedra1", "NAT_Pedra1"], (0.4, 1.4))}
gx, gy, gn = [], [], []
for cx, cy, kd in zip(X, Y, kind):
    pool, _ = GROUP[kd]
    n = rng.integers(3, 8)
    r = rng.uniform(0.6, 2.2)
    a = rng.uniform(0, 2 * np.pi, n)
    rr = r * np.sqrt(rng.random(n))
    gx += list(cx + rr * np.cos(a))
    gy += list(cy + rr * np.sin(a))
    gn += list(rng.choice(pool, n))
gx, gy, gn = np.array(gx), np.array(gy), np.array(gn, dtype=object)
ok = clear_ok(gx, gy, "detalhe", 0.3)
gx, gy, gn = gx[ok], gy[ok], gn[ok]
DH = {"NAT_Cogumelos": (0.35, 0.9), "NAT_Flor": (0.5, 1.1), "NAT_Flor2": (0.5, 1.1), "NAT_Pedra1": (0.2, 0.6),
      "MRC_Cristal": (0.5, 1.4)}
for nm, th in DH.items():
    s = gn == nm
    add("detalhe", "detalhe", [nm] * int(s.sum()), gx[s], gy[s], th, align=0.9 if nm != "MRC_Cristal" else 0.5,
        tilt_deg=8, sink=(0.02, 0.06), sink_frac=0.08 if nm in ("NAT_Pedra1", "MRC_Cristal") else 0.0)

# ============================================================================ 5) chão (grama recolorida)
dens_g = by_biome(D_CHAO) * BAND * (0.55 + 0.9 * N_PATCH) * np.where(PADIN, 0.45, 1.0)
X, Y = sample_poisson(dens_g)
X, Y = filt(X, Y, "chao", 0.0)
f, m_, d = grid_at(F, X, Y), grid_at(M, X, Y), grid_at(D, X, Y)
pa, pb, pc = grid_at(N_SPEC[3], X, Y), grid_at(N_SPEC[4], X, Y), grid_at(N_SPEC[5], X, Y)
W = np.stack([
    (f * 1.0 + m_ * 1.0 + d * 0.35) * (0.3 + pa),      # Grass_Common_Short (azul-petróleo)
    (f * 0.35 + m_ * 0.3) * (0.3 + pa),                # Grass_Common_Tall
    (f * 0.8 + m_ * 0.9 + d * 0.8) * (0.3 + pb),       # Grass_Wispy_Short (violeta)
    (f * 0.25 + m_ * 0.3 + d * 0.1) * (0.3 + pb),      # Grass_Wispy_Tall
    (f * 0.9 + m_ * 0.6) * (0.3 + pc),                 # Clover_1
    (f * 0.5 + m_ * 0.4) * (0.3 + pc),                 # Clover_2 (violeta)
    (f * 0.18 + m_ * 0.1),                             # Petal_1 (magenta, brilha)
    (f * 0.12 + m_ * 0.1),                             # Petal_2
    (f * 0.12 + m_ * 0.05),                            # Petal_3 (ciano)
    (m_ * 0.15 + d * 0.8),                             # Pebble_Round_1
    (m_ * 0.1 + d * 0.5),                              # Pebble_Square_1
    (f * 0.25 + m_ * 0.25 + d * 0.05),                 # Plant_7
], 1)
GN = ["Q_Grass_Common_Short", "Q_Grass_Common_Tall", "Q_Grass_Wispy_Short", "Q_Grass_Wispy_Tall", "Q_Clover_1",
      "Q_Clover_2", "Q_Petal_1", "Q_Petal_2", "Q_Petal_3", "Q_Pebble_Round_1", "Q_Pebble_Square_1", "Q_Plant_7"]
names = pick(W, GN)
GH = {"Q_Grass_Common_Short": ((0.40, 0.75), (0.7, 1.2)), "Q_Grass_Common_Tall": ((0.7, 1.05), (0.8, 1.2)),
      "Q_Grass_Wispy_Short": ((0.35, 0.65), (0.9, 1.4)), "Q_Grass_Wispy_Tall": ((0.6, 0.95), (1.0, 1.5)),
      "Q_Clover_1": ((0.30, 0.55), (0.7, 1.1)), "Q_Clover_2": ((0.30, 0.55), (0.7, 1.1)),
      "Q_Petal_1": ((0.12, 0.22), (0.5, 0.9)), "Q_Petal_2": ((0.12, 0.22), (0.6, 1.0)), "Q_Petal_3": ((0.1, 0.2), (0.5, 0.9)),
      "Q_Pebble_Round_1": ((0.06, 0.14), (0.25, 0.6)), "Q_Pebble_Square_1": ((0.08, 0.16), (0.25, 0.55)),
      "Q_Plant_7": ((0.18, 0.32), (0.8, 1.3))}
for nm, (th, tw) in GH.items():
    s = names == nm
    add("chao", "chao", [nm] * int(s.sum()), X[s], Y[s], th, tw, align=0.85, tilt_deg=6, sink=(0.02, 0.05))


# ============================================================================ 5b) morros v2 (item 7; OPCIONAL)
# Liga só com --morros-v2 (ou JR_MORROS_V2=1). Sem a flag nada aqui roda e o resultado é idêntico ao de antes.
# Usa um gerador de números próprio (SEED + 707): as camadas 1 a 5 continuam iguais com ou sem a flag.
# Regras (skill map-composition):
#   - pedras médias soltas nos morros (> MV_HILL_M da rede) saem, menos as perto das cristas: nada de "pedra jogada";
#   - afloramentos de rocha seguem as cumeeiras (convexo forte perto do topo local): 1 rocha grande + 2 a 4 médias
#     alinhadas com a crista, a cada ~22 m; no deserto, às vezes um cristal pequeno no lugar de uma pedra;
#   - cinturão de árvores na meia-encosta (altura relativa 15 a 72% do desnível local, inclinação < 29 graus),
#     com clareiras pelo ruído de bosque; espécie pelo bioma (floresta, misto, deserto = árvore morta e cristal);
#   - arbustos na borda de baixo do cinturão; tálus (pedras pequenas) no pé das encostas (côncavo, perto do fundo);
#   - mirantes (3 a 5): cumes (o ponto mais alto num quadrado de 120 m) a 60 a 300 m da rede, 12 m ou mais acima
#     da estrada, com trilha a pé (caminho de menor custo na grade de 4 m, com curvas; nenhum trecho > 30 graus), visíveis da estrada, no máximo um por zona; trilha (2,5 m) e topo
#     (raio 9 m; sem árvore/pedra até 18 m, para abrir a vista) ficam limpos e a trilha ganha chão; gravados em l01_mirantes_v2.json (recompensa: baú, ruína,
#     antena ou acampamento abandonado). Tudo passa depois pela etapa 6 (sem sobreposição).
MORROS_V2 = ("--morros-v2" in sys.argv) or (os.environ.get("JR_MORROS_V2") == "1")
MV_HILL_M = 60.0
MV_REWARDS = ["bau", "ruina", "antena", "acampamento", "bau"]
MORROS_STATS = {}


def _drop_inst(pred):
    """Tira de INST as instâncias em que pred(layer, mesh, X, Y) é True. Retorna quantas saíram."""
    gone = 0
    for ei, e in enumerate(INST):
        layer, ck, nm, x, y, z, q, sxy, sz, col, shd = e
        m = pred(layer, nm, ck, x, y)
        if m is None or not m.any():
            continue
        k = ~m
        gone += int(m.sum())
        INST[ei] = (layer, ck, nm, x[k], y[k], z[k], q[k], sxy[k], sz[k], col, shd)
    return gone


def _seg_dist(X, Y, pts):
    """Distância (m) dos pontos (X, Y) até a polilinha pts [(x, y), ...]."""
    best = np.full(np.shape(X), 1e9)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        dx, dy = bx - ax, by - ay
        L2 = dx * dx + dy * dy or 1.0
        t = np.clip(((X - ax) * dx + (Y - ay) * dy) / L2, 0, 1)
        best = np.minimum(best, np.hypot(X - (ax + t * dx), Y - (ay + t * dy)))
    return best


def morros_v2():
    global rng
    keep_rng = rng
    rng = np.random.default_rng(SEED + 707)          # add() e pick() usam o rng global: troca só aqui dentro
    try:
        st = MORROS_STATS
        Hs = ndimage.gaussian_filter(H, 2.0)
        lap = ndimage.laplace(Hs)
        win = int(160 / STEP) | 1
        lo = ndimage.minimum_filter(Hs, size=win)
        hi = ndimage.maximum_filter(Hs, size=win)
        rel = np.clip((Hs - lo) / np.maximum(hi - lo, 5.0), 0, 1)
        inside = (np.abs(GX) < EDGE - 12) & (np.abs(GY) < EDGE - 12)
        hill = inside & (E4 > MV_HILL_M)
        ridge = hill & (lap < -0.25) & (rel > 0.65) & (SLOPE_G < 0.9)
        d_ridge = ndimage.distance_transform_edt(~ridge) * STEP
        st["morros_km2"] = round(float(hill.sum()) * STEP * STEP / 1e6, 2)
        st["cumeeira_km"] = round(float(ridge.sum()) * STEP / 1000, 1)

        # 1) pedras médias soltas nos morros saem (fica 25% e as perto de crista)
        def loose(layer, nm, ck, x, y):
            if nm != "NAT_Pedra2" or ck != "pedras":
                return None
            far = grid_at(E4, x, y) > MV_HILL_M
            return far & (grid_at(d_ridge, x, y) > 12) & (rng.random(len(x)) > 0.25)
        st["pedras_soltas_tiradas"] = _drop_inst(loose)

        # 2) afloramentos nas cumeeiras
        X, Y = sample_poisson(0.6 * ridge)
        X, Y = filt(X, Y, "pedras", 3.0, 0.9)
        k = thin(X, Y, 22.0)
        X, Y = X[k], Y[k]
        gxs, gys = np.gradient(Hs, STEP)
        tx, ty = -grid_at(gys, X, Y), grid_at(gxs, X, Y)       # direção da crista (perpendicular ao gradiente)
        tl = np.hypot(tx, ty) + 1e-9
        tx, ty = tx / tl, ty / tl
        add("pedras", "pedras_grandes", ["NAT_Pedra3"] * len(X), X, Y, (2.5, 5.5), align=0.6, tilt_deg=8,
            sink=(0.3, 0.6), foot_frac=0.3, collision=True, shadows=True)
        bx, by, bn = [], [], []
        desert = grid_at(D, X, Y) > 0.5
        for i in range(len(X)):
            for j in range(int(rng.integers(2, 5))):
                side = (-1) ** j
                d = rng.uniform(3.5, 7.5)
                off = rng.uniform(-1.5, 1.5)
                bx.append(X[i] + tx[i] * d * side - ty[i] * off)
                by.append(Y[i] + ty[i] * d * side + tx[i] * off)
                bn.append("MRC_Cristal" if (desert[i] and rng.random() < 0.3) else "NAT_Pedra2")
        bx, by, bn = np.array(bx), np.array(by), np.array(bn, dtype=object)
        ok = clear_ok(bx, by, "pedras", 1.2) if len(bx) else np.zeros(0, bool)
        for nm, hh in (("NAT_Pedra2", (1.0, 2.4)), ("MRC_Cristal", (1.2, 2.5))):
            s = ok & (bn == nm)
            add("pedras" if nm == "NAT_Pedra2" else "detalhe", "pedras", [nm] * int(s.sum()), bx[s], by[s], hh,
                align=0.7, tilt_deg=14, sink=(0.15, 0.35), foot_frac=0.25, collision=True, shadows=True)
        st["afloramentos"] = int(len(X))
        st["pedras_de_afloramento"] = int(ok.sum())

        # 3) cinturão de árvores na meia-encosta (clareiras pelo ruído de bosque)
        belt = hill & (rel > 0.15) & (rel < 0.72) & (SLOPE_G < 0.57)
        clump = np.clip((N_CLUMP - 0.33) / 0.2, 0, 1)
        dens = (2.2 * F + 1.2 * M + 0.10 * D) * belt * clump
        X, Y = sample_poisson(dens)
        X, Y = filt(X, Y, "arvores", 1.0, 0.55)
        k = thin(X, Y, 5.0)
        X, Y = X[k], Y[k]
        f, m_, d = grid_at(F, X, Y), grid_at(M, X, Y), grid_at(D, X, Y)
        Wt = np.stack([f * 1.0 + m_ * 0.4, f * 0.6 + m_ * 0.2, f * 0.9 + m_ * 0.5, f * 0.25, d * 0.8 + m_ * 0.3, d * 0.25], 1)
        names = pick(Wt, ["NAT_Arvore1", "NAT_Arvore2", "NAT_Arvore4", "NAT_Cogumelo", "NAT_Arvore3", "MRC_Cristal"])
        HT2 = {"NAT_Arvore1": (8.0, 12.5), "NAT_Arvore2": (8.5, 13.0), "NAT_Arvore4": (8.0, 12.0), "NAT_Cogumelo": (4.0, 7.5),
               "NAT_Arvore3": (6.0, 9.5), "MRC_Cristal": (2.5, 5.0)}
        for nm in HT2:
            s = names == nm
            add("arvores", "arvores_longe", [nm] * int(s.sum()), X[s], Y[s], HT2[nm], align=0.0 if nm != "MRC_Cristal" else 0.5,
                tilt_deg=3.0 if nm != "MRC_Cristal" else 12.0, sink=(0.12, 0.38), foot_frac=0.06, collision=True, shadows=True)
        st["arvores_cinturao"] = int(len(X))

        # 4) arbustos na borda de baixo do cinturão e tálus no pé das encostas
        edge = hill & (rel > 0.10) & (rel < 0.26) & (SLOPE_G < 0.6)
        X, Y = sample_poisson((1.0 * F + 0.7 * M + 0.25 * D) * edge * (0.5 + N_PATCH))
        X, Y = filt(X, Y, "arbustos", 0.6)
        f, d = grid_at(F, X, Y), grid_at(D, X, Y)
        nm_s = pick(np.stack([f + 0.3, f + 0.3, 0.6 * f + 0.4 * d + 0.2, 0.5 * d], 1),
                    ["NAT_Arbusto1", "NAT_Arbusto2", "NAT_Arbusto3", "NAT_Tentaculo"])
        for nm in ("NAT_Arbusto1", "NAT_Arbusto2", "NAT_Arbusto3", "NAT_Tentaculo"):
            s = nm_s == nm
            add("arbustos", "arbustos", [nm] * int(s.sum()), X[s], Y[s], (0.8, 1.6), align=0.5, tilt_deg=5, sink=(0.05, 0.12))
        st["arbustos_borda"] = int(len(X))
        foot = hill & (lap > 0.12) & (rel < 0.25) & (SLOPE_G > 0.15) & (SLOPE_G < 0.6)
        X, Y = sample_poisson(0.35 * foot)
        X, Y = filt(X, Y, "pedras", 0.8)
        add("pedras", "pedras", ["NAT_Pedra2"] * len(X), X, Y, (0.5, 1.3), align=0.8, tilt_deg=18, sink=(0.08, 0.2),
            foot_frac=0.25, collision=True, shadows=True)
        st["talus"] = int(len(X))

        # 5) mirantes
        mir = pick_mirantes(Hs)
        st["mirantes"] = len(mir)
        if mir:
            def near_trail(layer, nm, ck, x, y):
                m = np.zeros(len(x), bool)
                for mm in mir:
                    m |= _seg_dist(x, y, mm["_trail_b"]) < (2.5 if layer != "chao" else 0.8)
                    m |= np.hypot(x - mm["_top_b"][0], y - mm["_top_b"][1]) < (9.0 if layer == "chao" else 18.0)
                return m
            st["tiradas_trilha_topo"] = _drop_inst(near_trail)
            # chão ralo nas margens da trilha (quem sobe a pé não anda no vazio)
            for mm in mir:
                pts = np.array(mm["_trail_b"])
                ts = np.linspace(0, 1, max(2, int(mm["trilha_m"] / 0.6)))
                seg = np.interp(ts, np.linspace(0, 1, len(pts)), np.arange(len(pts)))
                i0 = np.floor(seg).astype(int).clip(0, len(pts) - 2)
                fr = seg - i0
                cx = pts[i0, 0] * (1 - fr) + pts[i0 + 1, 0] * fr
                cy = pts[i0, 1] * (1 - fr) + pts[i0 + 1, 1] * fr
                side = rng.choice([-1, 1], len(cx)) * rng.uniform(1.2, 4.0, len(cx))
                dx, dy = np.gradient(cx), np.gradient(cy)
                dl = np.hypot(dx, dy) + 1e-9
                gx2, gy2 = cx - dy / dl * side, cy + dx / dl * side
                add("chao", "chao", ["Q_Grass_Wispy_Short"] * len(gx2), gx2, gy2, (0.35, 0.6), (0.9, 1.3), align=0.85,
                    tilt_deg=6, sink=(0.02, 0.05))
        write_mirantes(mir)                    # grava sempre (lista vazia se nenhum topo passar nas regras)
    finally:
        rng = keep_rng


def trail_path(X0, Y0, win_m=320.0):
    """Trilha a pé do cume (X0, Y0) até a estrada mais perto (estrada ou estrada de terra), pela grade de 4 m.
    Dijkstra: nenhum passo da grade com inclinação > 26 graus (a trilha final, medida de 2 em 2 m, fica < 30), nada de rio/lago; custo = comprimento x (1 + 2 x inclinação),
    então a trilha faz curvas (zigue-zague) onde a encosta é íngreme. Retorna (pontos [(x, y)], comprimento) ou None."""
    import heapq
    i0, j0 = int(round((X0 + HALF) / STEP)), int(round((Y0 + HALF) / STEP))
    r = int(win_m / STEP)
    ia, ib, ja, jb = max(1, i0 - r), min(N - 2, i0 + r), max(1, j0 - r), min(N - 2, j0 + r)
    sub = H[ia:ib + 1, ja:jb + 1]
    gx, gy = GX[ia:ib + 1, ja:jb + 1], GY[ia:ib + 1, ja:jb + 1]
    road_c = (np.minimum(at(D_MAIN, gx.ravel(), gy.ravel()), at(D_DIRT, gx.ravel(), gy.ravel())) < 5.0).reshape(sub.shape)
    wet = ((at(D_RIVER, gx.ravel(), gy.ravel()) < RIVER_CLEAR)
           | (np.hypot(gx.ravel() - LAKE_C[0], gy.ravel() - LAKE_C[1]) < LAKE_CLEAR)).reshape(sub.shape)
    tmax = math.tan(math.radians(26))      # margem: medido de 2 em 2 m na trilha final tem que dar < 30
    h_, w_ = sub.shape
    si, sj = i0 - ia, j0 - ja
    dist = {(si, sj): 0.0}
    prev = {}
    pq = [(0.0, si, sj)]
    goal = None
    nb8 = [(-1, 0), (1, 0), (0, -1), (0, 1), (-1, -1), (-1, 1), (1, -1), (1, 1)]
    while pq:
        c, i, j = heapq.heappop(pq)
        if c > dist.get((i, j), 1e18):
            continue
        if road_c[i, j]:
            goal = (i, j)
            break
        for di, dj in nb8:
            a, b = i + di, j + dj
            if not (0 <= a < h_ and 0 <= b < w_) or wet[a, b]:
                continue
            L = STEP * (1.4142 if di and dj else 1.0)
            sl = abs(sub[a, b] - sub[i, j]) / L
            if sl > tmax:
                continue
            nc = c + L * (1 + 2 * sl)
            if nc < dist.get((a, b), 1e18):
                dist[(a, b)] = nc
                prev[(a, b)] = (i, j)
                heapq.heappush(pq, (nc, a, b))
    if goal is None:
        return None
    path = [goal]
    while path[-1] != (si, sj):
        path.append(prev[path[-1]])
    pts = np.array([(gx[i, j], gy[i, j]) for i, j in path])      # da estrada até o cume
    seg = np.hypot(*np.diff(pts, axis=0).T)
    length = float(seg.sum())
    keep = [0]
    acc = 0.0
    for k in range(1, len(pts) - 1):                               # um ponto a cada ~12 m (mantém as curvas)
        acc += seg[k - 1]
        turn = k + 1 < len(pts) and np.any(pts[k + 1] - pts[k] != pts[k] - pts[k - 1])
        if acc >= 12.0 or (turn and acc >= 4.0):
            keep.append(k)
            acc = 0.0
    keep.append(len(pts) - 1)
    return [(float(x), float(y)) for x, y in pts[keep]], length


def trail_max_slope(pts):
    P = np.array(pts)
    L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
    t = np.arange(0, L[-1] + 1e-6, 2.0)
    x, y = np.interp(t, L, P[:, 0]), np.interp(t, L, P[:, 1])
    h = height(x, y)
    return float(np.degrees(np.arctan((np.abs(np.diff(h)) / 2.0).max()))) if len(h) > 1 else 0.0


def pick_mirantes(Hs):
    """Cumes alcançáveis a pé e visíveis da estrada ou de uma estrada de terra (no máximo um por zona, até 5)."""
    peaks = (Hs == ndimage.maximum_filter(Hs, size=int(120 / STEP) | 1))   # cume de verdade (o mais alto num quadrado de 120 m)
    ii, jj = np.nonzero(peaks)
    Xp, Yp = xs4[ii], xs4[jj]
    e4 = grid_at(E4, Xp, Yp)
    sel = (e4 > 60) & (e4 < 300) & (np.abs(Xp) < EDGE - 40) & (np.abs(Yp) < EDGE - 40)
    zones = L["zones"]
    cands = []
    for X0, Y0 in zip(Xp[sel], Yp[sel]):
        tp = trail_path(X0, Y0)
        if tp is None:
            continue
        trail, L_m = tp
        if L_m > 450.0:                     # trilha curta: o mirante tem que estar "logo ali" da estrada
            continue
        rx, ry = trail[0]
        top_h, road_h = float(height(np.array([X0]), np.array([Y0]))[0]), float(height(np.array([rx]), np.array([ry]))[0])
        if top_h - road_h < 12.0:
            continue
        smax = trail_max_slope(trail)
        if smax >= 30.0:
            continue
        # visível da estrada: a linha do olho (1,7 m) até o topo (+3 m) passa acima do terreno (testa o começo da
        # trilha e mais 2 pontos da estrada a 40 m dele; basta um enxergar)
        seen = False
        for ox, oy in ((rx, ry), (rx + 40, ry), (rx - 40, ry), (rx, ry + 40), (rx, ry - 40)):
            oh = float(height(np.array([ox]), np.array([oy]))[0])
            lx, ly = np.linspace(ox, X0, 40), np.linspace(oy, Y0, 40)
            lz = np.linspace(oh + 1.7, top_h + 3.0, 40)
            if not (height(lx[1:-1], ly[1:-1]) > lz[1:-1] + 0.3).any():
                seen = True
                break
        if not seen:
            continue
        zid = min(zones, key=lambda z: math.hypot(z["center"][0] / 100 - X0, -z["center"][1] / 100 - Y0) / max(1.0, z["radius_cm"] / 100))["id"]
        score = (top_h - road_h) - abs(L_m - 160) * 0.05
        cands.append((score, zid, X0, Y0, trail, top_h, road_h, L_m, smax))
    cands.sort(key=lambda c: -c[0])
    out, used = [], set()
    for c in cands:
        score, zid, X0, Y0, trail, top_h, road_h, L_m, smax = c
        if zid in used or any(math.hypot(X0 - o["_top_b"][0], Y0 - o["_top_b"][1]) < 250 for o in out):
            continue
        used.add(zid)
        n = len(out)
        out.append({"id": f"Mirante_{n + 1:02d}", "zona": zid, "recompensa": MV_REWARDS[n % len(MV_REWARDS)],
                    "altura_sobre_estrada_m": round(top_h - road_h, 1), "trilha_m": round(L_m, 1),
                    "inclinacao_max_graus": round(smax, 1), "_top_b": (float(X0), float(Y0)), "_trail_b": trail,
                    "_top_h": top_h})
        if len(out) >= 5:
            break
    MORROS_STATS["mirantes_candidatos"] = len(cands)
    return out


def write_mirantes(mir):
    data = {"version": 1, "fonte": "tools/blender/scatter_l01_v3.py --morros-v2", "unidade": "cm (Unreal)",
            "nota": "Usado por tools/unreal/build_mirantes_l01.py (A-077).", "mirantes": []}
    for m in mir:
        X0, Y0 = m["_top_b"]
        trail = [[round(x * 100, 1), round(-y * 100, 1), round(float(height(np.array([x]), np.array([y]))[0]) * 100, 1)]
                 for x, y in m["_trail_b"]]
        data["mirantes"].append({"id": m["id"], "zona": m["zona"], "recompensa": m["recompensa"],
                                 "topo_cm": [round(X0 * 100, 1), round(-Y0 * 100, 1), round(m["_top_h"] * 100, 1)],
                                 "raio_cm": 900.0, "trilha_cm": trail, "trilha_m": m["trilha_m"],
                                 "inclinacao_max_graus": m["inclinacao_max_graus"],
                                 "altura_sobre_estrada_m": m["altura_sobre_estrada_m"], "visivel_da_estrada": True,
                                 "motivo": "topo visível da estrada, com trilha a pé e recompensa"})
    json.dump(data, open(os.path.join(OUT, "l01_mirantes_v2.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)


if MORROS_V2:
    import math
    morros_v2()
    print("morros v2:", json.dumps(MORROS_STATS, ensure_ascii=False))


# ============================================================================ 6) sem sobreposição entre camadas (A-062)
# Cada camada acima só se afasta dela mesma. Aqui todas passam pelo registro de footprints
# (tools/pipeline/placement_registry.py, regras em l01_user_dressing.OK_PAIRS), na ordem de prioridade:
# pedras grandes > árvores e cristais grandes > troncos caídos > pedras > detalhe > arbustos.
# Quem bate em algo já colocado (ou nos modelos do usuário e no blockout dos POIs) sai.
# A grama (camada chao) só sai de dentro de tronco, pedra, cristal e construção.
# (tag, fração da largura da malha usada como raio)
FOOT = {"NAT_Penhasco": ("rocha_grande", 0.38), "NAT_Pedra3": ("rocha_grande", 0.42),
        "MRC_Cristal": ("cristal", 0.40), "NAT_Tronco": ("tronco", 0.30), "NAT_Pedra2": ("rocha", 0.45),
        "NAT_Pedra1": ("detalhe", 0.45), "NAT_Cogumelos": ("detalhe", 0.35), "NAT_Flor": ("detalhe", 0.35),
        "NAT_Flor2": ("detalhe", 0.35), "NAT_Arbusto1": ("arbusto", 0.35), "NAT_Arbusto2": ("arbusto", 0.35),
        "NAT_Arbusto3": ("arbusto", 0.35), "NAT_Tentaculo": ("arbusto", 0.35), "Q_Fern_1": ("arbusto", 0.30)}
TREES_COPA = ("NAT_Arvore1", "NAT_Arvore2", "NAT_Arvore3", "NAT_Arvore4", "NAT_Cogumelo")
COPA_FRAC, TRONCO_FRAC, TRONCO_MIN_M = 0.38, 0.09, 0.3
PRIO = {"rocha_grande": 0, "arvore": 1, "cristal": 1, "tronco": 2, "rocha": 3, "detalhe": 4, "arbusto": 5}
GRASS_BLOCK = ("tronco_arvore", "cristal", "rocha_grande", "rocha", "tronco", "estrutura", "cenario")
OVERLAP = {"removidas_por_malha": {}, "chao_removidas": 0, "registro": ""}


def foot(layer, nm):
    """(tag, fração). Cristal pequeno dos grupinhos (camada detalhe) pode encostar em outro: é um cacho."""
    if layer == "detalhe" and nm == "MRC_Cristal":
        return "detalhe", 0.40
    return FOOT[nm]


def resolve_overlaps():
    sys.path.insert(0, os.path.join(REPO, "tools", "pipeline"))
    sys.path.insert(0, os.path.join(REPO, "tools", "unreal"))
    import l01_user_dressing as UD2  # noqa: E402
    reg = UD2.new_registry()
    if PLAN_REG is not None:        # modelos do usuário, blockout, baús, itens (já em cm da Unreal)
        for f in PLAN_REG.items:
            reg.add(f.x, f.y, f.radius, f.tag, f.reason, f.id, force=True)
    # fila: (prioridade, -tamanho, entrada, índice)
    queue = []
    for ei, (layer, ck, nm, x, y, z, q, sxy, sz, col, shd) in enumerate(INST):
        if layer == "chao":
            continue
        w = max(MESH[nm]["dims"][0], MESH[nm]["dims"][1]) * sxy
        kind = "arvore" if nm in TREES_COPA else foot(layer, nm)[0]
        for k in range(len(x)):
            queue.append((PRIO[kind], -float(w[k]), ei, k))
    queue.sort()
    keep = [np.zeros(len(e[3]), bool) for e in INST]
    for _, negw, ei, k in queue:
        nm = INST[ei][2]
        w = -negw
        ux, uy = float(INST[ei][3][k]) * 100.0, -float(INST[ei][4][k]) * 100.0
        if nm in TREES_COPA:
            rc, rt = COPA_FRAC * w * 100.0, max(TRONCO_MIN_M, TRONCO_FRAC * w) * 100.0
            ok = reg.can_place(ux, uy, rc, tag="copa") and reg.can_place(ux, uy, rt, tag="tronco_arvore")
            if ok:
                reg.add(ux, uy, rc, "copa", nm, force=True)
                reg.add(ux, uy, rt, "tronco_arvore", nm, force=True)
        else:
            tag, frac = foot(INST[ei][0], nm)
            ok = reg.add(ux, uy, frac * w * 100.0, tag, nm)
        if ok:
            keep[ei][k] = True
        else:
            OVERLAP["removidas_por_malha"][nm] = OVERLAP["removidas_por_malha"].get(nm, 0) + 1
    # grama fora de dentro de tronco, pedra, cristal e construção
    hard = [f for f in reg.items if f.tag in GRASS_BLOCK]
    if hard:
        hx = np.array([f.x for f in hard]) / 100.0
        hy = -np.array([f.y for f in hard]) / 100.0
        hr = np.array([f.radius for f in hard]) / 100.0 * 0.9
        tree = cKDTree(np.stack([hx, hy], 1))
        for ei, e in enumerate(INST):
            if e[0] != "chao":
                continue
            d, ii = tree.query(np.stack([e[3], e[4]], 1), k=8, distance_upper_bound=float(hr.max()))
            inside = np.zeros(len(e[3]), bool)
            for c in range(d.shape[1]):
                v = ii[:, c] < len(hr)
                inside[v] |= d[v, c] < hr[ii[v, c]]
            keep[ei] = ~inside
            OVERLAP["chao_removidas"] += int(inside.sum())
    else:
        for ei, e in enumerate(INST):
            if e[0] == "chao":
                keep[ei][:] = True
    for ei, e in enumerate(INST):
        m = keep[ei]
        layer, ck, nm, x, y, z, q, sxy, sz, col, shd = e
        INST[ei] = (layer, ck, nm, x[m], y[m], z[m], q[m], sxy[m], sz[m], col, shd)
    # auditoria: só o que é sólido ou grande (arbusto e detalhe ficam de fora para o arquivo não pesar)
    audit = UD2.new_registry()
    for f in reg.items:
        if f.tag not in ("arbusto", "detalhe"):
            audit.add(f.x, f.y, f.radius, f.tag, f.reason, f.id, force=True)
    OVERLAP["sobreposicoes_restantes"] = len(audit.find_overlaps())
    path = os.path.join(REPO, "reports", "placement_L01.json")
    audit.save(path, compact=True, meta={"fonte": "tools/blender/scatter_l01_v3.py", "seed": SEED,
                                         "removidas_por_malha": OVERLAP["removidas_por_malha"],
                                         "chao_removidas": OVERLAP["chao_removidas"]})
    OVERLAP["registro"] = os.path.relpath(path, REPO).replace(os.sep, "/")


# ============================================================================ saída
def write_all():
    recs, batches, counts = [], [], {}
    lay_cnt = {}
    rows = []
    for (layer, ck, nm, x, y, z, q, sxy, sz, col, shd) in INST:
        ci = np.clip(((x + HALF) // CHUNK).astype(int), 0, int(2 * HALF / CHUNK) - 1)
        cj = np.clip(((y + HALF) // CHUNK).astype(int), 0, int(2 * HALF / CHUNK) - 1)
        rows.append((layer, ck, nm, x, y, z, q, sxy, sz, col, shd, ci, cj))
    # agrupa por pedaço e por (camada de corte, malha)
    groups = {}
    for (layer, ck, nm, x, y, z, q, sxy, sz, col, shd, ci, cj) in rows:
        for a in np.unique(ci * 100 + cj):
            s = (ci * 100 + cj) == a
            key = (int(a // 100), int(a % 100), ck, nm, col, shd, layer)
            groups.setdefault(key, []).append((x[s], y[s], z[s], q[s], sxy[s], sz[s]))
    first = 0
    for key in sorted(groups):
        ci, cj, ck, nm, col, shd, layer = key
        parts = groups[key]
        x = np.concatenate([p[0] for p in parts])
        y = np.concatenate([p[1] for p in parts])
        z = np.concatenate([p[2] for p in parts])
        q = np.concatenate([p[3] for p in parts])
        sxy = np.concatenate([p[4] for p in parts])
        sz = np.concatenate([p[5] for p in parts])
        n = len(x)
        # Blender -> Unreal: y espelhado; quaternion (w, x, y, z) -> (-x, y, -z, w)
        rec = np.stack([x * 100, -y * 100, z * 100, -q[:, 1], q[:, 2], -q[:, 3], q[:, 0], sxy, sz], 1).astype("<f4")
        recs.append(rec)
        cs, ce = CULL[ck]
        # chunk (ci, cj) em Blender; no índice vai o centro em Unreal (cm)
        cxu = (-HALF + (ci + 0.5) * CHUNK) * 100
        cyu = -(-HALF + (cj + 0.5) * CHUNK) * 100
        batches.append({"chunk": f"C{ci}_{cj}", "chunk_center_cm": [round(cxu), round(cyu)], "layer": layer,
                        "cull": ck, "mesh": nm, "first": first, "count": n, "cull_start_cm": cs * 100,
                        "cull_end_cm": ce * 100, "collision": bool(col), "shadows": bool(shd)})
        first += n
        counts[nm] = counts.get(nm, 0) + n
        lay_cnt[layer] = lay_cnt.get(layer, 0) + n
    allrec = np.concatenate(recs) if recs else np.zeros((0, 9), "<f4")
    with open(os.path.join(OUT, "l01_scatter_v3.bin"), "wb") as fh:
        fh.write(b"JRSC" + struct.pack("<iii", 1, 9, len(allrec)))
        fh.write(allrec.tobytes())
    meshes = {}
    for nm in counts:
        m = MESH[nm]
        e = {"kind": m["kind"], "nominal_dims_cm": [round(v * 100, 1) for v in m["dims"]]}
        if m["kind"] == "user":
            e["name"] = m["name"]
            e["tris"] = m.get("tris")
        else:
            e["ref"] = m["ref"]
            e["tint"] = m["tint"]
            e["glow"] = m["glow"]
        meshes[nm] = e
    idx = {"version": 1, "file": "l01_scatter_v3.bin", "header_bytes": 16, "record_floats": 9,
           "record": "x, y, z (cm), qx, qy, qz, qw, escala_xy, escala_z (Unreal)", "seed": SEED,
           "chunk_m": CHUNK, "total": int(len(allrec)), "counts_by_layer": lay_cnt, "counts_by_mesh": counts,
           "meshes": meshes, "batches": batches, "user_plan_pieces_avoided": USER_PLAN, "blocks": len(blocks),
           "overlap_pass": OVERLAP}
    if MORROS_V2:
        idx["morros_v2"] = MORROS_STATS
    if DENSO:
        idx["denso"] = True   # [A-077]
    json.dump(idx, open(os.path.join(OUT, "l01_scatter_v3.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    return idx, allrec


def preview(allrec, idx):
    from PIL import Image
    S = 2000
    hs = height(*np.meshgrid(np.linspace(-HALF, HALF, S), np.linspace(-HALF, HALF, S), indexing="ij"))
    gx_, gy_ = np.gradient(hs)
    shade = np.clip(0.75 + 0.25 * (-gx_ + gy_) / 1.0, 0.35, 1.15)
    base = np.array([0.55, 0.36, 0.28])
    img = (base[None, None] * shade[..., None])
    rd = (at(D_MAIN, *np.meshgrid(np.linspace(-HALF, HALF, S), np.linspace(-HALF, HALF, S), indexing="ij")) < 6)
    dd = (at(D_DIRT, *np.meshgrid(np.linspace(-HALF, HALF, S), np.linspace(-HALF, HALF, S), indexing="ij")) < 4)
    tt = (at(D_TRAIL, *np.meshgrid(np.linspace(-HALF, HALF, S), np.linspace(-HALF, HALF, S), indexing="ij")) < 2)
    img[rd] = (0.25, 0.25, 0.27)
    img[dd] = (0.62, 0.52, 0.38)
    img[tt] = (0.85, 0.80, 0.6)
    COL = {"chao": (0.25, 0.75, 0.70), "detalhe": (1.0, 0.4, 0.9), "arbustos": (0.55, 0.3, 0.95),
           "pedras": (0.6, 0.6, 0.6), "arvores": (0.1, 0.35, 0.2)}
    TCOL = {"NAT_Arvore3": (0.35, 0.22, 0.15), "MRC_Cristal": (0.3, 0.9, 1.0), "NAT_Cogumelo": (0.9, 0.2, 0.2),
            "NAT_Arvore2": (0.15, 0.5, 0.45), "NAT_Penhasco": (0.75, 0.35, 0.25), "NAT_Pedra3": (0.45, 0.45, 0.5)}
    order = {"chao": 0, "detalhe": 1, "arbustos": 2, "pedras": 3, "arvores": 4}
    for b in sorted(idx["batches"], key=lambda e: order[e["layer"]]):
        r = allrec[b["first"]:b["first"] + b["count"]]
        X = r[:, 0] / 100.0
        Y = -r[:, 1] / 100.0
        c = TCOL.get(b["mesh"], COL[b["layer"]])
        rad = {"arvores": 3, "pedras": 1, "arbustos": 1, "detalhe": 0, "chao": 0}[b["layer"]]
        if b["mesh"] in ("NAT_Arvore2",):
            rad = 5
        ii = np.clip((X + HALF).astype(int), 0, S - 1)
        jj = np.clip((Y + HALF).astype(int), 0, S - 1)
        for di in range(-rad, rad + 1):
            for dj in range(-rad, rad + 1):
                if di * di + dj * dj <= rad * rad:
                    img[np.clip(ii + di, 0, S - 1), np.clip(jj + dj, 0, S - 1)] = c
    # imagem: x para a direita, norte para cima
    out = np.clip(img.transpose(1, 0, 2)[::-1] * 255, 0, 255).astype(np.uint8)
    Image.fromarray(out).save(os.path.join(OUT, "l01_scatter_v3_preview.png"))


if __name__ == "__main__":
    resolve_overlaps()
    print("sem sobreposição:", json.dumps(OVERLAP, ensure_ascii=False))
    idx, allrec = write_all()
    print("total", idx["total"])
    print("por camada", json.dumps(idx["counts_by_layer"]))
    print("por malha", json.dumps(idx["counts_by_mesh"]))
    print("lotes", len(idx["batches"]), "bin MB", round(os.path.getsize(os.path.join(OUT, "l01_scatter_v3.bin")) / 1e6, 1))
    if "--no-preview" not in sys.argv:
        preview(allrec, idx)
        print("prévia ok")
