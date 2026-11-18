#!/usr/bin/env python3
"""Texturas do usuário (pasta texture/ com TX_*.png) -> assets/work/textures/user/T_User_<Nome>_D.png + _N.png.

Uso:
  python tools/pipeline/make_user_textures.py <pasta_com_TX_png> [pasta_saida]
  (saída padrão: assets/work/textures/user/)

- Renomeia: TX_Asfalto_2048_seamless.png -> T_User_Asfalto_D.png (cópia; o original não é tocado).
- Confere se a textura emenda (borda esquerda x direita, topo x base). Se a emenda for bem mais forte que a
  variação normal entre colunas vizinhas, corrige misturando com a versão deslocada em meia textura.
- Gera o mapa normal (padrão DirectX, o da Unreal: verde para baixo) a partir de uma altura aproximada
  (luminância suavizada), já repetível (bordas calculadas com a textura enrolada). 1024 x 1024.
- Relatório: <saida>/user_textures.json
Só precisa de numpy e Pillow.
"""
from __future__ import annotations

import json
import os
import re
import sys

import numpy as np
from PIL import Image

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
NORMAL_SIZE = 1024
STRENGTH = 3.0          # força do relevo (o mesmo para todas; ajuste no material com o parâmetro NormalStrength)
SEAM_LIMIT = 2.5        # emenda > 2,5x a diferença média entre colunas vizinhas = emenda visível


def clean_name(fname: str) -> str:
    base = os.path.splitext(fname)[0]
    base = re.sub(r"^TX_", "", base)
    base = re.sub(r"_?2048", "", base, flags=re.I)
    base = re.sub(r"_?seamless", "", base, flags=re.I)
    return base.strip("_")


def seam_ratio(a: np.ndarray) -> tuple[float, float]:
    """(emenda horizontal, emenda vertical) em relação à variação normal entre vizinhos."""
    g = a.astype(np.float32)
    inner_x = np.abs(np.diff(g, axis=1)).mean() + 1e-6
    inner_y = np.abs(np.diff(g, axis=0)).mean() + 1e-6
    sx = np.abs(g[:, 0] - g[:, -1]).mean() / inner_x
    sy = np.abs(g[0, :] - g[-1, :]).mean() / inner_y
    return float(sx), float(sy)


def make_tileable(a: np.ndarray) -> np.ndarray:
    """Mistura com a cópia deslocada em meia textura: no meio fica o original, nas bordas a cópia (contínua)."""
    h, w = a.shape[:2]
    rolled = np.roll(np.roll(a, h // 2, axis=0), w // 2, axis=1).astype(np.float32)
    yy = np.abs(np.linspace(-1, 1, h))[:, None]
    xx = np.abs(np.linspace(-1, 1, w))[None, :]
    wgt = np.clip(1.0 - np.maximum(xx, yy), 0, 1) ** 0.6       # 1 no centro, 0 na borda
    wgt = np.clip(wgt * 2.0, 0, 1)[..., None]
    return (a.astype(np.float32) * wgt + rolled * (1 - wgt)).clip(0, 255).astype(np.uint8)


def blur_wrap(h: np.ndarray, r: int = 2) -> np.ndarray:
    out = h.copy()
    for axis in (0, 1):
        acc = np.zeros_like(out)
        for k in range(-r, r + 1):
            acc += np.roll(out, k, axis=axis)
        out = acc / (2 * r + 1)
    return out


def normal_map(rgb: np.ndarray) -> np.ndarray:
    img = Image.fromarray(rgb).resize((NORMAL_SIZE, NORMAL_SIZE), Image.LANCZOS)
    a = np.asarray(img).astype(np.float32) / 255.0
    h = 0.299 * a[..., 0] + 0.587 * a[..., 1] + 0.114 * a[..., 2]
    h = blur_wrap(h, 1)
    dx = (np.roll(h, -1, axis=1) - np.roll(h, 1, axis=1)) * 0.5
    dy = (np.roll(h, -1, axis=0) - np.roll(h, 1, axis=0)) * 0.5   # linha para baixo
    s = STRENGTH * NORMAL_SIZE / 256.0
    nx, ny, nz = -dx * s, -dy * s, np.ones_like(h)                  # DirectX: verde para baixo
    n = np.stack([nx, ny, nz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255).round().clip(0, 255).astype(np.uint8)


def main() -> None:
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(REPO, "assets", "work", "textures", "user")
    os.makedirs(out, exist_ok=True)
    report = {}
    for f in sorted(os.listdir(src)):
        if not f.lower().endswith(".png") or not f.startswith("TX_"):
            continue
        name = clean_name(f)
        im = Image.open(os.path.join(src, f)).convert("RGB")
        a = np.asarray(im)
        sx, sy = seam_ratio(a)
        fixed = max(sx, sy) > SEAM_LIMIT
        d_path = os.path.join(out, f"T_User_{name}_D.png")
        if fixed:
            a = make_tileable(a)
            Image.fromarray(a).save(d_path, optimize=True)
        else:
            with open(os.path.join(src, f), "rb") as fi, open(d_path, "wb") as fo:   # cópia exata
                fo.write(fi.read())
        Image.fromarray(normal_map(a)).save(os.path.join(out, f"T_User_{name}_N.png"), optimize=True)
        after = seam_ratio(a)
        report[name] = {"source": f, "size": list(im.size), "seam_before": [round(sx, 2), round(sy, 2)],
                        "seam_after": [round(after[0], 2), round(after[1], 2)], "seam_fixed": fixed,
                        "diffuse": os.path.basename(d_path), "normal": f"T_User_{name}_N.png"}
        print(f"{name:16s} {im.size} emenda {sx:.2f}/{sy:.2f} {'CORRIGIDA' if fixed else 'ok'}")
    with open(os.path.join(out, "user_textures.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=1)


if __name__ == "__main__":
    main()
