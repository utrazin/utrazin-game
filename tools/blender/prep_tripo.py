"""Prepara os modelos do usuário (Tripo 3D, GLB) para a Unreal: tamanho real, origem no pé, +X para frente.

Uso (Blender 5.2 em modo fundo ou bpy como módulo):
  blender -b -P tools/blender/prep_tripo.py -- <pasta_raw> <pasta_saida> [Nome1 Nome2 ...]
  ex.: ... -- assets/raw/tripo assets/work/tripo

Entrada: assets/raw/tripo/tripo_catalog.json (nome final, regra de tamanho, giro, colisão, textura) e os GLB
         assets/raw/tripo/<Nome>.glb (cópias dos originais tripo_convert_<uuid>.glb da pasta do usuário).
Saída (em <pasta_saida>):
  SM_<Nome>.fbx              malha estática em metros (a Unreal converte para cm com escala 1), origem no
                             centro de baixo, frente em +X (armas: origem na pegada, cano/lâmina em +X, cima +Z)
                             + caixas de colisão UCX_SM_<Nome>_NN (regras "box" e "trunk")
  textures/T_<Nome>_D.jpg    cor base reduzida (o Tripo exporta 4096; aqui 1024 ou 2048)
  SM_PRP_Bau_Base.fbx / SM_PRP_Bau_Tampa.fbx   baú dividido (tampa com origem na dobradiça) para o AJRLootChest
  SM_<ZMB_*|NPC_*>_mixamo.fbx  personagem com textura embutida, olhando para -Y do Blender (frente do Mixamo)
  tripo_processed.json       medidas finais (m), triângulos, textura, dados extras (ponte, barraca)
Os GLB do Tripo vêm com 1 malha, 1 material só com cor base (4096) e o maior lado = 1 m; nenhum tem rig.
"""
import json
import os
import sys

import bpy
import bmesh  # noqa: E402
import numpy as np
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
RAW, OUT = argv[0], argv[1]
ONLY = set(argv[2:])
HERE = os.path.dirname(os.path.abspath(__file__))
CAT_PATH = os.path.join(RAW, "tripo_catalog.json")
CAT = json.load(open(CAT_PATH, encoding="utf-8"))
os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
RESULT_PATH = os.path.join(OUT, "tripo_processed.json")
RESULT = json.load(open(RESULT_PATH, encoding="utf-8")) if os.path.exists(RESULT_PATH) else {}


def glb_path(it):
    """Prefere assets/raw/tripo/<Nome>.glb; aceita o nome original tripo_convert_<uuid>.glb."""
    for f in (it["name"] + ".glb", it["src"]):
        p = os.path.join(RAW, f)
        if os.path.exists(p):
            return p
    raise FileNotFoundError(f"{it['name']}: GLB não achado em {RAW}")


def load(it):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=glb_path(it))
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in bpy.context.scene.objects:
        o.select_set(o in meshes)
    bpy.context.view_layer.objects.active = meshes[0]
    if len(meshes) > 1:
        bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for x in list(bpy.context.scene.objects):
        if x != o:
            bpy.data.objects.remove(x, do_unlink=True)
    o.select_set(True)
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return o


def verts(o):
    return np.array([v.co[:] for v in o.data.vertices])


def bounds(o):
    co = verts(o)
    return co.min(0), co.max(0)


def tris(o):
    return sum(len(p.vertices) - 2 for p in o.data.polygons)


