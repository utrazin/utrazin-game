"""Carro mais "arcade": aderência, estabilidade, colisão confiável e motorista visível.

RODA NO EDITOR (caixa Cmd), sem Play e DEPOIS de compilar o C++ novo
(DriverMesh/DriverPivot/SteeringWheelMesh, DrivingAnim e UJRVehicleTuningLibrary):
  py "E:/game/utrazin-game/tools/unreal/fix_vehicle_feel.py"
Rode de novo depois de build_l01.py (ele volta as rampas para colisão complexa).

Faz (cada parte é independente; ver reports/fix_vehicle_feel.json):
 1. movimento   BP_Vehicle_SUV: massa 1400, centro de massa baixo, inércia de giro maior, tração 4x4 (45/55),
                motor 7000 RPM / 750 Nm com curva plana, câmbio recalculado para ~140 km/h no limite,
                curva do volante plana (a redução por velocidade fica no C++), rodas ignoram Pawn
 2. rodas       cópias próprias BP_JRWheel_Front/Rear em /Game/Vehicles/SUV (não mexe nas da Epic),
                mais atrito e rigidez de curva, curva lateral plana depois do pico, controle de tração (ABS desligado),
                volante 40 graus só na frente; aponta o BP_Vehicle_SUV para elas
 3. visual      carroceria, pneus e volante sem colisão (só o corpo físico do esqueleto colide)
 4. física      CCD no corpo do carro (BP + todos os corpos do Physics Asset)
 5. rampas      L01: rampas, paredões, guard-rail e contêiner com colisão convexa
 6. motorista   importa Driving.fbx, retarget para Hero01/02 e preenche DrivingAnim no BP de cada herói
 7. buggy       reimporta SM_Car_AlienBuggy (sem volante) e importa SM_Car_AlienBuggy_SteeringWheel;
                motorista no banco central, mãos no volante; SeatPoint no banco central
 8. paredes     PM_VehicleChassis (atrito baixo) na carroceria + raspão nas paredes (C++)
 9. ajustes     nitro até 160 km/h, volante cheio até 50 km/h e 65% a 130 km/h
10. freio       torque de freio/freio de mão explícito nas rodas, "ré como freio" ligado, ré no câmbio;
                ajuda anti-capotagem e desvirar (C++) com valores do bloco STABILITY
11. teclas      IMC do carro: S/seta baixo/gatilho esquerdo = freio (e ré parado), W/seta cima/gatilho direito
                = acelerar, espaço/A = freio de mão, R/Y = desvirar (IA_Reset), nitro sai do gatilho esquerdo
                (brigava com o freio) para Shift esquerdo/RB; relata teclas antes/depois e conflitos
Valores ajustáveis nas constantes abaixo. Pode rodar de novo.
"""
import json
import math
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "values": {}}
VEHICLE_BP = "/Game/Vehicles/SUV/BP_Vehicle_SUV"
WHEEL_DIR = "/Game/Vehicles/SUV"
HEROES = ("01", "02")

# ---- valores (A-038 em docs/decisions/ASSUMPTIONS.md)
MASS_KG = 1400.0
COM_Z_CM = -40.0                      # centro de massa abaixo do eixo: difícil capotar (era -25; capotava no pilar)
INERTIA_SCALE = (1.0, 1.0, 1.5)       # Z maior = gira menos (menos pião)
MAX_TORQUE = 750.0
MAX_RPM = 7000.0
TORQUE_CURVE = ((0.0, 0.7), (1500.0, 0.9), (4500.0, 1.0), (7000.0, 0.85))   # X = RPM, Y = torque relativo
GEARS = [3.2, 2.1, 1.5, 1.15, 0.92]
TOP_SPEED_KMH = 140.0                 # velocidade no limite de RPM na última marcha (o arrasto segura ~130)
STEERING_CURVE = ((0.0, 1.0), (300.0, 1.0))   # plana: a redução por velocidade é feita no C++
FRONT_REAR_SPLIT = 0.45
DOWNFORCE = 0.8
DRAG = 0.1
NITRO = {"nitro_max_speed_kmh": 160.0, "nitro_acceleration": 500.0}
HANDLING = {"steer_full_until_kmh": 50.0, "steer_min_at_kmh": 130.0, "steer_at_high_speed": 0.65,
            "lateral_grip_assist": 2.5}
