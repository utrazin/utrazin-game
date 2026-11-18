"""Encaixe das armas na mão dos heróis (pistola, escopeta e graveto). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), depois de fix_weapons_user.py (graveto e escopeta do usuário):
  py "E:/game/utrazin-game/tools/unreal/fix_weapon_grips.py"

Por que: a conferência no Blender (assets/work/weapons/_grip_check_*.png) mostrou que:
 - a pistola ficava presa no PULSO (osso hand_r), não na palma, e o cano apontava ~17 a 20 graus para a
   DIREITA e ~6 graus para BAIXO da mira (o cálculo antigo usava "peito -> mão" como frente);
 - a escopeta usa o mesmo encaixe da pistola, mas o cabo dela fica 3 a 4 cm mais para trás/baixo;
 - o graveto (fix_weapons_user.py) segurava pelo pomo (origem da malha), não pela parte enrolada do cabo.

O que faz, para BP_Character_Hero01 e BP_Character_Hero02, medindo a pose NA UNREAL (verdade do jogo):
 1. Pistola: pose de mira (AimAnim, t=0). Centro do punho = média de (palma + 55% até os nós dos dedos,
    falanges do médio, polegar). O CENTRO DO CABO da pistola vai para o centro do punho (GUN_DROP_CM mais
    fundo); cano = frente do personagem (horizontal), cima = +Z. WeaponMesh recebe esse encaixe.
 2. Escopeta: mesmo cálculo com o cabo da escopeta. Se o C++ tiver encaixe por arma (PistolGripTransform /
    ShotgunGripTransform), grava nos dois; se não, a escopeta usa o da pistola e o relatório mostra o
    encaixe certo dela (diferença de poucos cm) para o dono do C++.
 3. Graveto: pegada de espada no golpe A_Melee_Slash_Out (30%): lâmina sai do lado do indicador, inclinada
    BLADE_FORWARD_DEG para a frente do antebraço (30: no Blender, 20 encostava no corpo em alguns quadros);
    o meio do cabo enrolado (STICK_HANDLE_CM da origem) fica no centro do punho.
 4. Confere (só relatório) o ângulo do cano nas poses de mira, tiro, recarga e parado (MM_Idle) e a direção
    da lâmina nos golpes. Valores do Blender ficam em BLENDER_REF para comparar.
Relatório: reports/fix_weapon_grips.json. Desfazer: rode fix_weapons_user.py e setup_mixamo.py de novo.
"""
import json
import math
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
HEROES = ("01", "02")
PISTOL = "/Game/Weapons/SM_AlienPistol"
STICK = "/Game/Environment/User/Armas/SM_ARM_Graveto"
SHOTGUN = "/Game/Environment/User/Armas/SM_ARM_Escopeta"

# Centro do cabo de cada malha (cm, espaço da malha; medido no Blender: média dos vértices do cabo)
PISTOL_HANDLE_CM = (-2.19, 0.0, -4.12)
SHOTGUN_HANDLE_CM = (-5.89, 0.0, -5.21)
STICK_HANDLE_CM = 16.5        # meio da parte enrolada do graveto, a partir da origem, ao longo de +X
GUN_DROP_CM = 1.5             # cabo um pouco mais fundo no punho
BLADE_FORWARD_DEG = 30.0      # graveto: quanto a lâmina tomba para a frente do antebraço
STICK_KEY_FRACTION = 0.3      # momento do golpe usado para medir a mão

# Resultado da conferência no Blender (tools/blender/grip_check.py), só para comparar no relatório
BLENDER_REF = {
    "01": {"pistola": {"loc": [-9.01, 2.88, 4.85], "rot": [9.71, 170.29, -8.58]},
           "escopeta": {"loc": [-12.40, 3.62, 6.53], "rot": [9.71, 170.29, -8.58]},
           "graveto": {"loc": [1.44, 1.54, -12.37], "rot": [59.44, 172.06, 170.87]}},
    "02": {"pistola": {"loc": [-6.89, 2.70, 4.64], "rot": [10.51, 167.37, -8.73]},
           "escopeta": {"loc": [-10.21, 3.62, 6.37], "rot": [10.51, 167.37, -8.73]},
           "graveto": {"loc": [3.08, 0.50, -12.69], "rot": [60.30, 167.08, 167.06]}},
}
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}, "cpp_needed": []}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[fix_weapon_grips] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[fix_weapon_grips] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[fix_weapon_grips] {where}: {exc}")


