"""Máscaras das decals (A-057): mancha de sangue e queimado de plasma, 512 px, cinza salvo em RGB.

Uso:  python tools/pipeline/gen_fx_textures.py [--out assets/work/vfx/textures]
Requer numpy, scipy e Pillow. Semente fixa. RGB (não "L") para a Unreal importar como cor linear comum.
"""
import argparse
import os

import numpy as np
from PIL import Image
from scipy import ndimage

_ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
_ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "..", "assets", "work", "vfx", "textures"))
OUT = os.path.abspath(_ap.parse_args().out)
os.makedirs(OUT, exist_ok=True)
N = 512; rng = np.random.default_rng(11)
yy, xx = np.mgrid[0:N, 0:N] / N - 0.5
def blob(cx, cy, r):
    return np.clip(1 - np.hypot(xx - cx, yy - cy) / r, 0, 1)
def fbm(scale, oct=4):
    acc = np.zeros((N, N))
    for o in range(oct):
        s = int(scale * 2 ** o); g = rng.random((s + 1, s + 1))
        acc += ndimage.zoom(g, N / s, order=3)[:N, :N] / 2 ** o
    return acc / acc.max()
# Sangue: mancha central irregular + gotas + raios de respingo
m = blob(0, 0, 0.26) ** 0.5
ang = np.arctan2(yy, xx); rad = np.hypot(xx, yy)
rays = np.zeros((N, N))
for i in range(9):
    a = rng.uniform(-np.pi, np.pi); w = rng.uniform(0.04, 0.09); L = rng.uniform(0.3, 0.46)
    d = np.abs(np.angle(np.exp(1j * (ang - a))))
    rays = np.maximum(rays, np.clip(1 - d / w, 0, 1) * np.clip(1 - rad / L, 0, 1) * 1.3)
drops = np.zeros((N, N))
for i in range(28):
    a = rng.uniform(-np.pi, np.pi); r = rng.uniform(0.2, 0.46); s = rng.uniform(0.008, 0.03)
    drops = np.maximum(drops, blob(np.cos(a) * r, np.sin(a) * r, s) ** 0.3)
mask = np.clip(np.maximum(np.maximum(m, rays), drops) + (fbm(6) - 0.5) * 0.6, 0, 1)
mask = (mask > 0.42).astype(float)
mask = ndimage.gaussian_filter(mask, 1.2)
dens = 0.65 + 0.35 * fbm(10)  # escuro no meio, mais claro na borda
img = np.clip(mask * dens, 0, 1)
Image.fromarray((img * 255).astype(np.uint8)).convert("RGB").save(os.path.join(OUT, "T_FX_BloodSplat.png"))
# Queimado: anel escuro irregular, centro mais forte
r2 = rad * (1 + (fbm(5) - 0.5) * 0.5)
sc = np.clip(1 - r2 / 0.42, 0, 1) ** 1.4
sc = np.clip(sc * (0.75 + 0.5 * fbm(14)), 0, 1)
Image.fromarray((sc * 255).astype(np.uint8)).convert("RGB").save(os.path.join(OUT, "T_FX_Scorch.png"))
print("ok")