# Buggy (cm no espaço da malha SM_Car_AlienBuggy, ver tools/blender/make_car_buggy.py)
SEAT_LOCAL = (-30.0, 0.0, 76.0)       # topo do assento central
DRIVER_PIVOT = (-30.0, -7.6, 88.0)    # quadril do motorista
DRIVER_HIPS_CM = 62.6                 # quadril acima dos pés na pose "Driving" (herói ~1,7 m), em cm de mundo
WHEEL_LOCAL = (8.0, 0.0, 116.5)       # centro do volante
WHEEL_PITCH = -20.25
BUGGY_FBX = ("SM_Car_AlienBuggy", "SM_Car_AlienBuggy_SteeringWheel")
# Freio (N·m por roda, raio 50 cm): frente 2500 + trás 1800 = ~12 m/s² num carro de 1400 kg. Com atrito 4x
# a roda não trava com esse torque, então o ABS do Chaos ficou DESLIGADO (ele solta o freio quando acha que
# a roda patina e era suspeito do "não freia"). Freio de mão só atrás (derrapa de propósito).
# O C++ soma BrakeAssistDecel por cima.
WHEEL = {
    "front": {"friction_force_multiplier": 4.0, "cornering_stiffness": 2000.0, "side_slip_modifier": 1.0,
              "max_steer_angle": 40.0, "affected_by_steering": True, "affected_by_engine": True,
              "affected_by_handbrake": False, "abs_enabled": False, "traction_control_enabled": True,
              "affected_by_brake": True, "max_brake_torque": 2500.0, "max_hand_brake_torque": 0.0},
    "rear": {"friction_force_multiplier": 4.0, "cornering_stiffness": 2000.0, "side_slip_modifier": 0.9,
             "max_steer_angle": 0.0, "affected_by_steering": False, "affected_by_engine": True,
             "affected_by_handbrake": True, "abs_enabled": False, "traction_control_enabled": True,
             "affected_by_brake": True, "max_brake_torque": 1800.0, "max_hand_brake_torque": 5000.0},
}
REVERSE_GEARS = [3.0]                 # ré (o Chaos usa "ré como freio": segurar S parado engata a ré)
# Ajuda anti-capotagem e desvirar (propriedades do AJRVehiclePawn; ver A-049 em ASSUMPTIONS.md)
STABILITY = {"brake_assist_decel": 450.0, "brake_assist_full_at_kmh": 15.0, "brake_assist_min_kmh": 2.0,
             "roll_stabilization": True, "roll_assist_start_degrees": 35.0, "roll_assist_air_start_degrees": 20.0,
             "roll_assist_accel": 8.0, "roll_assist_damping": 2.5, "roll_assist_air_scale": 0.5,
             "auto_recover": True, "auto_recover_delay": 2.5, "auto_recover_max_kmh": 10.0,
             "flipped_up_threshold": 0.5, "recover_height": 150.0, "recover_duration": 0.6,
             "manual_recover_max_kmh": 25.0, "recover_cooldown": 1.5}
# Teclas do carro (IMC do carro = 1º de BP_PlayerController.vehicle_mapping_contexts)
PC_BP = "/Game/Core/BP_PlayerController"
IMC_VEHICLE = "/Game/VehicleTemplate/Input/IMC_Vehicle_Default"
IA_DIR = "/Game/VehicleTemplate/Input/Actions"
IA_NITRO = "/Game/Core/Input/IA_Nitro"
VEHICLE_KEYS = {
    "IA_Throttle": ("W", "Up", "Gamepad_RightTriggerAxis"),
    "IA_Brake": ("S", "Down", "Gamepad_LeftTriggerAxis"),
    "IA_Handbrake": ("SpaceBar", "Gamepad_FaceButton_Bottom"),
    "IA_Reset": ("R", "Gamepad_FaceButton_Top"),
    "IA_Nitro": ("LeftShift", "Gamepad_RightShoulder"),
}
# O nitro estava no gatilho esquerdo junto com o freio: apertar para frear também empurrava para frente.
VEHICLE_KEYS_REMOVE = {"IA_Nitro": ("Gamepad_LeftTrigger", "Gamepad_LeftTriggerAxis")}
BP_ACTIONS = {"throttle_action": "IA_Throttle", "brake_action": "IA_Brake", "handbrake_action": "IA_Handbrake",
              "reset_action": "IA_Reset"}
RAMP_MESHES = ("SM_Ramp", "SM_RampLanding", "SM_RockWall", "SM_GuardRail", "SM_Container")
PROPS_DIR = "/Game/Environment/L01/Props"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[vehicle_feel] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[vehicle_feel] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1200:]})
    unreal.log_error(f"[vehicle_feel] {where}: {exc}")


