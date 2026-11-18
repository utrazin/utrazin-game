"""Diagnóstico do retarget Mixamo. Roda no editor:
  py "E:/game/utrazin-game/tools/unreal/diag_mixamo.py"
Relatório: reports/diag_mixamo.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
R = {"rtg": {}, "anims": {}, "errors": []}
PAIRS = {
    "zombie_punch": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Punching", "/Game/Enemies/Anims/A_Zombie_Punching_Manny"),
    "zombie_walk": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Walk", "/Game/Enemies/Anims/A_Zombie_Walk_Manny"),
    "hit_h01": ("/Game/Characters/Mixamo/Anims/hero/A_HitReact_Pistol", "/Game/Characters/Hero01/Anims/Mixamo/A_HitReact_Pistol_H01"),
    "death_h01": ("/Game/Characters/Mixamo/Anims/hero/A_Death_Backwards", "/Game/Characters/Hero01/Anims/Mixamo/A_Death_Backwards_H01"),
    "shoot_h01": ("/Game/Characters/Mixamo/Anims/hero/A_Shoot_Pistol", "/Game/Characters/Hero01/Anims/Mixamo/A_Shoot_Pistol_H01"),
    "manny_ref_jog": (None, "/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd"),
}
KEYS = {"pelvis": ("Hips", "pelvis"), "head": ("Head", "head"), "foot_l": ("LeftFoot", "foot_l"),
        "foot_r": ("RightFoot", "foot_r"), "hand_l": ("LeftHand", "hand_l"), "hand_r": ("RightHand", "hand_r"),
        "knee_l": ("LeftLeg", "calf_l")}


def find_bone(names, key):
    mix, ue = KEYS[key]
    for n in names:
        s = str(n)
        if s == ue or s.endswith(":" + mix) or s == "mixamorig_" + mix or s == mix:
            return s
    return None


def sample(path, times=(0.0, 0.25, 0.5, 0.75)):
    a = EAL.load_asset(path)
    if a is None:
        return "nao existe"
    out = {"len": round(a.get_play_length(), 2), "skel": a.get_editor_property("skeleton").get_name()}
    opts = unreal.AnimPoseEvaluationOptions()
    L = a.get_play_length()
    for t in times:
        p = unreal.AnimPoseExtensions.get_anim_pose_at_time(a, t * L, opts)
        names = unreal.AnimPoseExtensions.get_bone_names(p)
        if "bones" not in out:
            out["bones"] = [str(n) for n in names][:12]
        fr = {}
        for k in KEYS:
            b = find_bone(names, k)
            if b:
                v = unreal.AnimPoseExtensions.get_bone_pose(p, b, unreal.AnimPoseSpaces.WORLD).translation
                fr[k] = [round(v.x), round(v.y), round(v.z)]
        out[f"t{t}"] = fr
    return out


def rtg(path):
    o = {}
    r = EAL.load_asset(path)
    rc = unreal.IKRetargeterController.get_controller(r)
    for side in ("SOURCE", "TARGET"):
        try:
            o[f"pose_{side}"] = str(rc.get_current_retarget_pose_name(getattr(unreal.RetargetSourceOrTarget, side)))
        except Exception as exc:  # noqa: BLE001
            o[f"pose_{side}"] = f"ERR {exc}"
    try:
        o["chains"] = str(rc.get_all_chain_settings())[:3000]
    except Exception as exc:  # noqa: BLE001
        o["chains"] = f"ERR {exc}"
    try:
        tgt = rc.get_ik_rig(unreal.RetargetSourceOrTarget.TARGET)
        tc = unreal.IKRigController.get_controller(tgt)
        m = {}
        for ch in tc.get_retarget_chains():
            n = ch.get_editor_property("chain_name")
            for call in (lambda: rc.get_source_chain(n), lambda: rc.get_source_chain(n, "FK Chains")):
                try:
                    m[str(n)] = str(call())
                    break
                except Exception as exc:  # noqa: BLE001
                    m[str(n)] = f"ERR {exc}"
        o["map"] = m
    except Exception as exc:  # noqa: BLE001
        o["map"] = f"ERR {exc}"
    return o


try:
    for n in ("RTG_Mixamo_Manny", "RTG_Mixamo_Hero01"):
        try:
            R["rtg"][n] = rtg(f"/Game/Characters/Rigs/{n}")
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({n: str(exc), "t": traceback.format_exc()[-800:]})
    for k, (s, t) in PAIRS.items():
        try:
            R["anims"][k] = {"src": sample(s) if s else None, "tgt": sample(t)}
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({k: str(exc), "t": traceback.format_exc()[-800:]})
finally:
    with open(os.path.join(REPO, "reports", "diag_mixamo.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log("[diag_mixamo] ok")
