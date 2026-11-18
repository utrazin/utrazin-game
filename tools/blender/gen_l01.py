"""Gera a Fase 1 v2 "Vale Alienígena" (2 x 2 km): terreno com biomas, estrada com eventos, trilha a pé,
corredor guiado (morros + paredes invisíveis) e o layout de tudo (posições em cm, Unreal).

Uso: bpy52 python gen_l01.py -- <pasta_saida>
Saídas: L01_Terrain.fbx (64 pedaços + estrada), l01_layout.json, l01_preview.npz (minimapa/prévia)
Coordenadas Blender: X leste, Y norte, Z cima (metros). Unreal: x = X*100, y = -Y*100, z = Z*100.

Cor por vértice do TERRENO = máscaras de bioma (lidas pelo material M_L01_Terrain):
  R = areia vermelha, G = grama alien, B = terra; o resto (1-R-G-B) = musgo alien. Rocha = pela inclinação (no material).
Cor por vértice da ESTRADA = tom (multiplica a textura de cascalho/asfalto em M_L01_Road).
Roteiro: docs/gameplay/L01_STORYBOARD.md
"""
import json
import math
import os
import sys

import numpy as np

OUT = sys.argv[-1]
os.makedirs(OUT, exist_ok=True)
HALF = 1000.0      # mapa de -1000 a 1000 m
STEP = 4.0         # grade do terreno (m)
N = int(2 * HALF / STEP) + 1  # 501
CH = 8             # 8 x 8 pedaços de 250 m
CAR_CORRIDOR = 45.0    # folga do carro em volta da estrada (m)
FOOT_CORRIDOR = 25.0   # folga a pé em volta da trilha (m)
CAR_WALL = 70.0        # parede invisível (m da estrada)
FOOT_WALL = 32.0       # parede invisível (m da trilha)

# ------------------------------------------------------------------ rotas (m, Blender): mesmas da v1
ROAD_CTRL = [(-430, -330), (-480, -210), (-380, -130), (-240, -190), (-110, -250), (10, -190), (60, -60),
             (10, 60), (70, 170), (170, 230)]
TRAIL_CTRL = [(170, 230), (215, 280), (250, 360), (225, 440), (260, 520), (340, 560),
              (430, 575), (500, 640), (520, 730), (590, 790), (640, 840)]
SHIFT = (-80.0, -250.0)
ROAD_CTRL = [(x + SHIFT[0], y + SHIFT[1]) for x, y in ROAD_CTRL]
TRAIL_CTRL = [(x + SHIFT[0], y + SHIFT[1]) for x, y in TRAIL_CTRL]


def catmull(ctrl, step=1.0):
    p = np.array(ctrl, float)
    p = np.vstack([p[0] * 2 - p[1], p, p[-1] * 2 - p[-2]])
    pts = []
    for i in range(1, len(p) - 2):
        p0, p1, p2, p3 = p[i - 1], p[i], p[i + 1], p[i + 2]
        seg = np.linalg.norm(p2 - p1)
        n = max(2, int(seg / step * 1.5))
        for t in np.linspace(0, 1, n, endpoint=False):
            t2, t3 = t * t, t * t * t
            pts.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    pts.append(p[-2])
    pts = np.array(pts)
    d = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(pts, axis=0), axis=1))])
    s = np.arange(0, d[-1], step)
    return np.stack([np.interp(s, d, pts[:, 0]), np.interp(s, d, pts[:, 1])], 1), d[-1]


road, road_len = catmull(ROAD_CTRL)
trail, trail_len = catmull(TRAIL_CTRL)
NR, NT = len(road), len(trail)
print(f"estrada {road_len:.0f} m, trilha {trail_len:.0f} m")


def tangents(poly):
    t = np.gradient(poly, axis=0)
    t /= np.linalg.norm(t, axis=1)[:, None]
    return t, np.stack([-t[:, 1], t[:, 0]], 1)


r_tan, r_nrm = tangents(road)
t_tan, t_nrm = tangents(trail)


# ------------------------------------------------------------------ ruído
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


xs = np.linspace(-HALF, HALF, N)
X, Y = np.meshgrid(xs, xs, indexing="ij")
H = value_noise(420, 24, 1) + value_noise(160, 9, 2) + value_noise(60, 2.5, 3) + value_noise(22, 0.6, 4)
edge = np.maximum(np.abs(X), np.abs(Y))
rim = np.clip((edge - 780) / 200, 0, 1)
rim = rim * rim * (3 - 2 * rim)
H += rim * (95 + value_noise(90, 25, 5))


def sample(Hg, pts):
    pts = np.atleast_2d(pts)
    fi = (pts[:, 0] + HALF) / STEP
    fj = (pts[:, 1] + HALF) / STEP
    i0 = np.clip(np.floor(fi).astype(int), 0, N - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, N - 2)
    tx, ty = fi - i0, fj - j0
    return (Hg[i0, j0] * (1 - tx) * (1 - ty) + Hg[i0 + 1, j0] * tx * (1 - ty)
            + Hg[i0, j0 + 1] * (1 - tx) * ty + Hg[i0 + 1, j0 + 1] * tx * ty)