def step(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        err(fn.__name__, exc)


def setp(obj, k, v, where=""):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{where}.{k}: {exc}")
        return False


def getp(obj, k, where=""):
    try:
        return obj.get_editor_property(k)
    except Exception as exc:  # noqa: BLE001
        warn(f"{where}.{k} (leitura): {exc}")
        return None


def cdo_of(bp_path):
    bp = EAL.load_asset(bp_path)
    if bp is None:
        raise RuntimeError(f"não existe: {bp_path}")
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def compile_save(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)


def edit_struct(owner, prop, fields, where):
    """Structs voltam como cópia no Python: lê, muda campo a campo e grava de volta."""
    s = getp(owner, prop, where)
    if s is None:
        return None
    for k, v in fields.items():
        setp(s, k, v, f"{where}.{prop}")
    setp(owner, prop, s, where)
    return s


LIB = getattr(unreal, "JRVehicleTuningLibrary", None)


def v2(keys):
    return [unreal.Vector2D(float(x), float(y)) for x, y in keys]


def keys_of(lst):
    return [(round(float(k.x), 3), round(float(k.y), 3)) for k in (lst or [])]


def need_lib():
    if LIB is None:
        raise RuntimeError("UJRVehicleTuningLibrary não existe: compile o C++ novo antes")
    return LIB


def response_enum(name):
    for enum_name in ("CollisionResponseType", "CollisionResponse"):
        e = getattr(unreal, enum_name, None)
        if e is not None and hasattr(e, name):
            return getattr(e, name)
    raise RuntimeError(f"enum de resposta de colisão não encontrado: {name}")


# ------------------------------------------------------------------ 1. movimento
def movement():
    bp, cdo = cdo_of(VEHICLE_BP)
    mv = cdo.get_editor_property("vehicle_movement_component")
    w = "movement"
    before = {}
    for k in ("mass", "center_of_mass_override", "inertia_tensor_scale", "downforce_coefficient", "drag_coefficient"):
        before[k] = str(getp(mv, k, w))
    R["values"]["movement_before"] = before
    setp(mv, "mass", MASS_KG, w)
    setp(mv, "enable_center_of_mass_override", True, w)
    setp(mv, "center_of_mass_override", unreal.Vector(0.0, 0.0, COM_Z_CM), w)
    setp(mv, "inertia_tensor_scale", unreal.Vector(*INERTIA_SCALE), w)
    setp(mv, "downforce_coefficient", DOWNFORCE, w)

    setp(mv, "drag_coefficient", DRAG, w)
    # Freio: segurar S andando freia; quase parado engata a ré (padrão do Chaos, garantido aqui).
    R["values"]["reverse_as_brake_before"] = str(getp(mv, "reverse_as_brake", w))
    setp(mv, "reverse_as_brake", True, w)
    eng = getp(mv, "engine_setup", w)
    if eng is not None:
        R["values"]["engine_before"] = {k: str(getp(eng, k, "engine")) for k in
                                        ("max_torque", "max_rpm", "engine_idle_rpm", "engine_rev_up_moi", "engine_brake_effect")}
        setp(eng, "max_torque", MAX_TORQUE, "engine")
        setp(eng, "max_rpm", MAX_RPM, "engine")
        setp(mv, "engine_setup", eng, w)
    lib = need_lib()
    R["values"]["torque_curve_before"] = keys_of(lib.get_torque_curve(mv))
    R["values"]["steering_curve_before"] = keys_of(lib.get_steering_curve(mv))
    if not lib.set_torque_curve(mv, v2(TORQUE_CURVE)):
        warn("set_torque_curve falhou")
    if not lib.set_steering_curve(mv, v2(STEERING_CURVE)):
        warn("set_steering_curve falhou")
    R["values"]["torque_curve_after"] = keys_of(lib.get_torque_curve(mv))
    R["values"]["steering_curve_after"] = keys_of(lib.get_steering_curve(mv))

    # Câmbio: relação final calculada para TOP_SPEED_KMH no limite de RPM da última marcha.
    radius_cm = 40.0
    try:
        s0 = list(mv.get_editor_property("wheel_setups"))[0]
        radius_cm = float(unreal.get_default_object(s0.get_editor_property("wheel_class")).get_editor_property("wheel_radius"))
    except Exception as exc:  # noqa: BLE001
        warn(f"raio da roda (usando 40 cm): {exc}")
    final = MAX_RPM * 2.0 * math.pi * (radius_cm / 100.0) * 0.06 / (TOP_SPEED_KMH * GEARS[-1])
    tr = getp(mv, "transmission_setup", w)
    if tr is not None:
        R["values"]["transmission_before"] = {k: str(getp(tr, k, "transmission")) for k in
                                              ("use_automatic_gears", "final_ratio", "forward_gear_ratios",
                                               "change_up_rpm", "change_down_rpm", "gear_change_time")}
        R["values"]["reverse_gears_before"] = str(getp(tr, "reverse_gear_ratios", "transmission"))
        for k, v in (("use_automatic_gears", True), ("forward_gear_ratios", GEARS), ("final_ratio", round(final, 3)),
                     ("change_up_rpm", MAX_RPM * 0.85), ("change_down_rpm", MAX_RPM * 0.45), ("gear_change_time", 0.25),
                     ("reverse_gear_ratios", REVERSE_GEARS)):
            setp(tr, k, v, "transmission")
        setp(mv, "transmission_setup", tr, w)
    R["values"]["gearing"] = {"wheel_radius_cm": radius_cm, "final_ratio": round(final, 3), "gears": GEARS,
                              "kmh_por_marcha_no_limite": [round(MAX_RPM * 2 * math.pi * radius_cm / 100 * 0.06 / (g * final), 1)
                                                           for g in GEARS]}

    diff_type = None
    try:
        diff_type = unreal.VehicleDifferential.ALL_WHEEL_DRIVE
    except Exception as exc:  # noqa: BLE001
        warn(f"enum VehicleDifferential: {exc}")
    fields = {"front_rear_split": FRONT_REAR_SPLIT}
    if diff_type is not None:
        fields["differential_type"] = diff_type
    edit_struct(mv, "differential_setup", fields, w)

    # Rodas não detectam Pawn: o carro não "escala" zumbis (o chassi ainda atropela).
    try:
        resp = mv.get_editor_property("wheel_trace_collision_responses")
        resp.set_editor_property("pawn", response_enum("ECR_IGNORE"))
        mv.set_editor_property("wheel_trace_collision_responses", resp)
        log("rodas ignoram Pawn")
    except Exception as exc:  # noqa: BLE001
        warn(f"wheel_trace_collision_responses: {exc}")

    # Só registra (sem mexer): ajudas de rotação herdadas do Offroad da Epic.
    for k in ("torque_control", "target_rotation_control", "stabilize_control", "steering_setup"):
        R["values"][k] = str(getp(mv, k, w))[:600]
    bp.modify()
    compile_save(bp)
    after = {k: str(getp(mv, k, w)) for k in ("mass", "center_of_mass_override", "inertia_tensor_scale", "downforce_coefficient")}
    R["values"]["movement_after"] = after
    log(f"movimento: massa {MASS_KG}, CM z={COM_Z_CM}, torque {MAX_TORQUE}, 4x4 {FRONT_REAR_SPLIT}")


# ------------------------------------------------------------------ 2. rodas
def axle_of(setup, wheel_cdo):
    bone = str(setup.get_editor_property("bone_name")).upper()
    try:
        axle = str(wheel_cdo.get_editor_property("axle_type")).upper()
        if "FRONT" in axle:
            return "front"
        if "REAR" in axle:
            return "rear"
    except Exception:  # noqa: BLE001
        pass
    return "front" if ("_F" in bone or "FRONT" in bone) else "rear"


def own_wheel_class(src_class, axle):
    """Duplica o BP de roda da Epic para /Game/Vehicles/SUV (uma vez) e devolve a classe nova."""
    path = f"{WHEEL_DIR}/BP_JRWheel_{axle.capitalize()}"
    if not EAL.does_asset_exist(path):
        src_path = src_class.get_path_name().split(".")[0]
        if EAL.does_asset_exist(src_path):
            EAL.duplicate_asset(src_path, path)
            log(f"roda {axle}: {src_path} copiada para {path}")
        else:
            # Classe C++ (sem BP): cria um BP filho dela.
            factory = unreal.BlueprintFactory()
            factory.set_editor_property("parent_class", src_class)
            TOOLS.create_asset(path.split("/")[-1], WHEEL_DIR, unreal.Blueprint, factory)
            log(f"roda {axle}: BP novo filho de {src_class.get_name()}")
    return path


def wheels():
    bp, cdo = cdo_of(VEHICLE_BP)
    mv = cdo.get_editor_property("vehicle_movement_component")
    setups = list(mv.get_editor_property("wheel_setups"))
    if not setups:
        raise RuntimeError("BP_Vehicle_SUV sem wheel_setups")
    owned = {}
    info = []
    for i, s in enumerate(setups):
        cls = s.get_editor_property("wheel_class")
        if cls is None:
            warn(f"roda {i} sem classe")
            continue
        axle = axle_of(s, unreal.get_default_object(cls))
        if axle not in owned:
            if cls.get_path_name().startswith(WHEEL_DIR + "/BP_JRWheel_"):
                owned[axle] = cls.get_path_name().split(".")[0]
            else:
                owned[axle] = own_wheel_class(cls, axle)
        new_cls = unreal.BlueprintEditorLibrary.generated_class(EAL.load_asset(owned[axle]))
        s.set_editor_property("wheel_class", new_cls)
        setups[i] = s
        info.append({"bone": str(s.get_editor_property("bone_name")), "axle": axle, "from": cls.get_name()})
    mv.set_editor_property("wheel_setups", setups)
    R["values"]["wheels"] = info
    for axle, path in owned.items():
        wbp, wcdo = cdo_of(path)
        where = f"BP_JRWheel_{axle}"
        R["values"][f"{where}_before"] = {k: str(getp(wcdo, k, where)) for k in WHEEL[axle]}
        for k, v in WHEEL[axle].items():
            setp(wcdo, k, v, where)
        # Curva lateral: depois do pico não perde aderência (o "gelo" vinha da queda após o pico).
        try:
            lib = need_lib()
            keys = keys_of(lib.get_lateral_slip_graph(wcdo))
            R["values"][f"{where}_lateral_before"] = keys
            if len(keys) >= 2:
                peak_i = max(range(len(keys)), key=lambda j: keys[j][1])
                flat = keys[:peak_i + 1] + [(t, keys[peak_i][1]) for t, _ in keys[peak_i + 1:]]
                lib.set_lateral_slip_graph(wcdo, v2(flat))
                R["values"][f"{where}_lateral_after"] = keys_of(lib.get_lateral_slip_graph(wcdo))
            else:
                log(f"{where}: curva lateral vazia (o Chaos usa o atrito padrão); mantida")
        except Exception as exc:  # noqa: BLE001
            warn(f"{where}.lateral_slip_graph: {exc}")
        R["values"][f"{where}_after"] = {k: str(getp(wcdo, k, where)) for k in WHEEL[axle]}
        compile_save(wbp)
    bp.modify()
    compile_save(bp)
    log(f"rodas próprias: {owned}")


# ------------------------------------------------------------------ 3. visual sem colisão
def visuals():
    bp, cdo = cdo_of(VEHICLE_BP)
    n = 0
    for name in ("chassis_mesh", "tire_fl", "tire_fr", "tire_bl", "tire_br", "driver_mesh", "steering_wheel_mesh"):
        comp = getp(cdo, name, "visual")
        if comp is None:
            continue
        try:
            comp.set_collision_profile_name("NoCollision")
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}.collision_profile: {exc}")
        setp(comp, "can_ever_affect_navigation", False, name)
        n += 1
    compile_save(bp)
    log(f"{n} componentes visuais sem colisão")


