"""Prévias do item 7 (morros v2) do L01: ANTES x DEPOIS com proxies simples (Blender 5.3, bpy, Workbench).

Não mexe no mapa: só lê os arquivos e grava PNGs.

Uso (python com bpy, ou blender -b -P ... -- <args>):
  python tools/blender/preview_morros_l01.py --npz assets/work/levels/L01/l01_preview_v3.npz \
      --antes <pasta com l01_scatter_v3.bin/.json de hoje> \
      --depois <pasta com o resultado de scatter_l01_v3.py --morros-v2> \
      --mirantes <pasta-depois>/l01_mirantes_v2.json \
      --out assets/work/levels/L01/previews_morros

Saídas (PNG): 01_topo_antes_depois, 02_olho_A/B/C_antes_depois, 03_mirante_perto, 00_folha_contato.
Proxies: árvore = cone verde (cogumelo gigante = roxo), arbusto = cone baixo verde-oliva, pedra = octaedro
cinza, rocha grande = octaedro cinza-escuro, cristal = ciano, tronco = marrom. O chão (grama) não entra.
Mirante (só no DEPOIS): disco amarelo no topo, caixa laranja (recompensa) e a trilha em marrom claro.
"""
import json
import math
import os
import struct
import sys

import bpy
import numpy as np
from PIL import Image, ImageDraw

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]


def arg(name, default=None):
    return ARGS[ARGS.index(name) + 1] if name in ARGS else default


NPZ = arg("--npz")
ANTES, DEPOIS = arg("--antes"), arg("--depois")
MIR = arg("--mirantes")
OUT = arg("--out", "previews_morros")
W_EYE, H_EYE = int(arg("--w", 960)), int(arg("--h", 540))
TOP_PX = int(arg("--top", 900))
os.makedirs(OUT, exist_ok=True)

HALF, STEP = 1000.0, 4.0
Z = np.load(NPZ)
H = Z["H"].astype(np.float64)
COL = Z["col"].astype(np.float64)
COL = COL / 255.0 if COL.max() > 1.5 else COL
n = H.shape[0]
xs = np.linspace(-HALF, HALF, n)


def height(X, Y):
    fi = np.clip((np.asarray(X) + HALF) / STEP, 0, n - 1.001)
    fj = np.clip((np.asarray(Y) + HALF) / STEP, 0, n - 1.001)
    i, j = fi.astype(int), fj.astype(int)
    a, b = fi - i, fj - j
    return (H[i, j] * (1 - a) * (1 - b) + H[i + 1, j] * a * (1 - b) + H[i, j + 1] * (1 - a) * b
            + H[i + 1, j + 1] * a * b)


# ----------------------------------------------------------------------------- cena
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sh = sc.display.shading
    sh.light = "STUDIO"
    sh.color_type = "VERTEX"
    sh.show_shadows = True
    sh.shadow_intensity = 0.45
    sh.show_cavity = True
    sh.cavity_type = "WORLD"
    sh.background_type = "VIEWPORT"
    sh.background_color = (0.62, 0.74, 0.86)
    sc.display.light_direction = (0.45, -0.35, 0.82)
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    return sc


def mesh_obj(name, V, F, C):
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.astype(np.float32).ravel())
    nl = np.array([len(f) for f in F]) if isinstance(F, list) else np.full(len(F), F.shape[1])
    flat = np.concatenate(F) if isinstance(F, list) else F.ravel()
    me.loops.add(len(flat))
    me.loops.foreach_set("vertex_index", flat.astype(np.int32))
    me.polygons.add(len(nl))
    starts = np.concatenate([[0], np.cumsum(nl)[:-1]])
    me.polygons.foreach_set("loop_start", starts.astype(np.int32))
    me.polygons.foreach_set("loop_total", nl.astype(np.int32))
    me.update(calc_edges=True)
    at = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    rgba = np.concatenate([C, np.ones((len(C), 1))], 1).astype(np.float32)
    at.data.foreach_set("color", rgba.ravel())
    me.color_attributes.active_color = at
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def terrain(step=1):
    h = H[::step, ::step]
    c = COL[::step, ::step]
    m = h.shape[0]
    xx = xs[::step]
    GX, GY = np.meshgrid(xx, xx, indexing="ij")
    V = np.stack([GX.ravel(), GY.ravel(), h.ravel()], 1)
    idx = np.arange(m * m).reshape(m, m)
    F = np.stack([idx[:-1, :-1].ravel(), idx[1:, :-1].ravel(), idx[1:, 1:].ravel(), idx[:-1, 1:].ravel()], 1)
    return mesh_obj("Terreno", V, F, c.reshape(-1, 3))


