"""Gera a textura do minimapa da L01 (vista de cima, norte para cima) a partir do l01_preview.npz.
Uso: python make_minimap.py <l01_preview.npz> <saida.png> [--debug]  (--debug desenha paredes invisíveis)"""
import sys
import numpy as np
from PIL import Image, ImageDraw
src, out = sys.argv[1], sys.argv[2]
debug = "--debug" in sys.argv
d = np.load(src)
col, H = d["col"], d["H"]
HALF = 1000.0
gx, gy = np.gradient(H)
shade = np.clip(0.8 + (gx - gy) * 0.09, 0.45, 1.15)[..., None]
img = np.clip(col * shade * 1.1, 0, 1)
img = (np.transpose(img, (1, 0, 2))[::-1] * 255).astype(np.uint8)
S = 1024
im = Image.fromarray(img).resize((S, S), Image.BILINEAR)
dr = ImageDraw.Draw(im)


def px(p):
    return ((p[0] + HALF) / (2 * HALF) * S, (HALF - p[1]) / (2 * HALF) * S)


road = [px(p) for p in d["road"][::4]]
trail = [px(p) for p in d["trail"][::3]]
dr.line(road, fill=(30, 28, 30), width=9, joint="curve")
dr.line(road, fill=(150, 140, 125), width=5, joint="curve")
for i in range(0, len(trail) - 1, 2):
    dr.line([trail[i], trail[i + 1]], fill=(250, 235, 190), width=4)
for g in d["gaps"]:
    c = px(g); dr.ellipse([c[0] - 7, c[1] - 7, c[0] + 7, c[1] + 7], fill=(20, 10, 10), outline=(255, 170, 40), width=2)
c = px(d["pond"]); dr.ellipse([c[0] - 9, c[1] - 9, c[0] + 9, c[1] + 9], outline=(140, 255, 60), width=3)
c = px(d["arena"]); r = float(d["arena_r"]) / (2 * HALF) * S
dr.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], outline=(220, 40, 40), width=3)
p = px(d["plaza"]); dr.rectangle([p[0] - 6, p[1] - 6, p[0] + 6, p[1] + 6], outline=(40, 140, 240), width=3)
if debug:
    for w in d["walls"]:
        q = px(w); dr.point(q, fill=(255, 0, 255)); dr.ellipse([q[0] - 1.5, q[1] - 1.5, q[0] + 1.5, q[1] + 1.5], fill=(255, 0, 255))
a = np.array(im).astype(float)
yy, xx = np.mgrid[0:S, 0:S]
edge = np.maximum(np.abs(xx - S / 2), np.abs(yy - S / 2)) / (S / 2)
a *= np.clip(1.25 - np.clip((edge - 0.8) / 0.2, 0, 1) * 0.6, 0, 1)[..., None]
Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(out)
print("ok", out)