# ------------------------------------------------------------------ 4. CCD
def ccd():
    bp, cdo = cdo_of(VEHICLE_BP)
    mesh = cdo.get_editor_property("mesh")
    edit_struct(mesh, "body_instance", {"use_ccd": True}, "mesh")
    compile_save(bp)
    skm = mesh.get_editor_property("skeletal_mesh_asset")
    pa = getp(skm, "physics_asset", "skm") if skm else None
    if pa is None:
        warn("physics asset do carro não encontrado")
        return
    n = need_lib().set_physics_asset_ccd(pa, True)
    EAL.save_loaded_asset(pa, only_if_is_dirty=False)
    R["values"]["physics_asset"] = {"path": pa.get_path_name(), "bodies_ccd": n}
    log(f"CCD ligado em {pa.get_name()} ({n} corpos) e no BP")


# ------------------------------------------------------------------ 5. rampas
def ramps():
    sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
    done = []
    for name in RAMP_MESHES:
        path = f"{PROPS_DIR}/{name}"
        if not EAL.does_asset_exist(path):
            continue
        sm = EAL.load_asset(path)
        try:
            sub.set_convex_decomposition_collisions(sm, 6, 16, 100000)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: convexo falhou ({exc}); fica com colisão complexa")
            continue
        count = 0
        try:
            count = sub.get_convex_collision_count(sm)
        except Exception:  # noqa: BLE001
            count = -1
        if count == 0:
            warn(f"{name}: nenhum casco convexo gerado; fica com colisão complexa")
            continue
        bs = sm.get_editor_property("body_setup")
        bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_DEFAULT)
        EAL.save_loaded_asset(sm, only_if_is_dirty=False)
        done.append(f"{name} ({count} cascos)")
    R["values"]["ramps"] = done
    log(f"colisão convexa: {done or 'nenhuma malha L01 encontrada'}")


