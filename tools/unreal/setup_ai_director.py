"""Etapa 3: coloca (ou recoloca) o diretor de IA AJRAIDirector nos mapas. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/setup_ai_director.py"

Mapas, nesta ordem:
  1. o mapa aberto agora (se já foi salvo alguma vez);
  2. /Game/Levels/Test/L_VehicleTest (se existir);
  3. /Game/Levels/L01_ZombieValley/L01_ZombieValley (se existir).
No fim reabre o mapa que estava aberto.

Em cada mapa: apaga TODOS os AJRAIDirector (o deste script tem a tag AIDirectorGen; os de
build_l01.py / build_vehicle_test.py também saem, para ficar um só) e cria um novo com:
  - Subida: melee 8, arqueiro 1, atirador 1;
  - Pico:   melee 10, arqueiro 1,5, atirador 1,5, elite 0,3 (no máximo 1 elite vivo do diretor);
  - os outros ajustes ficam no padrão do C++ (FJRDirectorSettings; A-044 em docs/decisions/ASSUMPTIONS.md).
O AJRAmbientSpawner (obsoleto) continua no L01, mas fica quieto enquanto o diretor estiver ativo.
Se rodar build_l01.py ou build_vehicle_test.py de novo, rode este script depois.
Zonas (acampamento, posto etc.): arraste um "JRDirectorZone" do Place Actors e ajuste a caixa.
Relatório: reports/setup_ai_director.json
"""
import json
import os
import traceback
from datetime import datetime

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TAG = "AIDirectorGen"
EXTRA_MAPS = ["/Game/Levels/Test/L_VehicleTest", "/Game/Levels/L01_ZombieValley/L01_ZombieValley"]
ENEMIES = {
    "melee": "/Game/Enemies/BP_Enemy_ZombieMelee",
    "archer": "/Game/Enemies/BP_Enemy_ZombieArcher",
    "gunner": "/Game/Enemies/BP_Enemy_ZombieGunner",
    "elite": "/Game/Enemies/BP_Enemy_ZombieElite",
}
# (tipo, peso, máximo vivo do diretor; 0 = sem limite). Mude aqui e rode de novo.
BUILD_UP_TABLE = [("melee", 8.0, 0), ("archer", 1.0, 0), ("gunner", 1.0, 0)]
PEAK_TABLE = [("melee", 10.0, 0), ("archer", 1.5, 0), ("gunner", 1.5, 0), ("elite", 0.3, 1)]
R = {"time": datetime.now().isoformat(), "maps": {}, "steps": [], "warnings": [], "errors": []}


# ------------------------------------------------------------------ funções puras (testadas em tests/python)
def package_from_world_path(path):
    """'/Game/Levels/X/L_Map.L_Map' -> '/Game/Levels/X/L_Map'; mapa nunca salvo ('/Temp/...') -> None."""
    if not path:
        return None
    pkg = str(path).split(".")[0]
    if not pkg.startswith("/Game/"):
        return None
    return pkg


def maps_to_process(current, extra, exists):
    """Lista sem repetição: o mapa aberto primeiro (se salvo), depois os extras que existem."""
    out = []
    for m in [current, *extra]:
        if m and m not in out and exists(m):
            out.append(m)
    return out


def resolve_table(spec, available):
    """spec [(tipo, peso, max)] -> [(caminho, peso, max)] só com os tipos cujo asset existe."""
    return [(ENEMIES[k], w, mx) for k, w, mx in spec if k in ENEMIES and available.get(k)]


# ------------------------------------------------------------------ editor
def log(m):
    import unreal
    R["steps"].append(m)
    unreal.log(f"[setup_ai_director] {m}")


def warn(m):
    import unreal
    R["warnings"].append(m)
    unreal.log_warning(f"[setup_ai_director] {m}")


def err(where, exc):
    import unreal
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[setup_ai_director] {where}: {exc}")


def make_entries(rows):
    import unreal
    eal = unreal.EditorAssetLibrary
    out = []
    for path, weight, max_alive in rows:
        cls = eal.load_blueprint_class(path)
        if cls is None:
            warn(f"não consegui carregar {path}")
            continue
        e = unreal.JRDirectorEnemyEntry()
        e.set_editor_property("enemy_class", cls)
        e.set_editor_property("weight", float(weight))
        e.set_editor_property("max_alive", int(max_alive))
        out.append(e)
    return out


