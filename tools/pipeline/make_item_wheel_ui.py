"""Texturas da roda de itens (Tab) no estilo gibi anos 50: tinta preta, creme, retícula (halftone).

Gera em assets/work/ui/wheel/ (importadas por tools/unreal/setup_item_wheel.py para /Game/UI/HUD/Wheel):
  T_UI_Wheel_Sector.png   um setor (1/8 do anel) apontando para cima, no quadrado da roda inteira.
                          Miolo BRANCO (o HUD pinta: creme, verde do destaque, cinza bloqueado), contorno preto
                          e retícula cinza (vira um tom mais escuro da cor pintada).
  T_UI_Wheel_Center.png   disco central creme com contorno e retícula (desenhado sem tinta).
  T_UI_Wheel_<Ícone>.png  ícones coloridos com contorno de tinta: Hand, Stick, Pistol, Shotgun, Grenade,
                          Fury, Medkit, Bandage, Lock.
  _mockup.png             prévia 1920x1080 de como a roda aparece no jogo (só para ver; não é importada).

Uso (Python 3 + Pillow, fora da Unreal):  python tools/pipeline/make_item_wheel_ui.py
A geometria (raio interno 0,44 do externo, 8 setores, folga entre setores) precisa bater com
AJRHUD::DrawItemWheel (UI/JRHUD.cpp): se mudar aqui, mude lá.
"""
import math
import os
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
UI = os.path.join(REPO, "assets", "work", "ui")
OUT = os.path.join(UI, "wheel")

# paleta (gibi / filme B anos 50)
CREAM = (243, 230, 196)
INK = (20, 16, 14)
GREEN = (124, 255, 79)
RED = (232, 64, 42)
YELLOW = (255, 210, 63)
TEAL = (94, 200, 216)
BROWN = (160, 103, 58)
OLIVE = (107, 127, 58)
SKIN = (242, 201, 160)
WHITE = (255, 255, 255)

SS = 4                  # superamostragem (antisserrilhado)
WHEEL = 768             # textura do setor / centro
R_OUT = 372             # raio externo do anel dentro da textura (meia textura = 384)
R_IN_FRAC = 0.44        # raio interno / externo (igual ao C++)
GAP_DEG = 1.8           # meia folga entre setores (graus)
INK_W = 7               # espessura do contorno (px na textura final)
ICON = 256


def rng(seed):
    return random.Random(seed)


def wobble(points, amount, seed):
    """Tremidinho de pena: desloca cada ponto um pouco (traço feito à mão)."""
    r = rng(seed)
    return [(x + r.uniform(-amount, amount), y + r.uniform(-amount, amount)) for x, y in points]


def sector_poly(cx, cy, r_in, r_out, a0, a1, steps=48):
    """Setor do anel; ângulos em graus a partir do topo, sentido horário."""
    pts = []
    for i in range(steps + 1):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        pts.append((cx + r_out * math.sin(a), cy - r_out * math.cos(a)))
    for i in range(steps + 1):
        a = math.radians(a1 + (a0 - a1) * i / steps)
        pts.append((cx + r_in * math.sin(a), cy - r_in * math.cos(a)))
    return pts


