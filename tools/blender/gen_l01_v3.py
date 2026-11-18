"""Gera a Fase 1 v3 "Vale Alienígena aberto" (2 x 2 km): vale aberto com 8 zonas (carro / a pé alternados),
estrada principal suave, 1 ou 2 rotas alternativas de terra por trecho de carro, trilhas a pé, áreas planas
para os pontos de interesse, ravina do rio com a ponte, lago tóxico com ilha (colmeia), saltos opcionais e
limites naturais (morros, penhascos, rio). Paredes invisíveis só na borda do mapa.

Uso (Blender 5.2, não precisa de scipy):
  blender -b --python tools/blender/gen_l01_v3.py -- assets/work/levels/L01
  python tools/blender/plot_l01_v3.py assets/work/levels/L01      (minimapa, prévia, máscara de vegetação)
Saídas:
  L01_Terrain_v3.fbx         terreno (64 pedaços) + estrada principal (pedaços com a ponte inteira)
  l01_layout_v3.json         zonas, pontos de interesse, portões, checkpoints, itens, gatilhos... (cm, Unreal)
  l01_preview_v3.npz         dados para o minimapa e a prévia (tools/blender/plot_l01_v3.py)
  (depois: python tools/blender/plot_l01_v3.py gera o minimapa, a prévia e l01_veg_density_v3.png)
A versão 2 (tools/blender/gen_l01.py, corredor fechado) fica como histórico.

Coordenadas Blender: X leste, Y norte, Z cima (metros). Unreal: x = X*100, y = -Y*100, z = Z*100.
Cor por vértice do TERRENO = máscaras de bioma (lidas pelo material M_L01_Terrain, que já existe):
  R = areia vermelha, G = grama alien, B = terra; o resto (1-R-G-B) = musgo alien. Rocha = pela inclinação.
Cor por vértice da ESTRADA = tom (multiplica a textura em M_L01_Road).
Roteiro: docs/gameplay/L01_STORYBOARD.md (v3)

[A-069] Opção --road-flush (ou variável de ambiente JR_ROAD_FLUSH=1), DESLIGADA por padrão:
  a malha da estrada flutua sobre o terreno (borda ~22 cm acima, meio ~28 cm), e andar na beira ou atravessar
  a estrada faz o personagem subir e descer 22 cm de uma vez (item 18). Com a opção, cada lado da estrada ganha
  uma aba de 1,5 m que desce da borda até o terreno (rampa de ~8 graus); na ponte a aba fica reta.
  Só use com o OK do usuário: regera o terreno (depois: build_l01.py e scatter).
  blender -b --python tools/blender/gen_l01_v3.py -- --road-flush assets/work/levels/L01
"""
import json
import math
import os
import sys

import numpy as np

OUT = sys.argv[-1]
os.makedirs(OUT, exist_ok=True)
HALF = 1000.0          # mapa de -1000 a 1000 m
STEP = 4.0             # grade do terreno (m)
N = int(2 * HALF / STEP) + 1   # 501
CH = 8                 # 8 x 8 pedaços de 250 m
ROAD_HALF = 6.0        # meia largura da estrada principal (m)
EDGE_WALL = 985.0      # paredes invisíveis só aqui (borda do mapa)
# [A-069] aba da estrada até o terreno (ver docstring); desligada por padrão
ROAD_FLUSH = ("--road-flush" in sys.argv) or os.environ.get("JR_ROAD_FLUSH") == "1"
ROAD_SKIRT = 1.5       # largura da aba em cada lado (m)
rng = np.random.default_rng(31)

# ====================================================================== desenho (metros, Blender)
# Zonas: 0 acampamento (pé), 1 estrada A (carro), 2 posto (pé), 3 floresta (carro), 4 ponte/colmeia (pé),
#        5 fuga da horda (carro), 6 vila/nave (pé), 7 saída (carro)
ZONES = [
    dict(id=0, key="Z0_Acampamento", name="Acampamento da queda", mode="foot", center=(-700, -770), radius=75,
         landmark="Nave de resgate caída, pegando fogo", veg="sparse", biome="desert"),
    dict(id=1, key="Z1_EstradaVale", name="Estrada do vale (areia vermelha)", mode="car", center=(-280, -690), radius=200,
         landmark="Arco de pedra gigante sobre a estrada", veg="desert", biome="desert"),
    dict(id=2, key="Z2_Posto", name="Posto de gasolina abandonado", mode="foot", center=(255, -690), radius=80,
         landmark="Placa alta do posto + torre de rádio", veg="sparse", biome="dirt"),
    dict(id=3, key="Z3_Floresta", name="Floresta alienígena", mode="car", center=(370, -300), radius=170,
         landmark="Árvore-mãe gigante brilhando", veg="forest", biome="forest"),
    dict(id=4, key="Z4_PonteColmeia", name="Árvore caída na ponte / colmeia", mode="foot", center=(530, -40), radius=130,
         landmark="Colmeia alienígena na ilha do lago tóxico", veg="forest", biome="moss"),
    dict(id=5, key="Z5_FugaHorda", name="Fuga da horda", mode="car", center=(80, 360), radius=200,
         landmark="Ponte em chamas", veg="sparse", biome="grass"),
    dict(id=6, key="Z6_Vila", name="Vila da sobrevivente / disco voador", mode="foot", center=(-400, 660), radius=110,
         landmark="Disco voador enterrado", veg="sparse", biome="village"),
    dict(id=7, key="Z7_Saida", name="Saída do vale", mode="car", center=(30, 800), radius=170,
         landmark="Portão norte (passagem na serra)", veg="desert", biome="desert"),
]

# Estrada principal: pontos de controle com a zona de cada trecho (curvas largas, raio mínimo ~60 m).
ROAD_CTRL = [
    (-700, -705, 0), (-600, -700, 1), (-470, -662, 1), (-330, -615, 1), (-185, -603, 1), (-50, -635, 1),
    (80, -655, 1), (185, -652, 2), (275, -642, 2), (345, -600, 3), (372, -510, 3), (385, -400, 3),
    (425, -285, 3), (465, -170, 3), (455, -70, 3), (436, 10, 4), (432, 95, 4), (430, 165, 5), (400, 245, 5),
    (320, 320, 5), (190, 375, 5), (40, 410, 5), (-100, 460, 5), (-215, 525, 5), (-272, 575, 6),
    (-292, 630, 7), (-262, 700, 7), (-160, 762, 7), (-10, 795, 7), (140, 845, 7), (255, 895, 7), (300, 990, 7),
]
# Rotas alternativas de terra (carro): (nome, zona, pontos, salto?)
ALT_ROUTES = [
    ("Alt_Z1_Dunas", 1, [(-600, -700), (-520, -745), (-400, -790), (-250, -800), (-110, -770), (10, -705), (80, -655)], True),
    ("Alt_Z1_Pedras", 1, [(-470, -662), (-420, -585), (-320, -535), (-180, -540), (-80, -585), (-50, -635)], False),
    ("Alt_Z3_TrilhaMae", 3, [(372, -510), (305, -430), (265, -330), (275, -220), (345, -140), (420, -95), (455, -70)], False),
    ("Alt_Z5_Ribeirinha", 5, [(400, 245), (300, 255), (160, 280), (0, 320), (-120, 390), (-215, 525)], True),
    ("Alt_Z7_Serra", 7, [(-262, 700), (-230, 790), (-110, 860), (30, 880), (140, 845)], False),
]
# Trilhas a pé (só desenho no chão + terreno aplainado)
TRAILS = [
    ("Trilha_Z0", 0, [(-700, -705), (-705, -740), (-700, -770), (-735, -790)]),
    ("Trilha_Z2", 2, [(185, -652), (230, -672), (255, -690), (300, -712), (330, -722)]),
    ("Trilha_Z2b", 2, [(255, -690), (222, -722)]),
    ("Trilha_Z4", 4, [(436, 0), (470, -30), (520, -60), (572, -82)]),
    ("Trilha_Z6", 6, [(-272, 575), (-320, 605), (-350, 625), (-395, 655), (-440, 705), (-470, 742)]),
]
# Rio (ravina) atravessando o vale de oeste a leste: só a ponte cruza
RIVER_CTRL = [(-1060, 40), (-760, 110), (-520, 125), (-260, 70), (0, 80), (220, 125), (432, 95), (640, 55), (840, 90), (1060, 140)]
# Áreas planas (centro, raio, nome)
PADS = [
    ((-700, -770), 48, "Acampamento"), ((-700, -705), 14, "Buggy"), ((-785, -805), 26, "NaveQueda"),
    ((255, -690), 42, "Posto"), ((330, -722), 12, "TorreRadio"), ((222, -722), 10, "SalaTrancada"),
    ((215, -255), 22, "ArvoreMae"), ((520, -60), 16, "MargemLago"), ((628, -86), 17, "IlhaColmeia"),
    ((-395, 655), 58, "Vila"), ((-470, 745), 30, "DiscoVoador"), ((262, 905), 18, "PortaoNorte"),
]
LAKE_C, LAKE_R, ISLAND_R = np.array([628.0, -86.0]), 50.0, 17.0


# ====================================================================== geometria básica
def catmull(ctrl, step=1.0):
    p = np.array(ctrl, float)
    p = np.vstack([p[0] * 2 - p[1], p, p[-1] * 2 - p[-2]])
    pts = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        # parametrização centrípeta simplificada: amostragem densa e reamostragem por comprimento
        n = max(4, int(np.linalg.norm(p2 - p1) / step * 2))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    pts.append(p[-2])
    pts = np.array(pts)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    s = np.arange(0, d[-1], step)
    return np.stack([np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], 1)


def smooth_poly(poly, sigma):
    """Suaviza a linha (tira tremidas) mantendo as pontas."""
    out = poly.copy()
    for c in range(2):
        out[:, c] = smooth1(poly[:, c], sigma)
    out[0], out[-1] = poly[0], poly[-1]
    return out