def place(map_path, current_loaded):
    import unreal
    actors_ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    eal = unreal.EditorAssetLibrary
    info = {"removed": 0}
    if map_path != current_loaded:
        if not les.load_level(map_path):
            raise RuntimeError(f"não abriu {map_path}")
    actors = actors_ss.get_all_level_actors()

    old = [a for a in actors if isinstance(a, unreal.JRAIDirector) or TAG in [str(t) for t in a.tags]]
    loc = unreal.Vector(0, 0, 500)
    starts = [a for a in actors if isinstance(a, unreal.PlayerStart)]
    if old:
        loc = old[0].get_actor_location()
    elif starts:
        loc = starts[0].get_actor_location() + unreal.Vector(0, 0, 300)
    for a in old:
        actors_ss.destroy_actor(a)
    info["removed"] = len(old)

    available = {k: eal.does_asset_exist(p) for k, p in ENEMIES.items()}
    for k, ok in available.items():
        if not ok:
            warn(f"{map_path}: não existe {ENEMIES[k]} (fica fora do sorteio)")
    build_up = make_entries(resolve_table(BUILD_UP_TABLE, available))
    peak = make_entries(resolve_table(PEAK_TABLE, available))
    if not build_up and not peak:
        raise RuntimeError("nenhum BP_Enemy_* encontrado: o diretor não teria o que criar")

    d = actors_ss.spawn_actor_from_class(unreal.JRAIDirector, loc, unreal.Rotator(0, 0, 0))
    if d is None:
        raise RuntimeError("falha ao criar AJRAIDirector")
    d.set_editor_property("build_up_table", build_up)
    d.set_editor_property("peak_table", peak)
    d.set_editor_property("enemy_table", [])
    d.set_editor_property("tags", [unreal.Name(TAG)])
    d.set_folder_path("Gameplay")
    d.set_actor_label("AIDirector")

    info["build_up"] = len(build_up)
    info["peak"] = len(peak)
    info["ambient_spawners"] = len([a for a in actors if isinstance(a, unreal.JRAmbientSpawner)])
    info["zones"] = len([a for a in actors if isinstance(a, unreal.JRDirectorZone)])
    info["navmesh_volumes"] = len([a for a in actors if isinstance(a, unreal.NavMeshBoundsVolume)])
    if info["navmesh_volumes"] == 0:
        warn(f"{map_path}: sem NavMeshBoundsVolume; o diretor só cria zumbis em cima do navmesh")
    if not les.save_current_level():
        warn(f"{map_path}: save_current_level retornou False")
    R["maps"][map_path] = info
    log(f"{map_path}: diretor criado ({len(old)} antigo(s) removido(s), {len(build_up)} tipos na Subida, "
        f"{len(peak)} no Pico, {info['zones']} zona(s), {info['ambient_spawners']} spawner(s) antigo(s) cedem a vez)")


def main():
    import unreal
    if not hasattr(unreal, "JRAIDirector") or not hasattr(unreal, "JRDirectorZone"):
        raise RuntimeError("classe JRAIDirector/JRDirectorZone não encontrada: compile o C++ (Build.bat) e reabra o editor")
    eal = unreal.EditorAssetLibrary
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = package_from_world_path(world.get_path_name() if world else "")
    if current is None:
        warn("o mapa aberto nunca foi salvo: fica de fora (salve-o e rode de novo para ele ganhar o diretor)")
    maps = maps_to_process(current, EXTRA_MAPS, eal.does_asset_exist)
    for m in EXTRA_MAPS:
        if not eal.does_asset_exist(m):
            warn(f"mapa não existe (pulado): {m}")
    loaded = current
    for m in maps:
        try:
            place(m, loaded)
        except Exception as exc:  # noqa: BLE001
            err(m, exc)
        loaded = m
    if current and loaded != current:
        unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).load_level(current)
        log(f"mapa original reaberto: {current}")


def run():
    import unreal
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        err("main", exc)
    finally:
        os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
        with open(os.path.join(REPO, "reports", "setup_ai_director.json"), "w", encoding="utf-8") as fh:
            json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
        unreal.log(f"[setup_ai_director] fim | mapas: {len(R['maps'])} | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")


# No editor roda direto; fora dele (pytest) só as funções puras são importadas.
# (a pasta tools/unreal também pode ser importada como "unreal" no pytest: confere uma classe do editor)
try:
    import unreal as _unreal_check  # noqa: F401
except ImportError:
    _unreal_check = None
if _unreal_check is not None and hasattr(_unreal_check, "EditorAssetLibrary"):
    run()