# ----------------------------------------------------------------------------- proxies
def cone(k=6):
    a = np.linspace(0, 2 * np.pi, k, endpoint=False)
    V = np.concatenate([np.stack([np.cos(a), np.sin(a), np.zeros(k)], 1), [[0, 0, 1]]])
    F = np.array([[i, (i + 1) % k, k] for i in range(k)])
    return V, F


def octa():
    V = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -0.4]], float)
    F = np.array([[0, 2, 4], [2, 1, 4], [1, 3, 4], [3, 0, 4], [2, 0, 5], [1, 2, 5], [3, 1, 5], [0, 3, 5]])
    return V, F


def column():   # prisma (tronco, cristal)
    a = np.linspace(0, 2 * np.pi, 5, endpoint=False)
    b = np.stack([np.cos(a), np.sin(a)], 1)
    V = np.concatenate([np.c_[b, np.zeros(5)], np.c_[b * 0.6, np.ones(5)]])
    F = np.array([[i, (i + 1) % 5, 5 + (i + 1) % 5, 5 + i] for i in range(5)])
    return V, F


KIND = {  # malha -> (forma, cor, raio relativo à altura)
    "arvore": ("cone", (0.16, 0.42, 0.16), 0.33), "arvore_morta": ("cone", (0.42, 0.36, 0.26), 0.25),
    "cogumelo": ("cone", (0.55, 0.30, 0.62), 0.45), "arbusto": ("cone", (0.36, 0.48, 0.20), 0.7),
    "pedra": ("octa", (0.52, 0.52, 0.50), 0.75), "rocha": ("octa", (0.36, 0.36, 0.37), 0.8),
    "cristal": ("col", (0.20, 0.90, 0.95), 0.25), "tronco": ("col", (0.40, 0.27, 0.15), 0.25),
    "detalhe": ("cone", (0.72, 0.62, 0.30), 0.5),
}


def kind_of(mesh, layer):
    if layer == "chao":
        return None
    if "Cristal" in mesh:
        return "cristal"
    if "Tronco" in mesh:
        return "tronco"
    if mesh in ("NAT_Penhasco", "NAT_Pedra3"):
        return "rocha"
    if "Pedra" in mesh or "Pebble" in mesh:
        return "pedra"
    if mesh == "NAT_Arvore3":
        return "arvore_morta"
    if mesh == "NAT_Cogumelo":
        return "cogumelo"
    if layer == "arvores":
        return "arvore"
    if layer == "arbustos":
        return "arbusto"
    return "detalhe"


def load_scatter(d):
    idx = json.load(open(os.path.join(d, "l01_scatter_v3.json"), encoding="utf-8"))
    raw = open(os.path.join(d, "l01_scatter_v3.bin"), "rb").read()
    N = struct.unpack("<iii", raw[4:16])[2]
    rec = np.frombuffer(raw[16:], "<f4").reshape(N, 9)
    out = {}
    for bt in idx["batches"]:
        k = kind_of(bt["mesh"], bt["layer"])
        if k is None:
            continue
        r = rec[bt["first"]:bt["first"] + bt["count"]]
        out.setdefault(k, []).append(r)
    return {k: np.concatenate(v) for k, v in out.items()}