def V(x, y, z):
    return unreal.Vector(float(x), float(y), float(z))


def add(a, b):
    return V(a.x + b.x, a.y + b.y, a.z + b.z)


def sub(a, b):
    return V(a.x - b.x, a.y - b.y, a.z - b.z)


def mul(a, s):
    return V(a.x * s, a.y * s, a.z * s)


def dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z


def norm(a):
    return unreal.MathLibrary.normal(a)


def ortho(a, ref):
    return norm(sub(a, mul(ref, dot(a, ref))))


def avg(pts):
    s = V(0, 0, 0)
    for p in pts:
        s = add(s, p)
    return mul(s, 1.0 / len(pts))


def r3(v):
    return [round(v.x, 2), round(v.y, 2), round(v.z, 2)]


def rr(r):
    return [round(r.pitch, 2), round(r.yaw, 2), round(r.roll, 2)]


class Pose:
    """Pose de uma animação num instante, em espaço do componente (o que o jogo usa)."""

    def __init__(self, seq, t):
        self.pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, t, unreal.AnimPoseEvaluationOptions())
        self.names = {str(n) for n in unreal.AnimPoseExtensions.get_bone_names(self.pose)}

    def T(self, b):
        return unreal.AnimPoseExtensions.get_bone_pose(self.pose, b, unreal.AnimPoseSpaces.WORLD)

    def P(self, b, fallback=None):
        return self.T(b).translation if b in self.names else fallback


def ref_pose(mesh):
    p = Pose.__new__(Pose)
    p.pose = unreal.AnimPoseExtensions.get_reference_pose(mesh.skeleton)
    p.names = {str(n) for n in unreal.AnimPoseExtensions.get_bone_names(p.pose)}
    return p


def forward_of(mesh):
    """Frente do personagem no espaço do componente: média calcanhar -> ponta do pé na pose de referência."""
    p = ref_pose(mesh)
    d = V(0, 0, 0)
    for s in ("l", "r"):
        a, b = p.P(f"foot_{s}"), p.P(f"ball_{s}")
        if a is not None and b is not None:
            d = add(d, sub(b, a))
    d = V(d.x, d.y, 0)
    if d.length() < 1e-3:
        warn("sem foot/ball no esqueleto: frente = +Y")
        return V(0, 1, 0)
    f = norm(d)
    # o herói olha para +Y no componente; se o pé der outra coisa, avisa (mas usa o pé)
    if abs(f.y) < 0.8:
        warn(f"frente medida pelos pés = {r3(f)} (esperado ~ +Y)")
    return f


def fist(p):
    h = p.P("hand_r")
    if h is None:
        raise RuntimeError("pose sem hand_r")
    kn_list = [p.P(f"{f}_01_r") for f in ("index", "middle", "ring", "pinky")]
    kn_list = [x for x in kn_list if x is not None]
    if not kn_list:
        raise RuntimeError(f"pose sem ossos dos dedos (achei {sorted(n for n in p.names if n.endswith('_r'))[:20]})")
    kn = avg(kn_list)
    ring = [add(h, mul(sub(kn, h), 0.55))] + [x for x in (p.P("middle_02_r"), p.P("middle_03_r"), p.P("thumb_02_r")) if x]
    return avg(ring), h, kn


def gun_grip(p, fwd, handle_cm):
    """Encaixe relativo a hand_r: cabo no centro do punho, cano na frente do personagem."""
    c, _, _ = fist(p)
    up = V(0, 0, 1)
    rot = unreal.MathLibrary.make_rot_from_xz(fwd, up)
    hc = rot.quaternion().rotate_vector(V(*handle_cm))
    origin = sub(sub(c, hc), mul(up, GUN_DROP_CM))
    gun = unreal.Transform(origin, rot, V(1, 1, 1))
    return unreal.MathLibrary.make_relative_transform(gun, p.T("hand_r"))