def box_obj(name, mn, mx):
    """Caixa de colisão UCX (8 vértices, convexa)."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    c = (np.array(mn) + np.array(mx)) / 2
    s = np.maximum(np.array(mx) - np.array(mn), 0.02)
    me.transform(Matrix.Translation(Vector(c)) @ Matrix.Diagonal(Vector((s[0], s[1], s[2], 1.0))))
    return ob


def collision(o, it, sm_name):
    """Regras: box = caixa da malha toda (casas decorativas: fecha a porta); trunk = só o tronco/poste."""
    mn, mx = bounds(o)
    kind = it["collision"]
    out = []
    if kind == "box":
        out.append(box_obj(f"UCX_{sm_name}_00", mn, mx))
    elif kind == "trunk":
        co = verts(o)
        h = mx[2] - mn[2]
        low = co[co[:, 2] < mn[2] + 0.15 * h]
        c = low[:, :2].mean(0) if len(low) else (mn[:2] + mx[:2]) / 2
        span = max(mx[0] - mn[0], mx[1] - mn[1])
        half = max(0.12, min(0.06 * span, 0.12 * h)) if it["name"] != "PRP_Poste" else 0.15
        top = mn[2] + (0.95 if it["name"] == "PRP_Poste" else 0.45) * h
        out.append(box_obj(f"UCX_{sm_name}_00", (c[0] - half, c[1] - half, mn[2]), (c[0] + half, c[1] + half, top)))
    return out


def save_texture(o, it):
    """Reduz a cor base e salva em JPG (o Tripo embute 4096 x 4096)."""
    size = int(it["tex"])
    path = os.path.join(OUT, "textures", f"T_{it['name']}_D.jpg")
    imgs = [n.image for m in o.data.materials if m and m.node_tree for n in m.node_tree.nodes
            if n.type == "TEX_IMAGE" and n.image]
    if not imgs:
        return None
    img = imgs[0]
    if img.size[0] != size:
        img.scale(size, size)
    scn = bpy.context.scene
    scn.render.image_settings.file_format = "JPEG"
    scn.render.image_settings.quality = 92
    img.save_render(path, scene=scn)
    return os.path.relpath(path, OUT).replace("\\", "/")


def export_fbx(objs, path, embed=False):
    for x in bpy.context.scene.objects:
        x.select_set(x in objs)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                             mesh_smooth_type="FACE", add_leaf_bones=False, colors_type="NONE",
                             path_mode="COPY" if embed else "STRIP", embed_textures=embed)


def weapon_stick(o, it):
    """Graveto: em pé no GLB (cabo embaixo). Vira para +X (cabo atrás), lâmina larga no plano XZ."""
    o.data.transform(Matrix.Rotation(np.radians(90), 4, "Y"))      # Z (comprimento) -> +X; ponta de baixo -> -X
    mn, mx = bounds(o)
    if (mx[1] - mn[1]) > (mx[2] - mn[2]):                           # parte larga em Y -> passa para Z
        o.data.transform(Matrix.Rotation(np.radians(90), 4, "X"))
    mn, mx = bounds(o)
    s = it["size_m"] / (mx[0] - mn[0])
    o.data.transform(Matrix.Scale(s, 4))
    co = verts(o)
    mn, mx = co.min(0), co.max(0)
    L = mx[0] - mn[0]
    gx = mn[0] + 0.12 * L                                            # mão a 12% da ponta do cabo
    ring = co[np.abs(co[:, 0] - gx) < 0.03 * L]
    grip = np.array([gx, ring[:, 1].mean(), ring[:, 2].mean()]) if len(ring) else np.array([gx, 0, 0])
    o.data.transform(Matrix.Translation(Vector(-grip)))
    return {"grip_from_butt_m": round(0.12 * L, 3)}


def weapon_gun(o, it):
    """Escopeta: cano já em +X no GLB. Origem na empunhadura (parte de baixo e de trás), como prep_gun.py."""
    mn, mx = bounds(o)
    s = it["size_m"] / (mx[0] - mn[0])
    o.data.transform(Matrix.Scale(s, 4))
    co = verts(o)
    mn, mx = co.min(0), co.max(0)
    low = co[(co[:, 2] < mn[2] + 0.45 * (mx[2] - mn[2])) & (co[:, 0] < mn[0] + 0.55 * (mx[0] - mn[0]))]
    if len(low) < 20:
        low = co[co[:, 2] < mn[2] + 0.45 * (mx[2] - mn[2])]
    grip = np.array([low[:, 0].mean(), low[:, 1].mean(), mn[2] + 0.62 * (low[:, 2].max() - mn[2])])
    o.data.transform(Matrix.Translation(Vector(-grip)))
    return {"grip_m": [round(float(x), 3) for x in grip]}


def weapon_rifle(o, it):
    """Rifle de precisão (ARM_Sniper, A-057): cano já em +X no GLB, coronha em -X, luneta em cima.
    Origem no centro do punho da pistola (fatia de 18% a 40% do comprimento a partir da coronha, terço de baixo):
    a regra da escopeta pegaria a coronha junto. Guarda o centro da luneta (cm de câmera do C++)."""
    mn, mx = bounds(o)
    s = it["size_m"] / (mx[0] - mn[0])
    o.data.transform(Matrix.Scale(s, 4))
    co = verts(o)
    mn, mx = co.min(0), co.max(0)
    L, H = mx[0] - mn[0], mx[2] - mn[2]
    band = co[(co[:, 0] > mn[0] + 0.18 * L) & (co[:, 0] < mn[0] + 0.40 * L) & (co[:, 2] < mn[2] + 0.35 * H)]
    if len(band) < 20:
        band = co[co[:, 2] < mn[2] + 0.35 * H]
    grip = np.array([band[:, 0].mean(), band[:, 1].mean(), mn[2] + 0.7 * (band[:, 2].max() - mn[2])])
    o.data.transform(Matrix.Translation(Vector(-grip)))
    co = verts(o)
    mn, mx = co.min(0), co.max(0)
    top = co[co[:, 2] > mx[2] - 0.12 * (mx[2] - mn[2])]
    scope = [float(top[:, 0].mean()), float(top[:, 1].mean()), float(top[:, 2].min())] if len(top) else [0.0, 0.0, float(mx[2])]
    return {"grip_m": [round(float(x), 3) for x in grip], "scope_m": [round(x, 3) for x in scope]}


def scale_and_ground(o, it):
    if it["bake_yaw_deg"]:
        o.data.transform(Matrix.Rotation(np.radians(it["bake_yaw_deg"]), 4, "Z"))
    mn, mx = bounds(o)
    d = mx - mn
    ref = d[2] if it["size_rule"] == "z" else d.max()
    s = it["size_m"] / ref
    o.data.transform(Matrix.Scale(s, 4))
    mn, mx = bounds(o)
    o.data.transform(Matrix.Translation(Vector((-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]))))


def extra_bridge(o):
    """Altura das tábuas (m acima do pé) no meio e nas pontas; meia largura do tabuleiro."""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mn, mx = bounds(o)
    L = mx[0] - mn[0]
    z = {}
    for f in (-0.4, -0.2, 0.0, 0.2, 0.4):
        h = bvh.ray_cast(Vector((f * L, 0, mx[2] + 1)), Vector((0, 0, -1)))
        z[f"{f:+.1f}"] = round(h[0].z, 3) if h[0] else None
    half = 0.0
    z0 = z.get("+0.0") or 0.0
    for y in np.linspace(0, mx[1], 60):     # do meio para fora enquanto ainda acerta tábua (mesma altura)
        h = bvh.ray_cast(Vector((0.1 * L, y, mx[2] + 1)), Vector((0, 0, -1)))
        if not h[0] or abs(h[0].z - z0) > 0.25:
            break
        half = y
    return {"deck_z_m": z, "deck_half_width_m": round(float(half), 3)}


def extra_tent(o):
    """Altura livre da abertura da frente (+X) e profundidade interna."""
    bvh = BVHTree.FromObject(o, bpy.context.evaluated_depsgraph_get())
    mn, mx = bounds(o)
    door = 0.0
    for z in np.linspace(0.05, mx[2], 80):
        h = bvh.ray_cast(Vector((mx[0] + 1, 0, z)), Vector((-1, 0, 0)))
        if h[0] and h[0].x < 0:
            door = z
    back = bvh.ray_cast(Vector((0, 0, 0.5)), Vector((-1, 0, 0)))
    return {"door_clear_height_m": round(float(door), 2), "back_wall_x_m": round(back[0].x, 2) if back[0] else None}


def split_chest(o, it, sm_name):
    """Baú em 2 partes: base e tampa (corte a 62% da altura). Tampa com origem na dobradiça (+Y do Blender
    = -Y da Unreal = parte de trás no AJRLootChest)."""
    mn, mx = bounds(o)
    cut = mn[2] + 0.62 * (mx[2] - mn[2])
    parts = {}
    for part, keep_top in (("Base", False), ("Tampa", True)):
        c = o.copy()
        c.data = o.data.copy()
        bpy.context.scene.collection.objects.link(c)
        bm = bmesh.new()
        bm.from_mesh(c.data)
        geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
        r = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, cut), plane_no=(0, 0, 1),
                                   clear_inner=keep_top, clear_outer=not keep_top)
        edges = [e for e in r["geom_cut"] if isinstance(e, bmesh.types.BMEdge)]
        if edges:
            bmesh.ops.holes_fill(bm, edges=edges, sides=0)
        bm.to_mesh(c.data)
        bm.free()
        name = f"{sm_name}_{part}"
        c.name = name
        c.data.name = name
        if part == "Tampa":
            hinge = Vector((0, mx[1], cut))
            c.data.transform(Matrix.Translation(-hinge))
        else:
            hinge = None
        cm = collision(c, {"collision": "box", "name": it["name"]}, name)
        export_fbx([c] + cm, os.path.join(OUT, f"SM_{it['name']}_{part}.fbx"))
        parts[part] = {"hinge_m": [round(v, 3) for v in hinge] if hinge else None, "tris": tris(c)}
        for x in [c] + cm:
            bpy.data.objects.remove(x, do_unlink=True)
    return {"split_z_m": round(float(cut), 3), "parts": parts}


def mixamo_copy(o, it):
    """Cópia para subir no Mixamo: mesma escala real, olhando para -Y (frente do Blender), textura embutida."""
    c = o.copy()
    c.data = o.data.copy()
    bpy.context.scene.collection.objects.link(c)
    c.data.transform(Matrix.Rotation(np.radians(-90), 4, "Z"))
    c.name = it["name"]
    export_fbx([c], os.path.join(OUT, f"SM_{it['name']}_mixamo.fbx"), embed=True)
    bpy.data.objects.remove(c, do_unlink=True)


def process(it):
    o = load(it)
    sm_name = f"SM_{it['name']}"
    extra = {}
    if it["name"] == "ARM_Graveto":
        extra = weapon_stick(o, it)
    elif it["name"] == "ARM_Escopeta":
        extra = weapon_gun(o, it)
    elif it["name"] == "ARM_Sniper":
        extra = weapon_rifle(o, it)
    else:
        scale_and_ground(o, it)
    o.name = sm_name
    o.data.name = sm_name
    for m in o.data.materials:
        if m:
            m.name = f"M_{it['name']}"
    tex = save_texture(o, it)
    if it["name"] == "CON_Ponte":
        extra = extra_bridge(o)
    elif it["name"] == "CON_Barraca":
        extra = extra_tent(o)
    elif it["name"] == "PRP_Bau":
        extra = split_chest(o, it, sm_name)
    if it["category"] == "Personagens":
        mixamo_copy(o, it)
        extra["mixamo_fbx"] = f"SM_{it['name']}_mixamo.fbx"
    col = collision(o, it, sm_name)
    export_fbx([o] + col, os.path.join(OUT, f"SM_{it['name']}.fbx"))
    mn, mx = bounds(o)
    RESULT[it["name"]] = {"fbx": f"SM_{it['name']}.fbx", "texture": tex, "tris": tris(o),
                          "dims_m": [round(float(v), 3) for v in (mx - mn)],
                          "min_m": [round(float(v), 3) for v in mn], "max_m": [round(float(v), 3) for v in mx],
                          "ucx": [c.name for c in col], "category": it["category"], "collision": it["collision"],
                          **extra}
    print("OK", it["name"], RESULT[it["name"]]["dims_m"], RESULT[it["name"]]["tris"], flush=True)


for it in CAT["items"]:
    if it.get("source") == "noct_forge3d":
        continue  # [A-093] já sai pronto do tools/blender/polish_forge.py
    if ONLY and it["name"] not in ONLY:
        continue
    try:
        process(it)
    except Exception as exc:  # noqa: BLE001
        print("ERRO", it["name"], exc, flush=True)
        RESULT[it["name"]] = {"error": str(exc)}
    json.dump(RESULT, open(RESULT_PATH, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
