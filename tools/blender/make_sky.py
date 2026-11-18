"""Céu alienígena (Etapa 7): malhas + texturas procedurais + prévia. Blender 5.2 (bpy) + numpy.

Rodar (da raiz do repositório):
  blender -b --python tools/blender/make_sky.py -- assets/work/sky
  blender -b --python tools/blender/make_sky.py -- assets/work/sky --noprev     (sem a prévia)
  blender -b --python tools/blender/make_sky.py -- assets/work/sky --prevonly   (só a prévia)

Gera em <saída>:
  SM_Sky_Planet.fbx   esfera 128x64 (raio 1 m, UV equiretangular, polos em +Z)
  SM_Sky_Moon.fbx     esfera 64x32 (as duas luas usam a mesma malha)
  SM_Sky_Rings.fbx    anel plano XY, raio 1,25 a 2,30 m (U = raio de dentro para fora)
  SM_Sky_StarDome.fbx esfera 64x32 com normais para dentro (cúpula de estrelas)
  SM_Sky_Aurora.fbx   faixa curva (arco de raio ~1 m, -55 a +55 graus em volta de +X, altura 0,18 a ~0,52 m);
                      cor do vértice R = some nas pontas
  T_Sky_Planet.png (2048x1024) faixas tipo Saturno com tempestade; T_Sky_Rings.png (1024x8, RGBA);
  T_Sky_MoonA.png / T_Sky_MoonB.png (1024x512) crateras; T_Sky_Stars.png (4096x2048) estrelas + nebulosa;
  T_Sky_Aurora.png (512x256, linear: R raios, G perfil vertical, B altura 0..1)
  sky_preview.png  prévia do entardecer (visão do jogador + panorama 360) com a MESMA conta dos materiais
                   da Unreal; sky_preview_night.png igual, preset noite
Posições, presets e cores vêm de tools/unreal/setup_alien_sky.py (fonte única).
Tudo é gerado aqui (sem download): licença do projeto.
"""
import math
import os
import struct
import sys
import zlib

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(REPO, "tools", "unreal"))
import setup_alien_sky as cfg  # noqa: E402  (só dados/funções puras)

TAU = 2 * math.pi
RING_INNER, RING_OUTER = cfg.RING_INNER, cfg.RING_OUTER
AURORA_A0, AURORA_A1 = -55.0, 55.0
AURORA_U_REPEAT = 3.0


# ------------------------------------------------------------------ utilidades puras
def write_png(path, arr):
    """PNG 8 bits sem dependências (RGB ou RGBA, HxWxC uint8)."""
    arr = np.ascontiguousarray(arr, dtype=np.uint8)
    h, w, c = arr.shape
    ctype = {1: 0, 3: 2, 4: 6}[c]
    raw = b"".join(b"\x00" + arr[y].tobytes() for y in range(h))

    def chunk(tag, data):
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    with open(path, "wb") as fh:
        fh.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, ctype, 0, 0, 0))
                 + chunk(b"IDAT", zlib.compress(raw, 9)) + chunk(b"IEND", b""))


