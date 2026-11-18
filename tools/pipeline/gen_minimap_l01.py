#!/usr/bin/env python3
"""Minimapa v4 da Fase 1 (A-067, item 14): mapa estilizado no tema do HUD v2 (azul-marinho, ciano, lilás).

Uso (Python com numpy + Pillow; não precisa do Blender nem da Unreal):
  python tools/pipeline/gen_minimap_l01.py assets/work/levels/L01
Lê:  l01_preview_v3.npz (relevo, rio, estrada, trilhas, vegetação) e l01_layout_v3.json (POIs, lago, zonas).
Grava:
  T_L01_Minimap_v4.png         2048 px, norte para cima, mesmo enquadramento da v3 (map_half_cm), SEM nomes e com
                               ícones pequenos (o minimapa mostra só ~260 m); tools/unreal/setup_minimap.py importa.
  T_L01_Map_v4.png             2048 px, o mesmo mapa COM nomes e ícones grandes, para o mapa da tecla M.
  T_L01_Minimap_v4_preview.png prévia para revisão: mapa inteiro + recorte do tamanho do minimapa a pé.
Desenha em 4096 px e reduz (bordas suaves).
Estilo: relevo em faixas de cor suaves com sombra e curvas de nível finas; floresta pontilhada; rio e lago
em destaque; estrada creme com contorno escuro, estradas de terra areia, trilhas pontilhadas; ícones redondos
dos lugares importantes com nome; fora da área jogável escurece para o azul do HUD.
"""
from __future__ import annotations

import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

OUT_SIZE = 2048
SIZE = 4096            # desenha em dobro e reduz no fim (antisserrilhado)
INK = (12, 13, 32)
NAVY = (24, 30, 62)
CYAN = (64, 232, 240)
LILAC = (150, 128, 210)
YELLOW = (255, 214, 92)
CREAM = (240, 230, 205)
SAND = (205, 160, 112)
WATER = (52, 150, 220)
WATER_EDGE = (160, 228, 255)
TOXIC = (120, 225, 90)
# faixas de altura (0 = vale, 1 = picos): azul-petróleo -> azul -> lilás -> lilás claro
BANDS = [(0.00, (34, 70, 92)), (0.25, (44, 80, 112)), (0.45, (60, 78, 132)), (0.65, (86, 76, 146)),
         (0.85, (116, 100, 172)), (1.00, (150, 134, 200))]
EDGE_M = 985.0          # parede invisível da borda (o resto escurece)
NAMES = {"Acampamento": "Acampamento", "NaveQueda": "Nave caída", "ArcoPedra": "Arco de pedra", "Posto": "Posto",
         "TorreRadio": "Torre de rádio", "ArvoreMae": "Árvore-mãe", "Ponte": "Ponte", "Colmeia": "Colmeia",
         "Vila": "Vila", "DiscoVoador": "Disco voador", "PortaoNorte": "Saída"}
# tipo de ícone por POI (desenhados com formas simples)
GLYPH = {"Acampamento": "tenda", "NaveQueda": "nave", "ArcoPedra": "arco", "Posto": "bomba", "TorreRadio": "torre",
         "ArvoreMae": "arvore", "Ponte": "ponte", "Colmeia": "colmeia", "Vila": "casa", "DiscoVoador": "disco",
         "PortaoNorte": "portao"}


def font(size, bold=True):
    names = ("DejaVuSans-Bold.ttf", "arialbd.ttf", "LiberationSans-Bold.ttf") if bold else \
            ("DejaVuSans.ttf", "arial.ttf", "LiberationSans-Regular.ttf")
    for f in names:
        try:
            return ImageFont.truetype(f, size)
        except OSError:
            continue
    return ImageFont.load_default()


def band_color(t):
    t = np.clip(t, 0, 1)
    out = np.zeros(t.shape + (3,))
    for (t0, c0), (t1, c1) in zip(BANDS, BANDS[1:]):
        m = (t >= t0) & (t <= t1)
        a = ((t - t0) / (t1 - t0))[m][:, None]
        out[m] = np.array(c0) * (1 - a) + np.array(c1) * a
    return out