def smooth1(v, sigma):
    k = np.arange(-3 * sigma, 3 * sigma + 1)
    w = np.exp(-0.5 * (k / sigma) ** 2)
    w /= w.sum()
    pad = np.pad(v, (len(k) // 2, len(k) // 2), mode="edge")
    return np.convolve(pad, w, mode="valid")


def tangents(poly):
    t = np.gradient(poly, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    return t, np.stack([-t[:, 1], t[:, 0]], 1)


def radius_of_curve(poly, win=10):
    t, _ = tangents(poly)
    a = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    r = np.full(len(poly), 1e6)
    da = np.abs(a[2 * win:] - a[:-2 * win])
    r[win:-win] = (2 * win) / np.maximum(da, 1e-6)
    return r


def limit_slope(v, max_slope, step=1.0):
    for _ in range(4):
        for i in range(1, len(v)):
            v[i] = np.clip(v[i], v[i - 1] - max_slope * step, v[i - 1] + max_slope * step)
        for i in range(len(v) - 2, -1, -1):
            v[i] = np.clip(v[i], v[i + 1] - max_slope * step, v[i + 1] + max_slope * step)
    return v


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def dist_poly(points, poly, sub=3, maxd=None):
    """Distância exata de cada ponto até a polilinha (segmentos a cada `sub` m) e o índice mais próximo.
    maxd: só calcula perto da linha (caixa + maxd); o resto recebe 1e6 (bem mais rápido)."""
    q = poly[::sub]
    if len(q) < 2 or not np.allclose(q[-1], poly[-1]):
        q = np.vstack([q, poly[-1]])
    a, b = q[:-1], q[1:]
    ab = b - a
    L2 = np.maximum((ab ** 2).sum(1), 1e-9)
    best = np.full(len(points), 1e12)
    bidx = np.zeros(len(points))
    sel = np.arange(len(points))
    if maxd is not None:
        mn, mx = poly.min(0) - maxd, poly.max(0) + maxd
        sel = np.where((points[:, 0] > mn[0]) & (points[:, 0] < mx[0]) & (points[:, 1] > mn[1]) & (points[:, 1] < mx[1]))[0]
    pts = points[sel]
    bs = np.full(len(pts), 1e12)
    bi = np.zeros(len(pts))
    for k0 in range(0, len(a), 32):
        A, AB, LL = a[k0:k0 + 32], ab[k0:k0 + 32], L2[k0:k0 + 32]
        if maxd is not None:     # pula pontos longe deste bloco
            bmn, bmx = np.minimum(A, A + AB).min(0) - maxd, np.maximum(A, A + AB).max(0) + maxd
            near = np.where((pts[:, 0] > bmn[0]) & (pts[:, 0] < bmx[0]) & (pts[:, 1] > bmn[1]) & (pts[:, 1] < bmx[1]))[0]
        else:
            near = np.arange(len(pts))
        if len(near) == 0:
            continue
        pp = pts[near]
        ap = pp[:, None, :] - A[None, :, :]
        t = np.clip((ap * AB[None]).sum(2) / LL[None], 0, 1)
        d = ((ap - t[..., None] * AB[None]) ** 2).sum(2)
        i = np.argmin(d, 1)
        r_ = np.arange(len(pp))
        dd = d[r_, i]
        m = dd < bs[near]
        bs[near[m]] = dd[m]
        bi[near[m]] = (k0 + i[m] + t[r_, i][m]) * sub
    best[sel] = bs
    bidx[sel] = bi
    out = np.sqrt(best)
    if maxd is not None:
        out = np.minimum(out, 1e6)
    return out, np.clip(np.round(bidx).astype(int), 0, len(poly) - 1)


def value_noise(cell, amp, seed, n=N, half=HALF):
    r = np.random.default_rng(seed)
    g = int(2 * half / cell) + 4
    grid = r.uniform(-1, 1, (g, g))
    xs_ = (np.linspace(-half, half, n) + half) / cell + 1
    i0 = np.floor(xs_).astype(int)
    f = xs_ - i0
    f = f * f * (3 - 2 * f)
    a = grid[np.ix_(i0, i0)]
    b = grid[np.ix_(i0 + 1, i0)]
    c = grid[np.ix_(i0, i0 + 1)]
    d = grid[np.ix_(i0 + 1, i0 + 1)]
    fx = f[:, None]
    fy = f[None, :]
    return amp * ((a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy)


# ====================================================================== linhas
road = smooth_poly(catmull([(x, y) for x, y, _ in ROAD_CTRL]), 6)
NR = len(road)
r_tan, r_nrm = tangents(road)
r_rad = radius_of_curve(road)
# zona de cada metro da estrada (pelo ponto de controle anterior)
ctrl_k = [int(np.argmin(np.linalg.norm(road - np.array([x, y]), axis=1))) for x, y, _ in ROAD_CTRL]
road_zone = np.zeros(NR, int)
for (x, y, z), k in zip(ROAD_CTRL, ctrl_k):
    road_zone[k:] = z
alts = [(nm, z, smooth_poly(catmull(pts), 5), jump) for nm, z, pts, jump in ALT_ROUTES]
trails = [(nm, z, catmull(pts)) for nm, z, pts in TRAILS]
river = smooth_poly(catmull(RIVER_CTRL), 8)
print(f"estrada {NR} m, raio mínimo {r_rad[20:-20].min():.0f} m (k={int(np.argmin(r_rad[20:-20])) + 20})")
for nm, z, p, _ in alts:
    print(f"  {nm}: {len(p)} m, raio mínimo {radius_of_curve(p)[12:-12].min():.0f} m")

# trecho da ponte (estrada sobre a ravina)
dr_road_river, _ = dist_poly(road, river, 2)
bridge_k = np.where(dr_road_river < 26)[0]
K_BR0, K_BR1 = int(bridge_k.min()), int(bridge_k.max())
K_BRC = (K_BR0 + K_BR1) // 2
print("ponte", K_BR0, K_BR1, "comprimento", K_BR1 - K_BR0)

# ====================================================================== relevo base (sem escavação)
xs = np.linspace(-HALF, HALF, N)
X, Y = np.meshgrid(xs, xs, indexing="ij")
P = np.stack([X.ravel(), Y.ravel()], 1)
# fundo do vale: ondulações longas e baixas, leve caimento para o rio
floor = (value_noise(380, 7, 1) + value_noise(140, 2.6, 2) + value_noise(45, 0.7, 3)).ravel()
d_riv, i_riv = dist_poly(P, river, 3)
floor += np.clip(d_riv / 900.0, 0, 1) * 9.0
# distância à "rede jogável" (estradas, alternativas, trilhas, áreas planas)
d_road, i_road = dist_poly(P, road, 2)
d_net = d_road.copy()
D_ALT = [dist_poly(P, p, 2, maxd=330) for nm, z, p, _ in alts]
D_TR = [dist_poly(P, p, 2, maxd=330) for nm, z, p in trails]
for d_, _ in D_ALT:
    d_net = np.minimum(d_net, d_ + 15)
for d_, _ in D_TR:
    d_net = np.minimum(d_net, d_ + 25)
for (c, r, nm) in PADS:
    d_net = np.minimum(d_net, np.linalg.norm(P - np.array(c), axis=1) - r + 10)
for zd in ZONES:     # zonas a pé ganham uma clareira maior
    if zd["mode"] == "foot":
        d_net = np.minimum(d_net, np.linalg.norm(P - np.array(zd["center"]), axis=1) - zd["radius"] + 30)
n_hill = value_noise(170, 1.0, 11).ravel() * 0.5 + 0.5
fbm = (value_noise(120, 0.6, 14) + value_noise(55, 0.3, 15) + value_noise(25, 0.1, 16)).ravel()
# distância "torta" (o pé dos morros não acompanha a estrada certinho)
d_soft = d_net + value_noise(90, 35, 17).ravel()
# morros entre as rotas: começam suaves (dá para subir de buggy no começo) e ficam íngremes longe
hills = sstep(50, 230, d_soft) * (26 + 46 * n_hill) * (1 + 0.45 * fbm)
# alguns penhascos naturais (mesas) longe das rotas: degrau de 14 m
cliff_sel = sstep(0.3, 0.45, value_noise(200, 1.0, 13).ravel())
hills += cliff_sel * sstep(165, 180, d_soft) * 14
# serra da borda (mapa fechado por montanhas e penhascos)
edge = np.maximum(np.abs(P[:, 0]), np.abs(P[:, 1])) + value_noise(80, 25, 18).ravel()
rim = sstep(740, 920, edge) * (95 + 40 * n_hill) + sstep(805, 830, edge) * 26
H0 = floor + np.maximum(hills, rim * sstep(30, 120, d_net))   # a estrada abre a passagem na serra (portão norte)


def blur_grid(g, sigma):
    k = np.arange(-3 * sigma, 3 * sigma + 1)
    w = np.exp(-0.5 * (k / sigma) ** 2)
    w /= w.sum()
    pad = np.pad(g, len(k) // 2, mode="edge")
    tmp = np.apply_along_axis(lambda v: np.convolve(v, w, mode="valid"), 0, pad)
    return np.apply_along_axis(lambda v: np.convolve(v, w, mode="valid"), 1, tmp)


H0 = blur_grid(H0.reshape(N, N), 2).ravel()     # tira vincos e degraus duros (relevo mais natural)
H0g = H0.reshape(N, N)


def sample(Hg, pts):
    pts = np.atleast_2d(pts)
    fi = (pts[:, 0] + HALF) / STEP
    fj = (pts[:, 1] + HALF) / STEP
    i0 = np.clip(np.floor(fi).astype(int), 0, N - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, N - 2)
    tx, ty = np.clip(fi - i0, 0, 1), np.clip(fj - j0, 0, 1)
    return (Hg[i0, j0] * (1 - tx) * (1 - ty) + Hg[i0 + 1, j0] * tx * (1 - ty)
            + Hg[i0, j0 + 1] * (1 - tx) * ty + Hg[i0 + 1, j0 + 1] * tx * ty)


# ====================================================================== perfis (altura) das rotas
road_h = limit_slope(smooth1(sample(H0g, road), 40), 0.065)
road_h[K_BR0 - 10:K_BR1 + 11] = np.linspace(road_h[K_BR0 - 10], road_h[K_BR1 + 10], K_BR1 - K_BR0 + 21)
road_h = smooth1(road_h, 6)
road_h = limit_slope(road_h, 0.07)
# trecho final na passagem da serra: sobe no máximo 7%
alt_h = []
for nm, z, p, jump in alts:
    _, ka = dist_poly(p[[0, -1]], road, 1)
    h = limit_slope(smooth1(sample(H0g, p), 25), 0.12)
    # pontas casam com a estrada principal
    h += np.linspace(road_h[ka[0]] - h[0], road_h[ka[1]] - h[-1], len(h))
    h = limit_slope(h, 0.12)
    alt_h.append(h)
trail_h = [limit_slope(smooth1(sample(H0g, p), 8), 0.2) for nm, z, p in trails]
pad_h = []
for (c, r, nm) in PADS:
    pad_h.append(float(np.median(sample(H0g, np.array(c) + rng.uniform(-r, r, (40, 2)) * 0.6))))
# casa as alturas: acampamento/buggy/posto/vila na altura da estrada perto deles
for i, (c, r, nm) in enumerate(PADS):
    d, k = dist_poly(np.array([c]), road, 1)
    if d[0] < r + 40:
        pad_h[i] = float(road_h[k[0]]) + 0.1
pad_h[[p[2] for p in PADS].index("IlhaColmeia")] = pad_h[[p[2] for p in PADS].index("MargemLago")]
for (nm, z, p), h in zip(trails, trail_h):
    _, k0 = dist_poly(p[[0]], road, 1)
    h += (road_h[k0[0]] - h[0]) * np.linspace(1, 0, len(h)) ** 2 * (np.linalg.norm(p[0] - road[k0[0]]) < 6)
# trilhas terminam nas áreas planas
for ti, (nm, z, p) in enumerate(trails):
    for (c, r, pn), ph in zip(PADS, pad_h):
        for end in (0, -1):
            if np.linalg.norm(p[end] - np.array(c)) < r:
                n_ = min(40, len(p))
                w = np.linspace(1, 0, n_) if end == 0 else np.linspace(0, 1, n_)
                sl = slice(0, n_) if end == 0 else slice(len(p) - n_, len(p))
                trail_h[ti][sl] = trail_h[ti][sl] * (1 - w) + ph * w

# ====================================================================== saltos opcionais (nas alternativas)
JUMPS = []
GAP = 10.0
for ai, (nm, z, p, jump) in enumerate(alts):
    if not jump:
        continue
    rr = radius_of_curve(p, 12)
    best, bk = 1e9, None
    for k in range(80, len(p) - 80):
        if rr[k - 60:k + 40].min() < 250:      # reta de 60 m antes e 40 m depois
            continue
        grade = abs(alt_h[ai][k + 30] - alt_h[ai][k - 60]) / 90
        score = grade * 100 + abs(k - len(p) * 0.5) * 0.01
        if score < best:
            best, bk = score, k
    if bk is None:
        bk = len(p) // 2
        print("aviso: sem reta boa para o salto em", nm)
    # perfil plano no salto (sem lombada)
    a0, a1 = bk - 60, bk + 45
    alt_h[ai][a0:a1] = np.linspace(alt_h[ai][a0], alt_h[ai][a1], a1 - a0)
    t_, n_ = tangents(p)
    JUMPS.append(dict(route=nm, k=bk, p=p[bk], t=t_[bk], n=n_[bk], h=float(alt_h[ai][bk])))
    print("salto em", nm, "k", bk, "raio min", round(float(rr[bk - 60:bk + 40].min())))

# ====================================================================== escavação do terreno
Hf = H0.copy()
# 1) áreas planas
for (c, r, nm), ph in zip(PADS, pad_h):
    dist = np.linalg.norm(P - np.array(c), axis=1)
    w = 1 - sstep(r, r + 26, dist)
    Hf = Hf * (1 - w) + (ph - 0.05) * w
# 2) trilhas a pé
for (nm, z, p), h, (d, k) in zip(trails, trail_h, D_TR):
    w = 1 - sstep(2.5, 11, d)
    Hf = Hf * (1 - w) + (h[k] - 0.05) * w
# 3) alternativas de terra
d_alt_all = np.full(len(P), 1e9)
for (nm, z, p, jump), h, (d, k) in zip(alts, alt_h, D_ALT):
    w = 1 - sstep(4.5, 18, d)
    Hf = Hf * (1 - w) + (h[k] - 0.08) * w
    d_alt_all = np.minimum(d_alt_all, d)
# 4) estrada principal (menos no vão da ponte: a ravina continua por baixo)
w_road = 1 - sstep(ROAD_HALF + 1.5, 30, d_road)
on_bridge = (i_road >= K_BR0 - 4) & (i_road <= K_BR1 + 4) & (d_riv < 24)
w_road = np.where(on_bridge, 0.0, w_road)
Hf = Hf * (1 - w_road) + (road_h[i_road] - 0.3) * w_road
# 5) valas dos saltos (rasas, com saída pelos lados: nunca é queda fatal)
for j in JUMPS:
    c = j["p"] + j["t"] * GAP / 2
    s = (P - c) @ j["t"]
    l_ = (P - c) @ j["n"]
    depth = 1.9 * (1 - sstep(GAP / 2 - 1.5, GAP / 2 + 1.0, np.abs(s))) * (1 - sstep(8, 15, np.abs(l_)))
    Hf = np.where(depth > 0.01, np.minimum(Hf, j["h"] - 0.08 - depth), Hf)
# 6) ravina do rio (paredes íngremes, leito 15 m abaixo)
bed = smooth1(sample(H0g, river), 60) - 15.0
w_rv = 1 - sstep(7.0, 21.0, d_riv)
Hf = np.where(w_rv > 0, Hf * (1 - w_rv) + bed[i_riv] * w_rv, Hf)
# 7) lago tóxico em anel em volta da ilha da colmeia
dl = np.linalg.norm(P - LAKE_C, axis=1)
lake_h = pad_h[[p[2] for p in PADS].index("IlhaColmeia")]
in_lake = (dl < LAKE_R) & (dl > ISLAND_R)
Hf = np.where(in_lake, np.minimum(Hf, lake_h - 2.6), Hf)
rim_l = (dl >= LAKE_R) & (dl < LAKE_R + 6)
Hf = np.where(rim_l, np.minimum(Hf, lake_h + 0.1 + (dl - LAKE_R) * 0.15), Hf)
H2 = Hf.reshape(N, N)

# ====================================================================== biomas (cor por vértice)
gx, gy = np.gradient(H2, STEP)
slope = np.sqrt(gx ** 2 + gy ** 2)
BIOMES = {"desert": (0.92, 0.03, 0.03), "dirt": (0.35, 0.10, 0.45), "forest": (0.0, 0.55, 0.05),
          "moss": (0.0, 0.25, 0.05), "grass": (0.12, 0.62, 0.08), "village": (0.05, 0.35, 0.30)}
zone_biome = {zd["id"]: np.array(BIOMES[zd["biome"]]) for zd in ZONES}
# bioma ao longo da estrada (suavizado entre zonas) + zonas a pé pelo centro
road_bio = np.array([zone_biome[z] for z in road_zone])
for c in range(3):
    road_bio[:, c] = smooth1(road_bio[:, c], 70)
mask = road_bio[i_road].copy()
for zd in ZONES:
    if zd["mode"] == "foot":
        dz = np.linalg.norm(P - np.array(zd["center"]), axis=1)
        w = (1 - sstep(zd["radius"] * 0.6, zd["radius"] * 1.6, dz))[:, None]
        mask = mask * (1 - w) + zone_biome[zd["id"]][None] * w
# borra no espaço (sem linha dura onde muda a "estrada mais próxima")
mask = np.stack([blur_grid(mask[:, c].reshape(N, N), 10).ravel() for c in range(3)], 1)
nz = value_noise(55, 1, 31).ravel()
mask[:, 0] = np.clip(mask[:, 0] * (0.85 + 0.2 * nz), 0, 1)
mask[:, 1] = np.clip(mask[:, 1] * (0.8 + 0.35 * value_noise(30, 1, 32).ravel()), 0, 1)
# morros altos: musgo (o material põe rocha pela inclinação)
high = sstep(35, 80, Hf - floor)[:, None]
mask = mask * (1 - high * 0.7)
# terra nas estradas, alternativas, trilhas e áreas planas
Bx = np.maximum(1 - sstep(ROAD_HALF + 1, ROAD_HALF + 6, d_road), 1 - sstep(3.2, 6.5, d_alt_all))
for d_, _ in D_TR:
    Bx = np.maximum(Bx, 1 - sstep(1.4, 3.5, d_))
for (c, r, nm) in PADS:
    dist = np.linalg.norm(P - np.array(c), axis=1)
    Bx = np.maximum(Bx, (1 - sstep(r * 0.55, r * 0.95, dist)) * (0.65 + 0.3 * nz))
mask[:, 0] *= (1 - Bx)
mask[:, 1] *= (1 - Bx)
mask[:, 2] = np.maximum(mask[:, 2] * (1 - Bx), Bx)
mask = np.clip(mask, 0, 1)
s_ = mask.sum(1)
mask = np.where((s_ > 1)[:, None], mask / s_[:, None], mask)
maskg = mask.reshape(N, N, 3)

TEX_RGB = {"red": (0.70, 0.31, 0.15), "grass": (0.21, 0.46, 0.54), "dirt": (0.54, 0.37, 0.22),
           "moss": (0.39, 0.23, 0.51), "rock": (0.39, 0.37, 0.45), "toxic": (0.43, 0.8, 0.15), "water": (0.15, 0.35, 0.45)}
rest = np.clip(1 - maskg.sum(-1), 0, 1)[..., None]
prev = (maskg[..., :1] * TEX_RGB["red"] + maskg[..., 1:2] * TEX_RGB["grass"] + maskg[..., 2:3] * TEX_RGB["dirt"]
        + rest * TEX_RGB["moss"])
rk = sstep(0.55, 0.85, slope)[..., None]
prev = prev * (1 - rk) + np.array(TEX_RGB["rock"]) * rk
prev = np.where(in_lake.reshape(N, N)[..., None], np.array(TEX_RGB["toxic"]), prev)
prev = np.where((d_riv < 8).reshape(N, N)[..., None], np.array(TEX_RGB["water"]), prev)

# ====================================================================== malha da estrada (com a ponte)
CROSS = np.array([-6, -4.5, -3, -1.5, 0, 1.5, 3, 4.5, 6])
if ROAD_FLUSH:   # [A-069] aba de cada lado
    CROSS = np.concatenate([[-6 - ROAD_SKIRT], CROSS, [6 + ROAD_SKIRT]])
road_v, road_c = [], []
for k in range(NR):
    on_br = K_BR0 - 2 <= k <= K_BR1 + 2
    for o in CROSS:
        p = road[k] + r_nrm[k] * o
        z = road_h[k] + 0.06 - 0.004 * o * o
        if abs(o) > 6.01:
            # [A-069] aba: termina 2 cm abaixo do terreno (sem degrau); na ponte segue reta na altura da borda
            z_edge = road_h[k] + 0.06 - 0.004 * 36.0
            z = z_edge if on_br else min(z_edge, float(sample(H2, p)[0]) - 0.02)
        tone = 0.95 + 0.05 * math.sin(k * 0.37 + o)
        c = (tone, tone, tone) if abs(o) < 5 else (0.80, 0.72, 0.62)
        if on_br:
            c = (0.62, 0.48, 0.36)   # tábuas da ponte (mais escuro)
        road_v.append((p[0], p[1], z))
        road_c.append(c)
road_v = np.array(road_v)

# ====================================================================== Blender
import bpy  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
mat_t = bpy.data.materials.new("M_L01_Terrain")
mat_r = bpy.data.materials.new("M_L01_Road")


def make_obj(name, verts, faces, cols, mat):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ca = me.color_attributes.new("Col", "BYTE_COLOR", "POINT")
    c4 = np.concatenate([np.asarray(cols, float), np.ones((len(cols), 1))], 1).ravel()
    ca.data.foreach_set("color", c4.astype(np.float32))
    me.color_attributes.active_color = ca
    me.color_attributes.render_color_index = me.color_attributes.find("Col")
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


edges_ = np.linspace(0, N - 1, CH + 1).round().astype(int)
for a in range(CH):
    for b in range(CH):
        i0, i1, j0, j1 = edges_[a], edges_[a + 1], edges_[b], edges_[b + 1]
        ni, nj = i1 - i0 + 1, j1 - j0 + 1
        ii, jj = np.meshgrid(np.arange(i0, i1 + 1), np.arange(j0, j1 + 1), indexing="ij")
        verts = np.stack([xs[ii], xs[jj], H2[ii, jj]], -1).reshape(-1, 3)
        cols = maskg[ii, jj].reshape(-1, 3)
        faces = []
        for u in range(ni - 1):
            for v in range(nj - 1):
                q = u * nj + v
                # diagonal escolhida pela menor diferença de altura (relevo sem "dentes")
                h00, h10, h11, h01 = H2[i0 + u, j0 + v], H2[i0 + u + 1, j0 + v], H2[i0 + u + 1, j0 + v + 1], H2[i0 + u, j0 + v + 1]
                if abs(h00 - h11) <= abs(h10 - h01):
                    faces.append((q, q + nj, q + nj + 1))
                    faces.append((q, q + nj + 1, q + 1))
                else:
                    faces.append((q, q + nj, q + 1))
                    faces.append((q + nj, q + nj + 1, q + 1))
        make_obj(f"SM_L01v3_Terrain_{a}_{b}", verts, faces, cols, mat_t)

nc = len(CROSS)
seg_id = 0
for s0 in range(0, NR - 1, 250):
    ks = list(range(s0, min(NR, s0 + 251)))
    if len(ks) < 2:
        continue
    verts = np.concatenate([road_v[k * nc:(k + 1) * nc] for k in ks])
    cols = sum([road_c[k * nc:(k + 1) * nc] for k in ks], [])
    faces = []
    for k in range(len(ks) - 1):
        for o in range(nc - 1):
            q = k * nc + o
            faces.append((q, q + 1, q + nc + 1, q + nc))
    make_obj(f"SM_L01v3_Road_{seg_id:02d}", verts, faces, cols, mat_r)
    seg_id += 1

for ob in bpy.context.scene.objects:
    ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "L01_Terrain_v3.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, mesh_smooth_type="FACE", colors_type="LINEAR")
print("fbx ok", len(bpy.context.scene.objects), "objetos")


# ====================================================================== layout (cm, Unreal)
def ue(p, z):
    return [round(float(p[0]) * 100, 1), round(-float(p[1]) * 100, 1), round(float(z) * 100, 1)]


def yaw_of(d):
    return round(math.degrees(math.atan2(-d[1], d[0])), 1)


def gh(p):
    return float(sample(H2, np.array([p]))[0])


def road_pt(k, o=0.0):
    k = int(np.clip(k, 0, NR - 1))
    return road[k] + r_nrm[k] * o


def road_k(p):
    return int(np.argmin(np.linalg.norm(road - np.array(p), axis=1)))


def pad(name):
    i = [p[2] for p in PADS].index(name)
    return np.array(PADS[i][0], float), PADS[i][1], pad_h[i]


L = {"version": 3, "map_half_cm": HALF * 100, "units": "cm (Unreal: x leste, y sul, z cima)",
     "road_length_m": NR, "kill_z_cm": round((float(H2.min()) - 40) * 100),
     "zones": [], "pois": [], "gates": [], "checkpoints": [], "story": [], "pickups": [], "chests": [],
     "enemies": [], "director_zones": [], "lights": [], "hazards": [], "walls": [], "veg_hints": [],
     "barricades": [], "horde": {}, "routes": {}}

# ---- zonas
for zd in ZONES:
    c = np.array(zd["center"], float)
    ks = np.where(road_zone == zd["id"])[0]
    L["zones"].append({"id": zd["id"], "key": zd["key"], "name": zd["name"], "mode": zd["mode"],
                       "center": ue(c, gh(c)), "radius_cm": zd["radius"] * 100, "landmark": zd["landmark"],
                       "road_m": [int(ks.min()), int(ks.max())] if len(ks) else None,
                       "veg": zd["veg"]})
# ---- rotas (para o minimapa, a navegação e a vegetação manter livre)
L["routes"]["main"] = {"half_width_m": ROAD_HALF, "samples": [ue(road[k], road_h[k]) for k in range(0, NR, 20)]}
for (nm, z, p, jump), h in zip(alts, alt_h):
    L["routes"][nm] = {"zone": z, "half_width_m": 4.0, "kind": "dirt", "samples": [ue(p[k], h[k]) for k in range(0, len(p), 20)]}
for (nm, z, p), h in zip(trails, trail_h):
    L["routes"][nm] = {"zone": z, "half_width_m": 2.0, "kind": "trail", "samples": [ue(p[k], h[k]) for k in range(0, len(p), 10)]}
L["river"] = {"half_width_m": 21.0, "samples": [ue(river[k], bed[k]) for k in range(0, len(river), 25)]}


# ---- peças de cenário (blockout): "q" = Quaternius "Pack/Modelo", "mesh" = props L01, "engine" = forma básica
def piece(poi, p, z, yaw=0.0, scale=1.0, q=None, mesh=None, engine=None, pitch=0.0, roll=0.0, col="simple", cull=0):
    sc = [round(float(s), 3) for s in scale] if isinstance(scale, (list, tuple)) else round(float(scale), 3)
    e = {"loc": ue(p, z), "rot": [round(float(pitch), 1), round(float(yaw), 1), round(float(roll), 1)], "scale": sc,
         "col": col, "cull_m": cull}
    if q:
        e["q"] = q
    elif mesh:
        e["mesh"] = mesh
    else:
        e["engine"] = engine
    poi["pieces"].append(e)
    return e


def new_poi(key, name, zone, p, kind):
    poi = {"key": key, "name": name, "zone": zone, "kind": kind, "loc": ue(p, gh(p)), "pieces": []}
    L["pois"].append(poi)
    return poi


def light(p, z, color, intensity, radius, label):
    L["lights"].append({"loc": ue(p, z), "color": color, "intensity": intensity, "radius_cm": radius * 100, "label": label})


def pickup(p, z, typ, amount, label, display=None):
    e = {"loc": ue(p, z + 0.8), "type": typ, "amount": amount, "label": label}
    if display:
        e["display"] = display
    L["pickups"].append(e)


def chest(p, z, yaw, label, weapon="NONE", ammo=0, health=0, key_item="", key_label="", horde=None, tier="common"):
    L["chests"].append({"loc": ue(p, z + 0.02), "yaw": yaw, "label": label, "weapon": weapon, "ammo": ammo,
                        "health": health, "key_item": key_item, "key_label": key_label, "horde": horde, "tier": tier})


def story(p, z, label, msg, hint, foot=True, extent=(1500, 1500, 600), completes=False):
    L["story"].append({"loc": ue(p, z + 1.5), "label": label, "message": msg, "objective_hint": hint,
                       "on_foot_only": foot, "box_extent": list(extent), "completes_level": completes})


def enemy(p, typ, label, z=None):
    L["enemies"].append({"type": typ, "loc": ue(p, (gh(p) if z is None else z) + 1.0), "label": label})


def dzone(label, p, z, extent_m, yaw=0.0, no_spawns=False, block_hordes=False, density=1.0, decay=1.0, priority=0):
    L["director_zones"].append({"label": label, "loc": ue(p, z), "extent_cm": [e * 100 for e in extent_m], "yaw": yaw,
                                "no_spawns": no_spawns, "block_event_hordes": block_hordes, "density": density,
                                "decay": decay, "priority": priority})


def checkpoint(label, cid, p, z, yaw, stage, weapons=(), keys=(), transition=False, start=False, park=None, needs_item=""):
    cp = {"label": label, "id": cid, "loc": ue(p, z), "yaw": yaw, "stage": stage, "transition": transition,
          "level_start": start, "respawn_melee": "melee" in weapons, "respawn_pistol": "pistol" in weapons,
          "respawn_shotgun": "shotgun" in weapons, "respawn_key_items": list(keys), "vehicle_needs_item": needs_item}
    if park is not None:
        cp["park_vehicle"] = {"loc": ue(park[0], park[1] + 0.9), "yaw": park[2]}
    L["checkpoints"].append(cp)


# ------------------------------------------------------------------ Z0 acampamento (a pé)
camp, camp_r, camp_h = pad("Acampamento")
bug, _, bug_h = pad("Buggy")
k_bug = road_k(bug)
L["vehicle_start"] = {"loc": ue(road[k_bug], road_h[k_bug] + 0.9), "yaw": yaw_of(r_tan[k_bug]),
                      "note": "buggy estacionado no acampamento; o jogador começa A PÉ e precisa da chave (barraca)"}
poi = new_poi("Acampamento", "Acampamento da queda", 0, camp, "camp")
tents = []
for q_, (ang, rr_) in enumerate([(200, 22), (240, 26), (290, 21), (330, 27), (20, 24)]):
    p = camp + np.array([math.cos(math.radians(ang)), math.sin(math.radians(ang))]) * rr_
    tents.append(p)
    piece(poi, p, camp_h - 0.05, ang + 90, [4.2, 4.2, 2.6], engine="Cone", col="simple", cull=600)
for q_ in range(10):
    p = camp + rng.uniform(-28, 28, 2)
    if min(np.linalg.norm(p - t) for t in tents) < 5:
        continue
    m = ["ZombieKit/Barrel", "ZombieKit/Pallet", "SpaceKit/Pickup_Crate", "ZombieKit/TrashBag_1", "ZombieKit/Wheels_Stack"][q_ % 5]
    piece(poi, p, camp_h, rng.uniform(0, 360), 1.0, q=m, cull=300)
piece(poi, camp + np.array([0, 4.0]), camp_h, 0, 1.0, q="ZombieKit/Couch", cull=300)   # "sala" do acampamento
light(camp + np.array([0, 0]), camp_h + 3, [1.0, 0.6, 0.3], 9000, 14, "Fogueira_Acampamento")
ship, _, ship_h = pad("NaveQueda")
poi_s = new_poi("NaveQueda", "Nave de resgate caída (marco)", 0, ship, "landmark")
piece(poi_s, ship, ship_h - 1.6, 35, 2.6, q="SpaceKit/Spaceship_FinnTheFrog", pitch=-9, roll=17, col="complex", cull=0)
for q_ in range(5):
    pp = ship + rng.uniform(-9, 9, 2)
    piece(poi_s, pp, gh(pp) - 0.2, rng.uniform(0, 360), rng.uniform(0.8, 1.5), q="SpaceKit/Rock_1", cull=600)
for q_, off in enumerate([(-4, 2), (5, -3), (0, 6)]):
    light(ship + np.array(off), ship_h + 2.5, [1.0, 0.45, 0.12], 25000, 22, f"Fogo_Nave_{q_ + 1}")
tent_key = tents[3]
chest(tent_key, camp_h, yaw_of(camp - tent_key), "Bau_ChaveBuggy", key_item="CarKey", key_label="CHAVE DO BUGGY", tier="key")
pickup(camp + np.array([9, -6]), camp_h, "WEAPON_MELEE", 1, "Pickup_Graveto", display="SM_AlienStick")
pickup(camp + np.array([-12, 10]), camp_h, "HEALTH", 30, "Pickup_Vida_Acampamento")
for q_ in range(4):     # 3 a 5 zumbis lentos (tutorial)
    ang = math.radians(150 + q_ * 22)
    enemy(camp + np.array([math.cos(ang), math.sin(ang)]) * (camp_r + 14), "melee", f"ENM_Z0_Lento_{q_ + 1}")
story(camp, camp_h, "Historia_Z0_Queda", "Nossa nave caiu! Zumbis vindo. Pegue aquele galho brilhante.",
      "Pegue o graveto [E] e se defenda", extent=(2500, 2500, 800))
story(tents[2], camp_h, "Historia_Z0_Chave", "A chave do buggy ficou numa das barracas.",
      "Procure a chave nas barracas", extent=(900, 900, 600))
story(bug, bug_h, "Historia_Z0_Buggy", "O buggy! Com a chave, chegue perto e aperte E.",
      "Entre no buggy [E]", extent=(700, 700, 500))
checkpoint("CP_Z0_Inicio", "Start", camp + np.array([6, 8]), camp_h, yaw_of(bug - camp), "ON_FOOT", start=True)
dzone("DZ_Z0_AcampamentoSeguro", camp, camp_h, (110, 110, 40), no_spawns=True, block_hordes=True, decay=2.0, priority=10)

# ------------------------------------------------------------------ Z1 estrada A (carro)
ks1 = np.where(road_zone == 1)[0]
k_arch = road_k((-330, -615))
poi = new_poi("ArcoPedra", "Arco de pedra gigante", 1, road[k_arch], "landmark")
piece(poi, road[k_arch], road_h[k_arch] - 0.6, yaw_of(r_tan[k_arch]) + 90, 2.6, mesh="SM_AlienArch", col="complex")
checkpoint("CP_Z1_Estrada", "Z1_Road", road_pt(ks1[0] + 70), road_h[ks1[0] + 70], yaw_of(r_tan[ks1[0] + 70]), "DRIVING",
           weapons=("melee",), keys=("CarKey",))
story(road_pt(ks1[0] + 40), road_h[ks1[0] + 40], "Historia_Z1_Combustivel",
      "Tanque na reserva. Siga até o posto de gasolina.", "Vá ao posto (placa alta)", foot=False, extent=(1500, 1500, 600))
wreck_models = ["CarsPack/SUV", "ZombieKit/Vehicle_Pickup", "CarsPack/Taxi"]
for i, f in enumerate((0.22, 0.48, 0.74)):
    k = int(ks1[0] + f * len(ks1))
    side = 1 if i % 2 == 0 else -1
    p = road_pt(k, side * 11)
    poi_w = new_poi(f"Destroco_Z1_{i + 1}", "Carro abandonado com saque", 1, p, "wreck")
    piece(poi_w, p, gh(p) - 0.1, yaw_of(r_tan[k]) + rng.uniform(-30, 30), 1.0, q=wreck_models[i],
          roll=(170 if i == 1 else 0), col="simple", cull=900)
    pickup(road_pt(k, side * 6.5), road_h[k], "REPAIR" if i != 1 else "NITRO", 30 if i != 1 else 0.35, f"Pickup_Destroco_Z1_{i + 1}")
for i, f in enumerate((0.15, 0.4, 0.62, 0.86)):  # grupos para atropelar
    k = int(ks1[0] + f * len(ks1))
    for j in range(int(rng.integers(3, 5))):
        enemy(road_pt(k + j * 3, rng.uniform(-7, 7)), "melee", f"ENM_Z1_G{i + 1}_{j + 1}", z=road_h[k])
for i, f in enumerate((0.3, 0.65)):
    k = int(ks1[0] + f * len(ks1))
    pickup(road_pt(k, rng.uniform(-3, 3)), road_h[k], "NITRO", 0.25, f"Pickup_Nitro_Z1_{i + 1}")

# ------------------------------------------------------------------ Z2 posto de gasolina (a pé)
st, st_r, st_h = pad("Posto")
k_gate2 = road_k((185, -652))
t2 = r_tan[k_gate2]
poi = new_poi("Posto", "Posto de gasolina (kitbash)", 2, st, "gas_station")
yaw_st = yaw_of(t2)
fwd, side_v = t2, np.array([-t2[1], t2[0]])          # side_v aponta para o norte (estrada)
canopy_c = st + side_v * 12
for cx, cy in ((-6, -3.5), (6, -3.5), (-6, 3.5), (6, 3.5)):
    p = canopy_c + fwd * cx + side_v * cy
    piece(poi, p, st_h, yaw_st, [1.0, 1.0, 1.2], q="Ruins/Column_Square", col="simple")
piece(poi, canopy_c, st_h + 4.8, yaw_st, [7.0, 4.4, 1.0], q="Ruins/Floor_SquareLarge", col="simple")
for cx in (-3, 3):
    piece(poi, canopy_c + fwd * cx, st_h, yaw_st, [0.6, 1.1, 1.6], engine="Cube", col="simple")   # bombas
piece(poi, st - side_v * 6, st_h, yaw_st, 1.0, q="SpaceKit/Building_L", col="complex")
piece(poi, st - side_v * 6 + fwd * 2, st_h + 4.3, yaw_st, 1.0, q="SpaceKit/Roof_Radar", col="none")
piece(poi, road_pt(k_gate2 + 30, -9), road_h[k_gate2 + 30], yaw_st + 90, 1.7, q="ZombieKit/TownSign", col="simple")
for q_, (cx, cy) in enumerate(((-16, 8), (16, 8), (-14, -12), (18, -14))):
    piece(poi, st + fwd * cx + side_v * cy, st_h, yaw_st + 90, 1.0, q="ZombieKit/StreetLights", col="simple")
for q_ in range(12):
    p = st + fwd * rng.uniform(-30, 30) + side_v * rng.uniform(-24, 4)
    if np.linalg.norm(p - canopy_c) < 9 or np.linalg.norm(p - (st - side_v * 6)) < 8:
        continue
    m = ["ZombieKit/TrafficBarrier_1", "ZombieKit/Barrel", "ZombieKit/Pallet_Broken", "ZombieKit/TrashBag_2",
         "ZombieKit/Container_Red", "ZombieKit/Wheels_Stack"][q_ % 6]
    piece(poi, p, st_h, rng.uniform(0, 360), 1.0, q=m, cull=500)
piece(poi, st + fwd * 20 - side_v * 2, st_h, yaw_st + 25, 1.0, q="ZombieKit/Vehicle_Truck", col="simple")
room, _, room_h = pad("SalaTrancada")
poi_r = new_poi("SalaTrancada", "Sala dos fundos (pistola)", 2, room, "locked_room")
piece(poi_r, room, room_h, yaw_st + 180, 1.0, q="SpaceKit/House_Single", col="complex")
chest(room, room_h, yaw_st, "Bau_Pistola_Posto", weapon="PISTOL", ammo=24, tier="rare")
tower, _, tower_h = pad("TorreRadio")
poi_t = new_poi("TorreRadio", "Torre de rádio (marco)", 2, tower, "landmark")
piece(poi_t, tower, tower_h, 20, 7.0, q="SpaceKit/Roof_Antenna", col="simple")
light(tower, tower_h + 25, [1.0, 0.1, 0.1], 8000, 30, "Luz_TorreRadio")
chest(canopy_c + fwd * 3 + side_v * 1.6, st_h, yaw_st, "Bomba_Galao", key_item="Fuel", key_label="GALÃO CHEIO",
      horde={"size": 22, "duration": 50}, tier="objective")
pickup(st - side_v * 3 + fwd * 6, st_h, "HEALTH", 50, "Pickup_Medkit_Posto")
pickup(st + fwd * -8 - side_v * 10, st_h, "AMMO", 12, "Pickup_Municao_Posto")
park2 = road_pt(k_gate2 + 6, 0)
checkpoint("CP_Z2_Posto", "Z2_Posto", road_pt(k_gate2), road_h[k_gate2], yaw_st, "ON_FOOT", weapons=("melee",),
           keys=("CarKey",), transition=True, park=(park2, road_h[k_gate2 + 6], yaw_st), needs_item="Fuel")
story(road_pt(k_gate2 + 4), road_h[k_gate2], "Historia_Z2_Posto", "O tanque secou! Encha um galão na bomba.",
      "Encha o galão na bomba [E]", extent=(1400, 1400, 600))
story(st - side_v * 14, st_h, "Historia_Z2_Sala", "A sala dos fundos tem algo trancado lá dentro...",
      "Procure a pistola na sala dos fundos", extent=(900, 900, 600))
dzone("DZ_Z2_Posto", st, st_h, (95, 95, 40), density=1.3, priority=5)
enemy(st + fwd * 12 - side_v * 14, "melee", "ENM_Z2_1")
enemy(st - fwd * 15 - side_v * 8, "melee", "ENM_Z2_2")

# ------------------------------------------------------------------ Z3 floresta (carro)
ks3 = np.where(road_zone == 3)[0]
k3 = int(ks3[0] + 60)
checkpoint("CP_Z3_Floresta", "Z3_Forest", road_pt(k3), road_h[k3], yaw_of(r_tan[k3]), "DRIVING",
           weapons=("melee", "pistol"), keys=("CarKey",))
story(road_pt(k3 + 30), road_h[k3 + 30], "Historia_Z3_Floresta", "Floresta alienígena. Se subirem no carro, faça zigue-zague!",
      "Siga até a ponte do rio", foot=False)
mt, _, mt_h = pad("ArvoreMae")
poi = new_poi("ArvoreMae", "Árvore-mãe gigante (marco)", 3, mt, "landmark")
piece(poi, mt, mt_h - 0.5, 40, 3.0, q="Nature/TwistedTree_2", col="complex")
for q_ in range(6):
    ang = q_ / 6 * 2 * math.pi
    pp = mt + np.array([math.cos(ang), math.sin(ang)]) * 17
    piece(poi, pp, gh(pp), rng.uniform(0, 360), 1.8, q="SpaceKit/Tree_Light_1", col="none")
light(mt, mt_h + 12, [0.3, 1.0, 0.9], 30000, 45, "Brilho_ArvoreMae")
k_bar = road_k((425, -285))
L["barricades"].append({"label": "Barricada_Corpos_Z3", "loc": ue(road[k_bar], road_h[k_bar]), "yaw": yaw_of(r_tan[k_bar]),
                        "width_cm": 1500, "count": 12, "break_speed_kmh": 50,
                        "note": "acelere acima de 50 km/h para romper ou desvie pela Alt_Z3_TrilhaMae"})
story(road_pt(k_bar - 110), road_h[k_bar - 110], "Historia_Z3_Barricada",
      "Barricada de corpos à frente! Acelere com tudo ou pegue a trilha da esquerda.", "Rompa a barricada ou desvie",
      foot=False)
for i, f in enumerate((0.25, 0.55, 0.8)):
    k = int(ks3[0] + f * len(ks3))
    pickup(road_pt(k, rng.uniform(-3, 3)), road_h[k], "REPAIR" if i == 1 else "NITRO", 30 if i == 1 else 0.25, f"Pickup_Z3_{i + 1}")
dzone("DZ_Z3_Floresta", np.array(ZONES[3]["center"]), gh(ZONES[3]["center"]), (200, 300, 80), density=1.2, priority=1)

# ------------------------------------------------------------------ Z4 árvore na ponte / colmeia (a pé)
k_gate4 = road_k((436, 5))
br_c = road[K_BRC]
yaw_br = yaw_of(r_tan[K_BRC])
poi = new_poi("Ponte", "Ponte sobre a ravina", 4, br_c, "bridge")
br_len = (K_BR1 - K_BR0 + 10)
piece(poi, br_c, road_h[K_BRC] - 1.0, yaw_br, [br_len / 14.0, 2.0, 1.2], mesh="SM_BridgePlanks", col="complex")
for side in (-1, 1):
    for s in range(-int(br_len / 2) + 4, int(br_len / 2) - 3, 8):
        k = K_BRC + s
        piece(poi, road_pt(k, side * 6.4), road_h[k], yaw_of(r_tan[k]), 1.0, mesh="SM_GuardRail", col="simple")
    for s in (-14, 0, 14):
        k = K_BRC + s
        piece(poi, road_pt(k, side * 4.5), road_h[k] - 17, yaw_of(r_tan[k]), [2.0, 2.0, 4.3], q="Ruins/Column_BridgeSupport", col="simple")
L["gates"].append({"label": "Portao_ArvoreCaida_Ponte", "type": "explosive", "required_item": "Explosive",
                   "loc": ue(br_c, road_h[K_BRC]), "yaw": yaw_br, "block_extent_cm": [180, 750, 350],
                   "mesh_q": "Nature/DeadTree_5", "mesh_rel_rot": [-88, 90, 0], "mesh_scale": 1.5,
                   "mesh_rel_loc_cm": [0, -1230, 120], "horde": {"size": 30, "duration": 60},
                   "note": "E com explosivos: 4 s e explode; atrai a horda (Z5)"})
isl, _, isl_h = pad("IlhaColmeia")
poi_h = new_poi("Colmeia", "Colmeia alienígena na ilha (marco)", 4, isl, "hive")
for q_, ang in enumerate((-70, -20, 30, 80, 130)):
    a_ = math.radians(ang)
    pp = isl + np.array([math.cos(a_), math.sin(a_)]) * 11
    piece(poi_h, pp, isl_h - 1.0, ang + 180, [2.4, 2.4, 2.8 + 0.4 * (q_ % 2)], q="SpaceKit/Rock_Large_3", col="complex")
for q_ in range(5):
    ang = math.radians(rng.uniform(-80, 140))
    pp = isl + np.array([math.cos(ang), math.sin(ang)]) * rng.uniform(4, 8)
    piece(poi_h, pp, isl_h, rng.uniform(0, 360), 1.0, mesh=["SM_EggSac", "SM_SporePod", "SM_CrystalCluster"][q_ % 3], col="none")
light(isl, isl_h + 6, [0.5, 1.0, 0.2], 20000, 30, "Brilho_Colmeia")
chest(isl + np.array([3.0, 0.0]), isl_h, 180, "Bau_Colmeia", weapon="SHOTGUN", ammo=10, key_item="Explosive",
      key_label="EXPLOSIVOS", tier="rare")
# pilares do parkour (margem oeste -> ilha), zigue-zague
shore = LAKE_C + np.array([-LAKE_R, 0.0])
isl_edge = LAKE_C + np.array([-ISLAND_R, 0.0])
pk = []
n_pil = 6
for q_ in range(n_pil):
    f = (q_ + 0.5) / n_pil
    p = shore + (isl_edge - shore) * f + np.array([0.0, (2.2 if q_ % 2 else -2.2)])
    tall = q_ in (2, 4)
    top = lake_h + (0.5 if tall else 0.0)
    base = lake_h - 2.6
    hm = 2.0 if tall else 1.0
    piece(poi_h, p, base, rng.uniform(0, 90), [0.85, 0.85, round((top - base) / hm, 3)],
          mesh="SM_StonePlatformTall" if tall else "SM_StonePlatform", col="complex")
    pk.append(ue(p, top))
L["parkour"] = pk
L["hazards"].append({"label": "Lago_Toxico", "kind": "toxic_lake", "loc": ue(LAKE_C, lake_h - 1.7), "yaw": 0,
                     "box_extent_cm": [LAKE_R * 100, LAKE_R * 100, 110], "plane_loc": ue(LAKE_C, lake_h - 0.9),
                     "plane_size_m": [LAKE_R * 2 + 4, LAKE_R * 2 + 4], "instant_fail": True, "damage_per_second": 45})
# rio: cair na ravina = voltar ao checkpoint (limite natural, nunca na estrada)
for s0 in range(0, len(river) - 60, 120):
    seg = river[s0:s0 + 120]
    c = seg.mean(0)
    dv = seg[-1] - seg[0]
    L["hazards"].append({"label": f"Rio_{s0 // 120:02d}", "kind": "river", "loc": ue(c, float(bed[s0 + 60]) + 1.0),
                         "yaw": yaw_of(dv), "box_extent_cm": [float(np.linalg.norm(dv)) * 50 + 400, 900, 250],
                         "instant_fail": True, "damage_per_second": 100})
L["water"] = {"loc_z_cm": None, "river_plane_offset_m": 1.2}
mg, _, mg_h = pad("MargemLago")
pickup(mg + np.array([2, 3]), mg_h, "AMMO", 12, "Pickup_Municao_Margem")
pickup(isl + np.array([-4, 2]), isl_h, "HEALTH", 40, "Pickup_Vida_Ilha")
park4 = road_pt(k_gate4 - 8)
checkpoint("CP_Z4_Ponte", "Z4_Bridge", road_pt(k_gate4), road_h[k_gate4], yaw_of(r_tan[k_gate4]), "ON_FOOT",
           weapons=("melee", "pistol"), keys=("CarKey",), transition=True, park=(park4, road_h[k_gate4 - 8], yaw_of(r_tan[k_gate4])))
story(road_pt(k_gate4 + 3), road_h[k_gate4], "Historia_Z4_Arvore",
      "Uma árvore caiu na ponte! Explosivos? Talvez na colmeia, além do lago.", "Pegue os explosivos na colmeia",
      extent=(1500, 1500, 600))
story(mg, mg_h, "Historia_Z4_Lago", "Lago tóxico! Pule de pedra em pedra [ESPAÇO].", "Atravesse pelos pilares",
      extent=(1000, 1000, 600))
dzone("DZ_Z4_Colmeia", isl, isl_h, (60, 60, 30), density=0.6, priority=6)
dzone("DZ_Z4_Ponte", road[k_gate4], road_h[k_gate4], (120, 120, 40), density=1.3, priority=4)
for q_ in range(3):
    enemy(mg + rng.uniform(-14, 14, 2) + np.array([-12, 10]), "melee", f"ENM_Z4_{q_ + 1}")

# ------------------------------------------------------------------ Z5 fuga da horda (carro)
ks5 = np.where(road_zone == 5)[0]
k5 = int(K_BR1 + 35)
checkpoint("CP_Z5_Fuga", "Z5_Escape", road_pt(k5), road_h[k5], yaw_of(r_tan[k5]), "DRIVING",
           weapons=("melee", "pistol", "shotgun"), keys=("CarKey",))
story(road_pt(K_BR1 + 15), road_h[K_BR1 + 15], "Historia_Z5_Fuga", "A explosão atraiu a horda! Fuja para a vila!",
      "Fuja para a vila (noroeste)", foot=False)
for side in (-1, 1):
    light(road_pt(K_BRC + side * 12, side * 3), road_h[K_BRC] + 1.5, [1.0, 0.45, 0.1], 18000, 20, f"Fogo_Ponte_{side + 2}")
L["horde_hint"] = {"z5_from": ue(road[K_BRC], road_h[K_BRC]), "note": "a horda do portão nasce perto da ponte"}
for i, f in enumerate((0.2, 0.45, 0.7, 0.9)):
    k = int(ks5[0] + f * len(ks5))
    pickup(road_pt(k, rng.uniform(-3, 3)), road_h[k], "NITRO" if i % 2 == 0 else "REPAIR", 0.3 if i % 2 == 0 else 25, f"Pickup_Z5_{i + 1}")
    for j in range(3):
        enemy(road_pt(k + 10 + j * 3, rng.uniform(-6, 6)), "melee", f"ENM_Z5_G{i + 1}_{j + 1}", z=road_h[k])
dzone("DZ_Z5_Fuga", np.array(ZONES[5]["center"]), gh(ZONES[5]["center"]), (320, 200, 80), density=1.4, priority=1)

# ------------------------------------------------------------------ Z6 vila / disco voador (a pé)
vil, vil_r, vil_h = pad("Vila")
k_gate6 = road_k((-272, 575))
poi = new_poi("Vila", "Vila da sobrevivente", 6, vil, "village")
houses = []
for q_, (ang, rr_) in enumerate([(10, 34), (65, 38), (120, 33), (175, 36), (230, 32), (290, 37)]):
    a_ = math.radians(ang)
    p = vil + np.array([math.cos(a_), math.sin(a_)]) * rr_
    houses.append(p)
    m = ["SM_Ruin_House", "SpaceKit/House_Long", "SM_Ruin_House", "SpaceKit/House_Cylinder", "SM_Ruin_House", "SM_FarmhouseRuin"][q_]
    if m.startswith("SM_"):
        piece(poi, p, vil_h, ang + 90, 1.0, mesh=m, col="complex")
    else:
        piece(poi, p, vil_h, ang + 90, 1.0, q=m, col="complex")
piece(poi, vil + np.array([-6, -10]), vil_h, 0, 1.0, q="ZombieKit/WaterTower", col="simple")
for q_ in range(14):
    ang = q_ / 14 * 2 * math.pi
    p = vil + np.array([math.cos(ang), math.sin(ang)]) * (vil_r - 4)
    if np.linalg.norm(p - np.array([-350, 625])) < 16:     # entrada da trilha
        continue
    piece(poi, p, gh(p), math.degrees(ang) + 90, 1.0, mesh="SM_Fence" if q_ % 3 else "SM_Barricade", col="simple")
for q_ in range(8):
    p = vil + rng.uniform(-20, 20, 2)
    piece(poi, p, vil_h, rng.uniform(0, 360), 1.0, q=["ZombieKit/Barrel", "ZombieKit/Pallet", "ZombieKit/TrashBag_1",
                                                       "SpaceKit/Pickup_Crate"][q_ % 4], cull=300)
ufo, _, ufo_h = pad("DiscoVoador")
poi_u = new_poi("DiscoVoador", "Disco voador enterrado (marco)", 6, ufo, "landmark")
piece(poi_u, ufo, ufo_h - 2.2, 25, 1.5, mesh="SM_UFOWreck", pitch=8, roll=-12, col="complex")
for q_ in range(4):
    ang = math.radians(200 + q_ * 40)
    pp = ufo + np.array([math.cos(ang), math.sin(ang)]) * 24
    piece(poi_u, pp, gh(pp), rng.uniform(0, 360), 1.1, mesh="SM_AlienMonolith", col="simple")
light(ufo, ufo_h + 6, [0.6, 0.3, 1.0], 25000, 40, "Brilho_Disco")
# portão trancado (o carro não entra na vila; a pé passa pelo vão)
tr6 = [p for nm, z, p in trails if nm == "Trilha_Z6"][0]
k_ent = int(np.argmin(np.abs(np.linalg.norm(tr6 - vil, axis=1) - (vil_r - 4))))
gate6_c = tr6[k_ent]
gdir = tr6[min(k_ent + 3, len(tr6) - 1)] - tr6[max(k_ent - 3, 0)]
gdir /= np.linalg.norm(gdir)
L["gates"].append({"label": "Portao_Vila", "type": "car_block", "required_item": "", "loc": ue(gate6_c, gh(gate6_c)),
                   "yaw": yaw_of(gdir), "pieces_q": "ZombieKit/TrafficBarrier_1", "offsets_m": [-3.4, -1.7, 1.7, 3.4],
                   "note": "barreiras com vão de 1,6 m na entrada da vila: a pé passa, o carro fica (portão trancado)"})
cage_p = ufo + np.array([22.0, -16.0])
L["rescue"] = {"loc": ue(cage_p, gh(cage_p)), "yaw": yaw_of(vil - cage_p), "complete_level_on_rescue": False}
hring = []
for s in range(6):
    ang = s / 6 * 2 * math.pi + 0.4
    p = vil + np.array([math.cos(ang), math.sin(ang)]) * (vil_r + 22)
    hring.append(ue(p, gh(p) + 1))
L["horde"] = {"loc": ue(vil, vil_h), "trigger_extent_cm": [2600, 2600, 600], "spawn_points": hring,
              "waves": [["melee", 6, 0.9], ["melee", 8, 0.6], ["gunner", 3, 1.5], ["melee", 10, 0.5]],
              "note": "defesa de ~60 a 90 s na vila; no fim abre o resgate (estágio Rescue)"}
for i, (dx, dy) in enumerate(((8, 6), (-10, 4), (4, -12))):
    pickup(vil + np.array([dx, dy]), vil_h, "AMMO", 15, f"Pickup_Municao_Vila_{i + 1}")
pickup(vil + np.array([0, 12]), vil_h, "HEALTH", 40, "Pickup_Vida_Vila_1")
pickup(houses[2], vil_h, "FURY", 12, "Pickup_Furia_Vila")
chest(houses[0], vil_h, 0, "Bau_Vila_Municao", ammo=24, health=30, tier="common")
for q_ in range(5):
    enemy(vil + rng.uniform(-25, 25, 2), "melee" if q_ < 4 else "gunner", f"ENM_Z6_{q_ + 1}")
park6 = road_pt(k_gate6 - 6)
checkpoint("CP_Z6_Vila", "Z6_Village", road_pt(k_gate6), road_h[k_gate6], yaw_of(r_tan[k_gate6]), "ON_FOOT",
           weapons=("melee", "pistol", "shotgun"), keys=("CarKey",), transition=True,
           park=(park6, road_h[k_gate6 - 6], yaw_of(r_tan[k_gate6])))
story(road_pt(k_gate6 + 3), road_h[k_gate6], "Historia_Z6_Vila", "A vila da sobrevivente. Limpe a área e ache a moça.",
      "Encontre a sobrevivente", extent=(1400, 1400, 600))
story(cage_p + np.array([-6, 6]), gh(cage_p), "Historia_Z6_Saida", "Depois de soltá-la, voltem ao buggy e saiam pelo portão norte.",
      "Solte a sobrevivente [E]", extent=(900, 900, 600))
dzone("DZ_Z6_Vila", vil, vil_h, (110, 110, 40), density=1.5, priority=5)

# ------------------------------------------------------------------ Z7 saída (carro)
ks7 = np.where(road_zone == 7)[0]
ex, _, ex_h = pad("PortaoNorte")
k_ex = road_k(ex)
poi = new_poi("PortaoNorte", "Portão norte (saída)", 7, road[k_ex], "exit_gate")
piece(poi, road[k_ex], road_h[k_ex] - 0.4, yaw_of(r_tan[k_ex]) + 90, 5.0, q="Ruins/Wall_ArchRound_Overgrown", col="complex")
piece(poi, road_pt(k_ex - 25, 10), road_h[k_ex - 25], yaw_of(r_tan[k_ex]) + 90, 1.4, q="ZombieKit/TownSign", col="simple")
story(road_pt(k_ex + 8), road_h[k_ex + 8], "Historia_Z7_Fim", "Vocês saíram do vale. Resgate concluído!", "",
      foot=False, extent=(1200, 1200, 800), completes=True)
for i, f in enumerate((0.3, 0.65)):
    k = int(ks7[0] + f * len(ks7))
    pickup(road_pt(k, rng.uniform(-3, 3)), road_h[k], "NITRO", 0.3, f"Pickup_Z7_{i + 1}")
dzone("DZ_Z7_Saida", road[k_ex], road_h[k_ex], (60, 60, 40), no_spawns=True, priority=8)
# [A-075] checkpoint da zona 7: logo depois de sair da vila, já no carro com a sobrevivente (morrer na reta final
# não volta para a vila). Sem rng aqui: o resto do layout não muda.
k7cp = int(ks7[0] + 0.12 * len(ks7))
checkpoint("CP_Z7_Saida", "Z7_Exit", road_pt(k7cp), road_h[k7cp], yaw_of(r_tan[k7cp]), "DRIVING",
           weapons=("melee", "pistol", "shotgun"), keys=("CarKey",))

# ------------------------------------------------------------------ saltos (rampa + vala rasa + aterrissagem)
L["jumps"] = []
for j in JUMPS:
    yaw = yaw_of(j["t"])
    L["jumps"].append({"route": j["route"], "ramp": {"loc": ue(j["p"] - j["t"] * 3.5, j["h"] + 0.0), "yaw": yaw},
                       "landing": {"loc": ue(j["p"] + j["t"] * (GAP + 4.5), j["h"] + 0.0), "yaw": yaw},
                       "gap_m": GAP, "min_speed_kmh": 45, "note": "vala de 1,9 m com saída pelos lados (sem morte)"})
    pickup(j["p"] - j["t"] * 50, j["h"], "NITRO", 0.35, f"Pickup_NitroSalto_{j['route']}")

# ------------------------------------------------------------------ paredes invisíveis (só na borda)
for i, (cx, cy, yaw) in enumerate(((0, EDGE_WALL, 0), (0, -EDGE_WALL, 0), (EDGE_WALL, 0, 90), (-EDGE_WALL, 0, 90))):
    L["walls"].append({"loc": ue((cx, cy), -50), "yaw": yaw, "len_cm": 2 * EDGE_WALL * 100 + 400, "h_cm": 60000})

# ------------------------------------------------------------------ navegação: uma caixa por zona
L["nav_bounds"] = []
for zd in ZONES:
    pts = [np.array(zd["center"]) + np.array([dx, dy]) * zd["radius"] for dx in (-1, 1) for dy in (-1, 1)]
    ks = np.where(road_zone == zd["id"])[0]
    if len(ks):
        pts += list(road[ks[::10]])
    for nm, z, p, _ in alts:
        if z == zd["id"]:
            pts += list(p[::10])
    pts = np.array(pts)
    mn, mx = pts.min(0) - 60, pts.max(0) + 60
    hz = sample(H2, pts)
    L["nav_bounds"].append({"zone": zd["id"], "center": ue((mn + mx) / 2, float(np.mean(hz))),
                            "size_cm": [float(mx[0] - mn[0]) * 100, float(mx[1] - mn[1]) * 100,
                                        float(hz.max() - hz.min() + 80) * 100]})

# ------------------------------------------------------------------ dicas de vegetação (agente Densidade)
VEG_PALETTE = {
    "forest": ["SpaceKit/Tree_Blob_1", "SpaceKit/Tree_Swirl_1", "SpaceKit/Tree_Spiral_1", "SpaceKit/Tree_Light_1",
               "Nature/TwistedTree_1", "Nature/Fern_1", "SpaceKit/Plant_1", "Nature/Mushroom_Laetiporus"],
    "sparse": ["Nature/DeadTree_1", "Nature/Bush_Common", "SpaceKit/Bush_1", "Nature/Grass_Wispy_Short",
               "Nature/Rock_Medium_1", "SpaceKit/Plant_2"],
    "desert": ["SpaceKit/Rock_1", "SpaceKit/Rock_Large_1", "Nature/DeadTree_3", "SpaceKit/Plant_3", "SpaceKit/Grass_2"],
}
for zd in ZONES:
    L["veg_hints"].append({"zone": zd["id"], "key": zd["key"], "type": zd["veg"],
                           "density": {"forest": 0.85, "sparse": 0.35, "desert": 0.15}[zd["veg"]],
                           "palette": VEG_PALETTE[zd["veg"]]})
L["veg_rules"] = {"keep_clear_m": {"main_road": 9, "dirt_routes": 6, "trails": 3, "pads": "raio + 4", "river": 24,
                                   "lake": LAKE_R + 4, "jumps": 30},
                  "max_slope_trees": 0.6, "density_png": "l01_veg_density_v3.png",
                  "png_mapping": "R floresta, G esparso, B deserto (0-255); pixel (0,0) = noroeste; 1 px = 4 m",
                  "edge_forest_m": "cinturão denso 120-260 m das rotas (limite natural)"}
dens = np.zeros((N, N, 3))
veg_road = np.array([{"forest": (1, 0, 0), "sparse": (0, 1, 0), "desert": (0, 0, 1)}[ZONES[z]["veg"]] for z in road_zone], float)
for c in range(3):
    veg_road[:, c] = smooth1(veg_road[:, c], 60)
vr = veg_road[i_road]
for zd in ZONES:
    if zd["mode"] == "foot":
        dz = np.linalg.norm(P - np.array(zd["center"]), axis=1)
        w = (1 - sstep(zd["radius"], zd["radius"] * 1.8, dz))[:, None]
        vr = vr * (1 - w) + np.array({"forest": (1, 0, 0), "sparse": (0, 1, 0), "desert": (0, 0, 1)}[zd["veg"]])[None] * w
vr = np.stack([blur_grid(vr[:, c].reshape(N, N), 10).ravel() for c in range(3)], 1)
amount = np.array([0.85, 0.35, 0.15])[None] * vr
belt = sstep(60, 140, d_net) * (1 - sstep(220, 320, d_net))       # cinturão de mata densa (limite suave)
amount[:, 0] = np.maximum(amount[:, 0], belt * 0.8 * (Hf - floor < 45))
clear = np.ones(len(P))
clear *= sstep(ROAD_HALF + 3, ROAD_HALF + 9, d_road)
clear *= sstep(4.0, 7.0, d_alt_all)
for d_, _ in D_TR:
    clear *= sstep(2.0, 4.0, d_)
for (c, r, nm) in PADS:
    clear *= sstep(r, r + 6, np.linalg.norm(P - np.array(c), axis=1))
clear *= sstep(22, 28, d_riv) * sstep(LAKE_R + 2, LAKE_R + 6, dl)
for j in JUMPS:
    clear *= sstep(25, 35, np.linalg.norm(P - j["p"], axis=1))
clear *= (slope.ravel() < 0.6)
dens = np.clip(amount * clear[:, None], 0, 1).reshape(N, N, 3)
# o PNG é gravado por tools/blender/plot_l01_v3.py (o Python do Blender não tem PIL)

# ------------------------------------------------------------------ conferências
L["checks"] = [ue((x, y), gh((x, y))) for (x, y) in [(-400, -600), (300, -500), (-300, 400), (600, 200), (0, 0), (-700, -770)]]
L["stats"] = {"road_m": NR, "road_min_radius_m": round(float(r_rad[20:-20].min())),
              "road_max_grade": round(float(np.abs(np.diff(road_h)).max()), 3),
              "drive_m_per_zone": {str(z): int((road_zone == z).sum()) for z in range(8)},
              "bridge_m": [K_BR0, K_BR1], "alt_routes_m": {nm: len(p) for nm, z, p, _ in alts}}
json.dump(L, open(os.path.join(OUT, "l01_layout_v3.json"), "w", encoding="utf-8"), indent=1, ensure_ascii=False)
extra = {f"alt_{i}": p for i, (_, _, p, _) in enumerate(alts)}
extra.update({f"trail_{i}": p for i, (_, _, p) in enumerate(trails)})
np.savez_compressed(os.path.join(OUT, "l01_preview_v3.npz"), col=prev, H=H2, road=road, river=river, veg=dens,
                    road_zone=road_zone, **extra)
print("stats", json.dumps(L["stats"], ensure_ascii=False))
print("terreno min/max", round(float(H2.min()), 1), round(float(H2.max()), 1))
print("ok")
