"""[A-098] Villa Star v6: cidade de verdade, com malha de ruas, quarteirões, lotes e bairros que destravam.
Pedido do usuário (23/11 noite): "a cidade não é uma cidade, tem casa virada pro nada"; ruas de verdade com quarteirões,
bairros com função e desbloqueio por áreas (na arena 1 só a parte do centro).
Roda fora da Unreal: python gen_city_v6.py <pasta_saida>   (padrão do repo: assets/work/city_v6)
Mesmo Landscape da v5 (505 x 505, origem -25200): só reimporta o heightmap.

Saídas: city_height.png/.r16, city_mask.png (R asfalto, G concreto, B terra, A lama), city_layout.json, city_preview.png.

Planta (metros, x leste, y norte; muralha em +-100):
  ruas: grade com linhas em -84, -42, 0, 42, 84 nos dois sentidos. As duas do meio (x=0, y=0) são avenidas (8 m + calçada
        de 2 m), as outras ruas de 6 m + calçada de 1,5 m; a avenida norte vai até o portão do Kaar. Praça redonda (16 m)
        no cruzamento central com a nave de monumento.
  quarteirões: 16 (4 x 4), cada um com 4 lotes de ~16 x 16 m. Toda casa fica de FRENTE para uma rua (avenida tem
        prioridade), com recuo de 1,5 a 3 m da calçada, quintal no fundo (árvore/arbusto) e jardim na porta.
        Lotes colados na praça viram jardim de bolso.
  bairros (cada um com função e o nível de arena que abre):
    1 Praça Central (centro + 2 quarteirões do portão): Armeiro (Krug), Bar, Bancada (Ix-Vel), Casa do herói, Garagem,
      Jardim da Árvore-Mãe (árvore de melhorias), Rádio de contratos e Quartel de vigia, portão do Kaar.
    2 Mercado Leste: barracas em fileira na avenida, Prefeitura, casas.
    3 Vila Sul (residencial, Casa saqueada) e Armazém (sudeste: contêineres em fileiras, alguns empilhados).
    4 Oficinas Oeste (oficinas com carros em conserto, geradores, barris) e Ruínas do ataque (noroeste).
    5 Laboratório (nordeste, cristal no pátio) e Ferro-velho (sudoeste, carros batidos).
  barricadas: muro de contêineres (3,3 m de altura, o herói não escala) na metade da rua do lado do bairro fechado,
        cobrindo cruzamentos e a faixa até a muralha; um posto (AJRDistrictGate) com placa no cruzamento mais perto
        da praça. Nada de parede invisível.
  regras de colisão: tudo é testado por caixa girada (SAT), não só por raio: casa, prédio, árvore, poste, barricada.
"""
import json
import math
import os
import random
import sys

import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage

SEED = 2312
RES = 505
HALF_M = (RES - 1) / 2.0
MASK_RES = 2048
CITY_HALF = 100.0
PLAZA_R = 16.0
GL = [-84.0, -42.0, 0.0, 42.0, 84.0]   # linhas da grade
EDGES = [-100.0, -42.0, 0.0, 42.0, 100.0]  # células estendidas até a muralha (para as barricadas)
AVE_W, AVE_SW = 8.0, 2.0
ST_W, ST_SW = 6.0, 1.5

rng = random.Random(SEED)

DIMS = {
    "armeiro": (9.0, 7.5, 5.5), "bancada": (8.0, 6.2, 6.6), "casa1": (8.6, 7.1, 9.0), "casa2": (9.0, 8.9, 7.5),
    "casavila": (10.0, 9.1, 8.0), "cabana": (6.0, 5.7, 5.2), "torre_radio": (8.3, 8.2, 25.0), "posto_loja": (10.0, 8.5, 6.7),
    "barraca": (6.5, 5.1, 4.2), "conteiner": (6.0, 4.4, 2.3), "cristal": (8.0, 7.8, 8.0), "nave": (20.0, 10.8, 6.5),
    "arvoremae": (28.6, 35.6, 30.0), "carro1": (4.5, 2.74, 1.75), "carro2": (4.5, 2.74, 1.75), "barricada": (1.94, 3.0, 1.34),
    "poste": (1.4, 1.4, 5.0), "placa": (0.47, 1.33, 2.0), "gerador": (0.82, 1.5, 1.2), "barril": (0.81, 0.76, 0.9),
}


def half_of(c):
    return AVE_W / 2 + AVE_SW if abs(c) < 1e-6 else ST_W / 2 + ST_SW


# ------------------------------------------------------------------ ruas
ROADS = []


def densify(poly, step=2.0):
    out = [poly[0]]
    for (ax, ay), (bx, by) in zip(poly[:-1], poly[1:]):
        n = max(1, int(math.hypot(bx - ax, by - ay) / step))
        for k in range(1, n + 1):
            out.append((ax + (bx - ax) * k / n, ay + (by - ay) * k / n))
    return out


def add_road(name, poly, width, kind="asfalto", sidewalk=0.0):
    ROADS.append({"name": name, "poly": densify(poly), "width": width, "kind": kind, "sidewalk": sidewalk,
                  "a": poly[0], "b": poly[-1]})


for c in GL:
    w, sw = (AVE_W, AVE_SW) if c == 0 else (ST_W, ST_SW)
    top = CITY_HALF - 2 if c == 0 else GL[-1]   # avenida norte vai até o portão
    add_road(f"rua_x{c:+.0f}", [(c, GL[0]), (c, top)], w, sidewalk=sw)
    add_road(f"rua_y{c:+.0f}", [(GL[0], c), (GL[-1], c)], w, sidewalk=sw)


def seg_dist(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy + 1e-9)))
    return math.hypot(px - ax - dx * t, py - ay - dy * t)


def road_clear(x, y):
    """Metros de folga até a borda da calçada/praça (negativo = em cima da rua)."""
    best = math.hypot(x, y) - (PLAZA_R + 1.0)
    for r in ROADS:
        if r["kind"] != "asfalto":
            continue
        d = seg_dist(x, y, *r["a"], *r["b"]) - (r["width"] / 2 + r["sidewalk"])
        best = min(best, d)
    return best


# ------------------------------------------------------------------ caixas giradas (SAT)
FOOT = []  # (cx, cy, hl, hw, yaw_deg, tipo)