def smooth(v, sigma):
    k = np.arange(-3 * sigma, 3 * sigma + 1)
    w = np.exp(-0.5 * (k / sigma) ** 2)
    w /= w.sum()
    pad = np.pad(v, (len(k) // 2, len(k) // 2), mode="edge")
    return np.convolve(pad, w, mode="valid")


def limit_slope(v, max_slope, step=1.0):
    for _ in range(4):
        for i in range(1, len(v)):
            v[i] = np.clip(v[i], v[i - 1] - max_slope * step, v[i - 1] + max_slope * step)
        for i in range(len(v) - 2, -1, -1):
            v[i] = np.clip(v[i], v[i + 1] - max_slope * step, v[i + 1] + max_slope * step)
    return v


def curvature(poly, win=12):
    t, _ = tangents(poly)
    a = np.unwrap(np.arctan2(t[:, 1], t[:, 0]))
    c = np.zeros(len(poly))
    c[win:-win] = np.abs(a[2 * win:] - a[:-2 * win]) / (2 * win)
    c[:win] = c[win]
    c[-win:] = c[-win - 1]
    return c


r_curv = curvature(road)


def straight_near(target, span=60):
    """Índice da estrada perto de `target` (m) onde a curva é mais suave (para saltos)."""
    lo, hi = max(30, target - span), min(NR - 40, target + span)
    win = np.array([r_curv[max(0, k - 25):k + 25].max() for k in range(lo, hi)])
    return int(lo + np.argmin(win + np.abs(np.arange(lo, hi) - target) * 0.0004))


# ------------------------------------------------------------------ eventos da estrada (índice = metro)
K_BUMPS = (int(NR * 0.19), int(NR * 0.25))           # lombadas no cânion
K_JUMP1 = straight_near(int(NR * 0.37))               # início do buraco 1
GAP1 = 10.0
K_JUMP2 = straight_near(int(NR * 0.82))               # início da ravina 2
GAP2 = 13.0
CANYON = (int(NR * 0.13), int(NR * 0.34))
FOREST = (int(NR * 0.42), int(NR * 0.80))
print("salto1", K_JUMP1, "salto2", K_JUMP2, "curvas", round(float(r_curv[K_JUMP1]), 4), round(float(r_curv[K_JUMP2]), 4))

road_h = limit_slope(smooth(sample(H, road), 45), 0.11)
# lombadas: ondas de 16 m, 0,7 m de altura (o carro decola um pouco)
kk = np.arange(NR)
bump = (kk >= K_BUMPS[0]) & (kk < K_BUMPS[1])
road_h = road_h + np.where(bump, 0.7 * np.sin((kk - K_BUMPS[0]) / 16.0 * math.pi) ** 2, 0.0)
# trechos dos saltos: perfil reto (sem lombada nem curva vertical)
for kj, gap in ((K_JUMP1, GAP1), (K_JUMP2, GAP2)):
    a0, a1 = kj - 40, int(kj + gap + 40)
    road_h[a0:a1] = np.linspace(road_h[a0], road_h[a1], a1 - a0)

trail_h = limit_slope(smooth(sample(H, trail), 20), 0.16)
trail_h += road_h[-1] - trail_h[0]
trail_h = limit_slope(trail_h, 0.16)

# ------------------------------------------------------------------ áreas planas e pontos a pé
PLAZA = (road[-1], road_h[-1], 28.0)
ARENA_C = trail[-1] + (trail[-1] - trail[-15]) / np.linalg.norm(trail[-1] - trail[-15]) * 18
ARENA = (ARENA_C, trail_h[-1], 30.0)
VILLAGES = []
for frac in (0.20, 0.58, 0.84):
    k = int(frac * (NT - 1))
    VILLAGES.append((trail[k], trail_h[k], 26.0))
FLATS = [PLAZA, ARENA] + VILLAGES
K_POND = int(0.38 * (NT - 1))                 # lago tóxico (parkour) entre a vila 1 e a 2
POND_C, POND_H = trail[K_POND], trail_h[K_POND]
POND_ALONG, POND_SIDE = 13.0, 42.0            # meio comprimento ao longo da trilha / para os lados

# ------------------------------------------------------------------ escavação
P = np.stack([X.ravel(), Y.ravel()], 1)
Hf = H.ravel().copy()


def nearest(points, poly):
    best_d = np.full(len(points), 1e9)
    best_i = np.zeros(len(points), int)
    sub = poly[::3]
    for k0 in range(0, len(sub), 64):
        blk = sub[k0:k0 + 64]
        d = np.linalg.norm(points[:, None, :] - blk[None, :, :], axis=2)
        i = np.argmin(d, 1)
        dd = d[np.arange(len(points)), i]
        m = dd < best_d
        best_d[m] = dd[m]
        best_i[m] = (k0 + i[m]) * 3
    return best_d, np.clip(best_i, 0, len(poly) - 1)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


rd, ri = nearest(P, road)
td, ti = nearest(P, trail)
flat_d = np.min([np.linalg.norm(P - np.array(c)[None, :], axis=1) - r for (c, h, r) in FLATS], axis=0)

# corredor: fora dele o terreno sobe (morros/paredões): não é mapa aberto
corr = np.minimum(np.minimum(rd - CAR_CORRIDOR, td - FOOT_CORRIDOR), flat_d - 20)
hills = value_noise(70, 1.0, 11).ravel() * 0.5 + 0.5
rise_car = sstep(0, 55, rd - CAR_CORRIDOR) * (26 + 22 * hills)
rise_foot = sstep(0, 22, td - FOOT_CORRIDOR) * (14 + 10 * hills)
rise = np.minimum(np.where(rd - CAR_CORRIDOR > 0, rise_car, 0), np.where(td - FOOT_CORRIDOR > 0, rise_foot + sstep(0, 60, td - FOOT_CORRIDOR) * 18, 0))
rise = np.where(flat_d < 20, 0, rise) * sstep(-5, 15, flat_d)
Hf = Hf + rise

w_road = 1 - sstep(6.5, 28, rd)
Hf = Hf * (1 - w_road) + (road_h[ri] - 0.35) * w_road
w_tr = 1 - sstep(3.0, 14, td)
Hf = Hf * (1 - w_tr) + (trail_h[ti] - 0.05) * w_tr
for (c, h, r) in FLATS:
    dist = np.linalg.norm(P - np.array(c)[None, :], axis=1)
    w = 1 - sstep(r, r + 22, dist)
    Hf = Hf * (1 - w) + (h - 0.05) * w

# acostamento plano nos saltos (a ponte da ravina 2 fica a 16 m da estrada)
for kj, gap in ((K_JUMP1, GAP1), (K_JUMP2, GAP2)):
    m = (ri > kj - 30) & (ri < kj + gap + 30) & (rd < 26)
    Hf = np.where(m, road_h[ri] - 0.35, Hf)

# buracos/ravinas dos saltos: atravessam o corredor inteiro (não dá para contornar)
GAPS = []
for kj, gap in ((K_JUMP1, GAP1), (K_JUMP2, GAP2)):
    c = road[kj] + r_tan[kj] * gap / 2
    t, n = r_tan[kj], r_nrm[kj]
    s = (P - c) @ t
    l = (P - c) @ n
    inside = (np.abs(s) < gap / 2) & (np.abs(l) < CAR_WALL + 8)
    bottom = road_h[kj] - 11 + value_noise(9, 0.8, 21).ravel()
    Hf = np.where(inside, np.minimum(Hf, bottom), Hf)
    GAPS.append({"k": kj, "gap": gap, "c": c, "t": t, "n": n, "h": float(road_h[kj])})

# lago tóxico do parkour (elipse cruzando a trilha; as pontas entram nas paredes)
pt, pn = t_tan[K_POND], t_nrm[K_POND]
ps = (P - POND_C) @ pt
pl = (P - POND_C) @ pn
pond_e = (ps / POND_ALONG) ** 2 + (pl / POND_SIDE) ** 2
Hf = np.where(pond_e < 1.0, np.minimum(Hf, POND_H - 2.2), Hf)
Hf = np.where((pond_e >= 1.0) & (pond_e < 1.25), np.minimum(Hf, POND_H - 0.1), Hf)
H2 = Hf.reshape(N, N)

# ------------------------------------------------------------------ máscaras de bioma
gx, gy = np.gradient(H2, STEP)
slope = np.sqrt(gx ** 2 + gy ** 2)
rd2, td2, ri2 = rd.reshape(N, N), td.reshape(N, N), ri.reshape(N, N)
nz = value_noise(55, 1, 31)
# progresso: 0 na largada, 1 no fim da estrada; a pé conta como floresta
prog = ri2 / (NR - 1)
on_foot_zone = td2 < rd2
desert = 1 - sstep(0.28, 0.42, prog + nz * 0.08 + value_noise(240, 0.12, 33))
desert = np.where(on_foot_zone, 0.0, desert)
R = np.clip(desert * (0.85 + 0.15 * nz), 0, 1)
G = np.clip((1 - R) * (0.55 + 0.35 * value_noise(30, 1, 32)), 0, 1)
B = np.zeros_like(R)
B = np.maximum(B, 1 - sstep(8.0, 13.0, rd2))       # terra nas bordas da estrada
B = np.maximum(B, 1 - sstep(2.5, 6.5, td2))        # trilha de terra
for (c, h, r) in VILLAGES:
    dist = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2)
    B = np.maximum(B, (1 - sstep(r * 0.5, r * 0.9, dist)) * (0.7 + 0.3 * nz))
R = R * (1 - B)
G = G * (1 - B)
mask = np.stack([R, G, B], -1)
for (c, h, r) in [PLAZA, ARENA]:
    dist = np.sqrt((X - c[0]) ** 2 + (Y - c[1]) ** 2)
    mask = np.where((dist < r * 0.85)[..., None], np.array([0.0, 0.0, 1.0]), mask)

# cores médias das texturas (só para a prévia/minimapa)
TEX_RGB = {"red": (0.70, 0.31, 0.15), "grass": (0.21, 0.46, 0.54), "dirt": (0.54, 0.37, 0.22),
           "moss": (0.39, 0.23, 0.51), "rock": (0.39, 0.37, 0.45), "toxic": (0.43, 0.8, 0.15)}
rest = np.clip(1 - mask.sum(-1), 0, 1)[..., None]
prev = (mask[..., :1] * TEX_RGB["red"] + mask[..., 1:2] * TEX_RGB["grass"] + mask[..., 2:3] * TEX_RGB["dirt"]
        + rest * TEX_RGB["moss"])
rk = sstep(0.55, 0.85, slope)[..., None]
prev = prev * (1 - rk) + np.array(TEX_RGB["rock"]) * rk
prev = np.where((pond_e.reshape(N, N) < 1.0)[..., None], np.array(TEX_RGB["toxic"]), prev)

# ------------------------------------------------------------------ estrada (malha própria, com os vãos)
POTHOLES = [int(NR * f) for f in (0.10, 0.29, 0.52, 0.66, 0.74)]
CROSS = np.array([-6, -4.5, -3, -1.5, 0, 1.5, 3, 4.5, 6])
gap_idx = np.zeros(NR, bool)
for g in GAPS:
    gap_idx[g["k"]:int(g["k"] + g["gap"]) + 1] = True
road_v, road_c = [], []
for k in range(NR):
    for o in CROSS:
        p = road[k] + r_nrm[k] * o
        z = road_h[k] + 0.06 - 0.004 * o * o
        tone = 0.95 + 0.05 * math.sin(k * 0.37 + o)
        c = (tone, tone, tone) if abs(o) < 5 else (0.80, 0.72, 0.62)
        for ph in POTHOLES:
            dd = math.hypot(k - ph, o - (1.5 if ph % 2 else -1.5))
            if dd < 2.2:
                z -= 0.28 * (1 - dd / 2.2)
                c = (0.55, 0.5, 0.45)
        road_v.append((p[0], p[1], z))
        road_c.append(c)
road_v = np.array(road_v)

# ------------------------------------------------------------------ Blender
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
    # sem isto o FBX pode sair sem cor (a v1 ficava branca na Unreal)
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
        cols = mask[ii, jj].reshape(-1, 3)
        faces = []
        for u in range(ni - 1):
            for v in range(nj - 1):
                q = u * nj + v
                faces.append((q, q + nj, q + nj + 1, q + 1))
        make_obj(f"SM_L01_Terrain_{a}_{b}", verts, faces, cols, mat_t)

nc = len(CROSS)
runs, cur = [], []
for k in range(NR):
    if gap_idx[k]:
        if cur:
            runs.append(cur)
        cur = []
    else:
        cur.append(k)
if cur:
    runs.append(cur)
seg_id = 0
for run in runs:
    for s0 in range(0, len(run) - 1, 200):
        ks = run[s0:min(len(run), s0 + 201)]
        if len(ks) < 2:
            continue
        verts = np.concatenate([road_v[k * nc:(k + 1) * nc] for k in ks])
        cols = sum([road_c[k * nc:(k + 1) * nc] for k in ks], [])
        faces = []
        for k in range(len(ks) - 1):
            for o in range(nc - 1):
                q = k * nc + o
                faces.append((q, q + 1, q + nc + 1, q + nc))
        make_obj(f"SM_L01_Road_{seg_id:02d}", verts, faces, cols, mat_r)
        seg_id += 1

for ob in bpy.context.scene.objects:
    ob.select_set(True)
bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, "L01_Terrain.fbx"), use_selection=True, object_types={"MESH"},
                         apply_unit_scale=True, mesh_smooth_type="FACE", colors_type="LINEAR")
