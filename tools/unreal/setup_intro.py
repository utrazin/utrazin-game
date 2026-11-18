"""Abertura do jogo (A-074): põe o AJRIntroDirector na fase 1 e liga o HUD da abertura. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ novo (AJRIntroDirector, AJRIntroHUD):
  py "E:/game/utrazin-game/tools/unreal/setup_intro.py"
Opções (depois do caminho):
  --nave-voo quaternius   a nave em voo usa a SM_Spaceship_FinnTheFrog inteira (padrão: a mesma MRC_NaveResgate)
  --giro-nave 90          giro (yaw) que aponta o nariz da malha da nave para +X (padrão -90; troque se ela voar de lado/de ré)
Relatório: reports/setup_intro.json.

Faz:
 1. abre o mapa L01_ZombieValley;
 2. acha a nave caída (malha com "NaveResgate"), as luzes Fogo_Nave_*, o checkpoint do início e o gatilho
    Historia_Z0_Queda;
 3. calcula onde o herói aparece: ao lado da nave, do lado do acampamento, no chão e sem bater em nada;
 4. cria (ou reaproveita) o ator Abertura_Diretor nesse ponto, virado para o acampamento, e preenche as referências;
 5. põe o AJRIntroHUD no BP_GameMode_L01 (o C++ do GameMode já usa, isto garante o BP);
 6. salva o mapa e o BP.
Rode de novo depois de build_l01.py (ele recria a nave, as luzes e o gatilho; as referências antigas ficam vazias,
e o diretor ainda procura sozinho, mas é melhor preencher).
"""
import json
import math
import os
import sys
import traceback
from datetime import datetime

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
GAME_MODE_BP = "/Game/Core/BP_GameMode_L01"
QUATERNIUS_SHIP = "/Game/Environment/Quaternius/SpaceKit/SM_Spaceship_FinnTheFrog"
TAG = "L01Intro"
LABEL = "Abertura_Diretor"
FOLDER = "L01/Abertura"
SPAWN_ABOVE_GROUND_CM = 110.0   # meia altura da cápsula + folga (igual ao CharacterSpawnHeight do GameMode)

EAL = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[setup_intro] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[setup_intro] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-800:]})
    unreal.log_error(f"[setup_intro] {where}: {exc}")


