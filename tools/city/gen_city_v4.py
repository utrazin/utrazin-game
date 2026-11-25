"""[A-091] Villa Star v4: planta da cidade gerada por regras (roda fora da Unreal: python gen_city_v4.py <pasta_saida>).

Saídas (pasta assets/work/city_v4 no repo):
  city_height.png   heightmap 16 bits 1009 x 1009 (1 m por pixel, centro = centro da cidade). Importar no Landscape.
  city_mask.png     RGBA 2048 x 2048 sobre os mesmos 1008 m: R asfalto, G concreto (praça/calçada), B terra, A lama tóxica.
  city_layout.json  tudo o que vai no mapa (prédios, casas, postes, árvores, props, muralha, portão, NPCs), em metros.
  city_preview.png  vista de cima para aprovar.
Base: docs/design/mapa_cidade_proposta.png e REMAP_CIDADE_ARENA.md 3.x. Decisões do usuário (23/11): Landscape,
portão do Kaar = saída norte da muralha (arena lá fora), Bancada + Armeiro + 3 casas exploráveis.

Regras por item (resumo; detalhe em docs/design/CIDADE_V4.md):
  ruas: anel r=150 m (10 m) + 4 avenidas (9 m) + ruas tortas (6 m) ligando o anel aos bairros + trilhas de terra até
        a porta de cada prédio; calçada de concreto (2 m) no anel e nas avenidas.
  prédios com função: lugar fixo do rascunho, de frente para a rua mais perto, a até ~120 m da praça (os usados
        a cada volta); NPC na porta (por dentro quando os interiores existirem).
  casas: Poisson (16 a 22 m entre si), longe das ruas (meia largura + 4 m), de frente para a rua mais perta, giro
        com ±8 graus, escala 0,9 a 1,15, mais densas no sul (residencial), raras no norte (portão/rádio).
  postes: anel e avenidas a cada 32 m alternando lados, luz em um sim um não; praça com 8.
  árvores: anel interno da praça, jardins nos fundos das casas, faixa verde dentro do anel; nunca na rua.
  barris/geradores/placas: só em grupos de 2 a 3 perto de oficina, armazém, mercado e ruínas (antes: 60 soltos).
  ruínas: nos 5 lugares hachurados (pedras, troncos, barricadas, ossos, cristal).
  borda: muralha 400 x 400 com torre a cada ~48 m e nas quinas, portão norte com campo de força;
        fora: fosso raso, morros e penhascos (não dá para chegar: a muralha fecha), rio de lama tóxica a noroeste.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SEED = 2311
RES = 1009            # vértices do Landscape (1008 m)
HALF_M = (RES - 1) / 2.0
MASK_RES = 2048
CITY_HALF = 200.0     # muralha em +-200 m
RING_R = 150.0
PLAZA_R = 28.0

rng = random.Random(SEED)
np_rng = np.random.default_rng(SEED)

# medidas (m) das malhas (tripo_processed.json): comprido, largo, alto
DIMS = {
    "armeiro": (9.0, 7.5, 5.5), "bancada": (8.0, 6.2, 6.6), "casa1": (8.6, 7.1, 9.0), "casa2": (9.0, 8.9, 7.5),
    "casavila": (10.0, 9.1, 8.0), "cabana": (6.0, 5.7, 5.2), "torre_radio": (8.3, 8.2, 25.0), "posto_loja": (10.0, 8.5, 6.7),
    "barraca": (6.5, 5.1, 4.2), "conteiner": (6.0, 4.4, 2.3), "cristal": (8.0, 7.8, 8.0), "nave": (20.0, 10.8, 6.5),
}


# ------------------------------------------------------------------ ruas (polilinhas em metros)
def circle(r, n=180):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n + 1)]


def catmull(points, steps=12):
    out = []
    pts = [points[0]] + points + [points[-1]]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for s in range(steps):
            t = s / steps
            t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * ((2 * p1[k]) + (-p0[k] + p2[k]) * t + (2 * p0[k] - 5 * p1[k] + 4 * p2[k] - p3[k]) * t2
                                    + (-p0[k] + 3 * p1[k] - 3 * p2[k] + p3[k]) * t3) for k in range(2)))
    out.append(points[-1])
    return out


def wobbly(a, b, amp, n=4):
    """Rua torta de a até b: pontos intermediários deslocados de lado."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    ln = math.hypot(dx, dy)
    nx, ny = -dy / ln, dx / ln
    pts = [a]
    for i in range(1, n):
        t = i / n
        off = rng.uniform(-amp, amp) * math.sin(math.pi * t)
        pts.append((ax + dx * t + nx * off, ay + dy * t + ny * off))
    pts.append(b)
    return catmull(pts)


ROADS = []  # (nome, polilinha, largura, tipo) tipo: asfalto | terra


def densify(poly, step=2.0):
    out = [poly[0]]
    for (ax, ay), (bx, by) in zip(poly[:-1], poly[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / step))
        for k in range(1, n + 1):
            out.append((ax + (bx - ax) * k / n, ay + (by - ay) * k / n))
    return out


