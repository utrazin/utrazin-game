"""Monta o greybox da Fase 1 no mapa ABERTO no Editor (deve se chamar L01_Zombies).

RODA DENTRO DO EDITOR UNREAL, com /Game/Levels/L01_Zombies/L01_Zombies aberto:
  py "E:/game/utrazin-game/tools/unreal/setup_m1_level.py" [escala]

escala (opcional, padrão 1.0) encolhe as distâncias: 0.2 cabe na pista plana do template (~120 m).

Coloca, em linha reta a partir do PlayerStart (ajuste depois no Editor):
  Checkpoint Start (0 m) -> inimigos no caminho -> Checkpoint Transition (~400 m)
  -> trecho a pé com zumbis -> Arena da horda (~550 m) -> Resgate (~600 m)
Também: NavMeshBoundsVolume no trecho a pé e GameMode Override = BP_GameMode_L01.
Idempotente: se já houver atores JR no mapa, não duplica. Relatório: reports/setup_m1_level.json
"""
import json
import os
import sys
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"time": datetime.now().isoformat(), "spawned": [], "errors": [], "warnings": []}


def err(where, exc):
    REPORT["errors"].append({"where": where, "error": str(exc), "trace": traceback.format_exc()[-800:]})
    unreal.log_error(f"[setup_m1_level] {where}: {exc}")


def bp_class(path):
    cls = EAL.load_blueprint_class(path)
    if cls is None:
        raise RuntimeError(f"blueprint não encontrado: {path}")
    return cls


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def ground(loc):
    """Projeta o ponto no terreno (trace vertical). Retorna o ponto original se não achar chão."""
    start = unreal.Vector(loc.x, loc.y, loc.z + 50000)
    end = unreal.Vector(loc.x, loc.y, loc.z - 50000)
    try:
        hit = unreal.SystemLibrary.line_trace_single(world(), start, end, unreal.TraceTypeQuery.TRACE_TYPE_QUERY1,
                                                     False, [], unreal.DrawDebugTrace.NONE, True)
        if isinstance(hit, tuple):
            hit = hit[-1] if len(hit) > 1 else hit[0]
        if hit:
            t = hit.to_tuple()
            if t[0]:
                p = t[5]  # impact_point
                return unreal.Vector(p.x, p.y, p.z + 20)
    except Exception as exc:  # noqa: BLE001
        REPORT["warnings"].append(f"ground trace: {exc}")
    return loc


def spawn(cls, loc, rot, label, props=None, snap=True):
    actor = ACTORS.spawn_actor_from_class(cls, ground(loc) if snap else loc, rot)
    if actor is None:
        raise RuntimeError(f"falha ao spawnar {label}")
    actor.set_actor_label(label)
    for k, v in (props or {}).items():
        try:
            actor.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"{label}.{k}", exc)
    REPORT["spawned"].append(label)
    return actor


