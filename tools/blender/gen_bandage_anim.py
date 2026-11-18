"""Animação de cura "enrolar bandagem no braço" (item 10 do handoff 2026-11-17, A-069) feita no Blender.

O Mixamo não tem animação de bandagem; a cura usava "Drinking". Este script parte da pose parada da Drinking
(mesmo esqueleto mixamorig de 65 ossos, mesma escala) e monta, com IK temporário, a ação nova:
  quadros 1-12   braço esquerdo dobra na frente do peito (antebraço quase na horizontal), mão direita chega
  quadros 12-48  mão direita dá 3 voltas em torno do antebraço esquerdo (espiral do punho para o cotovelo),
                 dedos apontando para o braço; cabeça olhando para o braço
  quadros 48-56  puxão para apertar (mão direita afasta rápido e volta)
  quadros 56-66  braço esquerdo gira o punho e abre/fecha (testando o curativo)
  quadros 66-72  volta suave para a pose parada (a montage da Unreal ainda mistura 0,25 s)
30 fps, 72 quadros (2,4 s; a cura dura 2,2 s e cura em 1,4 s: no meio das voltas). Respiração leve no tronco.
Depois assa (bake) tudo em keyframes de osso puros (sem restrições) e exporta só o esqueleto + a ação.

Uso (Python 3.13 com o módulo bpy 5.3, ou blender -b --python ... --):
  python tools/blender/gen_bandage_anim.py [base.fbx] [saida_dir] [malha_preview.fbx]
Padrões: base = assets/raw/mixamo/hero/Heal_Bandage.fbx (a Drinking), saída = assets/work/anims,
malha da prévia = assets/raw/mixamo/XBot.fbx (só para os PNGs; não vai no FBX).
Grava: A_Hero_Bandage_Mixamo.fbx, previews/bandage_fNN.png, previews/bandage_contato.png e bandage_info.json.
"""
import json
import math
import os
import sys

import bpy
from mathutils import Matrix, Vector

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
if "--" in sys.argv:
    ARGS = sys.argv[sys.argv.index("--") + 1:]
BASE = ARGS[0] if len(ARGS) > 0 else os.path.join(REPO, "assets", "raw", "mixamo", "hero", "Heal_Bandage.fbx")
OUT = ARGS[1] if len(ARGS) > 1 else os.path.join(REPO, "assets", "work", "anims")
PREVIEW_MESH = ARGS[2] if len(ARGS) > 2 else os.path.join(REPO, "assets", "raw", "mixamo", "XBot.fbx")
FPS = 30
F0, F1 = 1, 72
P = "mixamorig:"
INFO = {"base": os.path.basename(BASE), "frames": [F0, F1], "fps": FPS, "checks": {}}


def smooth(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3.0 - 2.0 * t)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = F0, F1


def import_fbx(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False, ignore_leaf_bones=False)
    new = [o for o in bpy.data.objects if o not in before]
    arm = next(o for o in new if o.type == "ARMATURE")
    return arm, new


def world(arm, bone):
    return arm.matrix_world @ arm.pose.bones[P + bone].matrix


def empty(name, loc, size=0.03):
    e = bpy.data.objects.new(name, None)
    e.empty_display_size = size
    e.location = loc
    bpy.context.scene.collection.objects.link(e)
    return e


def key_loc(obj, frame, loc):
    obj.location = loc
    obj.keyframe_insert("location", frame=frame)


def key_infl(con, frame, value):
    con.influence = value
    con.keyframe_insert("influence", frame=frame)