# ------------------------------------------------------------------ 6. motorista
def import_anim(fbx, skeleton):
    name = "A_" + os.path.splitext(os.path.basename(fbx))[0]
    folder = "/Game/Characters/Mixamo/Anims/hero"
    target = f"{folder}/{name}"
    if EAL.does_asset_exist(target):
        return target
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = False
    o.import_as_skeletal = True
    o.import_animations = True
    o.import_materials = False
    o.import_textures = False
    o.skeleton = skeleton
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    task.options = o
    TOOLS.import_asset_tasks([task])
    if not EAL.does_asset_exist(target):
        for p in task.imported_object_paths:
            a = EAL.load_asset(p.split(".")[0])
            if isinstance(a, unreal.AnimSequence):
                EAL.rename_asset(p.split(".")[0], target)
                break
    if not EAL.does_asset_exist(target):
        raise RuntimeError(f"animação não importada: {fbx}")
    return target


def driver():
    fbx = os.path.join(REPO, "assets", "raw", "mixamo", "hero", "Driving.fbx")
    if not os.path.exists(fbx):
        raise RuntimeError(f"falta {fbx}")
    xbot = EAL.load_asset("/Game/Characters/Mixamo/SK_XBot")
    src = import_anim(fbx, xbot.skeleton)
    try:
        a = EAL.load_asset(src)
        a.set_editor_property("enable_root_motion", False)
        EAL.save_loaded_asset(a, only_if_is_dirty=False)
    except Exception as exc:  # noqa: BLE001
        warn(f"A_Driving root motion: {exc}")
    for nn in HEROES:
        folder = f"/Game/Characters/Hero{nn}/Anims/Wave1"
        target = f"{folder}/A_Driving_H{nn}"
        # A Unreal NÃO sobrescreve no retarget: só faz se ainda não existir (senão cria cópia renomeada).
        if not EAL.does_asset_exist(target):
            EAL.make_directory(folder)
            mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
            rtg = EAL.load_asset(f"/Game/Characters/Rigs/RTG_Mixamo_Hero{nn}")
            out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
                [EAL.find_asset_data(src)], xbot, mesh, rtg, search="", replace="", prefix="",
                suffix=f"_H{nn}", target_path=folder, use_source_path=False, include_referenced_assets=False,
                overwrite_existing_files=True)
            for o in out:
                p = str(getattr(o, "package_name", "") or "")
                if p and EAL.does_asset_exist(p):
                    EAL.save_loaded_asset(EAL.load_asset(p), only_if_is_dirty=False)
        if not EAL.does_asset_exist(target):
            warn(f"Hero{nn}: retarget não gerou {target}")
            continue
        bp, cdo = cdo_of(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
        if setp(cdo, "driving_anim", EAL.load_asset(target), f"Hero{nn}"):
            compile_save(bp)
            log(f"Hero{nn}: DrivingAnim = {target}")
    # Reserva: herói sem DrivingAnim usa a do Hero01.
    if EAL.does_asset_exist("/Game/Characters/Hero01/Anims/Wave1/A_Driving_H01"):
        bp, cdo = cdo_of(VEHICLE_BP)
        if setp(cdo, "fallback_driving_anim", EAL.load_asset("/Game/Characters/Hero01/Anims/Wave1/A_Driving_H01"), "Vehicle"):
            compile_save(bp)


# ------------------------------------------------------------------ 7. buggy: volante separado e motorista
def import_static(fbx, folder, name):
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)):
        setp(d, k, v, name)
    task.options = o
    TOOLS.import_asset_tasks([task])
    sm = EAL.load_asset(f"{folder}/{name}")
    if sm is None:
        raise RuntimeError(f"não importou {fbx}")
    # mesmos materiais do setup_wave1 (cor do vértice + brilho)
    glow = EAL.load_asset("/Game/Environment/L01/Materials/M_L01_Glow")
    base = EAL.load_asset("/Game/Environment/L01/Materials/M_L01_VertexColor")
    for i, slot in enumerate(sm.get_editor_property("static_materials")):
        sm.set_material(i, glow if "Glow" in str(slot.get_editor_property("material_slot_name")) else base)
    EAL.save_loaded_asset(sm, only_if_is_dirty=False)
    return sm


