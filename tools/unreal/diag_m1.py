"""Diagnóstico: mostra os valores padrão (CDO) dos Blueprints do M1 e salva em reports/diag_m1.json.
RODA NO EDITOR:  py "E:/game/utrazin-game/tools/unreal/diag_m1.py"
"""
import json
import os

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHECKS = {
    "/Game/Core/BP_GameMode_L01": ["level_definition", "fallback_vehicle_class", "fallback_character_class", "player_controller_class", "default_pawn_class"],
    "/Game/Core/BP_PlayerController": ["vehicle_mapping_contexts", "on_foot_mapping_contexts"],
    "/Game/Characters/Hero01/BP_Character_Hero01": ["move_action", "fire_action"],
    "/Game/Vehicles/SUV/BP_Vehicle_SUV": ["throttle_action", "steer_action"],
    "/Game/Core/BP_GameInstance": ["characters", "levels"],
}
out = {}
for path, props in CHECKS.items():
    entry = {}
    try:
        bp = unreal.EditorAssetLibrary.load_asset(path)
        cls = unreal.BlueprintEditorLibrary.generated_class(bp)
        cdo = unreal.get_default_object(cls)
        entry["class"] = cls.get_path_name()
        entry["parent"] = str(unreal.BlueprintEditorLibrary.get_blueprint_parent_class(bp).get_name()) if hasattr(unreal.BlueprintEditorLibrary, "get_blueprint_parent_class") else "?"
        for p in props:
            try:
                v = cdo.get_editor_property(p)
                entry[p] = str(v.get_path_name()) if hasattr(v, "get_path_name") else str(v)
            except Exception as exc:  # noqa: BLE001
                entry[p] = f"ERRO: {exc}"
        if path.endswith("BP_Character_Hero01") or path.endswith("BP_Vehicle_SUV"):
            mesh = cdo.get_editor_property("mesh")
            entry["mesh_asset"] = str(mesh.get_skeletal_mesh_asset().get_path_name()) if mesh.get_skeletal_mesh_asset() else "None"
    except Exception as exc:  # noqa: BLE001
        entry["erro"] = str(exc)
    out[path] = entry
try:
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    gm = ws.get_editor_property("default_game_mode")
    out["world_game_mode"] = gm.get_path_name() if gm else "None"
except Exception as exc:  # noqa: BLE001
    out["world_game_mode"] = f"ERRO: {exc}"
path = os.path.join(REPO, "reports", "diag_m1.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(out, f, ensure_ascii=False, indent=2)
unreal.log(f"[diag_m1] salvo em {path}")
