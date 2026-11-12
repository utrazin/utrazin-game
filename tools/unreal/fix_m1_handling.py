"""Ajustes do greybox M1 (rodar no Editor, com L01_Zombies aberto e o jogo parado):
  py "E:/game/utrazin-game/tools/unreal/fix_m1_handling.py"

1. SUV mais estável: copia controles de estabilidade do Offroad da Epic e abaixa o centro de massa.
2. SUV gera eventos de sobreposição (necessário para disparar checkpoints).
3. Checkpoints visíveis durante o jogo (caixa desenhada) e maiores; relatório com a distância até cada um.
Relatório: reports/fix_m1_handling.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
REPORT = {"done": [], "errors": [], "values": {}, "checkpoints": []}
COM_DROP_CM = 60.0


def step(name, fn):
    try:
        fn()
        REPORT["done"].append(name)
    except Exception as exc:  # noqa: BLE001
        REPORT["errors"].append({"step": name, "error": str(exc), "trace": traceback.format_exc()[-600:]})
        unreal.log_error(f"[fix_m1_handling] {name}: {exc}")


def vehicle():
    bp = EAL.load_asset("/Game/Vehicles/SUV/BP_Vehicle_SUV")
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    tpl = unreal.get_default_object(EAL.load_blueprint_class("/Game/VehicleTemplate/Blueprints/OffroadCar/BP_VehicleAdvOffroadCar"))
    src = tpl.get_editor_property("vehicle_movement_component")
    dst = cdo.get_editor_property("vehicle_movement_component")
    for prop in ("torque_control", "target_rotation_control", "stabilize_control", "inertia_tensor_scale",
                 "sleep_threshold", "sleep_slope_limit", "aerofoil_setups", "thruster_setups",
                 "wheel_traction_control_enabled", "requires_controller_for_inputs"):
        try:
            dst.set_editor_property(prop, src.get_editor_property(prop))
        except Exception as exc:  # noqa: BLE001
            REPORT["values"][f"skip.{prop}"] = str(exc)[:120]
    com = src.get_editor_property("center_of_mass_override")
    new_com = unreal.Vector(com.x, com.y, com.z - COM_DROP_CM)
    dst.set_editor_property("enable_center_of_mass_override", True)
    dst.set_editor_property("center_of_mass_override", new_com)
    REPORT["values"]["template_com"] = str(com)
    REPORT["values"]["new_com"] = str(new_com)
    REPORT["values"]["mass"] = dst.get_editor_property("mass")
    mesh = cdo.get_editor_property("mesh")
    mesh.set_editor_property("generate_overlap_events", True)
    bp.modify()
    EAL.save_loaded_asset(bp, False)


def checkpoints():
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors()
    start = None
    cps = [a for a in actors if isinstance(a, unreal.JRCheckpoint)]
    for cp in cps:
        if cp.get_editor_property("is_level_start"):
            start = cp.get_actor_location()
    for cp in cps:
        trig = cp.get_editor_property("trigger")
        trig.set_editor_property("hidden_in_game", False)
        trig.set_editor_property("line_thickness", 20.0)
        trig.set_editor_property("shape_color", unreal.Color(255, 220, 0, 255))
        if cp.get_editor_property("is_vehicle_transition"):
            trig.set_box_extent(unreal.Vector(600, 1500, 500))
        loc = cp.get_actor_location()
        dist = (loc - start).length() / 100.0 if start else None
        REPORT["checkpoints"].append({"label": cp.get_actor_label(), "location": str(loc), "dist_from_start_m": dist})
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)  # mapas World Partition: salva também os pacotes de atores externos


step("vehicle", vehicle)
step("checkpoints", checkpoints)
path = os.path.join(REPO, "reports", "fix_m1_handling.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
unreal.log(f"[fix_m1_handling] ok={REPORT['done']} erros={len(REPORT['errors'])}")