def hx(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def srgb_to_lin(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def to_u8(c):
    return (np.clip(c, 0, 1) * 255 + 0.5).astype(np.uint8)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def value_noise(h, w, cy, cx, rng, wrap_x=True):
    """Ruído de valor 2D suave (cy x cx células), contínuo na emenda horizontal se wrap_x."""
    g = rng.random((cy + 1, cx if wrap_x else cx + 1))
    x = np.arange(w) / w * cx
    y = np.arange(h) / max(1, h - 1) * cy
    xi = np.floor(x).astype(int)
    yi = np.minimum(np.floor(y).astype(int), cy - 1)
    xf, yf = x - xi, y - yi
    xf, yf = xf * xf * (3 - 2 * xf), yf * yf * (3 - 2 * yf)
    x0 = xi % g.shape[1]
    x1 = (xi + 1) % g.shape[1] if wrap_x else np.minimum(xi + 1, cx)
    a = g[yi][:, x0]
    b = g[yi][:, x1]
    c = g[yi + 1][:, x0]
    d = g[yi + 1][:, x1]
    top = a + (b - a) * xf[None, :]
    bot = c + (d - c) * xf[None, :]
    return top + (bot - top) * yf[:, None]


def fbm(h, w, cy, cx, octaves, seed, gain=0.5, wrap_x=True):
    rng = np.random.default_rng(seed)
    out = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * value_noise(h, w, cy * 2 ** o, cx * 2 ** o, rng, wrap_x)
        tot += amp
        amp *= gain
    return out / tot


def noise1d(n, cells, rng, wrap=False):
    g = rng.random(cells + 1)
    if wrap:
        g[-1] = g[0]
    x = np.linspace(0, cells, n, endpoint=not wrap)
    i = np.minimum(np.floor(x).astype(int), cells - 1)
    f = x - i
    f = f * f * (3 - 2 * f)
    return g[i] + (g[i + 1] - g[i]) * f


def ramp(v, stops):
    """Gradiente: stops = [(pos, cor sRGB hex)], v em 0..1 -> HxWx3 sRGB."""
    pos = np.array([p for p, _ in stops])
    cols = np.array([hx(c) for _, c in stops])
    out = np.zeros(v.shape + (3,))
    for k in range(3):
        out[..., k] = np.interp(v, pos, cols[:, k])
    return out


def equirect_dirs(h, w):
    lat = (0.5 - (np.arange(h) + 0.5) / h) * math.pi
    lon = (np.arange(w) + 0.5) / w * TAU
    LON, LAT = np.meshgrid(lon, lat)
    return LON, LAT, np.stack([np.cos(LAT) * np.cos(LON), np.cos(LAT) * np.sin(LON), np.sin(LAT)], -1)


# ------------------------------------------------------------------ texturas
def tex_planet(h=1024, w=2048, seed=7):
    rng = np.random.default_rng(seed)
    LON, LAT, _ = equirect_dirs(h, w)
    warp = fbm(h, w, 12, 24, 5, seed + 1) - 0.5
    latw = LAT + 0.05 * warp * (0.5 + 1.5 * np.cos(LAT) ** 4) + 0.012 * np.sin(3 * LON + 9 * LAT)
    n = 4096
    prof = 0.55 * noise1d(n, 13, rng) + 0.3 * noise1d(n, 37, rng) + 0.15 * noise1d(n, 95, rng)
    prof = (prof - prof.min()) / (prof.max() - prof.min())
    idx = np.clip(((latw / math.pi) + 0.5) * (n - 1), 0, n - 1).astype(int)
    v = prof[idx]
    streak = fbm(h, w, 90, 6, 3, seed + 2)
    v = np.clip(v + 0.16 * (streak - 0.5), 0, 1)
    col = ramp(v, [(0.0, "4b3a78"), (0.18, "8a6fc0"), (0.36, "e9d6bf"), (0.5, "f0b98a"),
                   (0.64, "d98a72"), (0.8, "74c2b6"), (1.0, "f6ead8")])
    polar = smoothstep(math.radians(52), math.radians(84), np.abs(LAT))[..., None] * 0.75
    col = col * (1 - polar) + hx("4e4486") * polar
    # tempestade oval (lat -24, lon 120) com redemoinho
    def oval(lat0, lon0, a, b, core, edge, strength):
        dlon = (LON - lon0 + math.pi) % TAU - math.pi
        dl = LAT - lat0
        ang = np.arctan2(dl / b, dlon * np.cos(lat0) / a)
        d = np.sqrt((dlon * math.cos(lat0) / a) ** 2 + (dl / b) ** 2)
        swirl = 0.5 + 0.5 * np.sin(ang * 2 + d * 9)
        m = smoothstep(1.15, 0.55, d)[..., None] * strength
        c = hx(core) * (1 - smoothstep(0.0, 0.9, d))[..., None] + hx(edge) * smoothstep(0.0, 0.9, d)[..., None]
        c = c * (0.85 + 0.15 * swirl[..., None])
        return col * (1 - m) + c * m
    col = oval(math.radians(-24), math.radians(120), 0.20, 0.075, "c24f3c", "f2c9a4", 0.95)
    for k in range(5):
        col = oval(math.radians(rng.uniform(-45, 45)), rng.uniform(0, TAU), rng.uniform(0.03, 0.06),
                   rng.uniform(0.012, 0.02), "fbf2e6", "e9d6bf", 0.7)
    grain = fbm(h, w, 64, 128, 2, seed + 3)[..., None]
    col = col * (0.93 + 0.14 * grain)
    return to_u8(col)


def ring_profile(w=1024, seed=11):
    """Densidade (0..1) do anel de dentro (u=0) para fora (u=1); bordas zeradas."""
    rng = np.random.default_rng(seed)
    u = np.linspace(0, 1, w)
    d = np.zeros(w)
    d += np.where(u < 0.22, 0.16 + 0.12 * u / 0.22, 0)                    # anel C (fraco)
    d += np.where((u >= 0.22) & (u < 0.55), 0.82 + 0.15 * np.sin(u * 40), 0)  # anel B (forte)
    d += np.where((u >= 0.55) & (u < 0.60), 0.035, 0)                     # divisão de Cassini
    d += np.where((u >= 0.60) & (u < 0.94), 0.62, 0)                      # anel A
    d = np.where((u > 0.855) & (u < 0.872), 0.08, d)                      # falha de Encke
    d += np.where(u >= 0.94, 0.25 * (1 - smoothstep(0.94, 1.0, u)), 0)    # anel F tênue
    ringlets = 0.55 + 0.45 * noise1d(w, 160, rng) * 0.6 + 0.4 * noise1d(w, 23, rng)
    d = np.clip(d * ringlets, 0, 1)
    edge = smoothstep(0.0, 0.025, u) * (1 - smoothstep(0.975, 1.0, u))
    return d * edge


def tex_rings(w=1024, h=8, seed=11):
    rng = np.random.default_rng(seed + 1)
    d = ring_profile(w, seed)
    tint = noise1d(w, 40, rng)
    u = np.linspace(0, 1, w)
    col = ramp(tint, [(0, "cdb391"), (0.5, "e8d8bd"), (1, "b39ad6")])
    col = col * (1 - smoothstep(0.6, 1.0, u)[:, None] * 0.25) + hx("7fc7c0") * smoothstep(0.6, 1.0, u)[:, None] * 0.25
    rgba = np.concatenate([col, (d * 0.97)[:, None]], 1)
    return to_u8(np.repeat(rgba[None], h, 0))


def tex_moon(h=512, w=1024, seed=21, base=("b9b4cc", "8d88a8"), mare="5e5a78", rim="e6e2f2", n_craters=240):
    rng = np.random.default_rng(seed)
    LON, LAT, D = equirect_dirs(h, w)
    n = fbm(h, w, 6, 12, 6, seed + 1)
    col = ramp(n, [(0, base[1]), (1, base[0])])
    maria = smoothstep(0.55, 0.7, fbm(h, w, 3, 6, 4, seed + 2))[..., None] * 0.6
    col = col * (1 - maria) + hx(mare) * maria
    shade = np.zeros((h, w))
    for k in range(n_craters):
        z = rng.uniform(-1, 1)
        a = rng.uniform(0, TAU)
        c = np.array([math.sqrt(1 - z * z) * math.cos(a), math.sqrt(1 - z * z) * math.sin(a), z])
        r = 0.012 * (1 - rng.random()) ** -0.9
        r = min(r, 0.32)
        th = np.arccos(np.clip(D @ c, -1, 1))
        x = th / r
        bowl = np.where(x < 1, -0.22 * (1 - x * x), 0)
        rimv = 0.2 * np.exp(-((x - 1.0) / 0.12) ** 2)
        ejecta = np.where(x > 1, 0.05 * np.exp(-(x - 1) * 2.5), 0) if r > 0.08 else 0
        shade += bowl + rimv + ejecta
    col = col * (1 + np.clip(shade, -0.5, 0.6)[..., None])
    col = col + (hx(rim) - col) * np.clip(shade - 0.25, 0, 1)[..., None]
    return to_u8(col)


def tex_stars(h=2048, w=4096, seed=31, count=9000):
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3))
    temps = [hx("aecbff"), hx("ffffff"), hx("fff1d6"), hx("ffd2a1"), hx("9ff7ff"), hx("ffb3e6")]
    tw = np.array([0.25, 0.35, 0.2, 0.12, 0.05, 0.03])
    for _ in range(count):
        z = rng.uniform(-0.12, 1)
        lon = rng.uniform(0, TAU)
        lat = math.asin(z)
        b = (1 - rng.random()) ** 3.2
        b = 0.15 + 2.6 * b
        cx = lon / TAU * w
        cy = (0.5 - lat / math.pi) * h
        sx = 0.7 / max(0.08, math.cos(lat))
        sy = 0.7
        rx, ry = int(math.ceil(sx * 3)), 3
        x0, y0 = int(cx) - rx, int(cy) - ry
        xs = np.arange(x0, x0 + 2 * rx + 2)
        ys = np.arange(max(0, y0), min(h, y0 + 2 * ry + 2))
        if len(ys) == 0:
            continue
        gx = np.exp(-(((xs + 0.5 - cx) / sx) ** 2) / 2)
        gy = np.exp(-(((ys + 0.5 - cy) / sy) ** 2) / 2)
        c = temps[rng.choice(len(temps), p=tw)]
        img[np.ix_(ys, xs % w)] += (gy[:, None] * gx[None, :])[..., None] * c * b
    LON, LAT, D = equirect_dirs(h, w)
    pole = np.array([0.3, -0.5, 0.81])
    pole /= np.linalg.norm(pole)
    band = np.exp(-((D @ pole) / 0.22) ** 2)
    neb = fbm(h, w, 8, 16, 5, seed + 1)
    neb2 = fbm(h, w, 5, 10, 4, seed + 2)
    nebc = hx("6a3fa8") * (1 - neb2[..., None]) + hx("2f8f9a") * neb2[..., None]
    img += nebc * (band * smoothstep(0.45, 0.85, neb))[..., None] * 0.12
    img *= smoothstep(math.radians(-4), math.radians(3), LAT)[..., None]  # nada abaixo do horizonte
    return to_u8(lin_to_srgb(np.clip(img, 0, 1) ** 1.0 * 0.95))


