"""HUD v2 (estilo "argila alienígena"): recorta as peças das referências do usuário e gera as texturas do HUD.

Entrada : assets/raw/ui_refs/ref_hud_personagem.png, ref_hud_carro.png, ref_weapon_wheel.png
          assets/work/ui/v2/icons_raw/*.png (renders do Blender: tools/blender/render_hud_icons.py)
Saída   : assets/work/ui/v2/T_HUD2_*.png (importadas por tools/unreal/setup_hud_v2.py)
          assets/work/ui/v2/hud_v2_layout.json (retângulos, em pixels da referência)
          unreal/JogoResgate/Source/JogoResgate/UI/JRHudArt.h (os mesmos números para o C++)

O que faz em cada referência:
  * tira os textos de exemplo ("VIDA", "STAMINA", "OBJETIVO"...) ajustando um gradiente na superfície em volta
    (o C++ escreve os textos com a fonte Fredoka);
  * apaga as linhas/mapa/ícones de exemplo de dentro dos painéis;
  * separa as barras: o painel base fica com os segmentos "apagados" e cada barra vira uma textura de
    preenchimento que o C++ recorta pela porcentagem;
  * abre o furo do minimapa (o mapa é desenhado por baixo da moldura);
  * roda de armas: tira os ícones dos 8 setores, desfaz o destaque do setor da direita (espelha o lado
    esquerdo), limpa o disco central e gera, por setor, a máscara e o brilho de destaque.

Dependências: numpy, scipy, opencv-python, pillow.  Uso: python tools/pipeline/make_hud_v2.py
"""
from __future__ import annotations

import json
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REFS = os.path.join(REPO, "assets", "raw", "ui_refs")
OUT = os.path.join(REPO, "assets", "work", "ui", "v2")
ICONS_RAW = os.path.join(OUT, "icons_raw")
HEADER = os.path.join(REPO, "unreal", "JogoResgate", "Source", "JogoResgate", "UI", "JRHudArt.h")
# Painéis exportados 1,5x maiores que a referência (nitidez em 1440p/4K); a roda fica no tamanho original.
PANEL_UPSCALE = 1.5
LAYOUT: dict = {"panels": {}, "wheel": {}, "icons": {}, "misc": {}}


# ====================================================================== utilidades
def load(name):
    return np.array(Image.open(os.path.join(REFS, name)).convert("RGBA")).astype(np.float32)


def save(arr, name, scale=1.0):
    arr = np.clip(arr, 0, 255)
    if scale != 1.0:
        arr = resize_premul(arr, scale)
    os.makedirs(OUT, exist_ok=True)
    Image.fromarray(arr.astype(np.uint8), "RGBA").save(os.path.join(OUT, name + ".png"), optimize=True)
    return arr.shape[1], arr.shape[0]


def resize_premul(arr, k=None, size=None):
    al = arr[..., 3:4] / 255.0
    pm = arr.copy()
    pm[..., :3] *= al
    im = Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), "RGBA")
    if size is None:
        size = (max(1, int(round(arr.shape[1] * k))), max(1, int(round(arr.shape[0] * k))))
    up = np.array(im.resize(size, Image.LANCZOS)).astype(np.float32)
    a2 = np.clip(up[..., 3:4] / 255.0, 1e-4, 1)
    up[..., :3] = np.where(up[..., 3:4] > 0.5, up[..., :3] / a2, 0)
    return np.clip(up, 0, 255)


def rectmask(shape, x0, y0, x1, y1):
    m = np.zeros(shape[:2], bool)
    m[max(0, y0):y1, max(0, x0):x1] = True
    return m


def white_text_mask(a, rect, thr=185, sat=60, grow=3):
    x0, y0, x1, y1 = rect
    rgb = a[..., :3]
    mn = rgb.min(-1)
    mx = rgb.max(-1)
    m = (mn > thr) & ((mx - mn) < sat) & rectmask(a.shape, *rect)
    m = ndimage.binary_dilation(m, iterations=grow) & rectmask(a.shape, x0 - grow, y0 - grow, x1 + grow, y1 + grow)
    return m


def poly_fill(a, hole, sample, deg=2, noise=0.0, seed=1):
    """Troca os pixels de 'hole' por um gradiente suave ajustado nas cores de 'sample'."""
    ys, xs = np.nonzero(sample)
    if len(xs) < 10:
        return a

    def feats(x, y):
        x = x / 1000.0
        y = y / 1000.0
        cols = [np.ones_like(x)]
        for d in range(1, deg + 1):
            for i in range(d + 1):
                cols.append((x ** (d - i)) * (y ** i))
        return np.stack(cols, -1)

    F = feats(xs.astype(np.float64), ys.astype(np.float64))
    hy, hx = np.nonzero(hole)
    G = feats(hx.astype(np.float64), hy.astype(np.float64))
    b = a.copy()
    rng = np.random.default_rng(seed)
    for c in range(3):
        coef, *_ = np.linalg.lstsq(F, a[ys, xs, c].astype(np.float64), rcond=None)
        v = G @ coef
        if noise > 0:
            v = v + rng.normal(0, noise, v.shape)
        b[hy, hx, c] = v
    return b


def text_fill(a, rect, surf_fn, thr=185, grow=3, deg=2, ring=14):
    """Apaga texto branco (com contorno escuro) de uma superfície lisa."""
    m = white_text_mask(a, rect, thr=thr, grow=grow)
    surf0 = surf_fn(a[..., 0], a[..., 1], a[..., 2])
    near = ndimage.binary_dilation(m, iterations=5) & rectmask(a.shape, rect[0] - 6, rect[1] - 6, rect[2] + 6, rect[3] + 6)
    m = m | (near & ~surf0)
    m = ndimage.binary_closing(m, iterations=2) & near
    ringm = ndimage.binary_dilation(m, iterations=ring) & ~ndimage.binary_dilation(m, iterations=1)
    sample = ringm & surf0
    b = poly_fill(a, m, sample, deg=deg)
    soft = cv2.GaussianBlur(m.astype(np.float32), (0, 0), 1.2)
    bl = cv2.GaussianBlur(b[..., :3], (0, 0), 1.0)
    edge = (soft > 0.05) & (soft < 0.95)
    b[edge, :3] = bl[edge]
    return b


def column_fill(a, x_src, x0, x1, y0, y1, feather=3):
    """Pílula de título: copia uma coluna limpa (degradê vertical) por cima do texto."""
    out = a.copy()
    col = a[y0:y1, x_src:x_src + 3].mean(1)
    for x in range(x0, x1):
        w = min(1.0, (x - x0 + 1) / feather, (x1 - x) / feather)
        out[y0:y1, x, :3] = out[y0:y1, x, :3] * (1 - w) + col[:, :3] * w
    return out


