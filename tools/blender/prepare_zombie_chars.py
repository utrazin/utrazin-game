"""Prepara os 4 personagens (Tripo 3D + rig Mixamo/Tripo) para a Unreal e gera a prévia (A-052).

Uso (Blender 5.2 em modo fundo ou bpy):
  blender -b -P tools/blender/prepare_zombie_chars.py -- <saida_dir> <Zombie_Walk.fbx> <Rescued_InjuredWaveIdle.fbx> \
      <SM_ZMB_Comum_mixamo.fbx> <SM_ZMB_Corredor_mixamo.fbx> <hulking_monster_3d_model.glb> <SM_NPC_Sobrevivente_mixamo.fbx>
Saída: CHR_*.fbx (metros, armadura "Armature" escala 1, sem osso folha, textura embutida), characters.json
(medidas, cápsula sugerida, conferência de pesos) e _preview.png (pose de andar de zumbi / parado do NPC).
O tanque (GLB do Tripo) perde a Icosphere e os empties de ponta de osso e é escalado para 2,60 m.
"""
import json
import math
import os
import sys
import tempfile

import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
OUT, WALK, NPC_IDLE, F_COMUM, F_CORREDOR, F_TANQUE, F_SOBREV = ARGS[:7]
CHARS = [
    ("CHR_ZMB_Comum", F_COMUM, None),
    ("CHR_ZMB_Corredor", F_CORREDOR, None),
    ("CHR_ZMB_Tanque", F_TANQUE, 2.60),       # altura final em metros
    ("CHR_NPC_Sobrevivente", F_SOBREV, None),
]
os.makedirs(OUT, exist_ok=True)
TEX = tempfile.mkdtemp(prefix="chr_tex_")  # texturas soltas temporárias (vão embutidas no FBX)
REPORT = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def objs(t):
    return [o for o in bpy.context.scene.objects if o.type == t]


def world_bounds(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def evaluated_bounds(o):
    dg = bpy.context.evaluated_depsgraph_get()
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    pts = [o.matrix_world @ v.co for v in me.vertices]
    ev.to_mesh_clear()
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def apply_all(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def clean_and_normalize(arm, mesh, name, target_h):
    """Tira animação, aplica escala/rotação (armadura em metros, escala 1), confere pesos."""
    if arm.animation_data:
        arm.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    # tira pais extras (glTF: Node_0/node_0)
    for o in (arm, mesh):
        if o.parent and o.parent != arm:
            mw = o.matrix_world.copy()
            o.parent = None
            o.matrix_world = mw
    if mesh.parent != arm:
        mw = mesh.matrix_world.copy()
        mesh.parent = arm
        mesh.matrix_parent_inverse = arm.matrix_world.inverted()
        mesh.matrix_world = mw
    bpy.context.view_layer.update()
    if target_h:
        lo, hi = world_bounds(mesh)
        f = target_h / (hi.z - lo.z)
        arm.scale = arm.scale * f
        arm.location = arm.location * f
        bpy.context.view_layer.update()
        REPORT.setdefault(name, {})["scale_factor"] = round(f, 4)
    apply_all(arm)
    apply_all(mesh)
    bpy.context.view_layer.update()
    # pés no chão, centrado em XY pelo quadril
    lo, hi = world_bounds(mesh)
    hips = arm.data.bones["mixamorig:Hips"].head_local
    off = Vector((-hips.x, -hips.y, -lo.z))
    if off.length > 1e-4:
        arm.location += off
        bpy.context.view_layer.update()
        apply_all(arm)
        apply_all(mesh)
    arm.name = "Armature"  # a Unreal não cria osso raiz extra com esse nome
    arm.data.name = "Armature"
    mesh.name = name
    mesh.data.name = name
    # pesos: max 4 influências, normalizados, sem vértice solto
    bpy.ops.object.select_all(action="DESELECT")
    mesh.select_set(True)
    bpy.context.view_layer.objects.active = mesh
    bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
    bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
    bone_names = {b.name for b in arm.data.bones}
    gidx = {g.index: g.name for g in mesh.vertex_groups}
    unweighted = sum(1 for v in mesh.data.vertices
                     if sum(g.weight for g in v.groups if gidx.get(g.group) in bone_names) < 1e-3)
    orphan_groups = [g.name for g in mesh.vertex_groups if g.name not in bone_names]
    for m in mesh.modifiers:
        if m.type == "ARMATURE":
            m.object = arm
    return unweighted, orphan_groups


def fix_material(mesh, name):
    short = name.replace("CHR_", "")
    for i, slot in enumerate(mesh.material_slots):
        mat = slot.material
        if not mat:
            continue
        mat.name = f"M_{short}" if i == 0 else f"M_{short}_{i}"
        for n in mat.node_tree.nodes:
            if n.type == "TEX_IMAGE" and n.image:
                img = n.image
                img.name = f"T_{short}_D"
                path = os.path.join(TEX, f"T_{short}_D.jpg" if img.file_format == "JPEG" else f"T_{short}_D.png")
                img.filepath_raw = path
                if not img.packed_file:
                    img.save(filepath=path)
                else:
                    with open(path, "wb") as fh:
                        fh.write(img.packed_file.data)
                    img.unpack(method="REMOVE")
                    img.filepath = path
                    img.reload()


def measure(arm, mesh, name):
    lo, hi = world_bounds(mesh)
    co = [v.co for v in mesh.data.vertices]
    hz = arm.data.bones["mixamorig:Hips"].head_local.z
    # tronco: vértices entre quadril e ombro, perto do eixo (sem braços)
    sh = arm.data.bones["mixamorig:LeftArm"].head_local
    torso = [c for c in co if hz - 0.1 <= c.z <= sh.z and abs(c.x) <= abs(sh.x) + 0.02]
    tx = max(abs(c.x) for c in torso) if torso else 0.3
    ty = max(abs(c.y) for c in torso) if torso else 0.2
    r = {
        "height_m": round(hi.z - lo.z, 3),
        "width_m": round(hi.x - lo.x, 3),
        "depth_m": round(hi.y - lo.y, 3),
        "hips_z_m": round(hz, 3),
        "torso_half_width_m": round(tx, 3),
        "torso_half_depth_m": round(ty, 3),
        "bones": len(arm.data.bones),
        "verts": len(mesh.data.vertices),
        "tris": sum(len(p.vertices) - 2 for p in mesh.data.polygons),
        "rest_arm_angle_below_horizontal_deg": None,
    }
    a = arm.data.bones["mixamorig:LeftArm"].head_local
    h = arm.data.bones["mixamorig:LeftHand"].head_local
    d = h - a
    r["rest_arm_angle_below_horizontal_deg"] = round(math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y))), 1)
    toe = arm.data.bones["mixamorig:LeftToeBase"].head_local
    foot = arm.data.bones["mixamorig:LeftFoot"].head_local
    r["faces_minus_y_blender"] = bool(toe.y < foot.y)
    # cápsula sugerida (cm): metade da altura, raio pelo tronco (limitado)
    hh = round((hi.z - lo.z) * 100 / 2.0, 1)
    rad = round(min(max(max(tx, ty) * 100 * 0.9, 30.0), 75.0), 1)
    r["capsule_cm"] = {"half_height": hh, "radius": rad}
    return r