def base_pose(arm):
    """Ação de base = quadro 1 da Drinking parado em todos os ossos + respiração leve no tronco."""
    src = arm.animation_data.action
    bpy.context.scene.frame_set(1)
    pose = {pb.name: (pb.location.copy(), pb.rotation_quaternion.copy()) for pb in arm.pose.bones}
    act = bpy.data.actions.new("BandageBase")
    arm.animation_data.action = act
    for pb in arm.pose.bones:
        loc, rot = pose[pb.name]
        pb.rotation_mode = "QUATERNION"
        pb.location, pb.rotation_quaternion = loc, rot
        pb.keyframe_insert("location", frame=F0)
        pb.keyframe_insert("rotation_quaternion", frame=F0)
    # respiração: Spine1/Spine2 inclinam ~1,2 grau num ciclo de 2,4 s
    for name, amp in (("Spine1", 0.012), ("Spine2", 0.016)):
        pb = arm.pose.bones[P + name]
        q0 = pose[pb.name][1]
        for f in range(F0, F1 + 1, 6):
            ang = amp * math.sin(2 * math.pi * (f - F0) / (F1 - F0))
            pb.rotation_quaternion = q0 @ Matrix.Rotation(ang - 0.06 * smooth((f - 4) / 10.0) * (1 - smooth((f - 64) / 8.0)), 4, "X").to_quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=f)
    INFO["base_action"] = src.name if src else None
    return pose


def forward_axis(arm, bone):
    """Eixo local do osso que aponta mais para a frente do personagem (-Y no mundo)."""
    m = (arm.matrix_world @ arm.data.bones[P + bone].matrix_local).to_3x3().normalized()
    best = None
    for name, v in (("TRACK_X", Vector((1, 0, 0))), ("TRACK_NEGATIVE_X", Vector((-1, 0, 0))),
                    ("TRACK_Z", Vector((0, 0, 1))), ("TRACK_NEGATIVE_Z", Vector((0, 0, -1)))):
        d = (m @ v).dot(Vector((0, -1, 0)))
        if best is None or d > best[0]:
            best = (d, name)
    return best[1]


