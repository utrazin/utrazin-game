"""Cria os assets do greybox M1 a partir das classes C++ e do conteúdo placeholder da Epic.

RODA DENTRO DO EDITOR UNREAL (caixa Cmd, embaixo):
  py "E:/game/utrazin-game/tools/unreal/setup_m1_assets.py"

Pré-requisitos: projeto compilado; pacotes "Third Person" e "Vehicle" adicionados.
Idempotente: assets já existentes são mantidos (não sobrescreve). Relatório em reports/setup_m1_assets.json.

Cria:
  /Game/Core/Input:   IA_Sprint, IA_Aim, IA_Fire, IA_Reload, IA_Interact, IMC_JR_Combat
  /Game/Data:         DA_Weapon_AlienPistol, DA_Enemy_Zombie{Melee,Archer,Gunner}, DA_Character_Hero01, DA_Level_L01_Zombies
  /Game/Core:         BP_GameInstance, BP_PlayerController, BP_GameMode_L01
  /Game/Characters/Hero01:  BP_Character_Hero01   (placeholder: Manny)
  /Game/Vehicles/SUV:       BP_Vehicle_SUV        (placeholder: Offroad da Epic, física copiada)
  /Game/Enemies:            BP_Enemy_Zombie{Melee,Archer,Gunner} (placeholder: Quinn/Manny)
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {"time": datetime.now().isoformat(), "created": [], "skipped": [], "errors": [], "warnings": []}

# Conteúdo placeholder (pacotes Third Person e Vehicle)
TPL = {
    "imc_default": "/Game/Input/IMC_Default",
    "imc_mouselook": "/Game/Input/IMC_MouseLook",
    "ia_move": "/Game/Input/Actions/IA_Move",
    "ia_look": "/Game/Input/Actions/IA_Look",
    "ia_mouselook": "/Game/Input/Actions/IA_MouseLook",
    "ia_jump": "/Game/Input/Actions/IA_Jump",
    "imc_vehicle": "/Game/VehicleTemplate/Input/IMC_Vehicle_Default",
    "imc_vehicle_mouse": "/Game/VehicleTemplate/Input/IMC_Vehicle_MouseLook",
    "ia_throttle": "/Game/VehicleTemplate/Input/Actions/IA_Throttle",
    "ia_brake": "/Game/VehicleTemplate/Input/Actions/IA_Brake",
    "ia_steering": "/Game/VehicleTemplate/Input/Actions/IA_Steering",
    "ia_handbrake": "/Game/VehicleTemplate/Input/Actions/IA_Handbrake",
    "ia_lookaround": "/Game/VehicleTemplate/Input/Actions/IA_LookAround",
    "manny": "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple",
    "quinn": "/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple",
    "abp_unarmed": "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed",
    "offroad_mesh": "/Game/Vehicles/OffroadCar/SKM_Offroad",
    "offroad_abp": "/Game/Vehicles/OffroadCar/Offroad_AnimBP",
    "offroad_bp": "/Game/VehicleTemplate/Blueprints/OffroadCar/BP_VehicleAdvOffroadCar",
}


def log(msg):
    unreal.log(f"[setup_m1] {msg}")


def err(where, exc):
    REPORT["errors"].append({"where": where, "error": str(exc), "trace": traceback.format_exc()[-800:]})
    unreal.log_error(f"[setup_m1] {where}: {exc}")


def warn(msg):
    REPORT["warnings"].append(msg)
    unreal.log_warning(f"[setup_m1] {msg}")


def load(path):
    asset = EAL.load_asset(path)
    if asset is None:
        raise RuntimeError(f"asset não encontrado: {path}")
    return asset


def bp_class(path):
    cls = EAL.load_blueprint_class(path)
    if cls is None:
        raise RuntimeError(f"blueprint não encontrado: {path}")
    return cls


def ensure_asset(name, folder, asset_class, factory):
    path = f"{folder}/{name}"
    if EAL.does_asset_exist(path):
        REPORT["skipped"].append(path)
        return load(path), False
    EAL.make_directory(folder)
    asset = TOOLS.create_asset(name, folder, asset_class, factory)
    if asset is None:
        raise RuntimeError(f"falha ao criar {path}")
    REPORT["created"].append(path)
    return asset, True


def ensure_input_action(name, value_type):
    factory_cls = getattr(unreal, "InputAction_Factory", None)
    ia, created = ensure_asset(name, "/Game/Core/Input", unreal.InputAction, factory_cls() if factory_cls else None)
    if created:
        ia.set_editor_property("value_type", value_type)
        EAL.save_loaded_asset(ia)
    return ia


def make_key(name):
    key = unreal.Key()
    try:
        key.set_editor_property("key_name", name)
    except Exception:  # noqa: BLE001 - fallback de API
        key.import_text(name)
    return key


def ensure_data_asset(name, cls, props):
    factory = unreal.DataAssetFactory()
    factory.set_editor_property("data_asset_class", cls)
    da, created = ensure_asset(name, "/Game/Data", cls, factory)
    if created:
        for k, v in props.items():
            try:
                da.set_editor_property(k, v)
            except Exception as exc:  # noqa: BLE001
                err(f"{name}.{k}", exc)
        EAL.save_loaded_asset(da)
    return da


def ensure_blueprint(name, folder, parent):
    factory = unreal.BlueprintFactory()
    factory.set_editor_property("parent_class", parent)
    bp, created = ensure_asset(name, folder, unreal.Blueprint, factory)
    if created:
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    return bp, created


def cdo_of(bp):
    return unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def set_props(obj, props, where):
    for k, v in props.items():
        try:
            obj.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"{where}.{k}", exc)


def setup_mesh(mesh_comp, skeletal_mesh, anim_class, where, location=None, rotation=None):
    try:
        mesh_comp.set_skeletal_mesh_asset(skeletal_mesh)
    except Exception:  # noqa: BLE001
        try:
            mesh_comp.set_editor_property("skeletal_mesh_asset", skeletal_mesh)
        except Exception as exc:  # noqa: BLE001
            err(f"{where}.mesh", exc)
    set_props(mesh_comp, {"animation_mode": unreal.AnimationMode.ANIMATION_BLUEPRINT, "anim_class": anim_class}, where)
    if location is not None:
        mesh_comp.set_editor_property("relative_location", location)
    if rotation is not None:
        mesh_comp.set_editor_property("relative_rotation", rotation)


def finish_bp(bp):
    EAL.save_loaded_asset(bp)


def main():
    # ---------------- Input
    vt = unreal.InputActionValueType
    ia = {
        "sprint": ensure_input_action("IA_Sprint", vt.BOOLEAN),
        "aim": ensure_input_action("IA_Aim", vt.BOOLEAN),
        "fire": ensure_input_action("IA_Fire", vt.BOOLEAN),
        "reload": ensure_input_action("IA_Reload", vt.BOOLEAN),
        "interact": ensure_input_action("IA_Interact", vt.BOOLEAN),
    }
    factory_cls = getattr(unreal, "InputMappingContext_Factory", None)
    imc, created = ensure_asset("IMC_JR_Combat", "/Game/Core/Input", unreal.InputMappingContext,
                                factory_cls() if factory_cls else None)
    if created:
        bindings = [
            ("sprint", "LeftShift"), ("sprint", "Gamepad_LeftThumbstick"),
            ("aim", "RightMouseButton"), ("aim", "Gamepad_LeftTrigger"),
            ("fire", "LeftMouseButton"), ("fire", "Gamepad_RightTrigger"),
            ("reload", "R"), ("reload", "Gamepad_FaceButton_Left"),
            ("interact", "E"), ("interact", "Gamepad_FaceButton_Top"),
        ]
        for action, key in bindings:
            try:
                imc.map_key(ia[action], make_key(key))
            except Exception as exc:  # noqa: BLE001
                err(f"IMC_JR_Combat.{action}.{key}", exc)
        EAL.save_loaded_asset(imc)

    # ---------------- Dados
    weapon = ensure_data_asset("DA_Weapon_AlienPistol", unreal.JRWeaponDefinition, {
        "weapon_id": "WPN-001", "damage": 25.0, "fire_rate": 4.0, "magazine_size": 12, "starting_reserve": 48,
        "reload_time": 1.6, "range": 6000.0, "spread_half_angle_degrees": 1.5,
    })
    ea = unreal.JREnemyAttackType
    arche = {
        "Melee": ensure_data_asset("DA_Enemy_ZombieMelee", unreal.JREnemyArchetype, {
            "archetype_id": "ENM-001", "max_health": 60.0, "move_speed": 380.0, "aggro_radius": 2500.0,
            "lose_aggro_radius": 3500.0, "attack_type": ea.MELEE, "attack_range": 150.0, "attack_damage": 15.0,
            "attack_interval": 1.0}),
        "Archer": ensure_data_asset("DA_Enemy_ZombieArcher", unreal.JREnemyArchetype, {
            "archetype_id": "ENM-002", "max_health": 40.0, "move_speed": 300.0, "aggro_radius": 4000.0,
            "lose_aggro_radius": 5000.0, "attack_type": ea.PROJECTILE, "attack_range": 1800.0, "attack_damage": 20.0,
            "attack_interval": 2.5, "projectile_speed": 3000.0, "spread_half_angle_degrees": 3.0}),
        "Gunner": ensure_data_asset("DA_Enemy_ZombieGunner", unreal.JREnemyArchetype, {
            "archetype_id": "ENM-003", "max_health": 50.0, "move_speed": 320.0, "aggro_radius": 3500.0,
            "lose_aggro_radius": 4500.0, "attack_type": ea.BURST, "attack_range": 1500.0, "attack_damage": 8.0,
            "attack_interval": 3.0, "burst_count": 3, "burst_shot_interval": 0.15, "projectile_speed": 8000.0,
            "spread_half_angle_degrees": 5.0}),
    }

    # ---------------- Personagem
    char_bp, created = ensure_blueprint("BP_Character_Hero01", "/Game/Characters/Hero01", unreal.JRCharacter)
    if created:
        cdo = cdo_of(char_bp)
        set_props(cdo, {
            "move_action": load(TPL["ia_move"]), "look_action": load(TPL["ia_look"]),
            "mouse_look_action": load(TPL["ia_mouselook"]), "jump_action": load(TPL["ia_jump"]),
            "sprint_action": ia["sprint"], "aim_action": ia["aim"], "fire_action": ia["fire"],
            "reload_action": ia["reload"], "interact_action": ia["interact"],
        }, "BP_Character_Hero01")
        setup_mesh(cdo.get_editor_property("mesh"), load(TPL["manny"]), bp_class(TPL["abp_unarmed"]),
                   "BP_Character_Hero01", unreal.Vector(0, 0, -90), unreal.Rotator(0, 0, -90))
        try:
            cdo.get_editor_property("weapon_component").set_editor_property("definition", weapon)
        except Exception as exc:  # noqa: BLE001
            err("BP_Character_Hero01.weapon", exc)
        finish_bp(char_bp)
    char_class = unreal.BlueprintEditorLibrary.generated_class(char_bp)

    skin_a = unreal.JRSkinDefinition()
    set_props(skin_a, {"skin_id": "SKN-001", "mesh": load(TPL["manny"])}, "skin_a")
    skin_b = unreal.JRSkinDefinition()
    set_props(skin_b, {"skin_id": "SKN-002", "mesh": load(TPL["quinn"])}, "skin_b")
    char_def = ensure_data_asset("DA_Character_Hero01", unreal.JRCharacterDefinition, {
        "character_id": "CHR-001", "character_class": char_class, "skins": [skin_a, skin_b]})

    # ---------------- Veículo
    veh_bp, created = ensure_blueprint("BP_Vehicle_SUV", "/Game/Vehicles/SUV", unreal.JRVehiclePawn)
    if created:
        cdo = cdo_of(veh_bp)
        set_props(cdo, {
            "throttle_action": load(TPL["ia_throttle"]), "brake_action": load(TPL["ia_brake"]),
            "steer_action": load(TPL["ia_steering"]), "handbrake_action": load(TPL["ia_handbrake"]),
            "look_action": load(TPL["ia_lookaround"]),
        }, "BP_Vehicle_SUV")
        mesh = cdo.get_editor_property("mesh")
        setup_mesh(mesh, load(TPL["offroad_mesh"]), bp_class(TPL["offroad_abp"]), "BP_Vehicle_SUV")
        # Copia física (rodas, motor, transmissão, colisão) do Offroad da Epic
        try:
            tcdo = unreal.get_default_object(bp_class(TPL["offroad_bp"]))
            try:
                mesh.set_editor_property("body_instance", tcdo.get_editor_property("mesh").get_editor_property("body_instance"))
            except Exception as exc:  # noqa: BLE001
                err("BP_Vehicle_SUV.body_instance", exc)
            src = tcdo.get_editor_property("vehicle_movement_component")
            dst = cdo.get_editor_property("vehicle_movement_component")
            for prop in ["wheel_setups", "engine_setup", "differential_setup", "transmission_setup", "steering_setup",
                         "mass", "chassis_width", "chassis_height", "drag_coefficient", "downforce_coefficient",
                         "enable_center_of_mass_override", "center_of_mass_override", "suspension_trace_collision_response",
                         "legacy_wheel_friction_position"]:
                try:
                    dst.set_editor_property(prop, src.get_editor_property(prop))
                except Exception as exc:  # noqa: BLE001
                    warn(f"BP_Vehicle_SUV.movement.{prop}: {exc}")
        except Exception as exc:  # noqa: BLE001
            err("BP_Vehicle_SUV.copy_template", exc)
        finish_bp(veh_bp)
    veh_class = unreal.BlueprintEditorLibrary.generated_class(veh_bp)

    # ---------------- Inimigos
    enemy_classes = {}
    for key, mesh_key in (("Melee", "manny"), ("Archer", "quinn"), ("Gunner", "manny")):
        name = f"BP_Enemy_Zombie{key}"
        bp, created = ensure_blueprint(name, "/Game/Enemies", unreal.JREnemyCharacter)
        if created:
            cdo = cdo_of(bp)
            set_props(cdo, {"archetype": arche[key]}, name)
            setup_mesh(cdo.get_editor_property("mesh"), load(TPL[mesh_key]), bp_class(TPL["abp_unarmed"]), name,
                       unreal.Vector(0, 0, -90), unreal.Rotator(0, 0, -90))
            finish_bp(bp)
        enemy_classes[key] = unreal.BlueprintEditorLibrary.generated_class(bp)

    # ---------------- Fase
    level_def = ensure_data_asset("DA_Level_L01_Zombies", unreal.JRLevelDefinition, {
        "level_id": "L01", "next_level_id": "L02", "vehicle_class": veh_class,
        "checkpoint_ids": ["Start", "Transition"], "rescue_target_id": "Victim01",
        "available_characters": [char_def], "enemy_archetypes": list(arche.values()),
        "max_full_update_enemies": 12, "max_visible_enemies": 30,
    })

    # ---------------- Core
    pc_bp, created = ensure_blueprint("BP_PlayerController", "/Game/Core", unreal.JRPlayerController)
    if created:
        set_props(cdo_of(pc_bp), {
            "vehicle_mapping_contexts": [load(TPL["imc_vehicle"]), load(TPL["imc_vehicle_mouse"])],
            "on_foot_mapping_contexts": [load(TPL["imc_default"]), load(TPL["imc_mouselook"]), imc],
        }, "BP_PlayerController")
        finish_bp(pc_bp)
    pc_class = unreal.BlueprintEditorLibrary.generated_class(pc_bp)

    gm_bp, created = ensure_blueprint("BP_GameMode_L01", "/Game/Core", unreal.JRGameMode)
    if created:
        set_props(cdo_of(gm_bp), {
            "level_definition": level_def, "fallback_vehicle_class": veh_class,
            "fallback_character_class": char_class, "player_controller_class": pc_class,
        }, "BP_GameMode_L01")
        finish_bp(gm_bp)

    gi_bp, created = ensure_blueprint("BP_GameInstance", "/Game/Core", unreal.JRGameInstance)
    if created:
        set_props(cdo_of(gi_bp), {"characters": [char_def], "levels": [level_def]}, "BP_GameInstance")
        finish_bp(gi_bp)

    REPORT["enemy_classes"] = {k: v.get_path_name() for k, v in enemy_classes.items()}


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    out = os.path.join(REPO, "reports", "setup_m1_assets.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=2)
    log(f"criados={len(REPORT['created'])} existentes={len(REPORT['skipped'])} "
        f"erros={len(REPORT['errors'])} avisos={len(REPORT['warnings'])}. Relatório: {out}")
