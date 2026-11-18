"""Mapa de teste do carro: /Game/Levels/Test/L_VehicleTest.

RODA NO EDITOR (caixa Cmd), sem Play:
  py "E:/game/utrazin-game/tools/unreal/build_vehicle_test.py"
Depois: o mapa fica aberto; aperte Play. O jogo começa DENTRO do carro (checkpoint de início "Driving").

Monta: chão plano 400 x 400 m (grade), 3 rampas (10, 15 e 20 graus), um salto com vão de 10 m,
paredes (grossa, fina e um canto), reta de 200 m com muro comprido (raspão, y = 4500), 25 zumbis BP_Enemy_ZombieMelee
perto do caminho do carro (3 grupos: beira da pista em x = 5000, multidão em x = 7000 e outra em x = 9500), luz e céu, CP_Start,
PlayerStart, navegação (o chão todo) e o GameMode da Fase 1 (BP_GameMode_L01).
Etapas 2 e 3 (zumbis x carro, diretor de IA):
- 2 barricadas (AJRZombieBarricade): uma na reta do muro (x = 6000, y = 3200) e outra
  depois das paredes (x = 15000, y = -500). Cada uma tem 3 destroços (SM_CarWreck/SM_Roadblock/SM_Barricade,
  ou cubos) na frente e 10 zumbis atrás. A 50+ km/h fura (destroços voam, dano na frente); devagar o carro
  para nos destroços (dê ré e acelere ou desvie). Zumbis colados no carro devagar agarram no capô/laterais:
  vire forte, freie forte ou passe de 60 km/h para derrubar.
- 1 diretor de IA (AJRAIDirector): grupos a cada 10 a 20 s dirigindo (à frente do carro), horda depois.
  Console: "JRDirector" mostra fase/intensidade na tela; "JRDirector horda" começa uma horda agora;
  "JRCarDamage 30" danifica o carro (fumaça < 50%, fogo < 25%, explode no fim).
Tudo com colisão simples (caixas), para separar problema do carro de problema de malha.
Pode rodar de novo: apaga o que ele mesmo criou (tag VehTestGen) e refaz. Relatório: reports/build_vehicle_test.json
"""
import json
import math
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MAP = "/Game/Levels/Test/L_VehicleTest"
TAG = "VehTestGen"
CUBE = "/Engine/BasicShapes/Cube"          # 100 cm, colisão de caixa simples
GRID = "/Engine/EngineMaterials/WorldGridMaterial"
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "counts": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[vehicle_test] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[vehicle_test] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[vehicle_test] {where}: {exc}")


def tagged(a, folder, label):
    a.set_editor_property("tags", [unreal.Name(TAG)])
    a.set_folder_path(folder)
    a.set_actor_label(label)
    return a


def box(label, center, size_cm, pitch=0.0, yaw=0.0, folder="Teste/Pista"):
    """Caixa (cubo escalado) com colisão simples. size_cm = (comprimento X, largura Y, altura Z)."""
    cube = EAL.load_asset(CUBE)
    a = ACTORS.spawn_actor_from_object(cube, unreal.Vector(*center), unreal.Rotator(0.0, pitch, yaw))
    if a is None:
        raise RuntimeError(f"falha ao criar {label}")
    a.set_actor_scale3d(unreal.Vector(size_cm[0] / 100.0, size_cm[1] / 100.0, size_cm[2] / 100.0))
    c = a.static_mesh_component
    c.set_collision_profile_name("BlockAll")
    grid = EAL.load_asset(GRID)
    if grid:
        c.set_material(0, grid)
    return tagged(a, folder, label)


def ramp(label, x0, y, length_cm, deg, width_cm=600.0, thick_cm=40.0, down=False):
    """Rampa: a borda de baixo da face de cima fica em (x0, y, 0) e sobe no sentido +X (ou desce se down)."""
    a = math.radians(deg)
    # centro = borda baixa + meio comprimento ao longo da rampa - meia espessura na normal
    sign = -1.0 if down else 1.0
    pitch = sign * deg
    cx = x0 + (length_cm / 2.0) * math.cos(a) + sign * (thick_cm / 2.0) * math.sin(a)
    cz = (length_cm / 2.0) * math.sin(a) - (thick_cm / 2.0) * math.cos(a)
    if down:
        # desce em +X: a borda alta fica em x0
        cx = x0 + (length_cm / 2.0) * math.cos(a) - (thick_cm / 2.0) * math.sin(a)
    box(label, (cx, y, cz), (length_cm, width_cm, thick_cm), pitch=pitch)
    return length_cm * math.sin(a), x0 + length_cm * math.cos(a)


