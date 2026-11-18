"""Assenta no chão os enfeites pequenos que ficaram no ar (A-078). Usado pelo build_l01.py e pelo
fix_l01_props_a078.py. Só mexe na altura (z); nunca em x/y nem na rotação.

Quem entra: StaticMeshActor nas pastas L01/POI/... e L01/Cenario/... com caixa de até 4 m de altura e 6 m de lado
(barris, caixotes, pallets, pneus, sacos, placas, carros batidos...). Construções grandes, terreno, estrada,
vegetação instanciada e interiores (tag L01Interior) ficam fora.
Regra: mede o terreno (só o terreno, pasta L01/Terreno) no centro e nos 4 cantos da caixa; a base do objeto vai
para a MENOR altura medida menos 3 cm (em encosta o lado de cima afunda um pouco, nunca flutua). Só move se a base
estiver a mais de 8 cm do lugar certo.
"""
import unreal

ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
MAX_H_CM = 400.0
MAX_SIDE_CM = 600.0
SINK_CM = 3.0
TOL_CM = 8.0
FOLDERS = ("L01/POI", "L01/Cenario")


def terrain_actors():
    return [a for a in ACTORS.get_all_level_actors() if str(a.get_folder_path()).startswith("L01/Terreno")]


def _ground(world, ignore, x, y):
    hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(x, y, 200000), unreal.Vector(x, y, -200000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    t = hit.to_tuple() if hit else None
    return t[5].z if t and t[0] else None


def candidates():
    out = []
    for a in ACTORS.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        folder = str(a.get_folder_path())
        if not folder.startswith(FOLDERS):
            continue
        if "L01Interior" in [str(t) for t in a.tags]:
            continue
        o, e = a.get_actor_bounds(False)
        if e.z * 2 > MAX_H_CM or max(e.x, e.y) * 2 > MAX_SIDE_CM:
            continue
        out.append(a)
    return out


def snap_all(log=None, dry=False):
    """Devolve a lista [(rótulo, subiu/desceu cm)]. dry=True só mede."""
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    keep = set(x.get_path_name() for x in terrain_actors())
    ignore = [x for x in ACTORS.get_all_level_actors() if x.get_path_name() not in keep]
    moved = []
    for a in candidates():
        o, e = a.get_actor_bounds(False)
        pts = [(o.x, o.y)] + [(o.x + sx * e.x * 0.8, o.y + sy * e.y * 0.8) for sx in (-1, 1) for sy in (-1, 1)]
        zs = [z for z in (_ground(world, ignore, x, y) for x, y in pts) if z is not None]
        if not zs:
            continue
        target_bottom = min(zs) - SINK_CM
        bottom = o.z - e.z
        dz = target_bottom - bottom
        if abs(dz) <= TOL_CM:
            continue
        if not dry:
            loc = a.get_actor_location()
            a.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + dz), False, False)
        moved.append((a.get_actor_label(), round(dz, 1)))
    if log:
        log(f"chão: {len(moved)} enfeites assentados (maior ajuste {max([abs(m[1]) for m in moved] or [0]):.0f} cm)")
    return moved