BASE_H = {"arvore": 10.0, "arvore_morta": 7.5, "cogumelo": 5.5, "arbusto": 1.2, "pedra": 1.4, "rocha": 3.8,
          "cristal": 2.5, "tronco": 0.8, "detalhe": 0.6}


def proxies(data, center=None, radius=None, scale_up=1.0, hole=None):
    shapes = {"cone": cone(), "octa": octa(), "col": column()}
    for k, r in data.items():
        X, Y, Zb = r[:, 0] / 100.0, -r[:, 1] / 100.0, r[:, 2] / 100.0
        sel = np.ones(len(X), bool)
        if center is not None:
            sel = np.hypot(X - center[0], Y - center[1]) < radius
        if hole is not None:                       # nada colado na câmera (não abrir a vista dentro de uma copa)
            sel &= np.hypot(X - hole[0], Y - hole[1]) > hole[2]
        if not sel.any():
            continue
        X, Y, Zb = X[sel], Y[sel], Zb[sel]
        # altura: escala relativa (coluna sz do registro) x altura base, com limites
        sz = r[sel, 8]
        rel = np.clip(sz / max(1e-6, float(np.median(r[:, 8]))), 0.5, 1.8)
        h = BASE_H[k] * rel * scale_up
        shp, col, rr = KIND[k]
        V0, F0 = shapes[shp]
        m = len(X)
        ang = (X * 12.9898 + Y * 78.233) % (2 * np.pi)
        ca, sa = np.cos(ang), np.sin(ang)
        rad = h * rr
        if k == "arvore":   # copa começa a 25% da altura: cone + tronco fino implícito
            zoff = 0.25 * h
            hh = 0.75 * h
        else:
            zoff, hh = 0.0, h
        Vx = (V0[None, :, 0] * ca[:, None] - V0[None, :, 1] * sa[:, None]) * rad[:, None] + X[:, None]
        Vy = (V0[None, :, 0] * sa[:, None] + V0[None, :, 1] * ca[:, None]) * rad[:, None] + Y[:, None]
        Vz = V0[None, :, 2] * hh[:, None] + (Zb + zoff)[:, None]
        V = np.stack([Vx, Vy, Vz], -1).reshape(-1, 3)
        F = (F0[None] + (np.arange(m) * len(V0))[:, None, None]).reshape(-1, F0.shape[1])
        jit = 0.85 + 0.3 * ((X * 3.1 + Y * 1.7) % 1.0)
        C = np.repeat(np.clip(np.array(col)[None] * jit[:, None], 0, 1), len(V0), 0)
        mesh_obj("P_" + k, V, F, C)
        if k == "arvore":   # troncos
            Vc, Fc = column()
            tr = np.full(m, 0.35) * (h / 10.0)
            Vx = Vc[None, :, 0] * tr[:, None] + X[:, None]
            Vy = Vc[None, :, 1] * tr[:, None] + Y[:, None]
            Vz = Vc[None, :, 2] * (0.3 * h)[:, None] + Zb[:, None]
            V = np.stack([Vx, Vy, Vz], -1).reshape(-1, 3)
            F = (Fc[None] + (np.arange(m) * len(Vc))[:, None, None]).reshape(-1, 4)
            mesh_obj("P_tronco_arv", V, F, np.tile([0.33, 0.22, 0.12], (len(V), 1)))


