"""Correções do M1 em assets já criados (rodar no Editor depois de recompilar o C++):
  py "E:/game/utrazin-game/tools/unreal/setup_m1_fixes.py"

- BP_Vehicle_SUV: carroceria e pneus visuais do Offroad (malhas estáticas nos sockets VisWheel_*).
- DA_Character_Hero01: skins SKN-001 (Manny) e SKN-002 (Quinn) placeholder.
Relatório: reports/setup_m1_fixes.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
REPORT = {"done": [], "errors": []}


def step(name, fn):
    try:
        fn()
        REPORT["done"].append(name)
    except Exception as exc:  # noqa: BLE001
        REPORT["errors"].append({"step": name, "error": str(exc), "trace": traceback.format_exc()[-600:]})
        unreal.log_error(f"[setup_m1_fixes] {name}: {exc}")


def vehicle_visuals():
    bp = EAL.load_asset("/Game/Vehicles/SUV/BP_Vehicle_SUV")
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    body = EAL.load_asset("/Game/Vehicles/OffroadCar/SM_Offroad_Body")
    tire = EAL.load_asset("/Game/Vehicles/OffroadCar/SM_Offroad_Tire")
    cdo.get_editor_property("chassis_mesh").set_editor_property("static_mesh", body)
    for name in ("tire_fl", "tire_fr", "tire_bl", "tire_br"):
        comp = cdo.get_editor_property(name)
        comp.set_editor_property("static_mesh", tire)
        if name.endswith("r"):  # pneus do lado direito espelhados
            comp.set_editor_property("relative_rotation", unreal.Rotator(0, 0, 180))
    bp.modify()
    EAL.save_loaded_asset(bp, False)


def skins():
    da = EAL.load_asset("/Game/Data/DA_Character_Hero01")
    out = []
    for skin_id, mesh in (("SKN-001", "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"),
                          ("SKN-002", "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple")):
        s = unreal.JRSkinDefinition()
        s.set_editor_property("skin_id", skin_id)
        s.set_editor_property("mesh", EAL.load_asset(mesh))
        out.append(s)
    da.set_editor_property("skins", out)
    EAL.save_loaded_asset(da, False)


step("vehicle_visuals", vehicle_visuals)
step("skins", skins)
path = os.path.join(REPO, "reports", "setup_m1_fixes.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
unreal.log(f"[setup_m1_fixes] ok={len(REPORT['done'])} erros={len(REPORT['errors'])}")