print("fbx ok", len(bpy.context.scene.objects), "objetos")

# ------------------------------------------------------------------ layout (cm, Unreal)
rng = np.random.default_rng(7)


def ue(p, z):
    return [round(float(p[0]) * 100, 1), round(-float(p[1]) * 100, 1), round(float(z) * 100, 1)]


def yaw_of(d):
    return round(math.degrees(math.atan2(-d[1], d[0])), 1)


def ground_h(p):
    return float(sample(H2, np.array([p]))[0])


L = {"version": 2, "map_half_cm": HALF * 100, "road_length_m": round(road_len), "trail_length_m": round(trail_len),
     "kill_z_cm": round((H2.min() - 60) * 100), "props": [], "enemies": [], "horde_points": [], "actors": [],
     "walls": []}


def add_prop(mesh, p, z, yaw=None, scale=1.0, cull=0, nocol=False):
    sc = [round(float(s), 2) for s in scale] if isinstance(scale, (list, tuple)) else round(float(scale), 2)
    L["props"].append({"mesh": mesh, "loc": ue(p, z), "yaw": float(rng.uniform(0, 360) if yaw is None else yaw),
                       "scale": sc, "cull_m": cull, "nocol": bool(nocol)})


def add_actor(cls, p, z, yaw=0.0, label=None, **props):
    L["actors"].append({"cls": cls, "loc": ue(p, z), "yaw": float(yaw), "label": label, "props": props})