def halftone(size, mask, color, step, rmin, rmax, grad, seed=0):
    """Retícula: bolinhas numa grade a 45 graus; grad(x, y) -> 0..1 define o tamanho; mask (L) recorta."""
    layer = Image.new("RGBA", size, (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    w, h = size
    for j in range(-2, int(h / step * 1.5) + 4):
        for i in range(-2, int(w / step * 1.5) + 4):
            x = (i - j) * step * 0.7071 + w * 0.5
            y = (i + j) * step * 0.7071 - h * 0.25
            if not (0 <= x < w and 0 <= y < h):
                continue
            t = grad(x, y)
            if t <= 0.02:
                continue
            r = rmin + (rmax - rmin) * min(1.0, t)
            d.ellipse([x - r, y - r, x + r, y + r], fill=color)
    # só dentro da máscara (L)
    return Image.composite(layer, Image.new("RGBA", size, (0, 0, 0, 0)), mask)


def make_sector():
    k = WHEEL * SS
    c = k / 2
    ro = R_OUT * SS
    ri = ro * R_IN_FRAC
    w = INK_W * SS
    half = 22.5 - GAP_DEG
    im = Image.new("RGBA", (k, k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.polygon(wobble(sector_poly(c, c, ri, ro, -half, half), 1.2 * SS, 1), fill=INK + (255,))
    # miolo: recuado pela espessura da tinta (ângulo recuado pelo arco equivalente)
    ri2, ro2 = ri + w, ro - w
    da = math.degrees(w / ri)
    inner = wobble(sector_poly(c, c, ri2, ro2, -half + da * 0.8, half - da * 0.8), 0.8 * SS, 2)
    fill_mask = Image.new("L", (k, k), 0)
    ImageDraw.Draw(fill_mask).polygon(inner, fill=255)
    im.paste(Image.new("RGBA", (k, k), WHITE + (255,)), (0, 0), fill_mask)
    # retícula mais forte perto da borda externa (sombra de gibi)
    def grad(x, y):
        r = math.hypot(x - c, y - c)
        return max(0.0, (r - (ri2 + (ro2 - ri2) * 0.55)) / ((ro2 - ri2) * 0.45))
    dots = halftone((k, k), fill_mask, (200, 200, 200, 255), 13 * SS, 0.6 * SS,
                    4.2 * SS, grad)
    im.alpha_composite(dots)
    # brilho: linha fina branca não; traço interno de tinta paralelo à borda interna (acabamento de pena)
    arc = sector_poly(c, c, ri2 + 10 * SS, ri2 + 10 * SS, -half + da * 2.2, half - da * 2.2, 32)[:33]
    d.line(wobble(arc, 0.6 * SS, 3), fill=INK + (255,), width=int(2 * SS))
    return im.resize((WHEEL, WHEEL), Image.LANCZOS)


def make_center():
    k = WHEEL * SS
    c = k / 2
    ro = R_OUT * SS
    w = int(INK_W * 1.2 * SS)
    im = Image.new("RGBA", (k, k), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    circle = [(c + ro * math.cos(t * 2 * math.pi / 160), c + ro * math.sin(t * 2 * math.pi / 160)) for t in range(160)]
    d.polygon(wobble(circle, 1.5 * SS, 4), fill=INK + (255,))
    rf = ro - w
    circle2 = [(c + rf * math.cos(t * 2 * math.pi / 160), c + rf * math.sin(t * 2 * math.pi / 160)) for t in range(160)]
    mask = Image.new("L", (k, k), 0)
    ImageDraw.Draw(mask).polygon(wobble(circle2, 1.0 * SS, 5), fill=255)
    im.paste(Image.new("RGBA", (k, k), CREAM + (255,)), (0, 0), mask)

    def grad(x, y):
        r = math.hypot(x - c, y - c)
        lower = max(0.0, (y - c) / rf)  # mais retícula embaixo (luz vindo de cima)
        return max(0.0, (r - rf * 0.72) / (rf * 0.28)) * 0.6 + lower * 0.35
    dots = halftone((k, k), mask, (214, 196, 150, 255), 15 * SS, 0.5 * SS, 4.5 * SS, grad)
    im.alpha_composite(dots)
    ri = rf - 16 * SS
    d.ellipse([c - ri, c - ri, c + ri, c + ri], outline=INK + (255,), width=int(2.5 * SS))
    return im.resize((WHEEL, WHEEL), Image.LANCZOS)


# ---------------------------------------------------------------- ícones
def ink_silhouette(alpha, fill, outline_px=11, shade=True):
    """Silhueta (canal alfa, ICON*SS) -> ícone com contorno de tinta, cor e retícula embaixo."""
    k = alpha.size[0]
    grow = alpha.filter(ImageFilter.MaxFilter(_odd(outline_px * SS * 2)))
    im = Image.new("RGBA", (k, k), (0, 0, 0, 0))
    im.paste(Image.new("RGBA", (k, k), INK + (255,)), (0, 0), grow)
    im.paste(Image.new("RGBA", (k, k), fill + (255,)), (0, 0), alpha)
    if shade:
        darker = tuple(int(v * 0.62) for v in fill) + (255,)
        dots = halftone((k, k), alpha, darker, 9 * SS, 0.4 * SS, 3.2 * SS,
                        lambda x, y: max(0.0, (y / k - 0.45) / 0.55))
        im.alpha_composite(dots)
    return im


def _odd(n):
    n = int(n)
    return n if n % 2 == 1 else n + 1


def from_hud_icon(name, fill, scale=0.86):
    """Usa a silhueta branca do HUD atual (T_UI_<name>.png), um pouco menor para caber o contorno."""
    src = Image.open(os.path.join(UI, f"T_UI_{name}.png")).convert("RGBA").split()[3]
    k = ICON * SS
    big = src.resize((int(k * scale), int(k * scale)), Image.LANCZOS)
    alpha = Image.new("L", (k, k), 0)
    alpha.paste(big, ((k - big.size[0]) // 2, (k - big.size[1]) // 2))
    alpha = alpha.point(lambda v: 255 if v > 110 else 0)
    return ink_silhouette(alpha, fill).resize((ICON, ICON), Image.LANCZOS)


def parts_icon(draw_fn):
    """Ícone desenhado em partes, cada uma com contorno (draw_fn(d, k, ink_w))."""
    k = ICON * SS
    im = Image.new("RGBA", (k, k), (0, 0, 0, 0))
    draw_fn(im, ImageDraw.Draw(im), k, int(9 * SS))
    return im.resize((ICON, ICON), Image.LANCZOS)


def icon_hand(im, d, k, w):
    alpha = Image.new("L", (k, k), 0)
    a = ImageDraw.Draw(alpha)
    a.rounded_rectangle([0.30 * k, 0.42 * k, 0.72 * k, 0.86 * k], radius=0.12 * k, fill=255)
    for i, (x, top) in enumerate(((0.31, 0.20), (0.41, 0.12), (0.51, 0.13), (0.61, 0.21))):
        a.rounded_rectangle([x * k, top * k, (x + 0.09) * k, 0.55 * k], radius=0.045 * k, fill=255)
    thumb = Image.new("L", (k, k), 0)
    ImageDraw.Draw(thumb).rounded_rectangle([0.16 * k, 0.50 * k, 0.40 * k, 0.60 * k], radius=0.05 * k, fill=255)
    thumb = thumb.rotate(-35, center=(0.36 * k, 0.62 * k), resample=Image.BICUBIC)
    alpha = Image.composite(Image.new("L", (k, k), 255), alpha, thumb)
    im.alpha_composite(ink_silhouette(alpha, SKIN))
    # linhas dos dedos e da palma
    for x in (0.40, 0.50, 0.60):
        d.line([(x * k, 0.42 * k), (x * k, 0.50 * k)], fill=INK + (255,), width=int(w * 0.5))
    d.line([(0.40 * k, 0.66 * k), (0.52 * k, 0.72 * k)], fill=INK + (255,), width=int(w * 0.4))


def icon_bandage(im, d, k, w):
    # faixa desenrolada saindo do rolo, com pontas recortadas
    strip = [(0.48 * k, 0.78 * k), (0.92 * k, 0.70 * k), (0.86 * k, 0.76 * k), (0.93 * k, 0.82 * k),
             (0.50 * k, 0.90 * k)]
    d.polygon(wobble(strip, 0.004 * k, 7), fill=(255, 248, 232, 255), outline=INK + (255,), width=w)
    for t in (0.62, 0.74):
        d.line([(t * k, 0.75 * k), (t * k + 0.012 * k, 0.86 * k)], fill=(200, 190, 170, 255), width=int(w * 0.4))
    # rolo (de lado): elipse + corpo
    d.rounded_rectangle([0.12 * k, 0.20 * k, 0.62 * k, 0.86 * k], radius=0.25 * k, fill=(255, 248, 232, 255),
                        outline=INK + (255,), width=w)
    d.ellipse([0.36 * k, 0.24 * k, 0.60 * k, 0.82 * k], fill=(236, 226, 205, 255), outline=INK + (255,), width=w)
    d.ellipse([0.44 * k, 0.44 * k, 0.52 * k, 0.62 * k], fill=INK + (255,))
    # espiral sugerida
    d.arc([0.40 * k, 0.33 * k, 0.56 * k, 0.73 * k], 100, 330, fill=INK + (255,), width=int(w * 0.45))
    # cruz vermelha no rolo
    cx, cy, s = 0.24 * k, 0.53 * k, 0.07 * k
    d.rectangle([cx - s * 0.38, cy - s, cx + s * 0.38, cy + s], fill=RED + (255,), outline=INK + (255,), width=int(w * 0.4))
    d.rectangle([cx - s, cy - s * 0.38, cx + s, cy + s * 0.38], fill=RED + (255,), outline=INK + (255,), width=int(w * 0.4))
    d.rectangle([cx - s * 0.38 + w * 0.4, cy - s * 0.38 + w * 0.4, cx + s * 0.38 - w * 0.4, cy + s * 0.38 - w * 0.4],
                fill=RED + (255,))
    # brilho
    d.arc([0.17 * k, 0.26 * k, 0.40 * k, 0.70 * k], 200, 250, fill=WHITE + (255,), width=int(w * 0.7))


def icon_medkit(im, d, k, w):
    # alça
    d.rounded_rectangle([0.34 * k, 0.12 * k, 0.66 * k, 0.34 * k], radius=0.07 * k, fill=INK + (255,))
    d.rounded_rectangle([0.40 * k, 0.18 * k, 0.60 * k, 0.34 * k], radius=0.04 * k, fill=(0, 0, 0, 0))
    # caixa
    box = Image.new("L", (k, k), 0)
    ImageDraw.Draw(box).rounded_rectangle([0.10 * k, 0.28 * k, 0.90 * k, 0.86 * k], radius=0.08 * k, fill=255)
    im.alpha_composite(ink_silhouette(box, RED, outline_px=9))
    # faixa da tampa
    d.line([(0.12 * k, 0.40 * k), (0.88 * k, 0.40 * k)], fill=INK + (255,), width=int(w * 0.6))
    # cruz creme com contorno
    cx, cy, s = 0.5 * k, 0.62 * k, 0.17 * k
    t = s * 0.36
    cross = [(cx - t, cy - s), (cx + t, cy - s), (cx + t, cy - t), (cx + s, cy - t), (cx + s, cy + t), (cx + t, cy + t),
             (cx + t, cy + s), (cx - t, cy + s), (cx - t, cy + t), (cx - s, cy + t), (cx - s, cy - t), (cx - t, cy - t)]
    d.polygon(wobble(cross, 0.003 * k, 9), fill=CREAM + (255,), outline=INK + (255,), width=int(w * 0.8))
    # brilho
    d.line([(0.17 * k, 0.47 * k), (0.17 * k, 0.70 * k)], fill=(255, 170, 150, 255), width=int(w * 0.8))


def icon_grenade(im, d, k, w):
    body = Image.new("L", (k, k), 0)
    b = ImageDraw.Draw(body)
    b.ellipse([0.22 * k, 0.30 * k, 0.78 * k, 0.92 * k], fill=255)
    b.rectangle([0.38 * k, 0.20 * k, 0.62 * k, 0.36 * k], fill=255)
    im.alpha_composite(ink_silhouette(body, OLIVE))
    for x in (0.37, 0.50, 0.63):
        d.line([(x * k, 0.34 * k), (x * k, 0.90 * k)], fill=INK + (255,), width=int(w * 0.45))
    for y in (0.52, 0.70):
        d.line([(0.24 * k, y * k), (0.76 * k, y * k)], fill=INK + (255,), width=int(w * 0.45))
    # alavanca e pino
    d.polygon([(0.60 * k, 0.20 * k), (0.86 * k, 0.26 * k), (0.84 * k, 0.48 * k), (0.78 * k, 0.48 * k),
               (0.78 * k, 0.31 * k), (0.60 * k, 0.28 * k)], fill=(170, 170, 160, 255), outline=INK + (255,), width=int(w * 0.6))
    d.ellipse([0.22 * k, 0.10 * k, 0.40 * k, 0.28 * k], outline=INK + (255,), width=int(w * 0.8))


def icon_lock(im, d, k, w):
    d.arc([0.28 * k, 0.10 * k, 0.72 * k, 0.60 * k], 180, 360, fill=INK + (255,), width=int(0.13 * k))
    d.arc([0.32 * k, 0.14 * k, 0.68 * k, 0.56 * k], 180, 360, fill=(190, 190, 185, 255), width=int(0.05 * k))
    body = Image.new("L", (k, k), 0)
    ImageDraw.Draw(body).rounded_rectangle([0.18 * k, 0.38 * k, 0.82 * k, 0.88 * k], radius=0.07 * k, fill=255)
    im.alpha_composite(ink_silhouette(body, YELLOW, outline_px=9))
    d.ellipse([0.44 * k, 0.52 * k, 0.56 * k, 0.64 * k], fill=INK + (255,))
    d.polygon([(0.47 * k, 0.60 * k), (0.53 * k, 0.60 * k), (0.55 * k, 0.76 * k), (0.45 * k, 0.76 * k)], fill=INK + (255,))


def make_icons():
    icons = {
        "Hand": parts_icon(icon_hand),
        "Stick": from_hud_icon("Stick", BROWN),
        "Pistol": from_hud_icon("Pistol", TEAL),
        "Shotgun": from_hud_icon("Shotgun", RED),
        "Fury": from_hud_icon("Fury", YELLOW),
        "Grenade": parts_icon(icon_grenade),
        "Medkit": parts_icon(icon_medkit),
        "Bandage": parts_icon(icon_bandage),
        "Lock": parts_icon(icon_lock),
    }
    return icons


# ---------------------------------------------------------------- prévia (mesma geometria do HUD)
def font(size, bold=True):
    for name in (("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), "arialbd.ttf", "arial.ttf"):
        for base in ("/usr/share/fonts/truetype/dejavu", "C:/Windows/Fonts", ""):
            try:
                return ImageFont.truetype(os.path.join(base, name) if base else name, size)
            except OSError:
                continue
    return ImageFont.load_default()


def tinted(im, rgb, alpha=1.0):
    r, g, b, a = im.split()
    r = r.point(lambda v: v * rgb[0] // 255)
    g = g.point(lambda v: v * rgb[1] // 255)
    b = b.point(lambda v: v * rgb[2] // 255)
    a = a.point(lambda v: int(v * alpha))
    return Image.merge("RGBA", (r, g, b, a))


def text_c(d, xy, s, f, fill, shadow=None):
    w = d.textlength(s, font=f)
    if shadow:
        d.text((xy[0] - w / 2 + 3, xy[1] + 3), s, font=f, fill=shadow)
    d.text((xy[0] - w / 2, xy[1]), s, font=f, fill=fill)


def make_mockup(sector, center, icons):
    W, H = 1920, 1080
    bg = Image.new("RGBA", (W, H), (0, 0, 0, 255))
    d = ImageDraw.Draw(bg)
    for y in range(H):  # céu alienígena
        t = y / H
        d.line([(0, y), (W, y)], fill=(int(70 + 60 * t), int(40 + 70 * t), int(110 - 30 * t), 255))
    r = rng(11)
    for i in range(26):  # árvores/cogumelos em silhueta
        x = r.uniform(0, W)
        h = r.uniform(250, 600)
        d.rectangle([x - 12, H - h, x + 12, H], fill=(30, 25, 45, 255))
        d.ellipse([x - 90, H - h - 70, x + 90, H - h + 60], fill=(40 + r.randint(0, 30), 80, 60, 255))
    d.rectangle([0, H - 140, W, H], fill=(45, 70, 40, 255))
    bg.alpha_composite(Image.new("RGBA", (W, H), (10, 8, 6, 120)))  # escurece (tempo lento)
    S = H / 1080.0
    cx, cy = W / 2, H / 2 + 10 * S
    Rw = 340 * S
    tex_size = int(2 * Rw * (WHEEL / 2) / R_OUT)
    sec = sector.resize((tex_size, tex_size), Image.LANCZOS)
    entries = [
        ("Hand", "MÃOS", None, True, False, ""),
        ("Stick", "GRAVETO ALIEN", None, True, False, ""),
        ("Pistol", "PISTOLA ALIEN", None, True, False, "8 / 32"),
        ("Shotgun", "ESCOPETA ALIEN", None, False, False, ""),
        ("Grenade", "GRANADA", None, False, True, ""),
        ("Fury", "FÚRIA", None, True, False, "x1"),
        ("Medkit", "KIT MÉDICO", None, True, False, "1/3"),
        ("Bandage", "BANDAGEM", None, True, False, "3/5"),
    ]
    sel = 7
    f_small = font(int(22 * S))
    for i, (icon, name, _, owned, future, count) in enumerate(entries):
        ang = i * 45.0
        pop = 12 * S if i == sel else 0.0
        ox = math.sin(math.radians(ang)) * pop
        oy = -math.cos(math.radians(ang)) * pop
        rot = sec.rotate(-ang, resample=Image.BICUBIC)
        shadow = tinted(rot, INK, 0.9)
        bg.alpha_composite(shadow, (int(cx - tex_size / 2 + ox + 6 * S), int(cy - tex_size / 2 + oy + 8 * S)))
        tint = GREEN if i == sel else (CREAM if owned else (150, 145, 130))
        bg.alpha_composite(tinted(rot, tint), (int(cx - tex_size / 2 + ox), int(cy - tex_size / 2 + oy)))
        ir = 0.72 * Rw
        isz = int(0.30 * Rw * (1.12 if i == sel else 1.0))
        ix = cx + math.sin(math.radians(ang)) * ir + ox
        iy = cy - math.cos(math.radians(ang)) * ir + oy - 10 * S
        ic = icons[icon].resize((isz, isz), Image.LANCZOS)
        if not owned:
            ic = tinted(ic, (120, 115, 105), 0.55)
        bg.alpha_composite(ic, (int(ix - isz / 2), int(iy - isz / 2)))
        if not owned:
            lk = icons["Lock"].resize((int(isz * 0.45), int(isz * 0.45)), Image.LANCZOS)
            bg.alpha_composite(lk, (int(ix + isz * 0.12), int(iy + isz * 0.08)))
        dd = ImageDraw.Draw(bg)
        if count:
            text_c(dd, (ix, iy + isz / 2 - 4 * S), count, f_small, INK + (255,))
    csz = int(2 * 0.40 * Rw * (WHEEL / 2) / R_OUT)
    bg.alpha_composite(tinted(center.resize((csz, csz), Image.LANCZOS), INK, 0.9), (int(cx - csz / 2 + 5 * S), int(cy - csz / 2 + 7 * S)))
    bg.alpha_composite(center.resize((csz, csz), Image.LANCZOS), (int(cx - csz / 2), int(cy - csz / 2)))
    dd = ImageDraw.Draw(bg)
    text_c(dd, (cx, cy - 78 * S), "BANDAGEM", font(int(30 * S)), INK + (255,))
    text_c(dd, (cx, cy - 30 * S), "Cura 25 de vida", font(int(22 * S), False), INK + (255,))
    text_c(dd, (cx, cy - 2 * S), "Na bolsa: 3 / 5", font(int(22 * S), False), INK + (255,))
    text_c(dd, (cx, cy + 36 * S), "SOLTE TAB PARA USAR", font(int(18 * S)), RED + (255,))
    # seta do cursor
    a = math.radians(sel * 45.0 - 8)
    tip = (cx + math.sin(a) * 0.40 * Rw * 1.02, cy - math.cos(a) * 0.40 * Rw * 1.02)
    # título e dicas
    tw = 210 * S
    dd.rounded_rectangle([cx - tw / 2 + 6 * S, cy - Rw - 92 * S + 8 * S, cx + tw / 2 + 6 * S, cy - Rw - 40 * S + 8 * S],
                         radius=10 * S, fill=INK + (255,))
    dd.rounded_rectangle([cx - tw / 2, cy - Rw - 92 * S, cx + tw / 2, cy - Rw - 40 * S], radius=10 * S,
                         fill=YELLOW + (255,), outline=INK + (255,), width=int(5 * S))
    text_c(dd, (cx, cy - Rw - 86 * S), "ITENS", font(int(34 * S)), INK + (255,))
    text_c(dd, (cx, cy + Rw + 34 * S), "Mouse / analógico: escolher     Soltar TAB: usar     Botão direito / B: cancelar",
           font(int(22 * S)), CREAM + (255,), shadow=INK + (255,))
    dd.polygon([tip, (tip[0] - 10 * S, tip[1] + 18 * S), (tip[0] + 10 * S, tip[1] + 18 * S)], fill=INK + (255,))
    # HUD de vida com contadores (como fica no canto)
    px, py = 32 * S, H - 32 * S - 96 * S
    dd.rounded_rectangle([px, py, px + 430 * S, py + 96 * S], radius=14 * S, fill=(0, 0, 0, 130))
    dd.text((px + 90 * S, py + 12 * S), "VIDA", font=font(int(20 * S)), fill=(220, 220, 230, 255))
    dd.rounded_rectangle([px + 90 * S, py + 42 * S, px + 410 * S, py + 76 * S], radius=17 * S, fill=(30, 30, 40, 255))
    dd.rounded_rectangle([px + 90 * S, py + 42 * S, px + 240 * S, py + 76 * S], radius=17 * S, fill=(242, 64, 64, 255))
    for j, (icon, cnt) in enumerate((("Bandage", "x3"), ("Medkit", "x1"))):
        bx, by = px + 440 * S, py + j * 50 * S
        dd.rounded_rectangle([bx, by, bx + 118 * S, by + 44 * S], radius=10 * S, fill=CREAM + (235,), outline=INK + (255,),
                             width=int(3 * S))
        bg.alpha_composite(icons[icon].resize((int(40 * S), int(40 * S)), Image.LANCZOS), (int(bx + 4 * S), int(by + 2 * S)))
        dd.text((bx + 50 * S, by + 8 * S), cnt, font=font(int(24 * S)), fill=INK + (255,))
    dd.text((px + 440 * S + 124 * S, py + 30 * S), "[H]", font=font(int(20 * S)), fill=CREAM + (255,))
    return bg.convert("RGB")


def main():
    os.makedirs(OUT, exist_ok=True)
    sector = make_sector()
    center = make_center()
    sector.save(os.path.join(OUT, "T_UI_Wheel_Sector.png"))
    center.save(os.path.join(OUT, "T_UI_Wheel_Center.png"))
    icons = make_icons()
    for name, im in icons.items():
        im.save(os.path.join(OUT, f"T_UI_Wheel_{name}.png"))
    make_mockup(sector, center, icons).save(os.path.join(OUT, "_mockup.png"))
    print(f"ok: {len(icons) + 2} texturas + _mockup.png em {OUT}")


if __name__ == "__main__":
    main()