def build(src):
    d = np.load(os.path.join(src, "l01_preview_v3.npz"), allow_pickle=True)
    L = json.load(open(os.path.join(src, "l01_layout_v3.json"), encoding="utf-8"))
    half = L["map_half_cm"] / 100.0
    H = d["H"].astype(float)
    n = H.shape[0]
    step = 2 * half / (n - 1)

    def px(p):          # metros Blender (x leste, y norte) -> pixel (norte para cima)
        return ((p[0] + half) / (2 * half) * SIZE, (half - p[1]) / (2 * half) * SIZE)

    def ue(loc):        # cm Unreal -> metros Blender
        return (loc[0] / 100.0, -loc[1] / 100.0)

    # ---- relevo: amplia a grade de 4 m para a imagem ANTES de calcular (curvas de nível sem degraus)
    R = 1024                                                      # resolução do relevo (~2 m por pixel)
    H = np.array(Image.fromarray(H.astype(np.float32), mode="F").resize((R, R), Image.BICUBIC), dtype=float)
    veg_full = np.stack([np.array(Image.fromarray(d["veg"][..., c].astype(np.float32), mode="F").resize((R, R), Image.BILINEAR))
                         for c in range(3)], -1)
    n = R
    step = 2 * half / (n - 1)
    lo, hi = np.percentile(H, 2), np.percentile(H, 99.5)
    t = (H - lo) / (hi - lo)
    t = np.round(t * 14) / 14 * 0.65 + t * 0.35                 # faixas suaves (leitura de mapa)
    base = band_color(t)
    gx, gy = np.gradient(H, step)
    shade = np.clip(1.0 + (-gx * 0.55 + gy * 0.55) * 0.9, 0.62, 1.25)[..., None]
    img = base * shade
    # tom do bioma (floresta mais esverdeada, deserto mais quente), bem leve
    veg = veg_full.astype(float)
    forest, desert = veg[..., 0:1], veg[..., 2:3]
    img = img * (1 - 0.22 * forest) + np.array([26, 92, 96]) * 0.22 * forest
    img = img * (1 - 0.18 * desert) + np.array([128, 86, 98]) * 0.18 * desert
    # curvas de nível a cada 10 m (linha fina mais escura)
    lev = H / 10.0
    edge_c = (np.abs(np.diff(np.floor(lev), axis=0, prepend=np.floor(lev[:1]))) > 0) | \
             (np.abs(np.diff(np.floor(lev), axis=1, prepend=np.floor(lev[:, :1]))) > 0)
    img[edge_c] *= 0.88
    img = np.transpose(img, (1, 0, 2))[::-1]                     # grade (X, Y) -> imagem (linha = norte)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).resize((SIZE, SIZE), Image.BICUBIC)

    # ---- floresta pontilhada (bolinhas escuras onde a densidade é alta)
    rng = np.random.default_rng(67)
    dots = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dd = ImageDraw.Draw(dots)
    fmap = np.transpose(veg[..., 0], (1, 0))[::-1]
    for _ in range(26000):
        u, v = rng.uniform(0, SIZE, 2)
        f = fmap[min(n - 1, int(v / SIZE * n)), min(n - 1, int(u / SIZE * n))]
        if rng.random() < f * 0.9:
            r = rng.uniform(2.2, 4.2)
            dd.ellipse([u - r, v - r, u + r, v + r], fill=(18, 56, 64, 150))
    im = Image.alpha_composite(im.convert("RGBA"), dots)

    ov = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    dr = ImageDraw.Draw(ov)
    k = SIZE / 2000.0      # pixels por metro

    # ---- lago tóxico
    for h in L["hazards"]:
        if h["kind"] == "toxic_lake":
            c = px(ue(h["loc"]))
            rx, ry = h["box_extent_cm"][0] / 100.0 * k, h["box_extent_cm"][1] / 100.0 * k
            dr.ellipse([c[0] - rx - 4, c[1] - ry - 4, c[0] + rx + 4, c[1] + ry + 4], fill=(30, 70, 40, 255))
            dr.ellipse([c[0] - rx, c[1] - ry, c[0] + rx, c[1] + ry], fill=TOXIC + (255,))
            dr.ellipse([c[0] - rx * 0.55, c[1] - ry * 0.55, c[0] + rx * 0.2, c[1] + ry * 0.1], fill=(170, 245, 140, 120))
    # ---- rio
    river = [px(p) for p in d["river"]]
    rw = max(6, int(L.get("river", {}).get("half_width_m", 20) * 2 * k))
    for width, colr in ((rw + 8, WATER_EDGE), (rw, WATER)):
        rr = width / 2
        for (x0, y0) in river[::2]:
            dr.ellipse([x0 - rr, y0 - rr, x0 + rr, y0 + rr], fill=colr + (255,))
    # ---- estradas de terra, estrada principal, trilhas
    for name in sorted(d.files):
        if name.startswith("alt_"):
            pts = [px(p) for p in d[name][::3]]
            dr.line(pts, fill=INK + (255,), width=int(11 * k), joint="curve")
            dr.line(pts, fill=SAND + (255,), width=int(6 * k), joint="curve")
    road = [px(p) for p in d["road"][::3]]
    dr.line(road, fill=INK + (255,), width=int(17 * k), joint="curve")
    dr.line(road, fill=CREAM + (255,), width=int(10 * k), joint="curve")
    for name in sorted(d.files):
        if name.startswith("trail_"):
            pts = [px(p) for p in d[name][::2]]
            for i in range(0, len(pts) - 1, 3):
                dr.line([pts[i], pts[i + 1]], fill=CREAM + (230,), width=max(3, int(4 * k)))
    im = Image.alpha_composite(im, ov)

    # ---- fora da área jogável: escurece até o azul do HUD com borda ciano fina
    yy, xx = np.mgrid[0:SIZE, 0:SIZE]
    mx = np.abs(xx - SIZE / 2) / (SIZE / 2) * half
    my = np.abs(yy - SIZE / 2) / (SIZE / 2) * half
    out = np.clip((np.maximum(mx, my) - (EDGE_M - 25)) / 40.0, 0, 1)[..., None]
    a = np.array(im).astype(float)
    a[..., :3] = a[..., :3] * (1 - 0.8 * out) + np.array(NAVY) * 0.8 * out
    im = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(im)
    e0, e1 = px((-EDGE_M, EDGE_M)), px((EDGE_M, -EDGE_M))
    dr.rounded_rectangle([e0[0], e0[1], e1[0], e1[1]], radius=int(40 * k), outline=CYAN + (110,), width=3)

    return im, L, half, px, ue