def area_fill(a, hole, sample_region, seed=2, noise=1.6, deg=2):
    """Preenche uma área grande (ex.: miolo azul-marinho) com gradiente + grão leve e emenda suave."""
    sample = sample_region & ~ndimage.binary_dilation(hole, iterations=2)
    fit = poly_fill(a, hole, sample, deg=deg)
    H, W = a.shape[:2]
    rng = np.random.default_rng(seed)
    grain = cv2.GaussianBlur(rng.normal(0, noise, (H, W)).astype(np.float32), (0, 0), 1.3)[..., None]
    soft = cv2.GaussianBlur(hole.astype(np.float32), (0, 0), 1.6)[..., None]
    soft = np.clip(soft * 1.4, 0, 1)
    out = a.copy()
    out[..., :3] = a[..., :3] * (1 - soft) + (fit[..., :3] + grain) * soft
    return out


def comp_boxes(mask, min_area=150):
    lab, n = ndimage.label(mask)
    sl = ndimage.find_objects(lab)
    keep = np.zeros_like(mask)
    boxes = []
    for i, s in enumerate(sl):
        if s is None:
            continue
        if (lab[s] == i + 1).sum() > min_area:
            keep |= lab == i + 1
            boxes.append([int(s[1].start), int(s[0].start), int(s[1].stop), int(s[0].stop)])
    boxes.sort()
    return keep, boxes


def dim_segments(a, m, k=0.62, mul=0.62):
    """Segmentos de barra "apagados": mistura com a cor da canaleta e escurece (o brilho volta pelo C++)."""
    soft = cv2.GaussianBlur(ndimage.binary_dilation(m, iterations=2).astype(np.float32), (0, 0), 0.9)
    ring = ndimage.binary_dilation(m, iterations=5) & ~ndimage.binary_dilation(m, iterations=2)
    trough = a[ring, :3].mean(0)
    rgb = a[..., :3]
    dark = (rgb * (1 - k) + trough * k) * mul
    out = a.copy()
    out[..., :3] = rgb * (1 - soft[..., None]) + dark * soft[..., None]
    return out


def fill_layer(a, m, rect):
    """Textura de preenchimento: só os pixels da barra (alfa = máscara suave), recortada no retângulo."""
    x0, y0, x1, y1 = rect
    soft = cv2.GaussianBlur(ndimage.binary_dilation(m, iterations=1).astype(np.float32), (0, 0), 0.8)
    f = a.copy()
    f[..., 3] = np.minimum(f[..., 3], soft * 255)
    return f[y0:y1, x0:x1]


def circle_hole(a, cx, cy, r, shadow=10, shadow_alpha=0.75, color=(10, 12, 30)):
    """Furo redondo com sombra interna (a moldura "pesa" sobre o mapa)."""
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(xx - cx, yy - cy)
    return hole_from_dist(a, r - d, shadow, shadow_alpha, color)


def hole_from_dist(a, inside_dist, shadow, shadow_alpha, color):
    """inside_dist > 0 dentro do furo (distância até a borda)."""
    out = a.copy()
    inside = inside_dist > 0
    t = np.clip(inside_dist / float(shadow), 0, 1)
    sh = shadow_alpha * (1 - t) ** 1.7
    edge_aa = np.clip(inside_dist, 0, 1)  # 1 px de suavização na borda do furo
    keep = (1 - edge_aa)
    al = out[..., 3] / 255.0
    new_a = np.where(inside, np.maximum(keep * al, sh), al)
    col = np.array(color, np.float32)
    mixw = np.where(inside, 1 - keep, 0)[..., None]
    out[..., :3] = out[..., :3] * (1 - mixw) + col * mixw
    out[..., 3] = new_a * 255
    return out


def key_alpha(crop, bg, lo=18, hi=60):
    """Tira o fundo azul-marinho de um recorte: alfa pela distância de cor até o fundo."""
    d = np.sqrt(((crop[..., :3] - np.array(bg, np.float32)) ** 2).sum(-1))
    al = np.clip((d - lo) / (hi - lo), 0, 1)
    out = crop.copy()
    out[..., 3] = al * 255
    return out


def add_outline(arr, px=4, color=(16, 14, 34), shadow=(3, 5), shadow_alpha=0.45, blur=1.0):
    """Contorno escuro + sombra deslocada (padrão dos ícones das referências)."""
    al = arr[..., 3] / 255.0
    pad = px + max(abs(shadow[0]), abs(shadow[1])) + 4
    H, W = al.shape
    big = np.zeros((H + 2 * pad, W + 2 * pad, 4), np.float32)
    big[pad:pad + H, pad:pad + W] = arr
    alb = big[..., 3] / 255.0
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * px + 1, 2 * px + 1))
    dil = cv2.dilate(alb, k)
    dil = cv2.GaussianBlur(dil, (0, 0), blur)
    sh = np.roll(np.roll(dil, shadow[1], 0), shadow[0], 1)
    sh = cv2.GaussianBlur(sh, (0, 0), 2.0) * shadow_alpha
    out = np.zeros_like(big)
    # sombra
    out[..., :3] = np.array(color, np.float32)
    out[..., 3] = sh * 255
    # contorno
    oa = dil
    out = over(out, np.dstack([np.broadcast_to(np.array(color, np.float32), alb.shape + (3,)), oa * 255]))
    out = over(out, big)
    return out


def over(dst, src):
    sa = src[..., 3:4] / 255.0
    da = dst[..., 3:4] / 255.0
    oa = sa + da * (1 - sa)
    oc = (src[..., :3] * sa + dst[..., :3] * da * (1 - sa)) / np.clip(oa, 1e-5, None)
    return np.concatenate([oc, oa * 255], -1)


def trim(arr, pad=2):
    ys, xs = np.nonzero(arr[..., 3] > 3)
    if len(xs) == 0:
        return arr
    return arr[max(0, ys.min() - pad):ys.max() + 1 + pad, max(0, xs.min() - pad):xs.max() + 1 + pad]


def square(arr, size):
    """Centraliza num quadrado com margem e reduz para 'size'."""
    h, w = arr.shape[:2]
    s = int(max(h, w) * 1.04)
    big = np.zeros((s, s, 4), np.float32)
    y0 = (s - h) // 2
    x0 = (s - w) // 2
    big[y0:y0 + h, x0:x0 + w] = arr
    return resize_premul(big, size=(size, size))


