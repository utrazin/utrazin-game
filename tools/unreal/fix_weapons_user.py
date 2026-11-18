"""Armas do usuário nos heróis: graveto (SM_ARM_Graveto) com pegada de espada e escopeta (SM_ARM_Escopeta).

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de import_user_assets.py:
  py "E:/game/utrazin-game/tools/unreal/fix_weapons_user.py"

O que faz (BP_Character_Hero01 e BP_Character_Hero02):
- MeleeMesh = SM_ARM_Graveto com pegada calculada da animação A_Melee_Slash_Out_HNN (30% do golpe):
  ponto de pegada = meio do punho (palma + falanges do dedo médio); lâmina sai pelo lado do indicador
  (eixo mínimo -> indicador), inclinada 20° para a frente do antebraço; o fio (+Z da malha) aponta para
  onde os nós dos dedos apontam. O graveto tem a origem na pegada, lâmina em +X (prep_tripo.py).
  Antes era a pegada da pistola girada 65° (o usuário viu que "não fica na mão").
- ShotgunStaticMesh = SM_ARM_Escopeta e ShotgunMeshScale = 1 (a malha já tem 0,9 m e a origem na empunhadura,
  cano em +X: usa o mesmo encaixe da pistola, que já foi calculado por setup_mixamo.weapon_grip).
- BP_Enemy_ZombieElite.GuaranteedDropMesh = SM_ARM_Escopeta (a escopeta que cai do elite).
Pode rodar de novo. Relatório: reports/fix_weapons_user.json
"""
import json
import math
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
STICK = "/Game/Environment/User/Armas/SM_ARM_Graveto"
SHOTGUN = "/Game/Environment/User/Armas/SM_ARM_Escopeta"
HEROES = ("01", "02")
KEY_FRACTION = 0.3          # momento do golpe usado para medir a mão (a pegada é rígida na mão)
BLADE_FORWARD_DEG = 20.0    # quanto a lâmina tomba para a frente do antebraço
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[fix_weapons_user] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[fix_weapons_user] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-700:]})
    unreal.log_error(f"[fix_weapons_user] {where}: {exc}")


def add(a, b):
    return unreal.Vector(a.x + b.x, a.y + b.y, a.z + b.z)


def sub(a, b):
    return unreal.Vector(a.x - b.x, a.y - b.y, a.z - b.z)


def mul(a, s):
    return unreal.Vector(a.x * s, a.y * s, a.z * s)


def dot(a, b):
    return a.x * b.x + a.y * b.y + a.z * b.z


def norm(a):
    return unreal.MathLibrary.normal(a)


def ortho(a, ref):
    """a sem a componente ao longo de ref (ref normalizado)."""
    return norm(sub(a, mul(ref, dot(a, ref))))


def stick_grip(nn):
    """Transform do graveto relativo ao osso hand_r (pegada de espada)."""
    seq_path = f"/Game/Characters/Hero{nn}/Anims/Wave1/A_Melee_Slash_Out_H{nn}"
    seq = EAL.load_asset(seq_path)
    if seq is None:
        raise RuntimeError(f"falta {seq_path} (rode setup_wave1.py)")
    try:
        t = float(seq.get_play_length()) * KEY_FRACTION
    except Exception:  # noqa: BLE001
        t = 0.0
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, t, unreal.AnimPoseEvaluationOptions())
    names = {str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)}
    W = unreal.AnimPoseSpaces.WORLD

    def T(b):
        return unreal.AnimPoseExtensions.get_bone_pose(pose, b, W)

    def P(b, fallback=None):
        return T(b).translation if b in names else fallback
    hand = T("hand_r")
    h = hand.translation
    la = P("lowerarm_r", sub(h, unreal.Vector(0, 0, 25)))
    f = norm(sub(h, la))                                   # antebraço -> mão
    idx, mid, pin = P("index_01_r"), P("middle_01_r", h), P("pinky_01_r")
    knuck = [x for x in (idx, mid, pin) if x is not None]
    kn = mul(knuck[0], 0)
    for x in knuck:
        kn = add(kn, x)
    kn = mul(kn, 1.0 / len(knuck))
    # ponto da pegada: entre a palma e as falanges do médio (o cabo passa dentro do punho)
    ring = [add(h, mul(sub(kn, h), 0.55))] + [x for x in (P("middle_02_r"), P("middle_03_r"), P("thumb_02_r")) if x]
    grip = mul(ring[0], 0)
    for x in ring:
        grip = add(grip, x)
    grip = mul(grip, 1.0 / len(ring))
    # eixo do cabo: do mínimo para o indicador (a lâmina sai do lado do polegar/indicador)
    if idx is not None and pin is not None:
        axis = ortho(sub(idx, pin), f)
    else:
        axis = ortho(sub(P("thumb_01_r", add(h, unreal.Vector(0, 0, 5))), h), f)
    a = math.radians(BLADE_FORWARD_DEG)
    blade = norm(add(mul(axis, math.cos(a)), mul(f, math.sin(a))))
    edge = ortho(sub(kn, h), blade)                       # fio para onde os nós dos dedos apontam
    rot = unreal.MathLibrary.make_rot_from_xz(blade, edge)
    stick = unreal.Transform(grip, rot, unreal.Vector(1, 1, 1))
    rel = unreal.MathLibrary.make_relative_transform(stick, hand)
    R["info"][f"stick_grip_H{nn}"] = {"time_s": round(t, 3), "loc": str(rel.translation),
                                      "rot": str(rel.rotation.rotator()), "blade_ws": str(blade),
                                      "bones": sorted(b for b in ("index_01_r", "middle_01_r", "pinky_01_r", "middle_02_r",
                                                                  "middle_03_r", "thumb_02_r", "lowerarm_r") if b in names)}
    return rel


def cdo_of(bp_path):
    bp = EAL.load_asset(bp_path)
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def compile_save(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)


def main():
    stick = EAL.load_asset(STICK) if EAL.does_asset_exist(STICK) else None
    gun = EAL.load_asset(SHOTGUN) if EAL.does_asset_exist(SHOTGUN) else None
    if stick is None or gun is None:
        raise RuntimeError("rode import_user_assets.py antes (faltam SM_ARM_Graveto / SM_ARM_Escopeta)")
    for nn in HEROES:
        path = f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}"
        try:
            bp, cdo = cdo_of(path)
            mm = cdo.get_editor_property("melee_mesh")
            mm.set_editor_property("static_mesh", stick)
            try:
                rel = stick_grip(nn)
                mm.set_editor_property("relative_location", rel.translation)
                mm.set_editor_property("relative_rotation", rel.rotation.rotator())
            except Exception as exc:  # noqa: BLE001
                err(f"Hero{nn}: pegada do graveto (ficou a anterior)", exc)
            mm.set_editor_property("relative_scale3d", unreal.Vector(1, 1, 1))
            cdo.set_editor_property("shotgun_static_mesh", gun)
            cdo.set_editor_property("shotgun_mesh_scale", 1.0)
            compile_save(bp)
            log(f"Hero{nn}: graveto e escopeta do usuário")
        except Exception as exc:  # noqa: BLE001
            err(f"Hero{nn}", exc)
    elite = "/Game/Enemies/BP_Enemy_ZombieElite"
    if EAL.does_asset_exist(elite):
        try:
            bp, cdo = cdo_of(elite)
            cdo.set_editor_property("guaranteed_drop_mesh", gun)
            compile_save(bp)
            log("elite: escopeta do usuário no drop")
        except Exception as exc:  # noqa: BLE001
            err("elite drop", exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    with open(os.path.join(REPO, "reports", "fix_weapons_user.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[fix_weapons_user] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
