#!/usr/bin/env python3
"""Procedural, seamlessly tileable stylized textures for Unreal Engine.

Generates albedo (T_<Name>_D.png, sRGB) + DirectX-convention normal maps
(T_<Name>_N.png, green down) from a height field built alongside the albedo.
All noise is periodic (FFT-based / periodic Voronoi / wrapped stamping) so
every texture tiles without seams.

Usage: python3 make_textures.py [out_dir] [material ...]   (material = function name, e.g. toxic)
License: original work, CC0.
"""
import os
import sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.spatial import cKDTree

N = 1024
OUT = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))


# ----------------------------------------------------------------- helpers
def rng(seed):
    return np.random.default_rng(seed)


def norm01(a):
    a = a - a.min()
    m = a.max()
    return a / m if m > 0 else a


def fft_noise(seed, beta=2.0, fmin=1.0, fmax=None, n=N):
    """Periodic fractal noise: power spectrum ~ 1/f^beta, band-limited.
    fmin/fmax are in cycles per tile (integer frequencies -> tileable)."""
    r = rng(seed)
    fx = np.fft.fftfreq(n) * n
    fy = np.fft.rfftfreq(n) * n
    f = np.sqrt(fx[:, None] ** 2 + fy[None, :] ** 2)
    amp = np.zeros_like(f)
    m = f >= fmin
    if fmax is not None:
        m &= f <= fmax
    amp[m] = f[m] ** (-beta / 2.0)
    if fmax is not None:  # soft roll-off near fmax to avoid ringing
        amp *= np.clip((fmax - f) / (0.25 * fmax + 1e-6), 0, 1)
    phase = r.uniform(0, 2 * np.pi, f.shape)
    spec = amp * np.exp(1j * phase) * r.normal(1.0, 0.25, f.shape)
    return norm01(np.fft.irfft2(spec, s=(n, n)))


def blur(a, s):
    if a.ndim == 3:
        return np.stack([ndimage.gaussian_filter(a[..., i], s, mode="wrap") for i in range(a.shape[2])], -1)
    return ndimage.gaussian_filter(a, s, mode="wrap")


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def warp(a, dx, dy):
    """Periodic domain warp (dx, dy in pixels)."""
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    return ndimage.map_coordinates(a, [yy + dy, xx + dx], order=1, mode="grid-wrap")


def voronoi(npts, seed, k=2, pts=None):
    """Periodic Voronoi: returns distances (k, N, N) and nearest ids."""
    r = rng(seed)
    if pts is None:
        pts = r.uniform(0, N, (npts, 2))
    tree = cKDTree(pts, boxsize=N)
    yy, xx = np.mgrid[0:N, 0:N]
    q = np.stack([xx.ravel() + 0.5, yy.ravel() + 0.5], -1)
    d, i = tree.query(q, k=k)
    d = d.T.reshape(k, N, N)
    i = i.T.reshape(k, N, N)
    return d, i, pts


def lerp(a, b, t):
    t = np.asarray(t)
    if t.ndim == 2 and np.ndim(a) <= 1 and np.ndim(b) <= 1:
        t = t[..., None]
    elif t.ndim == 2:
        t = t[..., None]
    return a + (b - a) * t