def with_places(base, L, px, ue, badge_px, font_px):
    """Copia do mapa com os lugares importantes: ícone redondo e, se font_px > 0, o nome (sem encavalar)."""
    im = base.copy()
    dr = ImageDraw.Draw(im)
    fnt = font(font_px) if font_px > 0 else None
    # os ícones entram primeiro na lista de ocupados: nenhum nome passa por cima de um ícone
    placed = []
    for poi in L["pois"]:
        if poi["key"] in GLYPH:
            c = px(ue(poi["loc"]))
            placed.append((c[0] - badge_px - 6, c[1] - badge_px - 6, c[0] + badge_px + 6, c[1] + badge_px + 6))
    for poi in sorted(L["pois"], key=lambda p: p["loc"][1]):
        if poi["key"] not in GLYPH:
            continue
        c = px(ue(poi["loc"]))
        draw_badge(dr, c, badge_px, GLYPH[poi["key"]])
        if not fnt:
            continue
        label = NAMES[poi["key"]]
        tw = dr.textlength(label, font=fnt)
        th = font_px * 1.15
        # embaixo do ícone; se encavalar com outro nome, tenta em cima, depois à direita
        g = badge_px + 10
        for tx, ty in ((c[0] - tw / 2, c[1] + g), (c[0] - tw / 2, c[1] - g - th), (c[0] + g, c[1] - th / 2),
                       (c[0] - g - tw, c[1] - th / 2), (c[0] + g * 0.6, c[1] + g * 0.6), (c[0] - g * 0.6 - tw, c[1] + g * 0.6),
                       (c[0] + g * 0.6, c[1] - g * 0.6 - th), (c[0] - g * 0.6 - tw, c[1] - g * 0.6 - th)):
            box = (tx - 6, ty - 4, tx + tw + 6, ty + th + 4)
            if not any(box[0] < b[2] and b[0] < box[2] and box[1] < b[3] and b[1] < box[3] for b in placed):
                break
        placed.append(box)
        o = max(2, font_px // 12)
        for ox in (-o, 0, o):
            for oy in (-o, 0, o):
                if ox or oy:
                    dr.text((tx + ox, ty + oy), label, font=fnt, fill=INK)
        dr.text((tx, ty), label, font=fnt, fill=(250, 250, 255))
    return im.resize((OUT_SIZE, OUT_SIZE), Image.LANCZOS)


def draw_badge(dr, c, r, glyph):
    x, y = c
    dr.ellipse([x - r - 4, y - r - 4, x + r + 4, y + r + 4], fill=INK)
    dr.ellipse([x - r, y - r, x + r, y + r], fill=LILAC)
    ri = int(r * 0.8)
    dr.ellipse([x - ri, y - ri, x + ri, y + ri], fill=NAVY)
    s = ri * 0.62
    w = (250, 250, 255)
    if glyph == "tenda":
        dr.polygon([(x - s, y + s * 0.7), (x, y - s), (x + s, y + s * 0.7)], fill=w)
        dr.polygon([(x - s * 0.25, y + s * 0.7), (x, y + s * 0.05), (x + s * 0.25, y + s * 0.7)], fill=NAVY)
    elif glyph == "bomba":
        dr.rectangle([x - s * 0.55, y - s * 0.8, x + s * 0.25, y + s * 0.8], fill=w)
        dr.rectangle([x - s * 0.38, y - s * 0.6, x + s * 0.08, y - s * 0.15], fill=NAVY)
        dr.line([(x + s * 0.25, y - s * 0.4), (x + s * 0.7, y - s * 0.4), (x + s * 0.7, y + s * 0.4)], fill=w, width=max(2, int(s * 0.18)))
    elif glyph == "casa":
        dr.polygon([(x - s, y - s * 0.05), (x, y - s), (x + s, y - s * 0.05)], fill=w)
        dr.rectangle([x - s * 0.7, y - s * 0.05, x + s * 0.7, y + s * 0.8], fill=w)
        dr.rectangle([x - s * 0.18, y + s * 0.25, x + s * 0.18, y + s * 0.8], fill=NAVY)
    elif glyph == "ponte":
        dr.arc([x - s, y - s * 0.6, x + s, y + s * 1.4], 180, 360, fill=w, width=max(2, int(s * 0.22)))
        dr.line([(x - s, y + s * 0.4), (x + s, y + s * 0.4)], fill=w, width=max(2, int(s * 0.22)))
    elif glyph == "torre":
        dr.polygon([(x - s * 0.55, y + s * 0.9), (x, y - s * 0.6), (x + s * 0.55, y + s * 0.9)], outline=w, width=max(2, int(s * 0.15)))
        dr.ellipse([x - s * 0.18, y - s * 0.95, x + s * 0.18, y - s * 0.6], fill=YELLOW)
    elif glyph == "arvore":
        dr.ellipse([x - s * 0.8, y - s, x + s * 0.8, y + s * 0.35], fill=(120, 240, 200))
        dr.rectangle([x - s * 0.15, y + s * 0.2, x + s * 0.15, y + s * 0.9], fill=w)
    elif glyph == "colmeia":
        for i, yy in enumerate((-0.55, 0.0, 0.55)):
            ww = (0.55, 0.85, 0.65)[i]
            dr.ellipse([x - s * ww, y + s * yy - s * 0.3, x + s * ww, y + s * yy + s * 0.3], fill=YELLOW)
    elif glyph == "disco":
        dr.ellipse([x - s, y - s * 0.2, x + s, y + s * 0.35], fill=w)
        dr.ellipse([x - s * 0.45, y - s * 0.6, x + s * 0.45, y + s * 0.1], fill=CYAN)
    elif glyph == "nave":
        dr.polygon([(x - s * 0.9, y + s * 0.5), (x + s * 0.9, y - s * 0.7), (x + s * 0.3, y + s * 0.8)], fill=w)
        dr.ellipse([x - s * 0.25, y - s * 0.95, x + s * 0.25, y - s * 0.45], fill=(255, 140, 60))
    elif glyph == "arco":
        dr.arc([x - s * 0.85, y - s * 0.85, x + s * 0.85, y + s * 1.2], 180, 360, fill=w, width=max(3, int(s * 0.35)))
        dr.line([(x - s * 0.68, y + s * 0.15), (x - s * 0.68, y + s * 0.85)], fill=w, width=max(3, int(s * 0.35)))
        dr.line([(x + s * 0.68, y + s * 0.15), (x + s * 0.68, y + s * 0.85)], fill=w, width=max(3, int(s * 0.35)))
    elif glyph == "portao":
        dr.rectangle([x - s * 0.8, y - s * 0.8, x - s * 0.5, y + s * 0.85], fill=w)
        dr.rectangle([x + s * 0.5, y - s * 0.8, x + s * 0.8, y + s * 0.85], fill=w)
        dr.polygon([(x - s * 0.3, y - s * 0.2), (x + s * 0.3, y), (x - s * 0.3, y + s * 0.2)], fill=YELLOW)


def preview(im, mini, L, half, path):
    """Mapa inteiro (reduzido) + recorte do tamanho que o minimapa a pé mostra (260 m), com um pino de exemplo."""
    W = 1500
    full = im.resize((1000, 1000), Image.LANCZOS)
    S2 = OUT_SIZE
    canvas = Image.new("RGB", (W, 1080), NAVY)
    canvas.paste(full, (20, 60))
    cam = next(p for p in L["pois"] if p["key"] == "Acampamento")["loc"]
    cx = (cam[0] / 100.0 + half) / (2 * half) * S2
    cy = (cam[1] / 100.0 + half) / (2 * half) * S2         # Unreal y (sul) = linha da imagem
    span = 260.0 / (2 * half) * S2
    crop = mini.crop((int(cx - span / 2), int(cy - span / 2), int(cx + span / 2), int(cy + span / 2))).resize((420, 420), Image.LANCZOS)
    mask = Image.new("L", (420, 420), 0)
    ImageDraw.Draw(mask).ellipse([0, 0, 419, 419], fill=255)
    ring = Image.new("RGBA", (440, 440), (0, 0, 0, 0))
    rd = ImageDraw.Draw(ring)
    rd.ellipse([0, 0, 439, 439], fill=(118, 96, 178, 255))
    canvas.paste(ring, (1045, 140), ring)
    canvas.paste(crop, (1055, 150), mask)
    d = ImageDraw.Draw(canvas)
    d.polygon([(1265, 345), (1255, 375), (1275, 375)], fill=CYAN)        # seta do jogador (exemplo)
    f = font(28)
    d.text((20, 15), "Minimapa v4: mapa inteiro (tecla M)", font=f, fill=(250, 250, 255))
    d.text((1045, 95), "Minimapa a pé (260 m), acampamento", font=font(22), fill=(250, 250, 255))
    d.text((1045, 610), "No jogo: N/L/S/O na borda, pino dourado\nda tarefa com ícone, pontos ciano nos\nitens por perto, pontos vermelhos = zumbis.",
           font=font(20, False), fill=(196, 206, 236))
    canvas.save(path)


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    src = argv[0] if argv else "."
    base, L, half, px, ue = build(src)
    k = SIZE / 2000.0
    mini = with_places(base, L, px, ue, int(15 * k), 0).convert("RGB")
    big = with_places(base, L, px, ue, int(30 * k), int(44 * k)).convert("RGB")
    out = os.path.join(src, "T_L01_Minimap_v4.png")
    mini.save(out)
    big.save(os.path.join(src, "T_L01_Map_v4.png"))
    preview(big, mini, L, half, os.path.join(src, "T_L01_Minimap_v4_preview.png"))
    print("ok", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