def stick_grip(p):
    c, h, kn = fist(p)
    la = p.P("lowerarm_r", sub(h, V(0, 0, 25)))
    f = norm(sub(h, la))
    idx, pin = p.P("index_01_r"), p.P("pinky_01_r")
    if idx is not None and pin is not None:
        axis = ortho(sub(idx, pin), f)
    else:
        axis = ortho(sub(p.P("thumb_01_r", add(h, V(0, 0, 5))), h), f)
    a = math.radians(BLADE_FORWARD_DEG)
    blade = norm(add(mul(axis, math.cos(a)), mul(f, math.sin(a))))
    edge = ortho(sub(kn, h), blade)
    rot = unreal.MathLibrary.make_rot_from_xz(blade, edge)
    origin = sub(c, mul(blade, STICK_HANDLE_CM))
    st = unreal.Transform(origin, rot, V(1, 1, 1))
    return unreal.MathLibrary.make_relative_transform(st, p.T("hand_r"))


def weapon_axis_in_pose(p, rel):
    """Eixo +X (cano/lâmina) da arma presa com rel em hand_r, no espaço do componente."""
    w = unreal.MathLibrary.compose_transforms(rel, p.T("hand_r"))
    return w.rotation.rotate_vector(V(1, 0, 0)), w.translation


def check(seq, rel, fwd, label, fracs):
    out = []
    if seq is None:
        return out
    length = float(seq.get_play_length())
    for fr in fracs:
        p = Pose(seq, length * fr)
        x, _ = weapon_axis_in_pose(p, rel)
        ang = math.degrees(math.acos(max(-1.0, min(1.0, dot(norm(x), fwd)))))
        pitch = math.degrees(math.asin(max(-1.0, min(1.0, norm(x).z))))
        out.append({"pose": label, "t": round(length * fr, 2), "graus_da_frente": round(ang, 1), "inclinacao": round(pitch, 1)})
    return out


def find_anim(nn, names):
    for n in names:
        for base in (f"/Game/Characters/Hero{nn}/Anims/Mixamo", f"/Game/Characters/Hero{nn}/Anims/Wave1",
                     f"/Game/Characters/Hero{nn}/Anims"):
            p = f"{base}/{n}_H{nn}"
            if EAL.does_asset_exist(p):
                return EAL.load_asset(p)
    return None


def try_set(obj, prop, value, where):
    try:
        obj.set_editor_property(prop, value)
        return True
    except Exception:  # noqa: BLE001
        R["cpp_needed"].append(f"{where}.{prop}")
        return False