def rect_local(rect, origin):
    return [rect[0] - origin[0], rect[1] - origin[1], rect[2] - rect[0], rect[3] - rect[1]]


def panel(name, arr, crop, extra):
    x0, y0, x1, y1 = crop
    piece = arr[y0:y1, x0:x1]
    save(piece, "T_HUD2_" + name, PANEL_UPSCALE)
    entry = {"size": [x1 - x0, y1 - y0]}
    entry.update(extra)
    LAYOUT["panels"][name] = entry


def is_red(r, g, b):
    return (r > 140) & (g < 125) & (r - b > 55)


def is_green(r, g, b):
    return (g > 120) & (b < 95) & (g - b > 55)


def is_purple(r, g, b):
    return (b > 150) & (r > 110) & (g < 120) & (b - g > 60)


def is_dark(r, g, b):
    return (r + g + b) < 330


# ====================================================================== HUD a pé
def hero():
    a = load("ref_hud_personagem.png")
    # ---- objetivo: tira o texto da pílula e as linhas de exemplo (o losango fica: é o marcador)
    a = column_fill(a, 346, 112, 344, 27, 76)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    lines = (r > 80) & (b > 120) & rectmask(a.shape, 108, 110, 395, 170)
    lines = ndimage.binary_dilation(lines, iterations=4) & rectmask(a.shape, 104, 104, 399, 174)
    body = rectmask(a.shape, 60, 95, 420, 185) & is_dark(r, g, b) & (b < 110)
    a = area_fill(a, lines, body, seed=4)
    crop = (8, 8, 462, 255)
    panel("ObjHero", a, crop, {
        "title": rect_local((122, 26, 352, 74), crop[:2]),
        "body": rect_local((112, 100, 396, 176), crop[:2]),
        "marker": rect_local((52, 104, 100, 152), crop[:2]),
    })

    # ---- minimapa: tira o texto e abre o furo redondo
    a = load("ref_hud_personagem.png")
    a = column_fill(a, 1437, 1438, 1612, 20, 68)
    cx, cy, R = 1486.8, 194.5, 112.0
    a = circle_hole(a, cx, cy, R)
    crop = (1318, 8, 1663, 344)
    panel("MapHero", a, crop, {
        "title": rect_local((1432, 18, 1618, 72), crop[:2]),
        "circle": [cx - crop[0], cy - crop[1], R + 3.0],
        "ellipse": [cx - crop[0], cy - crop[1], R + 3.0, R + 3.0],
    })

    # ---- painel de baixo: VIDA (vermelha) e FÚRIA (verde: era STAMINA)
    a = load("ref_hud_personagem.png")
    a = text_fill(a, (258, 735, 345, 776), is_red)
    a = text_fill(a, (255, 826, 395, 866), is_green)
    src = a.copy()
    segR, bR = comp_boxes(rectmask(a.shape, 258, 772, 612, 818) & (a[..., 0] > 225) & (a[..., 1] > 105))
    segG, bG = comp_boxes(rectmask(a.shape, 262, 856, 600, 908) & (a[..., 1] > 205) & (a[..., 0] > 150))
    base = dim_segments(a, segR)
    base = dim_segments(base, segG)
    crop = (6, 675, 661, 933)
    rectR = (258, 768, 614, 820)
    rectG = (260, 850, 600, 910)
    fR = fill_layer(src, segR, rectR)
    fG = fill_layer(src, segG, rectG)
    save(fR, "T_HUD2_BotHero_FillA", PANEL_UPSCALE)
    save(fG, "T_HUD2_BotHero_FillB", PANEL_UPSCALE)
    panel("BotHero", base, crop, {
        "ring": [103.1 - crop[0], 815.5 - crop[1], 66.0],
        "barA": {"rect": rect_local(rectR, crop[:2]), "segments": [rect_local(bx, crop[:2]) for bx in bR],
                 "label": rect_local((262, 736, 360, 774), crop[:2]), "value": rect_local((470, 734, 600, 772), crop[:2]),
                 "icon": rect_local((200, 728, 250, 782), crop[:2])},
        "barB": {"rect": rect_local(rectG, crop[:2]), "segments": [rect_local(bx, crop[:2]) for bx in bG],
                 "label": rect_local((262, 826, 400, 864), crop[:2]), "value": rect_local((440, 812, 590, 850), crop[:2]),
                 "icon": rect_local((200, 815, 250, 870), crop[:2])},
    })
    return src


def weapon_card(hero_src):
    """Cartão da arma (canto inferior direito): o painel de baixo do herói espelhado, sem barras e sem o boneco."""
    a = hero_src.copy()
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    sat = a[..., :3].max(-1) - a[..., :3].min(-1)
    rim = (b > 100) & (r > 45) & (r < 160) & (g > 55) & (g < 160) & (b - r > 15) & (b - r < 100) & (sat < 100)
    cyan = (g > 150) & (b > 150) & (r < 140)
    purple = (b > 150) & (r > 110) & (g < 130)
    wall = rim | cyan | purple | (a[..., 3] < 128)
    free = ndimage.binary_opening(~wall & rectmask(a.shape, 180, 700, 650, 930), iterations=1)
    lab, _ = ndimage.label(free)
    comp = ndimage.binary_fill_holes(ndimage.binary_closing(lab == lab[840, 450], iterations=3))
    ext = comp | (rectmask(a.shape, 150, 700, 182, 930) & ~wall)
    dist = ndimage.distance_transform_edt(ext).astype(np.float32)
    navy_px = comp & (r + g + b < 200) & (b < 110) & ~((r - b) > 30) & ~((g - b) > 30)
    c0 = np.median(a[navy_px, :3], 0)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    shade = 0.62 + 0.38 * (1 - np.exp(-dist / 9.0))
    vgrad = 1.06 - 0.12 * np.clip((yy - 720) / 190.0, 0, 1)
    rng = np.random.default_rng(7)
    grain = cv2.GaussianBlur(rng.normal(0, 1.8, (H, W)).astype(np.float32), (0, 0), 1.4)
    col = c0[None, None, :] * (shade * vgrad)[..., None] + grain[..., None]
    w = cv2.GaussianBlur(comp.astype(np.float32), (0, 0), 1.0)
    w = np.minimum(w, np.clip((xx - 180) / 10.0, 0, 1))
    a[..., :3] = a[..., :3] * (1 - w[..., None]) + col * w[..., None]
    # sobras vermelhas/verdes entre o anel e o miolo
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    left = ((r - b > 30) | (g - b > 30)) & rectmask(a.shape, 165, 700, 270, 930)
    left = ndimage.binary_dilation(left, iterations=3) & rectmask(a.shape, 165, 700, 270, 930) & ~cyan
    a = area_fill(a, left, rectmask(a.shape, 150, 700, 280, 930) & ~left & (r + g + b < 200), seed=9)
    # boneco correndo: some do anel
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(xx - 103.1, yy - 815.5)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    disc_in = d < 63
    fit = poly_fill(a, disc_in, disc_in & ((r + g + b) < 250) & (b < 140), deg=2)
    diff = np.abs(a[..., :3] - fit[..., :3]).sum(-1)
    fig = ndimage.binary_dilation((diff > 30) & disc_in, iterations=4) & (d < 64)
    a = area_fill(a, fig, disc_in & ~fig, seed=8)
    crop = (6, 675, 661, 933)
    piece = a[crop[1]:crop[3], crop[0]:crop[2]][:, ::-1].copy()
    w = crop[2] - crop[0]
    save(piece, "T_HUD2_Weapon", PANEL_UPSCALE)
    LAYOUT["panels"]["Weapon"] = {
        "size": [w, crop[3] - crop[1]],
        "ring": [w - (103.1 - crop[0]), 815.5 - crop[1], 66.0],
        # área útil (espelhada): nome, munição, barra do pente
        "body": [w - (600 - crop[0]), 728 - crop[1], 600 - 250, 905 - 728],
    }
    return a