def road_pt(k, o=0.0):
    k = int(np.clip(k, 0, NR - 1))
    return road[k] + r_nrm[k] * o


def trail_pt(k, o=0.0):
    k = int(np.clip(k, 0, NT - 1))
    return trail[k] + t_nrm[k] * o


d0 = road[8] - road[0]
L["start"] = {"loc": ue(road[0], road_h[0] + 1.2), "yaw": yaw_of(d0)}
L["cp_start"] = {"loc": ue(road[0], road_h[0]), "yaw": yaw_of(d0)}
L["cp_transition"] = {"loc": ue(PLAZA[0], PLAZA[1]), "yaw": yaw_of(trail[10] - trail[0])}
L["arena"] = {"loc": ue(ARENA[0], ARENA[1]), "radius_cm": ARENA[2] * 100}
L["road_samples"] = [ue(road[k], road_h[k]) for k in range(0, NR, 50)]
L["trail_samples"] = [ue(trail[k], trail_h[k]) for k in range(0, NT, 25)]
L["checks"] = [ue((x, y), ground_h((x, y))) for (x, y) in [(-400, -600), (300, -500), (-300, 400), (600, 200), (0, 0)]]
L["events_m"] = {"bumps": list(K_BUMPS), "jump1": K_JUMP1, "jump2": K_JUMP2, "canyon": list(CANYON),
                 "forest": list(FOREST), "pond_trail_m": K_POND}

# checkpoints extras (o mapa recarrega ao falhar: renasce no último alcançado)
CPS = [("CP_Road1", road_pt(K_JUMP1 - 70), road_h[K_JUMP1 - 70], yaw_of(r_tan[K_JUMP1 - 70]), "Road1", "DRIVING", {}),
       ("CP_Road2", road_pt(K_JUMP2 - 90), road_h[K_JUMP2 - 90], yaw_of(r_tan[K_JUMP2 - 90]), "Road2", "DRIVING", {}),
       ("CP_Parkour", trail_pt(K_POND - 30), trail_h[K_POND - 30], yaw_of(t_tan[K_POND - 30]), "Parkour", "ON_FOOT",
        {"respawn_with_melee": True, "respawn_with_pistol": True}),
       ("CP_Arena", trail_pt(NT - 45), trail_h[NT - 45], yaw_of(t_tan[NT - 45]), "Arena", "ON_FOOT",
        {"respawn_with_melee": True, "respawn_with_pistol": True, "respawn_with_shotgun": True})]
L["checkpoints"] = [{"label": a, "loc": ue(p, z), "yaw": y, "id": i, "stage": s, "props": pr} for a, p, z, y, i, s, pr in CPS]

# ---- saltos: rampa antes do vão, aterrissagem depois, zona de queda (falha instantânea)
for gi, g in enumerate(GAPS):
    kj, gap, t, n = g["k"], g["gap"], g["t"], g["n"]
    yaw = yaw_of(t)
    ramp_c = road[kj] - t * 3.5                     # SM_Ramp: 7 m, sobe para +X, borda alta no início do vão
    add_prop("SM_Ramp", ramp_c, g["h"] + 0.04, yaw, [1.0, 1.6, 1.0], 900)
    land_c = road[kj] + t * (gap + 4.5)             # SM_RampLanding: 9 m, alto em -X (lado do vão)
    add_prop("SM_RampLanding", land_c, g["h"] + 0.04, yaw, [1.0, 1.5, 1.0], 900)
    cz = g["h"] - 8.0
    add_actor("hazard", g["c"], cz, yaw, f"Hazard_Ravina{gi + 1}", instant_fail=True,
              box_extent=[gap * 50 + 50, (CAR_WALL + 8) * 100, 300])
    for side in (-1, 1):                            # placas e barris avisando
        add_prop("SM_ZombieBillboard", road[kj] - t * 45 + n * side * 10, ground_h(road[kj] - t * 45 + n * side * 10),
                 yaw + 90 * side, 1.0, 600)
        for q in range(3):
            pp = road[kj] - t * (1 + q * 1.2) + n * side * 7.5
            add_prop("SM_Roadblock", pp, ground_h(pp), yaw + 90, 1.0, 400)
    if gi == 1:                                     # ponte estreita (alternativa mais lenta)
        bc = g["c"] + n * 16
        add_prop("SM_BridgePlanks", bc, g["h"] - 0.4, yaw, [1.0, 0.75, 1.0], 900)
        for side in (-1, 1):
            add_prop("SM_GuardRail", bc + n * side * 3.0 + t * (gap / 2 + 6), g["h"], yaw, 1.0, 400)
    add_actor("pickup", road_pt(kj - 60), road_h[kj - 60] + 0.8, 0, f"Pickup_NitroSalto{gi + 1}", type="NITRO", amount=0.5)

# ---- cânion: paredões alternados, cristais, barris explosivos, lombadas
for i, k in enumerate(range(CANYON[0], CANYON[1], 14)):
    for side in (-1, 1):
        o = side * (17 + rng.uniform(0, 5))
        p = road_pt(k, o)
        add_prop("SM_RockWall", p, ground_h(p) - 0.5, yaw_of(r_tan[k]) + rng.uniform(-8, 8),
                 [1.0, 1.0, float(rng.uniform(0.9, 1.6))], 900)
    if i % 3 == 0:
        p = road_pt(k + 7, (24 + rng.uniform(0, 8)) * (1 if i % 2 else -1))
        add_prop("SM_CrystalCluster", p, ground_h(p), None, float(rng.uniform(1.0, 1.8)), 700)
for i, k in enumerate(range(CANYON[0] + 20, CANYON[1], 34)):
    o = float(rng.uniform(-4.5, 4.5))
    add_actor("barrel", road_pt(k, o), road_h[k] + 0.1, float(rng.uniform(0, 360)), f"Barril_Canion_{i + 1:02d}")
    if i % 2 == 0:
        add_actor("barrel", road_pt(k + 1, o + 0.9), road_h[k] + 0.1, 0, f"Barril_Canion_{i + 1:02d}b")
add_actor("pickup", road_pt(CANYON[0] + 90, 2.5), road_h[CANYON[0] + 90] + 0.8, 0, "Pickup_Reparo_Canion", type="REPAIR", amount=30)

