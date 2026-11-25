"""[A-083] Ícones e peças da HUD do Remap (cidade/arena) no estilo v2 "argila alienígena".

Desenho próprio em Python (PIL + numpy), sem arte de terceiros: formas simples com volume de massinha
(degradê de cima para baixo, borda clara em cima, sombra embaixo, brilho de vidro), contorno azul-tinta
e sombra projetada, como os ícones de /Game/UI/HUD/V2.

Saída: assets/work/ui/remap/T_HUD2_R_*.png (256 x 256 para ícones; peças de painel em 9 fatias).
Importação: tools/unreal/setup_remap_hud.py (no editor), para /Game/UI/HUD/V2 (o AJRHUD acha por HudTex("R_...")).
Rodar de novo: python assets/work/ui/remap/_make_remap_hud.py
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

OUT = os.path.dirname(os.path.abspath(__file__)) if len(sys.argv) < 2 else sys.argv[1]
SS = 1024  # supersample
FINAL = 256
INK = (12, 13, 32)


# ------------------------------------------------------------------ base
def new_mask():
    return Image.new("L", (SS, SS), 0)


def grow(mask, px):
    """Dilata (px > 0) ou corrói (px < 0) por desfoque + limiar (rápido e liso)."""
    if px == 0:
        return mask
    b = mask.filter(ImageFilter.GaussianBlur(abs(px) * 0.6))
    a = np.asarray(b).astype(np.float32)
    if px > 0:
        a = np.clip((a - 8.0) * 6.0, 0, 255)
    else:
        a = np.clip((a - 235.0) * 12.0, 0, 255)
    return Image.fromarray(a.astype(np.uint8))


def shade(c, f):
    return tuple(int(max(0, min(255, v * f))) for v in c)


def mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def clay_layer(mask, color, gloss=True, bevel=1.0):
    """Preenche a máscara com volume de massinha. Retorna RGBA."""
    m = np.asarray(mask).astype(np.float32) / 255.0
    ys, xs = np.nonzero(m > 0.5)
    if len(ys) == 0:
        return Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    y0, y1 = ys.min(), ys.max()
    top = np.array(mix(color, (255, 255, 255), 0.30), np.float32)
    bot = np.array(shade(color, 0.62), np.float32)
    t = np.clip((np.arange(SS, dtype=np.float32) - y0) / max(1, (y1 - y0)), 0, 1)[:, None, None]
    rgb = top[None, None, :] * (1 - t) + bot[None, None, :] * t
    rgb = np.broadcast_to(rgb, (SS, SS, 3)).copy()
    # borda: clara em cima/esquerda, escura embaixo/direita
    blur = np.asarray(mask.filter(ImageFilter.GaussianBlur(22))).astype(np.float32) / 255.0
    gy, gx = np.gradient(blur)
    light = np.clip((gy * 1.0 + gx * 0.4) * 60.0 * bevel, -1, 1)  # >0: lado de cima
    edge = np.clip(1.0 - blur * 1.6, 0, 1) * m
    rgb += (light * edge)[..., None] * 90.0
    # sombra interna embaixo
    inner = np.asarray(grow(mask, -30).filter(ImageFilter.GaussianBlur(30))).astype(np.float32) / 255.0
    rgb *= (0.80 + 0.20 * inner)[..., None]
    if gloss:
        g = new_mask()
        d = ImageDraw.Draw(g)
        x0, x1 = xs.min(), xs.max()
        w, h = x1 - x0, y1 - y0
        d.ellipse([x0 + w * 0.16, y0 + h * 0.06, x0 + w * 0.62, y0 + h * 0.30], fill=255)
        g = Image.fromarray(np.minimum(np.asarray(g), np.asarray(grow(mask, -26))))
        g = g.filter(ImageFilter.GaussianBlur(14))
        ga = np.asarray(g).astype(np.float32) / 255.0 * 0.38
        rgb = rgb * (1 - ga[..., None]) + 255.0 * ga[..., None]
    rgb = np.clip(rgb, 0, 255).astype(np.uint8)
    a = (m * 255).astype(np.uint8)
    return Image.fromarray(np.dstack([rgb, a]), "RGBA")


def render(parts, name, outline=26, inner_line=12, size=FINAL, shadow=True):
    """parts: lista de (máscara, cor[, opções]). Contorno geral + linha fina entre partes."""
    union = new_mask()
    for p in parts:
        union = Image.fromarray(np.maximum(np.asarray(union), np.asarray(p[0])))
    out = Image.new("RGBA", (SS, SS), (0, 0, 0, 0))
    ol = grow(union, outline)
    if shadow:
        sh = Image.new("L", (SS, SS), 0)
        sh.paste(ol, (0, 22))
        sh = sh.filter(ImageFilter.GaussianBlur(16))
        sa = (np.asarray(sh).astype(np.float32) * 0.55).astype(np.uint8)
        out = Image.alpha_composite(out, Image.fromarray(np.dstack([np.full((SS, SS, 3), INK, np.uint8), sa]), "RGBA"))
    out = Image.alpha_composite(out, Image.fromarray(np.dstack([np.full((SS, SS, 3), INK, np.uint8), np.asarray(ol)]), "RGBA"))
    for i, p in enumerate(parts):
        mask, color = p[0], p[1]
        opts = p[2] if len(p) > 2 else {}
        if i > 0 and inner_line > 0 and not opts.get("noline"):
            il = grow(mask, inner_line)
            out = Image.alpha_composite(out, Image.fromarray(np.dstack([np.full((SS, SS, 3), INK, np.uint8), np.asarray(il)]), "RGBA"))
        out = Image.alpha_composite(out, clay_layer(mask, color, gloss=opts.get("gloss", True), bevel=opts.get("bevel", 1.0)))
    out = out.resize((size, size), Image.LANCZOS)
    out.save(os.path.join(OUT, f"T_HUD2_R_{name}.png"))
    return out


def shape(fn):
    m = new_mask()
    fn(ImageDraw.Draw(m))
    return m


def poly_star(cx, cy, r_out, r_in, n, rot=-90):
    pts = []
    for i in range(n * 2):
        r = r_out if i % 2 == 0 else r_in
        a = math.radians(rot + i * 180.0 / n)
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def heart_pts(cx, cy, s):
    pts = []
    for i in range(200):
        t = 2 * math.pi * i / 200
        x = 16 * math.sin(t) ** 3
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        pts.append((cx + x * s, cy - y * s))
    return pts


def sub(a, b):
    return Image.fromarray(np.clip(np.asarray(a).astype(np.int16) - np.asarray(b), 0, 255).astype(np.uint8))


def rot_mask(m, deg):
    return m.rotate(deg, resample=Image.BICUBIC, center=(SS / 2, SS / 2))


# ------------------------------------------------------------------ cores (paleta da HUD v2)
GOLD = (255, 196, 54)
CYAN = (64, 226, 236)
LILAC = (176, 150, 232)
PURPLE = (164, 84, 240)
RED = (255, 92, 84)
GREEN = (96, 214, 110)
BONE = (238, 236, 250)
NAVY = (40, 52, 104)
ORANGE = (255, 138, 50)
PINK = (255, 110, 200)
STEEL = (150, 172, 210)


def crystal(d, cx, cy, w, h):
    d.polygon([(cx, cy - h * 0.5), (cx + w * 0.5, cy - h * 0.18), (cx + w * 0.38, cy + h * 0.5),
               (cx - w * 0.38, cy + h * 0.5), (cx - w * 0.5, cy - h * 0.18)], fill=255)


def icons():
    C = SS / 2
    # Moeda (créditos): disco dourado, aro, cristal roxo no meio
    coin = shape(lambda d: d.ellipse([C - 380, C - 380, C + 380, C + 380], fill=255))
    face = shape(lambda d: d.ellipse([C - 290, C - 290, C + 290, C + 290], fill=255))
    gem = shape(lambda d: crystal(d, C, C, 270, 360))
    render([(coin, GOLD), (face, shade(GOLD, 0.92), {"gloss": False}), (gem, PURPLE)], "Coin")

    # Pilha de moedas (carta de créditos)
    parts = []
    for i, (ox, oy) in enumerate([(-150, 230), (130, 200), (-10, 30), (60, -170)]):
        parts.append((shape(lambda d, ox=ox, oy=oy: d.ellipse([C + ox - 250, C + oy - 150, C + ox + 250, C + oy + 150], fill=255)), shade(GOLD, 1.0 - 0.04 * (3 - i))))
    parts.append((shape(lambda d: crystal(d, C + 60, C - 175, 150, 170)), PURPLE))
    render(parts, "Coins")

    # Bancada: engrenagem lilás + chave inglesa ciano
    gear = shape(lambda d: d.polygon(poly_star(C - 60, C + 40, 330, 250, 8, -90 + 22.5), fill=255))
    gear = Image.fromarray(np.maximum(np.asarray(gear), np.asarray(shape(lambda d: d.ellipse([C - 60 - 270, C + 40 - 270, C - 60 + 270, C + 40 + 270], fill=255)))))
    gear = sub(gear, shape(lambda d: d.ellipse([C - 60 - 110, C + 40 - 110, C - 60 + 110, C + 40 + 110], fill=255)))

    def wrench(d):
        d.rounded_rectangle([C - 70, C - 300, C + 70, C + 360], radius=70, fill=255)
        d.ellipse([C - 190, C - 470, C + 190, C - 90], fill=255)
    wr = shape(wrench)
    wr = sub(wr, shape(lambda d: d.rectangle([C - 75, C - 520, C + 75, C - 290], fill=255)))
    wr = rot_mask(wr, -40)
    wr = wr.transform((SS, SS), Image.AFFINE, (1, 0, -110, 0, 1, 40))
    render([(gear, LILAC), (wr, CYAN)], "Bench")

    # Troféu (recorde)
    def cup(d):
        d.pieslice([C - 280, C - 520, C + 280, C + 140], 0, 180, fill=255)
        d.rectangle([C - 280, C - 330, C + 280, C - 190], fill=255)
        d.rectangle([C - 60, C + 120, C + 60, C + 260], fill=255)
        d.rounded_rectangle([C - 230, C + 240, C + 230, C + 380], radius=40, fill=255)
    body = shape(cup)
    handles = shape(lambda d: (d.ellipse([C - 420, C - 300, C - 160, C - 20], fill=255), d.ellipse([C + 160, C - 300, C + 420, C - 20], fill=255)))
    handles = sub(handles, shape(lambda d: (d.ellipse([C - 350, C - 230, C - 230, C - 90], fill=255), d.ellipse([C + 230, C - 230, C + 350, C - 90], fill=255))))
    star = shape(lambda d: d.polygon(poly_star(C, C - 150, 120, 52, 5), fill=255))
    render([(handles, shade(GOLD, 0.9)), (body, GOLD), (star, (255, 250, 220), {"gloss": False})], "Trophy")

    # Onda (horda): três ondas empilhadas
    parts = []
    for k, oy in enumerate((-250, 0, 250)):
        def band(d, oy=oy):
            top, bot = [], []
            for i in range(80):
                x = -400 + 800 * i / 79.0
                yy = 70 * math.sin(i / 79.0 * 2 * math.pi * 1.5)
                top.append((C + x, C + oy + yy - 75))
                bot.append((C + x, C + oy + yy + 75))
            d.polygon(top + bot[::-1], fill=255)
        parts.append((shape(band), mix(RED, (255, 190, 120), k * 0.3)))
    render(parts, "Wave")

    # Caveira (abates)
    def skull(d):
        d.ellipse([C - 330, C - 400, C + 330, C + 200], fill=255)
        d.rounded_rectangle([C - 200, C + 60, C + 200, C + 360], radius=60, fill=255)
    sk = shape(skull)
    holes = shape(lambda d: (d.ellipse([C - 230, C - 160, C - 50, C + 30], fill=255), d.ellipse([C + 50, C - 160, C + 230, C + 30], fill=255),
                             d.polygon([(C, C + 70), (C - 50, C + 160), (C + 50, C + 160)], fill=255),
                             d.rectangle([C - 115, C + 270, C - 85, C + 360], fill=255), d.rectangle([C - 15, C + 270, C + 15, C + 360], fill=255),
                             d.rectangle([C + 85, C + 270, C + 115, C + 360], fill=255)))
    render([(sub(sk, holes), BONE)], "Skull")

    # Energia: três cristais roxos
    c1 = shape(lambda d: crystal(d, C, C - 40, 300, 720))
    c2 = rot_mask(shape(lambda d: crystal(d, C - 250, C + 110, 220, 460)), 18)
    c3 = rot_mask(shape(lambda d: crystal(d, C + 250, C + 120, 220, 440)), -18)
    render([(c2, shade(PURPLE, 0.85)), (c3, shade(PURPLE, 0.85)), (c1, (196, 120, 255))], "Energy")

    # Nave de extração: disco lilás, cúpula ciano, luzes amarelas
    dome = shape(lambda d: d.ellipse([C - 210, C - 330, C + 210, C + 60], fill=255))
    disc = shape(lambda d: d.ellipse([C - 440, C - 110, C + 440, C + 190], fill=255))
    beam = shape(lambda d: d.polygon([(C - 150, C + 150), (C + 150, C + 150), (C + 260, C + 440), (C - 260, C + 440)], fill=255))
    lights = shape(lambda d: [d.ellipse([C + x - 42, C + 20 - 42, C + x + 42, C + 20 + 42], fill=255) for x in (-280, -95, 95, 280)])
    render([(beam, (120, 250, 255), {"gloss": False, "bevel": 0.3}), (dome, CYAN), (disc, LILAC), (lights, GOLD, {"gloss": False})], "Ship")

    # Multiplicador: estrela dourada
    st = shape(lambda d: d.polygon(poly_star(C, C + 20, 450, 210, 5), fill=255))
    render([(st, GOLD)], "Star")

    # Relógio (contagem da nave / intervalo)
    ring = shape(lambda d: d.ellipse([C - 400, C - 380, C + 400, C + 420], fill=255))
    face = shape(lambda d: d.ellipse([C - 300, C - 280, C + 300, C + 320], fill=255))
    hands = shape(lambda d: (d.rounded_rectangle([C - 40, C - 220, C + 40, C + 60], radius=40, fill=255),
                             d.rounded_rectangle([C - 40, C - 20, C + 220, C + 60], radius=40, fill=255)))
    knob = shape(lambda d: d.rounded_rectangle([C - 90, C - 520, C + 90, C - 380], radius=30, fill=255))
    render([(knob, LILAC), (ring, CYAN), (face, (230, 244, 255), {"gloss": False}), (hands, NAVY, {"gloss": False})], "Clock")

    # Portal da arena: anel roxo com miolo ciano
    outer = shape(lambda d: d.ellipse([C - 360, C - 440, C + 360, C + 440], fill=255))
    inner = shape(lambda d: d.ellipse([C - 230, C - 300, C + 230, C + 300], fill=255))
    swirl = shape(lambda d: d.ellipse([C - 120, C - 170, C + 120, C + 170], fill=255))
    stones = shape(lambda d: [d.ellipse([C + 400 * math.cos(a) - 70, C + 480 * math.sin(a) - 70, C + 400 * math.cos(a) + 70, C + 480 * math.sin(a) + 70], fill=255)
                              for a in [math.radians(v) for v in (-90, -30, 30, 150, 210)]])
    render([(sub(outer, inner), PURPLE), (inner, CYAN), (swirl, (230, 255, 255), {"gloss": False}), (stones, LILAC)], "Portal")

    # Bandeira (objetivos cumpridos)
    pole = shape(lambda d: d.rounded_rectangle([C - 300, C - 420, C - 210, C + 430], radius=45, fill=255))
    flag = shape(lambda d: d.polygon([(C - 220, C - 400), (C + 380, C - 260), (C - 220, C - 40)], fill=255))
    render([(pole, LILAC), (flag, GOLD)], "Flag")

    # Chama (combo): gota de fogo com ponta curva e uma lambida do lado
    def flame(d, s, ox, oy, lean):
        pts = []
        for i in range(160):
            t = i / 159.0 * 2 * math.pi
            x = math.sin(t) * math.sin(t / 2) ** 1.6 * 0.95
            y = -math.cos(t)
            x += lean * (1 - (y + 1) / 2) ** 2  # ponta entorta
            pts.append((C + ox + x * s, C + oy + y * s * 1.05))
        d.polygon(pts, fill=255)
    f1 = shape(lambda d: (flame(d, 420, 0, 40, 0.25), flame(d, 230, -250, 170, -0.3)))
    f2 = shape(lambda d: flame(d, 220, 30, 220, 0.15))
    render([(f1, ORANGE), (f2, GOLD)], "Flame")

    # ---------------- cartas
    burst = shape(lambda d: d.polygon(poly_star(C, C, 450, 250, 9), fill=255))
    core = shape(lambda d: d.polygon(poly_star(C, C, 250, 150, 9, -70), fill=255))
    render([(burst, RED), (core, GOLD)], "CardDamage")

    parts = []
    for ox in (-230, 0, 230):
        b = shape(lambda d, ox=ox: (d.rounded_rectangle([C + ox - 85, C - 200, C + ox + 85, C + 330], radius=30, fill=255)))
        tip = shape(lambda d, ox=ox: d.pieslice([C + ox - 85, C - 420, C + ox + 85, C - 30], 180, 360, fill=255))
        parts.append((b, GOLD))
        parts.append((tip, (255, 150, 90)))
    render(parts, "CardFireRate")

    chev = shape(lambda d: [d.polygon([(C + ox - 200, C - 330), (C + ox - 20, C - 330), (C + ox + 230, C), (C + ox - 20, C + 330), (C + ox - 200, C + 330), (C + ox + 50, C)], fill=255) for ox in (-170, 170)])
    render([(chev, GREEN)], "CardSpeed")

    h = shape(lambda d: d.polygon(heart_pts(C, C + 10, 26), fill=255))
    plus = shape(lambda d: (d.rounded_rectangle([C + 130, C - 420, C + 230, C - 120], radius=30, fill=255), d.rounded_rectangle([C + 30, C - 320, C + 330, C - 220], radius=30, fill=255)))
    render([(h, RED), (plus, (255, 240, 240))], "CardMaxHealth")

    h2 = shape(lambda d: d.polygon(heart_pts(C - 60, C - 20, 22), fill=255))
    drop = shape(lambda d: (d.ellipse([C + 120, C + 120, C + 380, C + 380], fill=255), d.polygon([(C + 250, C - 60), (C + 140, C + 190), (C + 360, C + 190)], fill=255)))
    render([(h2, (220, 60, 110)), (drop, RED)], "CardLifeOnKill")

    h3 = shape(lambda d: d.polygon(heart_pts(C, C + 10, 26), fill=255))
    cross = shape(lambda d: (d.rounded_rectangle([C - 70, C - 230, C + 70, C + 170], radius=30, fill=255), d.rounded_rectangle([C - 200, C - 100, C + 200, C + 40], radius=30, fill=255)))
    render([(h3, GREEN), (cross, (240, 255, 240))], "CardHeal")

    def shield(d):
        pts = [(C - 360, C - 380), (C, C - 450), (C + 360, C - 380), (C + 340, C + 20)]
        for i in range(30):
            t = i / 29.0
            pts.append((C + 340 * (1 - t), C + 20 + 430 * math.sin(t * math.pi / 2)))
        for i in range(30):
            t = i / 29.0
            pts.append((C - 340 * t, C + 450 - 430 * (1 - math.cos(t * math.pi / 2))))
        pts.append((C - 340, C + 20))
        d.polygon(pts, fill=255)
    sh = shape(shield)
    band = shape(lambda d: d.polygon([(C - 60, C - 420), (C + 60, C - 420), (C + 60, C + 420), (C - 60, C + 420)], fill=255))
    band = Image.fromarray(np.minimum(np.asarray(band), np.asarray(grow(sh, -60))))
    render([(sh, STEEL), (band, CYAN)], "CardArmor")


# ------------------------------------------------------------------ peças de painel
def panels():
    """Painel em 9 fatias (256 x 256, cantos de 80 px): miolo azul-marinho + aro claro para tingir (lilás/raridade)."""
    N = 1024
    R = 220
    def rr(inset, rad):
        m = Image.new("L", (N, N), 0)
        ImageDraw.Draw(m).rounded_rectangle([inset, inset, N - 1 - inset, N - 1 - inset], radius=rad, fill=255)
        return m
    outer = rr(40, R)
    rim_in = rr(108, R - 66)
    fill_m = rr(104, R - 64)
    ink = grow(outer, 18)
    # miolo: degradê azul-marinho, mais claro em cima, com sombra interna
    a = np.asarray(fill_m).astype(np.float32) / 255
    t = np.linspace(0, 1, N, dtype=np.float32)[:, None]
    top = np.array((38, 48, 100), np.float32)
    bot = np.array((24, 30, 66), np.float32)
    rgb = top * (1 - t[..., None]) + bot * t[..., None]
    rgb = np.broadcast_to(rgb, (N, N, 3)).copy()
    inner = np.asarray(grow(fill_m, -40).filter(ImageFilter.GaussianBlur(40))).astype(np.float32) / 255
    rgb *= (0.72 + 0.28 * inner)[..., None]
    fill = np.dstack([np.clip(rgb, 0, 255), a * 255]).astype(np.uint8)
    base = Image.new("RGBA", (N, N), (0, 0, 0, 0))
    base = Image.alpha_composite(base, Image.fromarray(np.dstack([np.full((N, N, 3), INK, np.uint8), np.asarray(ink)]), "RGBA"))
    base = Image.alpha_composite(base, Image.fromarray(fill, "RGBA"))
    base.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "T_HUD2_R_PanelFill.png"))
    # aro (cinza claro com volume, para ser tingido)
    ring = sub(outer, rim_in)
    lay = clay_layer(ring.resize((SS, SS)) if N != SS else ring, (235, 235, 245), gloss=False, bevel=1.4)
    # bolinhas de luz nos cantos de baixo (ficam brancas e são tingidas junto)
    lay.resize((256, 256), Image.LANCZOS).save(os.path.join(OUT, "T_HUD2_R_PanelRim.png"))
    # brilho de seleção (aro desfocado, some antes da borda da textura)
    gl = Image.new("L", (N, N), 0)
    ImageDraw.Draw(gl).rounded_rectangle([124, 124, N - 125, N - 125], radius=200, fill=255)
    glow = gl.filter(ImageFilter.GaussianBlur(38))
    hole = Image.new("L", (N, N), 0)
    ImageDraw.Draw(hole).rounded_rectangle([200, 200, N - 201, N - 201], radius=140, fill=255)
    ga = np.asarray(sub(glow, hole.filter(ImageFilter.GaussianBlur(20)))).astype(np.uint8)
    Image.fromarray(np.dstack([np.full((N, N, 3), 255, np.uint8), ga]), "RGBA").resize((256, 256), Image.LANCZOS).save(
        os.path.join(OUT, "T_HUD2_R_PanelGlow.png"))
    # luzinha ciano (enfeite do canto)
    d = Image.new("L", (SS, SS), 0)
    ImageDraw.Draw(d).rounded_rectangle([SS * 0.1, SS * 0.32, SS * 0.9, SS * 0.68], radius=SS * 0.18, fill=255)
    render([(d, CYAN)], "Light", outline=40, size=128, shadow=False)


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    icons()
    panels()
    print("ok", OUT)
