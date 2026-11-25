"""[A-093] Polimento dos modelos do Noct Forge 3D para a Unreal (Blender 5.3 / bpy, roda na nuvem ou no PC).

Uso: python polish_forge.py <pasta_glb> <pasta_saida_tripo> [ids...]
  entrada: <id>/<id>.glb + texture.png (export do Forge; 16 unidades = 1 m, frente +Z)
  saída:   SM_<Nome>.fbx (metros, origem no centro de baixo, frente +X, igual aos modelos do Tripo)
           textures/T_<Nome>_D.jpg (cor do Forge x oclusão assada aqui)
           preview/<Nome>.png (render rápido para conferir)
           forge_processed.json (medidas, triângulos) -> juntar no tripo_processed.json
Polimento (nada facetado):
  - duro (madeira, metal): bevel 1,2 cm em 3 segmentos nas quinas > 30 graus + normais ponderadas
  - macio (colchão, travesseiro, cobertor, almofada): bevel 4 cm em 4 segmentos + subdivisão 1
  - orgânico (ninho): ruído no monte + subdivisão 2; ovos e bolhas subdivisão 2
  - oclusão ambiente assada (Cycles) e multiplicada na cor (sombra arroxeada, como a arte do usuário)
"""
import json
import math
import os
import sys

import bpy
import numpy as np

NAMES = {
    "arn_ninho": ("ARN_Ninho", "Arena", "none"), "int_balcao": ("INT_Balcao", "Interior", "box"),
    "int_prateleira": ("INT_Prateleira", "Interior", "box"), "int_bancada": ("INT_Bancada", "Interior", "box"),
    "int_suporte_armas": ("INT_SuporteArmas", "Interior", "box"), "int_cama": ("INT_Cama", "Interior", "box"),
    "int_mesa": ("INT_Mesa", "Interior", "box"), "int_cadeira": ("INT_Cadeira", "Interior", "box"),
    "int_armario": ("INT_Armario", "Interior", "box"), "int_caixotes": ("INT_Caixotes", "Interior", "box"),
    "int_luminaria": ("INT_Luminaria", "Interior", "none"),
    "veh_bike_quadro": ("VEH_BikeQuadro", "Veiculos", "box"), "veh_bike_roda": ("VEH_BikeRoda", "Veiculos", "none"),
}
# [A-097] tubos e anéis finos (bicicleta): só sombreado suave; o chanfro de 1,2 cm é maior que o tubo e estragaria
TUBE = ("pneu", "aro", "raio", "tubo", "mesa", "escora", "garfo", "avanco", "guidao", "manopla", "canote", "pedivela",
        "corrente", "faixa_luz", "paralama", "caixa_direcao", "eixo", "cubo", "coroa")