def buggy():
    src = os.path.join(REPO, "assets", "work", "vehicles")
    meshes = {n: import_static(os.path.join(src, f"{n}.fbx"), "/Game/Vehicles/AlienBuggy", n) for n in BUGGY_FBX}
    bp, cdo = cdo_of(VEHICLE_BP)
    ch = cdo.get_editor_property("chassis_mesh")
    ch.set_editor_property("static_mesh", meshes["SM_Car_AlienBuggy"])
    sc = ch.get_editor_property("relative_scale3d")
    loc = ch.get_editor_property("relative_location")
    R["values"]["chassis"] = {"scale": str(sc), "location": str(loc)}
    wheel = cdo.get_editor_property("steering_wheel_mesh")
    wheel.set_editor_property("static_mesh", meshes["SM_Car_AlienBuggy_SteeringWheel"])
    wheel.set_editor_property("relative_location", unreal.Vector(*WHEEL_LOCAL))
    wheel.set_editor_property("relative_rotation", unreal.Rotator(0.0, WHEEL_PITCH, 0.0))
    setp(cdo, "steering_wheel_base_rotation", unreal.Rotator(0.0, WHEEL_PITCH, 0.0), "Vehicle")
    pivot = cdo.get_editor_property("driver_pivot")
    pivot.set_editor_property("relative_location", unreal.Vector(*DRIVER_PIVOT))
    dm = cdo.get_editor_property("driver_mesh")
    dm.set_editor_property("relative_location", unreal.Vector(0.0, 0.0, -DRIVER_HIPS_CM / max(float(sc.z), 0.01)))
    dm.set_editor_property("relative_rotation", unreal.Rotator(0.0, 0.0, -90.0))
    dm.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))
    setp(dm, "absolute_scale", True, "driver_mesh")
    # Banco central também para a animação de sair (SeatPoint fica no espaço do esqueleto do carro).
    seat = cdo.get_editor_property("seat_point")
    seat.set_editor_property("relative_location", unreal.Vector(loc.x + SEAT_LOCAL[0] * sc.x, loc.y + SEAT_LOCAL[1] * sc.y,
                                                                loc.z + SEAT_LOCAL[2] * sc.z))
    compile_save(bp)
    log("buggy: chassi sem volante reimportado, volante separado, motorista e SeatPoint no banco central")


