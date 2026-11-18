"""Minimapa, prévia de cima (com zonas e legendas) e máscara de vegetação da Fase 1 v3.

Uso (Python normal com numpy + Pillow; NÃO precisa do Blender):
  python tools/blender/plot_l01_v3.py assets/work/levels/L01
Lê:  l01_preview_v3.npz, l01_layout_v3.json  (gerados por tools/blender/gen_l01_v3.py)
Grava:
  T_L01_Minimap_v3.png    minimapa do jogo (1024 px, norte para cima; importado por tools/unreal/setup_minimap.py)
  l01_map_v3.png          prévia para revisão (2048 px): zonas, rotas, POIs, portões, checkpoints, saltos, itens
  l01_veg_density_v3.png  dicas de vegetação para o agente Densidade (R floresta, G esparso, B deserto; 1 px = 4 m)
"""
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

SRC = sys.argv[1] if len(sys.argv) > 1 else "."
d = np.load(os.path.join(SRC, "l01_preview_v3.npz"), allow_pickle=True)
L = json.load(open(os.path.join(SRC, "l01_layout_v3.json"), encoding="utf-8"))
HALF = L["map_half_cm"] / 100.0
col, H = d["col"], d["H"]


def font(size):
    for f in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "LiberationSans-Bold.ttf"):
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def base_image(S):
    gx, gy = np.gradient(H)
    shade = np.clip(0.82 + (gx - gy) * 0.07, 0.45, 1.2)[..., None]
    img = np.clip(col * shade * 1.08, 0, 1)
    img = (np.transpose(img, (1, 0, 2))[::-1] * 255).astype(np.uint8)
    return Image.fromarray(img).resize((S, S), Image.BILINEAR)


def px_of(S):
    def px(p):
        return ((p[0] + HALF) / (2 * HALF) * S, (HALF - p[1]) / (2 * HALF) * S)
    return px


def ue2b(loc):
    """cm Unreal -> metros Blender (x leste, y norte)."""
    return (loc[0] / 100.0, -loc[1] / 100.0)


def draw_routes(dr, px, S, wide):
    k = S / 1024.0
    for name in sorted(d.files):
        if name.startswith("alt_"):
            pts = [px(p) for p in d[name][::4]]
            dr.line(pts, fill=(60, 40, 25), width=int(7 * k), joint="curve")
            dr.line(pts, fill=(205, 160, 105), width=int(4 * k), joint="curve")
    road = [px(p) for p in d["road"][::4]]
    dr.line(road, fill=(25, 22, 25), width=int(11 * k), joint="curve")
    dr.line(road, fill=(170, 160, 140), width=int(6 * k), joint="curve")
    for name in sorted(d.files):
        if name.startswith("trail_"):
            pts = [px(p) for p in d[name][::3]]
            for i in range(0, len(pts) - 1, 2):
                dr.line([pts[i], pts[i + 1]], fill=(255, 240, 200), width=max(2, int(3 * k)))


S = 1024
im = base_image(S)
dr = ImageDraw.Draw(im)
px = px_of(S)
draw_routes(dr, px, S, False)
# marcos (ícones simples) no minimapa do jogo
for poi in L["pois"]:
    if poi["kind"] in ("landmark", "gas_station", "village", "hive", "bridge", "exit_gate", "camp"):
        c = px(ue2b(poi["loc"]))
        dr.ellipse([c[0] - 6, c[1] - 6, c[0] + 6, c[1] + 6], fill=(255, 210, 60), outline=(40, 20, 10), width=2)
a = np.array(im).astype(float)
yy, xx = np.mgrid[0:S, 0:S]
edge = np.maximum(np.abs(xx - S / 2), np.abs(yy - S / 2)) / (S / 2)
a *= np.clip(1.25 - np.clip((edge - 0.86) / 0.14, 0, 1) * 0.6, 0, 1)[..., None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(SRC, "T_L01_Minimap_v3.png"))