def badge(hero_clean):
    """Anel redondo do painel (selo para cura, progresso e itens rápidos)."""
    a = hero_clean
    cx, cy, R = 103.1, 815.5, 92.0
    x0, y0 = int(cx - R), int(cy - R)
    piece = a[y0:y0 + int(2 * R), x0:x0 + int(2 * R)].copy()
    H, W = piece.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    d = np.hypot(xx - (cx - x0), yy - (cy - y0))
    al = np.clip((84.0 - d) / 2.0, 0, 1)
    piece[..., 3] = np.minimum(piece[..., 3], al * 255)
    save(piece, "T_HUD2_Badge", 1.0)
    LAYOUT["misc"]["Badge"] = {"size": [W, H], "inner": 66.0 / (2 * R) * 2}


# ====================================================================== HUD do carro
def car():
    a = load("ref_hud_carro.png")
    a = column_fill(a, 402, 132, 401, 33, 88)
    crop = (15, 18, 502, 246)
    panel("ObjCar", a, crop, {
        "title": rect_local((140, 30, 405, 86), crop[:2]),
        "body": rect_local((80, 112, 430, 210), crop[:2]),
        "marker": rect_local((38, 168, 84, 214), crop[:2]),
    })

    a = load("ref_hud_carro.png")
    a = column_fill(a, 1366, 1370, 1556, 20, 66)
    # furo oval: tudo que não é moldura, a partir do centro
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    frame = ((r > 95) & (g > 90) & (b > 120) & (g - r < 25) & (np.abs(r - g) < 40)) | (a[..., 3] < 128)
    frame |= (r > 100) & (b > 160) & (g < 120)  # cristais
    frame |= (g > 170) & (b > 170) & (r < 120) & ~rectmask(a.shape, 1310, 90, 1625, 330)
    region = rectmask(a.shape, 1270, 75, 1650, 360)
    free = ~frame & region
    lab, _ = ndimage.label(free)
    inside = lab == lab[215, 1465]
    inside = ndimage.binary_fill_holes(ndimage.binary_closing(inside, iterations=4))
    inside = ndimage.binary_opening(inside, iterations=3)
    H, W = a.shape[:2]
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    ell = ((xx - 1466) / 170.0) ** 2 + ((yy - 200) / 126.0) ** 2 < 1.0
    inside = (inside & ell) | (((xx - 1466) / 150.0) ** 2 + ((yy - 200) / 108.0) ** 2 < 1.0)
    dist = ndimage.distance_transform_edt(inside).astype(np.float32)
    ecx, ecy, erx, ery = 1466.0, 200.0, 168.0, 124.0
    a = hole_from_dist(a, dist - 1.0, 12, 0.75, (10, 12, 30))
    crop = (1267, 11, 1654, 361)
    panel("MapCar", a, crop, {
        "title": rect_local((1365, 14, 1560, 70), crop[:2]),
        "circle": [ecx - crop[0], ecy - crop[1], max(erx, ery) + 4.0],
        "ellipse": [ecx - crop[0], ecy - crop[1], erx + 5.0, ery + 5.0],
    })

    a = load("ref_hud_carro.png")
    a = text_fill(a, (255, 690, 425, 728), is_red, thr=175)
    a = text_fill(a, (282, 772, 395, 808), is_green, thr=175)
    a = text_fill(a, (275, 850, 357, 888), is_purple, thr=175)
    src = a.copy()
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    bars = {}
    specs = [("A", (258, 724, 616, 772), is_red), ("B", (282, 795, 602, 845), is_green), ("C", (262, 862, 578, 914), is_purple)]
    base = a.copy()
    crop = (6, 634, 707, 936)
    for key, rc, fn in specs:
        m = rectmask(a.shape, *rc) & fn(r, g, b)
        lab, n = ndimage.label(m)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        m = lab == (np.argmax(sizes) + 1)
        ys, xs = np.nonzero(m)
        base = dim_segments(base, m, k=0.55, mul=0.55)
        f = fill_layer(src, m, rc)
        save(f, f"T_HUD2_BotCar_Fill{key}", PANEL_UPSCALE)
        bars[key] = {"rect": rect_local(rc, crop[:2]), "span": [int(xs.min()) - crop[0], int(xs.max()) - crop[0]]}
    bars["A"].update({"label": rect_local((256, 690, 440, 728), crop[:2]), "value": rect_local((470, 686, 610, 722), crop[:2])})
    bars["B"].update({"label": rect_local((283, 772, 420, 808), crop[:2]), "value": rect_local((460, 762, 600, 798), crop[:2])})
    bars["C"].update({"label": rect_local((276, 850, 380, 888), crop[:2]), "value": rect_local((430, 840, 570, 876), crop[:2])})
    entry = {"ring": [108.9 - crop[0], 810.7 - crop[1], 66.0], "speed": rect_local((640, 760, 700, 880), crop[:2])}
    entry.update({"bar" + k: v for k, v in bars.items()})
    panel("BotCar", base, crop, entry)


