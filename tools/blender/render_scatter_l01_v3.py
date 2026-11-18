"""Prévia na altura dos olhos da vegetação da Fase 1 v3, com as malhas de verdade (Cycles, sem a Unreal).

Uso (Blender 5.2):
  blender -b --python tools/blender/render_scatter_l01_v3.py -- assets/work/levels/L01 [zona] [lado]
  (sem zona: renderiza as duas: scatter_eye_forest.png na zona 3 e scatter_eye_desert.png na zona 1)
Entradas: l01_preview_v3.npz (relevo), l01_scatter_v3.bin/.json (tools/blender/scatter_l01_v3.py),
  assets/work/tripo/SM_<Nome>.fbx + textures/T_<Nome>_D.jpg (modelos do usuário),
  assets/raw/quaternius/StylizedNatureMegaKit/FBX/<Nome>.fbx (grama; cor = tint do índice, igual às MIs da Unreal).
Câmera: 1,7 m acima da estrada, olhando para o LADO (perpendicular à estrada), FOV 90 como no jogo.
Só aproximação: luz, céu e materiais não são os da Unreal; serve para conferir densidade e escala.
"""
import json
import math
import os
import sys

import bpy
import numpy as np

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.abspath(ARGS[0]) if ARGS else os.path.join(REPO, "assets", "work", "levels", "L01")
TRIPO = os.path.join(REPO, "assets", "work", "tripo")
QDIR = os.path.join(REPO, "assets", "raw", "quaternius", "StylizedNatureMegaKit", "FBX")
HALF, STEP = 1000.0, 4.0
RADIUS = 110.0                       # m em volta da câmera
SHOTS = {"forest": (3, 0.55, 1), "desert": (1, 0.40, -1)}   # zona, fração do trecho da estrada, lado (+1 esq.)

Z = np.load(os.path.join(OUT, "l01_preview_v3.npz"))
H = Z["H"].astype(float)
COL = Z["col"].astype(float)
N = H.shape[0]
IDX = json.load(open(os.path.join(OUT, "l01_scatter_v3.json"), encoding="utf-8"))
REC = np.fromfile(os.path.join(OUT, "l01_scatter_v3.bin"), dtype="<f4", offset=16).reshape(-1, 9)


def height(X, Y):
    fi = (np.asarray(X, float) + HALF) / STEP
    fj = (np.asarray(Y, float) + HALF) / STEP
    i0 = np.clip(np.floor(fi).astype(int), 0, N - 2)
    j0 = np.clip(np.floor(fj).astype(int), 0, N - 2)
    tx, ty = np.clip(fi - i0, 0, 1), np.clip(fj - j0, 0, 1)
    h00, h10, h11, h01 = H[i0, j0], H[i0 + 1, j0], H[i0 + 1, j0 + 1], H[i0, j0 + 1]
    diag = np.abs(h00 - h11) <= np.abs(h10 - h01)
    a = np.where(tx >= ty, h00 + tx * (h10 - h00) + ty * (h11 - h10), h00 + ty * (h01 - h00) + tx * (h11 - h01))
    b = np.where(tx + ty <= 1, h00 + tx * (h10 - h00) + ty * (h01 - h00),
                 h11 + (1 - tx) * (h01 - h11) + (1 - ty) * (h10 - h11))
    return np.where(diag, a, b)


def colat(X, Y):
    fi = np.clip(np.round((X + HALF) / STEP).astype(int), 0, N - 1)
    fj = np.clip(np.round((Y + HALF) / STEP).astype(int), 0, N - 1)
    return COL[fi, fj]


def mat_color(name, rgb, emit=0.0, rough=0.85):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Roughness"].default_value = rough
    if emit > 0:
        b.inputs["Emission Color"].default_value = (*rgb, 1)
        b.inputs["Emission Strength"].default_value = emit
    return m


def mat_tex(name, path):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    b = nt.nodes["Principled BSDF"]
    t = nt.nodes.new("ShaderNodeTexImage")
    t.image = bpy.data.images.load(path)
    nt.links.new(t.outputs["Color"], b.inputs["Base Color"])
    b.inputs["Roughness"].default_value = 0.8
    return m