def build(arm):
    sc = bpy.context.scene
    sc.frame_set(F0)
    bpy.context.view_layer.update()
    sh_l = world(arm, "LeftArm").translation
    sh_r = world(arm, "RightArm").translation
    chest = world(arm, "Spine2").translation
    up_len = (arm.data.bones[P + "LeftForeArm"].head_local - arm.data.bones[P + "LeftArm"].head_local).length * arm.matrix_world.to_scale()[0]
    fo_len = (arm.data.bones[P + "LeftHand"].head_local - arm.data.bones[P + "LeftForeArm"].head_local).length * arm.matrix_world.to_scale()[0]
    INFO["arm_lengths_m"] = [round(up_len, 3), round(fo_len, 3)]
    # ---- braço esquerdo: mão na frente do peito, um pouco à direita do centro; cotovelo para fora e para baixo
    # braço esquerdo dobrado: cotovelo para a frente e para baixo, antebraço atravessado na frente do peito,
    # punho a ~25 cm do tronco (a mão direita precisa de espaço para dar a volta sem entrar no corpo)
    elbow_l = sh_l + Vector((0.0, -0.75, -0.66)).normalized() * up_len
    l_hand = elbow_l + Vector((-0.70, -0.70, 0.12)).normalized() * fo_len
    l_pole = empty("PoleL", elbow_l + Vector((0.35, -0.15, -0.35)))
    t_l = empty("TargetL", l_hand)
    # ---- braço direito: pole para fora e para baixo
    r_pole = empty("PoleR", Vector((sh_r.x - 0.45, chest.y - 0.30, chest.z - 0.40)))
    t_r = empty("TargetR", l_hand)
    center = empty("Center", l_hand)
    look = empty("Look", l_hand)

    def add_ik(bone, target, pole, pole_angle):
        c = arm.pose.bones[P + bone].constraints.new("IK")
        c.target, c.pole_target, c.chain_count = target, pole, 2
        c.pole_angle = pole_angle
        c.use_tail = True
        return c

    ik_l = add_ik("LeftForeArm", t_l, l_pole, math.radians(0))
    ik_r = add_ik("RightForeArm", t_r, r_pole, math.radians(180))
    tr_r = arm.pose.bones[P + "RightHand"].constraints.new("DAMPED_TRACK")
    tr_r.target, tr_r.track_axis = center, "TRACK_Y"
    head_axis = forward_axis(arm, "Head")
    tr_h = arm.pose.bones[P + "Head"].constraints.new("DAMPED_TRACK")
    tr_h.target, tr_h.track_axis = look, head_axis
    tr_n = arm.pose.bones[P + "Neck"].constraints.new("DAMPED_TRACK")
    tr_n.target, tr_n.track_axis = look, forward_axis(arm, "Neck")
    INFO["head_track_axis"] = head_axis

    # influências: entra em 1-12, fica, sai em 66-72
    for c, peak in ((ik_l, 1.0), (ik_r, 1.0), (tr_r, 0.85), (tr_h, 0.55), (tr_n, 0.3)):
        key_infl(c, F0, 0.0)
        key_infl(c, 12, peak)
        key_infl(c, 66, peak)
        key_infl(c, F1, 0.0)
    # o braço esquerdo chega primeiro (a mão direita vem logo atrás)
    key_infl(ik_r, 6, 0.25)

    # posição do antebraço esquerdo já no lugar (avalia com a IK ligada)
    sc.frame_set(20)
    bpy.context.view_layer.update()
    elbow = world(arm, "LeftForeArm").translation.copy()
    wrist = world(arm, "LeftHand").translation.copy()
    axis = (wrist - elbow).normalized()
    u = axis.cross(Vector((0, 0, 1)))
    if u.length < 1e-3:
        u = axis.cross(Vector((0, 1, 0)))
    u.normalize()
    v = axis.cross(u).normalized()
    INFO["forearm"] = {"elbow": [round(x, 3) for x in elbow], "wrist": [round(x, 3) for x in wrist],
                       "angle_from_horizontal_deg": round(math.degrees(math.asin(abs(axis.z))), 1)}
    R_WRAP = 0.075           # punho direito a ~7,5 cm do eixo do antebraço (dedos encostam no braço)
    # ---- alvo da mão esquerda: fica; no fim gira o punho (testando)
    for f in (F0, 12, 56):
        key_loc(t_l, f, l_hand)
    for f, dz, dx in ((59, 0.03, -0.015), (62, -0.01, 0.02), (65, 0.02, -0.01)):
        key_loc(t_l, f, l_hand + Vector((dx, 0, dz)))
    key_loc(t_l, 68, l_hand)
    lh = arm.pose.bones[P + "LeftHand"]
    q_lh = lh.rotation_quaternion.copy()
    for f, ang in ((56, 0.0), (59, 0.45), (62, -0.35), (65, 0.25), (68, 0.0)):
        lh.rotation_quaternion = q_lh @ Matrix.Rotation(ang, 4, "Y").to_quaternion()
        lh.keyframe_insert("rotation_quaternion", frame=f)
    # ---- alvo da mão direita: chega, 3 voltas em espiral (do punho para o cotovelo), puxa, volta
    start_pt = wrist - axis * 0.03
    end_pt = wrist - axis * min(0.10, (wrist - elbow).length * 0.5)
    key_loc(t_r, F0, start_pt + u * 0.25 + v * 0.10)
    for f in range(12, 49):
        t = (f - 12) / 36.0
        th = 2 * math.pi * 3 * t
        c = start_pt.lerp(end_pt, t)
        p = c + (u * math.cos(th) + v * math.sin(th)) * R_WRAP
        key_loc(t_r, f, p)
        key_loc(center, f, c)
        key_loc(look, f, c)
    # puxão: afasta 15 cm na direção da última volta e para trás, e volta
    c_end = end_pt
    last = c_end + (u * math.cos(2 * math.pi * 3) + v * math.sin(2 * math.pi * 3)) * R_WRAP
    pull_dir = (last - c_end).normalized()
    key_loc(t_r, 51, last + pull_dir * 0.16 + Vector((0, 0.04, 0.02)))
    key_loc(t_r, 53, last + pull_dir * 0.18 + Vector((0, 0.05, 0.03)))
    key_loc(t_r, 56, c_end + (u * 0.6 + v * 0.8).normalized() * R_WRAP)
    key_loc(t_r, 66, c_end + (u * 0.6 + v * 0.8).normalized() * (R_WRAP + 0.03) + Vector((0, 0.02, -0.04)))
    key_loc(t_r, F1, c_end + Vector((-0.2, 0.05, -0.25)))
    for f in (F0, 11):
        key_loc(center, f, start_pt)
        key_loc(look, f, start_pt)
    for f in (56, F1):
        key_loc(center, f, c_end)
        key_loc(look, f, c_end + Vector((0, 0, -0.02)))
    # dedos da direita meio fechados (segurando a faixa) enquanto enrola
    for name in ("RightHandIndex1", "RightHandMiddle1", "RightHandRing1", "RightHandPinky1"):
        pb = arm.pose.bones.get(P + name)
        if not pb:
            continue
        q0 = pb.rotation_quaternion.copy()
        for f, ang in ((F0, 0.0), (12, 0.55), (48, 0.55), (52, 0.9), (56, 0.55), (66, 0.55), (F1, 0.0)):
            pb.rotation_quaternion = q0 @ Matrix.Rotation(ang, 4, "X").to_quaternion()
            pb.keyframe_insert("rotation_quaternion", frame=f)
    # linear nas voltas (velocidade constante), suave no resto
    for ob in (t_r, center, look):
        for fc in fcurves_of(ob):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR" if 12 <= kp.co.x <= 48 else "BEZIER"