# ====================================================================== roda
def wheel():
    a = load("ref_weapon_wheel.png")
    orig = a.copy()
    H, W = a.shape[:2]
    cx, cy = 627.0, 602.0
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    rad = np.hypot(xx - cx, yy - cy)
    ang = (np.degrees(np.arctan2(xx - cx, -(yy - cy))) + 360) % 360
    d90 = np.minimum(np.abs(ang - 90), 360 - np.abs(ang - 90))
    # ---- 1) setor da direita (estava destacado): espelha o lado esquerdo
    mir0 = a[:, ::-1].copy()
    base_shift = int(round(2 * cx - (W - 1)))

    def mirror(sh, dy):
        return np.roll(np.roll(mir0, base_shift + sh, axis=1), dy, axis=0)

    zone = (((ang > 62) & (ang < 78)) | ((ang > 102) & (ang < 118))) & (rad > 205) & (rad < 262)
    best = None
    for sh in range(-20, 1):
        for dy in range(-6, 7):
            e = np.abs(mirror(sh, dy)[zone, :3] - a[zone, :3]).mean()
            if best is None or e < best[0]:
                best = (e, sh, dy)
    mc = mirror(0, 0)
    mr = mirror(best[1], best[2])
    regC = (d90 < 28) & (rad > 283) & (rad < 640)
    regR = (d90 < 24) & (rad > 200) & (rad <= 283)
    sC = cv2.GaussianBlur(regC.astype(np.float32), (0, 0), 2.5)[..., None]
    sR = cv2.GaussianBlur(regR.astype(np.float32), (0, 0), 2.5)[..., None]
    wsum = np.clip(sC + sR, 0, 1)
    mixed = (mc * sC + mr * sR) / np.clip(sC + sR, 1e-6, None)
    a = a * (1 - wsum) + mixed * wsum

    # ---- 2) setores: máscara de cada um e limpeza dos ícones
    r_, g_, b_ = a[..., 0], a[..., 1], a[..., 2]
    al = a[..., 3] > 128
    navy = (r_ < 72) & (g_ < 72) & (b_ < 115) & (b_ >= r_) & al
    cells = []
    for k in range(8):
        c = k * 45.0
        d = np.minimum(np.abs(ang - c), 360 - np.abs(ang - c))
        sector = (d < 22.5) & (rad > 285) & (rad < 600)
        m = navy & sector
        lab, n = ndimage.label(m)
        sizes = ndimage.sum(m, lab, range(1, n + 1))
        big = lab == (np.argmax(sizes) + 1)
        filled = ndimage.binary_fill_holes(ndimage.binary_closing(big, iterations=6))
        cells.append(ndimage.binary_fill_holes(filled))
    for k, cm in enumerate(cells):
        inner = ndimage.binary_erosion(cm, iterations=10)
        fit = poly_fill(a, inner, inner & navy, deg=2)
        diff = np.abs(a[..., :3] - fit[..., :3]).sum(-1)
        icon = (diff > 11) & inner
        icon = ndimage.binary_fill_holes(ndimage.binary_dilation(icon, iterations=8) & inner)
        soft = cv2.GaussianBlur(icon.astype(np.float32), (0, 0), 2.5)[..., None]
        soft = np.clip(soft * 1.6, 0, 1) * inner[..., None]
        rng = np.random.default_rng(k)
        noise = cv2.GaussianBlur(rng.normal(0, 3, (H, W)).astype(np.float32), (0, 0), 1.2)[..., None]
        a[..., :3] = a[..., :3] * (1 - soft) + (fit[..., :3] + noise) * soft

    # ---- 3) disco central limpo (o C++ escreve nome, munição e atributos)
    pr = np.array([[29, 31, 62], [30, 32, 64], [31, 33, 66], [33, 36, 73], [34, 38, 79], [30, 33, 68]], np.float64)
    rk = np.array([0, 80, 140, 190, 222, 240], np.float64)
    fill = np.stack([np.interp(rad, rk, pr[:, c]) for c in range(3)], -1).astype(np.float32)
    rng = np.random.default_rng(3)
    fill += cv2.GaussianBlur(rng.normal(0, 2.2, (H, W)).astype(np.float32), (0, 0), 1.5)[..., None]
    R1 = 236.0
    w = np.clip((R1 - rad) / 4.0, 0, 1)[..., None]
    a[..., :3] = a[..., :3] * (1 - w) + fill * w
    band = (rad >= R1 - 6) & (rad < 252)
    yel = band & (a[..., 0] > 120) & (a[..., 2] < 120)
    cyn = band & (a[..., 1] > 150) & (a[..., 0] < 120)
    wht = band & (a[..., :3].min(-1) > 170)
    m = ndimage.binary_dilation(yel | cyn | wht, iterations=4) & (rad < 256)
    rgb = cv2.inpaint(np.clip(a[..., :3], 0, 255).astype(np.uint8), m.astype(np.uint8) * 255, 5, cv2.INPAINT_TELEA)
    a[m, :3] = rgb[m].astype(np.float32)
    save(a, "T_HUD2_Wheel")
    LAYOUT["wheel"] = {"size": [W, H], "center": [cx, cy], "disc_radius": 236.0, "cells": []}

    # ---- 4) por setor: máscara (escurecer/bloquear) e brilho de destaque
    for k, cm in enumerate(cells):
        ys, xs = np.nonzero(cm)
        pad = 26
        x0, y0, x1, y1 = xs.min() - pad, ys.min() - pad, xs.max() + 1 + pad, ys.max() + 1 + pad
        sub = cm[y0:y1, x0:x1].astype(np.float32)
        sub_s = cv2.GaussianBlur(sub, (0, 0), 1.0)
        # máscara branca
        mk = np.zeros(sub.shape + (4,), np.float32)
        mk[..., :3] = 255
        mk[..., 3] = sub_s * 255
        save(mk, f"T_HUD2_WheelCell{k}_Mask")
        # brilho: miolo verde-água em gradiente, borda clara por dentro e halo por fora
        hh, ww = sub.shape
        syy, sxx = np.mgrid[0:hh, 0:ww].astype(np.float32)
        rr = np.hypot(sxx + x0 - cx, syy + y0 - cy)
        t = np.clip((rr - 290) / 300.0, 0, 1)[..., None]
        inner_c = np.array([18, 110, 125], np.float32) * (1 - t) + np.array([40, 175, 178], np.float32) * t
        dist_in = ndimage.distance_transform_edt(sub > 0.5).astype(np.float32)
        rim = np.clip(1 - np.abs(dist_in - 5) / 3.5, 0, 1) * (sub > 0.5)
        glow_in = np.exp(-dist_in / 14.0) * (sub > 0.5)
        outside = ndimage.distance_transform_edt(sub < 0.5).astype(np.float32)
        halo = np.exp(-outside / 9.0) * (sub < 0.5) * 0.85
        col = inner_c + glow_in[..., None] * np.array([60, 110, 100], np.float32)
        al_fill = sub_s * 0.93
        out = np.zeros(sub.shape + (4,), np.float32)
        out[..., :3] = col
        out[..., 3] = al_fill * 255
        rim_layer = np.zeros_like(out)
        rim_layer[..., :3] = np.array([150, 255, 250], np.float32)
        rim_layer[..., 3] = rim * 255
        halo_layer = np.zeros_like(out)
        halo_layer[..., :3] = np.array([60, 240, 240], np.float32)
        halo_layer[..., 3] = halo * 255
        out = over(halo_layer, out)
        out = over(out, rim_layer)
        # cantoneiras nos dois cantos de fora (como na referência)
        cnt, _ = cv2.findContours((sub > 0.5).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
        pts = max(cnt, key=len)[:, 0, :].astype(np.float32)
        prr = np.hypot(pts[:, 0] + x0 - cx, pts[:, 1] + y0 - cy)
        pang = (np.degrees(np.arctan2(pts[:, 0] + x0 - cx, -(pts[:, 1] + y0 - cy))) - k * 45 + 540) % 360 - 180
        outer = prr > np.percentile(prr, 55)
        br = Image.new("L", (ww, hh), 0)
        dr = ImageDraw.Draw(br)
        for side in (-1, 1):
            sel = outer & (pang * side > 0)
            if sel.sum() < 5:
                continue
            idx = np.argmax(np.abs(pang) * sel)
            px, py = pts[idx]
            # anda para dentro 16 px e desenha um "L" arredondado
            vx, vy = (cx - (px + x0)), (cy - (py + y0))
            n = np.hypot(vx, vy)
            vx, vy = vx / n, vy / n
            qx, qy = px + vx * 16 - side * vy * 0 , py + vy * 16
            tx, ty = -vy * side, vx * side
            pts_l = [(qx - tx * 26, qy - ty * 26), (qx, qy), (qx + vx * 30, qy + vy * 30)]
            dr.line([tuple(p) for p in pts_l], fill=255, width=5, joint="curve")
        brk = np.array(br.filter(ImageFilter.GaussianBlur(0.8))).astype(np.float32) / 255.0
        brk *= (dist_in > 9)
        bl = np.zeros_like(out)
        bl[..., :3] = np.array([200, 255, 252], np.float32)
        bl[..., 3] = brk * 230
        out = over(out, bl)
        save(out, f"T_HUD2_WheelCell{k}_Glow")
        ccy, ccx = ndimage.center_of_mass(cm)
        LAYOUT["wheel"]["cells"].append({"rect": [int(x0), int(y0), int(x1 - x0), int(y1 - y0)],
                                         "center": [float(ccx), float(ccy)]})

    # ---- 5) peças do centro: pílula do nome e ícones dos atributos
    pill = orig[492:560, 462:795].copy()
    bgc = (30, 32, 64)
    pill = key_alpha(pill, bgc, 20, 70)
    pill = text_fill_pill(pill)
    LAYOUT["misc"]["PillTeal"] = pill_slices(pill, "T_HUD2_PillTeal")
    lav = recolor(pill, (125, 105, 190))
    LAYOUT["misc"]["PillLavender"] = pill_slices(lav, "T_HUD2_PillLavender")
    stat = {"Ammo": (458, 560, 492, 612), "Damage": (444, 614, 498, 664), "Accuracy": (446, 658, 498, 704),
            "FireRate": (448, 698, 498, 744), "Range": (444, 740, 500, 788)}
    for nm, (x0, y0, x1, y1) in stat.items():
        piece = key_alpha(orig[y0:y1, x0:x1].copy(), bgc, 26, 70)
        lav = (piece[..., 2] > 120) & (piece[..., 0] > 70) & (piece[..., 1] < 130) & (piece[..., 2] - piece[..., 1] > 40)
        piece[..., 3] = np.where(ndimage.binary_dilation(lav, iterations=2), 0, piece[..., 3])
        piece = trim(piece)
        piece = add_outline(piece, 2, (14, 12, 30), (1, 2), 0.4, 0.6)
        piece = square(piece, 64)
        save(piece, "T_HUD2_Stat_" + nm)
    # granada (ícone de exemplo da referência: setor da esquerda original)
    gx0, gy0, gx1, gy1 = 110, 470, 300, 720
    sub = orig[gy0:gy1, gx0:gx1].copy()
    cm = cells[6][gy0:gy1, gx0:gx1]
    inner = ndimage.binary_erosion(cm, iterations=10)
    nv = (sub[..., 0] < 72) & (sub[..., 1] < 72) & (sub[..., 2] < 115)
    fit = poly_fill(sub, inner, inner & nv, deg=2)
    diff = np.abs(sub[..., :3] - fit[..., :3]).sum(-1)
    alg = np.clip((diff - 45) / 45.0, 0, 1) * inner
    alg = cv2.erode(alg.astype(np.float32), np.ones((3, 3), np.uint8))
    sub[..., 3] = alg * 255
    sub = trim(sub)
    icons_out("Grenade", sub, already_outlined=True)


def text_fill_pill(pill):
    """Pílula verde-água: tira "ASSALTO" e reconstrói o miolo com o degradê vertical da própria pílula."""
    out = pill.copy()
    h, w = pill.shape[:2]
    clean_col = pill[:, 44:48].mean(1)  # coluna limpa entre a ponta e o texto
    x0, x1 = 46, w - 46
    for x in range(x0, x1):
        out[:, x, :3] = clean_col[:, :3]
        out[:, x, 3] = clean_col[:, 3]
    return out


def pill_slices(pill, name):
    """3 fatias (ponta esquerda | meio esticável | ponta direita) numa textura só."""
    h, w = pill.shape[:2]
    capL = 44
    capR = 46
    mid = pill[:, capL:capL + 4]
    tex = np.concatenate([pill[:, :capL], mid, pill[:, w - capR:]], 1)
    tex = add_pad(tex, 4)
    tw, th = save(tex, name)
    return {"size": [tw, th], "capL": capL + 4, "mid": 4, "capR": capR + 4}


def add_pad(arr, p):
    h, w = arr.shape[:2]
    out = np.zeros((h + 2 * p, w + 2 * p, 4), np.float32)
    out[p:p + h, p:p + w] = arr
    return out


def recolor(arr, tint):
    """Mesma pílula em lilás (aba inativa): troca o matiz mantendo a luz."""
    lum = arr[..., :3].mean(-1, keepdims=True) / 255.0
    t = np.array(tint, np.float32)
    out = arr.copy()
    out[..., :3] = np.clip(t * (0.35 + lum * 1.15), 0, 255)
    return out


# ====================================================================== peças desenhadas
def ss(size, k=4):
    return Image.new("RGBA", (size * k, size * k), (0, 0, 0, 0)), k


def misc():
    # círculo liso (cantos arredondados no C++) e brilho radial
    im, k = ss(128)
    ImageDraw.Draw(im).ellipse([2 * k, 2 * k, 126 * k, 126 * k], fill=(255, 255, 255, 255))
    save(np.array(im.resize((128, 128), Image.LANCZOS)).astype(np.float32), "T_HUD2_Circle")
    yy, xx = np.mgrid[0:128, 0:128].astype(np.float32)
    d = np.hypot(xx - 63.5, yy - 63.5) / 64.0
    g = np.zeros((128, 128, 4), np.float32)
    g[..., :3] = 255
    g[..., 3] = np.clip(np.exp(-(d ** 2) * 4.5) - 0.012, 0, 1) * 255
    save(g, "T_HUD2_Glow")
    # pílula escura (avisos, dicas, interação, velocidade): azul-marinho com borda ciano, 3 fatias
    W, H, k = 220, 72, 4
    im = Image.new("RGBA", (W * k, H * k), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    rr = (H - 8) * k // 2
    dr.rounded_rectangle([3 * k, 5 * k, (W - 3) * k, (H - 1) * k], rr, fill=(8, 10, 26, 150))  # sombra
    dr.rounded_rectangle([2 * k, 2 * k, (W - 2) * k, (H - 6) * k], rr, fill=(14, 16, 38, 255))  # contorno
    dr.rounded_rectangle([6 * k, 6 * k, (W - 6) * k, (H - 10) * k], rr - 4 * k, fill=(46, 196, 214, 255))  # borda ciano
    dr.rounded_rectangle([10 * k, 10 * k, (W - 10) * k, (H - 14) * k], rr - 8 * k, fill=(24, 30, 62, 255))  # miolo
    arr = np.array(im.resize((W, H), Image.LANCZOS)).astype(np.float32)
    # degradês: borda clara em cima, miolo mais escuro embaixo
    yy = np.linspace(0, 1, H)[:, None]
    border = (arr[..., 1] > 150)
    arr[..., :3] = np.where(border[..., None], arr[..., :3] * (1.18 - 0.35 * yy[..., None]), arr[..., :3])
    core = (arr[..., 2] > 50) & ~border & (arr[..., 3] > 250)
    arr[..., :3] = np.where(core[..., None], arr[..., :3] * (1.12 - 0.3 * yy[..., None]), arr[..., :3])
    # filete de luz em cima do miolo
    hl = np.zeros_like(arr)
    hl[13:15, 30:W - 30, :3] = 255
    hl[13:15, 30:W - 30, 3] = 40
    arr = over(arr, hl)
    capL = 44
    tex = np.concatenate([arr[:, :capL], arr[:, W // 2:W // 2 + 4], arr[:, W - capL:]], 1)
    tw, th = save(tex, "T_HUD2_PillNavy")
    LAYOUT["misc"]["PillNavy"] = {"size": [tw, th], "capL": capL, "mid": 4, "capR": capL}
    # tecla (E, M, Q...)
    S2 = 96
    im = Image.new("RGBA", (S2 * k, S2 * k), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.rounded_rectangle([4 * k, 10 * k, 92 * k, 94 * k], 22 * k, fill=(8, 10, 26, 170))
    dr.rounded_rectangle([4 * k, 4 * k, 92 * k, 88 * k], 22 * k, fill=(14, 16, 38, 255))
    dr.rounded_rectangle([9 * k, 9 * k, 87 * k, 83 * k], 18 * k, fill=(90, 236, 240, 255))
    dr.rounded_rectangle([14 * k, 14 * k, 82 * k, 72 * k], 14 * k, fill=(235, 252, 255, 255))
    arr = np.array(im.resize((S2, S2), Image.LANCZOS)).astype(np.float32)
    save(arr, "T_HUD2_Key")
    # ponteiro (triângulo arredondado ciano com borda branca e contorno)
    S3 = 96
    im = Image.new("RGBA", (S3 * k, S3 * k), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)

    def tri(inset):
        return [((14 + inset) * k, (10 + inset * 1.2) * k), ((86 - inset * 1.6) * k, 48 * k), ((14 + inset) * k, (86 - inset * 1.2) * k)]
    dr.polygon(tri(0), fill=(14, 16, 38, 255))
    dr.polygon(tri(6), fill=(240, 255, 255, 255))
    dr.polygon(tri(12), fill=(40, 225, 235, 255))
    im = im.filter(ImageFilter.GaussianBlur(k * 0.8))
    arr = np.array(im.resize((S3, S3), Image.LANCZOS)).astype(np.float32)
    save(arr, "T_HUD2_Pointer")
    # mira (anel fino) para a escopeta
    S4 = 256
    im = Image.new("RGBA", (S4 * 2, S4 * 2), (0, 0, 0, 0))
    dr = ImageDraw.Draw(im)
    dr.ellipse([10, 10, 2 * S4 - 10, 2 * S4 - 10], outline=(0, 0, 0, 150), width=16)
    dr.ellipse([14, 14, 2 * S4 - 14, 2 * S4 - 14], outline=(255, 255, 255, 255), width=8)
    save(np.array(im.resize((S4, S4), Image.LANCZOS)).astype(np.float32), "T_HUD2_Ring")


def icons_out(name, arr, already_outlined=False):
    if not already_outlined:
        arr = add_outline(trim(arr), 7, (16, 14, 34), (4, 7), 0.5, 1.2)
    else:
        arr = add_outline(trim(arr), 3, (16, 14, 34), (2, 4), 0.45, 0.8)
    sq = square(trim(arr), 256)
    save(sq, "T_HUD2_Icon_" + name)
    LAYOUT["icons"][name] = "T_HUD2_Icon_" + name


def icons():
    if not os.path.isdir(ICONS_RAW):
        print("AVISO: sem renders do Blender em", ICONS_RAW, "(rode tools/blender/render_hud_icons.py)")
        return
    for f in sorted(os.listdir(ICONS_RAW)):
        if f.endswith(".png"):
            arr = np.array(Image.open(os.path.join(ICONS_RAW, f)).convert("RGBA")).astype(np.float32)
            icons_out(os.path.splitext(f)[0], arr)


# ====================================================================== cabeçalho C++
def write_header():
    L = LAYOUT
    lines = [
        "// Copyright utrazin. All Rights Reserved.",
        "// GERADO por tools/pipeline/make_hud_v2.py: não edite à mão (rode o script de novo).",
        "// Números em pixels das imagens de referência (assets/raw/ui_refs). O HUD converte com a escala da tela.",
        "",
        "#pragma once",
        "",
        "#include \"CoreMinimal.h\"",
        "",
        "namespace JRHudArt",
        "{",
        "\tstruct FRect { float X; float Y; float W; float H; };",
        "\tstruct FPanel { float W; float H; };",
        "\tstruct FBarSegments { int32 Num; FRect Seg[10]; };",
        "\tstruct FPill { float TexW; float TexH; float CapL; float Mid; float CapR; };",
        "",
    ]

    def rect(name, r):
        return f"\tconstexpr FRect {name} = {{ {r[0]:.1f}f, {r[1]:.1f}f, {r[2]:.1f}f, {r[3]:.1f}f }};"

    def panel_size(name, p):
        return f"\tconstexpr FPanel {name}Size = {{ {p['size'][0]:.1f}f, {p['size'][1]:.1f}f }};"

    P = L["panels"]
    for nm in ("ObjHero", "ObjCar"):
        lines += [panel_size(nm, P[nm]), rect(nm + "Title", P[nm]["title"]), rect(nm + "Body", P[nm]["body"]),
                  rect(nm + "Marker", P[nm]["marker"]), ""]
    for nm in ("MapHero", "MapCar"):
        e = P[nm]["ellipse"]
        lines += [panel_size(nm, P[nm]), rect(nm + "Title", P[nm]["title"]),
                  f"\tconstexpr FRect {nm}Ellipse = {{ {e[0]:.1f}f, {e[1]:.1f}f, {e[2]:.1f}f, {e[3]:.1f}f }}; // centro X, Y, raio X, raio Y",
                  ""]
    bh = P["BotHero"]
    lines += [panel_size("BotHero", bh),
              f"\tconstexpr FRect BotHeroRing = {{ {bh['ring'][0]:.1f}f, {bh['ring'][1]:.1f}f, {bh['ring'][2]:.1f}f, 0.f }}; // centro X, Y, raio"]
    for key in ("A", "B"):
        bar = bh["bar" + key]
        segs = ", ".join(f"{{ {s[0]:.1f}f, {s[1]:.1f}f, {s[2]:.1f}f, {s[3]:.1f}f }}" for s in bar["segments"])
        lines += [rect(f"BotHeroBar{key}", bar["rect"]), rect(f"BotHeroBar{key}Label", bar["label"]),
                  rect(f"BotHeroBar{key}Value", bar["value"]), rect(f"BotHeroBar{key}Icon", bar["icon"]),
                  f"\tconstexpr FBarSegments BotHeroBar{key}Segments = {{ {len(bar['segments'])}, {{ {segs} }} }};"]
    lines.append("")
    bc = P["BotCar"]
    lines += [panel_size("BotCar", bc),
              f"\tconstexpr FRect BotCarRing = {{ {bc['ring'][0]:.1f}f, {bc['ring'][1]:.1f}f, {bc['ring'][2]:.1f}f, 0.f }};",
              rect("BotCarSpeed", bc["speed"])]
    for key in ("A", "B", "C"):
        bar = bc["bar" + key]
        lines += [rect(f"BotCarBar{key}", bar["rect"]), rect(f"BotCarBar{key}Label", bar["label"]),
                  rect(f"BotCarBar{key}Value", bar["value"]),
                  f"\tconstexpr float BotCarBar{key}Span[2] = {{ {bar['span'][0]:.1f}f, {bar['span'][1]:.1f}f }}; // x inicial e final da barra"]
    lines.append("")
    wp = P["Weapon"]
    lines += [panel_size("Weapon", wp),
              f"\tconstexpr FRect WeaponRing = {{ {wp['ring'][0]:.1f}f, {wp['ring'][1]:.1f}f, {wp['ring'][2]:.1f}f, 0.f }};",
              rect("WeaponBody", wp["body"]), ""]
    wh = L["wheel"]
    lines += [f"\tconstexpr FPanel WheelSize = {{ {wh['size'][0]:.1f}f, {wh['size'][1]:.1f}f }};",
              f"\tconstexpr float WheelCenter[2] = {{ {wh['center'][0]:.1f}f, {wh['center'][1]:.1f}f }};",
              f"\tconstexpr float WheelDiscRadius = {wh['disc_radius']:.1f}f;"]
    cells = ", ".join(f"{{ {c['rect'][0]:.1f}f, {c['rect'][1]:.1f}f, {c['rect'][2]:.1f}f, {c['rect'][3]:.1f}f }}" for c in wh["cells"])
    centers = ", ".join(f"{{ {c['center'][0]:.1f}f, {c['center'][1]:.1f}f, 0.f, 0.f }}" for c in wh["cells"])
    lines += [f"\tconstexpr FRect WheelCellRect[8] = {{ {cells} }};",
              f"\tconstexpr FRect WheelCellCenter[8] = {{ {centers} }}; // X, Y do centro de massa", ""]
    for nm in ("PillTeal", "PillLavender", "PillNavy"):
        p = L["misc"][nm]
        lines.append(f"\tconstexpr FPill {nm} = {{ {p['size'][0]:.1f}f, {p['size'][1]:.1f}f, {p['capL']:.1f}f, {p['mid']:.1f}f, {p['capR']:.1f}f }};")
    lines += ["}", ""]
    os.makedirs(os.path.dirname(HEADER), exist_ok=True)
    with open(HEADER, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines))


def main():
    os.makedirs(OUT, exist_ok=True)
    src = hero()
    clean = weapon_card(src)
    badge(clean)
    car()
    wheel()
    misc()
    icons()
    with open(os.path.join(OUT, "hud_v2_layout.json"), "w", encoding="utf-8") as fh:
        json.dump(LAYOUT, fh, ensure_ascii=False, indent=1)
    write_header()
    print("HUD v2: texturas em", OUT)


if __name__ == "__main__":
    sys.exit(main())