def tex_aurora(h=256, w=512, seed=41):
    rng = np.random.default_rng(seed)
    v = 1 - (np.arange(h) + 0.5) / h            # 1 em cima (linha 0), 0 embaixo
    shift = (fbm(h, 1, 6, 1, 3, seed + 1, wrap_x=False)[:, 0] - 0.5) * 18
    x = (np.arange(w)[None, :] + shift[:, None]) % w
    rays1 = noise1d(w * 4, 48, rng, wrap=True)
    rays2 = noise1d(w * 4, 131, rng, wrap=True)
    xi = (x / w * (w * 4)).astype(int) % (w * 4)
    r = (0.55 * rays1[xi] + 0.45 * rays2[xi]) ** 2.2
    r = r / r.max()
    r = (0.3 + 0.7 * r) * (0.8 + 0.2 * np.sin(v * 7)[:, None])        # brilho de fundo + raios
    prof = smoothstep(0.0, 0.07, v) * np.exp(-np.maximum(v - 0.06, 0) * 1.8)
    prof = prof / prof.max()
    img = np.stack([r, np.repeat(prof[:, None], w, 1), np.repeat(v[:, None], w, 1)], -1)
    return to_u8(img)


TEXTURES = {
    "T_Sky_Planet": tex_planet,
    "T_Sky_Rings": tex_rings,
    "T_Sky_MoonA": lambda: tex_moon(seed=21),
    "T_Sky_MoonB": lambda: tex_moon(seed=22, base=("d07a4c", "9a4c32"), mare="5a2e2a", rim="f4c39a", n_craters=160),
    "T_Sky_Stars": tex_stars,
    "T_Sky_Aurora": tex_aurora,
}