def corners(cx, cy, hl, hw, yaw):
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    return [(cx + dx * c - dy * s, cy + dx * s + dy * c) for dx, dy in ((hl, hw), (hl, -hw), (-hl, -hw), (-hl, hw))]


def obb_overlap(a, b, margin=0.0):
    pa = corners(a[0], a[1], a[2] + margin, a[3] + margin, a[4])
    pb = corners(b[0], b[1], b[2], b[3], b[4])
    for poly in (pa, pb):
        for i in range(4):
            x1, y1 = poly[i]
            x2, y2 = poly[(i + 1) % 4]
            nx, ny = -(y2 - y1), x2 - x1
            pa_p = [nx * x + ny * y for x, y in pa]
            pb_p = [nx * x + ny * y for x, y in pb]
            if max(pa_p) < min(pb_p) or max(pb_p) < min(pa_p):
                return False
    return True


def free(box, margin=0.5, kinds=None):
    for f in FOOT:
        if kinds and f[5] not in kinds:
            continue
        if obb_overlap(box, f, margin):
            return False
    return True


def occupy(box):
    FOOT.append(box)


# ------------------------------------------------------------------ bairros
CELL_C = [-63.0, -21.0, 21.0, 63.0]
DISTRICTS = [
    {"id": "Centro", "name": "Praça Central", "tier": 1, "cells": [(1, 1), (1, 2), (2, 1), (2, 2), (1, 3), (2, 3)], "color": (90, 200, 150)},
    {"id": "Mercado", "name": "Mercado Leste", "tier": 2, "cells": [(3, 1), (3, 2)], "color": (230, 170, 70)},
    {"id": "VilaSul", "name": "Vila Sul", "tier": 3, "cells": [(1, 0), (2, 0)], "color": (120, 160, 240)},
    {"id": "Armazem", "name": "Armazém", "tier": 3, "cells": [(3, 0)], "color": (150, 150, 160)},
    {"id": "Oficinas", "name": "Oficinas Oeste", "tier": 4, "cells": [(0, 1), (0, 2)], "color": (230, 110, 70)},
    {"id": "Ruinas", "name": "Ruínas do Ataque", "tier": 4, "cells": [(0, 3)], "color": (140, 90, 120)},
    {"id": "Laboratorio", "name": "Laboratório", "tier": 5, "cells": [(3, 3)], "color": (170, 110, 230)},
    {"id": "FerroVelho", "name": "Ferro-Velho", "tier": 5, "cells": [(0, 0)], "color": (160, 120, 80)},
]
CELL_DIST = {}
for d in DISTRICTS:
    for c in d["cells"]:
        CELL_DIST[c] = d
assert len(CELL_DIST) == 16


def block_rect(i, j):
    return (GL[i] + half_of(GL[i]), GL[i + 1] - half_of(GL[i + 1]), GL[j] + half_of(GL[j]), GL[j + 1] - half_of(GL[j + 1]))