def load_char(path):
    if path.endswith(".glb"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    # remove ajudantes: Icosphere, empties de ponta de osso, câmeras/luzes
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH" and (o.name.lower().startswith("icosphere") or not o.vertex_groups):
            bpy.data.objects.remove(o, do_unlink=True)
    arm = objs("ARMATURE")[0]
    mesh = [o for o in objs("MESH")][0]
    return arm, mesh


def prepare_one(name, path, target_h):
    reset()
    arm, mesh = load_char(path)
    removed = []
    unweighted, orphan = clean_and_normalize(arm, mesh, name, target_h)
    for o in list(bpy.context.scene.objects):
        if o not in (arm, mesh):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    fix_material(mesh, name)
    info = REPORT.setdefault(name, {})
    info.update(measure(arm, mesh, name))
    info["unweighted_verts"] = unweighted
    info["vertex_groups_without_bone"] = orphan
    info["removed_helpers"] = removed
    info["materials"] = [s.material.name for s in mesh.material_slots if s.material]
    out = os.path.join(OUT, name + ".fbx")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", global_scale=1.0,
        axis_forward="-Z", axis_up="Y", use_mesh_modifiers=False, mesh_smooth_type="FACE",
        add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
        armature_nodetype="NULL", bake_anim=False, path_mode="COPY", embed_textures=True)
    info["fbx_bytes"] = os.path.getsize(out)
    return out


def verify(name, out):
    """Reimporta o FBX exportado e confere altura, escala da armadura e textura embutida."""
    reset()
    bpy.ops.import_scene.fbx(filepath=out)
    arm = objs("ARMATURE")[0]
    mesh = objs("MESH")[0]
    bpy.context.view_layer.update()
    lo, hi = world_bounds(mesh)
    imgs = [(i.name, tuple(i.size), i.packed_file is not None or os.path.exists(bpy.path.abspath(i.filepath)))
            for i in bpy.data.images]
    REPORT[name]["reimport"] = {"height_m": round(hi.z - lo.z, 3), "arm_name": arm.name,
                                "arm_scale": [round(s, 4) for s in arm.scale], "bones": len(arm.data.bones),
                                "images": imgs}


# ------------------------------------------------------------------ prévia

