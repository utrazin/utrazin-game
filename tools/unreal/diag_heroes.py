"""Diagnóstico do retarget dos heróis. Roda no editor:
  py "E:/game/utrazin-game/tools/unreal/diag_heroes.py"
Relatório: reports/diag_heroes.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
R = {"rtg": {}, "anims": {}, "errors": []}


def api(o):
    return sorted(n for n in dir(o) if not n.startswith("_"))


def rtg_info(path):
    out = {}
    rtg = EAL.load_asset(path)
    rc = unreal.IKRetargeterController.get_controller(rtg)
    n = rc.get_num_retarget_ops()
    out["num_ops"] = n
    ops = []
    for i in range(n):
        o = {"name": str(rc.get_op_name(i)), "enabled": rc.get_retarget_op_enabled(i)}
        try:
            oc = rc.get_op_controller(i)
            o["class"] = oc.get_class().get_name() if oc else None
            if oc:
                o["api"] = [m for m in api(oc) if "chain" in m.lower() or "setting" in m.lower()]
                for m in ("get_chain_mapping", "get_all_chain_settings", "get_settings"):
                    if hasattr(oc, m):
                        try:
                            v = getattr(oc, m)()
                            o[m] = str(v)[:1500]
                        except Exception as exc:  # noqa: BLE001
                            o[m] = f"ERR {exc}"
        except Exception as exc:  # noqa: BLE001
            o["err"] = str(exc)
        ops.append(o)
    out["ops"] = ops
    for m in ("get_all_chain_settings",):
        try:
            out[m] = str(getattr(rc, m)())[:2000]
        except Exception as exc:  # noqa: BLE001
            out[m] = f"ERR {exc}"
    try:
        out["controller_api"] = api(rc)
    except Exception:  # noqa: BLE001
        pass
    return out


def anim_motion(path, bones=("thigh_l", "calf_l", "upperarm_l", "pelvis")):
    a = EAL.load_asset(path)
    if a is None:
        return "nao existe"
    res = {"length": a.get_play_length()}
    try:
        opts = unreal.AnimPoseEvaluationOptions()
        p0 = unreal.AnimPoseExtensions.get_anim_pose_at_time(a, 0.0, opts)
        p1 = unreal.AnimPoseExtensions.get_anim_pose_at_time(a, a.get_play_length() * 0.5, opts)
        for b in bones:
            t0 = unreal.AnimPoseExtensions.get_bone_pose(p0, b, unreal.AnimPoseSpaces.LOCAL)
            t1 = unreal.AnimPoseExtensions.get_bone_pose(p1, b, unreal.AnimPoseSpaces.LOCAL)
            r0, r1 = t0.rotation.rotator(), t1.rotation.rotator()
            res[b] = [round(r0.roll, 1), round(r0.pitch, 1), round(r0.yaw, 1), "->", round(r1.roll, 1), round(r1.pitch, 1), round(r1.yaw, 1)]
    except Exception as exc:  # noqa: BLE001
        res["err"] = str(exc)
    return res


try:
    for nn in ("01", "02"):
        try:
            R["rtg"][nn] = rtg_info(f"/Game/Characters/Rigs/RTG_Manny_Hero{nn}")
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({"rtg": nn, "e": str(exc), "t": traceback.format_exc()[-600:]})
    R["anims"]["manny_jog"] = anim_motion("/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd")
    R["anims"]["h01_jog"] = anim_motion("/Game/Characters/Hero01/Anims/MF_Unarmed_Jog_Fwd_H01")
    R["anims"]["h02_jog"] = anim_motion("/Game/Characters/Hero02/Anims/MF_Unarmed_Jog_Fwd_H02")
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"main": str(exc), "t": traceback.format_exc()[-600:]})
finally:
    with open(os.path.join(REPO, "reports", "diag_heroes.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2, default=str)
    unreal.log("[diag_heroes] ok")
