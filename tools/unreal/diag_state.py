"""Diagnóstico geral (andar sumindo + tecla de equipar). Roda no editor:
  py "E:/game/utrazin-game/tools/unreal/diag_state.py"
Relatório: reports/diag_state.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
AR = unreal.AssetRegistryHelpers.get_asset_registry()
R = {"errors": []}


def safe(fn):
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001
        return f"ERR {exc}"


def deps(path):
    o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
    return [str(d) for d in AR.get_dependencies(path, o) or []]


def refs(path):
    o = unreal.AssetRegistryDependencyOptions(include_soft_package_references=True, include_hard_package_references=True)
    return [str(d) for d in AR.get_referencers(path, o) or []]


try:
    for nn in ("01", "02"):
        bsp = f"/Game/Characters/Hero{nn}/Anims/BS_Idle_Walk_Run_H{nn}"
        bs = EAL.load_asset(bsp)
        o = {"skeleton": safe(lambda: bs.get_editor_property("skeleton").get_path_name()),
             "class": bs.get_class().get_name(), "deps": deps(bsp), "refs": refs(bsp)}
        o["samples"] = safe(lambda: [
            (s.get_editor_property("animation").get_path_name() if s.get_editor_property("animation") else None,
             s.get_editor_property("animation").get_editor_property("skeleton").get_path_name() if s.get_editor_property("animation") else None,
             str(s.get_editor_property("sample_value")))
            for s in bs.get_editor_property("sample_data")])
        o["api"] = [m for m in dir(bs) if "sample" in m.lower() or "skeleton" in m.lower()]
        abp = f"/Game/Characters/Hero{nn}/Anims/ABP_Unarmed_H{nn}"
        o["abp_deps"] = [d for d in deps(abp) if "BS_" in d or "Mannequins" in d]
        o["mesh_skeleton"] = safe(lambda: EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}").skeleton.get_path_name())
        bp = EAL.load_asset(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
        cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
        o["cdo"] = {p: safe(lambda p=p: str(cdo.get_editor_property(p).get_path_name() if cdo.get_editor_property(p) else None))
                    for p in ("toggle_weapon_action", "fire_action", "equip_anim", "aim_anim", "fire_anim", "unequip_anim")}
        o["cdo"]["weapon_mesh"] = safe(lambda: str(cdo.get_editor_property("weapon_mesh").get_editor_property("static_mesh")))
        o["cdo"]["anim_class"] = safe(lambda: str(cdo.get_editor_property("mesh").get_editor_property("anim_class")))
        R[f"H{nn}"] = o
    imc = EAL.load_asset("/Game/Core/Input/IMC_JR_Combat")
    R["imc"] = safe(lambda: [(str(m.get_editor_property("action").get_name() if m.get_editor_property("action") else None),
                              str(m.get_editor_property("key").get_editor_property("key_name")))
                             for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")])
    if isinstance(R["imc"], str):
        R["imc_api"] = [m for m in dir(imc) if "map" in m.lower()]
        R["imc2"] = safe(lambda: [(str(m.action.get_name()), str(m.key)) for m in imc.get_editor_property("mappings")])
    R["imc_refs"] = refs("/Game/Core/Input/IMC_JR_Combat")
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1500:]})
finally:
    with open(os.path.join(REPO, "reports", "diag_state.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log("[diag_state] ok")