def cell_of(x, y):
    i = min(3, max(0, int((x + 84) // 42))) if -84 <= x <= 84 else (0 if x < 0 else 3)
    j = min(3, max(0, int((y + 84) // 42))) if -84 <= y <= 84 else (0 if y < 0 else 3)
    return (i, j)


# ------------------------------------------------------------------ lotes
PLACES = []
houses = []
props = []


def put_building(key, x, y, yaw, scale, role=None, label=None, explorable=False, folder="Predios", house=False):
    l, w, _ = DIMS[key]
    box = (x, y, l * scale / 2, w * scale / 2, yaw, "bld")
    occupy(box)
    rec = {"key": key, "x": round(x, 2), "y": round(y, 2), "yaw": round(yaw % 360, 1), "scale": round(scale, 3), "role": role,
           "folder": "Casas" if house else folder, "collide": True, "explorable": explorable, "label": label}
    yr = math.radians(yaw)
    door = (x + math.cos(yr) * l * scale / 2, y + math.sin(yr) * l * scale / 2)
    rec["door"] = [round(door[0], 2), round(door[1], 2)]
    (houses if house else PLACES).append(rec)
    return rec


def prop(key, x, y, yaw=None, scale=1.0, folder="Props", collide=False, light=None, z=0.0, align=False, box=None):
    props.append({"key": key, "x": round(x, 2), "y": round(y, 2), "yaw": round((yaw if yaw is not None else rng.uniform(0, 360)) % 360, 1),
                  "scale": scale if isinstance(scale, list) else round(scale, 3), "folder": folder, "collide": collide, "light": light,
                  "z": round(z, 2), "align": align})
    if box:
        occupy(box)


DIRS = {"N": (0, 1), "S": (0, -1), "L": (1, 0), "O": (-1, 0)}


def lot_info(i, j, a, b):
    x0, x1, y0, y1 = block_rect(i, j)
    cx = x0 + (x1 - x0) * (0.25 + 0.5 * a)
    cy = y0 + (y1 - y0) * (0.25 + 0.5 * b)
    # as duas ruas que encostam neste lote (lado de fora do quarteirão)
    side_x = ("L", GL[i + 1]) if a == 1 else ("O", GL[i])
    side_y = ("N", GL[j + 1]) if b == 1 else ("S", GL[j])
    return (x0, x1, y0, y1), (cx, cy), side_x, side_y


def choose_face(i, j, a, b):
    _, _, sx, sy = lot_info(i, j, a, b)
    # avenida primeiro; depois a rua de dentro da cidade (não a do perímetro); depois alterna pelo quarteirão
    if abs(sx[1]) < 1e-6:
        return sx[0]
    if abs(sy[1]) < 1e-6:
        return sy[0]
    if abs(sx[1]) > 80 and abs(sy[1]) < 80:
        return sy[0]
    if abs(sy[1]) > 80 and abs(sx[1]) < 80:
        return sx[0]
    return sx[0] if (i + j) % 2 == 0 else sy[0]


def place_on_lot(key, i, j, a, b, face, scale, setback=None, **kw):
    (x0, x1, y0, y1), (cx, cy), _, _ = lot_info(i, j, a, b)
    fx, fy = DIRS[face]
    l, w, _ = DIMS[key]
    depth = l * scale
    sb = setback if setback is not None else rng.uniform(1.5, 3.0)
    if fx:
        front = x1 if fx > 0 else x0
        x = front - fx * (sb + depth / 2)
        y = cy + rng.uniform(-1.0, 1.0)
    else:
        front = y1 if fy > 0 else y0
        y = front - fy * (sb + depth / 2)
        x = cx + rng.uniform(-1.0, 1.0)
    yaw = math.degrees(math.atan2(fy, fx)) + rng.uniform(-2.0, 2.0)
    return put_building(key, x, y, yaw, scale, **kw)


TAKEN = set()  # (i, j, a, b)
HOUSE_KEYS = [("casa1", 3), ("casa2", 3), ("casavila", 2), ("cabana", 2)]


def weighted_key():
    tot = sum(w for _, w in HOUSE_KEYS)
    r = rng.uniform(0, tot)
    for k, w in HOUSE_KEYS:
        r -= w
        if r <= 0:
            return k
    return HOUSE_KEYS[-1][0]


def fixed(key, cell, lot, face, scale, role, label, explorable=False, folder="Predios"):
    i, j = cell
    a, b = lot
    TAKEN.add((i, j, a, b))
    return place_on_lot(key, i, j, a, b, face, scale, setback=2.0, role=role, label=label, explorable=explorable, folder=folder)


# --- bairro 1: Praça Central
fixed("armeiro", (2, 2), (1, 0), "S", 1.2, "Armeiro", "Armeiro_Krug", True)
fixed("casa2", (2, 2), (0, 1), "O", 1.05, "Bar", "Bar_Conversa", True)
fixed("bancada", (1, 1), (0, 1), "N", 1.2, "Bancada", "Bancada_IxVel", True)
fixed("casa1", (1, 1), (1, 0), "L", 1.05, "CasaHeroi", "Casa_Heroi", True)
fixed("posto_loja", (2, 1), (1, 1), "N", 1.05, "Garagem", "Garagem")
fixed("torre_radio", (1, 3), (1, 1), "L", 0.9, "Radio", "Radio_Contratos")
fixed("cabana", (2, 3), (0, 1), "O", 1.25, "Quartel", "Quartel_Vigia")
# --- 2: Mercado Leste
fixed("casavila", (3, 1), (0, 1), "N", 1.1, "Prefeitura", "Prefeitura")
# --- 3: Vila Sul
fixed("casavila", (2, 0), (0, 1), "O", 1.0, "CasaSaqueada", "Casa_Saqueada", True)
# --- 4: Oficinas
fixed("posto_loja", (0, 2), (1, 0), "S", 1.0, "Oficina", "Oficina_Norte")
fixed("cabana", (0, 1), (1, 1), "N", 1.2, "Oficina", "Oficina_Sul")
# --- 5: Laboratório
fixed("cabana", (3, 3), (0, 0), "S", 1.35, "Laboratorio", "Laboratorio")

# lotes encostados na praça viram jardins; Jardim da Árvore-Mãe ocupa o quarteirão (1,2) inteiro
POCKET = []
for (i, j, a, b) in ((1, 1, 1, 1), (2, 1, 0, 1), (2, 2, 0, 0), (1, 2, 1, 0)):
    TAKEN.add((i, j, a, b))
    POCKET.append(lot_info(i, j, a, b)[1])
for a in (0, 1):
    for b in (0, 1):
        TAKEN.add((1, 2, a, b))
# mercado: metade sul do quarteirão (3,2) é a praça das barracas; armazém, ferro-velho e ruínas sem casas
for a in (0, 1):
    TAKEN.add((3, 2, a, 0))
    for b in (0, 1):
        TAKEN.add((3, 0, a, b))
        TAKEN.add((0, 0, a, b))
        TAKEN.add((0, 3, a, b))
TAKEN.add((3, 3, 1, 1))  # pátio do laboratório (cristal)
TAKEN.add((3, 3, 1, 0))

# casas nos lotes livres
for i in range(4):
    for j in range(4):
        for a in (0, 1):
            for b in (0, 1):
                if (i, j, a, b) in TAKEN:
                    continue
                if CELL_DIST[(i, j)]["id"] in ("Oficinas",) and rng.random() < 0.35:
                    continue  # pátio de oficina
                face = choose_face(i, j, a, b)
                for _try in range(4):
                    key = weighted_key()
                    sc = rng.uniform(1.05, 1.28)
                    n0 = len(FOOT)
                    rec = place_on_lot(key, i, j, a, b, face, sc, house=True)
                    box = FOOT.pop()
                    if free(box, 1.2):
                        FOOT.append(box)
                        break
                    houses.pop()  # não coube: tenta outra casa
                    assert len(FOOT) == n0

# ------------------------------------------------------------------ praça, Árvore-Mãe, mercado, armazém...
put_building("nave", 0, 0, 35.0, 0.6, role="Monumento", label="Monumento_Nave", folder="Praca")
x0, x1, y0, y1 = block_rect(1, 2)
TREE_C = ((x0 + x1) / 2, (y0 + y1) / 2)
put_building("arvoremae", TREE_C[0] - 1.0, TREE_C[1] + 1.0, 200.0, 0.5, role="ArvoreMae", label="Arvore_Mae", folder="Praca")
FOOT[-1] = (FOOT[-1][0], FOOT[-1][1], 3.5, 3.5, FOOT[-1][4], "bld")  # só o tronco bloqueia; a copa é alta
tdir = math.atan2(-TREE_C[1], -TREE_C[0])  # de frente para a praça
SHRINE = {"x": round(TREE_C[0] - 1.0 + math.cos(tdir) * 5.5, 2), "y": round(TREE_C[1] + 1.0 + math.sin(tdir) * 5.5, 2),
          "yaw": round(math.degrees(tdir), 1)}
DIRT_DISKS = []
# caminhos de terra das avenidas até a árvore + canteiros
for (px, py) in ((TREE_C[0], y0 - 1), (x1 + 1, TREE_C[1])):
    DIRT_DISKS.append(((px + TREE_C[0]) / 2, (py + TREE_C[1]) / 2, 2.2))
    for t in np.linspace(0, 1, 9):
        DIRT_DISKS.append((px + (TREE_C[0] - px) * t, py + (TREE_C[1] - py) * t, 1.6))
DIRT_DISKS.append((TREE_C[0], TREE_C[1], 7.5))
for k in range(10):
    ang = 2 * math.pi * k / 10 + 0.3
    x, y = TREE_C[0] + math.cos(ang) * 12.5, TREE_C[1] + math.sin(ang) * 12.5
    if road_clear(x, y) > 2.5 and free((x, y, 1.6, 1.6, 0, "nat"), 0.3):
        prop(rng.choice(["arv1", "arv3", "arv4"]), x, y, None, rng.uniform(0.6, 0.8), "Jardim", True, box=(x, y, 1.6, 1.6, 0, "nat"))
for k in range(14):
    ang = rng.uniform(0, 2 * math.pi)
    r = rng.uniform(8.5, 11)
    x, y = TREE_C[0] + math.cos(ang) * r, TREE_C[1] + math.sin(ang) * r
    if free((x, y, 0.6, 0.6, 0, "nat"), 0.2):
        prop(rng.choice(["flor", "flor2", "arb1", "cogu"]), x, y, None, rng.uniform(0.8, 1.1), "Jardim")

# jardins de bolso perto da praça
for (cx, cy) in POCKET:
    for k in range(3):
        x, y = cx + rng.uniform(-4, 4), cy + rng.uniform(-4, 4)
        if road_clear(x, y) > 2.0 and free((x, y, 1.6, 1.6, 0, "nat"), 0.5):
            prop(rng.choice(["arv1", "arv3", "arv4"]) if k == 0 else rng.choice(["arb1", "arb2", "flor", "flor2"]), x, y, None,
                 rng.uniform(0.6, 0.85) if k == 0 else 1.0, "Jardim", k == 0, box=(x, y, 1.6, 1.6, 0, "nat") if k == 0 else None)

# mercado: 2 fileiras de barracas viradas para a avenida y=0 (calçadão de concreto entre elas)
mx0, mx1, my0, my1 = block_rect(3, 2)
MARKET = (mx0, mx1, my0, my0 + (my1 - my0) * 0.55)
for n, x in enumerate(np.linspace(mx0 + 5, mx1 - 5, 4)):
    for row, (yy, yaw) in enumerate(((my0 + 4.2, -90.0), (my0 + 13.5, -90.0))):
        put_building("barraca", float(x), yy, yaw, 0.95, role="Mercado" if n == 0 and row == 0 else None, label=f"Mercado_{row}{n}", folder="Mercado")
        if rng.random() < 0.7:
            cxp = float(x) + rng.uniform(-2, 2)
            prop("barril", cxp, yy + 3.0, None, 1.0, "Mercado", True)
prop("placa", mx0 + 1.5, my0 + 1.0, -90, 1.2, "Placas", True)

# armazém: contêineres em fileiras alinhadas, alguns empilhados (2o andar em cima de um do 1o)
ax0, ax1, ay0, ay1 = block_rect(3, 0)
for r_, yy in enumerate(np.linspace(ay0 + 5, ay1 - 6, 4)):
    for c_, xx in enumerate(np.linspace(ax0 + 5, ax1 - 5, 4)):
        if (r_, c_) in ((1, 1), (2, 2)):
            continue  # corredor para a empilhadeira
        sc = 1.0
        x, y = float(xx), float(yy)
        put_building("conteiner", x, y, 0.0 + rng.uniform(-1.5, 1.5), sc, role="Armazem" if r_ == c_ == 0 else None,
                     label=f"Armazem_{r_}{c_}", folder="Armazem")
        if rng.random() < 0.35:
            prop("conteiner", x + rng.uniform(-0.2, 0.2), y + rng.uniform(-0.2, 0.2), rng.uniform(-3, 3), 1.0, "Armazem", True,
                 z=DIMS["conteiner"][2])
DIRT_DISKS += [((ax0 + ax1) / 2, (ay0 + ay1) / 2, 16)]
for k in range(5):
    prop(rng.choice(["barril", "gerador"]), ax0 + 2 + k * 1.4, ay1 - 2.0, None, 1.0, "Armazem", True)

# laboratório: cristal no pátio, geradores em volta
lx0, lx1, ly0, ly1 = block_rect(3, 3)
LABC = (lx0 + (lx1 - lx0) * 0.72, ly0 + (ly1 - ly0) * 0.5)
prop("cristal", LABC[0], LABC[1], rng.uniform(0, 360), 0.7, "Laboratorio", True, box=(LABC[0], LABC[1], 2.8, 2.8, 0, "bld"))
for k in range(4):
    ang = math.pi / 2 * k + 0.6
    prop("gerador", LABC[0] + math.cos(ang) * 6, LABC[1] + math.sin(ang) * 6, math.degrees(ang) + 180, 1.0, "Laboratorio", True)
DIRT_DISKS.append((LABC[0], LABC[1], 8))

# ferro-velho e ruínas: carros batidos, entulho por cima dos lotes que eram casas
RUINS = []
fx0, fx1, fy0, fy1 = block_rect(0, 0)
for r_, yy in enumerate(np.linspace(fy0 + 4, fy1 - 4, 5)):
    for c_, xx in enumerate(np.linspace(fx0 + 4, fx1 - 4, 4)):
        if rng.random() < 0.75:
            prop(rng.choice(["carro1", "carro2"]), float(xx) + rng.uniform(-1, 1), float(yy) + rng.uniform(-0.6, 0.6),
                 rng.choice([0, 180]) + rng.uniform(-12, 12), 1.0, "FerroVelho", True, align=True)
            if rng.random() < 0.2:
                prop(rng.choice(["carro1", "carro2"]), float(xx), float(yy), rng.uniform(0, 360), 1.0, "FerroVelho", True, z=1.6)
DIRT_DISKS.append(((fx0 + fx1) / 2, (fy0 + fy1) / 2, 17))
RUINS.append(((fx0 + fx1) / 2, (fy0 + fy1) / 2))
rx0, rx1, ry0, ry1 = block_rect(0, 3)
for a in (0, 1):
    for b in (0, 1):
        cx = rx0 + (rx1 - rx0) * (0.25 + 0.5 * a)
        cy = ry0 + (ry1 - ry0) * (0.25 + 0.5 * b)
        RUINS.append((cx, cy))
        for k in range(rng.randint(4, 6)):
            prop(rng.choice(["pedra3", "pedra2", "tronco", "barricada", "pedra1"]), cx + rng.uniform(-5, 5), cy + rng.uniform(-5, 5), None,
                 rng.uniform(0.8, 1.2), "Ruinas", True, align=True)
        for k in range(rng.randint(2, 3)):
            prop(rng.choice(["ossos", "cogu"]), cx + rng.uniform(-5, 5), cy + rng.uniform(-5, 5), None, 1.0, "Ruinas", False, align=True)
        prop("cristal_peq", cx + rng.uniform(-3, 3), cy + rng.uniform(-3, 3), None, rng.uniform(0.25, 0.35), "Ruinas", True)
        DIRT_DISKS.append((cx, cy, 8))
    prop(rng.choice(["carro1", "carro2"]), rx0 + 6 + a * 18, ry0 + 3, rng.uniform(0, 360), 1.0, "Ruinas", True, align=True)

# oficinas: carros em conserto, geradores, barris no pátio de cada oficina
for p in PLACES:
    if p["role"] != "Oficina" and p["role"] != "Garagem":
        continue
    yr = math.radians(p["yaw"])
    l = DIMS[p["key"]][0] * p["scale"]
    side = math.radians(p["yaw"] + 90)
    bx = p["x"] + math.cos(side) * (DIMS[p["key"]][1] * p["scale"] / 2 + 3.5)
    by = p["y"] + math.sin(side) * (DIMS[p["key"]][1] * p["scale"] / 2 + 3.5)
    box = (bx, by, 2.3, 1.4, p["yaw"] + 90, "prop")
    if free(box, 0.4) and road_clear(bx, by) > 0.5:
        prop(rng.choice(["carro1", "carro2"]), bx, by, p["yaw"] + 90, 1.0, "Oficinas", True, align=True, box=box)
    for k in range(3):
        gx = p["x"] - math.cos(yr) * (l / 2 + 1.2) + math.cos(side) * (k - 1) * 1.3
        gy = p["y"] - math.sin(yr) * (l / 2 + 1.2) + math.sin(side) * (k - 1) * 1.3
        prop(["gerador", "barril", "barril"][k], gx, gy, p["yaw"], 1.0, "Oficinas", True)
    DIRT_DISKS.append((p["x"], p["y"], max(DIMS[p["key"]][:2]) * p["scale"] * 0.5 + 4))

# ------------------------------------------------------------------ barricadas entre bairros
BARRIERS = []
GATES = []
CONT_L, CONT_W, CONT_H = DIMS["conteiner"]
BARRIER_ZS = 3.3 / CONT_H  # 3,3 m: acima do que o herói escala (2,65 m)


def add_barrier_line(axis, line, sign, s0, s1, dist):
    """Contêineres ao longo da linha da grade (axis 'x': linha x=line, correndo em y), do lado `sign`."""
    off = line + sign * (CONT_W / 2 + 0.05)
    n = max(1, int(math.ceil((s1 - s0) / (CONT_L * 0.97))))
    step = (s1 - s0) / n
    for k in range(n):
        s = s0 + step * (k + 0.5)
        if axis == "x":
            x, y, yaw = off, s, 90.0
        else:
            x, y, yaw = s, off, 0.0
        sx = step / CONT_L * 1.03
        box = (x, y, CONT_L * sx / 2, CONT_W / 2, yaw, "bar")
        BARRIERS.append({"district": dist["id"], "tier": dist["tier"], "key": "conteiner", "x": round(x, 2), "y": round(y, 2),
                         "yaw": yaw + rng.choice([0, 180]), "scale": [round(sx, 3), 1.0, round(BARRIER_ZS, 3)]})
        occupy(box)


crossings = {}
for i in range(4):
    for j in range(4):
        A = CELL_DIST[(i, j)]
        for (di, dj) in ((1, 0), (0, 1)):
            ni, nj = i + di, j + dj
            if ni > 3 or nj > 3:
                continue
            B = CELL_DIST[(ni, nj)]
            if A["tier"] == B["tier"]:
                continue
            hi, lo_cell, hi_cell = (B, (i, j), (ni, nj)) if B["tier"] > A["tier"] else (A, (ni, nj), (i, j))
            sign = 1 if (hi_cell[0] - lo_cell[0] + hi_cell[1] - lo_cell[1]) > 0 else -1
            if di:
                line = GL[i + 1]
                s0, s1 = EDGES[j] - 3.0, EDGES[j + 1] + 3.0
                add_barrier_line("x", line, sign, max(s0, -CITY_HALF - 1.0), min(s1, CITY_HALF + 1.0), hi)
                cand = [(line, c) for c in GL if s0 < c < s1]
                normal = (-sign, 0)
            else:
                line = GL[j + 1]
                s0, s1 = EDGES[i] - 3.0, EDGES[i + 1] + 3.0
                add_barrier_line("y", line, sign, max(s0, -CITY_HALF - 1.0), min(s1, CITY_HALF + 1.0), hi)
                cand = [(c, line) for c in GL if s0 < c < s1]
                normal = (0, -sign)
            for (cx, cy) in cand:
                crossings.setdefault(hi["id"], []).append((cx, cy, normal))

for d in DISTRICTS:
    if d["tier"] <= 1:
        continue
    cs = crossings.get(d["id"], [])
    if not cs:
        continue
    cx, cy, (nx, ny) = min(cs, key=lambda c: math.hypot(c[0], c[1]))
    gx, gy = cx + nx * 2.5, cy + ny * 2.5
    GATES.append({"id": d["id"], "name": d["name"], "tier": d["tier"], "x": round(gx, 2), "y": round(gy, 2),
                  "yaw": round(math.degrees(math.atan2(ny, nx)), 1)})

# ------------------------------------------------------------------ jardins, quintais, postes, carros na rua
for h in houses + [p for p in PLACES if p["folder"] == "Predios"]:
    yr = math.radians(h["yaw"])
    l, w, _ = DIMS[h["key"]]
    hl, hw = l * h["scale"] / 2, w * h["scale"] / 2
    c, s = math.cos(yr), math.sin(yr)
    # dois arbustos/flores dos lados da porta
    for side in (-1, 1):
        x = h["x"] + c * (hl + 0.9) - s * side * (hw * 0.6)
        y = h["y"] + s * (hl + 0.9) + c * side * (hw * 0.6)
        if road_clear(x, y) > 0.3 and free((x, y, 0.5, 0.5, 0, "nat"), 0.1, ("bld", "bar")) and rng.random() < 0.8:
            prop(rng.choice(["arb1", "arb2", "arb3", "flor", "flor2"]), x, y, None, rng.uniform(0.7, 0.95), "Jardins")
    # quintal
    x = h["x"] - c * (hl + 3.5) + s * rng.uniform(-1.5, 1.5)
    y = h["y"] - s * (hl + 3.5) + c * rng.uniform(-1.5, 1.5)
    box = (x, y, 1.6, 1.6, 0, "nat")
    if road_clear(x, y) > 2.5 and free(box, 0.6) and max(abs(x), abs(y)) < CITY_HALF - 4:
        if rng.random() < 0.55:
            prop(rng.choice(["arv1", "arv3", "arv4"]), x, y, None, rng.uniform(0.55, 0.8), "Quintais", True, align=True, box=box)
        else:
            prop(rng.choice(["arb1", "arb2", "tronco", "barril"]), x, y, None, rng.uniform(0.8, 1.1), "Quintais", False, align=True)
    # placa nos prédios com função
    if h.get("role") and h["role"] not in ("Monumento", "ArvoreMae"):
        x = h["x"] + c * (hl + 1.6) + s * (hw + 0.6)
        y = h["y"] + s * (hl + 1.6) - c * (hw + 0.6)
        if free((x, y, 0.4, 0.7, h["yaw"], "prop"), 0.1):
            prop("placa", x, y, h["yaw"], 1.2, "Placas", True, box=(x, y, 0.3, 0.7, h["yaw"], "prop"))

# postes nas calçadas a cada ~22 m, alternando lados; luz um sim um não; nada no cruzamento
DOOR_LIGHTS = []
lamp_i = 0
for r in ROADS:
    (ax, ay), (bx, by) = r["a"], r["b"]
    ln = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / ln, (by - ay) / ln
    nx, ny = -uy, ux
    off = r["width"] / 2 + r["sidewalk"] - 0.5
    n = int(ln // 21)
    for k in range(n):
        t = (k + 0.5) * ln / n
        x, y = ax + ux * t, ay + uy * t
        if any(abs((x if abs(ux) > 0.5 else y) - g) < 7.5 for g in GL) or math.hypot(x, y) < PLAZA_R + 5:
            continue
        side = 1 if k % 2 == 0 else -1
        px, py = x + nx * off * side, y + ny * off * side
        box = (px, py, 0.5, 0.5, 0, "prop")
        if not free(box, 0.2) or max(abs(px), abs(py)) > CITY_HALF - 3:
            continue
        lamp_i += 1
        prop("poste", px, py, math.degrees(math.atan2(-ny * side, -nx * side)), 1.0, "Postes", True,
             light=(40.0 if lamp_i % 2 == 0 else None), box=box)
for k in range(8):
    ang = math.radians(k * 45 + 22.5)
    prop("poste", (PLAZA_R - 1.2) * math.cos(ang), (PLAZA_R - 1.2) * math.sin(ang), k * 45 + 22.5 + 180, 1.0, "Postes", True, light=40.0)

# luz quente na porta de cada prédio com função
for p in PLACES:
    if p["folder"] == "Predios" and p.get("role") not in ("Monumento", "ArvoreMae"):
        yr = math.radians(p["yaw"])
        DOOR_LIGHTS.append({"x": round(p["door"][0] + math.cos(yr) * 0.8, 2), "y": round(p["door"][1] + math.sin(yr) * 0.8, 2),
                            "z": 3.2, "cd": 22.0})

# carros batidos estacionados no meio-fio fora do centro (1 em 3 trechos)
for r in ROADS:
    (ax, ay), (bx, by) = r["a"], r["b"]
    ln = math.hypot(bx - ax, by - ay)
    ux, uy = (bx - ax) / ln, (by - ay) / ln
    for k in range(int(ln // 30)):
        if rng.random() > 0.33:
            continue
        t = rng.uniform(0.1, 0.9) * ln
        side = rng.choice([-1, 1])
        x = ax + ux * t - uy * side * (r["width"] / 2 - 1.3)
        y = ay + uy * t + ux * side * (r["width"] / 2 - 1.3)
        if CELL_DIST[cell_of(x, y)]["tier"] == 1 or any(abs((x if abs(ux) > 0.5 else y) - g) < 8 for g in GL):
            continue
        yaw = math.degrees(math.atan2(uy, ux)) + rng.choice([0, 180]) + rng.uniform(-8, 8)
        box = (x, y, 2.3, 1.4, yaw, "prop")
        if free(box, 0.3):
            prop(rng.choice(["carro1", "carro2"]), x, y, yaw, 1.0, "CarrosRua", True, align=True, box=box)

# pedras ao pé da muralha
for k in range(16):
    side = k % 4
    t = rng.uniform(-CITY_HALF + 10, CITY_HALF - 10)
    x, y = [(t, CITY_HALF - 4), (CITY_HALF - 4, t), (t, -CITY_HALF + 4), (-CITY_HALF + 4, t)][side]
    box = (x, y, 1.5, 1.5, 0, "nat")
    if road_clear(x, y) > 2 and free(box, 0.5) and not (side == 0 and abs(t) < 12):
        prop(rng.choice(["pedra2", "pedra1", "arb3"]), x, y, None, rng.uniform(0.8, 1.3), "Muralha", True, align=True, box=box)

# fora da muralha (horizonte)
for k in range(30):
    ang = 2 * math.pi * k / 30 + rng.uniform(-0.05, 0.05)
    r = rng.uniform(150, 190)
    c_, s_ = math.cos(ang), math.sin(ang)
    m = max(abs(c_), abs(s_))
    prop("penhasco", c_ / m * r, s_ / m * r, None, rng.uniform(1.6, 2.6), "Fora", False)
for k in range(70):
    ang = rng.uniform(0, 2 * math.pi)
    r = rng.uniform(122, 235)
    c_, s_ = math.cos(ang), math.sin(ang)
    m = max(abs(c_), abs(s_))
    prop(rng.choice(["arv1", "arv2", "arv3", "arv4", "tentaculo", "cogu"]), c_ / m * r, s_ / m * r, None, rng.uniform(1.0, 1.8), "Fora", False)
for (x, y, key, sc) in ((-185, 150, "arvoremae", 1.3), (200, -140, "arvoremae", 1.1), (175, 190, "cristal", 2.5),
                        (-200, -185, "colmeia", 2.0), (25, 215, "cristal", 1.8)):
    prop(key, x, y, None, sc, "Fora", False)

# ------------------------------------------------------------------ muralha, NPCs, chegada
WALL = {"half": CITY_HALF, "tower_every": 40.0, "gate": {"side": "N", "x": 0.0, "width": 14.0}}
NPCS = {"Krug": None, "IxVel": None, "Kaar": {"x": 0.0, "y": CITY_HALF - 10, "yaw": -90.0}}
for p in PLACES:
    if p["role"] in ("Armeiro", "Bancada"):
        yr = math.radians(p["yaw"])
        NPCS["Krug" if p["role"] == "Armeiro" else "IxVel"] = {
            "x": round(p["door"][0] + math.cos(yr) * 1.6, 2), "y": round(p["door"][1] + math.sin(yr) * 1.6, 2),
            "yaw": round(p["yaw"], 1), "building": p["label"]}
hero = next(p for p in PLACES if p["role"] == "CasaHeroi")
PLAYER_START = {"x": round(hero["door"][0] + 3.0, 2), "y": round(hero["door"][1], 2), "yaw": 90.0}
BIKE = {"x": 2.6, "y": round(hero["door"][1] + 2.0, 2), "yaw": 90.0}

# ------------------------------------------------------------------ rasterização
SIZE_M = RES - 1


def to_px(x, y, res, size_m):
    s = res / size_m
    return ((x + size_m / 2) * s, (size_m / 2 - y) * s)


def draw_layer(res, kinds, extra_width=0.0, sidewalk_only=False):
    im = Image.new("L", (res, res), 0)
    dr = ImageDraw.Draw(im)
    s = res / SIZE_M
    for r in ROADS:
        if r["kind"] not in kinds:
            continue
        w = (r["width"] + (2 * r["sidewalk"] if sidewalk_only else 0) + extra_width) * s
        pts = [to_px(x, y, res, SIZE_M) for x, y in r["poly"]]
        dr.line(pts, fill=255, width=max(1, int(round(w))))
        for (px, py) in (pts[0], pts[-1]):
            rr = w / 2
            dr.rectangle([px - rr, py - rr, px + rr, py + rr], fill=255)  # ponta reta (cruzamento em T limpo)
    return np.asarray(im, dtype=np.float32) / 255.0


def disk(res, x, y, r):
    im = Image.new("L", (res, res), 0)
    dr = ImageDraw.Draw(im)
    s = res / SIZE_M
    cx, cy = to_px(x, y, res, SIZE_M)
    dr.ellipse([cx - r * s, cy - r * s, cx + r * s, cy + r * s], fill=255)
    return np.asarray(im, dtype=np.float32) / 255.0


def world_to_idx(x, y):
    px, py = to_px(x, y, RES, SIZE_M)
    return int(round(py)), int(round(px))


road_1m = draw_layer(RES, ("asfalto",), sidewalk_only=True)
plaza_1m = disk(RES, 0, 0, PLAZA_R + 1)


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


noise = fbm((RES, RES), (96, 40, 14), (1.0, 0.45, 0.15), SEED)
noise_in = fbm((RES, RES), (48, 22, 9), (1.0, 0.5, 0.2), SEED + 3)  # ondulação de dentro da cidade
# distância "quadrada arredondada" ao centro (superelipse) para a muralha
sq = CITY_HALF * ((np.abs(X) / CITY_HALF) ** 24 + (np.abs(Y) / CITY_HALF) ** 24) ** (1 / 24)
H = np.zeros((RES, RES), np.float32)
# [A-096] dentro: relevo de verdade (o v4 era quase plano): morro a nordeste (+5 m), baixada ao sul (-3 m),
# colina a oeste (+3 m) e ondulação de 1 a 2 m; as ruas acompanham o terreno suavizado e cada prédio ganha plataforma
inside = sq <= CITY_HALF + 8
terr = (5.0 * np.clip((X + Y - 40) / 90, 0, 1) ** 1.3 - 3.0 * np.clip((-Y - 25) / 65, 0, 1)
        + 3.0 * np.exp(-(((X + 70) / 28) ** 2 + ((Y - 10) / 34) ** 2)) + 1.6 * noise_in + 0.6 * noise)
H += np.where(inside, terr, 0)
# fora: fosso raso, depois morros que sobem até 60-160 m (horizonte fechado)
d_out = np.clip(sq - (CITY_HALF + 8), 0, None)
moat = -5.0 * np.clip(d_out / 15.0, 0, 1)
hills = np.clip((d_out - 18) / 100, 0, 1) ** 1.5 * (70 + 40 * noise) + np.clip((d_out - 110) / 30, 0, 1) * 30
ridged = (1 - np.abs(fbm((RES, RES), (48, 18), (1.0, 0.5), SEED + 7))) * 14 * np.clip((d_out - 30) / 70, 0, 1)
H += np.where(inside, 0, moat + hills + ridged)
# rio de lama tóxica a noroeste (fora da muralha): vale mais fundo
river = np.exp(-(((X + 135) / 12) ** 2)) * np.clip((Y - 20) / 40, 0, 1) * np.clip((220 - Y) / 40, 0, 1)
H -= river * 9 * (~inside)
# ruas e praça niveladas (média local) para não ter degrau
flat_mask = ndimage.gaussian_filter(np.maximum(road_1m, plaza_1m), 2.0)
H_blur = ndimage.gaussian_filter(H, 6.0)
H = H * (1 - flat_mask) + H_blur * flat_mask
# [A-096] plataforma sob cada prédio/casa: altura média do lote, borda suave de 8 m (nada de casa flutuando de um lado)
pad_w = np.zeros((RES, RES), np.float32)
pad_h = np.zeros((RES, RES), np.float32)
pad_sum = np.zeros((RES, RES), np.float32)
for p in PLACES + houses:
    half_p = max(DIMS[p["key"]][:2]) * p["scale"] * 0.5
    i, j = world_to_idx(p["x"], p["y"])
    r_in = int(half_p + 1.5)
    r_out = r_in + 8
    i0, i1, j0, j1 = max(0, i - r_out), min(RES, i + r_out + 1), max(0, j - r_out), min(RES, j + r_out + 1)
    di, dj = np.mgrid[i0:i1, j0:j1]
    dd = np.hypot(di - i, dj - j)
    lvl = float(H[max(0, i - r_in):i + r_in + 1, max(0, j - r_in):j + r_in + 1].mean())
    t_ = np.clip((r_out - dd) / (r_out - r_in), 0, 1)
    w = t_ * t_ * (3 - 2 * t_)  # smoothstep: sem degrau na borda da plataforma
    pad_h[i0:i1, j0:j1] += w * lvl          # média ponderada: lotes vizinhos se fundem sem degrau
    pad_sum[i0:i1, j0:j1] += w
    pad_w[i0:i1, j0:j1] = np.maximum(pad_w[i0:i1, j0:j1], w)
pad_h = pad_h / np.maximum(pad_sum, 1e-6)
H = H * (1 - pad_w) + pad_h * pad_w
plaza_level = float(H[world_to_idx(0, 0)])
H = H - plaza_level  # praça em Z = 0 (os NPCs/atores atuais continuam no chão)
# calçada 12 cm acima do asfalto (meio-fio)
H += 0.12 * np.clip(draw_layer(RES, ("asfalto",), sidewalk_only=True) - draw_layer(RES, ("asfalto",)), 0, 1)
# borda externa do Landscape alta (nada de "fim do mundo")
H = np.where(sq > 238, np.maximum(H, 100 + 15 * noise), H)

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
    dirt = np.maximum(dirt, disk(MASK_RES, rx, ry, 9) * 0.9)
for (dx_, dy_, dr_) in DIRT_DISKS:  # [A-098] pátios, caminhos do jardim, armazém, ferro-velho
    dirt = np.maximum(dirt, disk(MASK_RES, dx_, dy_, dr_) * 0.9)
# calçadão de concreto do mercado
_mi = Image.new("L", (MASK_RES, MASK_RES), 0)
_md = ImageDraw.Draw(_mi)
_p0, _p1 = to_px(MARKET[0], MARKET[3], MASK_RES, SIZE_M), to_px(MARKET[1], MARKET[2], MASK_RES, SIZE_M)
_md.rectangle([_p0[0], _p0[1], _p1[0], _p1[1]], fill=255)
concrete = np.maximum(concrete, np.asarray(_mi, dtype=np.float32) / 255.0)
ym, xm = np.mgrid[0:MASK_RES, 0:MASK_RES].astype(np.float32)
s = SIZE_M / MASK_RES
Xm, Ym = xm * s - SIZE_M / 2, SIZE_M / 2 - ym * s
sqm = CITY_HALF * ((np.abs(Xm) / CITY_HALF).astype(np.float64) ** 24 + (np.abs(Ym) / CITY_HALF).astype(np.float64) ** 24) ** (1 / 24)
dirt = np.maximum(dirt, np.clip(1 - np.abs(sqm - CITY_HALF) / 8, 0, 1) * 0.8)
dirt = np.maximum(dirt, np.clip((sqm - CITY_HALF - 4) / 30, 0, 1) * 0.55)  # fora: terra com grama rala
toxic = np.exp(-(((Xm + 135) / 8) ** 2)) * np.clip((Ym - 30) / 30, 0, 1) * np.clip((210 - Ym) / 30, 0, 1)
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
    "version": 6, "seed": SEED, "units": "m", "landscape": {"res": RES, "size_m": SIZE_M, "z_scale_m": Z_SCALE_M,
                                                         "plaza_level_m": 0.0},
    "city_half_m": CITY_HALF, "plaza_r_m": PLAZA_R, "wall": WALL, "npcs": NPCS, "player_start": PLAYER_START, "bike": BIKE,
    "buildings": PLACES, "houses": houses, "props": props, "ruins": RUINS,
    "districts": [{"id": d["id"], "name": d["name"], "tier": d["tier"], "cells": d["cells"]} for d in DISTRICTS],
    "barriers": BARRIERS, "gates": GATES, "shrine": SHRINE, "door_lights": DOOR_LIGHTS,
    "roads": [{"name": r["name"], "width": r["width"], "kind": r["kind"], "poly": [[round(a, 2), round(b, 2)] for a, b in r["poly"]]}
              for r in ROADS],
}
with open(os.path.join(out_dir, "city_layout.json"), "w", encoding="utf-8") as fh:
    json.dump(layout, fh, ensure_ascii=False, indent=1)

# prévia
PV = 1400
crop = 250.0  # m mostrados
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
            "Prefeitura": (220, 150, 60), "Mercado": (220, 150, 60), "Armazem": (80, 160, 80), "Monumento": (240, 220, 120),
            "Quartel": (70, 110, 200), "Oficina": (200, 110, 60), "ArvoreMae": (60, 200, 120)}
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
# [A-098] bairros (cor na borda de cada quarteirão), barricadas e postos
for d in DISTRICTS:
    for (ci, cj) in d["cells"]:
        x0_, x1_, y0_, y1_ = EDGES[ci], EDGES[ci + 1], EDGES[cj], EDGES[cj + 1]
        a_, b_ = P(x0_ + 1, y1_ - 1), P(x1_ - 1, y0_ + 1)
        dr.rectangle([a_[0], a_[1], b_[0], b_[1]], outline=d["color"], width=3)
    ci, cj = d["cells"][0]
    tx, ty = P(EDGES[ci] + 3, EDGES[cj + 1] - 3)
    dr.text((tx, ty), f"{d['name']} (arena {d['tier']})", fill=d["color"])
for b_ in BARRIERS:
    rect(b_["x"], b_["y"], DIMS["conteiner"][0] * b_["scale"][0], DIMS["conteiner"][1], b_["yaw"], (200, 70, 50), outline=(90, 20, 20))
for g_ in GATES:
    gx_, gy_ = P(g_["x"], g_["y"])
    dr.ellipse([gx_ - 7, gy_ - 7, gx_ + 7, gy_ + 7], fill=(255, 80, 60), outline=(255, 255, 255))
sx_, sy_ = P(SHRINE["x"], SHRINE["y"])
dr.ellipse([sx_ - 7, sy_ - 7, sx_ + 7, sy_ + 7], fill=(80, 255, 200), outline=(255, 255, 255))
for pr in props:
    if pr["key"] in ("carro1", "carro2"):
        rect(pr["x"], pr["y"], 4.5, 2.7, pr["yaw"], (120, 130, 150))
bx_, by_ = P(BIKE["x"], BIKE["y"])
dr.rectangle([bx_ - 4, by_ - 4, bx_ + 4, by_ + 4], fill=(0, 255, 255))
pv.save(os.path.join(out_dir, "city_preview.png"))
print(f"barricadas {len(BARRIERS)} | postos {len(GATES)} | casas {len(houses)} | props {len(props)} | ruas {len(ROADS)} | postes {sum(1 for p in props if p['key']=='poste')} "
      f"| altura min {H.min():.1f} max {H.max():.1f} m")