# ------------------------------------------------------------------ geometria (formas também usadas na prévia)
def aurora_shape(theta_deg):
    """Raio (x raio-base), base e topo (x raio-base) da aurora no ângulo local theta (graus)."""
    t = np.radians(theta_deg)
    r = 1.0 + 0.05 * np.sin(3.1 * t + 0.4) + 0.02 * np.sin(11 * t)
    z0 = 0.18 + 0.015 * np.sin(2.3 * t + 1.0)
    z1 = z0 + 0.34 * (0.8 + 0.2 * np.sin(5 * t))
    return r, z0, z1


def aurora_end_fade(theta_deg):
    a = (np.asarray(theta_deg) - AURORA_A0) / (AURORA_A1 - AURORA_A0)
    return smoothstep(0.0, 0.18, a) * (1 - smoothstep(0.82, 1.0, a))


# ------------------------------------------------------------------ Blender
def _mesh_object(name, verts, faces, uvs, smooth=True, colors=None):
    import bpy
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], [tuple(f) for f in faces])
    me.update()
    uvl = me.uv_layers.new(name="UVMap")
    for poly, fuv in zip(me.polygons, uvs):
        for li, uv in zip(poly.loop_indices, fuv):
            uvl.data[li].uv = uv
    if colors is not None:
        ca = me.color_attributes.new("Col", "BYTE_COLOR", "CORNER")
        for poly, fc in zip(me.polygons, colors):
            for li, c in zip(poly.loop_indices, fc):
                ca.data[li].color = c
    for p in me.polygons:
        p.use_smooth = smooth
    mat = bpy.data.materials.get("M_Sky") or bpy.data.materials.new("M_Sky")
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def build_sphere(name, nu, nv, inward=False):
    verts = [(0, 0, 1)]
    for i in range(1, nv):
        lat = math.pi / 2 - math.pi * i / nv
        for j in range(nu):
            lon = TAU * j / nu
            verts.append((math.cos(lat) * math.cos(lon), math.cos(lat) * math.sin(lon), math.sin(lat)))
    south = len(verts)
    verts.append((0, 0, -1))

    def vid(i, j):
        if i == 0:
            return 0
        if i == nv:
            return south
        return 1 + (i - 1) * nu + (j % nu)

    def uv(i, j):
        return (j / nu, 1 - i / nv)

    faces, uvs = [], []
    for i in range(nv):
        for j in range(nu):
            if i == 0:
                f = [(0, j), (1, j), (1, j + 1)]
                f[0] = (0, j + 0.5)
            elif i == nv - 1:
                f = [(i, j), (nv, j + 0.5), (i, j + 1)]
            else:
                f = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
            if inward:
                f = f[::-1]
            faces.append([vid(a, int(b)) for a, b in f])
            uvs.append([uv(a, b) for a, b in f])
    return _mesh_object(name, verts, faces, uvs)


def build_rings(name, na=256, nr=4):
    verts, faces, uvs = [], [], []
    for k in range(nr + 1):
        r = RING_INNER + (RING_OUTER - RING_INNER) * k / nr
        for j in range(na):
            a = TAU * j / na
            verts.append((r * math.cos(a), r * math.sin(a), 0))
    for k in range(nr):
        for j in range(na):
            q = [(k, j), (k + 1, j), (k + 1, j + 1), (k, j + 1)]
            faces.append([kk * na + (jj % na) for kk, jj in q])
            uvs.append([(kk / nr, jj / na) for kk, jj in q])
    return _mesh_object(name, verts, faces, uvs, smooth=False)