# ------------------------------------------------------------------ 8. paredes e 9. ajustes
def walls_and_tuning():
    path = "/Game/Vehicles/SUV/PM_VehicleChassis"
    pm = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "PM_VehicleChassis", "/Game/Vehicles/SUV", unreal.PhysicalMaterial, unreal.PhysicalMaterialFactoryNew())
    setp(pm, "friction", 0.05, "PM")
    setp(pm, "static_friction", 0.05, "PM")
    setp(pm, "restitution", 0.1, "PM")
    setp(pm, "override_friction_combine_mode", True, "PM")
    for enum_name in ("FrictionCombineMode", "EFrictionCombineMode"):
        e = getattr(unreal, enum_name, None)
        if e is not None and hasattr(e, "MIN"):
            setp(pm, "friction_combine_mode", e.MIN, "PM")
            break
    else:
        warn("enum FrictionCombineMode não encontrado: atrito da carroceria combina pela média")
    EAL.save_loaded_asset(pm, only_if_is_dirty=False)
    bp, cdo = cdo_of(VEHICLE_BP)
    setp(cdo, "chassis_phys_material", pm, "Vehicle")
    for k, v in list(NITRO.items()) + list(HANDLING.items()) + list(STABILITY.items()):
        setp(cdo, k, v, "Vehicle")
    setp(cdo, "wall_scrape_enabled", True, "Vehicle")
    compile_save(bp)
    log("PM_VehicleChassis na carroceria; nitro 160 km/h; volante cheio até 50 km/h")


# ------------------------------------------------------------------ 11. teclas do carro
def make_key(name):
    k = unreal.Key()
    try:
        k.import_text(name)
    except Exception:  # noqa: BLE001
        k.set_editor_property("key_name", name)
    return k


def imc_mappings(imc):
    """[(ação, tecla, modificadores, gatilhos)] do IMC (5.8: default_key_mappings.mappings)."""
    try:
        maps = imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
    except Exception:  # noqa: BLE001
        maps = imc.get_editor_property("mappings")
    out = []
    for m in maps:
        a = m.get_editor_property("action")
        out.append((a.get_name() if a else None, str(m.get_editor_property("key").get_editor_property("key_name")),
                    [x.get_class().get_name() for x in (m.get_editor_property("modifiers") or []) if x],
                    [x.get_class().get_name() for x in (m.get_editor_property("triggers") or []) if x]))
    return out


