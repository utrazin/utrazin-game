"""Prepara os 4 personagens rigados pelo usuário (assets/raw/characters_rig) para a Unreal e gera prévias (A-053).

Uso (Blender 5.2 em modo fundo, ou o módulo bpy):
  blender -b -P tools/blender/prepare_character_rigs.py -- <repo>
  (lê assets/raw/characters_rig/*, assets/raw/mixamo/zombie/Zombie_Walk.fbx e
   assets/raw/mixamo/npc/Rescued_InjuredWaveIdle.fbx; escreve em assets/work/characters_rig/)

Saída em assets/work/characters_rig/:
  CHR_<Nome>.fbx       metros, armadura "Armature" escala 1, sem animação, pés no chão, 4 pesos por vértice,
                       nomes mixamorig: mantidos, textura embutida (o tanque GLB vira FBX e é escalado para 2,60 m)
  textures/T_<Nome>_D.jpg  a mesma textura solta (reserva, caso a Unreal não extraia a embutida)
  characters.json      medidas, cápsula sugerida (cm), conferência de pesos e de deformação
  _preview_<Nome>.png  à esquerda pose de repouso (T/A) com textura; à direita a pose de andar de zumbi
                       (o sobrevivente usa o Rescued_InjuredWaveIdle), copiada osso a osso do FBX do Mixamo
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else sys.argv[1:]
REPO = os.path.abspath(ARGS[0] if ARGS else os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(REPO, "assets", "raw", "characters_rig")
OUT = os.path.join(REPO, "assets", "work", "characters_rig")
TEXDIR = os.path.join(OUT, "textures")
WALK = os.path.join(REPO, "assets", "raw", "mixamo", "zombie", "Zombie_Walk.fbx")
NPC_IDLE = os.path.join(REPO, "assets", "raw", "mixamo", "npc", "Rescued_InjuredWaveIdle.fbx")
# nome, arquivo do usuário, altura final em metros (None = mantém)
CHARS = [
    ("ZMB_Comum", "ZMB_Comum_rig.fbx", None),
    ("ZMB_Corredor", "ZMB_Corredor_rig.fbx", None),
    ("ZMB_Tanque", "ZMB_Tanque_rig.glb", 2.60),
    ("NPC_Sobrevivente", "NPC_Sobrevivente_rig.fbx", None),
]
ONLY = [a for a in ARGS[1:]]  # opcional: nomes para preparar só alguns
os.makedirs(TEXDIR, exist_ok=True)
REPORT = {}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def objs(t):
    return [o for o in bpy.context.scene.objects if o.type == t]


def world_bounds(o):
    pts = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in pts) for i in range(3)]), Vector([max(p[i] for p in pts) for i in range(3)])


def apply_all(o):
    bpy.ops.object.select_all(action="DESELECT")
    o.select_set(True)
    bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)


def load_char(path):
    if path.lower().endswith(".glb"):
        bpy.ops.import_scene.gltf(filepath=path)
    else:
        bpy.ops.import_scene.fbx(filepath=path)
    removed = []
    # ajudantes: Icosphere do Tripo, malhas sem pesos, empties de ponta de osso
    for o in list(bpy.context.scene.objects):
        if o.type == "MESH" and (o.name.lower().startswith("icosphere") or not o.vertex_groups):
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    arm = objs("ARMATURE")[0]
    meshes = [o for o in objs("MESH")]
    return arm, meshes, removed


def normalize(arm, meshes, name, target_h):
    """Sem animação, sem pais extras, escala/rotação aplicadas (metros), pés no chão, quadril no centro."""
    if arm.animation_data:
        arm.animation_data_clear()
    for a in list(bpy.data.actions):
        bpy.data.actions.remove(a)
    for pb in arm.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
        pb.rotation_euler = (0, 0, 0)
        pb.scale = (1, 1, 1)
    bpy.context.view_layer.update()
    if arm.parent:
        mw = arm.matrix_world.copy()
        arm.parent = None
        arm.matrix_world = mw
    for m in meshes:
        if m.parent != arm:
            mw = m.matrix_world.copy()
            m.parent = arm
            m.matrix_parent_inverse = arm.matrix_world.inverted()
            m.matrix_world = mw
    bpy.context.view_layer.update()
    lo, hi = bounds_all(meshes)
    info = REPORT.setdefault(name, {})
    info["height_in_file_m"] = round(hi.z - lo.z, 3)
    if target_h:
        f = target_h / (hi.z - lo.z)
        arm.scale = arm.scale * f
        arm.location = arm.location * f
        bpy.context.view_layer.update()
        info["scale_factor"] = round(f, 4)
    apply_all(arm)
    for m in meshes:
        apply_all(m)
    bpy.context.view_layer.update()
    lo, hi = bounds_all(meshes)
    hips = arm.data.bones["mixamorig:Hips"].head_local
    off = Vector((-hips.x, -hips.y, -lo.z))
    if off.length > 1e-4:
        arm.location += off
        bpy.context.view_layer.update()
        apply_all(arm)
        for m in meshes:
            apply_all(m)
    arm.name = "Armature"  # a Unreal não cria osso raiz extra com esse nome
    arm.data.name = "Armature"
    for i, m in enumerate(meshes):
        m.name = name if i == 0 else f"{name}_{i}"
        m.data.name = m.name
        for md in m.modifiers:
            if md.type == "ARMATURE":
                md.object = arm
    # pesos: no máximo 4 por vértice, normalizados
    unweighted, orphan = 0, []
    bone_names = {b.name for b in arm.data.bones}
    for m in meshes:
        bpy.ops.object.select_all(action="DESELECT")
        m.select_set(True)
        bpy.context.view_layer.objects.active = m
        bpy.ops.object.vertex_group_limit_total(group_select_mode="ALL", limit=4)
        bpy.ops.object.vertex_group_normalize_all(group_select_mode="ALL", lock_active=False)
        gidx = {g.index: g.name for g in m.vertex_groups}
        unweighted += sum(1 for v in m.data.vertices
                          if sum(g.weight for g in v.groups if gidx.get(g.group) in bone_names) < 1e-3)
        orphan += [g.name for g in m.vertex_groups if g.name not in bone_names]
    info["unweighted_verts"] = unweighted
    info["vertex_groups_without_bone"] = orphan


def bounds_all(meshes):
    los, his = zip(*(world_bounds(m) for m in meshes))
    return (Vector([min(v[i] for v in los) for i in range(3)]), Vector([max(v[i] for v in his) for i in range(3)]))


def fix_materials(meshes, name):
    """Material M_<Nome>, textura T_<Nome>_D (embutida no FBX e também salva solta em textures/)."""
    k = 0
    seen = {}
    for m in meshes:
        for slot in m.material_slots:
            mat = slot.material
            if not mat or mat in seen:
                continue
            seen[mat] = True
            mat.name = f"M_{name}" if k == 0 else f"M_{name}_{k}"
            k += 1
            if not mat.use_nodes:
                continue
            for n in mat.node_tree.nodes:
                if n.type != "TEX_IMAGE" or not n.image:
                    continue
                img = n.image
                is_base = any(l.to_socket.name == "Base Color" for l in n.outputs[0].links)
                tag = "D" if is_base else f"X{len(seen)}"
                img.name = f"T_{name}_{tag}"
                ext = ".png" if img.file_format == "PNG" else ".jpg"
                path = os.path.join(TEXDIR, f"T_{name}_{tag}{ext}")
                if img.packed_file:
                    with open(path, "wb") as fh:
                        fh.write(img.packed_file.data)
                    img.unpack(method="REMOVE")
                    img.filepath = path
                    img.reload()
                else:
                    img.filepath_raw = path
                    img.save(filepath=path)
    return [s.material.name for m in meshes for s in m.material_slots if s.material]


def measure(arm, meshes, name):
    lo, hi = bounds_all(meshes)
    co = [m.matrix_world @ v.co for m in meshes for v in m.data.vertices]
    b = arm.data.bones
    hz = b["mixamorig:Hips"].head_local.z
    sh = b["mixamorig:LeftArm"].head_local
    torso = [c for c in co if hz - 0.1 <= c.z <= sh.z and abs(c.x) <= abs(sh.x) + 0.02]
    tx = max(abs(c.x) for c in torso) if torso else 0.3
    ty = max(abs(c.y) for c in torso) if torso else 0.2
    a = b["mixamorig:LeftArm"].head_local
    h = b["mixamorig:LeftHand"].head_local
    d = h - a
    hh = round((hi.z - lo.z) * 100 / 2.0, 1)
    rad = round(min(max(max(tx, ty) * 100 * 0.9, 30.0), 75.0), 1)
    return {
        "height_m": round(hi.z - lo.z, 3), "width_m": round(hi.x - lo.x, 3), "depth_m": round(hi.y - lo.y, 3),
        "hips_z_m": round(hz, 3), "torso_half_width_m": round(tx, 3), "torso_half_depth_m": round(ty, 3),
        "bones": len(b), "bone_names": [x.name for x in b], "verts": len(co),
        "tris": sum(len(p.vertices) - 2 for m in meshes for p in m.data.polygons),
        "rest_arm_angle_below_horizontal_deg": round(math.degrees(math.atan2(-d.z, math.hypot(d.x, d.y))), 1),
        "faces_minus_y_blender": bool(b["mixamorig:LeftToeBase"].head_local.y < b["mixamorig:LeftFoot"].head_local.y),
        "capsule_cm": {"half_height": hh, "radius": rad},
    }


def prepare_one(name, src, target_h):
    reset()
    arm, meshes, removed = load_char(src)
    normalize(arm, meshes, name, target_h)
    for o in list(bpy.context.scene.objects):
        if o != arm and o not in meshes:
            removed.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    info = REPORT[name]
    info["source"] = os.path.relpath(src, REPO).replace("\\", "/")
    info["removed_helpers"] = removed
    info["materials"] = fix_materials(meshes, name)
    info.update(measure(arm, meshes, name))
    out = os.path.join(OUT, f"CHR_{name}.fbx")
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.fbx(
        filepath=out, use_selection=True, object_types={"ARMATURE", "MESH"},
        apply_unit_scale=True, apply_scale_options="FBX_SCALE_ALL", global_scale=1.0,
        axis_forward="-Z", axis_up="Y", use_mesh_modifiers=False, mesh_smooth_type="FACE",
        add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
        armature_nodetype="NULL", bake_anim=False, path_mode="COPY", embed_textures=True)
    info["fbx"] = os.path.relpath(out, REPO).replace("\\", "/")
    info["fbx_bytes"] = os.path.getsize(out)
    return out


def verify(name, out):
    """Reabre o FBX exportado: altura, escala da armadura, ossos e textura embutida."""
    reset()
    bpy.ops.import_scene.fbx(filepath=out)
    arm = objs("ARMATURE")[0]
    meshes = objs("MESH")
    bpy.context.view_layer.update()
    lo, hi = bounds_all(meshes)
    REPORT[name]["reimport"] = {
        "height_m": round(hi.z - lo.z, 3), "arm_name": arm.name, "arm_scale": [round(s, 4) for s in arm.scale],
        "bones": len(arm.data.bones),
        "images": [(i.name, list(i.size), i.packed_file is not None or os.path.exists(bpy.path.abspath(i.filepath)))
                   for i in bpy.data.images]}


# ------------------------------------------------------------------ prévia

def retarget_pose(src_arm, dst_arm, src_frame, x_offset):
    """Copia a pose do Mixamo para o personagem, alinhando a direção de cada osso (repouso T ou A)."""
    bpy.context.scene.frame_set(src_frame)
    bpy.context.view_layer.update()
    Ms = src_arm.matrix_world
    ratio = dst_arm.data.bones["mixamorig:Hips"].head_local.z / (Ms @ src_arm.data.bones["mixamorig:Hips"].head_local).z
    order = []

    def walk(bone):
        order.append(bone)
        for c in bone.children:
            walk(c)
    for bone in dst_arm.data.bones:
        if bone.parent is None:
            walk(bone)
    for bone in order:
        if bone.name not in src_arm.pose.bones:
            continue
        sp = src_arm.pose.bones[bone.name]
        sb = src_arm.data.bones[bone.name]
        s_rest = (Ms @ sb.matrix_local).to_quaternion()
        s_pose = (Ms @ sp.matrix).to_quaternion()
        s_dir = ((Ms @ sb.tail_local) - (Ms @ sb.head_local)).normalized()
        d_rest = dst_arm.matrix_world @ bone.matrix_local
        d_dir = ((dst_arm.matrix_world @ bone.tail_local) - (dst_arm.matrix_world @ bone.head_local)).normalized()
        rot = s_pose @ s_rest.inverted() @ d_dir.rotation_difference(s_dir) @ d_rest.to_quaternion()
        dp = dst_arm.pose.bones[bone.name]
        bpy.context.view_layer.update()
        if bone.parent is None:
            sh = Ms @ sp.head
            loc = Vector((sh.x * ratio + x_offset, sh.y * ratio, sh.z * ratio))
        else:
            loc = (dst_arm.matrix_world @ dp.matrix).to_translation()
        dp.matrix = dst_arm.matrix_world.inverted() @ Matrix.LocRotScale(loc, rot, Vector((1, 1, 1)))
        bpy.context.view_layer.update()


def stretch_check(meshes):
    """Compara o comprimento das arestas na pose com o repouso: arestas muito esticadas = pele quebrada."""
    dg = bpy.context.evaluated_depsgraph_get()
    worst, n_bad, n_all = 1.0, 0, 0
    for m in meshes:
        rest = [v.co.copy() for v in m.data.vertices]
        ev = m.evaluated_get(dg)
        me = ev.to_mesh()
        posed = [v.co.copy() for v in me.vertices]
        for e in m.data.edges:
            a, b = e.vertices
            l0 = (rest[a] - rest[b]).length
            if l0 < 1e-5:
                continue
            r = (posed[a] - posed[b]).length / l0
            n_all += 1
            r = max(r, 1.0 / max(r, 1e-6))
            worst = max(worst, r)
            if r > 2.0:
                n_bad += 1
        ev.to_mesh_clear()
    return {"worst_edge_ratio": round(worst, 2), "edges_over_2x": n_bad, "edges": n_all,
            "pct_over_2x": round(100.0 * n_bad / max(n_all, 1), 3)}


def import_anim(path, label):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.context.scene.objects if o not in before]
    arm = [o for o in new if o.type == "ARMATURE"][0]
    for o in new:
        if o != arm:
            bpy.data.objects.remove(o, do_unlink=True)
    arm.name = label
    arm.hide_render = True
    act = arm.animation_data.action
    return arm, act


def import_char(path):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.fbx(filepath=path)
    new = [o for o in bpy.context.scene.objects if o not in before]
    return [o for o in new if o.type == "ARMATURE"][0], [o for o in new if o.type == "MESH"]


def preview(name, fbx):
    reset()
    sc = bpy.context.scene
    is_npc = name.startswith("NPC")
    src, act = import_anim(NPC_IDLE if is_npc else WALK, "SRC")
    frame = int(act.frame_range[0] + (act.frame_range[1] - act.frame_range[0]) * (0.5 if is_npc else 0.3))
    h = REPORT[name]["height_m"]
    gap = max(1.2, h * 0.75)
    rest_arm, rest_meshes = import_char(fbx)
    pose_arm, pose_meshes = import_char(fbx)
    rest_arm.location.x = -gap / 2
    pose_arm.location.x = 0.0
    bpy.context.view_layer.update()
    retarget_pose(src, pose_arm, frame, gap / 2)
    REPORT[name]["deformation"] = stretch_check(pose_meshes)
    src.hide_set(True)
    bpy.ops.mesh.primitive_plane_add(size=40, location=(0, 0, 0))
    floor = bpy.context.active_object
    fm = bpy.data.materials.new("Floor")
    fm.use_nodes = True
    fm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.08, 0.1, 0.09, 1)
    floor.data.materials.append(fm)
    world = bpy.data.worlds.new("W")
    sc.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (0.35, 0.4, 0.45, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.7
    bpy.ops.object.light_add(type="SUN", location=(3, -6, 8))
    sun = bpy.context.active_object
    sun.data.energy = 3.5
    sun.rotation_euler = (math.radians(50), 0, math.radians(25))
    # câmera de frente (o personagem olha para -Y no Blender), um pouco em 3/4
    dist = h * 2.4 + gap * 1.2
    yaw = math.radians(18)
    cam_loc = Vector((math.sin(yaw) * dist, -math.cos(yaw) * dist, h * 0.62))
    bpy.ops.object.camera_add(location=cam_loc)
    cam = bpy.context.active_object
    target = Vector((0, 0, h * 0.5))
    cam.rotation_euler = (target - cam_loc).to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 40
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 40
    sc.cycles.use_denoising = False
    sc.render.resolution_x = 1400
    sc.render.resolution_y = 1000
    sc.view_settings.view_transform = "Standard"
    out = os.path.join(OUT, f"_preview_{name}.png")
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)
    REPORT[name]["preview"] = os.path.relpath(out, REPO).replace("\\", "/")


def main():
    old = {}
    jpath = os.path.join(OUT, "characters.json")
    if os.path.exists(jpath):
        with open(jpath, encoding="utf-8") as fh:
            old = json.load(fh)
    outs = {}
    for name, fname, h in CHARS:
        if ONLY and name not in ONLY:
            if name in old:
                REPORT[name] = old[name]
            continue
        outs[name] = prepare_one(name, os.path.join(RAW, fname), h)
    for name, out in outs.items():
        verify(name, out)
        preview(name, out)
    with open(jpath, "w", encoding="utf-8") as fh:
        json.dump(REPORT, fh, ensure_ascii=False, indent=1)
    print(json.dumps({k: {x: v[x] for x in ("height_m", "bones", "capsule_cm", "deformation") if x in v}
                      for k, v in REPORT.items()}, indent=1))


main()