def hero(nn):
    info = R["info"].setdefault(f"Hero{nn}", {"blender_ref": BLENDER_REF.get(nn)})
    bp = EAL.load_asset(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
    fwd = forward_of(mesh)
    info["frente_componente"] = r3(fwd)
    wm = cdo.get_editor_property("weapon_mesh")
    mm = cdo.get_editor_property("melee_mesh")
    info["antes"] = {"weapon_mesh": {"loc": r3(wm.get_editor_property("relative_location")),
                                     "rot": rr(wm.get_editor_property("relative_rotation"))},
                     "melee_mesh": {"loc": r3(mm.get_editor_property("relative_location")),
                                    "rot": rr(mm.get_editor_property("relative_rotation")),
                                    "mesh": str(mm.get_editor_property("static_mesh").get_name() if mm.get_editor_property("static_mesh") else None)}}

    # ---- pistola e escopeta (pose de mira)
    aim = cdo.get_editor_property("aim_anim") or find_anim(nn, ("A_Pistol_idle",))
    if aim is None:
        raise RuntimeError("sem AimAnim (rode setup_mixamo.py)")
    p_aim = Pose(aim, 0.0)
    info["ossos_mao"] = sorted(n for n in p_aim.names if n.endswith("_r") and any(k in n for k in ("hand", "index", "middle", "ring", "pinky", "thumb")))
    pistol = gun_grip(p_aim, fwd, PISTOL_HANDLE_CM)
    # escopeta: se o C++ já tiver mira própria (rifle do template, setup_anims_wave2.py), mede nela
    sg_aim = None
    try:
        sg_aim = cdo.get_editor_property("shotgun_aim_anim")
    except Exception:  # noqa: BLE001
        pass
    shotgun = gun_grip(Pose(sg_aim, 0.0) if sg_aim else p_aim, fwd, SHOTGUN_HANDLE_CM)
    info["escopeta_medida_em"] = sg_aim.get_name() if sg_aim else aim.get_name()
    info["pistola"] = {"loc": r3(pistol.translation), "rot": rr(pistol.rotation.rotator())}
    info["escopeta"] = {"loc": r3(shotgun.translation), "rot": rr(shotgun.rotation.rotator())}
    if EAL.does_asset_exist(PISTOL) and wm.get_editor_property("static_mesh") is None:
        wm.set_editor_property("static_mesh", EAL.load_asset(PISTOL))
    wm.set_editor_property("relative_location", pistol.translation)
    wm.set_editor_property("relative_rotation", pistol.rotation.rotator())
    # encaixe por arma, se o C++ já tiver (senão vai para cpp_needed no relatório)
    per_weapon = try_set(cdo, "pistol_grip_transform", pistol, f"Hero{nn}")
    per_weapon &= try_set(cdo, "shotgun_grip_transform", shotgun, f"Hero{nn}")
    info["encaixe_por_arma_no_cpp"] = per_weapon
    if not per_weapon:
        d = sub(shotgun.translation, pistol.translation)
        warn(f"Hero{nn}: sem encaixe por arma no C++; a escopeta usa o da pistola (cabo fica {d.length():.1f} cm fora do punho)")

    # ---- graveto
    stick_ok = False
    if EAL.does_asset_exist(STICK):
        slash = find_anim(nn, ("A_Melee_Slash_Out",))
        if slash is None:
            warn(f"Hero{nn}: falta A_Melee_Slash_Out (rode setup_wave1.py): graveto sem ajuste")
        else:
            st = stick_grip(Pose(slash, float(slash.get_play_length()) * STICK_KEY_FRACTION))
            mm.set_editor_property("static_mesh", EAL.load_asset(STICK))
            mm.set_editor_property("relative_location", st.translation)
            mm.set_editor_property("relative_rotation", st.rotation.rotator())
            mm.set_editor_property("relative_scale3d", V(1, 1, 1))
            try_set(cdo, "melee_grip_transform", st, f"Hero{nn}")
            info["graveto"] = {"loc": r3(st.translation), "rot": rr(st.rotation.rotator())}
            stick_ok = True
    else:
        warn(f"falta {STICK} (rode import_user_assets.py e fix_weapons_user.py): graveto sem ajuste")

    # ---- conferência (só relatório)
    conf = []
    conf += check(aim, pistol, fwd, "mira", (0.0, 0.5))
    conf += check(cdo.get_editor_property("fire_anim"), pistol, fwd, "tiro", (0.1, 0.25, 0.5))
    conf += check(cdo.get_editor_property("reload_anim"), pistol, fwd, "recarga", (0.25, 0.5, 0.75))
    conf += check(find_anim(nn, ("MM_Idle",)), pistol, fwd, "parado (MM_Idle, arma abaixada)", (0.0, 0.5))
    if stick_ok:
        for n in ("A_Melee_Slash_Out", "A_Melee_Slash_In"):
            conf += check(find_anim(nn, (n,)), st, fwd, f"graveto {n}", (0.2, 0.4, 0.6, 0.8))
    info["conferencia"] = conf
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)
    log(f"Hero{nn}: pistola {info['pistola']} | graveto {info.get('graveto')}")


def main():
    for nn in HEROES:
        try:
            hero(nn)
        except Exception as exc:  # noqa: BLE001
            err(f"Hero{nn}", exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    with open(os.path.join(REPO, "reports", "fix_weapon_grips.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[fix_weapon_grips] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