def col(hexs):
    hexs = hexs.lstrip("#")
    return np.array([int(hexs[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def wrap_offsets(x, y, rad):
    offs = [0]
    xs = [0] + ([N] if x - rad < 0 else []) + ([-N] if x + rad > N else [])
    ys = [0] + ([N] if y - rad < 0 else []) + ([-N] if y + rad > N else [])
    return [(a, b) for a in xs for b in ys]


class Canvas:
    """Float canvas built from PIL 'L' layers drawn with wrap-around."""

    def __init__(self, mode="L"):
        self.img = Image.new(mode, (N, N), 0)
        self.d = ImageDraw.Draw(self.img)

    def line(self, pts, fill, width, rad=None):
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        cx, cy = np.mean(xs), np.mean(ys)
        r = rad or (max(max(xs) - min(xs), max(ys) - min(ys)) + width)
        for ox, oy in wrap_offsets(cx, cy, r):
            self.d.line([(x + ox, y + oy) for x, y in pts], fill=fill, width=width, joint="curve")

    def ellipse(self, cx, cy, rx, ry, fill):
        for ox, oy in wrap_offsets(cx, cy, max(rx, ry) + 2):
            self.d.ellipse([cx - rx + ox, cy - ry + oy, cx + rx + ox, cy + ry + oy], fill=fill)

    def polygon(self, pts, fill):
        cx = np.mean([p[0] for p in pts]); cy = np.mean([p[1] for p in pts])
        r = max(max(abs(p[0] - cx), abs(p[1] - cy)) for p in pts) + 2
        for ox, oy in wrap_offsets(cx, cy, r):
            self.d.polygon([(x + ox, y + oy) for x, y in pts], fill=fill)

    def arr(self):
        return np.asarray(self.img, dtype=np.float32) / 255.0


def normal_from_height(h, strength):
    """Tangent-space normal, DirectX convention (green = -dh/dv, i.e. green down)."""
    dx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    dy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5   # +row = down in image
    nx = -dx * strength
    ny_gl = dy * strength          # OpenGL: green points up (toward smaller row)
    ny = -ny_gl                    # DirectX: flip green
    nz = np.ones_like(h)
    l = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
    n = np.stack([nx / l, ny / l, nz / l], -1)
    return (n * 0.5 + 0.5)


def save(name, albedo, height, slope, blur_h=0.8):
    """slope = target mean surface slope (|grad h|), used to auto-scale the normal map."""
    albedo = np.clip(albedo, 0.04, 0.94)
    if blur_h:
        height = blur(height, blur_h)
    Image.fromarray((albedo * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(OUT, f"T_{name}_D.png"))
    h = height.astype(np.float64)
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * 0.5
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * 0.5
    strength = slope / (np.sqrt(gx ** 2 + gy ** 2).mean() + 1e-9)
    nrm = normal_from_height(h, strength)
    Image.fromarray((nrm * 255 + 0.5).astype(np.uint8), "RGB").save(os.path.join(OUT, f"T_{name}_N.png"))
    print("wrote", name)


def shade(albedo, height, amount=0.25):
    """Bake a bit of painted light/AO from height into the albedo (stylized)."""
    h = blur(height, 1.5)
    dx = np.roll(h, -2, 1) - np.roll(h, 2, 1)
    dy = np.roll(h, -2, 0) - np.roll(h, 2, 0)
    light = -(dx * 0.6 + dy * 0.8)  # light from top-left
    light = np.tanh(light * 8.0)
    cav = h - blur(h, 12)
    f = 1.0 + amount * (0.6 * light + 2.0 * cav)
    return albedo * f[..., None]


def palette_map(t, stops):
    """Map scalar 0..1 to colors through (pos, hex) stops."""
    pos = np.array([s[0] for s in stops])
    cs = np.array([col(s[1]) for s in stops])
    out = np.empty(t.shape + (3,))
    for c in range(3):
        out[..., c] = np.interp(t, pos, cs[:, c])
    return out


def posterize_soft(t, levels, softness=0.35):
    """Soft banding for a hand-painted feel."""
    s = t * levels
    f = np.floor(s)
    fr = s - f
    fr = smoothstep(0.5 - softness, 0.5 + softness, fr)
    return (f + fr) / levels


# --------------------------------------------------------------- materials
def grass():
    r = rng(11)
    low = fft_noise(101, 3.0, 1, 10)
    mid = fft_noise(102, 2.2, 3, 40)
    t = posterize_soft(0.6 * low + 0.4 * mid, 5, 0.3)
    alb = palette_map(t, [(0, "#3a6e28"), (0.45, "#518c31"), (0.75, "#679f3a"), (1, "#7db045")])
    # painted blade strokes on separate light/dark layers + height
    light = Canvas(); dark = Canvas(); hgt = Canvas()
    for i in range(5200):
        x, y = r.uniform(0, N, 2)
        L = r.uniform(14, 30)
        ang = np.deg2rad(-90 + r.normal(0, 22))
        bend = r.normal(0, 0.35)
        pts = []
        for s in np.linspace(0, 1, 5):
            a = ang + bend * s
            pts.append((x + np.cos(a) * L * s, y + np.sin(a) * L * s))
        w = int(r.integers(2, 5))
        tone = r.random()
        v = int(r.uniform(140, 255))
        (light if tone > 0.45 else dark).line(pts, v, w)
        hgt.line(pts, int(r.uniform(150, 255)), w)
    lt = blur(light.arr(), 0.8); dk = blur(dark.arr(), 0.8)
    alb = lerp(alb, alb * np.array([1.22, 1.18, 0.95]) + np.array([0.03, 0.04, 0.0]), lt * 0.75)
    alb = lerp(alb, alb * np.array([0.72, 0.8, 0.72]), dk * 0.7)
    h = 0.5 * blur(hgt.arr(), 1.0) + 0.5 * low
    alb = shade(alb, h, 0.12)
    save("Grass", alb, h, 0.22, 1.2)


def pebbles(seed, count, rmin, rmax):
    r = rng(seed)
    c = Canvas(); ids = Canvas()
    for i in range(count):
        x, y = r.uniform(0, N, 2)
        rad = r.uniform(rmin, rmax)
        k = int(r.integers(6, 10))
        angs = np.sort(r.uniform(0, 2 * np.pi, k))
        pts = [(x + np.cos(a) * rad * r.uniform(0.7, 1.1), y + np.sin(a) * rad * r.uniform(0.6, 1.0)) for a in angs]
        c.polygon(pts, 255)
        ids.polygon(pts, int(r.integers(1, 255)))
    m = c.arr()
    dist = ndimage.distance_transform_edt(np.tile(m > 0.5, (3, 3)))[N:2 * N, N:2 * N]
    return m, ids.arr(), dist


def cracks(seed, npts, width, coverage, wiggle=6):
    d, _, _ = voronoi(npts, seed)
    e = d[1] - d[0]
    nx = (fft_noise(seed + 1, 2, 2, 30) - 0.5) * 2 * wiggle
    ny = (fft_noise(seed + 2, 2, 2, 30) - 0.5) * 2 * wiggle
    e = warp(e, nx, ny)
    line = 1 - smoothstep(0, width, e)
    mask = smoothstep(1 - coverage - 0.1, 1 - coverage + 0.1, fft_noise(seed + 3, 2.5, 1, 12))
    return line * mask


def dirt():
    low = fft_noise(201, 3.0, 1, 10)
    mid = fft_noise(202, 2.0, 4, 60)
    t = posterize_soft(0.55 * low + 0.45 * mid, 4, 0.3)
    alb = palette_map(t, [(0, "#6b4528"), (0.5, "#8a5c35"), (1, "#a77447")])
    m, ids, dist = pebbles(203, 420, 4, 11)
    pv = ids
    pcol = palette_map(pv, [(0, "#7c6a58"), (0.5, "#9a8670"), (1, "#b39c80")])
    dome = np.clip(dist / 5.0, 0, 1)
    alb = lerp(alb, pcol * (0.85 + 0.25 * dome[..., None]), m)
    shadow = blur(np.roll(np.roll(m, 3, 0), 2, 1), 2) * (1 - m)
    alb *= (1 - 0.35 * shadow)[..., None]
    cr = cracks(204, 70, 2.2, 0.55)
    alb = lerp(alb, alb * 0.55, cr)
    h = 0.35 * low + 0.15 * mid + 0.45 * m * (0.5 + 0.5 * dome) - 0.35 * cr
    alb = shade(alb, h, 0.15)
    save("Dirt", alb, h, 0.25)


def gravel():
    low = fft_noise(301, 3.0, 1, 10)
    mid = fft_noise(302, 2.0, 4, 60)
    t = posterize_soft(0.5 * low + 0.5 * mid, 4, 0.3)
    alb = palette_map(t, [(0, "#5e4f40"), (0.5, "#776654"), (1, "#8c7b67")])
    # dense stones from periodic voronoi
    r = rng(303)
    pts = r.uniform(0, N, (2600, 2))
    d, i, _ = voronoi(0, 0, pts=pts)
    cellv = r.random(len(pts))
    keep = r.random(len(pts)) < 0.78
    sv = cellv[i[0]]
    gap = d[1] - d[0]
    stone = smoothstep(1.0, 3.5, gap) * keep[i[0]]
    dome = np.clip(np.sqrt(np.clip(gap, 0, None)) / 3.0, 0, 1)
    scol = palette_map(sv, [(0, "#5f5a54"), (0.35, "#746d65"), (0.7, "#887e72"), (1, "#958e85")])
    # tire tracks: two soft vertical bands, stones sparser/flattened there
    xx = np.arange(N)[None, :].repeat(N, 0)
    tw = (fft_noise(304, 3, 1, 4) - 0.5) * 40
    track = np.zeros((N, N))
    for c in (300, 724):
        dd = np.abs(((xx + tw - c + N / 2) % N) - N / 2)
        track = np.maximum(track, 1 - smoothstep(55, 85, dd))
    stone *= 1 - 0.55 * track * (sv > 0.4)
    alb = lerp(alb, scol * (0.82 + 0.3 * dome[..., None]), stone)
    alb *= (1 - 0.12 * track)[..., None]
    h = 0.25 * low + 0.55 * stone * dome - 0.15 * track + 0.1 * mid
    alb = shade(alb, h, 0.18)
    save("Gravel", alb, h, 0.4)


def rock():
    r = rng(401)
    # large faceted plates: each cell gets a random tilted plane
    pts = r.uniform(0, N, (55, 2))
    d, i, _ = voronoi(0, 0, pts=pts)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = pts[i[0]]
    rx = ((xx - c[..., 0] + N / 2) % N) - N / 2
    ry = ((yy - c[..., 1] + N / 2) % N) - N / 2
    sx = r.normal(0, 0.006, len(pts))[i[0]]
    sy = (r.normal(0, 0.006, len(pts)) - 0.004)[i[0]]
    base = r.uniform(0.3, 0.7, len(pts))[i[0]]
    plane = base + sx * rx + sy * ry
    edge = d[1] - d[0]
    crack = 1 - smoothstep(0, 5, edge)
    bevel = smoothstep(0, 18, edge)
    # medium facets
    pts2 = r.uniform(0, N, (300, 2))
    d2, i2, _ = voronoi(0, 0, pts=pts2)
    c2 = pts2[i2[0]]
    rx2 = ((xx - c2[..., 0] + N / 2) % N) - N / 2
    ry2 = ((yy - c2[..., 1] + N / 2) % N) - N / 2
    plane2 = r.normal(0, 0.004, len(pts2))[i2[0]] * rx2 + r.normal(0, 0.004, len(pts2))[i2[0]] * ry2
    e2 = d2[1] - d2[0]
    crack2 = (1 - smoothstep(0, 2.5, e2)) * smoothstep(0.45, 0.6, fft_noise(402, 2.5, 1, 10))
    n = fft_noise(403, 2.2, 3, 50)
    h = plane * bevel * 0.8 + plane2 * 0.25 + 0.12 * n - 0.25 * crack2 - 0.3 * crack
    h = norm01(h)
    cellt = r.random(len(pts))[i[0]]
    t = posterize_soft(0.5 * cellt + 0.3 * n + 0.2 * norm01(plane2), 5, 0.25)
    alb = palette_map(t, [(0, "#5f5850"), (0.4, "#7a7067"), (0.75, "#8f857a"), (1, "#a1968a")])
    # warm brown streaks
    br = smoothstep(0.55, 0.75, fft_noise(404, 3, 1, 8))
    alb = lerp(alb, alb * np.array([1.1, 0.95, 0.8]), br * 0.6)
    alb = lerp(alb, alb * 0.45, np.maximum(crack, crack2))
    alb = shade(alb, h, 0.35)
    save("Rock", alb, h, 0.28)


def concrete():
    low = fft_noise(501, 3.0, 1, 8)
    mid = fft_noise(502, 2.0, 4, 60)
    t = 0.6 * low + 0.4 * mid
    alb = palette_map(t, [(0, "#8f8e8a"), (0.5, "#a3a29e"), (1, "#b4b3ae")])
    st = smoothstep(0.6, 0.8, fft_noise(503, 3.2, 1, 10))
    st2 = smoothstep(0.62, 0.78, fft_noise(504, 2.5, 2, 20))
    alb = lerp(alb, alb * np.array([0.82, 0.8, 0.74]), st * 0.7)
    alb = lerp(alb, alb * 0.86, st2 * 0.6)
    # sparse pores (low density, slightly blurred)
    r = rng(505)
    pore = Canvas()
    for _ in range(500):
        x, y = r.uniform(0, N, 2)
        rr = r.uniform(1.2, 3.0)
        pore.ellipse(x, y, rr, rr, 255)
    p = blur(pore.arr(), 0.7)
    cr = cracks(506, 25, 1.8, 0.35, wiggle=10)
    alb = lerp(alb, alb * 0.7, p * 0.6)
    alb = lerp(alb, alb * 0.5, cr)
    h = 0.3 * low + 0.15 * mid - 0.3 * p - 0.4 * cr
    alb = shade(alb, h, 0.1)
    save("Concrete", alb, h, 0.12)


def wood():
    r = rng(601)
    boards = 4
    bh = N // boards
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    bidx = (yy // bh).astype(int)
    by = yy % bh
    alb = np.zeros((N, N, 3)); h = np.zeros((N, N))
    gap = np.zeros((N, N))
    wn = fft_noise(602, 2.6, 1, 20)
    fine = fft_noise(603, 1.5, 8, 120)
    nails = Canvas()
    tones = ["#7a4f2c", "#8c5c34", "#6f4728", "#93633a"]
    for b in range(boards):
        m = bidx == b
        # board end seams (vertical joints) at random x
        nseam = int(r.integers(0, 2)) + 1
        seams = np.sort(r.uniform(0, N, nseam))
        seg = np.zeros((N, N), int)
        for s in seams:
            seg += (xx >= s)
        seg %= nseam
        # grain: stretched sinusoid warped by noise, periodic in x
        freq = r.uniform(9, 14)
        ph = r.uniform(0, 10, nseam)[seg]
        g = np.sin((by / bh * freq + 6 * (wn - 0.5) + 0.8 * np.sin(2 * np.pi * (xx / N * 2 + b)) + ph) * np.pi)
        g = 0.5 + 0.5 * g
        g = posterize_soft(g, 3, 0.3)
        g = 0.7 * g + 0.3 * fine
        base = col(tones[b]) * r.uniform(0.95, 1.05, nseam)[seg][..., None]
        bcol = lerp(base * 0.78, base * 1.18, g)
        alb[m] = bcol[m]
        h[m] = (0.5 + 0.15 * g + 0.1 * fine)[m]
        # gaps between boards and at seams
        gy = np.minimum(by, bh - 1 - by)
        gm = 1 - smoothstep(1.5, 4.5, gy)
        for s in seams:
            dxs = np.abs(((xx - s + N / 2) % N) - N / 2)
            gm = np.maximum(gm, 1 - smoothstep(1.0, 3.5, dxs))
            for ny_ in (0.25, 0.75):
                for sx in (-14, 14):
                    nails.ellipse((s + sx) % N, b * bh + bh * ny_, 4.5, 4.5, 255)
        gap[m] = gm[m]
        # edge bevel darkening
        bev = 1 - smoothstep(3, 14, gy)
        alb[m] *= (1 - 0.25 * bev[m])[..., None]
        h[m] -= 0.15 * bev[m]
    na = nails.arr()
    alb = lerp(alb, alb * 0.35 + np.array([0.12, 0.11, 0.1]), na)
    alb = lerp(alb, np.array([0.17, 0.11, 0.07]), gap)
    h = h - 0.5 * gap + 0.12 * na
    alb = shade(alb, h, 0.12)
    save("Wood", alb, h, 0.2)


def rustmetal():
    paint = col("#4d7a80")
    low = fft_noise(701, 3.0, 1, 10)
    mid = fft_noise(702, 2.0, 4, 60)
    alb = paint[None, None, :] * (0.88 + 0.22 * posterize_soft(low, 4))[..., None]
    rust_n = 0.65 * fft_noise(703, 2.6, 1, 30) + 0.35 * mid
    rust = smoothstep(0.55, 0.6, rust_n)
    rim = smoothstep(0.5, 0.55, rust_n) - rust          # worn paint rim (bare metal)
    rt = posterize_soft(fft_noise(704, 2.0, 4, 80), 4, 0.3)
    rcol = palette_map(rt, [(0, "#6b3a1f"), (0.4, "#8f4c22"), (0.75, "#b0632a"), (1, "#c27b3a")])
    alb = lerp(alb, np.array([0.55, 0.53, 0.5]), rim * 0.8)
    alb = lerp(alb, rcol, rust)
    # streaks below rust (vertical drip)
    drip = blur(rust, 1)
    drips = np.zeros_like(drip)
    for k in range(1, 40, 3):
        drips = np.maximum(drips, np.roll(drip, k, 0) * (1 - k / 40))
    dn = smoothstep(0.4, 0.7, fft_noise(705, 1.2, 20, 200))  # vertical-ish via stretch below
    alb = lerp(alb, alb * np.array([1.05, 0.85, 0.7]), np.clip(drips - rust, 0, 1) * 0.35)
    # scratches
    r = rng(706)
    sc = Canvas()
    for _ in range(140):
        x, y = r.uniform(0, N, 2)
        a = r.normal(0.3, 0.6)
        L = r.uniform(25, 110)
        pts = [(x, y), (x + np.cos(a) * L * 0.5 + r.normal(0, 3), y + np.sin(a) * L * 0.5 + r.normal(0, 3)),
               (x + np.cos(a) * L, y + np.sin(a) * L)]
        sc.line(pts, int(r.uniform(120, 255)), int(r.integers(1, 3)))
    s = blur(sc.arr(), 0.6) * (1 - rust)
    alb = lerp(alb, np.array([0.66, 0.65, 0.62]), s * 0.8)
    h = 0.5 + 0.08 * low - 0.12 * rust + 0.1 * rust * fft_noise(707, 1.5, 10, 150) - 0.15 * s - 0.05 * rim
    alb = shade(alb, h, 0.12)
    save("RustMetal", alb, h, 0.15)


def zombieskin():
    low = fft_noise(801, 3.0, 1, 10)
    mid = fft_noise(802, 2.2, 3, 50)
    t = posterize_soft(0.6 * low + 0.4 * mid, 4, 0.35)
    alb = palette_map(t, [(0, "#6f7f62"), (0.5, "#839273"), (1, "#97a385")])
    bruise = smoothstep(0.62, 0.8, fft_noise(803, 3.0, 1, 12))
    alb = lerp(alb, col("#6e5a78"), bruise * 0.65)
    yellow = smoothstep(0.6, 0.78, fft_noise(804, 3.0, 1, 12))
    alb = lerp(alb, alb * np.array([1.08, 1.05, 0.82]), yellow * 0.5)
    # veins: ridged periodic noise
    vn = fft_noise(805, 2.4, 3, 40)
    vn2 = fft_noise(806, 2.0, 6, 70)
    rid = 1 - np.abs(vn - 0.5) * 2
    rid2 = 1 - np.abs(vn2 - 0.5) * 2
    veins = smoothstep(0.93, 0.985, rid) * smoothstep(0.35, 0.65, fft_noise(807, 2.5, 1, 10))
    veins2 = smoothstep(0.95, 0.99, rid2) * 0.6 * smoothstep(0.4, 0.7, fft_noise(808, 2.5, 1, 10))
    v = blur(np.maximum(veins, veins2), 0.8)
    alb = lerp(alb, col("#4f4a5e"), v * 0.75)
    blot = smoothstep(0.65, 0.8, mid) * 0.35
    alb = lerp(alb, alb * 0.82, blot)
    # dried blood speckles
    r = rng(809)
    sp = Canvas()
    cluster = fft_noise(810, 3, 1, 8)
    for _ in range(900):
        x, y = r.uniform(0, N, 2)
        if cluster[int(y) % N, int(x) % N] < 0.55:
            continue
        rr = r.uniform(1.0, 3.2)
        sp.ellipse(x, y, rr, rr * r.uniform(0.6, 1), int(r.uniform(150, 255)))
    s = blur(sp.arr(), 0.6)
    alb = lerp(alb, col("#5a2420"), s * 0.85)
    pores = fft_noise(811, 1.0, 40, 160)
    h = 0.35 * low + 0.15 * mid + 0.25 * v + 0.05 * pores + 0.05 * s
    alb = shade(alb, h, 0.1)
    save("ZombieSkin", alb, h, 0.15)


def cloth():
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    threads = 96  # integer count -> periodic
    jitter = (fft_noise(901, 2.5, 2, 30) - 0.5) * 3
    u = (xx + jitter) / N * threads * 2 * np.pi
    v = (yy - jitter) / N * threads * 2 * np.pi
    warpT = 0.5 + 0.5 * np.sin(u)
    weftT = 0.5 + 0.5 * np.sin(v)
    checker = np.sign(np.sin(u / 2) * np.sin(v / 2))
    weave = np.where(checker > 0, warpT * (0.6 + 0.4 * weftT), weftT * (0.6 + 0.4 * warpT))
    low = fft_noise(902, 3.0, 1, 10)
    alb = palette_map(0.5 * low + 0.5 * posterize_soft(fft_noise(903, 2.2, 2, 30), 4),
                      [(0, "#837c70"), (0.5, "#978f81"), (1, "#a9a191")])
    alb *= (0.9 + 0.12 * weave)[..., None]
    # stains with darker rims
    sn = fft_noise(904, 3.0, 1, 14)
    stain = smoothstep(0.62, 0.68, sn)
    rimm = smoothstep(0.6, 0.64, sn) - smoothstep(0.66, 0.7, sn)
    alb = lerp(alb, alb * np.array([0.85, 0.8, 0.7]), stain * 0.6)
    alb = lerp(alb, alb * np.array([0.7, 0.65, 0.56]), np.clip(rimm, 0, 1) * 0.6)
    dirtn = smoothstep(0.5, 0.8, fft_noise(905, 2.5, 2, 25))
    alb = lerp(alb, alb * 0.8, dirtn * 0.5)
    # tears: ragged dark holes with frayed light edges
    tn = fft_noise(906, 2.2, 2, 40)
    tearmask = smoothstep(0.72, 0.85, fft_noise(907, 3, 1, 6))
    tv = tn * tearmask
    hole = smoothstep(0.66, 0.68, tv)
    fray = smoothstep(0.58, 0.66, tv) - hole
    alb = lerp(alb, alb * 1.12, np.clip(fray, 0, 1) * 0.6)
    alb = lerp(alb, np.array([0.13, 0.12, 0.11]), hole)
    h = 0.5 + 0.25 * weave + 0.15 * low - 0.6 * hole + 0.05 * fray
    alb = shade(alb, h, 0.08)
    save("Cloth", alb, h, 0.3, 0.5)


def grunge():
    a = fft_noise(1001, 2.4, 1, 30)
    b = fft_noise(1002, 1.8, 4, 90)
    g = 0.6 * a + 0.4 * b
    base = 0.8 + 0.18 * norm01(blur(b, 1.5))
    spots = smoothstep(0.62, 0.85, g)
    r = rng(1003)
    sp = Canvas()
    for _ in range(300):
        x, y = r.uniform(0, N, 2)
        rr = r.uniform(1.5, 6)
        sp.ellipse(x, y, rr, rr, int(r.uniform(100, 255)))
    s = blur(sp.arr(), 1.0)
    out = base * (1 - 0.35 * spots) * (1 - 0.25 * s)
    out = np.clip(out, 0.45, 0.98)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(OUT, "T_Detail_Grunge.png"))
    print("wrote Detail_Grunge")


# ------------------------------------------------------- alien materials
def blades(seed, count, lmin, lmax, wmin=2, wmax=5, spread=22, tip=0.45):
    """Painted grass blades: returns (body, tips, height) float layers."""
    r = rng(seed)
    body = Canvas(); tips = Canvas(); hgt = Canvas()
    for _ in range(count):
        x, y = r.uniform(0, N, 2)
        L = r.uniform(lmin, lmax)
        ang = np.deg2rad(-90 + r.normal(0, spread))
        bend = r.normal(0, 0.35)
        pts = []
        for s in np.linspace(0, 1, 6):
            a = ang + bend * s
            pts.append((x + np.cos(a) * L * s, y + np.sin(a) * L * s))
        w = int(r.integers(wmin, wmax))
        body.line(pts, int(r.uniform(140, 255)), w)
        k = int(round(6 * (1 - tip)))
        tips.line(pts[k - 1:], int(r.uniform(170, 255)), max(1, w - 1))
        hgt.line(pts, int(r.uniform(150, 255)), w)
    return blur(body.arr(), 0.8), blur(tips.arr(), 0.8), blur(hgt.arr(), 1.0)


def vein_network(seed, npts=60, width=2.6, wiggle=14, fine=True):
    """Tileable branching vein network (0..1), thick trunks + thin branches."""
    def edge_dist(n, sd):
        d, i, pts = voronoi(n, sd)
        dp = pts[i[1]] - pts[i[0]]
        dp = (dp + N / 2) % N - N / 2
        return (d[1] ** 2 - d[0] ** 2) / (2 * np.sqrt((dp ** 2).sum(-1)) + 1e-6)  # true distance to cell edge

    e = edge_dist(npts, seed)
    wx = (fft_noise(seed + 1, 2.2, 2, 24) - 0.5) * 2 * wiggle
    wy = (fft_noise(seed + 2, 2.2, 2, 24) - 0.5) * 2 * wiggle
    e = warp(e, wx, wy)
    wmod = 0.55 + 0.9 * fft_noise(seed + 3, 2.5, 1, 8)
    v = 1 - smoothstep(0, width * wmod, e)
    v *= smoothstep(0.3, 0.5, fft_noise(seed + 4, 2.5, 2, 12))  # gaps -> open branches
    if fine:
        e2 = warp(edge_dist(npts * 5, seed + 10), wx * 0.6, wy * 0.6)
        v2 = (1 - smoothstep(0, 1.2 * wmod, e2)) * smoothstep(0.5, 0.7, fft_noise(seed + 5, 2.5, 1, 10))
        v = np.maximum(v, 0.7 * v2)
    return np.clip(blur(v, 0.7), 0, 1)


def organic_veins(seed, width=1.0):
    """Tileable organic vein web from ridged periodic noise contours (0..1)."""
    out = np.zeros((N, N))
    for k, (f0, f1, thr, amt) in enumerate([(2, 14, 0.965, 1.0), (3, 26, 0.975, 0.8), (6, 48, 0.982, 0.55)]):
        n = fft_noise(seed + 10 * k, 2.6, f0, f1)
        wx = (fft_noise(seed + 10 * k + 1, 2.4, 2, 20) - 0.5) * 30
        wy = (fft_noise(seed + 10 * k + 2, 2.4, 2, 20) - 0.5) * 30
        rid = 1 - np.abs(warp(n, wx, wy) - 0.5) * 2
        t = thr - (1 - thr) * (width - 1) * 2 - 0.02 * fft_noise(seed + 10 * k + 3, 2.5, 1, 8)
        line = smoothstep(t, t + (1 - t) * 0.6, rid)
        line *= smoothstep(0.3 + 0.1 * k, 0.5 + 0.1 * k, fft_noise(seed + 10 * k + 4, 2.5, 1, 8))
        out = np.maximum(out, line * amt)
    return np.clip(blur(out, 0.7), 0, 1)


def alien_grass():
    low = fft_noise(1101, 3.0, 1, 8)
    mid = fft_noise(1102, 2.2, 3, 30)
    t = posterize_soft(0.65 * low + 0.35 * mid, 5, 0.3)
    alb = palette_map(t, [(0, "#1d5463"), (0.45, "#24707c"), (0.75, "#2f8a8e"), (1, "#3c9d9a")])
    blot = smoothstep(0.55, 0.8, blur(fft_noise(1103, 3.2, 1, 7), 6))
    alb = lerp(alb, col("#4a4a8e"), blot * 0.35)
    body, tips, hb = blades(1104, 5200, 14, 30, tip=0.55)
    tone = fft_noise(1105, 2.0, 4, 60)
    alb = lerp(alb, alb * np.array([1.15, 1.25, 1.2]) + 0.02, body * (tone > 0.45) * 0.7)
    alb = lerp(alb, alb * np.array([0.72, 0.78, 0.85]), body * (tone <= 0.45) * 0.6)
    tipcol = lerp(col("#b24fc4"), col("#e070c8"), fft_noise(1106, 2.5, 2, 20))
    alb = lerp(alb, tipcol, tips * (0.6 + 0.3 * blot))
    h = 0.5 * hb + 0.5 * low
    alb = shade(alb, h, 0.12)
    save("AlienGrass", alb, h, 0.22, 1.2)


def alien_moss():
    r = rng(1201)
    pts = r.uniform(0, N, (230, 2))
    d, i, _ = voronoi(0, 0, pts=pts, k=4)
    rad = r.uniform(38, 66, len(pts))
    pv = r.random(len(pts))
    domes = np.clip(1 - (d / rad[i]) ** 2, 0, 1) ** 0.7 * (0.75 + 0.25 * pv[i])
    j = np.argmax(domes, 0)
    dome = np.take_along_axis(domes, j[None], 0)[0]
    cellv = np.take_along_axis(pv[i], j[None], 0)[0]
    fuzz = fft_noise(1203, 1.2, 30, 200)
    big = fft_noise(1202, 3.0, 1, 8)
    dome = blur(dome + 0.05 * fuzz, 2.0)
    h = 0.55 * dome * (0.7 + 0.3 * cellv) + 0.3 * big + 0.12 * fuzz
    t = posterize_soft(np.clip(0.55 * dome + 0.25 * cellv + 0.2 * big, 0, 1), 4, 0.3)
    alb = palette_map(t, [(0, "#3b2350"), (0.35, "#583174"), (0.7, "#744595"), (1, "#9563b5")])
    alb = lerp(alb, alb * np.array([1.05, 0.9, 1.1]), smoothstep(0.55, 0.75, fft_noise(1204, 3, 1, 10)) * 0.5)
    alb *= (0.92 + 0.12 * fuzz)[..., None]
    sp = Canvas()
    for _ in range(140):
        x, y = r.uniform(0, N, 2)
        rr = r.uniform(1.2, 2.6)
        sp.ellipse(x, y, rr, rr, 255)
    s = blur(sp.arr(), 0.6) * smoothstep(0.3, 0.6, dome)
    alb *= (0.8 + 0.3 * dome)[..., None]
    alb = shade(alb, h, 0.3)
    alb = lerp(alb, col("#6ff0f0"), s * 0.9)
    save("AlienMoss", alb, h + 0.04 * s, 0.25, 1.0)


def red_sand():
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    low = fft_noise(1301, 3.0, 1, 8)
    wy = (fft_noise(1302, 3.0, 1, 5) - 0.5) * 140
    wy2 = (fft_noise(1303, 2.5, 2, 12) - 0.5) * 20
    ph = (yy + wy + wy2) / N * 22 + (xx / N) * 2  # integer slope keeps tiling
    fr = ph - np.floor(ph)
    rip = np.where(fr < 0.7, fr / 0.7, (1 - fr) / 0.3)  # asymmetric wind ripple
    rip = smoothstep(0, 1, rip)
    amp = 0.5 + 0.5 * fft_noise(1304, 3, 1, 6)
    t = posterize_soft(0.45 * low + 0.35 * rip * amp + 0.2 * fft_noise(1305, 2, 4, 50), 4, 0.35)
    alb = palette_map(t, [(0, "#8e3a1e"), (0.4, "#b14d24"), (0.75, "#c9632f"), (1, "#dc7d3e")])
    m, ids, dist = pebbles(1306, 70, 4, 10)
    pcol = palette_map(ids, [(0, "#5c2c22"), (0.5, "#734036"), (1, "#8e5a45")])
    pd = np.clip(dist / 5.0, 0, 1)
    alb = lerp(alb, pcol * (0.85 + 0.3 * pd[..., None]), m)
    shadow = blur(np.roll(np.roll(m, 3, 0), 2, 1), 2) * (1 - m)
    alb *= (1 - 0.3 * shadow)[..., None]
    h = 0.3 * low + 0.35 * rip * amp + 0.45 * m * (0.5 + 0.5 * pd)
    alb = shade(alb, h, 0.14)
    save("RedSand", alb, h, 0.12)


def alien_dirt():
    low = fft_noise(1401, 3.0, 1, 10)
    mid = fft_noise(1402, 2.0, 4, 60)
    t = posterize_soft(0.55 * low + 0.45 * mid, 4, 0.3)
    alb = palette_map(t, [(0, "#3c2838"), (0.5, "#53344a"), (1, "#69445a")])
    m, ids, dist = pebbles(1403, 80, 5, 11)
    pcol = palette_map(ids, [(0, "#3fb8c8"), (0.5, "#5fd8e0"), (1, "#8ef0ea")])
    pd = np.clip(dist / 4.5, 0, 1)
    alb = lerp(alb, pcol * (0.8 + 0.25 * pd[..., None]), m)
    m2, ids2, dist2 = pebbles(1404, 160, 5, 12)
    m2 *= 1 - m
    alb = lerp(alb, palette_map(ids2, [(0, "#6a5664"), (1, "#8a7482")]) * (0.85 + 0.25 * np.clip(dist2 / 4, 0, 1))[..., None], m2)
    mm = np.maximum(m, m2)
    shadow = blur(np.roll(np.roll(mm, 3, 0), 2, 1), 2) * (1 - mm)
    alb *= (1 - 0.35 * shadow)[..., None]
    cr = cracks(1415, 60, 2.4, 0.5, wiggle=4)
    alb = lerp(alb, alb * 0.5, cr)
    h = 0.35 * low + 0.15 * mid + 0.45 * mm * (0.5 + 0.5 * np.clip(dist2 / 4, 0, 1) + 0.5 * pd) - 0.35 * cr
    alb = shade(alb, h, 0.15)
    save("AlienDirt", alb, h, 0.25)


def crystal_rock():
    r = rng(1501)
    pts = r.uniform(0, N, (50, 2))
    d, i, _ = voronoi(0, 0, pts=pts)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    c = pts[i[0]]
    rx = ((xx - c[..., 0] + N / 2) % N) - N / 2
    ry = ((yy - c[..., 1] + N / 2) % N) - N / 2
    plane = r.uniform(0.3, 0.7, len(pts))[i[0]] + r.normal(0, 0.006, len(pts))[i[0]] * rx \
        + (r.normal(0, 0.006, len(pts)) - 0.004)[i[0]] * ry
    edge = d[1] - d[0]
    crack = 1 - smoothstep(0, 4, edge)
    bevel = smoothstep(0, 18, edge)
    n = fft_noise(1502, 2.2, 3, 50)
    cellt = r.random(len(pts))[i[0]]
    vein = vein_network(1503, 14, 5.0, 22, fine=False)
    vein = np.maximum(vein, 0.8 * vein_network(1510, 40, 1.8, 10, fine=False) * smoothstep(0.5, 0.65, fft_noise(1511, 2.5, 1, 8)))
    core = smoothstep(0.55, 0.9, vein)
    t = posterize_soft(0.5 * cellt + 0.3 * n + 0.2 * plane, 5, 0.25)
    alb = palette_map(t, [(0, "#4a4352"), (0.4, "#5f5669"), (0.75, "#73697c"), (1, "#857b8e")])
    h = norm01(plane * bevel * 0.8 + 0.12 * n - 0.3 * crack)
    alb = lerp(alb, alb * 0.45, crack)
    alb = shade(alb, h, 0.32)
    halo = blur(vein, 6)
    alb = lerp(alb, alb * np.array([0.9, 1.1, 1.2]), np.clip(halo * 1.5, 0, 1) * 0.5)
    vcol = lerp(col("#1f8fb0"), col("#7ff4f0"), core)
    alb = lerp(alb, vcol, smoothstep(0.15, 0.5, vein))
    h = h + 0.25 * vein - 0.15 * blur(vein, 4)
    save("CrystalRock", alb, h, 0.28)


def toxic():
    r = rng(1601)
    low = fft_noise(1602, 3.0, 1, 8)
    sw = fft_noise(1603, 2.6, 2, 20)
    swirl = warp(low, (sw - 0.5) * 120, (fft_noise(1604, 2.6, 2, 20) - 0.5) * 120)
    t = posterize_soft(0.7 * swirl + 0.3 * sw, 5, 0.3)
    alb = palette_map(t, [(0, "#3f9a1a"), (0.4, "#5cc21e"), (0.75, "#83e02c"), (1, "#b4f24a")])
    bub = Canvas(); rim = Canvas(); hi = Canvas(); ring = Canvas()
    for _ in range(160):
        x, y = r.uniform(0, N, 2)
        rr = r.uniform(5, 26) if r.random() < 0.8 else r.uniform(28, 42)
        bub.ellipse(x, y, rr, rr, 255)
        rim.ellipse(x, y, rr, rr, 255); rim.ellipse(x, y, rr * 0.78, rr * 0.78, 0)
        hi.ellipse(x - rr * 0.35, y - rr * 0.35, rr * 0.22, rr * 0.18, 255)
    for _ in range(14):
        x, y = r.uniform(0, N, 2)
        for k, R in enumerate((30, 55, 82)):
            w = max(2, 5 - k)
            for ox, oy in wrap_offsets(x, y, R + 4):
                ring.d.ellipse([x - R + ox, y - R * 0.85 + oy, x + R + ox, y + R * 0.85 + oy], outline=int(220 - 50 * k), width=w)
    b = blur(bub.arr(), 0.7); rm = blur(rim.arr(), 0.8); hl = blur(hi.arr(), 0.8); rg = blur(ring.arr(), 1.2)
    bdist = ndimage.distance_transform_edt(np.tile(bub.arr() > 0.5, (3, 3)))[N:2 * N, N:2 * N]
    bdome = np.clip(bdist / 12, 0, 1)
    alb = lerp(alb, alb * np.array([1.12, 1.1, 0.85]) + 0.04, rg * 0.7)
    alb = lerp(alb, col("#9ff03a") * (0.85 + 0.2 * bdome[..., None]), b * 0.85)
    alb = lerp(alb, col("#2f7a14"), rm * 0.75)
    alb = lerp(alb, col("#eaffb0"), hl)
    h = 0.35 * swirl + 0.6 * b * (0.4 + 0.6 * bdome) + 0.1 * rg
    alb = shade(alb, h, 0.08)
    save("Toxic", alb, h, 0.2, 1.0)


def alien_metal():
    r = rng(1701)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    rows = [256, 192, 320, 256]
    seam = np.zeros((N, N)); pid = np.zeros((N, N)); edist = np.full((N, N), 1e9)
    riv = Canvas()
    y0 = 0
    for ri, rh in enumerate(rows):
        nseg = int(r.integers(2, 4))
        cuts = np.sort(r.choice(np.arange(2, 16), nseg - 1, replace=False)) * 64 if nseg > 1 else np.array([], int)
        off = int(r.integers(0, 16)) * 64
        xs = sorted(((np.concatenate([[0], cuts]) + off) % N).tolist())
        my = (yy >= y0) & (yy < y0 + rh)
        dy = np.minimum(yy - y0, y0 + rh - 1 - yy)
        dxm = np.full((N, N), 1e9)
        seg = np.zeros((N, N), int)
        for k, sx in enumerate(xs):
            dxm = np.minimum(dxm, np.abs(((xx - sx + N / 2) % N) - N / 2))
            seg += (xx >= sx)
        seg = seg % len(xs)
        dd = np.minimum(dy, dxm)
        edist[my] = dd[my]
        pid[my] = (ri * 7 + seg[my] * 3 + 1) % 11 / 10.0
        # rivets along horizontal edges and vertical seams
        for yrow in (y0 + 12, y0 + rh - 12):
            for x in np.arange(16, N, 48):
                riv.ellipse(x + 0.5, yrow, 4.5, 4.5, 255)
        for sx in xs:
            for sgn in (-12, 12):
                for y in np.arange(y0 + 40, y0 + rh - 30, 48):
                    riv.ellipse((sx + sgn) % N, y, 4.5, 4.5, 255)
        y0 += rh
    seam = 1 - smoothstep(1.0, 3.0, edist)
    bevel = 1 - smoothstep(3, 12, edist)
    low = fft_noise(1702, 3.0, 1, 10)
    rv = riv.arr()
    rdist = ndimage.distance_transform_edt(np.tile(rv > 0.5, (3, 3)))[N:2 * N, N:2 * N]
    rdome = np.clip(rdist / 4, 0, 1)
    base = palette_map(pid, [(0, "#4f6b6c"), (0.5, "#5d7a7a"), (1, "#6b8786")])
    alb = base * (0.9 + 0.15 * posterize_soft(low, 4))[..., None]
    # soft wear: lighter metal near panel edges, broken by noise
    wear = (1 - smoothstep(3, 16, edist)) * smoothstep(0.5, 0.65, fft_noise(1703, 2.0, 4, 60))
    alb = lerp(alb, col("#9fb5b0"), wear * 0.45)
    grime = smoothstep(0.55, 0.8, fft_noise(1704, 3, 1, 10))
    alb = lerp(alb, alb * np.array([0.78, 0.8, 0.78]), grime * 0.5)
    sc = Canvas()
    for _ in range(80):
        x, y = r.uniform(0, N, 2); a = r.normal(0.2, 0.5); L = r.uniform(20, 80)
        sc.line([(x, y), (x + np.cos(a) * L, y + np.sin(a) * L)], int(r.uniform(100, 200)), 1)
    s = blur(sc.arr(), 0.6)
    alb = lerp(alb, col("#b8c8c4"), s * 0.5)
    alb = lerp(alb, alb * 0.75, bevel * 0.4)
    alb = lerp(alb, col("#1e2a2c"), seam)
    alb = lerp(alb, col("#7f9a98") * (0.75 + 0.4 * rdome[..., None]), rv)
    h = 0.5 + 0.05 * low - 0.15 * bevel - 0.4 * seam + 0.25 * rv * (0.5 + 0.5 * rdome) - 0.05 * s
    alb = shade(alb, h, 0.12)
    save("AlienMetal", alb, h, 0.12, 0.6)


def zombie_alien():
    low = fft_noise(1801, 3.0, 1, 10)
    mid = fft_noise(1802, 2.2, 3, 50)
    t = posterize_soft(0.6 * low + 0.4 * mid, 4, 0.35)
    alb = palette_map(t, [(0, "#4f6366"), (0.5, "#62777a"), (1, "#768b8b")])
    bn = fft_noise(1803, 3.0, 1, 10)
    alb = lerp(alb, col("#6a4b7a"), smoothstep(0.58, 0.82, bn) * 0.6)
    alb = lerp(alb, col("#4a3258"), smoothstep(0.72, 0.92, bn) * 0.45)
    v = np.maximum(vein_network(1804, 34, 3.4, 9), 0.6 * organic_veins(1830, 0.6))
    glow = np.clip(blur(v, 6) * 2.2, 0, 1)
    gcol = lerp(col("#38e0c0"), col("#8af08a"), fft_noise(1805, 2.5, 1, 8))
    alb = lerp(alb, alb * 0.75 + gcol * 0.35, glow * 0.6)
    alb = lerp(alb, gcol, smoothstep(0.2, 0.6, v))
    alb = lerp(alb, col("#d8fff0"), smoothstep(0.7, 1.0, v) * 0.7)
    pores = fft_noise(1806, 1.0, 40, 160)
    h = 0.35 * low + 0.15 * mid + 0.3 * v + 0.05 * pores
    alb = shade(alb, h, 0.08)
    save("ZombieAlien", alb, h, 0.15)


def asphalt():
    r = rng(1901)
    yy, xx = np.mgrid[0:N, 0:N].astype(np.float64)
    low = fft_noise(1902, 3.0, 1, 8)
    mid = fft_noise(1903, 2.0, 4, 60)
    t = posterize_soft(0.55 * low + 0.45 * mid, 4, 0.3)
    alb = palette_map(t, [(0, "#2c2c2f"), (0.5, "#38383b"), (1, "#454547")])
    agg = Canvas()
    for _ in range(2200):
        x, y = r.uniform(0, N, 2); rr = r.uniform(1.0, 2.4)
        agg.ellipse(x, y, rr, rr * r.uniform(0.6, 1), int(r.uniform(90, 255)))
    a = blur(agg.arr(), 0.5)
    alb = lerp(alb, col("#6a6a6a"), a * 0.6)
    # patches: darker repaired rectangles
    pt = Canvas()
    for _ in range(3):
        x, y = r.uniform(0, N, 2); rx, ry = r.uniform(70, 140, 2)
        angs = np.linspace(0, 2 * np.pi, 14, endpoint=False) + r.uniform(0, 0.4)
        pt.polygon([(x + np.cos(a) * rx * r.uniform(0.75, 1.05), y + np.sin(a) * ry * r.uniform(0.75, 1.05)) for a in angs], 255)
    pw = (fft_noise(1910, 2.4, 2, 30) - 0.5) * 16
    p = blur(warp(pt.arr(), pw, -pw), 1.0)
    pedge = np.clip(blur(pt.arr(), 2.5) * (1 - pt.arr()) * 3, 0, 1)
    alb = lerp(alb, alb * 0.86 + 0.01, p)
    # faded yellow line fragments (dashed, center line)
    lw = (fft_noise(1905, 3, 1, 3) - 0.5) * 6
    dline = np.abs(((xx + lw - 512 + N / 2) % N) - N / 2)
    band = 1 - smoothstep(18, 21, dline)
    dash = (((yy / N * 3) % 1) < 0.6) & (((yy / N * 3) % 1) > 0.05)
    fade = smoothstep(0.3, 0.6, fft_noise(1906, 2.0, 3, 60)) * smoothstep(0.25, 0.5, fft_noise(1907, 3, 1, 6))
    yl = band * dash * fade * (1 - p)
    alb = lerp(alb, col("#a99449"), yl * 0.75)
    cr = cracks(1908, 45, 2.2, 0.6, wiggle=10) * (1 - p)
    cr2 = cracks(1909, 160, 1.3, 0.35, wiggle=5) * (1 - p) * 0.7
    c = np.maximum(cr, cr2)
    alb = lerp(alb, col("#141416"), c * 0.9)
    alb = lerp(alb, alb * 0.75, pedge * 0.5)
    h = 0.3 * low + 0.1 * mid + 0.12 * a - 0.08 * p - 0.45 * c + 0.03 * yl
    alb = shade(alb, h, 0.12)
    save("Asphalt", alb, h, 0.15)


def emissive_veins():
    v = np.maximum(vein_network(1804, 34, 3.4, 9), 0.6 * organic_veins(1830, 0.6))  # same network as ZombieAlien so the mask lines up
    out = np.clip(smoothstep(0.1, 0.7, v), 0, 1)
    Image.fromarray((out * 255 + 0.5).astype(np.uint8), "L").save(os.path.join(OUT, "T_Emissive_Mask_Veins.png"))
    print("wrote Emissive_Mask_Veins")


# ---------------------------------------------------------- contact sheet
NAMES = ["Grass", "Dirt", "Gravel", "Rock", "Concrete", "Wood", "RustMetal", "ZombieSkin", "Cloth",
         "AlienGrass", "AlienMoss", "RedSand", "AlienDirt", "CrystalRock", "Toxic", "AlienMetal",
         "ZombieAlien", "Asphalt"]
MASKS = {"Detail_Grunge": "T_Detail_Grunge.png", "Emissive_Mask_Veins": "T_Emissive_Mask_Veins.png"}


def contact_sheet():
    cell = 380
    items = NAMES + list(MASKS)
    cols = 6
    rows = (len(items) + cols - 1) // cols
    W, H = cols * (cell + 20) + 20, rows * (cell + 60) + 20
    sheet = Image.new("RGB", (W, H), (40, 40, 44))
    d = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype("DejaVuSans-Bold.ttf", 20)
    except Exception:
        font = ImageFont.load_default()
    for k, nm in enumerate(items):
        cx = 20 + (k % cols) * (cell + 20)
        cy = 20 + (k // cols) * (cell + 60)
        fn = MASKS.get(nm, f"T_{nm}_D.png")
        im = Image.open(os.path.join(OUT, fn)).convert("RGB")
        half = im.resize((cell // 2, cell // 2), Image.LANCZOS)
        tile = Image.new("RGB", (cell, cell))
        for ox in (0, cell // 2):
            for oy in (0, cell // 2):
                tile.paste(half, (ox, oy))
        sheet.paste(tile, (cx, cy))
        if nm not in MASKS:
            nm_img = Image.open(os.path.join(OUT, f"T_{nm}_N.png")).resize((110, 110), Image.LANCZOS)
            sheet.paste(nm_img, (cx + cell - 114, cy + cell - 114))
        d.text((cx, cy + cell + 8), nm, fill=(230, 230, 230), font=font)
    sheet.save(os.path.join(OUT, "textures_preview.png"))
    print("wrote preview")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    only = set(sys.argv[2:])
    for fn in [grass, dirt, gravel, rock, concrete, wood, rustmetal, zombieskin, cloth, grunge,
               alien_grass, alien_moss, red_sand, alien_dirt, crystal_rock, toxic, alien_metal,
               zombie_alien, asphalt, emissive_veins]:
        if not only or fn.__name__ in only:
            fn()
    contact_sheet()