def load_proto(key, meta):
    """Importa o FBX e devolve um objeto (escondido) para instanciar."""
    before = set(bpy.data.objects)
    if meta["kind"] == "user":
        fbx = os.path.join(TRIPO, f"SM_{meta['name']}.fbx")
    else:
        fbx = os.path.join(QDIR, meta["ref"].split("/")[1] + ".fbx")
    bpy.ops.import_scene.fbx(filepath=fbx)
    objs = [o for o in bpy.data.objects if o not in before and o.type == "MESH" and not o.name.startswith("UCX_")]
    for o in [o for o in bpy.data.objects if o not in before and o.name.startswith("UCX_")]:
        bpy.data.objects.remove(o)
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    o.name = "P_" + key
    if meta["kind"] == "user":
        tex = os.path.join(TRIPO, "textures", f"T_{meta['name']}_D.jpg")
        m = mat_tex("M_" + key, tex) if os.path.exists(tex) else mat_color("M_" + key, (0.5, 0.5, 0.5))
    else:
        m = mat_color("M_" + key, tuple(meta["tint"]), emit=meta.get("glow", 0.0) * 2.0)
    o.data.materials.clear()
    o.data.materials.append(m)
    # tamanho real do protótipo vs nominal do índice (mesma correção que a Unreal faz: scale_mul)
    d = np.array(o.dimensions)
    nom = np.array(meta["nominal_dims_cm"]) / 100.0
    o["mul"] = float(max(nom) / max(d.max(), 1e-6))
    o.hide_render = True
    o.hide_viewport = True
    return o