def spawn_cls(cls, loc, yaw, label, folder, props=None):
    a = ACTORS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
    if a is None:
        raise RuntimeError(f"falha ao spawnar {label}")
    for k, v in (props or {}).items():
        try:
            a.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"{label}.{k}", exc)
    return tagged(a, folder, label)


def open_map():
    if EAL.does_asset_exist(MAP):
        LES.load_level(MAP)
        old = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
        for a in old:
            ACTORS.destroy_actor(a)
        log(f"mapa existente aberto; {len(old)} atores antigos removidos")
    else:
        EAL.make_directory("/Game/Levels/Test")
        try:
            LES.new_level(MAP, False)
        except TypeError:
            LES.new_level(MAP)
        log("mapa novo criado")


def track():
    # chão: topo em z = 0
    box("Chao", (0, 0, -50), (40000, 40000, 100), folder="Teste/Chao")
    # 3 rampas lado a lado (y = -1500, -3000, -4500), começando em x = 3000 (lado -Y)
    for i, deg in enumerate((10, 15, 20)):
        y = -1500 - i * 1500
        h, x_top = ramp(f"Rampa_{deg}graus", 3000, y, 1400, deg)
        # plataforma no topo e rampa de descida para não cair de bico
        box(f"Rampa_{deg}graus_Topo", (x_top + 500, y, h / 2.0), (1000, 600, h))
        ramp(f"Rampa_{deg}graus_Descida", x_top + 1000, y, 1400 * math.sin(math.radians(deg)) / math.sin(math.radians(10)), 10, down=True)
        R["counts"][f"rampa_{deg}_altura_cm"] = round(h)
    # salto: rampa de 15 graus (3,6 m de altura), vão de 10 m, pouso em rampa descendo 12 graus
    y = 2500
    h, x_top = ramp("Salto_Rampa", 3000, y, 1400, 15, width_cm=800)
    land_len = (h - 10.0) / math.sin(math.radians(12))
    ramp("Salto_Pouso", x_top + 1000, y, land_len, 12, width_cm=1200, down=True)
    R["counts"]["salto_altura_cm"] = round(h)
    # paredes: grossa, fina (teste de atravessar em alta velocidade) e um canto
    box("Parede_Grossa", (12000, -2000, 150), (100, 2000, 300), folder="Teste/Paredes")
    box("Parede_Fina", (12000, 1000, 150), (20, 2000, 300), folder="Teste/Paredes")
    box("Canto_A", (9000, 6000, 150), (2000, 100, 300), folder="Teste/Paredes")
    box("Canto_B", (9950, 7000, 150), (100, 2000, 300), folder="Teste/Paredes")
    # reta longa (velocidade máxima) com muro comprido do lado esquerdo: teste de raspão
    box("Muro_Raspao", (8000, 4500, 150), (15000, 100, 300), folder="Teste/Paredes")
    box("Muro_Raspao_Angulo", (17000, 3800, 150), (3000, 100, 300), yaw=-25.0, folder="Teste/Paredes")
    # meio-fio baixo (testa as rodas subindo degrau)
    box("MeioFio", (6000, -6000, 15), (2000, 300, 30), folder="Teste/Pista")
    log("pista: chão, 3 rampas, salto, paredes e meio-fio")