def add_road(name, poly, width, kind="asfalto", sidewalk=0.0):
    ROADS.append({"name": name, "poly": densify(poly), "width": width, "kind": kind, "sidewalk": sidewalk})


add_road("anel", circle(RING_R), 10.0, sidewalk=2.0)
add_road("av_norte", [(0, PLAZA_R - 2), (0, CITY_HALF - 6)], 9.0, sidewalk=2.0)
add_road("av_sul", [(0, -PLAZA_R + 2), (0, -CITY_HALF + 12)], 9.0, sidewalk=2.0)
add_road("av_leste", [(PLAZA_R - 2, 0), (CITY_HALF - 12, 0)], 9.0, sidewalk=2.0)
add_road("av_oeste", [(-PLAZA_R + 2, 0), (-CITY_HALF + 12, 0)], 9.0, sidewalk=2.0)


def ring_pt(deg, r=RING_R):
    return (r * math.cos(math.radians(deg)), r * math.sin(math.radians(deg)))


# ruas tortas: anel -> bairros (e algumas para fora do anel, perto da muralha)
for name, a, b, amp in (
    ("rua_lab", ring_pt(45), (158, 132), 6),
    ("rua_comercio", ring_pt(20), (60, 70), 10),
    ("rua_mercado", ring_pt(-15), (60, -45), 10),
    ("rua_armazem", ring_pt(-45), (150, -140), 6),
    ("rua_residencial_l", ring_pt(-80), (40, -60), 12),
    ("rua_residencial_o", ring_pt(-105), (-45, -70), 12),
    ("rua_prefeitura", ring_pt(-135), (-150, -145), 6),
    ("rua_oficinas", ring_pt(170), (-75, 25), 10),
    ("rua_radio", ring_pt(110), (-40, 132), 8),
    ("beco_sudeste", (40, -60), (95, -110), 10),
    ("beco_sudoeste", (-45, -70), (-100, -110), 10),
    ("beco_noroeste", ring_pt(150), (-170, 120), 8),
    ("beco_externo_s", ring_pt(-90), (0, -185), 0),
):
    add_road(name, wobbly(a, b, amp), 6.0)


# ------------------------------------------------------------------ prédios com função (rascunho)
def facing(x, y, tx, ty):
    return math.degrees(math.atan2(ty - y, tx - x))


PLACES = []  # prédios/conjuntos fixos


def place(key, x, y, yaw, scale=1.0, role=None, folder="Predios", collide=True, explorable=False, label=None):
    PLACES.append({"key": key, "x": round(x, 2), "y": round(y, 2), "yaw": round(yaw % 360, 1), "scale": round(scale, 3),
                   "role": role, "folder": folder, "collide": collide, "explorable": explorable, "label": label})


# prédio fica de frente para o ponto de rua mais perto (porta para a rua)
def face_road(x, y):
    best = None
    for r in ROADS:
        if r["kind"] != "asfalto":
            continue
        for (px, py) in r["poly"]:
            d = (px - x) ** 2 + (py - y) ** 2
            if best is None or d < best[0]:
                best = (d, px, py)
    return facing(x, y, best[1], best[2]), math.sqrt(best[0])


FUNCTIONAL = [
    # key, x, y, role, label, explorable, escala
    ("armeiro", 98, 38, "Armeiro", "Armeiro_Krug", True, 1.25),
    ("bancada", -108, -26, "Bancada", "Bancada_IxVel", True, 1.25),
    ("casa1", -62, -112, "CasaHeroi", "Casa_Heroi", True, 1.05),
    ("casavila", 22, -112, "CasaSaqueada", "Casa_Saqueada", True, 1.0),
    ("casa2", 60, 92, "Bar", "Bar_Conversa", True, 1.05),
    ("posto_loja", -108, 40, "Garagem", "Garagem", False, 1.1),
    ("torre_radio", -50, 150, "Radio", "Radio_Contratos", False, 0.9),
    ("cabana", 150, 150, "Laboratorio", "Laboratorio", False, 1.3),
    ("casavila", -150, -160, "Prefeitura", "Prefeitura", False, 1.15),
]
for key, x, y, role, label, expl, sc in FUNCTIONAL:
    yaw, _ = face_road(x, y)
    place(key, x, y, yaw, sc, role=role, label=label, explorable=expl, folder="Predios")

# trilha de terra da porta até a rua (cada prédio com função)
for p in list(PLACES):
    yaw = math.radians(p["yaw"])
    d = max(DIMS[p["key"]][:2]) * p["scale"] * 0.5
    door = (p["x"] + math.cos(yaw) * d, p["y"] + math.sin(yaw) * d)
    _, dist = face_road(*door)
    end = (door[0] + math.cos(yaw) * (dist + 2), door[1] + math.sin(yaw) * (dist + 2))
    add_road(f"trilha_{p['label']}", [door, end], 3.5, kind="terra")
    p["door"] = [round(door[0], 2), round(door[1], 2)]