# ---- floresta: manada, contêineres/ônibus em zigue-zague, tapetes de pregos, costela gigante
for i, k in enumerate(range(FOREST[0] + 120, FOREST[0] + 190, 13)):
    side = 1 if i % 2 == 0 else -1
    mesh = "SM_BusWreck" if i % 3 == 1 else "SM_Container"
    p = road_pt(k, side * 2.8)
    add_prop(mesh, p, road_h[k], yaw_of(r_tan[k]) + rng.uniform(-12, 12), 1.0, 700)
for i, f in enumerate((0.6, 0.71)):
    k = int(NR * f)
    add_actor("spike", road_pt(k, -2.0 if i == 0 else 2.0), road_h[k] + 0.05, yaw_of(r_tan[k]) + 90, f"Pregos_{i + 1:02d}")
    add_prop("SM_SpikeStrip", road_pt(k, 2.5 if i == 0 else -2.5), road_h[k] + 0.05, yaw_of(r_tan[k]) + 90, 1.0, 300)
K_RIBS = int(NR * 0.77)
add_prop("SM_BoneRibs", road_pt(K_RIBS), road_h[K_RIBS] - 0.2, yaw_of(r_tan[K_RIBS]), 1.6, 1200)
add_actor("pickup", road_pt(FOREST[0] + 40, -2), road_h[FOREST[0] + 40] + 0.8, 0, "Pickup_Reparo_Floresta", type="REPAIR", amount=30)
add_actor("pickup", road_pt(int(NR * 0.92), 2), road_h[int(NR * 0.92)] + 0.8, 0, "Pickup_Reparo_Final", type="REPAIR", amount=30)
for i, k in enumerate(range(80, NR - 60, 170)):
    if any(abs(k - g["k"]) < 70 for g in GAPS):
        continue
    add_actor("pickup", road_pt(k, rng.uniform(-3, 3)), road_h[k] + 0.8, 0, f"Pickup_Nitro_{i + 1:02d}", type="NITRO", amount=0.25)
# guard-rails nas curvas fechadas (lado de fora)
for k in range(30, NR - 30, 9):
    if r_curv[k] > 0.010 and not gap_idx[max(0, k - 12):k + 12].any():
        a5, b5 = r_tan[k - 5], r_tan[k + 5]
        sgn = np.sign(a5[0] * b5[1] - a5[1] * b5[0])
        p = road_pt(k, -sgn * 7.6)
        add_prop("SM_GuardRail", p, road_h[k], yaw_of(r_tan[k]), 1.0, 350)

# ---- zumbis na estrada (grupos a cada ~60 m) + manada + arqueiros
for i, f in enumerate((0.22, 0.43, 0.63, 0.86)):
    k = int(f * (NR - 1))
    side = 16 if i % 2 == 0 else -16
    p = road_pt(k, side)
    gz = ground_h(p)
    add_prop("SM_Watchtower", p, gz, yaw_of(-r_nrm[k] * np.sign(side)), 1.0, 600)
    L["enemies"].append({"type": "archer", "loc": ue(p, gz + 6.0), "label": f"ENM_Road_Archer_{i + 1:02d}", "snap": False})
gid = 0
for k in range(50, NR - 40, 58):
    if any(-40 < k - g["k"] < g["gap"] + 25 for g in GAPS):
        continue
    gid += 1
    for j in range(int(rng.integers(2, 5))):
        p = road_pt(k + j * 3, rng.uniform(-9, 9))
        L["enemies"].append({"type": "melee", "loc": ue(p, road_h[k] + 1), "label": f"ENM_Road_G{gid:02d}_{j + 1}"})
K_HERD = FOREST[0] + 60
for j in range(10):                                  # manada atravessando a estrada
    p = road_pt(K_HERD + (j % 4) * 3, -14 + j * 3.0)
    L["enemies"].append({"type": "melee", "loc": ue(p, ground_h(p) + 1), "label": f"ENM_Road_Manada_{j + 1:02d}"})

# ---- histórias (mensagens): estrada
STORY = [
    (road_pt(15), road_h[15], "Sinal de socorro vindo do posto de pesquisa, no fundo do vale. Pise fundo! [SHIFT] = nitro.",
     "Siga a estrada até o desembarque", False),
    (road_pt(CANYON[0]), road_h[CANYON[0]], "Cânion de cristais. Barris vermelhos explodem: jogue os zumbis neles.",
     "Cuidado com os barris", False),
    (road_pt(K_JUMP1 - 110), road_h[K_JUMP1 - 110], "A ponte caiu! Pegue velocidade e salte pela rampa.",
     "Acelere para a rampa (use o nitro)", False),
    (road_pt(FOREST[0] + 20), road_h[FOREST[0] + 20], "Floresta alienígena. Uma manada vem aí: atropelar enche o nitro.",
     "Atravesse a floresta", False),
    (road_pt(K_JUMP2 - 120), road_h[K_JUMP2 - 120], "Ravina à frente: rampa (rápido) ou ponte estreita à direita (seguro).",
     "Salte a ravina ou use a ponte", False),
]
for i, (p, z, msg, hint, foot) in enumerate(STORY):
    add_actor("story", p, z + 1.5, 0, f"Historia_Estrada_{i + 1:02d}", message=msg, objective_hint=hint, on_foot_only=foot,
              box_extent=[1600, 1600, 600])

# ---- a pé: graveto, vilas, baú, parkour, Fúria, elite, arena
stick_p = PLAZA[0] + (trail[12] - trail[0]) / np.linalg.norm(trail[12] - trail[0]) * 14 + t_nrm[0] * 6
add_actor("pickup", stick_p, PLAZA[1] + 0.15, 0, "Pickup_Graveto", type="WEAPON_MELEE", amount=1, display="SM_AlienStick")
for q in range(5):                                   # bosque roxo em volta do graveto
    a_ = q / 5 * 2 * math.pi
    pp = stick_p + np.array([math.cos(a_), math.sin(a_)]) * rng.uniform(5, 8)
    add_prop(["SM_AlienFlowerGlow", "SM_MushroomCluster", "SM_AlienPlant_Tentacle"][q % 3], pp, ground_h(pp), None, 1.0, 300, True)
add_actor("story", PLAZA[0], PLAZA[1] + 1.5, 0, "Historia_Desembarque",
          message="O carro não passa daqui. Você está desarmado... aquele galho brilhante parece uma espada.",
          objective_hint="Pegue o graveto brilhante [E]", on_foot_only=True, box_extent=[2000, 2000, 600])

enc = [("melee", "melee", "melee", "melee"), ("melee", "melee", "archer", "melee", "gunner"),
       ("melee", "gunner", "melee", "archer", "melee")]