def retarget_pose(src_arm, dst_arm, src_frame, x_offset):
    """Copia a pose (rotação relativa ao repouso, alinhando direção dos ossos) de src para dst."""
    bpy.context.scene.frame_set(src_frame)
    bpy.context.view_layer.update()
    Ms = src_arm.matrix_world
    s_hips_h = (Ms @ src_arm.data.bones["mixamorig:Hips"].head_local).z
    d_hips_h = dst_arm.data.bones["mixamorig:Hips"].head_local.z
    ratio = d_hips_h / s_hips_h
    order = []

    def walk(b):
        order.append(b)
        for c in b.children:
            walk(c)
    for b in dst_arm.data.bones:
        if b.parent is None:
            walk(b)
    for b in order:
        if b.name not in src_arm.pose.bones:
            continue
        sp = src_arm.pose.bones[b.name]
        sb = src_arm.data.bones[b.name]
        s_rest = (Ms @ sb.matrix_local).to_quaternion()
        s_pose = (Ms @ sp.matrix).to_quaternion()
        s_dir = ((Ms @ sb.tail_local) - (Ms @ sb.head_local)).normalized()
        d_rest_m = dst_arm.matrix_world @ b.matrix_local
        d_dir = ((dst_arm.matrix_world @ b.tail_local) - (dst_arm.matrix_world @ b.head_local)).normalized()
        align = d_dir.rotation_difference(s_dir)
        rot = s_pose @ s_rest.inverted() @ align @ d_rest_m.to_quaternion()
        dp = dst_arm.pose.bones[b.name]
        bpy.context.view_layer.update()
        cur = dst_arm.matrix_world @ dp.matrix
        if b.parent is None:
            sh = Ms @ sp.head
            loc = Vector((sh.x * ratio, sh.y * ratio, sh.z * ratio)) + Vector((x_offset, 0, 0))
        else:
            loc = cur.to_translation()
        mw = Matrix.LocRotScale(loc, rot, Vector((1, 1, 1)))
        dp.matrix = dst_arm.matrix_world.inverted() @ mw
        bpy.context.view_layer.update()


def preview(outs):
    reset()
    sc = bpy.context.scene
    bpy.ops.import_scene.fbx(filepath=WALK)
    walk_arm = objs("ARMATURE")[0]
    for o in list(sc.objects):
        if o != walk_arm:
            bpy.data.objects.remove(o, do_unlink=True)
    walk_arm.name = "SRC_Walk"
    bpy.ops.import_scene.fbx(filepath=NPC_IDLE)
    idle_arm = [o for o in objs("ARMATURE") if o != walk_arm][0]
    for o in list(sc.objects):
        if o not in (walk_arm, idle_arm):
            bpy.data.objects.remove(o, do_unlink=True)
    idle_arm.name = "SRC_Idle"
    walk_act = walk_arm.animation_data.action
    idle_act = idle_arm.animation_data.action
    xs = [-2.4, -0.8, 1.0, 3.0]
    chars = []
    for (name, _, _), x in zip(CHARS, xs):
        before = set(sc.objects)
        bpy.ops.import_scene.fbx(filepath=outs[name])
        new = [o for o in sc.objects if o not in before]
        arm = [o for o in new if o.type == "ARMATURE"][0]
        chars.append((name, arm, x))
    walk_mid = int(walk_act.frame_range[0] + (walk_act.frame_range[1] - walk_act.frame_range[0]) * 0.3)
    idle_mid = int(idle_act.frame_range[0] + (idle_act.frame_range[1] - idle_act.frame_range[0]) * 0.5)
    for name, arm, x in chars:
        src, fr = (idle_arm, idle_mid) if "NPC" in name else (walk_arm, walk_mid)
        retarget_pose(src, arm, fr, x)
    walk_arm.hide_render = True
    idle_arm.hide_render = True
    for o in (walk_arm, idle_arm):
        o.hide_set(True)
    # chão, luz, câmera
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, 0))
    floor = bpy.context.active_object
    fm = bpy.data.materials.new("Floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.1, 0.09, 1)
    floor.data.materials.append(fm)
    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.4, 0.45, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.6
    bpy.ops.object.light_add(type="SUN", location=(3, -6, 8))
    sun = bpy.context.active_object
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(25))
    bpy.ops.object.camera_add(location=(0.3, -6.6, 1.35), rotation=(math.radians(89), 0, 0))
    cam = bpy.context.active_object
    cam.data.lens = 30
    sc.camera = cam
    # rótulo de altura (linha de 1,8 m) para referência
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 48
    sc.cycles.use_denoising = False
    sc.render.resolution_x = 1600
    sc.render.resolution_y = 900
    sc.render.filepath = os.path.join(OUT, "_preview.png")
    sc.view_settings.view_transform = "Standard"
    bpy.ops.render.render(write_still=True)


def main():
    outs = {}
    for name, path, h in CHARS:
        outs[name] = prepare_one(name, path, h)
    for name, out in outs.items():
        verify(name, out)
    with open(os.path.join(OUT, "characters.json"), "w", encoding="utf-8") as fh:
        json.dump(REPORT, fh, ensure_ascii=False, indent=1)
    print(json.dumps(REPORT, indent=1))
    preview(outs)


main()