def zombies():
    cls = EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieMelee")
    if cls is None:
        raise RuntimeError("BP_Enemy_ZombieMelee não existe")
    spots = []
    # Grupo 1 (7): beira da pista logo no começo, dos dois lados (correm para o carro passando).
    for i in range(7):
        side = -1 if i % 2 == 0 else 1
        spots.append((4600 + (i // 2) * 300, side * (800 + (i % 3) * 120)))
    # Grupo 2 (10): multidão atravessando a pista (o ponto antigo de teste).
    for i in range(10):
        spots.append((7000 + (i % 5) * 250, -400 + (i // 5) * 300))
    # Grupo 3 (8): segunda multidão mais espalhada, antes das paredes.
    for i in range(8):
        spots.append((9500 + (i % 4) * 300, -700 + (i // 4) * 900 + (i % 2) * 150))
    n = 0
    for x, y in spots:
        n += 1
        spawn_cls(cls, (x, y, 100), 180, f"Zumbi_{n:02d}", "Teste/Inimigos")
    R["counts"]["zumbis"] = n
    log(f"{n} zumbis em 3 grupos perto da pista")


def barricade_props():
    """Destroços da barricada: props da L01 se existirem, senão o cubo da engine."""
    out = []
    for path in ("/Game/Environment/L01/Props/SM_CarWreck", "/Game/Environment/L01/Props/SM_Roadblock",
                 "/Game/Environment/L01/Props/SM_Barricade"):
        if EAL.does_asset_exist(path):
            mesh = EAL.load_asset(path)
            if mesh:
                out.append(mesh)
    if not out:
        warn("sem SM_CarWreck/SM_Roadblock/SM_Barricade: barricada com cubos")
        out.append(EAL.load_asset(CUBE))
    R["counts"]["destrocos_tipos"] = len(out)
    return out


def enemy_classes():
    out = {}
    for key, path in (("melee", "/Game/Enemies/BP_Enemy_ZombieMelee"), ("archer", "/Game/Enemies/BP_Enemy_ZombieArcher"),
                      ("gunner", "/Game/Enemies/BP_Enemy_ZombieGunner"), ("elite", "/Game/Enemies/BP_Enemy_ZombieElite")):
        out[key] = EAL.load_blueprint_class(path) if EAL.does_asset_exist(path) else None
    if out["melee"] is None:
        raise RuntimeError("BP_Enemy_ZombieMelee não existe")
    return out


def director_table(cls):
    """Sorteio do diretor: maioria corpo a corpo, alguns à distância, elite raro."""
    table = []
    for key, weight in (("melee", 8.0), ("archer", 1.0), ("gunner", 1.0), ("elite", 0.3)):
        if cls.get(key) is None:
            continue
        e = unreal.JRDirectorEnemyEntry()
        e.set_editor_property("enemy_class", cls[key])
        e.set_editor_property("weight", weight)
        table.append(e)
    return table


def ai_director():
    cls = enemy_classes()
    spawn_cls(unreal.JRAIDirector, (0, 0, 300), 0, "AIDirector", "Teste/Gameplay",
              {"enemy_table": director_table(cls)})
    log("diretor de IA")


def barricades():
    cls = enemy_classes()
    props = barricade_props()
    # Barricadas: a seta X aponta para de onde o carro vem (o carro nasce em x = 0 olhando para +X).
    for label, loc in (("Barricada_Reta", (6000, 3200, 20)), ("Barricada_Fim", (15000, -500, 20))):
        spawn_cls(unreal.JRZombieBarricade, loc, 180, label, "Teste/Inimigos",
                  {"enemy_classes": [cls["melee"]], "count": 10, "width": 900.0, "depth": 300.0,
                   "prop_meshes": props, "prop_count": 3, "break_speed_kmh": 50.0, "break_damage": 25.0})
    R["counts"]["barricadas"] = 2
    log("2 barricadas com destroços")


def lights():
    sun = spawn_cls(unreal.DirectionalLight, (0, 0, 5000), 0, "Sol", "Teste/Luz")
    sun.set_actor_rotation(unreal.Rotator(0, -45, 30), False)
    lc = sun.light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for k, v in (("intensity", 7.0), ("atmosphere_sun_light", True)):
        try:
            lc.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"sol.{k}: {exc}")
    spawn_cls(unreal.SkyAtmosphere, (0, 0, 0), 0, "Ceu", "Teste/Luz")
    sky = spawn_cls(unreal.SkyLight, (0, 0, 1000), 0, "LuzDoCeu", "Teste/Luz")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    try:
        sky.light_component.set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001
        warn(f"skylight: {exc}")
    spawn_cls(unreal.ExponentialHeightFog, (0, 0, 0), 0, "Neblina", "Teste/Luz")
    log("luz e céu")


def gameplay():
    stage = unreal.JRLevelStage
    spawn_cls(unreal.JRCheckpoint, (0, 0, 20), 0, "CP_Start", "Teste/Gameplay",
              {"checkpoint_id": "Start", "stage_on_respawn": stage.DRIVING, "is_level_start": True})
    spawn_cls(unreal.PlayerStart, (0, 0, 120), 0, "PlayerStart", "Teste/Gameplay")
    # Navegação no chão todo: o diretor cria zumbis até 120 m à frente do carro.
    nav = spawn_cls(unreal.NavMeshBoundsVolume, (0, 0, 0), 0, "NavBounds", "Teste/Gameplay")
    nav.set_actor_scale3d(unreal.Vector(39000 / 200.0, 39000 / 200.0, 2000 / 200.0))
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    for k, v in (("default_game_mode", EAL.load_blueprint_class("/Game/Core/BP_GameMode_L01")),
                 ("kill_z", -3000.0), ("force_no_precomputed_lighting", True)):
        try:
            ws.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"WorldSettings.{k}", exc)
    log("checkpoint de início (no carro), PlayerStart, navegação e GameMode")


def main():
    open_map()
    for f in (track, zombies, ai_director, barricades, lights, gameplay):
        try:
            f()
        except Exception as exc:  # noqa: BLE001
            err(f.__name__, exc)
    LES.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "build_vehicle_test.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[vehicle_test] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