for vi, ((c, h, r), group) in enumerate(zip(VILLAGES, enc)):
    k = int(np.argmin(np.linalg.norm(trail - np.array(c), axis=1)))
    t = trail[min(k + 5, NT - 1)] - trail[max(k - 5, 0)]
    t /= np.linalg.norm(t)
    n = np.array([-t[1], t[0]])
    for hidx, (fo, so) in enumerate(((-10, 13), (8, -14), (16, 12), (-4, -15))):
        p = np.array(c) + t * fo + n * so
        add_prop("SM_Ruin_House" if hidx % 2 == 0 else "SM_Ruin_Wall", p, h, yaw_of(t) + (0 if hidx % 2 == 0 else 90), 1.0, 700)
        if vi == 0 and hidx == 0:                    # baú dentro da casa grande da vila 1
            add_actor("chest", p, h + 0.02, yaw_of(-n), "Bau_Vila1", weapon="PISTOL", ammo=24)
    for q in range(6):
        p = np.array(c) + t * rng.uniform(-20, 20) + n * rng.uniform(6, 10) * (1 if q % 2 else -1)
        add_prop(["SM_Crate", "SM_Barrel", "SM_Fence", "SM_EggSac", "SM_SporePod", "SM_Crate"][q], p, h, None, 1.0, 250)
    for gi2, typ in enumerate(group):
        p = np.array(c) + t * (6 + gi2 * 3) + n * ((gi2 % 2) * 2 - 1) * 4
        L["enemies"].append({"type": typ, "loc": ue(p, h + 1), "label": f"ENM_Foot_E{vi + 1}_{gi2 + 1:02d}_{typ}"})
    add_actor("pickup", np.array(c) + t * -6 + n * 3, h + 0.8, 0, f"Pickup_Municao_Vila{vi + 1}", type="AMMO", amount=18)
v1c, v1h = VILLAGES[0][0], VILLAGES[0][1]
add_actor("story", v1c, v1h + 1.5, 0, "Historia_Vila1", message="Uma vila abandonada. Tem um baú na casa grande...",
          objective_hint="Abra o baú da casa [E]", on_foot_only=True, box_extent=[2200, 2200, 600])
# Fúria escondida na vila 2 (atrás da casa)
v2c, v2h = VILLAGES[1][0], VILLAGES[1][1]
add_actor("pickup", np.array(v2c) + (v2c - trail[0]) / np.linalg.norm(v2c - trail[0]) * 0 + np.array([12.0, -16.0]), v2h + 0.8, 0,
          "Pickup_Furia_Vila2", type="FURY", amount=12)
add_actor("story", v2c, v2h + 1.5, 0, "Historia_Vila2", message="Algo brilha atrás das ruínas... dizem que dá uma fúria danada.",
          objective_hint="Procure o brilho vermelho", on_foot_only=True, box_extent=[2200, 2200, 600])
# vila 3: nave caída, monólitos e o zumbi elite (deixa a escopeta)
v3c, v3h = VILLAGES[2][0], VILLAGES[2][1]
k3 = int(np.argmin(np.linalg.norm(trail - np.array(v3c), axis=1)))
ufo_p = trail_pt(k3, 30)
add_prop("SM_UFOWreck", ufo_p, ground_h(ufo_p) - 1.0, yaw_of(t_tan[k3]) + 20, 1.0, 1500)
for q in range(4):
    pp = trail_pt(k3 + q * 6 - 9, -14 if q % 2 else 14)
    add_prop("SM_AlienMonolith", pp, ground_h(pp), None, float(rng.uniform(0.9, 1.3)), 900)
L["enemies"].append({"type": "elite", "loc": ue(trail_pt(k3 + 8, 4), v3h + 1), "label": "ENM_Foot_Elite_Nave"})
add_actor("story", trail_pt(k3 - 20), trail_h[max(0, k3 - 20)] + 1.5, 0, "Historia_Nave",
          message="A nave caída! Um zumbi enorme guarda o lugar. Derrube-o: ele carrega algo pesado.",
          objective_hint="Derrote o zumbi gigante", on_foot_only=True, box_extent=[2000, 2000, 600])

# parkour: pilares sobre o lago tóxico (zigue-zague), lago com dano forte
pk = []
n_pil = 7   # vãos de ~1,2 a 1,8 m entre pilares; ~2,3 m da margem até o primeiro
for q in range(n_pil):
    s_ = -POND_ALONG + 2.6 + q * (2 * POND_ALONG - 5.2) / (n_pil - 1)
    l_ = (1.2 if q % 2 else -1.2) + rng.uniform(-0.3, 0.3)
    p = POND_C + pt * s_ + pn * l_
    tall = q in (2, 4)
    mesh_top = 2.0 if tall else 2.5
    top = POND_H + (0.45 if tall else 0.0)
    base = POND_H - 2.2
    mesh = "SM_StonePlatformTall" if tall else "SM_StonePlatform"
    hm = 2.0 if tall else 1.0
    add_prop(mesh, p, base, float(rng.uniform(0, 90)), [1.0, 1.0, round((top - base) / hm, 3)], 500)
    pk.append(ue(p, top))
L["parkour"] = pk
add_actor("toxic_plane", POND_C, POND_H - 0.9, yaw_of(pt), "Lago_Toxico", size_m=[POND_ALONG * 2 + 6, POND_SIDE * 2 + 6])
add_actor("hazard", POND_C, POND_H - 1.6, yaw_of(pt), "Hazard_LagoToxico", instant_fail=True, damage_per_second=45,
          box_extent=[POND_ALONG * 100 + 200, POND_SIDE * 100 + 200, 120])
add_actor("story", trail_pt(K_POND - 22), trail_h[K_POND - 22] + 1.5, 0, "Historia_Lago",
          message="Lago tóxico! Pule de pedra em pedra [ESPAÇO]. Cair = voltar ao checkpoint.",
          objective_hint="Atravesse pelos pilares", on_foot_only=True, box_extent=[1200, 1200, 600])
add_actor("pickup", trail_pt(K_POND + 22, 2), trail_h[min(NT - 1, K_POND + 22)] + 0.8, 0, "Pickup_Vida_Lago", type="HEALTH", amount=40)
for q in range(8):                                   # borda do lago
    a_ = q / 8 * 2 * math.pi
    pp = POND_C + pt * math.cos(a_) * (POND_ALONG + 1.5) + pn * math.sin(a_) * (POND_SIDE * 0.5)
    if abs(math.cos(a_)) > 0.8:
        continue
    add_prop("SM_ToxicPoolRim", pp, ground_h(pp) - 0.2, None, 1.0, 400, True)

