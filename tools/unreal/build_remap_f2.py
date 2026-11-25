"""[Remap F2] Base da arena procedural (docs/design/REMAP_CIDADE_ARENA.md, etapa F2).

RODA NO EDITOR (caixa Cmd, modo Python), sem Play, DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/build_remap_f2.py"
Opções (no fim da linha): --sem-salvar (só monta, não salva)

Deixa /Game/Levels/Remap/L_Arena_F1 só com a base; o resto (coberturas, muro, posto, pontos, baús) o
AJRArenaGenerator monta sozinho no BeginPlay a partir de uma semente:
- tira tudo o que o build_remap_f1.py tinha posto na arena (tag RemapF1) e o que este script pôs antes (tag RemapF2);
- chão grande (240 x 240 m), sol, céu, luz do céu e neblina;
- NavMeshBoundsVolume de 200 x 200 m (a arena vai até 160 m e o centro livre pode ficar até 2 células fora do meio),
  RecastNavMesh (se faltar) e RebuildNavigation;
- PlayerStart, AJRArenaGenerator e AJRArenaDirector no centro (o gerador alinha o centro livre 3 x 3 com ele);
- World Settings com AJRRemapGameMode.
Testar sementes no Play: console "jr.Arena.Seed 1234" (0 = sorteia), "jr.Arena.Shape 0..4" (-1 = sorteia),
depois "RestartLevel". Relatório: reports/build_remap_f2.json
"""
import json
import os
import sys
import traceback
from datetime import datetime

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
ARENA_MAP = "/Game/Levels/Remap/L_Arena_F1"
OLD_TAGS = ("RemapF1", "RemapF2")
TAG = "RemapF2"
CUBE = "/Engine/BasicShapes/Cube"
GRID = "/Engine/EngineMaterials/WorldGridMaterial"
FLOOR_M = 240.0
NAV_M = 200.0
NAV_HEIGHT_M = 20.0
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": []}


# ------------------------------------------------------------------ funções puras (testadas em tests/python)

def nav_bounds_scale(size_m, height_m):
    """Escala do NavMeshBoundsVolume (o pincel padrão tem 200 uu de lado) para cobrir size_m x size_m x height_m."""
    if size_m <= 0 or height_m <= 0:
        raise ValueError("tamanho inválido")
    return (size_m * 100.0 / 200.0, size_m * 100.0 / 200.0, height_m * 100.0 / 200.0)


def floor_box(size_m, thickness_cm=100.0):
    """Centro e tamanho (cm) do chão: topo em z = 0."""
    s = size_m * 100.0
    return (0.0, 0.0, -thickness_cm / 2.0), (s, s, thickness_cm)


def arena_fits_nav(max_arena_m, cell_m, start_offset_cells, nav_m):
    """A arena (até max_arena_m, centro deslocado até start_offset_cells) cabe no volume de navegação?"""
    half_needed = max_arena_m / 2.0 + start_offset_cells * cell_m
    return half_needed <= nav_m / 2.0


def is_old_actor(tags):
    return any(t in OLD_TAGS for t in tags)


# ------------------------------------------------------------------ editor

def log(m):
    R["steps"].append(m)
    import unreal
    unreal.log(f"[remap_f2] {m}")