def arg(name, default=None):
    if name in sys.argv:
        i = sys.argv.index(name)
        if i + 1 < len(sys.argv):
            return sys.argv[i + 1]
    return default


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def ground_z(x, y, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world(), unreal.Vector(x, y, 100000), unreal.Vector(x, y, -100000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    t = hit.to_tuple() if hit else None
    return t[5].z if t and t[0] else None


def blocked(x, y, z, ignore):
    """Algo (além do chão) no espaço do herói? Esfera de 45 cm na altura do peito."""
    try:
        found = unreal.SystemLibrary.sphere_overlap_actors(
            world(), unreal.Vector(x, y, z + 60.0), 45.0,
            [unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY1, unreal.ObjectTypeQuery.OBJECT_TYPE_QUERY2], None, ignore)
    except Exception as exc:  # noqa: BLE001
        warn(f"teste de espaço livre falhou ({exc}); usando o ponto mesmo assim")
        return False
    if isinstance(found, tuple):
        found = found[-1]
    return bool(found)


def mesh_path(a):
    try:
        comp = a.get_component_by_class(unreal.StaticMeshComponent)
        sm = comp.get_editor_property("static_mesh") if comp else None
        return sm.get_path_name() if sm else ""
    except Exception:  # noqa: BLE001
        return ""


def find_scene(actors):
    ship = [a for a in actors if isinstance(a, unreal.StaticMeshActor) and "NaveResgate" in mesh_path(a)]
    lights = [a for a in actors if a.get_actor_label().startswith("Fogo_Nave")]
    start = None
    for a in actors:
        if isinstance(a, unreal.JRCheckpoint):
            try:
                if a.get_editor_property("is_level_start"):
                    start = a
                    break
            except Exception:  # noqa: BLE001
                pass
    trig = [a for a in actors if a.get_actor_label() == "Historia_Z0_Queda"]
    return (ship[0] if ship else None), lights, start, (trig[0] if trig else None)


def hero_mark(ship, start, lights):
    origin, extent = ship.get_actor_bounds(False)
    cx, cy = origin.x, origin.y
    sx, sy = (start.get_actor_location().x, start.get_actor_location().y) if start else (cx + 6000.0, cy)
    base = math.atan2(sy - cy, sx - cx)
    hull = math.hypot(extent.x, extent.y)
    ignore = [ship] + list(lights)
    tried = []
    # do lado do acampamento; se estiver ocupado ou fundo demais, tenta girar e afastar um pouco
    for extra in (0.0, 0.6, 1.2, 2.0):
        for da in (0, 20, -20, 40, -40):
            ang = base + math.radians(da)
            d = hull * 0.8 + 350.0 + extra * 100.0
            x, y = cx + math.cos(ang) * d, cy + math.sin(ang) * d
            gz = ground_z(x, y, ignore)
            tried.append([round(x), round(y), None if gz is None else round(gz)])
            if gz is None:
                continue
            if blocked(x, y, gz + 50.0, ignore):
                continue
            yaw = math.degrees(math.atan2(sy - y, sx - x))
            return x, y, gz, yaw, tried
    warn("não achei um ponto livre ao lado da nave; usando o checkpoint do início")
    loc = start.get_actor_location() if start else origin
    gz = ground_z(loc.x, loc.y, ignore) or loc.z
    return loc.x, loc.y, gz, (start.get_actor_rotation().yaw if start else 0.0), tried


def niagara_from_vehicle():
    """Fumaça/fogo do carro (se setup_car_zombies.py achou algum Niagara) servem para a nave."""
    out = {}
    try:
        da = EAL.load_asset("/Game/Data/DA_Level_L01_Zombies")
        soft = da.get_editor_property("vehicle_class") if da else None
        cls = None
        if soft:
            try:
                cls = unreal.SystemLibrary.load_class_asset_blocking(soft)
            except Exception:  # noqa: BLE001
                cls = None
        if cls:
            cdo = unreal.get_default_object(cls)
            for k in ("smoke_system", "fire_system"):
                try:
                    v = cdo.get_editor_property(k)
                    if v:
                        out[k] = v
                except Exception:  # noqa: BLE001
                    pass
    except Exception as exc:  # noqa: BLE001
        warn(f"Niagara do carro: {exc}")
    return out


def setup_game_mode():
    cls = EAL.load_blueprint_class(GAME_MODE_BP)
    if not cls:
        warn(f"{GAME_MODE_BP} não encontrado (o GameMode C++ já usa o AJRIntroHUD)")
        return
    cdo = unreal.get_default_object(cls)
    cur = cdo.get_editor_property("hud_class")
    R["info"]["hud_before"] = cur.get_name() if cur else None
    if cur != unreal.JRIntroHUD.static_class():
        cdo.set_editor_property("hud_class", unreal.JRIntroHUD.static_class())
        EAL.save_asset(GAME_MODE_BP, only_if_is_dirty=False)
        log(f"BP_GameMode_L01: HUD trocado de {R['info']['hud_before']} para JRIntroHUD")
    else:
        log("BP_GameMode_L01 já usa JRIntroHUD")


def main():
    if getattr(unreal, "JRIntroDirector", None) is None or getattr(unreal, "JRIntroHUD", None) is None:
        raise RuntimeError("classes JRIntroDirector/JRIntroHUD não encontradas: feche o editor, compile o C++ e abra de novo")
    w = world()
    if w is None or w.get_path_name().split(".")[0] != MAP:
        LES.load_level(MAP)
    actors = ACTORS.get_all_level_actors()
    ship, lights, start, trig = find_scene(actors)
    R["info"].update({"ship": ship.get_actor_label() if ship else None, "lights": [a.get_actor_label() for a in lights],
                      "start_checkpoint": start.get_actor_label() if start else None,
                      "story_trigger": trig.get_actor_label() if trig else None})
    if not ship:
        raise RuntimeError("nave caída (malha com 'NaveResgate') não encontrada no mapa: rode o build_l01.py antes")
    if not start:
        warn("checkpoint do início (is_level_start) não encontrado")
    if not trig:
        warn("Historia_Z0_Queda não encontrado: o diretor vai procurar o gatilho mais perto do início")
    if len(lights) == 0:
        warn("luzes Fogo_Nave_* não encontradas (o diretor procura luzes laranja perto da nave)")

    x, y, gz, yaw, tried = hero_mark(ship, start, lights)
    R["info"]["hero_mark"] = [round(x, 1), round(y, 1), round(gz + SPAWN_ABOVE_GROUND_CM, 1), round(yaw, 1)]
    R["info"]["tried"] = tried

    old = [a for a in actors if TAG in [str(t) for t in a.tags] or isinstance(a, unreal.JRIntroDirector)]
    director = old[0] if old else None
    for extra in old[1:]:
        ACTORS.destroy_actor(extra)  # só um diretor por mapa
        log(f"diretor duplicado removido: {extra.get_actor_label()}")
    loc = unreal.Vector(x, y, gz + SPAWN_ABOVE_GROUND_CM)
    rot = unreal.Rotator(0.0, 0.0, yaw)
    if director is None:
        director = ACTORS.spawn_actor_from_class(unreal.JRIntroDirector, loc, rot)
        if director is None:
            raise RuntimeError("falha ao criar o Abertura_Diretor")
        log("Abertura_Diretor criado")
    else:
        director.set_actor_location_and_rotation(loc, rot, False, False)
        log("Abertura_Diretor reaproveitado e reposicionado")
    director.set_editor_property("tags", [unreal.Name(TAG)])
    director.set_folder_path(FOLDER)
    director.set_actor_label(LABEL)

    props = {"crashed_ship": ship, "fire_lights": list(lights)}
    if trig:
        props["first_story_trigger"] = trig
    giro = arg("--giro-nave")
    if giro is not None:
        props["ship_model_yaw_offset"] = float(giro)
    if arg("--nave-voo") == "quaternius":
        sm = EAL.load_asset(QUATERNIUS_SHIP)
        if sm:
            props["flight_ship_mesh"] = sm
            props["flight_ship_scale"] = 2.6
            if giro is None:
                props["ship_model_yaw_offset"] = 0.0
        else:
            warn(f"{QUATERNIUS_SHIP} não existe; a nave em voo fica igual à caída")
    props.update(niagara_from_vehicle())
    for k, v in props.items():
        try:
            director.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"Abertura_Diretor.{k}", exc)
    R["info"]["props"] = {k: (v.get_name() if hasattr(v, "get_name") else
                              [i.get_name() for i in v] if isinstance(v, list) else v) for k, v in props.items()}
    log(f"herói aparece em ({x:.0f}, {y:.0f}, {gz + SPAWN_ABOVE_GROUND_CM:.0f}) olhando {yaw:.0f} graus")

    try:
        setup_game_mode()
    except Exception as exc:  # noqa: BLE001
        err("BP_GameMode_L01", exc)

    LES.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("mapa salvo")


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_intro.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=2, default=str)
    unreal.log(f"[setup_intro] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