# munição/vida pela trilha (sempre algo para pegar)
for i, k in enumerate(range(30, NT - 40, 70)):
    typ = "HEALTH" if i % 4 == 3 else "AMMO"
    add_actor("pickup", trail_pt(k, rng.uniform(-3, 3)), trail_h[k] + 0.8, 0, f"Pickup_Trilha_{i + 1:02d}",
              type=typ, amount=30 if typ == "HEALTH" else 12)
# spawner ambiente a pé (grupos pequenos fora da visão, sempre perseguindo)
add_actor("spawner", PLAZA[0], PLAZA[1] + 1, 0, "Spawner_APe", stage="ON_FOOT")
add_actor("story", trail_pt(NT - 30), trail_h[NT - 30] + 1.5, 0, "Historia_Arena",
          message="A cela está ali na cratera. Eles sentiram seu cheiro: segure a horda!",
          objective_hint="Sobreviva às ondas", on_foot_only=True, box_extent=[1500, 1500, 600])
# arco de pedra sobre a trilha (marco visual)
ka = int(NT * 0.70)
add_prop("SM_AlienArch", trail_pt(ka), trail_h[ka] - 0.3, yaw_of(t_tan[ka]) + 90, 1.0, 1500)

# ---- arena
ac, ah, ar = ARENA
entry = math.degrees(math.atan2(*(trail[-30] - np.array(ac))[::-1]))
for s in range(16):
    ang = s / 16 * 2 * math.pi
    if abs(((math.degrees(ang) - entry + 180) % 360) - 180) < 25:
        continue
    if s % 4 == 2:
        continue
    p = np.array(ac) + np.array([math.cos(ang), math.sin(ang)]) * ar
    add_prop("SM_ArenaWall", p, ah, yaw_of((-math.sin(ang), math.cos(ang))), 1.0, 800)
for s in range(4):
    ang = (s * 4 + 2) / 16 * 2 * math.pi
    p = np.array(ac) + np.array([math.cos(ang), math.sin(ang)]) * (ar + 14)
    L["horde_points"].append(ue(p, ground_h(p) + 1))
for q in range(6):
    ang = q / 6 * 2 * math.pi + 0.3
    p = np.array(ac) + np.array([math.cos(ang), math.sin(ang)]) * ar * 0.55
    add_prop(["SM_Crate", "SM_Barricade", "SM_CarWreck"][q % 3], p, ah, None, 1.0, 400)
    pp = np.array(ac) + np.array([math.cos(ang + 0.5), math.sin(ang + 0.5)]) * ar * 0.4
    add_actor("pickup", pp, ah + 0.8, 0, f"Pickup_Arena_{q + 1}", type="AMMO" if q % 2 else "HEALTH",
              amount=15 if q % 2 else 30)
dirv = (np.array(ac) - trail[-30])
dirv /= np.linalg.norm(dirv)
cage = np.array(ac) + dirv * (ar * 0.7)
L["rescue"] = {"loc": ue(cage, ah), "yaw": yaw_of(-dirv)}
L["horde_director"] = {"loc": ue(ac, ah)}

# ---- paredes invisíveis (limite do corredor)
road_d_all = lambda q: float(np.min(np.linalg.norm(road[::2] - q, axis=1)))   # noqa: E731
trail_d_all = lambda q: float(np.min(np.linalg.norm(trail[::2] - q, axis=1)))  # noqa: E731


def flat_ok(q):
    return all(np.linalg.norm(q - np.array(c)) > r + 18 for (c, h, r) in FLATS)


def wall_line(poly, nrm_, off, is_road):
    for side in (-1, 1):
        pts = [poly[k] + nrm_[k] * off * side for k in range(0, len(poly), 12)]
        ok = []
        for q in pts:
            good = (road_d_all(q) > (CAR_WALL - 6 if is_road else CAR_WALL - 6)) or not is_road
            if is_road:
                good = road_d_all(q) > CAR_WALL - 6 and trail_d_all(q) > FOOT_WALL - 3
            else:
                good = trail_d_all(q) > FOOT_WALL - 3 and road_d_all(q) > CAR_WALL - 6
            ok.append(good and flat_ok(q))
        for a_, b_, oa, ob in zip(pts[:-1], pts[1:], ok[:-1], ok[1:]):
            if oa and ob:
                mid = (a_ + b_) / 2
                ln = float(np.linalg.norm(b_ - a_)) + 2.0
                L["walls"].append({"loc": ue(mid, ground_h(mid) - 10), "yaw": yaw_of(b_ - a_), "len_cm": round(ln * 100),
                                   "h_cm": 6000})


wall_line(road, r_nrm, CAR_WALL, True)
wall_line(trail, t_nrm, FOOT_WALL, False)
# tampas: atrás da largada e em volta das áreas planas (exceto onde a rota passa)
for (c, h, r), extra in ((PLAZA, 22), (ARENA, 26)):
    rr = r + extra
    for s in range(24):
        a0_, a1_ = s / 24 * 2 * math.pi, (s + 1) / 24 * 2 * math.pi
        pa = np.array(c) + np.array([math.cos(a0_), math.sin(a0_)]) * rr
        pb = np.array(c) + np.array([math.cos(a1_), math.sin(a1_)]) * rr
        mid = (pa + pb) / 2
        if road_d_all(mid) < CAR_WALL - 4 or trail_d_all(mid) < FOOT_WALL - 2:
            continue
        L["walls"].append({"loc": ue(mid, ground_h(mid) - 10), "yaw": yaw_of(pb - pa),
                           "len_cm": round(float(np.linalg.norm(pb - pa) + 2) * 100), "h_cm": 6000})
back = road[0] - r_tan[0] * 25
L["walls"].append({"loc": ue(back, ground_h(back) - 10), "yaw": yaw_of(r_nrm[0]), "len_cm": round(CAR_WALL * 2 * 100), "h_cm": 6000})
print("paredes:", len(L["walls"]))

# ---- vistas fora do caminho (só para olhar)
VISTAS = []


def high_spot(center, rmin, rmax, tries=300):
    best, bz = None, -1e9
    for _ in range(tries):
        a_ = rng.uniform(0, 2 * math.pi)
        q = np.array(center) + np.array([math.cos(a_), math.sin(a_)]) * rng.uniform(rmin, rmax)
        if np.max(np.abs(q)) > 900:
            continue
        if road_d_all(q) < CAR_WALL + 20 or trail_d_all(q) < FOOT_WALL + 25:
            continue
        z = ground_h(q)
        if z > bz:
            best, bz = q, z
    return best, bz