def mirantes_objs(mir):
    for m in mir["mirantes"]:
        tx, ty, tz = m["topo_cm"][0] / 100, -m["topo_cm"][1] / 100, m["topo_cm"][2] / 100
        # disco do topo
        k = 24
        a = np.linspace(0, 2 * np.pi, k, endpoint=False)
        R = m["raio_cm"] / 100
        V = np.concatenate([[[tx, ty, tz + 0.15]], np.stack([tx + R * np.cos(a), ty + R * np.sin(a),
                                                              height(tx + R * np.cos(a), ty + R * np.sin(a)) + 0.15], 1)])
        F = np.array([[0, 1 + i, 1 + (i + 1) % k] for i in range(k)])
        mesh_obj(m["id"] + "_topo", V, F, np.tile([0.95, 0.82, 0.25], (len(V), 1)))
        # recompensa: caixa laranja 1,6 m (antena: mastro alto)
        hb = 9.0 if m["recompensa"] == "antena" else 1.6
        wb = 0.5 if m["recompensa"] == "antena" else 1.2
        bx = np.array([[-1, -1, 0], [1, -1, 0], [1, 1, 0], [-1, 1, 0], [-1, -1, 1], [1, -1, 1], [1, 1, 1], [-1, 1, 1]], float)
        V = bx * [wb, wb, hb] + [tx, ty, tz]
        F = np.array([[0, 1, 2, 3], [4, 7, 6, 5], [0, 4, 5, 1], [1, 5, 6, 2], [2, 6, 7, 3], [3, 7, 4, 0]])
        mesh_obj(m["id"] + "_recompensa", V, F, np.tile([1.0, 0.45, 0.08], (8, 1)))
        # trilha (faixa de 2 m acompanhando o terreno)
        P = np.array([[p[0] / 100, -p[1] / 100] for p in m["trilha_cm"]])
        L = np.r_[0, np.cumsum(np.hypot(*np.diff(P, axis=0).T))]
        t = np.linspace(0, L[-1], max(2, int(L[-1] / 2)))
        cx, cy = np.interp(t, L, P[:, 0]), np.interp(t, L, P[:, 1])
        dx, dy = np.gradient(cx), np.gradient(cy)
        dl = np.hypot(dx, dy) + 1e-9
        nx, ny = -dy / dl, dx / dl
        lx, ly, rx, ry = cx + nx, cy + ny, cx - nx, cy - ny
        V = np.concatenate([np.stack([lx, ly, height(lx, ly) + 0.12], 1), np.stack([rx, ry, height(rx, ry) + 0.12], 1)])
        q = len(cx)
        F = np.array([[i, i + 1, q + i + 1, q + i] for i in range(q - 1)])
        mesh_obj(m["id"] + "_trilha", V, F, np.tile([0.80, 0.62, 0.38], (len(V), 1)))


def camera(loc, look, lens=24.0, ortho=None):
    cd = bpy.data.cameras.new("Cam")
    if ortho:
        cd.type = "ORTHO"
        cd.ortho_scale = ortho
    else:
        cd.lens = lens
    cd.clip_start, cd.clip_end = 0.1, 5000
    ob = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    d = np.array(look, float) - np.array(loc, float)
    yaw = math.atan2(d[1], d[0]) - math.pi / 2
    pitch = math.atan2(d[2], math.hypot(d[0], d[1]))
    ob.rotation_euler = (math.pi / 2 + pitch, 0, yaw)
    bpy.context.scene.camera = ob
    return ob


def render(path, w, h):
    sc = bpy.context.scene
    sc.render.resolution_x, sc.render.resolution_y = w, h
    sc.render.resolution_percentage = 100
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


# ----------------------------------------------------------------------------- vistas
def eye_views(mir):
    """3 pontos da estrada: o começo da trilha de cada mirante, olhando para o topo (é o que o jogador vê)."""
    out = []
    for m in mir["mirantes"][:3]:
        s = m["trilha_cm"][0]
        sx, sy = s[0] / 100, -s[1] / 100
        tx, ty, tz = m["topo_cm"][0] / 100, -m["topo_cm"][1] / 100, m["topo_cm"][2] / 100
        d = np.array([tx - sx, ty - sy])
        d /= np.linalg.norm(d)
        # câmera no próprio ponto da estrada onde a trilha começa (a estrada já é limpa)
        ex, ey = sx - d[0] * 3, sy - d[1] * 3
        ez = float(height(ex, ey)) + 1.7
        look = (tx, ty, tz * 0.6 + ez * 0.4)
        out.append((m["id"], (ex, ey, ez), look, (tx, ty)))
    return out