def build_aurora(name, na=200, nz=8):
    verts, cols = [], []
    for j in range(na + 1):
        th = AURORA_A0 + (AURORA_A1 - AURORA_A0) * j / na
        r, z0, z1 = aurora_shape(th)
        for k in range(nz + 1):
            t = k / nz
            rr = float(r) + 0.04 * t
            a = math.radians(th)
            verts.append((rr * math.cos(a), rr * math.sin(a), float(z0 + (z1 - z0) * t)))
            cols.append(float(aurora_end_fade(th)))
    faces, uvs, fcols = [], [], []
    for j in range(na):
        for k in range(nz):
            q = [(j, k), (j + 1, k), (j + 1, k + 1), (j, k + 1)]
            ids = [jj * (nz + 1) + kk for jj, kk in q]
            faces.append(ids)
            uvs.append([(jj / na * AURORA_U_REPEAT, kk / nz) for jj, kk in q])
            fcols.append([(cols[i], cols[i], cols[i], 1.0) for i in ids])
    return _mesh_object(name, verts, faces, uvs, colors=fcols)


def export_fbx(ob, path):
    import bpy
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             mesh_smooth_type="FACE", colors_type="SRGB", add_leaf_bones=False, bake_anim=False)


def build_meshes(out):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.unit_settings.system = "METRIC"
    obs = {
        "SM_Sky_Planet": build_sphere("SM_Sky_Planet", 128, 64),
        "SM_Sky_Moon": build_sphere("SM_Sky_Moon", 64, 32),
        "SM_Sky_StarDome": build_sphere("SM_Sky_StarDome", 64, 32, inward=True),
        "SM_Sky_Rings": build_rings("SM_Sky_Rings"),
        "SM_Sky_Aurora": build_aurora("SM_Sky_Aurora"),
    }
    for name, ob in obs.items():
        export_fbx(ob, os.path.join(out, name + ".fbx"))
        print(f"[make_sky] {name}.fbx: {len(ob.data.vertices)} vértices, {len(ob.data.polygons)} faces")


# ------------------------------------------------------------------ prévia (mesma conta dos materiais)
def sample_eq(tex, u, v):
    h, w = tex.shape[:2]
    x = (np.mod(u, 1.0) * w).astype(int) % w
    y = np.clip((v * h).astype(int), 0, h - 1)
    return tex[y, x]


def atmosphere_lut(sun_dir, n_el=96, n_az=72, el_min=-6.0):
    """Espalhamento simples (Rayleigh + Mie + ozônio) com os coeficientes de ATMOSPHERE, por
    elevação x diferença de azimute ao sol. Só para a prévia: aproxima o SkyAtmosphere."""
    A = cfg.ATMOSPHERE
    Rg, Rt = 6360.0, 6460.0
    br = np.array(A["rayleigh"]) * A["rayleigh_scale"]
    bm = np.array(A["mie"]) * A["mie_scale"]
    am = np.array(A["mie_abs"]) * A["mie_abs_scale"]
    bo = np.array(A["ozone"]) * A["ozone_scale"]
    g = A["mie_g"]
    els = np.radians(np.linspace(el_min, 90, n_el))
    azs = np.radians(np.linspace(0, 180, n_az))
    sun_el = math.asin(sun_dir[2])
    E, Z = np.meshgrid(els, azs, indexing="ij")
    d = np.stack([np.cos(E) * np.cos(Z), np.cos(E) * np.sin(Z), np.sin(E)], -1)
    s = np.array([math.cos(sun_el), 0.0, math.sin(sun_el)])
    mu = d @ s
    cam = np.array([0, 0, Rg + 0.3])

    def dens(h):
        oz = np.maximum(0, 1 - np.abs(h - 25.0) / 15.0)
        return np.exp(-h / A["rayleigh_km"]), np.exp(-h / A["mie_km"]), oz

    def ray_len(p, dd):
        b = np.sum(p * dd, -1)
        c = np.sum(p * p, -1) - Rt * Rt
        t_top = -b + np.sqrt(np.maximum(b * b - c, 0))
        cg = np.sum(p * p, -1) - Rg * Rg
        disc = b * b - cg
        t_g = np.where((disc > 0) & (b < 0), -b - np.sqrt(np.maximum(disc, 0)), np.inf)
        return np.minimum(t_top, t_g), np.isfinite(t_g) & (t_g < t_top)

    def tau_to(p, dd, n=12):
        L, hit = ray_len(p, dd)
        dt = (L / n)[..., None]
        tot = np.zeros(p.shape[:-1] + (3,))
        for i in range(n):
            q = p + dd * (dt * (i + 0.5))
            hh = np.linalg.norm(q, axis=-1) - Rg
            r_, m_, o_ = dens(hh)
            tot += (r_[..., None] * br + m_[..., None] * (bm + am) + o_[..., None] * bo) * dt
        tot[hit] = 1e3
        return tot

    L, _ = ray_len(np.broadcast_to(cam, d.shape), d)
    n = 32
    dt = (L / n)[..., None]
    acc_r = np.zeros(d.shape)
    acc_m = np.zeros(d.shape)
    tau_c = np.zeros(d.shape)
    for i in range(n):
        p = cam + d * (dt * (i + 0.5))
        hh = np.linalg.norm(p, axis=-1) - Rg
        r_, m_, o_ = dens(hh)
        ext = (r_[..., None] * br + m_[..., None] * (bm + am) + o_[..., None] * bo) * dt
        tau_c += ext * 0.5
        ts = tau_to(p, np.broadcast_to(s, p.shape))
        T = np.exp(-(tau_c + ts))
        acc_r += T * r_[..., None] * br * dt
        acc_m += T * m_[..., None] * bm * dt
        tau_c += ext * 0.5
    pr = 3 / (16 * math.pi) * (1 + mu ** 2)
    pm = 3 / (8 * math.pi) * ((1 - g * g) * (1 + mu ** 2)) / ((2 + g * g) * (1 + g * g - 2 * g * mu) ** 1.5)
    ms = A["multi_scattering"] * 0.25 / (4 * math.pi)  # aproximação grosseira do espalhamento múltiplo
    lum = acc_r * (pr[..., None] + ms) + acc_m * (pm[..., None] + ms)
    return els, azs, lum