def instancer(name, proto, pts, quats, scales):
    """Nuvem de pontos + Geometry Nodes (Instance on Points) com rotação e escala por ponto."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(p) for p in pts], [], [])
    a = me.attributes.new("rot", "QUATERNION", "POINT")
    a.data.foreach_set("value", quats.astype(np.float32).ravel())
    s = me.attributes.new("scl", "FLOAT_VECTOR", "POINT")
    s.data.foreach_set("vector", scales.astype(np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + "_GN", "GeometryNodeTree")
    ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
    ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
    nd = ng.nodes
    gi = nd.new("NodeGroupInput")
    go = nd.new("NodeGroupOutput")
    m2p = nd.new("GeometryNodeMeshToPoints")
    inst = nd.new("GeometryNodeInstanceOnPoints")
    oi = nd.new("GeometryNodeObjectInfo")
    oi.inputs["Object"].default_value = proto
    oi.transform_space = "ORIGINAL"
    ra = nd.new("GeometryNodeInputNamedAttribute")
    ra.data_type = "QUATERNION"
    ra.inputs["Name"].default_value = "rot"
    sa = nd.new("GeometryNodeInputNamedAttribute")
    sa.data_type = "FLOAT_VECTOR"
    sa.inputs["Name"].default_value = "scl"
    L = ng.links
    L.new(gi.outputs[0], m2p.inputs["Mesh"])
    L.new(m2p.outputs["Points"], inst.inputs["Points"])
    L.new(oi.outputs["Geometry"], inst.inputs["Instance"])
    L.new(ra.outputs["Attribute"], inst.inputs["Rotation"])
    L.new(sa.outputs["Attribute"], inst.inputs["Scale"])
    L.new(inst.outputs["Instances"], go.inputs[0])
    mod = ob.modifiers.new("GN", "NODES")
    mod.node_group = ng
    return ob


def build(shot):
    zone, frac, side = SHOTS[shot]
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    road = Z["road"]
    ks = np.where(Z["road_zone"] == zone)[0]
    k = int(ks[0] + frac * (ks[-1] - ks[0]))
    c = road[k]
    t = road[min(k + 3, len(road) - 1)] - road[max(k - 3, 0)]
    t /= np.linalg.norm(t)
    nside = np.array([-t[1], t[0]]) * side
    # terreno local (1 m)
    g = np.arange(-RADIUS, RADIUS + 1, 1.0)
    GX, GY = np.meshgrid(c[0] + g, c[1] + g, indexing="ij")
    Hh = height(GX, GY)
    n = len(g)
    verts = np.stack([GX - c[0], GY - c[1], Hh], -1).reshape(-1, 3)
    faces = [(i * n + j, (i + 1) * n + j, (i + 1) * n + j + 1, i * n + j + 1) for i in range(n - 1) for j in range(n - 1)]
    me = bpy.data.meshes.new("Terreno")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    ca = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
    cols = colat(GX.ravel(), GY.ravel())
    ca.data.foreach_set("color", np.concatenate([cols, np.ones((len(cols), 1))], 1).astype(np.float32).ravel())
    ob = bpy.data.objects.new("Terreno", me)
    sc.collection.objects.link(ob)
    mt = bpy.data.materials.new("M_Terreno")
    mt.use_nodes = True
    vc = mt.node_tree.nodes.new("ShaderNodeVertexColor")
    vc.layer_name = "Col"
    mt.node_tree.links.new(vc.outputs["Color"], mt.node_tree.nodes["Principled BSDF"].inputs["Base Color"])
    mt.node_tree.nodes["Principled BSDF"].inputs["Roughness"].default_value = 0.95
    me.materials.append(mt)
    # estrada (fita de 12 m um pouco acima do terreno)
    sel = np.where(np.linalg.norm(road - c, axis=1) < RADIUS * 1.3)[0]
    rv, rf = [], []
    for i, kk in enumerate(sel):
        tt = road[min(kk + 1, len(road) - 1)] - road[max(kk - 1, 0)]
        tt /= np.linalg.norm(tt)
        nn = np.array([-tt[1], tt[0]])
        for o in (-6.0, 6.0):
            p = road[kk] + nn * o
            rv.append((p[0] - c[0], p[1] - c[1], float(height(road[kk][0], road[kk][1])) + 0.12))
        if i:
            rf.append((2 * i - 2, 2 * i - 1, 2 * i + 1, 2 * i))
    rm = bpy.data.meshes.new("Estrada")
    rm.from_pydata(rv, [], rf)
    rm.materials.append(mat_color("M_Estrada", (0.09, 0.08, 0.09)))
    sc.collection.objects.link(bpy.data.objects.new("Estrada", rm))
    # instâncias perto da câmera (respeita o corte de cada lote)
    cam_xy = c + nside * 0.0
    by_mesh = {}
    for b in IDX["batches"]:
        r = REC[b["first"]:b["first"] + b["count"]]
        X, Y = r[:, 0] / 100.0, -r[:, 1] / 100.0
        d = np.hypot(X - cam_xy[0], Y - cam_xy[1])
        s = (d < min(RADIUS, b["cull_end_cm"] / 100.0)) & (np.abs(X - c[0]) < RADIUS) & (np.abs(Y - c[1]) < RADIUS)
        if s.any():
            by_mesh.setdefault(b["mesh"], []).append(r[s])
    total = 0
    for key, parts in by_mesh.items():
        r = np.concatenate(parts)
        proto = load_proto(key, IDX["meshes"][key])
        mul = proto["mul"]
        pts = np.stack([r[:, 0] / 100.0 - c[0], -r[:, 1] / 100.0 - c[1], r[:, 2] / 100.0], 1)
        # Unreal (qx, qy, qz, qw) -> Blender (w, x, y, z): y espelhado = (w, -qx, qy, -qz)
        q = np.stack([r[:, 6], -r[:, 3], r[:, 4], -r[:, 5]], 1)
        scl = np.stack([r[:, 7], r[:, 7], r[:, 8]], 1) * mul
        instancer("I_" + key, proto, pts, q, scl)
        total += len(r)
    # luz e céu
    sun = bpy.data.lights.new("Sol", "SUN")
    sun.energy = 3.2
    sun.color = (1.0, 0.92, 0.85)
    so = bpy.data.objects.new("Sol", sun)
    so.rotation_euler = (math.radians(50), 0, math.radians(30))
    sc.collection.objects.link(so)
    w = bpy.data.worlds.new("Ceu")
    w.use_nodes = True
    w.node_tree.nodes["Background"].inputs["Color"].default_value = (0.42, 0.30, 0.62, 1)
    w.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.9
    sc.world = w
    # câmera: olhos a 1,7 m na beira da estrada, olhando para o lado
    cz = float(height(c[0], c[1])) + 0.12 + 1.7
    cam = bpy.data.cameras.new("Cam")
    cam.lens_unit = "FOV"
    cam.angle = math.radians(90)
    cam.clip_end = 2000
    co = bpy.data.objects.new("Cam", cam)
    sc.collection.objects.link(co)
    p0 = nside * 3.0
    co.location = (p0[0], p0[1], cz)
    look = np.array([nside[0], nside[1], -math.tan(math.radians(6))])
    yaw = math.atan2(look[1], look[0])
    co.rotation_euler = (math.radians(90 - 6), 0, yaw - math.pi / 2)
    sc.camera = co
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 24
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:  # noqa: BLE001
        pass
    sc.render.resolution_x, sc.render.resolution_y = 1280, 720
    sc.view_settings.view_transform = "Standard"
    sc.render.filepath = os.path.join(OUT, f"scatter_eye_{shot}.png")
    print(f"{shot}: zona {zone}, estrada k={k}, {total} instâncias, {len(by_mesh)} malhas")
    bpy.ops.render.render(write_still=True)


shots = [ARGS[1]] if len(ARGS) > 1 else list(SHOTS)
for s_ in shots:
    if len(ARGS) > 2:
        SHOTS[s_] = (SHOTS[s_][0], SHOTS[s_][1], int(ARGS[2]))
    build(s_)
