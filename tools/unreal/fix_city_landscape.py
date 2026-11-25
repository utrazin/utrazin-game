"""[A-095/A-096] Confere (e conserta o que der) o Landscape da cidade e tira o que foi importado sem querer na arena.

RODA NO EDITOR (caixa Cmd, sem Play):
    py "E:/game/utrazin-game/tools/unreal/fix_city_landscape.py"

O que faz:
  1. L_Arena_F1: apaga qualquer Landscape (a arena nunca teve; um foi importado lá por engano às 20:21).
  2. L_Cidade: mede o Landscape (componentes, quads, posição, escala) e compara com a planta (city_v5: 504 x 504 quads).
     - Tamanho certo mas posição/escala erradas: corrige (origem -tamanho/2, escala 100).
     - Tamanho errado (ex.: o de 1008 m da v4): APAGA o Landscape velho, salva e para com os números do import novo.
     - Mais de um Landscape: mantém o de tamanho certo e apaga os outros.
  3. Se ficou tudo certo: roda setup_city_landscape.py e dress_city_v4.py em seguida (a cidade é reposta em cima do chão).
"""
import json
import os
import runpy
import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
CITY_MAP = "/Game/Levels/Remap/L_Cidade"
ARENA_MAP = "/Game/Levels/Remap/L_Arena_F1"
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
WORK = os.path.join(REPO, "assets", "work", "city_v6")  # [A-098]
if not os.path.isfile(os.path.join(WORK, "city_layout.json")):
    WORK = os.path.join(REPO, "assets", "work", "city_v5")
if not os.path.isfile(os.path.join(WORK, "city_layout.json")):
    WORK = os.path.join(REPO, "assets", "work", "city_v4")
with open(os.path.join(WORK, "city_layout.json"), encoding="utf-8") as _fh:
    _LAND = json.load(_fh)["landscape"]
QUADS = int(_LAND["res"]) - 1
HALF_CM = QUADS * 100.0 / 2.0
LOC = unreal.Vector(-HALF_CM, -HALF_CM, 0.0)
SCALE = unreal.Vector(100.0, 100.0, 100.0)
COMPONENTS = QUADS // 63


def log(msg):
    unreal.log(f"[fix_land] {msg}")


def warn(msg):
    unreal.log_warning(f"[fix_land] {msg}")


def landscapes():
    return [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.LandscapeProxy)]


def measure(land):
    comps = land.get_components_by_class(unreal.LandscapeComponent)
    cols = land.get_components_by_class(unreal.LandscapeHeightfieldCollisionComponent)
    origin, ext = land.get_actor_bounds(False)
    sc = land.get_actor_scale3d()
    loc = land.get_actor_location()
    qx = round(ext.x * 2.0 / max(sc.x, 0.001))
    qy = round(ext.y * 2.0 / max(sc.y, 0.001))
    log(f"{land.get_actor_label()}: {len(comps)} componentes, {len(cols)} de colisão, {qx} x {qy} quads, "
        f"pos ({loc.x:.0f}, {loc.y:.0f}, {loc.z:.0f}), escala ({sc.x:.1f}, {sc.y:.1f}, {sc.z:.1f}), "
        f"centro ({origin.x:.0f}, {origin.y:.0f})")
    return {"comps": len(comps), "cols": len(cols), "qx": qx, "qy": qy, "loc": loc, "sc": sc}


def near(a, b, tol):
    return abs(a.x - b.x) <= tol and abs(a.y - b.y) <= tol and abs(a.z - b.z) <= tol


def height_mismatch(land):
    """Maior diferença (cm) entre o chão medido por traço e o city_height.r16, em 25 pontos dentro da muralha."""
    from array import array
    h = array("H")
    with open(os.path.join(WORK, "city_height.r16"), "rb") as fh:
        h.frombytes(fh.read())
    res = QUADS + 1
    world = unreal.EditorLevelLibrary.get_editor_world()
    worst = 0.0
    hits = 0
    for gx in range(-2, 3):
        for gy in range(-2, 3):
            X, Y = gx * 3700.0 + 900.0, gy * 3700.0 - 700.0
            fx, fy = (X + HALF_CM) / 100.0, (Y + HALF_CM) / 100.0
            ix, iy = int(round(fx)), int(round(fy))
            want = (h[iy * res + ix] - 32768.0) * 100.0 / 128.0
            hit = unreal.SystemLibrary.line_trace_single(world, unreal.Vector(X, Y, 30000.0), unreal.Vector(X, Y, -30000.0),
                                                         unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [], unreal.DrawDebugTrace.NONE, True)
            if not hit:
                continue
            t = hit.to_tuple()
            actor = t[9] if len(t) > 9 else None  # (blocking, overlap, time, dist, location, impact, normal, impact_normal, phys_mat, actor, ...)
            if actor is not None and not isinstance(actor, unreal.LandscapeProxy):
                continue  # bateu numa casa
            hits += 1
            worst = max(worst, abs(t[4].z - want))
    log(f"relevo: {hits} pontos medidos, maior diferença para a planta {worst / 100:.2f} m")
    return worst if hits >= 8 else None