def warn(m):
    R["warnings"].append(m)
    import unreal
    unreal.log_warning(f"[remap_f2] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    import unreal
    unreal.log_error(f"[remap_f2] {where}: {exc}")


def build():
    import unreal
    eal = unreal.EditorAssetLibrary
    actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    def tagged(a, folder, label):
        a.set_editor_property("tags", [unreal.Name(TAG)])
        a.set_folder_path(folder)
        a.set_actor_label(label)
        return a

    def spawn_cls(cls, loc, yaw, label, folder):
        a = actors.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
        if a is None:
            raise RuntimeError(f"falha ao spawnar {label}")
        return tagged(a, folder, label)

    if not hasattr(unreal, "JRArenaGenerator"):
        raise RuntimeError("classe JRArenaGenerator não existe: compile o C++ (compilar_remap.bat) antes")

    if eal.does_asset_exist(ARENA_MAP):
        les.load_level(ARENA_MAP)
    else:
        eal.make_directory(ARENA_MAP.rsplit("/", 1)[0])
        try:
            les.new_level(ARENA_MAP, False)
        except TypeError:
            les.new_level(ARENA_MAP)
        log(f"{ARENA_MAP}: mapa novo")

    old = [a for a in actors.get_all_level_actors() if is_old_actor([str(t) for t in a.tags])]
    # diretor/gerador soltos (sem tag) também saem: só pode haver um de cada
    old += [a for a in actors.get_all_level_actors()
            if isinstance(a, (unreal.JRArenaDirector, unreal.JRArenaGenerator)) and a not in old]
    for a in old:
        actors.destroy_actor(a)
    log(f"{len(old)} atores antigos removidos (F1 e F2)")

    # chão
    center, size = floor_box(FLOOR_M)
    cube = eal.load_asset(CUBE)
    floor = actors.spawn_actor_from_object(cube, unreal.Vector(*center), unreal.Rotator(0, 0, 0))
    floor.set_actor_scale3d(unreal.Vector(size[0] / 100.0, size[1] / 100.0, size[2] / 100.0))
    floor.static_mesh_component.set_collision_profile_name("BlockAll")
    grid = eal.load_asset(GRID)
    if grid:
        floor.static_mesh_component.set_material(0, grid)
    tagged(floor, "Remap/Chao", "Chao")

    # luz e céu (escuro de propósito, os postes do gerador iluminam)
    sun = spawn_cls(unreal.DirectionalLight, (0, 0, 5000), 0, "Sol", "Remap/Luz")
    sun.set_actor_rotation(unreal.Rotator(0, -35.0, 200.0), False)
    lc = sun.light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for k, v in (("intensity", 2.5), ("atmosphere_sun_light", True)):
        try:
            lc.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"sol.{k}: {exc}")
    spawn_cls(unreal.SkyAtmosphere, (0, 0, 0), 0, "Ceu", "Remap/Luz")
    sky = spawn_cls(unreal.SkyLight, (0, 0, 1000), 0, "LuzDoCeu", "Remap/Luz")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    try:
        sky.light_component.set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001
        warn(f"skylight: {exc}")
    fog = spawn_cls(unreal.ExponentialHeightFog, (0, 0, 0), 0, "Neblina", "Remap/Luz")
    try:
        fog.component.set_editor_property("fog_density", 0.015)
    except Exception as exc:  # noqa: BLE001
        warn(f"neblina: {exc}")

    # jogo: gerador e PlayerStart no mesmo ponto (o centro livre 3 x 3 da planta fica aqui)
    spawn_cls(unreal.JRArenaGenerator, (0, 0, 0), 0, "ArenaGenerator", "Remap/Gameplay")
    spawn_cls(unreal.JRArenaDirector, (0, 0, 60), 0, "ArenaDirector", "Remap/Gameplay")
    spawn_cls(unreal.PlayerStart, (0, 0, 120), 90.0, "PlayerStart", "Remap/Gameplay")

    nav = spawn_cls(unreal.NavMeshBoundsVolume, (0, 0, 500), 0, "NavBounds", "Remap/Gameplay")
    nav.set_actor_scale3d(unreal.Vector(*nav_bounds_scale(NAV_M, NAV_HEIGHT_M)))
    if not [x for x in actors.get_all_level_actors() if isinstance(x, unreal.RecastNavMesh)]:
        try:
            actors.spawn_actor_from_class(unreal.RecastNavMesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
            log("RecastNavMesh criado")
        except Exception as exc:  # noqa: BLE001
            warn(f"RecastNavMesh: {exc} (use Build > Build Paths)")

    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    for k, v in (("default_game_mode", unreal.JRRemapGameMode.static_class()),
                 ("kill_z", -10000.0)  # [A-098] cômodos a -45 m, ("force_no_precomputed_lighting", True)):
        try:
            ws.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"WorldSettings.{k}", exc)
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")
    except Exception as exc:  # noqa: BLE001
        warn(f"RebuildNavigation: {exc} (use Build > Build Paths)")
    log(f"arena base: chão {FLOOR_M:.0f} m, navegação {NAV_M:.0f} m, gerador + diretor + PlayerStart no centro")

    if "--sem-salvar" not in sys.argv[1:]:
        les.save_current_level()
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("salvo")


def main():
    try:
        build()
    except Exception as exc:  # noqa: BLE001
        err("build", exc)
    finally:
        os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
        with open(os.path.join(REPO, "reports", "build_remap_f2.json"), "w", encoding="utf-8") as fh:
            json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
        try:
            import unreal
            unreal.log(f"[remap_f2] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
        except ImportError:
            pass
    return 1 if R["errors"] else 0


def _in_unreal():
    try:
        import unreal  # noqa: F401
        return True
    except ImportError:
        return False


if __name__ == "__main__":
    if "--help" in sys.argv[1:]:
        print(__doc__)
    else:
        CODE = main()
        if not _in_unreal():
            sys.exit(CODE)