# mercado: 3 barracas em arco; armazém: pátio de contêineres; laboratório: cristal ao lado
for i, ang in enumerate((-25, 0, 25)):
    x, y = 112 + 14 * math.cos(math.radians(180 + ang)), -32 + 14 * math.sin(math.radians(180 + ang))
    place("barraca", x, y, facing(x, y, 70, -30), 1.0, role="Mercado" if i == 1 else None, label=f"Mercado_{i}", folder="Mercado")
for i in range(5):
    place("conteiner", 140 + (i % 3) * 7.5, -160 + (i // 3) * 10, 90 + rng.uniform(-3, 3), 1.15, role="Armazem" if i == 0 else None,
          label=f"Armazem_{i}", folder="Armazem")
place("cristal", 166, 138, rng.uniform(0, 360), 0.8, label="Lab_Cristal", folder="Predios")
# monumento
place("nave", 0, 0, 35.0, 0.7, role="Monumento", label="Monumento_Nave", folder="Praca")

# ruínas (hachurado no rascunho)
RUINS = [(-140, 90), (-172, -58), (166, 60), (92, -172), (-58, 172)]


# ------------------------------------------------------------------ rasterização (máscara e distância às ruas)
def to_px(x, y, res, size_m):
    s = res / size_m
    return ((x + size_m / 2) * s, (size_m / 2 - y) * s)  # y para cima no mundo, para baixo na imagem


SIZE_M = RES - 1  # 1008 m


def draw_layer(res, kinds, extra_width=0.0, sidewalk_only=False):
    im = Image.new("L", (res, res), 0)
    dr = ImageDraw.Draw(im)
    s = res / SIZE_M
    for r in ROADS:
        if r["kind"] not in kinds:
            continue
        w = (r["width"] + (2 * r["sidewalk"] if sidewalk_only else 0) + extra_width) * s
        pts = [to_px(x, y, res, SIZE_M) for x, y in r["poly"]]
        dr.line(pts, fill=255, width=max(1, int(round(w))), joint="curve")
        for (px, py) in (pts[0], pts[-1]):
            rr = w / 2
            dr.ellipse([px - rr, py - rr, px + rr, py + rr], fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0


def disk(res, x, y, r):
    im = Image.new("L", (res, res), 0)
    dr = ImageDraw.Draw(im)
    s = res / SIZE_M
    cx, cy = to_px(x, y, res, SIZE_M)
    dr.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s], fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0


# grade de 1 m (heightmap) para regras de distância
road_1m = draw_layer(RES, ("asfalto",), sidewalk_only=True)
path_1m = draw_layer(RES, ("terra",))
plaza_1m = disk(RES, 0, 0, PLAZA_R + 3)
blocked_1m = np.maximum(np.maximum(road_1m, path_1m), plaza_1m) > 0.5
dist_road = ndimage.distance_transform_edt(~blocked_1m)  # m até rua/praça/trilha


def world_to_idx(x, y):
    px, py = to_px(x, y, RES, SIZE_M)
    return int(round(py)), int(round(px))


def dist_to_road(x, y):
    i, j = world_to_idx(x, y)
    if 0 <= i < RES and 0 <= j < RES:
        return float(dist_road[i, j])
    return 0.0


# ------------------------------------------------------------------ casas (Poisson com regras)
HOUSE_KEYS = [("casa1", 3), ("casa2", 3), ("casavila", 2), ("cabana", 2)]
houses = []
occupied = [(p["x"], p["y"], max(DIMS[p["key"]][:2]) * p["scale"] * 0.5 + 6) for p in PLACES]
occupied.append((0, 0, PLAZA_R + 12))
for (rx, ry) in RUINS:
    occupied.append((rx, ry, 18))


def district_density(x, y):
    if y < -40:
        return 1.0      # residencial (sul)
    if y > 120 and abs(x) < 80:
        return 0.15     # portão e rádio: espaço aberto
    if x > 60 and y > -40:
        return 0.55     # comércio
    if x < -60:
        return 0.6      # oficinas
    return 0.5


def weighted_key():
    tot = sum(w for _, w in HOUSE_KEYS)
    r = rng.uniform(0, tot)
    for k, w in HOUSE_KEYS:
        r -= w
        if r <= 0:
            return k
    return HOUSE_KEYS[-1][0]


def along(poly, step, offset_side):
    """Pontos a cada `step` m ao longo da polilinha, deslocados para o lado."""
    out = []
    acc = 0.0
    nxt = step * 0.5
    for i in range(len(poly) - 1):
        (ax, ay), (bx, by) = poly[i], poly[i + 1]
        seg = math.hypot(bx - ax, by - ay)
        if seg < 1e-6:
            continue
        while acc + seg >= nxt:
            t = (nxt - acc) / seg
            x, y = ax + (bx - ax) * t, ay + (by - ay) * t
            nx, ny = -(by - ay) / seg, (bx - ax) / seg
            out.append((x + nx * offset_side, y + ny * offset_side, math.degrees(math.atan2(ny, nx))))
            nxt += step
        acc += seg
    return out


def try_house(x, y, yaw, key, sc, gap):
    half_size = max(DIMS[key][:2]) * sc * 0.5
    if max(abs(x), abs(y)) > CITY_HALF - 10 - half_size:
        return False
    if dist_to_road(x, y) < half_size + 2.5:
        return False
    for (ox, oy, orad) in occupied:
        if math.hypot(x - ox, y - oy) < orad + half_size + gap:
            return False
    houses.append({"key": key, "x": round(x, 2), "y": round(y, 2), "yaw": round(yaw % 360, 1), "scale": round(sc, 3),
                   "role": None, "folder": "Casas", "collide": True, "explorable": False, "label": None})
    occupied.append((x, y, half_size))
    return True


# 1) frente de rua: lotes dos dois lados das ruas (casas de frente para a rua, recuo e intervalo variados)
FRONTAGE = {"anel": 0.55, "av_sul": 0.8, "av_leste": 0.55, "av_oeste": 0.6, "av_norte": 0.12}
for r in ROADS:
    if r["kind"] != "asfalto":
        continue
    chance = FRONTAGE.get(r["name"], 0.85)
    for side in (1, -1):
        for (x, y, ang) in along(r["poly"], rng.uniform(17.0, 20.0), 0):
            if rng.random() > chance:
                continue
            key = weighted_key()
            sc = rng.uniform(0.9, 1.15)
            l, w, _ = DIMS[key]
            depth = l * sc * 0.5
            setback = r["width"] / 2 + r["sidewalk"] + rng.uniform(3.0, 6.5) + depth
            nx, ny = math.cos(math.radians(ang)) * side, math.sin(math.radians(ang)) * side
            hx, hy = x + nx * setback, y + ny * setback
            if rng.random() > district_density(hx, hy) * 1.2:
                continue
            yaw = math.degrees(math.atan2(-ny, -nx)) + rng.uniform(-6, 6)  # porta virada para a rua
            try_house(hx, hy, yaw, key, sc, rng.uniform(3.0, 5.5))
# 2) fundos de lote: poucas casas soltas, de frente para a rua mais perto
attempts = 0
while attempts < 6000 and len(houses) < 95:
    attempts += 1
    x = rng.uniform(-CITY_HALF + 14, CITY_HALF - 14)
    y = rng.uniform(-CITY_HALF + 14, CITY_HALF - 14)
    if rng.random() > district_density(x, y) * 0.5:
        continue
    key = weighted_key()
    sc = rng.uniform(0.9, 1.1)
    half_size = max(DIMS[key][:2]) * sc * 0.5
    d_road = dist_to_road(x, y)
    if d_road > half_size + 30:
        continue
    yaw, _ = face_road(x, y)
    try_house(x, y, yaw + rng.uniform(-8, 8), key, sc, rng.uniform(4.0, 7.0))

# ------------------------------------------------------------------ props com regras
props = []


def prop(key, x, y, yaw=None, scale=1.0, folder="Props", collide=False, light=None):
    props.append({"key": key, "x": round(x, 2), "y": round(y, 2), "yaw": round((yaw if yaw is not None else rng.uniform(0, 360)) % 360, 1),
                  "scale": round(scale, 3), "folder": folder, "collide": collide, "light": light})


lamp_i = 0
for r in ROADS:
    if r["name"] not in ("anel", "av_norte", "av_sul", "av_leste", "av_oeste"):
        continue
    off = r["width"] / 2 + r["sidewalk"] - 0.6
    for k, (x, y, ang) in enumerate(along(r["poly"], 32.0, off)):
        side = 1 if k % 2 == 0 else -1
        if side < 0:
            x, y = x - 2 * off * math.cos(math.radians(ang)), y - 2 * off * math.sin(math.radians(ang))
            ang += 180
        if math.hypot(x, y) < PLAZA_R + 6 or max(abs(x), abs(y)) > CITY_HALF - 8:
            continue
        lamp_i += 1
        prop("poste", x, y, ang + 180, 1.0, folder="Postes", collide=True, light=(40.0 if lamp_i % 2 == 0 else None))
for ang in range(0, 360, 45):
    x, y = (PLAZA_R + 1.5) * math.cos(math.radians(ang + 22.5)), (PLAZA_R + 1.5) * math.sin(math.radians(ang + 22.5))
    prop("poste", x, y, ang + 22.5 + 180, 1.0, folder="Postes", collide=True, light=40.0)

# árvores: anel em volta da praça (entre os postes)
for ang in range(0, 360, 30):
    if ang % 90 == 0:
        continue  # deixa as avenidas livres
    x, y = (PLAZA_R + 9) * math.cos(math.radians(ang)), (PLAZA_R + 9) * math.sin(math.radians(ang))
    prop(rng.choice(["arv1", "arv3", "arv4"]), x, y, None, rng.uniform(0.75, 0.95), folder="Natureza", collide=True)
# faixa verde por dentro do anel
for (x, y, ang) in along(circle(RING_R - 14), 26.0, 0):
    if dist_to_road(x, y) < 6 or any(math.hypot(x - ox, y - oy) < orad + 4 for ox, oy, orad in occupied):
        continue
    if rng.random() < 0.7:
        prop(rng.choice(["arv1", "arv3", "arv4", "arb1", "arb2"]), x, y, None, rng.uniform(0.7, 1.0), folder="Natureza", collide=True)
# jardim de cada casa: 1 a 2 arbustos/flores na frente, árvore nos fundos às vezes
for h in houses:
    yaw = math.radians(h["yaw"])
    half_size = max(DIMS[h["key"]][:2]) * h["scale"] * 0.5
    for _ in range(rng.randint(1, 2)):
        side = rng.uniform(-half_size, half_size)
        x = h["x"] + math.cos(yaw) * (half_size + 2.0) - math.sin(yaw) * side
        y = h["y"] + math.sin(yaw) * (half_size + 2.0) + math.cos(yaw) * side
        if dist_to_road(x, y) > 1.5:
            prop(rng.choice(["arb1", "arb2", "arb3", "flor", "flor2"]), x, y, None, rng.uniform(0.8, 1.1), folder="Jardins")
    if rng.random() < 0.45:
        x = h["x"] - math.cos(yaw) * (half_size + 5)
        y = h["y"] - math.sin(yaw) * (half_size + 5)
        if dist_to_road(x, y) > 4 and max(abs(x), abs(y)) < CITY_HALF - 6:
            prop(rng.choice(["arv1", "arv3", "arv4"]), x, y, None, rng.uniform(0.7, 0.95), folder="Jardins", collide=True)


def cluster(cx, cy, keys, n, spread, folder):
    for _ in range(n):
        a = rng.uniform(0, 2 * math.pi)
        r = rng.uniform(0.3, 1.0) * spread
        prop(rng.choice(keys), cx + math.cos(a) * r, cy + math.sin(a) * r, None, rng.uniform(0.9, 1.1), folder=folder, collide=True)


# grupos com lógica (barris/geradores só onde faz sentido)
for p in PLACES:
    if p["role"] in ("Garagem", "Armazem", "Bancada"):
        yaw = math.radians(p["yaw"])
        half_size = max(DIMS[p["key"]][:2]) * p["scale"] * 0.5
        side = 1 if rng.random() < 0.5 else -1
        cx = p["x"] + math.cos(yaw) * 2 - math.sin(yaw) * side * (half_size + 3)
        cy = p["y"] + math.sin(yaw) * 2 + math.cos(yaw) * side * (half_size + 3)
        cluster(cx, cy, ["barril", "barril", "gerador"], rng.randint(2, 3), 2.0, "Props")
    if p["role"] in ("Armeiro", "Bancada", "Bar", "Mercado", "Garagem", "Radio", "Laboratorio", "Prefeitura"):
        yaw = math.radians(p["yaw"])
        half_size = max(DIMS[p["key"]][:2]) * p["scale"] * 0.5
        x = p["x"] + math.cos(yaw) * (half_size + 3.5) + math.sin(yaw) * (half_size * 0.6)
        y = p["y"] + math.sin(yaw) * (half_size + 3.5) - math.cos(yaw) * (half_size * 0.6)
        prop("placa", x, y, p["yaw"], 1.2, folder="Placas", collide=True)
for (rx, ry) in RUINS:
    cluster(rx, ry, ["pedra3", "pedra2", "tronco", "barricada"], rng.randint(4, 6), 9.0, "Ruinas")
    cluster(rx, ry, ["ossos", "cogu", "pedra1"], rng.randint(2, 4), 6.0, "Ruinas")
    prop("cristal_peq", rx + rng.uniform(-3, 3), ry + rng.uniform(-3, 3), None, rng.uniform(0.25, 0.4), folder="Ruinas", collide=True)
# pedras ao pé da muralha (quebram a linha reta)
for k in range(28):
    side = k % 4
    t = rng.uniform(-CITY_HALF + 20, CITY_HALF - 20)
    x, y = [(t, CITY_HALF - 5), (CITY_HALF - 5, t), (t, -CITY_HALF + 5), (-CITY_HALF + 5, t)][side]
    if dist_to_road(x, y) > 6 and not (side == 0 and abs(t) < 25):
        prop(rng.choice(["pedra2", "pedra1", "arb3"]), x, y, None, rng.uniform(0.8, 1.3), folder="Muralha", collide=True)

# fora da muralha (não dá para chegar): penhascos nos morros, árvores e marcos ao longe (horizonte com cara de mundo)
for k in range(44):
    ang = 2 * math.pi * k / 44 + rng.uniform(-0.05, 0.05)
    r = rng.uniform(265, 320)
    c, s_ = math.cos(ang), math.sin(ang)
    m = max(abs(c), abs(s_))
    prop("penhasco", c / m * r, s_ / m * r, None, rng.uniform(1.6, 2.6), folder="Fora", collide=False)
for k in range(110):
    ang = rng.uniform(0, 2 * math.pi)
    r = rng.uniform(225, 430)
    c, s_ = math.cos(ang), math.sin(ang)
    m = max(abs(c), abs(s_))
    prop(rng.choice(["arv1", "arv2", "arv3", "arv4", "tentaculo", "cogu"]), c / m * r, s_ / m * r, None, rng.uniform(1.0, 1.8),
         folder="Fora", collide=False)
for (x, y, key, sc) in ((-330, 260, "arvoremae", 1.6), (360, -250, "arvoremae", 1.3), (300, 330, "cristal", 2.5),
                        (-360, -320, "colmeia", 2.0), (40, 380, "cristal", 1.8)):
    prop(key, x, y, None, sc, folder="Fora", collide=False)

# ------------------------------------------------------------------ muralha, portão, NPCs, chegada
WALL = {"half": CITY_HALF, "tower_every": 48.0, "gate": {"side": "N", "x": 0.0, "width": 14.0}}
NPCS = {
    "Krug": None, "IxVel": None,
    "Kaar": {"x": 0.0, "y": CITY_HALF - 14, "yaw": -90.0},
}
for p in PLACES:
    if p["role"] in ("Armeiro", "Bancada"):
        name = "Krug" if p["role"] == "Armeiro" else "IxVel"
        yaw = math.radians(p["yaw"])
        half_size = max(DIMS[p["key"]][:2]) * p["scale"] * 0.5
        # na porta, do lado de fora, virado para a rua (vai para dentro quando o interior existir)
        NPCS[name] = {"x": round(p["x"] + math.cos(yaw) * (half_size + 1.6), 2), "y": round(p["y"] + math.sin(yaw) * (half_size + 1.6), 2),
                      "yaw": round(p["yaw"], 1), "building": p["label"]}
PLAYER_START = {"x": 0.0, "y": -(PLAZA_R + 6), "yaw": 90.0}

# ------------------------------------------------------------------ heightmap
yy, xx = np.mgrid[0:RES, 0:RES].astype(np.float64)
X = xx - HALF_M                 # m, leste
Y = HALF_M - yy                 # m, norte


def fbm(shape, scales, amps, seed):
    g = np.random.default_rng(seed)
    out = np.zeros(shape, np.float32)
    for s, a in zip(scales, amps):
        n = g.standard_normal((shape[0] // s + 3, shape[1] // s + 3)).astype(np.float32)
        up = ndimage.zoom(n, s, order=3)[: shape[0], : shape[1]]
        out += up * a
    return out


noise = fbm((RES, RES), (128, 48, 16), (1.0, 0.45, 0.15), SEED)
# distância "quadrada arredondada" ao centro (superelipse) para a muralha
sq = CITY_HALF * ((np.abs(X) / CITY_HALF) ** 24 + (np.abs(Y) / CITY_HALF) ** 24) ** (1 / 24)
H = np.zeros((RES, RES), np.float32)
# dentro: platô com desníveis suaves (terraço nordeste +2 m, sul desce 1,5 m)
inside = sq <= CITY_HALF + 8
terr = 2.0 * np.clip((X + Y - 120) / 120, 0, 1) - 1.5 * np.clip((-Y - 60) / 120, 0, 1) + 0.6 * noise
H += np.where(inside, terr, 0)
# fora: fosso raso, depois morros que sobem até 60-160 m (horizonte fechado)
d_out = np.clip(sq - (CITY_HALF + 8), 0, None)
moat = -6.0 * np.clip(d_out / 25.0, 0, 1)
hills = np.clip((d_out - 40) / 160, 0, 1) ** 1.6 * (95 + 55 * noise) + np.clip((d_out - 220) / 60, 0, 1) * 40
ridged = (1 - np.abs(fbm((RES, RES), (64, 24), (1.0, 0.5), SEED + 7))) * 18 * np.clip((d_out - 60) / 100, 0, 1)
H += np.where(inside, 0, moat + hills + ridged)
# rio de lama tóxica a noroeste (fora da muralha): vale mais fundo
river = np.exp(-(((X + 230) / 18) ** 2)) * np.clip((Y - 40) / 60, 0, 1) * np.clip((330 - Y) / 60, 0, 1)
H -= river * 9 * (~inside)
# ruas e praça niveladas (média local) para não ter degrau
flat_mask = ndimage.gaussian_filter(np.maximum(road_1m, plaza_1m), 2.0)
H_blur = ndimage.gaussian_filter(H, 6.0)
H = H * (1 - flat_mask) + H_blur * flat_mask
plaza_level = float(H[world_to_idx(0, 0)])
H = H - plaza_level  # praça em Z = 0 (os NPCs/atores atuais continuam no chão)
# calçada 12 cm acima do asfalto (meio-fio)
H += 0.12 * np.clip(draw_layer(RES, ("asfalto",), sidewalk_only=True) - draw_layer(RES, ("asfalto",)), 0, 1)
# borda externa do Landscape alta (nada de "fim do mundo")
H = np.where(sq > 480, np.maximum(H, 140 + 20 * noise), H)

H = np.clip(H, -60.0, 230.0)
Z_SCALE_M = 512.0  # Landscape com Scale Z = 100: 0..65535 = -256..+256 m
h16 = np.clip(np.round(H / Z_SCALE_M * 65536.0 + 32768.0), 0, 65535).astype(np.uint16)

# ------------------------------------------------------------------ máscara (RGBA 2048)
asph = draw_layer(MASK_RES, ("asfalto",))
walk = np.clip(draw_layer(MASK_RES, ("asfalto",), sidewalk_only=True) - asph, 0, 1)
concrete = np.maximum(walk, disk(MASK_RES, 0, 0, PLAZA_R))
dirt = draw_layer(MASK_RES, ("terra",))
# terra em volta dos prédios com função, das ruínas e ao pé da muralha
for p in PLACES:
    dirt = np.maximum(dirt, disk(MASK_RES, p["x"], p["y"], max(DIMS[p["key"]][:2]) * p["scale"] * 0.5 + 3) * 0.85)
for (rx, ry) in RUINS:
    dirt = np.maximum(dirt, disk(MASK_RES, rx, ry, 14) * 0.9)
ym, xm = np.mgrid[0:MASK_RES, 0:MASK_RES].astype(np.float32)
s = SIZE_M / MASK_RES
Xm, Ym = xm * s - SIZE_M / 2, SIZE_M / 2 - ym * s
sqm = CITY_HALF * ((np.abs(Xm) / CITY_HALF).astype(np.float64) ** 24 + (np.abs(Ym) / CITY_HALF).astype(np.float64) ** 24) ** (1 / 24)
dirt = np.maximum(dirt, np.clip(1 - np.abs(sqm - CITY_HALF) / 8, 0, 1) * 0.8)
dirt = np.maximum(dirt, np.clip((sqm - CITY_HALF - 4) / 30, 0, 1) * 0.55)  # fora: terra com grama rala
toxic = np.exp(-(((Xm + 230) / 12) ** 2)) * np.clip((Ym - 50) / 40, 0, 1) * np.clip((320 - Ym) / 40, 0, 1)
dirt = np.clip(dirt - asph - concrete, 0, 1)
mask = np.stack([asph, concrete, dirt, toxic], -1)
mask = ndimage.gaussian_filter(mask, (1.2, 1.2, 0))
mask8 = np.clip(np.round(mask * 255), 0, 255).astype(np.uint8)

# ------------------------------------------------------------------ saída
out_dir = sys.argv[1] if len(sys.argv) > 1 else "."
os.makedirs(out_dir, exist_ok=True)
Image.fromarray(h16).save(os.path.join(out_dir, "city_height.png"))
h16.astype("<u2").tofile(os.path.join(out_dir, "city_height.r16"))  # o script da Unreal lê a altura daqui
Image.fromarray(mask8, "RGBA").save(os.path.join(out_dir, "city_mask.png"))
layout = {
    "version": 4, "seed": SEED, "units": "m", "landscape": {"res": RES, "size_m": SIZE_M, "z_scale_m": Z_SCALE_M,
                                                         "plaza_level_m": 0.0},
    "city_half_m": CITY_HALF, "plaza_r_m": PLAZA_R, "wall": WALL, "npcs": NPCS, "player_start": PLAYER_START,
    "buildings": PLACES, "houses": houses, "props": props, "ruins": RUINS,
    "roads": [{"name": r["name"], "width": r["width"], "kind": r["kind"], "poly": [[round(a, 2), round(b, 2)] for a, b in r["poly"]]}
              for r in ROADS],
}
with open(os.path.join(out_dir, "city_layout.json"), "w", encoding="utf-8") as fh:
    json.dump(layout, fh, ensure_ascii=False, indent=1)

# prévia
PV = 1400
crop = 470.0  # m mostrados
pv = Image.new("RGB", (PV, PV), (40, 36, 52))
hs = (H - H.min()) / (H.max() - H.min() + 1e-6)
shade = Image.fromarray((hs * 255).astype(np.uint8)).resize((PV, PV))
# recorta o centro
c0 = int(RES / 2 - crop / 2)
hcrop = H[c0:c0 + int(crop), c0:c0 + int(crop)]
gy, gx = np.gradient(hcrop)
light = np.clip(0.75 + (gx - gy) * 0.35, 0.3, 1.2)
mc0 = int(MASK_RES / 2 - crop / 2 * MASK_RES / SIZE_M)
mcs = int(crop * MASK_RES / SIZE_M)
mcrop = mask[mc0:mc0 + mcs, mc0:mc0 + mcs]
mcrop = np.stack([np.asarray(Image.fromarray((mcrop[..., k] * 255).astype(np.uint8)).resize((PV, PV))) for k in range(4)], -1) / 255.0
light_r = np.asarray(Image.fromarray((np.clip(light, 0, 1.2) / 1.2 * 255).astype(np.uint8)).resize((PV, PV))) / 255.0 * 1.2
grass = np.array([70, 120, 95]) / 255.0
cols = {"a": np.array([58, 58, 66]) / 255.0, "c": np.array([170, 165, 160]) / 255.0, "d": np.array([140, 105, 75]) / 255.0,
        "t": np.array([120, 200, 60]) / 255.0}
outside_px = np.asarray(Image.fromarray(((np.clip(sq[c0:c0 + int(crop), c0:c0 + int(crop)] - CITY_HALF - 8, 0, 1)) * 255).astype(np.uint8)).resize((PV, PV))) / 255.0
base = grass * (1 - outside_px[..., None]) + np.array([95, 90, 80]) / 255.0 * outside_px[..., None]
img = base
for ch, key in ((2, "d"), (1, "c"), (0, "a"), (3, "t")):
    w = mcrop[..., ch:ch + 1]
    img = img * (1 - w) + cols[key] * w
img = np.clip(img * light_r[..., None], 0, 1)
pv = Image.fromarray((img * 255).astype(np.uint8))
dr = ImageDraw.Draw(pv)


def P(x, y):
    return ((x + crop / 2) / crop * PV, (crop / 2 - y) / crop * PV)


def rect(x, y, l, w, yaw, fill, outline=(20, 20, 20)):
    c, s_ = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    pts = []
    for dx, dy in ((l / 2, w / 2), (l / 2, -w / 2), (-l / 2, -w / 2), (-l / 2, w / 2)):
        pts.append(P(x + dx * c - dy * s_, y + dx * s_ + dy * c))
    dr.polygon(pts, fill=fill, outline=outline)
    # porta (frente = +X local)
    fx, fy = P(x + c * l / 2, y + s_ * l / 2)
    dr.ellipse([fx - 3, fy - 3, fx + 3, fy + 3], fill=(255, 255, 255))


# muralha
for t in np.arange(-CITY_HALF, CITY_HALF + 1, 2):
    for (x, y) in ((t, CITY_HALF), (t, -CITY_HALF), (CITY_HALF, t), (-CITY_HALF, t)):
        if y == CITY_HALF and abs(x) < WALL["gate"]["width"] / 2:
            continue
        px, py = P(x, y)
        dr.rectangle([px - 3, py - 3, px + 3, py + 3], fill=(60, 50, 70))
gx0, gy0 = P(-WALL["gate"]["width"] / 2, CITY_HALF + 2)
gx1, gy1 = P(WALL["gate"]["width"] / 2, CITY_HALF - 2)
dr.rectangle([gx0, gy0, gx1, gy1], fill=(60, 180, 255))
for h in houses:
    l, w, _ = DIMS[h["key"]]
    rect(h["x"], h["y"], l * h["scale"], w * h["scale"], h["yaw"], (205, 190, 165))
role_col = {"Armeiro": (200, 60, 60), "Bancada": (70, 110, 200), "CasaHeroi": (80, 160, 80), "CasaSaqueada": (80, 160, 80),
            "Bar": (220, 150, 60), "Garagem": (70, 110, 200), "Radio": (220, 150, 60), "Laboratorio": (140, 90, 200),
            "Prefeitura": (220, 150, 60), "Mercado": (220, 150, 60), "Armazem": (80, 160, 80), "Monumento": (240, 220, 120)}
for p in PLACES:
    l, w, _ = DIMS[p["key"]]
    col = role_col.get(p["role"], (190, 180, 170))
    rect(p["x"], p["y"], l * p["scale"], w * p["scale"], p["yaw"], col, outline=(255, 255, 255) if p["explorable"] else (20, 20, 20))
for pr in props:
    px, py = P(pr["x"], pr["y"])
    if pr["key"] == "poste":
        dr.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 220, 120) if pr["light"] else (150, 140, 110))
    elif pr["key"].startswith("arv"):
        dr.ellipse([px - 6, py - 6, px + 6, py + 6], fill=(40, 100, 80))
    elif pr["key"] in ("barril", "gerador", "placa"):
        dr.rectangle([px - 2, py - 2, px + 2, py + 2], fill=(230, 120, 40))
    else:
        dr.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(110, 90, 140))
for name, n in NPCS.items():
    px, py = P(n["x"], n["y"])
    dr.ellipse([px - 6, py - 6, px + 6, py + 6], fill=(255, 60, 200), outline=(255, 255, 255))
    dr.text((px + 8, py - 6), name, fill=(255, 255, 255))
px, py = P(PLAYER_START["x"], PLAYER_START["y"])
dr.polygon([(px, py - 9), (px - 6, py + 6), (px + 6, py + 6)], fill=(255, 255, 0))
for p in PLACES:
    if p["label"] and not p["label"].startswith(("Mercado_1", "Mercado_2", "Armazem_1", "Armazem_2", "Armazem_3", "Armazem_4", "Lab_")):
        px, py = P(p["x"], p["y"])
        dr.text((px + 10, py + 8), p["label"].replace("_", " "), fill=(255, 255, 255))
pv.save(os.path.join(out_dir, "city_preview.png"))
print(f"casas {len(houses)} | props {len(props)} | ruas {len(ROADS)} | postes {sum(1 for p in props if p['key']=='poste')} "
      f"| altura min {H.min():.1f} max {H.max():.1f} m")