# ------------------------------------------------------------------ prévia grande com legendas
S = 2048
im = base_image(S).convert("RGBA")
ov = Image.new("RGBA", (S, S), (0, 0, 0, 0))
do = ImageDraw.Draw(ov)
px = px_of(S)
m2px = S / (2 * HALF)
ZCOL = {"car": (255, 120, 40, 70), "foot": (60, 170, 255, 80)}
for z in L["zones"]:
    c = px(ue2b(z["center"]))
    r = z["radius_cm"] / 100 * m2px
    do.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=ZCOL[z["mode"]], outline=ZCOL[z["mode"]][:3] + (230,), width=4)
for dz in L["director_zones"]:
    c = px(ue2b(dz["loc"]))
    ex, ey = dz["extent_cm"][0] / 100 * m2px, dz["extent_cm"][1] / 100 * m2px
    colr = (60, 255, 120, 200) if dz["no_spawns"] else (255, 60, 60, 160)
    do.rectangle([c[0] - ex, c[1] - ey, c[0] + ex, c[1] + ey], outline=colr, width=3)
im = Image.alpha_composite(im, ov)
dr = ImageDraw.Draw(im)
draw_routes(dr, px, S, True)
f_big, f_med, f_small = font(34), font(22), font(17)
# saltos
for j in L["jumps"]:
    for key, c_ in (("ramp", (255, 255, 0)), ("landing", (255, 160, 0))):
        c = px(ue2b(j[key]["loc"]))
        dr.rectangle([c[0] - 7, c[1] - 7, c[0] + 7, c[1] + 7], fill=c_, outline=(0, 0, 0), width=2)
    c = px(ue2b(j["ramp"]["loc"]))
    dr.text((c[0] + 10, c[1] - 26), "SALTO", font=f_small, fill=(255, 255, 0), stroke_width=3, stroke_fill=(0, 0, 0))
# portões, barricada
for g in L["gates"]:
    c = px(ue2b(g["loc"]))
    dr.rectangle([c[0] - 10, c[1] - 10, c[0] + 10, c[1] + 10], fill=(200, 0, 200), outline=(255, 255, 255), width=3)
    dr.text((c[0] + 14, c[1] - 12), "PORTÃO " + ("(explosivo)" if g["type"] == "explosive" else "(carro para)"), font=f_small,
            fill=(255, 140, 255), stroke_width=3, stroke_fill=(0, 0, 0))
for b in L["barricades"]:
    c = px(ue2b(b["loc"]))
    dr.rectangle([c[0] - 9, c[1] - 9, c[0] + 9, c[1] + 9], fill=(150, 0, 0), outline=(255, 255, 255), width=3)
    dr.text((c[0] + 14, c[1] - 12), "BARRICADA", font=f_small, fill=(255, 120, 120), stroke_width=3, stroke_fill=(0, 0, 0))
# POIs
for poi in L["pois"]:
    c = px(ue2b(poi["loc"]))
    big = poi["kind"] in ("landmark", "hive", "bridge", "exit_gate")
    r = 9 if big else 6
    dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=(255, 215, 60) if big else (240, 240, 240), outline=(0, 0, 0), width=2)
    if big:
        dr.text((c[0] + 12, c[1] + 2), poi["name"].replace(" (marco)", ""), font=f_small, fill=(255, 230, 120),
                stroke_width=3, stroke_fill=(0, 0, 0))
# checkpoints
for cp in L["checkpoints"]:
    c = px(ue2b(cp["loc"]))
    colr = (0, 220, 255) if cp["stage"] == "DRIVING" else (80, 255, 80)
    dr.polygon([(c[0], c[1] - 12), (c[0] + 10, c[1] + 8), (c[0] - 10, c[1] + 8)], fill=colr, outline=(0, 0, 0))
    dr.text((c[0] - 14, c[1] + 10), cp["label"].replace("CP_", ""), font=f_small, fill=colr, stroke_width=3, stroke_fill=(0, 0, 0))
# itens, baús, inimigos
PCOL = {"AMMO": (255, 220, 0), "HEALTH": (255, 60, 60), "NITRO": (0, 200, 255), "REPAIR": (120, 255, 120),
        "FURY": (255, 0, 120), "WEAPON_MELEE": (200, 120, 255)}