def inputs():
    imc = None
    contexts = []
    try:
        _, pc = cdo_of(PC_BP)
        contexts = [c for c in pc.get_editor_property("vehicle_mapping_contexts") if c]
        imc = contexts[0] if contexts else None
    except Exception as exc:  # noqa: BLE001
        warn(f"vehicle_mapping_contexts: {exc}")
    if imc is None:
        imc = EAL.load_asset(IMC_VEHICLE)
        warn("BP_PlayerController sem vehicle_mapping_contexts: usando IMC_Vehicle_Default (confira no BP)")
    R["values"]["vehicle_imc"] = imc.get_path_name()
    before = imc_mappings(imc)
    R["values"]["keys_before"] = [f"{a}: {k} {mods or ''}{trg or ''}" for a, k, mods, trg in before]
    actions = {}
    for name in VEHICLE_KEYS:
        path = IA_NITRO if name == "IA_Nitro" else f"{IA_DIR}/{name}"
        if not EAL.does_asset_exist(path):
            warn(f"{path} não existe: teclas de {name} puladas")
            continue
        actions[name] = EAL.load_asset(path)
    imc.modify()
    removed, added = [], []
    for name, keys in VEHICLE_KEYS_REMOVE.items():
        ia = actions.get(name)
        if ia is None:
            continue
        have = {k for a, k, _, _ in before if a == name}
        for key in keys:
            if key in have:
                imc.unmap_key(ia, make_key(key))
                removed.append(f"{name}: {key}")
    for name, keys in VEHICLE_KEYS.items():
        ia = actions.get(name)
        if ia is None:
            continue
        current = imc_mappings(imc)
        have = {k for a, k, _, _ in current if a == name}
        used = {k: a for a, k, _, _ in current if a != name}
        for key in keys:
            if key in have:
                continue
            if key in used:
                warn(f"{name}: tecla {key} já é de {used[key]} no {imc.get_name()}; não adicionada")
                continue
            imc.map_key(ia, make_key(key))
            added.append(f"{name}: {key}")
    EAL.save_loaded_asset(imc, only_if_is_dirty=False)
    after = imc_mappings(imc)
    R["values"]["keys_removed"] = removed
    R["values"]["keys_added"] = added
    R["values"]["keys_after"] = [f"{a}: {k} {mods or ''}{trg or ''}" for a, k, mods, trg in after]
    # Conflitos: a mesma tecla em outra ação de qualquer contexto do carro (ex.: nitro + freio no gatilho).
    ours = {k: n for n, keys in VEHICLE_KEYS.items() for k in keys}
    conflicts = []
    for ctx in contexts or [imc]:
        for a, k, mods, _ in (after if ctx == imc else imc_mappings(ctx)):
            if k in ours and a != ours[k]:
                conflicts.append(f"{ctx.get_name()}: {k} também em {a}")
            if a == "IA_Brake" and any("Negate" in m for m in mods):
                conflicts.append(f"{ctx.get_name()}: IA_Brake/{k} com Negate (freio viraria 0)")
    for c in conflicts:
        warn(f"conflito de tecla: {c}")
    R["values"]["key_conflicts"] = conflicts
    for name in ("IA_Brake", "IA_Throttle", "IA_Handbrake", "IA_Reset"):
        ia = actions.get(name)
        if ia is not None:
            R["values"][f"{name}_value_type"] = str(getp(ia, "value_type", name))
            R["values"][f"{name}_triggers"] = [t.get_class().get_name() for t in (getp(ia, "triggers", name) or []) if t]
    # Ações no BP do carro (vazias = o C++ usa teclas reserva S/espaço/R).
    bp, cdo = cdo_of(VEHICLE_BP)
    for prop, name in BP_ACTIONS.items():
        R["values"][f"bp_{prop}_before"] = str(getp(cdo, prop, "Vehicle"))
        if actions.get(name) is not None:
            setp(cdo, prop, actions[name], "Vehicle")
    compile_save(bp)
    log(f"teclas do carro: +{len(added)} -{len(removed)} ({imc.get_name()}); conflitos: {len(conflicts)}")


def main():
    for f in (movement, wheels, visuals, ccd, ramps, driver, buggy, walls_and_tuning, inputs):
        step(f)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        err("save", exc)
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "fix_vehicle_feel.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[vehicle_feel] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
