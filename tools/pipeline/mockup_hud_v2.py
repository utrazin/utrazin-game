"""Prévias do HUD v2 (sem a Unreal): refaz em Python o mesmo desenho do UI/JRHUD.cpp com as texturas geradas.

Saída: assets/work/ui/v2/_mockup_hud_pe.png, _mockup_hud_carro.png, _mockup_wheel_armas.png,
       _mockup_wheel_consumiveis.png (1920x1080).
As posições e tamanhos seguem o C++ (mesmas contas, mesma escala K = altura/1080 x HudScale).
Uso: python tools/pipeline/mockup_hud_v2.py   (depois de make_hud_v2.py)
"""
from __future__ import annotations

import json
import math
import os

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V2 = os.path.join(REPO, "assets", "work", "ui", "v2")
FONTS = os.path.join(REPO, "assets", "raw", "fonts", "fredoka")
MINIMAP = os.path.join(REPO, "assets", "work", "levels", "L01", "T_L01_Minimap_v3.png")
L = json.load(open(os.path.join(V2, "hud_v2_layout.json"), encoding="utf-8"))
P = L["panels"]
W, H = 1920, 1080
S = H / 1080.0
HUD_SCALE = 0.86
SAFE = 22.0

INK = (12, 13, 32)
NAVY = (24, 30, 62)
TEXT = (250, 250, 255)
SOFT = (196, 206, 236)
CYAN = (90, 240, 246)
LOCKED = (150, 140, 180)
YELLOW = (255, 214, 92)
ACCENT = (64, 232, 240)
HEALTH = (255, 96, 84)
OBJ = (255, 196, 40)


def rect(r):
    return r  # [x, y, w, h]


def pill_spec(name):
    return L["misc"][name]