SOFT = ("colchao", "travesseiro", "cobertor", "almofada", "selim_")
CRYSTAL = ("cristal", "cupula")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
SRC, OUT = args[0], args[1]
ONLY = args[2:] or list(NAMES)
os.makedirs(os.path.join(OUT, "textures"), exist_ok=True)
os.makedirs(os.path.join(OUT, "preview"), exist_ok=True)
RESULT = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def weld(o):
    """O Forge exporta cada face com vértices próprios (sombreado chapado): solda antes de chanfrar/suavizar."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0004)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def polish_obj(o, asset):
    n = o.name.lower()
    bpy.context.view_layer.objects.active = o
    weld(o)
    for p in o.data.polygons:
        p.use_smooth = True
    if asset == "arn_ninho":
        if n.startswith("monte"):
            tex = bpy.data.textures.new("ruido", type="CLOUDS")
            tex.noise_scale = 0.35
            d = o.modifiers.new("ruido", "DISPLACE")
            d.texture = tex
            d.strength = 0.09
            d.texture_coords = "OBJECT"
        s = o.modifiers.new("sub", "SUBSURF")
        s.levels = s.render_levels = 2 if n.startswith("monte") else 1
        return
    if asset.startswith("veh_") and any(n.startswith(k) for k in TUBE):
        w = o.modifiers.new("wn", "WEIGHTED_NORMAL")
        w.keep_sharp = False
        return
    if any(n.startswith(k) for k in SOFT):
        b = o.modifiers.new("bevel", "BEVEL")
        b.width = 0.04
        b.segments = 4
        b.limit_method = "ANGLE"
        b.angle_limit = math.radians(30)
        s = o.modifiers.new("sub", "SUBSURF")
        s.levels = s.render_levels = 1
        return
    b = o.modifiers.new("bevel", "BEVEL")
    b.width = 0.006 if any(n.startswith(k) for k in CRYSTAL) else 0.012
    b.segments = 2 if any(n.startswith(k) for k in CRYSTAL) else 3
    b.limit_method = "ANGLE"
    b.angle_limit = math.radians(30)
    b.harden_normals = True
    w = o.modifiers.new("wn", "WEIGHTED_NORMAL")
    w.keep_sharp = True


def bake_ao(obj, base_img):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.render.bake.margin = 6
    W, H = base_img.size
    ao = bpy.data.images.new("ao", W, H, alpha=False, float_buffer=False)
    for mat in obj.data.materials:
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = ao
        nt.nodes.active = node
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.bake(type="AO", use_clear=True)
    a = np.array(ao.pixels[:], dtype=np.float32).reshape(H, W, 4)[..., 0]
    c = np.array(base_img.pixels[:], dtype=np.float32).reshape(H, W, 4)
    # sombra arroxeada (não preta) e só 75% da força
    ao_w = 1.0 - 0.75 * (1.0 - np.clip(a, 0, 1))
    tint = np.array([0.55, 0.45, 0.75], np.float32)
    shade = ao_w[..., None] + (1 - ao_w[..., None]) * tint * 0.35
    c[..., :3] = np.clip(c[..., :3] * shade, 0, 1)
    return c


def save_jpg(rgba, path, max_side=2048):
    H, W = rgba.shape[:2]
    img = bpy.data.images.new("out", W, H, alpha=False)
    img.pixels[:] = rgba.ravel()
    img.filepath_raw = path
    img.file_format = "JPEG"
    sc = bpy.context.scene
    sc.render.image_settings.quality = 92
    img.save()


def ucx(obj, name):
    mn = [min(v.co[i] for v in obj.data.vertices) for i in range(3)]
    mx = [max(v.co[i] for v in obj.data.vertices) for i in range(3)]
    bpy.ops.mesh.primitive_cube_add(size=1)
    c = bpy.context.active_object
    c.name = f"UCX_{name}_00"
    c.scale = [(mx[i] - mn[i]) for i in range(3)]
    c.location = [(mx[i] + mn[i]) / 2 for i in range(3)]
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    return c


def preview(obj, name):
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "TEXTURE"
    sc.display.shading.show_cavity = False
    sc.render.resolution_x = sc.render.resolution_y = 640
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("w") if sc.world is None else sc.world
    dims = obj.dimensions
    r = max(dims) * 1.9
    cam_data = bpy.data.cameras.new("cam")
    cam = bpy.data.objects.new("cam", cam_data)
    sc.collection.objects.link(cam)
    target = (0, 0, dims.z * 0.45)
    cam.location = (r * 0.85, -r * 0.75, dims.z * 0.45 + r * 0.55)  # frente +X: câmera de frente-direita
    d = [target[i] - cam.location[i] for i in range(3)]
    import mathutils
    cam.rotation_euler = mathutils.Vector(d).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.filepath = os.path.join(OUT, "preview", f"{name}.png")
    bpy.ops.render.render(write_still=True)


for asset in ONLY:
    name, cat, coll = NAMES[asset]
    reset()
    glb = os.path.join(SRC, asset, f"{asset}.glb")
    bpy.ops.import_scene.gltf(filepath=glb)
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    for o in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        bpy.ops.object.parent_clear(type="CLEAR_KEEP_TRANSFORM")
    for o in [o for o in bpy.context.scene.objects if o.type != "MESH"]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in meshes:
        polish_obj(o, asset)
        bpy.context.view_layer.objects.active = o
        for mod in list(o.modifiers):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    bpy.ops.object.select_all(action="SELECT")
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    obj = bpy.context.active_object
    obj.name = f"SM_{name}"
    tris0 = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    if tris0 > 40000:  # orçamento: arena com vários ninhos
        dec = obj.modifiers.new("dec", "DECIMATE")
        dec.ratio = 36000.0 / tris0
        bpy.ops.object.modifier_apply(modifier="dec")
    # frente do Forge (+Z do glTF = -Y do Blender) para +X; origem no centro de baixo
    from mathutils import Matrix
    obj.data.transform(Matrix.Rotation(math.radians(90), 4, "Z"))
    obj.data.update()
    vs = obj.data.vertices
    mn = [min(v.co[i] for v in vs) for i in range(3)]
    mx = [max(v.co[i] for v in vs) for i in range(3)]
    off = [-(mn[0] + mx[0]) / 2, -(mn[1] + mx[1]) / 2, -mn[2]]
    for v in vs:
        v.co.x += off[0]
        v.co.y += off[1]
        v.co.z += off[2]
    # textura base do glTF
    base = None
    for mat in obj.data.materials:
        for nd in mat.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image is not None:
                base = nd.image
                nd.interpolation = "Linear"
    if base is None:
        raise RuntimeError(f"{asset}: GLB sem textura")
    rgba = bake_ao(obj, base)
    for mat in obj.data.materials:  # volta a textura base como ativa (a prévia mostra a ativa)
        for nd in mat.node_tree.nodes:
            if nd.type == "TEX_IMAGE" and nd.image is base:
                mat.node_tree.nodes.active = nd
    tex_path = os.path.join(OUT, "textures", f"T_{name}_D.jpg")
    save_jpg(rgba, tex_path)
    # a prévia usa a textura com oclusão
    base.pixels[:] = rgba.ravel()
    preview(obj, name)
    export = [obj]
    if coll == "box":
        export.append(ucx(obj, f"SM_{name}"))
    bpy.ops.object.select_all(action="DESELECT")
    for o in export:
        o.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, f"SM_{name}.fbx"), use_selection=True, object_types={"MESH"},
                             apply_unit_scale=True, mesh_smooth_type="FACE", add_leaf_bones=False, colors_type="NONE",
                             path_mode="STRIP")
    dims = [round(d, 3) for d in obj.dimensions]
    tris = sum(len(p.vertices) - 2 for p in obj.data.polygons)
    RESULT[name] = {"fbx": f"SM_{name}.fbx", "texture": f"textures/T_{name}_D.jpg", "tris": tris, "dims_m": dims,
                    "min_m": [0, 0, 0], "max_m": dims, "ucx": 1 if coll == "box" else 0, "category": cat,
                    "collision": coll, "source": "noct_forge3d"}
    print(f"[polish] {name}: {dims} m, {tris} tris")

with open(os.path.join(OUT, "forge_processed.json"), "w", encoding="utf-8") as fh:
    json.dump(RESULT, fh, ensure_ascii=False, indent=1)