def fcurves_of(ob):
    """F-curves da ação do objeto (Blender 4.4+ guarda em camadas/slots; 5.x não tem mais action.fcurves)."""
    act = ob.animation_data.action
    try:
        from bpy_extras import anim_utils
        cb = anim_utils.action_get_channelbag_for_slot(act, ob.animation_data.action_slot)
        return list(cb.fcurves) if cb else []
    except Exception:  # noqa: BLE001
        return list(getattr(act, "fcurves", []))


def bake(arm):
    bpy.context.view_layer.objects.active = arm
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    bpy.ops.object.mode_set(mode="POSE")
    for pb in arm.pose.bones:
        if hasattr(pb, "select"):          # Blender 5.x: seleção fica no PoseBone
            pb.select = True
        else:
            pb.bone.select = True
    bpy.ops.nla.bake(frame_start=F0, frame_end=F1, step=1, only_selected=False, visual_keying=True,
                     clear_constraints=True, clear_parents=False, use_current_action=False, bake_types={"POSE"})
    bpy.ops.object.mode_set(mode="OBJECT")
    act = arm.animation_data.action
    act.name = "Bandage"
    return act


REACH_ERR = [0.0]


def measure(arm):
    """Confere que a mão direita passa perto do antebraço esquerdo e que nada esticou."""
    sc = bpy.context.scene
    dmin, dmax = 9.0, 0.0
    for f in range(14, 48, 2):
        sc.frame_set(f)
        e = world(arm, "LeftForeArm").translation
        w = world(arm, "LeftHand").translation
        h = world(arm, "RightHand").translation
        ax = (w - e)
        t = max(0.0, min(1.0, (h - e).dot(ax) / ax.length_squared))
        d = (h - (e + ax * t)).length
        dmin, dmax = min(dmin, d), max(dmax, d)
    INFO["checks"]["right_wrist_to_left_forearm_m"] = [round(dmin, 3), round(dmax, 3)]
    INFO["checks"]["right_reach_error_max_m"] = round(REACH_ERR[0], 3)
    # mão direita e cotovelo esquerdo fora do tronco (cilindro de ~12 cm em volta da Spine2)
    clear = 9.0
    for f in range(F0, F1 + 1, 2):
        sc.frame_set(f)
        sp = world(arm, "Spine2").translation
        for b in ("RightHand", "LeftForeArm", "LeftHand"):
            q = world(arm, b).translation
            clear = min(clear, (Vector((q.x, q.y, 0)) - Vector((sp.x, sp.y, 0))).length)
    INFO["checks"]["min_dist_hands_elbow_to_torso_axis_m"] = round(clear, 3)
    sc.frame_set(F0)
    return dmin, dmax


def shift_to_zero(arm):
    """Os FBX do Mixamo começam no tempo 0 (o Blender importa como quadro 1): desloca as chaves -F0."""
    for fc in fcurves_of(arm):
        for kp in fc.keyframe_points:
            kp.co.x -= F0
            kp.handle_left.x -= F0
            kp.handle_right.x -= F0
    sc = bpy.context.scene
    sc.frame_start, sc.frame_end = 0, F1 - F0