farm, fz = high_spot(road[int(NR * 0.55)], 140, 260)
add_prop("SM_FarmhouseRuin", farm, fz - 0.3, yaw_of(road[int(NR * 0.55)] - farm), 1.2, 2500)
turb = farm + np.array([22.0, 14.0])
add_prop("SM_WindTurbineBroken", turb, ground_h(turb) - 0.3, 30, 1.2, 3000)
VISTAS.append(("fazenda", farm))
for i in range(9):
    sp, sz = high_spot(rng.uniform(-600, 600, 2), 50, 250, 120)
    if sp is not None:
        add_prop("SM_CrystalSpire", sp, sz - 0.5, None, float(rng.uniform(1.5, 3.0)), 3000)
ufo2, uz = high_spot(road[int(NR * 0.2)], 160, 300)
add_prop("SM_UFOWreck", ufo2, uz - 2.0, float(rng.uniform(0, 360)), 1.4, 3000)
VISTAS.append(("nave2", ufo2))
L["vistas"] = [{"name": n_, "loc": ue(p, ground_h(p))} for n_, p in VISTAS]

# ---- vegetação por bioma (mais densa na beira do corredor)
cands = rng.uniform(-930, 930, (16000, 2))
cd_r, cr_i = nearest(cands, road)
cd_t, _ = nearest(cands, trail)
fd = np.min([np.linalg.norm(cands - np.array(c)[None, :], axis=1) - r for (c, h, r) in FLATS], axis=0)
pond_c2 = ((cands - POND_C) @ pt / (POND_ALONG + 3)) ** 2 + ((cands - POND_C) @ pn / (POND_SIDE + 3)) ** 2
keep = (cd_r > 13) & (cd_t > 6) & (fd > 6) & (pond_c2 > 1.0)
for g in GAPS:
    keep &= np.linalg.norm(cands - g["c"], axis=1) > 30
dmin = np.minimum(cd_r, cd_t)
prob = np.where(dmin < 45, 0.35, np.where(dmin < 160, 0.6, 0.12))
keep &= rng.uniform(0, 1, len(cands)) < prob
DESERT = {"SM_Rock_Large": 0.2, "SM_Rock_Medium": 0.2, "SM_Rock_Small": 0.12, "SM_Tree_Dead": 0.12,
          "SM_CrystalCluster": 0.14, "SM_EggSac": 0.05, "SM_SporePod": 0.05, "SM_AlienPlant_Tentacle": 0.07,
          "SM_AlienMonolith": 0.02, "SM_Bush": 0.03}
FOREST_SET = {"SM_AlienTree_Spiral": 0.15, "SM_AlienTree_Umbrella": 0.14, "SM_AlienTree_Fan": 0.13,
              "SM_MushroomGiant": 0.1, "SM_MushroomCluster": 0.09, "SM_AlienPlant_Tentacle": 0.08,
              "SM_SporePod": 0.06, "SM_AlienFlowerGlow": 0.07, "SM_GrassAlienTuft": 0.08, "SM_Rock_Medium": 0.05,
              "SM_CrystalCluster": 0.03, "SM_Bush": 0.02}
HIGH = {"SM_Rock_Large": 0.35, "SM_Rock_Medium": 0.25, "SM_CrystalCluster": 0.25, "SM_CrystalSpire": 0.05,
        "SM_Tree_Dead": 0.1}
NOCOL = {"SM_Bush", "SM_Rock_Small", "SM_AlienFlowerGlow", "SM_GrassAlienTuft", "SM_MushroomCluster", "SM_EggSac"}
BIG = ("SM_AlienTree", "SM_MushroomGiant", "SM_Rock_Large", "SM_CrystalSpire", "SM_Tree", "SM_AlienMonolith")
counts = {}
for p, ridx, dr_, dt_ in zip(cands[keep], cr_i[keep], cd_r[keep], cd_t[keep]):
    z = ground_h(p)
    pr = ridx / (NR - 1)
    if z > 85:
        table = HIGH
    elif dt_ < dr_ or pr > 0.40:
        table = FOREST_SET
    else:
        table = DESERT
    names, ws = list(table), np.array(list(table.values()))
    mesh = str(rng.choice(names, p=ws / ws.sum()))
    if dmin.min() >= 0 and min(dr_, dt_) < 20 and mesh in ("SM_AlienTree_Umbrella", "SM_MushroomGiant"):
        mesh = "SM_MushroomCluster"
    cull = 1000 if mesh.startswith(BIG) else 350
    add_prop(mesh, p, z - 0.15, None, float(rng.uniform(0.8, 1.35)), cull, mesh in NOCOL)
    counts[mesh] = counts.get(mesh, 0) + 1
print("vegetação:", counts, "total props:", len(L["props"]))

# ---- navegação
pts = np.vstack([trail, road[-200:], np.array([ac])])
mn, mx = pts.min(0) - 60, pts.max(0) + 60
L["nav_bounds"] = {"center": ue((mn + mx) / 2, float(np.mean(trail_h))), "size_cm": [float(mx[0] - mn[0]) * 100,
                   float(mx[1] - mn[1]) * 100, 16000.0]}
L["road_nav_bounds"] = []
for s0 in range(0, NR - 200, 300):
    seg = road[s0:s0 + 300]
    mn, mx = seg.min(0) - 25, seg.max(0) + 25
    L["road_nav_bounds"].append({"center": ue((mn + mx) / 2, float(np.mean(road_h[s0:s0 + 300]))),
                                 "size_cm": [float(mx[0] - mn[0]) * 100, float(mx[1] - mn[1]) * 100, 12000.0]})
json.dump(L, open(os.path.join(OUT, "l01_layout.json"), "w"), indent=1)

np.savez_compressed(os.path.join(OUT, "l01_preview.npz"), col=prev, H=H2, road=road, trail=trail,
                    plaza=np.array(PLAZA[0]), arena=np.array(ARENA[0]), arena_r=ARENA[2], cage=cage,
                    gaps=np.array([g["c"] for g in GAPS]), pond=np.array(POND_C),
                    walls=np.array([[w["loc"][0] / 100, -w["loc"][1] / 100] for w in L["walls"]]))
print("ok")

# ------------------------------------------------------------------ conferência rápida (impresso)
for g in GAPS:
    prof = [round(ground_h(g["c"] + g["n"] * l_) - g["h"], 1) for l_ in (0, 10, 30, 50, 70, 80, 90)]
    edge_ = [round(ground_h(g["c"] + g["t"] * s_) - g["h"], 1) for s_ in (-g["gap"] / 2 - 2, -2, 2, g["gap"] / 2 + 2)]
    print("vão", g["k"], "lateral", prof, "ao longo", edge_)
print("lago", [round(ground_h(POND_C + pn * l_) - POND_H, 1) for l_ in (0, 20, 40, 45, 50)],
      [round(ground_h(POND_C + pt * s_) - POND_H, 1) for s_ in (-20, -16, 0, 16, 20)])
print("pilares (topo cm)", L["parkour"])