def tonemap(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14  # ACES (Narkowicz)
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0, 1)


def render_view(dirs, preset_name, textures, cam_z_km=0.002):
    """Cor linear (antes do tonemap) para direções de visão dirs (...x3), câmera no centro do mapa."""
    P = cfg.PRESETS[preset_name]
    shp = dirs.shape[:-1]
    D = dirs.reshape(-1, 3)
    sd = np.array(cfg.sun_direction(P))
    sun_lin = srgb_to_lin(np.array(P["sun_color"]) / 255.0)
    # céu
    els, azs, lut = atmosphere_lut(sd)
    # a prévia normaliza o céu (a exposição real depende da Unreal); 90% do céu fica <= 0,55
    lut = lut / max(1e-9, np.percentile(lut[len(els) // 8:].sum(-1), 90)) * 0.55 * 3
    el = np.arcsin(np.clip(D[:, 2], -1, 1))
    sun_az = math.atan2(sd[1], sd[0])
    daz = np.abs((np.arctan2(D[:, 1], D[:, 0]) - sun_az + math.pi) % TAU - math.pi)
    fe = np.clip((el - els[0]) / (els[-1] - els[0]) * (len(els) - 1), 0, len(els) - 1.001)
    fa = np.clip(daz / math.pi * (len(azs) - 1), 0, len(azs) - 1.001)
    e0, a0 = fe.astype(int), fa.astype(int)
    we, wa = (fe - e0)[:, None], (fa - a0)[:, None]
    sky = (lut[e0, a0] * (1 - we) * (1 - wa) + lut[e0 + 1, a0] * we * (1 - wa)
           + lut[e0, a0 + 1] * (1 - we) * wa + lut[e0 + 1, a0 + 1] * we * wa)
    col = sky * sun_lin / max(1e-6, sun_lin.mean()) * np.array(P["sky_luminance"]) * P["sun_lux"] / 5.0
    cosang = D @ sd
    disk = cosang > math.cos(math.radians(P["sun_angle"] / 2))
    col[disk] += sun_lin * np.array(P["sun_disk"]) * 40.0
    col += sun_lin * 0.35 * np.exp(-(np.arccos(np.clip(cosang, -1, 1)) / 0.05) ** 2)[:, None] * P["sun_disk"][0]
    # estrelas (cúpula aditiva) com o mesmo "fade" perto do sol do material
    lon = np.arctan2(D[:, 1], D[:, 0])
    lat = np.arcsin(np.clip(D[:, 2], -1, 1))
    st = srgb_to_lin(sample_eq(textures["T_Sky_Stars"], lon / TAU, 0.5 - lat / math.pi) / 255.0)
    fade = np.clip(1.5 + 1.6 * (-cosang), 0, 1)
    col += st * fade[:, None] * P["stars"] * 0.5
    depth = np.full(len(D), np.inf)
    # aurora (cilindro deformado, raio AURORA radius_km)
    Rk = cfg.AURORA["radius_km"]
    th = np.degrees((lon - math.radians(cfg.AURORA["az"] + cfg.SKY_YAW) + math.pi) % TAU - math.pi)
    inr = (th > AURORA_A0) & (th < AURORA_A1)
    r, z0, z1 = aurora_shape(np.clip(th, AURORA_A0, AURORA_A1))
    horiz = np.sqrt(D[:, 0] ** 2 + D[:, 1] ** 2) + 1e-9
    tdist = Rk * r / horiz
    zk = D[:, 2] * tdist / Rk
    t_rel = (zk - z0) / (z1 - z0)
    msk = inr & (t_rel > 0) & (t_rel < 1)
    atex = textures["T_Sky_Aurora"] / 255.0
    u = (th - AURORA_A0) / (AURORA_A1 - AURORA_A0) * AURORA_U_REPEAT
    vrow = 1 - np.clip(t_rel, 0, 0.999)
    s1 = sample_eq(atex, u, vrow)
    s2 = sample_eq(atex, u * 2.3 + 0.37, vrow)
    rays = s1[:, 0] * s2[:, 0] * 2.2
    cb, ct = np.array(cfg.AURORA_COLORS["bottom"]), np.array(cfg.AURORA_COLORS["top"])
    acol = (cb[None] * (1 - s1[:, 2:3]) + ct[None] * s1[:, 2:3]) * (rays * s1[:, 1] * aurora_end_fade(np.clip(th, AURORA_A0, AURORA_A1)))[:, None]
    col += np.where(msk[:, None], acol * P["aurora"] * 0.22, 0)
    # corpos opacos (planeta e luas)
    def shade_body(hitn, dview, albedo, bright, amb, rim, rimc, haze):
        lam = hitn @ sd
        s = np.clip(lam * 0.85 + 0.15, 0, 1)
        sh = amb + (1 - amb) * s
        fres = np.clip(1 - np.abs(np.sum(hitn * (-dview), -1)), 0, 1) ** 3
        return albedo * sh[:, None] * bright + fres[:, None] * np.array(rimc) * rim * s[:, None] + np.array(haze)

    tex_lin = {k: srgb_to_lin(textures[k] / 255.0) for k in ("T_Sky_Planet", "T_Sky_MoonA", "T_Sky_MoonB")}
    planet_info = None
    for body in cfg.BODIES:
        loc, prot, scale = cfg.body_transform(body)
        C = np.array(loc) / 100000.0 - np.array([0, 0, cam_z_km])
        Rb = scale * cfg.MESH_RADIUS_CM / 100000.0
        b = D @ C
        disc = b * b - (C @ C - Rb * Rb)
        hit = disc > 0
        t = b - np.sqrt(np.maximum(disc, 0))
        hit &= (t > 0) & (t < depth)
        if not hit.any():
            continue
        idx = np.where(hit)[0]
        Ph = D[idx] * t[idx, None]
        N = (Ph - C) / Rb
        X, Y, Z = (np.array(a) for a in cfg.rotator_axes(*prot))
        lx, ly, lz = N @ X, N @ Y, N @ Z
        uu = (np.arctan2(ly, lx) / TAU) % 1.0
        vv = 0.5 - np.arcsin(np.clip(lz, -1, 1)) / math.pi
        key = {"planet": "T_Sky_Planet", "moon_a": "T_Sky_MoonA", "moon_b": "T_Sky_MoonB"}[body["key"]]
        alb = sample_eq(tex_lin[key], uu, vv)
        is_planet = body["key"] == "planet"
        bright = P["planet_bright"] if is_planet else P["moon_bright"]
        rim = P["rim"] * (1.0 if is_planet else 0.4)
        rimc = cfg.PLANET_RIM if is_planet else (0.7, 0.8, 1.0)
        col[idx] = shade_body(N, D[idx], alb, bright, P["ambient"], rim, rimc, P["haze"])
        depth[idx] = t[idx]
        if is_planet:
            planet_info = (C, Rb, Z)
    # anéis (translúcidos, com sombra do planeta)
    if planet_info is not None:
        C, Rb, Z = planet_info
        dn = D @ Z
        t = ((C @ Z) / np.where(np.abs(dn) < 1e-9, 1e-9, dn))
        Ph = D * t[:, None]
        rr = np.linalg.norm(Ph - C, axis=1) / Rb
        ok = (t > 0) & (t < depth) & (rr > RING_INNER) & (rr < RING_OUTER)
        if ok.any():
            idx = np.where(ok)[0]
            rt = textures["T_Sky_Rings"][0] / 255.0
            ui = np.clip(((rr[idx] - RING_INNER) / (RING_OUTER - RING_INNER) * rt.shape[0]).astype(int), 0, rt.shape[0] - 1)
            rc = srgb_to_lin(rt[ui, :3])
            ra = rt[ui, 3] * P["ring_opacity"]
            Dv = Ph[idx] - C
            tl = Dv @ sd
            dist = np.linalg.norm(Dv - tl[:, None] * sd[None], axis=1)
            outside = np.clip((dist - Rb) / (Rb * 0.03), 0, 1)
            behind = np.clip(-tl / (Rb * 0.2), 0, 1)
            shadow = 1 + (outside - 1) * behind
            rcol = rc * P["ring_bright"] * shadow[:, None]
            col[idx] = col[idx] * (1 - ra[:, None]) + rcol * ra[:, None]
    return col.reshape(shp + (3,)), sd


def add_ground(img, dirs, preset_name, seed=5):
    """Silhueta de morros/árvores alienígenas com a cor da neblina, só para dar escala."""
    P = cfg.PRESETS[preset_name]
    rng = np.random.default_rng(seed)
    az = np.degrees(np.arctan2(dirs[..., 1], dirs[..., 0])) % 360
    el = np.degrees(np.arcsin(np.clip(dirs[..., 2], -1, 1)))
    a = np.arange(3600) / 10.0
    hill = 1.2 + 2.2 * noise1d(3600, 24, rng, wrap=True) + 0.8 * noise1d(3600, 90, rng, wrap=True)
    for _ in range(120):  # copas redondas de árvores alienígenas
        c = rng.uniform(0, 360)
        w = rng.uniform(0.6, 2.2)
        d = np.abs((a - c + 180) % 360 - 180)
        cap = np.sqrt(np.clip(1 - (d / w) ** 2, 0, 1))
        hill = np.maximum(hill, np.where(d < w, hill + cap * w * 0.7, 0))
    hz = hill[(az * 10).astype(int) % 3600]
    m = el < hz
    fog = srgb_to_lin(np.array(P["fog_color"]) ** (1 / 2.2)) * 0.9
    depthfade = np.clip((1.5 - el) / 9.0, 0, 1)[..., None]
    gcol = fog * (1 - depthfade) + np.array([0.02, 0.012, 0.03]) * depthfade
    img = np.where(m[..., None], gcol, img)
    return img


def render_preview(out, textures, preset_name=cfg.DEFAULT_PRESET, filename="sky_preview.png"):
    W, H = 1600, 900
    yaw, pitch, hfov = math.radians(-14 + cfg.SKY_YAW), math.radians(19), math.radians(100)
    fx = math.tan(hfov / 2)
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = 1 - (np.arange(H) + 0.5) / H * 2
    Xs, Ys = np.meshgrid(xs * fx, ys * fx * H / W)
    fwd = np.array([math.cos(pitch) * math.cos(yaw), math.cos(pitch) * math.sin(yaw), math.sin(pitch)])
    right = np.array([-math.sin(yaw), math.cos(yaw), 0.0])   # Unreal: +Y fica à direita de +X
    up = np.cross(fwd, right)
    d = fwd[None, None] + Xs[..., None] * right[None, None] + Ys[..., None] * up[None, None]
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    main, _ = render_view(d, preset_name, textures)
    main = add_ground(main, d, preset_name)
    # panorama 360 (elevação -8 a 72)
    PW, PH = 1600, 356
    lon = math.radians(cfg.SKY_YAW) - math.pi + (np.arange(PW) + 0.5) / PW * TAU   # girar à direita = yaw cresce
    lat = np.radians(72 - (np.arange(PH) + 0.5) / PH * 80)
    LON, LAT = np.meshgrid(lon, lat)
    pd = np.stack([np.cos(LAT) * np.cos(LON), np.cos(LAT) * np.sin(LON), np.sin(LAT)], -1)
    pano, _ = render_view(pd, preset_name, textures)
    pano = add_ground(pano, pd, preset_name)
    exposure = 1.0
    img = np.concatenate([main, np.zeros((6, W, 3)), pano], 0)
    img = lin_to_srgb(tonemap(img * exposure))
    img[H:H + 6] = 0.08
    write_png(os.path.join(out, filename), to_u8(img))
    print(f"[make_sky] prévia: {os.path.join(out, filename)}")


def load_png(path):
    """Leitor PNG mínimo (8 bits, sem entrelaçamento) para --prevonly."""
    with open(path, "rb") as fh:
        data = fh.read()
    pos, idat, w, h, c = 8, b"", 0, 0, 3
    while pos < len(data):
        n = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + n]
        if tag == b"IHDR":
            w, h, _, ct = struct.unpack(">IIBB", body[:10])
            c = {0: 1, 2: 3, 6: 4}[ct]
        elif tag == b"IDAT":
            idat += body
        pos += 12 + n
    raw = np.frombuffer(zlib.decompress(idat), np.uint8).reshape(h, 1 + w * c)
    out = np.zeros((h, w * c), np.int32)
    prev = np.zeros(w * c, np.int32)
    for y in range(h):
        f, line = raw[y, 0], raw[y, 1:].astype(np.int32)
        if f == 0:
            cur = line
        elif f == 2:
            cur = (line + prev) & 255
        else:
            cur = line.copy()
            for x in range(w * c):
                a = cur[x - c] if x >= c else 0
                if f == 1:
                    cur[x] = (line[x] + a) & 255
                elif f == 3:
                    cur[x] = (line[x] + ((a + prev[x]) >> 1)) & 255
                else:
                    b, cc = prev[x], prev[x - c] if x >= c else 0
                    p = a + b - cc
                    pa, pb, pc = abs(p - a), abs(p - b), abs(p - cc)
                    cur[x] = (line[x] + (a if pa <= pb and pa <= pc else (b if pb <= pc else cc))) & 255
        out[y] = cur
        prev = cur
    return out.reshape(h, w, c).astype(np.uint8)


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    pos = [a for a in argv if not a.startswith("--")]
    out = os.path.abspath(pos[0]) if pos else os.path.join(REPO, "assets", "work", "sky")
    os.makedirs(out, exist_ok=True)
    textures = {}
    if "--prevonly" in argv:
        for k in TEXTURES:
            textures[k] = load_png(os.path.join(out, k + ".png"))
    else:
        for k, fn in TEXTURES.items():
            textures[k] = fn()
            write_png(os.path.join(out, k + ".png"), textures[k])
            print(f"[make_sky] {k}.png {textures[k].shape[1]}x{textures[k].shape[0]}")
        build_meshes(out)
    if "--noprev" not in argv:
        preset = next((a[9:] for a in argv if a.startswith("--preset=")), cfg.DEFAULT_PRESET)
        render_preview(out, textures, preset)
        if preset != "night":
            render_preview(out, textures, "night", "sky_preview_night.png")


if __name__ == "__main__":
    main()