def export(arm, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(o == arm)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"ARMATURE"},
                             add_leaf_bones=False, primary_bone_axis="Y", secondary_bone_axis="X",
                             armature_nodetype="NULL", use_armature_deform_only=False,
                             bake_anim=True, bake_anim_use_all_actions=False, bake_anim_use_nla_strips=False,
                             bake_anim_force_startend_keying=True, bake_anim_step=1.0, bake_anim_simplify_factor=0.0,
                             axis_forward="-Z", axis_up="Y", global_scale=1.0, apply_scale_options="FBX_SCALE_NONE",
                             use_space_transform=True, apply_unit_scale=True)


def roundtrip(path, ref):
    """Reimporta o FBX exportado e compara posições de ossos com a cena assada (cm)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=path, automatic_bone_orientation=False)
    arm2 = next(o for o in bpy.data.objects if o not in before and o.type == "ARMATURE")
    sc = bpy.context.scene
    worst = 0.0
    start2 = int(round(arm2.animation_data.action.frame_range[0])) if arm2.animation_data else 1
    for f in (1, 20, 36, 52, 62):
        sc.frame_set(f - F0 + start2)
        for b in ("Hips", "Head", "LeftHand", "RightHand", "LeftForeArm"):
            worst = max(worst, (world(arm2, b).translation - ref[(f, b)]).length)
    INFO["checks"]["roundtrip_max_err_cm"] = round(worst * 100, 2)
    INFO["checks"]["fbx_frames"] = list(arm2.animation_data.action.frame_range) if arm2.animation_data else None
    for o in [o for o in bpy.data.objects if o not in before]:
        bpy.data.objects.remove(o, do_unlink=True)
    return worst


RIG_PARTS = {  # osso: raio (m) do "boneco" da prévia
    "Hips": 0.11, "Spine": 0.10, "Spine1": 0.11, "Spine2": 0.12, "Neck": 0.04, "Head": 0.09,
    "LeftShoulder": 0.045, "RightShoulder": 0.045, "LeftArm": 0.045, "RightArm": 0.045,
    "LeftForeArm": 0.038, "RightForeArm": 0.038, "LeftHand": 0.032, "RightHand": 0.032,
    "LeftUpLeg": 0.065, "RightUpLeg": 0.065, "LeftLeg": 0.05, "RightLeg": 0.05, "LeftFoot": 0.04, "RightFoot": 0.04,
}


def mannequin(arm):
    """Boneco de cápsulas preso aos ossos do próprio esqueleto (a ação é do esqueleto da Drinking)."""
    arm.data.pose_position = "REST"
    bpy.context.view_layer.update()
    mats = {}
    for key, col in (("corpo", (0.55, 0.5, 0.78, 1)), ("esq", (0.25, 0.85, 0.9, 1)), ("dir", (1.0, 0.75, 0.25, 1))):
        m = bpy.data.materials.new(key)
        m.diffuse_color = col
        mats[key] = m
    for name, r in RIG_PARTS.items():
        b = arm.data.bones.get(P + name)
        if not b:
            continue
        head = arm.matrix_world @ b.head_local
        tail = arm.matrix_world @ b.tail_local
        if name == "Head":
            tail = head + (tail - head).normalized() * 0.2
        length = max(0.02, (tail - head).length)
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=r, depth=length,
                                            location=(head + tail) / 2)
        ob = bpy.context.active_object
        ob.rotation_euler = (tail - head).to_track_quat("Z", "Y").to_euler()
        if name in ("Head", "Hips", "Spine2"):
            bpy.ops.object.modifier_add(type="SUBSURF")
        side = "esq" if name.startswith("Left") and ("Arm" in name or "Hand" in name) else \
               ("dir" if name.startswith("Right") and ("Arm" in name or "Hand" in name) else "corpo")
        ob.data.materials.append(mats[side])
        bpy.context.view_layer.update()
        mw = ob.matrix_world.copy()
        ob.parent = arm
        ob.parent_type = "BONE"
        ob.parent_bone = P + name
        bpy.context.view_layer.update()
        ob.matrix_world = mw
    arm.data.pose_position = "POSE"
    bpy.context.view_layer.update()


def previews(action_path_fbx):
    """Prévia: reimporta o FBX novo (o que vai para a Unreal) e põe um boneco de cápsulas nos ossos."""
    prev_dir = os.path.join(OUT, "previews")
    os.makedirs(prev_dir, exist_ok=True)
    reset()
    anim, _ = import_fbx(action_path_fbx)
    mannequin(anim)
    sc = bpy.context.scene
    sc.render.engine = "BLENDER_WORKBENCH"
    sc.display.shading.light = "STUDIO"
    sc.display.shading.color_type = "MATERIAL"
    sc.display.shading.show_cavity = True
    sc.display.shading.show_shadows = False
    sc.render.resolution_x, sc.render.resolution_y = 560, 640
    world_ = bpy.data.worlds.new("W")
    sc.world = world_
    world_.color = (0.09, 0.11, 0.2)
    sc.display.shading.background_type = "WORLD"
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 45
    cam = bpy.data.objects.new("Cam", cam_data)
    sc.collection.objects.link(cam)
    cam.location = (0.75, -1.35, 1.45)
    tgt = Vector((0.02, -0.08, 1.05))
    cam.rotation_euler = (tgt - Vector(cam.location)).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    files = []
    for f, label in ((1, "inicio"), (14, "volta_1"), (26, "volta_2"), (40, "volta_3"), (52, "puxao"), (61, "testando")):
        sc.frame_set(f)
        p = os.path.join(prev_dir, f"bandage_f{f:02d}_{label}.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        files.append((p, f, label))
    INFO["preview_rig"] = "boneco de cápsulas no esqueleto exportado (laranja = mão direita, ciano = braço esquerdo)"
    return files


def contact_sheet(files):
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return None
    ims = [Image.open(p) for p, _, _ in files]
    w, h = ims[0].size
    sheet = Image.new("RGB", (w * 3, h * 2 + 40), (24, 30, 62))
    d = ImageDraw.Draw(sheet)
    for i, (im, (_, f, label)) in enumerate(zip(ims, files)):
        x, y = (i % 3) * w, (i // 3) * h + 40
        sheet.paste(im, (x, y))
        d.text((x + 12, y + 10), f"quadro {f}: {label.replace('_', ' ')}", fill=(250, 250, 255))
    d.text((12, 12), "Cura: enrolar bandagem (2,4 s, 30 fps). Laranja = mao direita, ciano = braco esquerdo", fill=(255, 214, 92))
    out = os.path.join(OUT, "previews", "bandage_contato.png")
    sheet.save(out)
    return out


def main():
    reset()
    arm, _ = import_fbx(BASE)
    arm.name = "Armature"
    arm.data.name = "Armature"
    INFO["armature_scale"] = round(arm.scale[0], 4)
    base_pose(arm)
    build(arm)
    tr = bpy.data.objects["TargetR"]
    for f in range(12, 49, 2):
        bpy.context.scene.frame_set(f)
        REACH_ERR[0] = max(REACH_ERR[0], (world(arm, "RightHand").translation - tr.matrix_world.translation).length)
    bake(arm)
    for o in [o for o in bpy.data.objects if o.type == "EMPTY"]:
        bpy.data.objects.remove(o, do_unlink=True)
    measure(arm)
    ref = {}
    for f in (1, 20, 36, 52, 62):
        bpy.context.scene.frame_set(f)
        for b in ("Hips", "Head", "LeftHand", "RightHand", "LeftForeArm"):
            ref[(f, b)] = world(arm, b).translation.copy()
    path = os.path.join(OUT, "A_Hero_Bandage_Mixamo.fbx")
    shift_to_zero(arm)
    export(arm, path)
    roundtrip(path, ref)
    files = previews(path)
    INFO["previews"] = [os.path.relpath(p, REPO).replace(os.sep, "/") if p.startswith(REPO) else p for p, _, _ in files]
    sheet = contact_sheet(files) if files else None
    INFO["contact_sheet"] = sheet
    with open(os.path.join(OUT, "bandage_info.json"), "w", encoding="utf-8") as fh:
        json.dump(INFO, fh, ensure_ascii=False, indent=1)
    print(json.dumps(INFO, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