for p in L["pickups"]:
    c = px(ue2b(p["loc"]))
    dr.ellipse([c[0] - 4, c[1] - 4, c[0] + 4, c[1] + 4], fill=PCOL.get(p["type"], (255, 255, 255)), outline=(0, 0, 0))
for ch in L["chests"]:
    c = px(ue2b(ch["loc"]))
    dr.rectangle([c[0] - 6, c[1] - 5, c[0] + 6, c[1] + 5], fill=(255, 170, 0), outline=(0, 0, 0), width=2)
for e in L["enemies"]:
    c = px(ue2b(e["loc"]))
    dr.ellipse([c[0] - 3, c[1] - 3, c[0] + 3, c[1] + 3], fill=(150, 255, 60), outline=(20, 40, 0))
c = px(ue2b(L["vehicle_start"]["loc"]))
dr.rectangle([c[0] - 9, c[1] - 6, c[0] + 9, c[1] + 6], fill=(0, 120, 255), outline=(255, 255, 255), width=2)
dr.text((c[0] + 12, c[1] - 8), "BUGGY", font=f_small, fill=(120, 200, 255), stroke_width=3, stroke_fill=(0, 0, 0))
c = px(ue2b(L["rescue"]["loc"]))
dr.ellipse([c[0] - 10, c[1] - 10, c[0] + 10, c[1] + 10], outline=(255, 50, 50), width=4)
dr.text((c[0] + 12, c[1] - 10), "SOBREVIVENTE", font=f_small, fill=(255, 120, 120), stroke_width=3, stroke_fill=(0, 0, 0))
# nomes das zonas
for z in L["zones"]:
    c = px(ue2b(z["center"]))
    t = f"{z['id']} {z['name']}"
    sub = "CARRO" if z["mode"] == "car" else "A PÉ"
    dr.text((c[0] - 120, c[1] - 40), t, font=f_med, fill=(255, 255, 255), stroke_width=4, stroke_fill=(0, 0, 0))
    dr.text((c[0] - 120, c[1] - 14), sub, font=f_med, fill=(255, 170, 90) if z["mode"] == "car" else (120, 200, 255),
            stroke_width=4, stroke_fill=(0, 0, 0))
# grade de 250 m e legenda
for v in range(-750, 1000, 250):
    a_, _ = px((v, 0))
    dr.line([(a_, 0), (a_, S)], fill=(255, 255, 255), width=1)
    _, b_ = px((0, v))
    dr.line([(0, b_), (S, b_)], fill=(255, 255, 255), width=1)
leg = ["Fase 1 v3: vale aberto (2 x 2 km, grade 250 m, norte para cima)",
       "Laranja = zona de carro | azul = zona a pé | caixa verde = zona segura | caixa vermelha = zona do diretor",
       "Cinza = estrada principal | bege = rotas alternativas de terra | tracejado = trilha a pé",
       "Triângulo ciano/verde = checkpoint (carro/a pé) | roxo = portão | amarelo = salto | laranja = baú | bolinhas = itens/zumbis"]
HEAD, FOOT = 30 * len(leg) + 16, 40
canvas = Image.new("RGB", (S, S + HEAD + FOOT), (0, 0, 0))
canvas.paste(im.convert("RGB"), (0, HEAD))
dc = ImageDraw.Draw(canvas)
for i, t in enumerate(leg):
    dc.text((14, 8 + i * 30), t, font=f_med if i else f_big, fill=(255, 255, 255))
st = L["stats"]
dc.text((14, S + HEAD + 8), f"Estrada {st['road_m']} m | raio mínimo {st['road_min_radius_m']} m | rampa máx {st['road_max_grade'] * 100:.1f}% | "
        f"metros de carro por zona {st['drive_m_per_zone']}", font=f_small, fill=(220, 220, 220))
canvas.save(os.path.join(SRC, "l01_map_v3.png"))

# ------------------------------------------------------------------ máscara de vegetação
veg = d["veg"]
Image.fromarray((np.transpose(veg, (1, 0, 2))[::-1] * 255).astype(np.uint8)).save(os.path.join(SRC, "l01_veg_density_v3.png"))
print("ok:", "T_L01_Minimap_v3.png, l01_map_v3.png, l01_veg_density_v3.png")