def scene_for(data, mir, focus=None, radius=None, with_mir=False, scale_up=1.0, hole=None):
    reset()
    terrain(1)
    proxies(data, focus, radius, scale_up, hole)
    if with_mir:
        mirantes_objs(mir)


def side_by_side(a, b, out, la="ANTES", lb="DEPOIS (morros v2)"):
    A, B = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    W = A.width + B.width + 12
    im = Image.new("RGB", (W, A.height + 34), (24, 24, 24))
    im.paste(A, (0, 34))
    im.paste(B, (A.width + 12, 34))
    dr = ImageDraw.Draw(im)
    dr.text((10, 10), la, fill=(255, 255, 255))
    dr.text((A.width + 22, 10), lb, fill=(255, 220, 120))
    im.save(out)
    return out


def main():
    mir = json.load(open(MIR, encoding="utf-8"))
    tmp = os.path.join(OUT, "_parciais")
    os.makedirs(tmp, exist_ok=True)
    data = {"antes": load_scatter(ANTES), "depois": load_scatter(DEPOIS)}
    views = eye_views(mir)
    finals = []
    for tag in ("antes", "depois"):
        # (a) topo do mapa inteiro
        scene_for(data[tag], mir, with_mir=(tag == "depois"), scale_up=2.5)   # proxies 2,5x maiores só no topo
        camera((0, 0, 900), (0, 0.001, 0), ortho=2000)
        render(os.path.join(tmp, f"topo_{tag}.png"), TOP_PX, TOP_PX)
        # (b) olho do herói (1,7 m) em 3 pontos da estrada; proxies até 700 m
        for vid, loc, look, tgt in views:
            scene_for(data[tag], mir, focus=loc[:2], radius=700, with_mir=(tag == "depois"), hole=(loc[0], loc[1], 6.0))
            camera(loc, look, lens=22)
            render(os.path.join(tmp, f"olho_{vid}_{tag}.png"), W_EYE, H_EYE)
    finals.append(side_by_side(os.path.join(tmp, "topo_antes.png"), os.path.join(tmp, "topo_depois.png"),
                               os.path.join(OUT, "01_topo_antes_depois.png")))
    for n_, (vid, *_r) in enumerate(views):
        finals.append(side_by_side(os.path.join(tmp, f"olho_{vid}_antes.png"), os.path.join(tmp, f"olho_{vid}_depois.png"),
                                   os.path.join(OUT, f"02_olho_{'ABC'[n_]}_{vid}_antes_depois.png")))
    # (c) um mirante de perto (depois): câmera a ~30 m do topo, 8 m acima, olhando o disco
    m = mir["mirantes"][0]
    tx, ty, tz = m["topo_cm"][0] / 100, -m["topo_cm"][1] / 100, m["topo_cm"][2] / 100
    s = m["trilha_cm"][-3]
    sx, sy = s[0] / 100, -s[1] / 100
    d = np.array([sx - tx, sy - ty])
    d /= np.linalg.norm(d) + 1e-9
    cx, cy = tx + d[0] * 30, ty + d[1] * 30
    scene_for(data["depois"], mir, focus=(tx, ty), radius=400, with_mir=True)
    camera((cx, cy, max(float(height(cx, cy)) + 8, tz + 4)), (tx, ty, tz + 1), lens=24)
    finals.append(render(os.path.join(OUT, f"03_mirante_perto_{m['id']}.png"), W_EYE, H_EYE))
    # folha de contato
    ims = [Image.open(p).convert("RGB") for p in finals]
    cw = 960
    rows = []
    for im in ims:
        r = cw / im.width
        rows.append(im.resize((cw, int(im.height * r))))
    sheet = Image.new("RGB", (cw, sum(r.height for r in rows) + 8 * len(rows)), (18, 18, 18))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height + 8
    sheet.save(os.path.join(OUT, "00_folha_contato.png"))
    print("prévias em", os.path.abspath(OUT), [os.path.basename(p) for p in finals])


main()