def clean_arena():
    if not LES.load_level(ARENA_MAP):
        warn(f"não abriu {ARENA_MAP}")
        return
    found = landscapes()
    for land in found:
        measure(land)
        log(f"apagando {land.get_actor_label()} da arena (importado por engano)")
        ACTORS.destroy_actor(land)
    if found:
        LES.save_current_level()
        log("L_Arena_F1 salva sem Landscape")
    else:
        log("arena sem Landscape (ok)")


def fix_city():
    if not LES.load_level(CITY_MAP):
        raise RuntimeError(f"não abriu {CITY_MAP}")
    found = landscapes()
    if not found:
        raise RuntimeError("não há Landscape na L_Cidade: importe city_height.png (docs/design/CIDADE_V4.md)")
    info = [(land, measure(land)) for land in found]
    good = [(l, m) for l, m in info if m["qx"] == QUADS and m["qy"] == QUADS]
    if not good:
        m = info[0][1]
        for land, _ in info:
            ACTORS.destroy_actor(land)
        LES.save_current_level()
        raise RuntimeError(
            f"o Landscape tinha {m['qx']} x {m['qy']} quads e a planta pede {QUADS} x {QUADS}: o velho foi APAGADO. "
            f"Importe o novo: Landscape (Shift+2) > Manage > New > Import from File, arquivo {os.path.join(WORK, 'city_height.png')}, "
            f"Location {-HALF_CM:.0f}, {-HALF_CM:.0f}, 0 | Scale 100, 100, 100 | Section Size 63x63 | Sections Per Component 1x1 | "
            f"Number of Components {COMPONENTS} x {COMPONENTS} (resolução {QUADS + 1} x {QUADS + 1}) | Import | Shift+1 | Ctrl+S. "
            "Depois rode este script de novo.")
    keep, m = good[0]
    for land, _ in info:
        if land != keep:
            log(f"apagando Landscape a mais: {land.get_actor_label()}")
            ACTORS.destroy_actor(land)
    if not near(m["loc"], LOC, 5.0) or not near(m["sc"], SCALE, 0.05):
        keep.set_actor_scale3d(SCALE)
        keep.set_actor_location(LOC, False, False)
        log(f"posição/escala corrigidas para {-HALF_CM:.0f},{-HALF_CM:.0f},0 / 100,100,100")
        measure(keep)
    else:
        log("posição e escala certas")
    # [A-098] mesmo tamanho não quer dizer mesmo relevo (v5 -> v6): mede o chão com traços e compara com o r16
    bad = height_mismatch(keep)
    if bad is not None and bad > 60.0:
        ACTORS.destroy_actor(keep)
        LES.save_current_level()
        raise RuntimeError(
            f"o relevo do Landscape é de outra planta (diferença de {bad / 100:.1f} m): o velho foi APAGADO. "
            f"Importe o novo: Landscape (Shift+2) > Manage > New > Import from File, arquivo {os.path.join(WORK, 'city_height.png')}, "
            f"Location {-HALF_CM:.0f}, {-HALF_CM:.0f}, 0 | Scale 100, 100, 100 | Section Size 63x63 | Sections Per Component 1x1 | "
            f"Number of Components {COMPONENTS} x {COMPONENTS} | Import | Shift+1 | Ctrl+S. Depois rode este script de novo.")
    if m["cols"] == 0:
        warn("Landscape sem componentes de colisão: o personagem atravessa o chão. Reimporte (não desligue Collision).")
    LES.save_current_level()
    return True


def main():
    clean_arena()
    fix_city()
    for name in ("setup_city_landscape.py", "dress_city_v6.py" if "city_v6" in WORK else "dress_city_v4.py", "build_interiors_vila.py"):
        log(f"rodando {name}")
        runpy.run_path(os.path.join(HERE, name), run_name="__main__")
    log("fim: agora Build > Build Paths, Ctrl+S e Play")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        unreal.log_error(f"[fix_land] {e}")
        raise