class Canvas:
    def is_local(self):
        return self.img.shape[0] != H or self.img.shape[1] != W

    def __init__(self, bg):
        self.img = bg.astype(np.float32).copy()
        self.cache = {}
        self.fonts = {}

    # ---------------------------------------------------------------- texturas
    def tex(self, name):
        if name not in self.cache:
            p = os.path.join(V2, "T_HUD2_" + name + ".png")
            self.cache[name] = np.array(Image.open(p).convert("RGBA")).astype(np.float32) if os.path.exists(p) else None
        return self.cache[name]

    def blit(self, src, x, y, color=(255, 255, 255, 1.0), additive=False):
        h, w = src.shape[:2]
        x0, y0 = int(round(x)), int(round(y))
        ax0, ay0 = max(0, x0), max(0, y0)
        ax1, ay1 = min(self.img.shape[1], x0 + w), min(self.img.shape[0], y0 + h)
        if ax1 <= ax0 or ay1 <= ay0:
            return
        s = src[ay0 - y0:ay1 - y0, ax0 - x0:ax1 - x0]
        col = np.array(color[:3], np.float32) / 255.0
        a = s[..., 3:4] / 255.0 * color[3]
        rgb = s[..., :3] * col
        d = self.img[ay0:ay1, ax0:ax1, :3]
        if additive:
            self.img[ay0:ay1, ax0:ax1, :3] = np.clip(d + rgb * a, 0, 255)
        elif self.is_local():
            da = self.img[ay0:ay1, ax0:ax1, 3:4] / 255.0
            oa = a + da * (1 - a)
            self.img[ay0:ay1, ax0:ax1, :3] = (rgb * a + d * da * (1 - a)) / np.clip(oa, 1e-5, None)
            self.img[ay0:ay1, ax0:ax1, 3:4] = oa * 255
        else:
            self.img[ay0:ay1, ax0:ax1, :3] = d * (1 - a) + rgb * a

    def draw_tex(self, name_or_arr, x, y, w, h, color=(255, 255, 255, 1.0), uv0=(0, 0), uv1=(1, 1), additive=False):
        t = self.tex(name_or_arr) if isinstance(name_or_arr, str) else name_or_arr
        if t is None or w < 0.5 or h < 0.5:
            return
        th, tw = t.shape[:2]
        u0, v0 = uv0[0] * tw, uv0[1] * th
        u1, v1 = uv1[0] * tw, uv1[1] * th
        sub = t[int(round(v0)):max(int(round(v0)) + 1, int(round(v1))), int(round(u0)):max(int(round(u0)) + 1, int(round(u1)))]
        # alinhamento subpixel: desenha numa grade 1 px maior
        X0, Y0 = math.floor(x), math.floor(y)
        X1, Y1 = math.ceil(x + w), math.ceil(y + h)
        if X1 - X0 < 1 or Y1 - Y0 < 1:
            return
        pm = sub.copy()
        pm[..., :3] *= pm[..., 3:4] / 255.0
        res = cv2.resize(pm, (max(1, int(round(w))), max(1, int(round(h)))), interpolation=cv2.INTER_AREA if w < sub.shape[1] else cv2.INTER_CUBIC)
        res = np.clip(res, 0, 255)
        al = np.clip(res[..., 3:4], 1e-3, 255) / 255.0
        res[..., :3] = np.where(res[..., 3:4] > 0.5, res[..., :3] / al, 0)
        self.blit(res, x, y, color, additive)

    def rounded(self, x, y, w, h, r, color):
        if w <= 0 or h <= 0:
            return
        k = 3
        im = Image.new("L", (int(w * k) + 2, int(h * k) + 2), 0)
        ImageDraw.Draw(im).rounded_rectangle([0, 0, w * k, h * k], min(r, w / 2, h / 2) * k, fill=255)
        im = im.resize((max(1, int(round(w))), max(1, int(round(h)))), Image.LANCZOS)
        a = np.array(im).astype(np.float32)
        src = np.zeros(a.shape + (4,), np.float32)
        src[..., :3] = color[:3]
        src[..., 3] = a
        self.blit(src, x, y, (255, 255, 255, color[3] if len(color) > 3 else 1.0))

    def polys(self, polys):
        """[(pts, (r,g,b,a))...] com antisserrilhado 3x."""
        if not polys:
            return
        xs = [p[0] for pts, _ in polys for p in pts]
        ys = [p[1] for pts, _ in polys for p in pts]
        x0, y0 = int(min(xs)) - 2, int(min(ys)) - 2
        x1, y1 = int(max(xs)) + 3, int(max(ys)) + 3
        k = 3
        layer = Image.new("RGBA", ((x1 - x0) * k, (y1 - y0) * k), (0, 0, 0, 0))
        for pts, col in polys:
            tmp = Image.new("RGBA", layer.size, (0, 0, 0, 0))
            ImageDraw.Draw(tmp).polygon([((px - x0) * k, (py - y0) * k) for px, py in pts],
                                        fill=(int(col[0]), int(col[1]), int(col[2]), int(255 * col[3])))
            layer.alpha_composite(tmp)
        layer = layer.resize((x1 - x0, y1 - y0), Image.LANCZOS)
        self.blit(np.array(layer).astype(np.float32), x0, y0)

    def arc(self, c, rin, rout, d0, d1, color, seg=48):
        if rout <= rin or d1 <= d0:
            return
        polys = []
        for i in range(seg):
            a0 = math.radians(d0 + (d1 - d0) * i / seg)
            a1 = math.radians(d0 + (d1 - d0) * (i + 1) / seg)
            pts = [(c[0] + math.sin(a0) * rin, c[1] - math.cos(a0) * rin), (c[0] + math.sin(a0) * rout, c[1] - math.cos(a0) * rout),
                   (c[0] + math.sin(a1) * rout, c[1] - math.cos(a1) * rout), (c[0] + math.sin(a1) * rin, c[1] - math.cos(a1) * rin)]
            polys.append((pts, color))
        self.polys(polys)

    # ---------------------------------------------------------------- texto
    def font(self, bold, px):
        pts = max(6, min(220, round(px * 0.75)))
        key = (bold, pts)
        if key not in self.fonts:
            f = "Fredoka-Bold.ttf" if bold else "Fredoka-SemiBold.ttf"
            self.fonts[key] = ImageFont.truetype(os.path.join(FONTS, f), int(round(pts * 4 / 3)))
        return self.fonts[key]

    def measure(self, text, bold, px):
        if not text:
            return 0.0, 0.0
        f = self.font(bold, px)
        a, d = f.getmetrics()
        return f.getlength(text), float(a + d)

    def text(self, text, x, y, px, color, align=0, bold=True, outline=-1.0):
        if not text or (len(color) > 3 and color[3] <= 0.01):
            return 0.0
        f = self.font(bold, px)
        tw, th = self.measure(text, bold, px)
        dx = x - tw * 0.5 if align == 1 else (x - tw if align == 2 else x)
        th_ = outline if outline >= 0 else max(1.0, px * 0.085)
        alpha = color[3] if len(color) > 3 else 1.0
        pad = int(th_ * 3 + 6)
        Wl, Hl = int(tw + 2 * pad), int(th + 2 * pad)
        ox, oy = math.floor(dx) - pad, math.floor(y) - pad
        fx, fy = dx - ox, y - oy
        lay = Image.new("RGBA", (Wl, Hl), (0, 0, 0, 0))
        d = ImageDraw.Draw(lay)
        ink = INK
        if th_ > 0:
            d.text((fx, fy + th_ * 1.7), text, font=f, fill=ink + (int(255 * 0.55 * alpha),))
            steps = 12 if th_ > 2.5 else 8
            ol = Image.new("RGBA", (Wl, Hl), (0, 0, 0, 0))
            od = ImageDraw.Draw(ol)
            for i in range(steps):
                a = 2 * math.pi * i / steps
                od.text((fx + math.cos(a) * th_, fy + math.sin(a) * th_), text, font=f, fill=ink + (255,))
            oa = np.array(ol)
            oa[..., 3] = (oa[..., 3].astype(np.float32) * 0.95 * alpha).astype(np.uint8)
            lay.alpha_composite(Image.fromarray(oa))
        d2 = ImageDraw.Draw(lay)
        d2.text((fx, fy), text, font=f, fill=tuple(int(c) for c in color[:3]) + (int(255 * alpha),))
        self.blit(np.array(lay).astype(np.float32), ox, oy)
        return tw

    def text_fit(self, text, x, y, px, maxw, color, align=0, bold=True):
        size = px
        w = self.measure(text, bold, size)[0]
        if maxw > 0 and w > maxw:
            size = max(8, size * maxw / w)
        self.text(text, x, y + (px - size) * 0.45, size, color, align, bold)
        return size

    def wrap(self, text, bold, px, maxw):
        lines = []
        for para in text.split("\n"):
            line = ""
            for word in para.split():
                t = word if not line else line + " " + word
                if line and self.measure(t, bold, px)[0] > maxw:
                    lines.append(line)
                    line = word
                else:
                    line = t
            lines.append(line)
        return lines

    # ---------------------------------------------------------------- pílulas e teclas
    def pill_width(self, name, h, textw):
        p = pill_spec(name)
        unit = h / p["size"][1]
        return textw + (p["capL"] + p["capR"]) * unit * 0.62

    def three_slice(self, t, capl_px, mid_u0, mid_u1, capr_px, w, h):
        """Monta a peça de 3 fatias na resolução da textura e só então redimensiona (sem emendas)."""
        th, tw = t.shape[:2]
        unit = h / th
        capl, capr = capl_px * unit, capr_px * unit
        if capl + capr > w:
            f = w / (capl + capr)
            capl *= f
            capr *= f
        mid_w = max(0.0, w - capl - capr)
        mid_tex = max(1, int(round(mid_w / unit)))
        left = t[:, :int(round(capl_px))]
        mid = t[:, int(mid_u0 * tw):max(int(mid_u0 * tw) + 1, int(mid_u1 * tw))]
        mid = cv2.resize(mid, (mid_tex, th), interpolation=cv2.INTER_LINEAR)
        right = t[:, tw - int(round(capr_px)):]
        return np.concatenate([left, mid, right], 1)

    def pill(self, name, x, y, w, h, color=(255, 255, 255, 1.0)):
        p = pill_spec(name)
        t = self.tex(name)
        tw = p["size"][0]
        full = self.three_slice(t, p["capL"], (p["capL"] + 0.5) / tw, (p["capL"] + p["mid"] - 0.5) / tw, p["capR"], w, h)
        self.draw_tex(full, x, y, w, h, color)

    def keycap(self, key, x, y, h):
        ts = h * (0.46 if len(key) > 1 else 0.56)
        tw = self.measure(key, True, ts)[0]
        w = max(h, tw + h * 0.55)
        t = self.tex("Key")
        full = self.three_slice(t, 0.36 * t.shape[1], 0.36, 0.64, 0.36 * t.shape[1], w, h)
        self.draw_tex(full, x, y, w, h)
        th = self.measure(key, True, ts)[1]
        self.text(key, x + w * 0.5, y + h * 0.40 - th * 0.5, ts, INK, 1, True, 0)
        return w

    def diamond(self, c, r, color):
        o = r + 2.5 * S
        dark = INK + (0.95,)
        cx, cy = c
        self.polys([([(cx, cy - o), (cx + o, cy), (cx, cy + o), (cx - o, cy)], dark),
                    ([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], color + (1.0,)),
                    ([(cx, cy - r * 0.8), (cx + r * 0.45, cy - r * 0.3), (cx - r * 0.45, cy - r * 0.3)], (255, 255, 255, 0.45))])

    def arrow(self, c, yaw, r, color):
        a = math.radians(yaw)

        def tri(sc, col):
            return ([(c[0] + math.cos(a) * r * sc, c[1] + math.sin(a) * r * sc),
                     (c[0] + math.cos(a + 2.45) * r * 0.8 * sc, c[1] + math.sin(a + 2.45) * r * 0.8 * sc),
                     (c[0] + math.cos(a - 2.45) * r * 0.8 * sc, c[1] + math.sin(a - 2.45) * r * 0.8 * sc)], col)
        self.polys([tri(1.45, INK + (0.95,)), tri(1.0, color + (1.0,))])

    def map_ellipse(self, mapimg, c, rx, ry, uvc, uvh, tint=None, alpha=1.0):
        x0, x1 = int(c[0] - rx) - 1, int(c[0] + rx) + 2
        y0, y1 = int(c[1] - ry) - 1, int(c[1] + ry) + 2
        yy, xx = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        lx = (xx - c[0]) / rx
        ly = (yy - c[1]) / ry
        q = lx * lx + ly * ly
        m = np.clip((1.0 - np.sqrt(q)) * rx, 0, 1)[..., None]
        if mapimg is not None:
            mh, mw = mapimg.shape[:2]
            mxp = ((uvc[0] + lx * uvh[0]) * mw).astype(np.float32)
            myp = ((uvc[1] + ly * uvh[1]) * mh).astype(np.float32)
            src = cv2.remap(mapimg, mxp, myp, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
        else:
            src = np.zeros((y1 - y0, x1 - x0, 4), np.float32)
            src[..., :3] = tint
            src[..., 3] = 255
        src[..., 3:4] = src[..., 3:4] * m
        self.blit(src, x0, y0, (255, 255, 255, alpha))


# ====================================================================== fundo
def background(seed=3, car=False):
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    sky_top = np.array([60, 28, 92], np.float32)
    sky_hor = np.array([214, 120, 150], np.float32)
    ground = np.array([30, 70, 78], np.float32)
    t = np.clip(yy / (H * 0.55), 0, 1)[..., None]
    img = sky_top * (1 - t) + sky_hor * t
    g = np.clip((yy - H * 0.55) / (H * 0.45), 0, 1)[..., None]
    img = img * (1 - (g > 0)) + (ground * (0.7 + 0.5 * (1 - g)) + np.array([20, 10, 30]) * g) * (g > 0)
    im = Image.fromarray(np.clip(img, 0, 255).astype(np.uint8))
    d = ImageDraw.Draw(im)
    d.ellipse([1250, 120, 1650, 520], fill=(236, 170, 200))
    d.ellipse([1180, 290, 1720, 350], outline=(250, 210, 230), width=10)
    for i in range(26):
        x = rng.uniform(-50, W + 50)
        h_ = rng.uniform(250, 560)
        wv = rng.uniform(40, 110)
        base = H * 0.62 + rng.uniform(-20, 60)
        col = tuple(int(c) for c in (np.array([28, 20, 52]) + rng.uniform(0, 30)))
        d.rectangle([x - wv * 0.12, base - h_, x + wv * 0.12, base], fill=col)
        d.ellipse([x - wv, base - h_ - wv * 0.8, x + wv, base - h_ + wv * 0.8], fill=(col[0] + 40, col[1] + 10, col[2] + 70))
    if car:
        d.polygon([(760, H), (900, 640), (1020, 640), (1160, H)], fill=(80, 70, 100))
        d.rounded_rectangle([780, 760, 1140, 930], 40, fill=(70, 90, 120))
    else:
        d.ellipse([910, 600, 1010, 700], fill=(80, 60, 110))
        d.rounded_rectangle([900, 690, 1020, 960], 40, fill=(60, 80, 120))
    im = im.filter(ImageFilter.GaussianBlur(9))
    arr = np.array(im.convert("RGBA")).astype(np.float32)
    arr[..., 3] = 255
    return arr


# ====================================================================== partes (iguais ao C++)
def K():
    return S * HUD_SCALE


def panel_point(origin, k, x, y):
    return (origin[0] + x * k, origin[1] + y * k)


def draw_objective(cv, driving, text, hint="", wave=""):
    k = K()
    m = SAFE * S
    origin = (m, m)
    name = "ObjCar" if driving else "ObjHero"
    pp = P[name]
    size = pp["size"]
    title = pp["title"]
    body = pp["body"]
    cv.draw_tex(name, origin[0], origin[1], size[0] * k, size[1] * k)
    ts = 34 * k
    tc = panel_point(origin, k, title[0] + title[2] / 2, title[1] + title[3] / 2)
    th = cv.measure("OBJETIVO", True, ts)[1]
    cv.text("OBJETIVO", tc[0], tc[1] - th * 0.5, ts, TEXT, 1)
    if wave:
        wp = panel_point(origin, k, title[0] + title[2] + 8, title[1] + title[3] / 2)
        cv.text(wave, wp[0], wp[1] - cv.measure(wave, True, 22 * k)[1] * 0.5, 22 * k, YELLOW, 0)
    bw = body[2] * k
    bs = 25 * k
    lines = cv.wrap(text, False, bs, bw)
    while len(lines) > 2 and bs > 14 * k:
        bs *= 0.92
        lines = cv.wrap(text, False, bs, bw)
    lh = cv.measure("Ág", False, bs)[1] * 0.92
    bp = panel_point(origin, k, body[0], body[1] + body[3] * 0.5)
    ly = bp[1] - lh * len(lines) * 0.5
    for ln in lines:
        cv.text(ln, bp[0], ly, bs, TEXT, 0, False)
        ly += lh
    if hint:
        hs = 20 * k
        ph = 44 * k
        hw = cv.measure(hint, False, hs)[0]
        pw = min(cv.pill_width("PillNavy", ph, hw), W * 0.45)
        px = origin[0] + 24 * k
        py = origin[1] + size[1] * k + 2 * k
        cv.pill("PillNavy", px, py, pw, ph)
        hh = cv.measure(hint, False, hs)[1]
        cv.text_fit(hint, px + pw * 0.5, py + ph * 0.45 - hh * 0.5, hs, pw - 40 * k, YELLOW, 1, False)


def draw_minimap(cv, driving, mapimg, pawn_uv, yaw, target_uv, enemies_uv, dist):
    k = K()
    m = SAFE * S
    name = "MapCar" if driving else "MapHero"
    pp = P[name]
    size = pp["size"]
    ell = pp["ellipse"]
    title = pp["title"]
    origin = (W - m - size[0] * k, m)
    c = panel_point(origin, k, ell[0], ell[1])
    rx, ry = ell[2] * k, ell[3] * k
    cv.map_ellipse(None, c, rx, ry, None, None, NAVY)
    span = (520 if driving else 260) * 100.0
    world = 200000.0
    cm_per_px = span / (2 * rx)
    uvh = (rx * cm_per_px / world, ry * cm_per_px / world)
    uvc = (min(max(pawn_uv[0], uvh[0]), 1 - uvh[0]), min(max(pawn_uv[1], uvh[1]), 1 - uvh[1]))
    cv.map_ellipse(mapimg, c, rx, ry, uvc, uvh)
    cv.map_ellipse(None, c, rx, ry, None, None, NAVY, 0.18)

    def to_screen(uv):
        return (c[0] + (uv[0] - uvc[0]) / uvh[0] * rx, c[1] + (uv[1] - uvc[1]) / uvh[1] * ry)

    def q(p):
        return ((p[0] - c[0]) / rx) ** 2 + ((p[1] - c[1]) / ry) ** 2
    for e in enemies_uv:
        p = to_screen(e)
        if q(p) < 0.86:
            cv.rounded(p[0] - 5 * k, p[1] - 5 * k, 10 * k, 10 * k, 5 * k, INK + (0.9,))
            cv.rounded(p[0] - 3.5 * k, p[1] - 3.5 * k, 7 * k, 7 * k, 3.5 * k, HEALTH + (1.0,))
    p = to_screen(target_uv)
    qq = q(p)
    out = qq > 0.72
    if out:
        f = 0.85 / math.sqrt(qq)
        p = (c[0] + (p[0] - c[0]) * f, c[1] + (p[1] - c[1]) * f)
    cv.diamond(p, (9 if out else 12) * k, OBJ)
    cv.arrow(to_screen(pawn_uv), yaw, 11 * k, CYAN)
    cv.draw_tex(name, origin[0], origin[1], size[0] * k, size[1] * k)
    ts = 32 * k
    tc = panel_point(origin, k, title[0] + title[2] / 2, title[1] + title[3] / 2)
    cv.text("MINIMAPA", tc[0], tc[1] - cv.measure("MINIMAPA", True, ts)[1] * 0.5, ts, TEXT, 1)
    if not driving:
        nh = cv.measure("N", True, 20 * k)[1]
        cv.text("N", c[0], c[1] - ry + 4 * k - nh * 0.1, 20 * k, TEXT + (0.85,), 1)
    rowy = origin[1] + size[1] * k + 4 * k
    ph = 40 * k
    dt = f"OBJETIVO  {dist} m"
    ts2 = 19 * k
    tw = cv.measure(dt, True, ts2)[0]
    kw = 34 * k
    pw = cv.pill_width("PillNavy", ph, tw + kw + 10 * k)
    px = c[0] - pw * 0.5
    cv.pill("PillNavy", px, rowy, pw, ph)
    inner = px + (pw - (tw + kw + 10 * k)) * 0.5
    cv.keycap("M", inner, rowy + ph * 0.5 - 15 * k, 30 * k)
    cv.text(dt, inner + kw + 10 * k, rowy + ph * 0.45 - cv.measure(dt, True, ts2)[1] * 0.5, ts2, YELLOW, 0)


def seg_bar(cv, fill, origin, k, which, pct, trail, tint=(255, 255, 255, 1.0)):
    bar = P["BotHero"]["barA" if which == 0 else "barB"]
    br = bar["rect"]
    segs = bar["segments"]
    n = len(segs)
    for i, sg in enumerate(segs):
        f0, f1 = i / n, (i + 1) / n
        lit = min(max((pct - f0) / (f1 - f0), 0), 1)
        ghost = min(max((trail - f0) / (f1 - f0), 0), 1)
        pad = 2
        x0 = max(br[0], sg[0] - pad)
        y0 = max(br[1], sg[1] - pad)
        x1 = min(br[0] + br[2], sg[0] + sg[2] + pad)
        y1 = min(br[1] + br[3], sg[1] + sg[3] + pad)
        uv0 = ((x0 - br[0]) / br[2], (y0 - br[1]) / br[3])
        uv1 = ((x1 - br[0]) / br[2], (y1 - br[1]) / br[3])
        p0 = panel_point(origin, k, x0, y0)
        if ghost > lit:
            cv.draw_tex(fill, p0[0], p0[1], (x1 - x0) * k, (y1 - y0) * k, (255, 255, 255, (ghost - lit) * 0.85), uv0, uv1, True)
        if lit > 0:
            cv.draw_tex(fill, p0[0], p0[1], (x1 - x0) * k, (y1 - y0) * k, tint[:3] + (tint[3] * lit,), uv0, uv1)


def cont_bar(cv, fill, origin, k, which, pct, trail):
    bar = P["BotCar"]["bar" + "ABC"[which]]
    br = bar["rect"]
    span = bar["span"]

    def part(a, b, color, add):
        a = min(max(a, br[0]), br[0] + br[2])
        b = min(max(b, br[0]), br[0] + br[2])
        if b - a < 0.5:
            return
        p0 = panel_point(origin, k, a, br[1])
        cv.draw_tex(fill, p0[0], p0[1], (b - a) * k, br[3] * k, color, ((a - br[0]) / br[2], 0), ((b - br[0]) / br[2], 1), add)
    ln = span[1] - span[0]
    xe = br[0] + br[2] if pct >= 0.999 else span[0] + ln * pct
    xt = span[0] + ln * trail
    if xt > xe:
        part(xe, xt, (255, 255, 255, 0.8), True)
    if pct > 0.001:
        part(br[0], xe, (255, 255, 255, 1.0), False)


def draw_hero(cv, hp=72, hpmax=100, trail=0.86, fury_left=6.0, fury_charges=1, bandages=3, medkits=1):
    k = K()
    m = SAFE * S
    bh = P["BotHero"]
    origin = (m, H - m - bh["size"][1] * k)
    cv.draw_tex("BotHero", origin[0], origin[1], bh["size"][0] * k, bh["size"][1] * k)
    seg_bar(cv, "BotHero_FillA", origin, k, 0, hp / hpmax, trail)
    seg_bar(cv, "BotHero_FillB", origin, k, 1, fury_left / 10.0, fury_left / 10.0)
    ls, vs = 30 * k, 22 * k

    def label(r, t):
        p = panel_point(origin, k, r[0], r[1] + r[3] * 0.5)
        cv.text(t, p[0], p[1] - cv.measure(t, True, ls)[1] * 0.5, ls, TEXT, 0)

    def value(r, t, col):
        p = panel_point(origin, k, r[0] + r[2], r[1] + r[3] * 0.5)
        cv.text(t, p[0], p[1] - cv.measure(t, True, vs)[1] * 0.5, vs, col, 2)
    label(bh["barA"]["label"], "VIDA")
    value(bh["barA"]["value"], f"{hp} / {hpmax}", SOFT)
    label(bh["barB"]["label"], "FÚRIA")
    value(bh["barB"]["value"], f"ATIVA {int(math.ceil(fury_left))}s" if fury_left > 0 else (f"GUARDADAS x{fury_charges}" if fury_charges else "VAZIA"),
          (217, 255, 102) if fury_left > 0 else SOFT)
    # bolsa de cura
    x, y = origin[0] + 200 * k, origin[1] - 2 * k
    chip = 84 * k
    cx = x
    for icon, cnt in (("Icon_Bandage", bandages), ("Icon_Medkit", medkits)):
        cv.draw_tex("Badge", cx, y - chip, chip, chip, (255, 255, 255, 1.0 if cnt else 0.75))
        isz = chip * 0.78
        cv.draw_tex(icon, cx + (chip - isz) / 2, y - chip + (chip - isz) / 2, isz, isz, (255, 255, 255, 1.0) if cnt else (90, 85, 115, 0.8))
        cv.text(f"x{cnt}", cx + chip * 0.98, y - chip * 0.42, 24 * k, TEXT + ((1.0 if cnt else 0.5),), 2)
        cx += chip + 8 * k
    cv.keycap("H", cx + 4 * k, y - chip * 0.5 - 15 * k, 30 * k)
    cv.text("curar", cx + 40 * k, y - chip * 0.5 - 12 * k, 19 * k, SOFT, 0, False)


def draw_weapon(cv, name="PISTOLA ALIEN", icon="Icon_Pistol", mag=9, magsize=12, reserve=36, equipped=True):
    k = K()
    m = SAFE * S
    wp = P["Weapon"]
    origin = (W - m - wp["size"][0] * k, H - m - wp["size"][1] * k)
    cv.draw_tex("Weapon", origin[0], origin[1], wp["size"][0] * k, wp["size"][1] * k)
    ring = panel_point(origin, k, wp["ring"][0], wp["ring"][1])
    isz = wp["ring"][2] * 2.05 * k
    cv.draw_tex(icon, ring[0] - isz / 2, ring[1] - isz / 2, isz, isz)
    body = wp["body"]
    ns = 26 * k
    nw = cv.measure(name, True, ns)[0]
    ph = 50 * k
    pw = min(cv.pill_width("PillTeal", ph, nw), body[2] * k)
    bp = panel_point(origin, k, body[0], body[1])
    px = bp[0] + (body[2] * k - pw) * 0.5
    cv.pill("PillTeal", px, bp[1] + 4 * k, pw, ph)
    cv.text_fit(name, px + pw / 2, bp[1] + 4 * k + ph * 0.42 - cv.measure(name, True, ns)[1] * 0.5, ns, pw - 50 * k, TEXT, 1)
    right = bp[0] + body[2] * k
    rowy = bp[1] + 66 * k
    if equipped:
        rt = f"/ {reserve}"
        big, small = 60 * k, 30 * k
        rw = cv.measure(rt, True, small)[0]
        bigh = cv.measure("0", True, big)[1]
        smallh = cv.measure("0", True, small)[1]
        cv.text(rt, right, rowy + bigh * 0.62 - smallh * 0.62, small, CYAN, 2)
        cv.text(str(mag), right - rw - 8 * k, rowy, big, TEXT if mag else HEALTH, 2)
        cv.draw_tex("Stat_Ammo", bp[0] + 4 * k, rowy + 6 * k, 46 * k, 46 * k)
        cv.text("MUNIÇÃO", bp[0] + 50 * k, rowy + 14 * k, 22 * k, SOFT, 0)
        pipy = rowy + bigh + 2 * k
        area = body[2] * k - 8 * k
        gap = 4 * k
        pipw = min(26 * k, (area - gap * (magsize - 1)) / magsize)
        piph = 14 * k
        sx = right - (pipw * magsize + gap * (magsize - 1))
        for i in range(magsize):
            x = sx + i * (pipw + gap)
            fill = min(max(mag - i, 0), 1)
            cv.rounded(x - 1.5 * k, pipy - 1.5 * k, pipw + 3 * k, piph + 3 * k, 5 * k, INK + (0.95,))
            cv.rounded(x, pipy, pipw, piph, 4 * k, (52, 50, 92, 1.0))
            if fill:
                cv.rounded(x, pipy, pipw, piph, 4 * k, ACCENT + (fill,))
                cv.rounded(x + 2 * k, pipy + 2 * k, pipw - 4 * k, piph * 0.35, 2 * k, (255, 255, 255, 0.35))
    else:
        cv.text("MÃOS LIVRES", right, rowy + 14 * k, 32 * k, SOFT, 2)
    hy = origin[1] + 6 * k
    hx = origin[0] + 230 * k
    hx += cv.keycap("Q", hx, hy, 28 * k) + 6 * k
    hx += cv.text("trocar", hx, hy + 2 * k, 19 * k, SOFT, 0, False) + 16 * k
    hx += cv.keycap("TAB", hx, hy, 28 * k) + 6 * k
    cv.text("roda", hx, hy + 2 * k, 19 * k, SOFT, 0, False)


def draw_crosshair(cv):
    cx, cy = W / 2, H / 2
    gap, ln, t = 14 * S, 12 * S, max(2, 3 * S)
    for x, y, w, h in ((cx - gap - ln, cy - t / 2, ln, t), (cx + gap, cy - t / 2, ln, t), (cx - t / 2, cy - gap - ln, t, ln),
                       (cx - t / 2, cy + gap, t, ln), (cx - t / 2, cy - t / 2, t, t)):
        cv.rounded(x - 1.5, y - 1.5, w + 3, h + 3, min(w, h) / 2 + 1.5, INK + (0.75,))
        cv.rounded(x, y, w, h, min(w, h) / 2, (255, 255, 255, 1.0))


def draw_prompt(cv, line):
    ts = 26 * S
    ph = 58 * S
    kh = 40 * S
    tw = cv.measure(line, True, ts)[0]
    pw = cv.pill_width("PillNavy", ph, tw + kh + 14 * S)
    bx = W / 2 - pw / 2
    by = H * 0.66
    cv.pill("PillNavy", bx, by, pw, ph)
    ix = bx + (pw - (tw + kh + 14 * S)) / 2
    cv.keycap("E", ix, by + ph * 0.45 - kh / 2, kh)
    cv.text(line, ix + kh + 14 * S, by + ph * 0.44 - cv.measure(line, True, ts)[1] / 2, ts, TEXT, 0)


def draw_toasts(cv, toasts):
    ts = 23 * S
    ph = 50 * S
    y = H * 0.73
    for t, col in toasts:
        tw = cv.measure(t, True, ts)[0]
        pw = min(cv.pill_width("PillNavy", ph, tw), W * 0.7)
        cv.pill("PillNavy", W / 2 - pw / 2, y, pw, ph)
        cv.text_fit(t, W / 2, y + ph * 0.44 - cv.measure(t, True, ts)[1] / 2, ts, pw - 46 * S, col, 1)
        y += ph + 6 * S


def draw_world_marker(cv, x, y, dist):
    cv.diamond((x, y), 14 * S, OBJ)
    t = f"{dist} m"
    ts = 19 * S
    ph = 34 * S
    pw = cv.pill_width("PillNavy", ph, cv.measure(t, True, ts)[0])
    cv.pill("PillNavy", x - pw / 2, y + 20 * S, pw, ph, (255, 255, 255, 0.9))
    cv.text(t, x, y + 20 * S + ph * 0.45 - cv.measure(t, True, ts)[1] / 2, ts, YELLOW, 1)


def draw_vehicle(cv, integ=0.62, trail=0.74, fuel=1.0, nitro=0.55, kmh=87, nitro_on=False):
    k = K()
    m = SAFE * S
    bc = P["BotCar"]
    origin = (m, H - m - bc["size"][1] * k)
    cv.draw_tex("BotCar", origin[0], origin[1], bc["size"][0] * k, bc["size"][1] * k)
    cont_bar(cv, "BotCar_FillA", origin, k, 0, integ, trail)
    cont_bar(cv, "BotCar_FillB", origin, k, 1, fuel, fuel)
    cont_bar(cv, "BotCar_FillC", origin, k, 2, nitro, nitro)
    ls, vs = 26 * k, 21 * k

    def label(r, t):
        p = panel_point(origin, k, r[0], r[1] + r[3] * 0.5)
        cv.text(t, p[0], p[1] - cv.measure(t, True, ls)[1] * 0.5, ls, TEXT, 0)

    def value(r, t, col):
        p = panel_point(origin, k, r[0] + r[2], r[1] + r[3] * 0.5)
        cv.text(t, p[0], p[1] - cv.measure(t, True, vs)[1] * 0.5, vs, col, 2)
    label(bc["barA"]["label"], "VIDA DO CARRO")
    value(bc["barA"]["value"], f"{round(integ * 100)}%", SOFT)
    label(bc["barB"]["label"], "GASOLINA")
    value(bc["barB"]["value"], "CHEIO" if fuel > 0.5 else "VAZIO", SOFT if fuel > 0.5 else HEALTH)
    label(bc["barC"]["label"], "NITRO")
    value(bc["barC"]["value"], "ATIVO!" if nitro_on else f"{round(nitro * 100)}%", SOFT)
    bs = 230 * k
    c = (W - m - bs / 2, H - m - bs / 2)
    cv.draw_tex("Badge", c[0] - bs / 2, c[1] - bs / 2, bs, bs)
    arc_r = bs * 0.5 * (66 / 92)
    cv.arc(c, arc_r - 15 * k, arc_r - 5 * k, -135, 135, INK + (0.7,))
    cv.arc(c, arc_r - 14 * k, arc_r - 6 * k, -135, -135 + 270 * min(kmh / 160, 1), (236, 252, 255, 1.0))
    st = str(kmh)
    sh = cv.measure(st, True, 56 * k)[1]
    cv.text(st, c[0], c[1] - sh * 0.62, 56 * k, TEXT, 1)
    cv.text("km/h", c[0], c[1] + 14 * k, 22 * k, SOFT, 1)
    kh = 30 * k
    kw = cv.measure("SHIFT", True, kh * 0.5)[0] + kh * 0.55
    cv.keycap("SHIFT", c[0] - kw / 2, c[1] + bs / 2 - kh * 1.25, kh)


# ====================================================================== roda
def wheel_entries(tab):
    pistol_stats = (math.sqrt(25 / 120), 1 - 1.5 / 8, math.sqrt(4 / 8), math.sqrt(6000 / 20000))
    shotgun_stats = (math.sqrt(min(12 * 8, 120) / 120), max(0.06, 1 - 6 / 8), math.sqrt(1.2 / 8), math.sqrt(2500 / 20000))
    sniper_stats = (1.0, 1 - 0.1 / 8, math.sqrt((1 / 1.2) / 8), 1.0)
    melee_stats = (math.sqrt(40 / 120), 0.9, math.sqrt((1 / 0.55) / 8), max(0.06, math.sqrt(170 / 20000)))
    if tab == 0:
        return [
            dict(name="NADA", cat="SEM ARMA", icon="Hand", owned=True, detail="Guarda a arma\nCorre e interage com as mãos livres"),
            dict(name="GRAVETO ALIEN", cat="CORPO A CORPO", icon="Stick", owned=True, stats=melee_stats),
            dict(name="PISTOLA ALIEN", cat="ARMA DE FOGO", icon="Pistol", owned=True, current=True, loaded=9, reserve=36, stats=pistol_stats),
            dict(name="ESCOPETA ALIEN", cat="ARMA DE FOGO", icon="Shotgun", owned=True, loaded=6, reserve=39, stats=shotgun_stats),
            dict(name="RIFLE ALIEN", cat="ARMA DE FOGO", icon="Sniper", owned=False, stats=sniper_stats, detail="Ainda não encontrada"),
            dict(name="GRANADA", cat="EM BREVE", icon="Grenade", owned=False, future=True, detail="Ainda não existe nesta fase"),
            dict(empty=True), dict(empty=True)]
    return [
        dict(name="NADA", cat="CONSUMÍVEIS", icon="Hand", owned=True, detail="Fecha a roda sem usar nada"),
        dict(name="BANDAGEM", cat="CURA", icon="Bandage", owned=True, count=3, maxc=5, detail="Cura 25 de vida"),
        dict(name="KIT MÉDICO", cat="CURA", icon="Medkit", owned=True, count=1, maxc=3, detail="Cura 60 de vida"),
        dict(name="FÚRIA", cat="PODER", icon="Fury", owned=False, count=0, maxc=2, detail="Dano e cadência maiores\npor 10 s"),
        dict(name="CHAVE DO CARRO", cat="ITEM-CHAVE", icon="CarKey", owned=True, key=True, detail="Liga o carro: chegue perto e aperte E"),
        dict(name="GALÃO", cat="ITEM-CHAVE", icon="Fuel", owned=False, key=True, detail="Ainda não encontrado\n(ou já usado)"),
        dict(name="EXPLOSIVO", cat="ITEM-CHAVE", icon="Explosive", owned=False, key=True, detail="Ainda não encontrado\n(ou já usado)"),
        dict(empty=True)]


def draw_wheel(cv, tab, highlight):
    wl = L["wheel"]
    cv.img[..., :3] = cv.img[..., :3] * (1 - 0.55) + np.array(INK, np.float32) * 0.55
    k = H * 0.80 / wl["size"][1]
    mid = (W / 2, H * 0.51)
    tc = wl["center"]
    origin = (mid[0] - tc[0] * k, mid[1] - tc[1] * k)
    cv.draw_tex("Wheel", origin[0], origin[1], wl["size"][0] * k, wl["size"][1] * k)
    names = ["ARMAS", "CONSUMÍVEIS"]
    tab_h = 80 * k
    tts = 38 * k
    tab_y = origin[1] + 2 * k
    ws = [max(300 * k, cv.pill_width("PillTeal", tab_h, cv.measure(n, True, tts)[0])) for n in names]
    gap = 14 * k
    tw = ws[0] + ws[1] + gap
    tx = mid[0] - tw / 2
    top = tab_y - tab_h - 22 * k
    for i, n in enumerate(names):
        act = i == tab
        lift = 4 * k if act else 0
        cv.pill("PillTeal" if act else "PillLavender", tx, top - lift, ws[i], tab_h, (255, 255, 255, 1.0 if act else 0.85))
        th = cv.measure(n, True, tts)[1]
        cv.text(n, tx + ws[i] / 2, top - lift + tab_h * 0.42 - th / 2, tts, TEXT if act else SOFT, 1)
        tx += ws[i] + gap
    kh = 52 * k
    cv.keycap("Q", mid[0] - tw / 2 - kh - 14 * k, top + tab_h * 0.45 - kh / 2, kh)
    cv.keycap("E", mid[0] + tw / 2 + 14 * k, top + tab_h * 0.45 - kh / 2, kh)
    entries = wheel_entries(tab)
    sel = None
    for s_, e in enumerate(entries):
        cell = wl["cells"][s_]
        r = cell["rect"]
        cp = panel_point(origin, k, r[0], r[1])
        is_sel = s_ == highlight
        if is_sel:
            sel = e
        empty = e.get("empty", False)
        locked = not empty and (not e.get("owned") or e.get("future"))
        if is_sel:
            cv.draw_tex(f"WheelCell{s_}_Glow", cp[0], cp[1], r[2] * k, r[3] * k)
        elif empty or locked:
            cv.draw_tex(f"WheelCell{s_}_Mask", cp[0], cp[1], r[2] * k, r[3] * k, INK + (0.45 if empty else 0.3,))
        if empty:
            continue
        cc = cell["center"]
        d = np.array([cc[0] - tc[0], cc[1] - tc[1]])
        d = d / np.linalg.norm(d)
        ic = (origin[0] + cc[0] * k - d[0] * 6 * k, origin[1] + cc[1] * k - d[1] * 6 * k)
        isz = 262 * k * (1.1 if is_sel else 1.0)
        tint = (82, 77, 107, 0.75) if locked else (255, 255, 255, 1.0)
        cv.draw_tex("Icon_" + e["icon"], ic[0] - isz / 2, ic[1] - isz / 2, isz, isz, tint)
        if locked:
            ls = isz * 0.42
            cv.draw_tex("Icon_Lock", ic[0] + isz * 0.18 - ls / 2, ic[1] + isz * 0.16 - ls / 2, ls, ls)
        amt = ""
        if not locked and "loaded" in e:
            amt = f"{e['loaded']}/{e['reserve']}"
        elif "count" in e:
            amt = f"x{e['count']}"
        if amt:
            cv.text(amt, ic[0] + isz * 0.36, ic[1] + isz * 0.22, 30 * k, LOCKED if locked else TEXT, 2)
        if e.get("current"):
            dp = (ic[0] - isz * 0.36, ic[1] - isz * 0.3)
            ds = 40 * k
            cv.draw_tex("Glow", dp[0] - ds, dp[1] - ds, ds * 2, ds * 2, ACCENT + (0.7,), additive=True)
            cv.rounded(dp[0] - 14 * k, dp[1] - 14 * k, 28 * k, 28 * k, 14 * k, INK + (1.0,))
            cv.rounded(dp[0] - 11 * k, dp[1] - 11 * k, 22 * k, 22 * k, 11 * k, TEXT + (1.0,))
            cv.rounded(dp[0] - 7 * k, dp[1] - 7 * k, 14 * k, 14 * k, 7 * k, ACCENT + (1.0,))
    # ponteiro
    hd = highlight * 45.0
    hdir = (math.sin(math.radians(hd)), -math.cos(math.radians(hd)))
    pr = (wl["disc_radius"] + 34) * k
    pt = cv.tex("Pointer")
    size = 62 * k
    rot = Image.fromarray(pt.astype(np.uint8)).rotate(-(hd - 90), resample=Image.BICUBIC)
    cv.draw_tex(np.array(rot).astype(np.float32), mid[0] + hdir[0] * pr - size / 2, mid[1] + hdir[1] * pr - size / 2, size, size)
    wheel_center(cv, sel, mid, k)
    # dicas
    hs = 19 * S
    hph = 44 * S
    a, b, c = "mouse / analógico: escolher", "soltar: usar", "botão direito / B: cancelar"
    wa, wb, wc = (cv.measure(t, False, hs)[0] for t in (a, b, c))
    inner = wa + wb + wc + 64 * S + 70 * S
    pw = cv.pill_width("PillNavy", hph, inner)
    hy = min(H - hph - 8 * S, origin[1] + wl["size"][1] * k + 4 * S)
    hx = mid[0] - pw / 2
    cv.pill("PillNavy", hx, hy, pw, hph)
    x = hx + (pw - inner) / 2
    ty = hy + hph * 0.44 - cv.measure(a, False, hs)[1] / 2
    x += cv.text(a, x, ty, hs, SOFT, 0, False) + 24 * S
    x += cv.keycap("TAB", x, hy + hph / 2 - 15 * S, 30 * S) + 6 * S
    x += cv.text(b, x, ty, hs, TEXT, 0, False) + 24 * S
    cv.text(c, x, ty, hs, SOFT, 0, False)


def wheel_center(cv, e, mid, k):
    r = L["wheel"]["disc_radius"] * k
    locked = not e.get("empty") and (not e.get("owned") or e.get("future"))
    pnw = r * 1.66
    has_amount = ("loaded" in e and not locked) or "count" in e or e.get("key")
    detail = [] if "stats" in e else cv.wrap(e.get("detail", ""), False, 25 * k, pnw - 44 * k)
    ch = (52 * k if has_amount else 0) + (4 * 44 * k if "stats" in e else len(detail) * 33 * k) + 18 * k
    block = 38 * k + 76 * k + 12 * k + ch + 14 * k + 30 * k
    y = mid[1] - block * 0.5
    cv.text(e.get("cat", ""), mid[0], y, 27 * k, CYAN, 1)
    y += 38 * k
    ns = 46 * k
    ph = 76 * k
    nw = cv.measure(e["name"], True, ns)[0]
    pw = min(cv.pill_width("PillTeal", ph, nw), r * 1.78)
    cv.pill("PillLavender" if locked else "PillTeal", mid[0] - pw / 2, y, pw, ph)
    cv.text_fit(e["name"], mid[0], y + ph * 0.42 - cv.measure(e["name"], True, ns)[1] / 2, ns, pw - 60 * k, TEXT, 1)
    y += ph + 12 * k
    pnx = mid[0] - pnw / 2
    rx = pnx + 22 * k
    rr = pnx + pnw - 20 * k
    ry = y + 12 * k
    rs = 27 * k
    isz = 42 * k
    ptop = y
    cv.rounded(pnx, y, pnw, ch, 22 * k, INK + (0.35,))
    lab, val = "", ""
    if "loaded" in e and not locked:
        lab, val = "MUNIÇÃO:", f"{e['loaded']} / {e['reserve']}"
    elif "count" in e:
        lab, val = ("CARGAS:" if e["icon"] == "Fury" else "NA BOLSA:"), f"{e['count']} / {e['maxc']}"
    elif e.get("key"):
        lab, val = "STATUS:", "NA MOCHILA" if e["owned"] else "FALTA"
    if lab:
        icon = "Stat_Ammo" if "loaded" in e else "Icon_" + e["icon"]
        cv.draw_tex(icon, rx - 4 * k, ry - 4 * k, isz, isz)
        cv.text(lab, rx + isz + 4 * k, ry + 2 * k, rs, TEXT, 0)
        cv.text(val, rr, ry - 2 * k, 34 * k, CYAN if e.get("owned") else LOCKED, 2)
        ry += 52 * k
    if "stats" in e:
        rows = [("DANO", "Stat_Damage"), ("PRECISÃO", "Stat_Accuracy"), ("CADÊNCIA", "Stat_FireRate"), ("ALCANCE", "Stat_Range")]
        n = 5
        bw = 160 * k
        sg = 4 * k
        sw = (bw - sg * (n - 1)) / n
        sh = 18 * k
        sk = 6 * k
        for (lb, ic), v in zip(rows, e["stats"]):
            cv.draw_tex(ic, rx - 4 * k, ry - 4 * k, isz, isz)
            cv.text(lb, rx + isz + 4 * k, ry, 24 * k, TEXT, 0)
            bx = rr - bw
            by = ry + 6 * k
            cv.rounded(bx - 6 * k, by - 4 * k, bw + 12 * k, sh + 8 * k, (sh + 8 * k) / 2, INK + (0.85,))
            lit = v * n
            polys = []
            for i in range(n):
                sx = bx + i * (sw + sg)
                f = min(max(lit - i, 0), 1)
                off = np.array([92, 84, 140], np.float32)
                top = off * (1 - f) + np.array([150, 255, 252]) * f
                polys.append(([(sx + sk, by), (sx + sw + sk, by), (sx + sw - sk, by + sh), (sx - sk, by + sh)], tuple(top) + (1.0,)))
            cv.polys(polys)
            ry += 44 * k
    else:
        for ln in detail:
            cv.text(ln, mid[0], ry, 25 * k, SOFT, 1, False)
            ry += 33 * k
    if e.get("future"):
        act, col = "EM BREVE", LOCKED
    elif e.get("key"):
        act, col = ("USADO SOZINHO", SOFT) if e["owned"] else ("BLOQUEADO", LOCKED)
    elif not e.get("owned"):
        act, col = "BLOQUEADO", LOCKED
    elif e.get("current"):
        act, col = "NA MÃO", CYAN
    elif "count" in e:
        act, col = "SOLTE PARA USAR", YELLOW
    else:
        act, col = "SOLTE PARA EQUIPAR", YELLOW
    cv.text(act, mid[0], ptop + ch + 12 * k, 26 * k, col, 1)


# ====================================================================== cenas
def main():
    mapimg = np.array(Image.open(MINIMAP).convert("RGBA")).astype(np.float32) if os.path.exists(MINIMAP) else None
    enemies = [(0.52, 0.47), (0.55, 0.44), (0.47, 0.5), (0.6, 0.52), (0.5, 0.56)]
    # a pé
    cv = Canvas(background(3))
    draw_world_marker(cv, 1210, 380, 86)
    draw_crosshair(cv)
    draw_objective(cv, False, "Siga a pé pelas vilas até a nave caída", hint="Dica: abra o baú da barraca para achar a chave")
    draw_minimap(cv, False, mapimg, (0.52, 0.5), -60, (0.7, 0.42), enemies, 86)
    draw_hero(cv)
    draw_weapon(cv)
    draw_prompt(cv, "Abrir baú")
    draw_toasts(cv, [("Pegou: bandagem (3/5)", (255, 255, 255)), ("+12 células", (90, 240, 246))])
    Image.fromarray(np.clip(cv.img, 0, 255).astype(np.uint8)).convert("RGB").save(os.path.join(V2, "_mockup_hud_pe.png"))
    # carro
    cv = Canvas(background(5, car=True))
    draw_world_marker(cv, 980, 330, 412)
    draw_objective(cv, True, "Atravesse o vale alienígena até o desembarque")
    draw_minimap(cv, True, mapimg, (0.62, 0.62), -90, (0.62, 0.3), enemies, 412)
    draw_vehicle(cv)
    draw_toasts(cv, [("Nitro pronto!", (190, 150, 255))])
    Image.fromarray(np.clip(cv.img, 0, 255).astype(np.uint8)).convert("RGB").save(os.path.join(V2, "_mockup_hud_carro.png"))
    # roda
    for tab, hl, out in ((0, 2, "_mockup_wheel_armas.png"), (1, 1, "_mockup_wheel_consumiveis.png")):
        cv = Canvas(background(3))
        draw_objective(cv, False, "Siga a pé pelas vilas até a nave caída")
        draw_minimap(cv, False, mapimg, (0.52, 0.5), -60, (0.7, 0.42), enemies, 86)
        draw_hero(cv)
        draw_weapon(cv)
        draw_wheel(cv, tab, hl)
        Image.fromarray(np.clip(cv.img, 0, 255).astype(np.uint8)).convert("RGB").save(os.path.join(V2, out))
    print("prévias em", V2)


if __name__ == "__main__":
    main()
