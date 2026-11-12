"""Reposiciona os atores do greybox dentro da pista plana do template (mapa pequeno).
RODA NO EDITOR com L01_Zombies aberto e o jogo parado:
  py "E:/game/utrazin-game/tools/unreal/relayout_m1_testtrack.py"

Calcula a área útil a partir das paredes (pasta "Border") e distribui:
  Start (onde está) -> Transition do outro lado da pista -> zumbis a pé perto da transição
  -> horda num canto -> resgate ao lado da horda.
Relatório: reports/relayout_m1.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"moved": {}, "errors": [], "bounds": None}


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def ground(x, y):
    start, end = unreal.Vector(x, y, 50000), unreal.Vector(x, y, -50000)
    hit = unreal.SystemLibrary.line_trace_single(world(), start, end, unreal.TraceTypeQuery.ECC_VISIBILITY, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    if hit:
        t = hit.to_tuple()
        if t[0]:
            return t[5].z + 20
    return 50.0


def main():
    actors = SUB.get_all_level_actors()
    walls = [a for a in actors if "Border" in str(a.get_folder_path())]
    if not walls:
        raise RuntimeError("paredes (pasta Border) não encontradas")
    xs, ys = [], []
    for w in walls:
        origin, extent = w.get_actor_bounds(False)
        xs += [origin.x - extent.x, origin.x + extent.x]
        ys += [origin.y - extent.y, origin.y + extent.y]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    # área interna: menor meia-dimensão, com margem de 15% (paredes têm espessura)
    r = min(max(xs) - min(xs), max(ys) - min(ys)) / 2 * 0.80
    REPORT["bounds"] = {"center": [cx, cy], "usable_radius_m": r / 100}

    by_label = {a.get_actor_label(): a for a in actors}
    start = by_label.get("CP_Start")
    sx, sy = (start.get_actor_location().x, start.get_actor_location().y) if start else (cx + r, cy)
    # direção do centro para o Start; o "outro lado" é o oposto
    dx, dy = sx - cx, sy - cy
    n = max((dx * dx + dy * dy) ** 0.5, 1.0)
    ux, uy = dx / n, dy / n          # aponta para o Start
    px, py = -uy, ux                 # perpendicular

    def P(a, b):
        """a: ao longo de (centro->Start) em frações de r; b: perpendicular."""
        x = cx + (ux * a + px * b) * r
        y = cy + (uy * a + py * b) * r
        return unreal.Vector(x, y, ground(x, y))

    layout = {
        "CP_Transition": P(-0.75, 0.0),
        "ENM_Road_Archer_01": P(0.2, 0.85), "ENM_Road_Archer_02": P(0.2, -0.85),
        "ENM_Road_Melee_01": P(0.55, 0.55), "ENM_Road_Melee_02": P(-0.1, -0.6),
        "ENM_Foot_Melee_01": P(-0.85, 0.3), "ENM_Foot_Melee_02": P(-0.85, -0.3),
        "ENM_Foot_Melee_03": P(-0.6, 0.45), "ENM_Foot_Archer_01": P(-0.95, 0.6),
        "ENM_Foot_Gunner_01": P(-0.95, -0.6), "ENM_Foot_Melee_04": P(-0.6, -0.45),
        "HordeDirector_Final": P(-0.35, -0.8),
        "Horde_Spawn_01": P(-0.9, -0.95), "Horde_Spawn_02": P(0.1, -0.95),
        "Horde_Spawn_03": P(-0.6, -1.0), "Horde_Spawn_04": P(-0.1, -1.0),
        "Rescue_Victim01": P(-0.35, -0.98),
        "NavBounds_L01": unreal.Vector(cx, cy, 0),
    }
    for label, loc in layout.items():
        actor = by_label.get(label)
        if not actor:
            REPORT["errors"].append({"label": label, "error": "não encontrado"})
            continue
        actor.set_actor_location(loc, False, False)
        REPORT["moved"][label] = [round(loc.x), round(loc.y), round(loc.z)]
    hd = by_label.get("HordeDirector_Final")
    if hd:
        hd.get_editor_property("activation_trigger").set_box_extent(unreal.Vector(700, 700, 400))
    nav = by_label.get("NavBounds_L01")
    if nav:
        nav.set_actor_scale3d(unreal.Vector(r / 100 * 1.4, r / 100 * 1.4, 30))
    unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).save_current_level()


try:
    main()
except Exception as exc:  # noqa: BLE001
    REPORT["errors"].append({"label": "main", "error": str(exc), "trace": traceback.format_exc()[-600:]})
    unreal.log_error(f"[relayout_m1] {exc}")
path = os.path.join(REPO, "reports", "relayout_m1.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
unreal.log(f"[relayout_m1] movidos={len(REPORT['moved'])} erros={len(REPORT['errors'])}")