def main():
    level_name = world().get_name()
    if level_name != "L01_Zombies":
        raise RuntimeError(f"abra o mapa L01_Zombies antes (mapa atual: {level_name}); nada foi alterado")
    existing = [a for a in ACTORS.get_all_level_actors() if isinstance(a, (unreal.JRCheckpoint, unreal.JRHordeDirector))]
    if existing:
        raise RuntimeError("o mapa já tem checkpoints/horda JR; nada foi duplicado")

    starts = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.PlayerStart)]
    if starts:
        origin = starts[0].get_actor_location()
        yaw = starts[0].get_actor_rotation().yaw
    else:
        origin, yaw = unreal.Vector(0, 0, 200), 0.0
        REPORT["warnings"].append("sem PlayerStart: usando a origem")
    rot = unreal.Rotator(0, 0, yaw)
    fwd = rot.get_forward_vector()
    right = rot.get_right_vector()

    scale = float(sys.argv[1]) if len(sys.argv) > 1 else 1.0
    REPORT["scale"] = scale

    def at(forward_m, right_m=0.0, up=0.0):
        return origin + fwd * (forward_m * 100 * scale) + right * (right_m * 100 * max(scale, 0.4)) + unreal.Vector(0, 0, up)

    stage = unreal.JRLevelStage
    spawn(unreal.JRCheckpoint, at(0), rot, "CP_Start",
          {"checkpoint_id": "Start", "stage_on_respawn": stage.DRIVING, "is_level_start": True})
    spawn(unreal.JRCheckpoint, at(400), rot, "CP_Transition",
          {"checkpoint_id": "Transition", "stage_on_respawn": stage.ON_FOOT, "is_vehicle_transition": True})

    melee = bp_class("/Game/Enemies/BP_Enemy_ZombieMelee")
    archer = bp_class("/Game/Enemies/BP_Enemy_ZombieArcher")
    gunner = bp_class("/Game/Enemies/BP_Enemy_ZombieGunner")

    # Trecho de carro: arqueiros na beira da estrada e zumbis no caminho (podem ser atropelados)
    spawn(archer, at(150, 25), rot, "ENM_Road_Archer_01")
    spawn(archer, at(280, -30), rot, "ENM_Road_Archer_02")
    spawn(melee, at(220, 3), rot, "ENM_Road_Melee_01")
    spawn(melee, at(330, -4), rot, "ENM_Road_Melee_02")

    # Trecho a pé: 3 encontros escalonados
    spawn(melee, at(450, 5), rot, "ENM_Foot_Melee_01")
    spawn(melee, at(455, -5), rot, "ENM_Foot_Melee_02")
    spawn(melee, at(490, 8), rot, "ENM_Foot_Melee_03")
    spawn(archer, at(495, -15), rot, "ENM_Foot_Archer_01")
    spawn(gunner, at(520, 12), rot, "ENM_Foot_Gunner_01")
    spawn(melee, at(525, -6), rot, "ENM_Foot_Melee_04")

    # Arena da horda
    points = []
    for i, (f, r) in enumerate(((575, 25), (575, -25), (600, 30), (600, -30))):
        points.append(spawn(unreal.TargetPoint, at(f, r), rot, f"Horde_Spawn_{i + 1:02d}"))
    waves = []
    for cls, count, interval in ((melee, 6, 0.8), (melee, 8, 0.6), (gunner, 3, 1.5), (melee, 10, 0.5)):
        w = unreal.JRWave()
        w.set_editor_property("enemy_class", cls)
        w.set_editor_property("count", count)
        w.set_editor_property("spawn_interval", interval)
        waves.append(w)
    spawn(unreal.JRHordeDirector, at(560), rot, "HordeDirector_Final",
          {"waves": waves, "spawn_points": points, "is_final_horde": True, "min_spawn_distance": 1500.0, "max_alive": 30})

    # Resgate
    rescue = spawn(unreal.JRRescueTarget, at(610), unreal.Rotator(0, 0, yaw + 180), "Rescue_Victim01",
                   {"rescue_id": "Victim01"})
    try:
        cage = rescue.get_editor_property("cage_mesh")
        cage.set_static_mesh(unreal.EditorAssetLibrary.load_asset("/Engine/BasicShapes/Cube"))
        cage.set_relative_scale3d(unreal.Vector(2.0, 2.0, 2.5))
        cage.set_relative_location(unreal.Vector(0, 0, 125), False, False)
        victim = rescue.get_editor_property("victim_mesh")
        victim.set_skeletal_mesh_asset(unreal.EditorAssetLibrary.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"))
        # Placeholder: a "cela" é um cubo; o jogador interage com ele no estágio Rescue.
    except Exception as exc:  # noqa: BLE001
        err("Rescue_Victim01.meshes", exc)

    # Navegação para a IA no trecho a pé + estrada
    nav = spawn(unreal.NavMeshBoundsVolume, at(330, 0, 0), rot, "NavBounds_L01", snap=False)
    nav.set_actor_scale3d(unreal.Vector(400.0 * scale + 20, 60.0, 40.0))  # ~800 m x 120 m x 80 m (pincel base 200 uu)

    # GameMode da fase
    try:
        ws = world().get_world_settings()
        ws.set_editor_property("default_game_mode", bp_class("/Game/Core/BP_GameMode_L01"))
    except Exception as exc:  # noqa: BLE001
        err("WorldSettings.default_game_mode", exc)

    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)  # mapas World Partition: salva também os pacotes de atores externos


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    out = os.path.join(REPO, "reports", "setup_m1_level.json")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=2)
    unreal.log(f"[setup_m1_level] atores={len(REPORT['spawned'])} erros={len(REPORT['errors'])}. Relatório: {out}")
