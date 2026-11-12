"""Reposiciona os atores do greybox SOBRE O CHÃO da pista do template (mapa pequeno).
RODA NO EDITOR com L01_Zombies aberto e o jogo parado:
  py "E:/game/utrazin-game/tools/unreal/relayout_m1_testtrack.py"

v2: em vez de usar as paredes, faz uma varredura de traços verticais para achar onde existe chão
(fora das paredes não há chão). Depois distribui:
  Transição = ponto de chão mais longe do Start; Horda = mais longe de ambos; Resgate perto da horda;
  zumbis a pé perto da transição; zumbis de estrada no meio do caminho.
Relatório: reports/relayout_m1.json
"""
import json
import math
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
REPORT = {"moved": {}, "errors": [], "floor_points": 0}
STEP = 500.0        # 5 m
HALF = 15000.0      # varre ±150 m
MAX_FLOOR_Z = 400.0


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def trace(x, y):
    hit = unreal.SystemLibrary.line_trace_single(world(), unreal.Vector(x, y, 20000), unreal.Vector(x, y, -20000),
                                                 unreal.TraceTypeQuery.ECC_VISIBILITY, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    if not hit:
        return None
    t = hit.to_tuple()
    if not t[0]:
        return None
    return t[5], t[9]  # impact_point, hit_actor


def dist(a, b):
    return math.hypot(a.x - b.x, a.y - b.y)


def main():
    actors = SUB.get_all_level_actors()
    by_label = {a.get_actor_label(): a for a in actors}
    start = by_label["CP_Start"].get_actor_location()
    skip = {"CP_Start", "CP_Transition", "HordeDirector_Final", "Rescue_Victim01"}
    floor = []
    y = start.y - HALF
    while y <= start.y + HALF:
        x = start.x - HALF
        while x <= start.x + HALF:
            r = trace(x, y)
            if r:
                p, actor = r
                label = actor.get_actor_label() if actor else ""
                folder = str(actor.get_folder_path()) if actor else ""
                if p.z < MAX_FLOOR_Z and "Border" not in folder and not label.startswith(("ENM_", "Beacon_")) \
                        and label not in skip and not label.startswith("Horde_"):
                    floor.append(unreal.Vector(p.x, p.y, p.z + 20))
            x += STEP
        y += STEP
    REPORT["floor_points"] = len(floor)
    if len(floor) < 30:
        raise RuntimeError(f"pouco chão encontrado ({len(floor)} pontos)")

    # pontos com margem de 10 m até a borda do chão (evita colar na parede)
    floor_set = {(round(p.x / STEP), round(p.y / STEP)) for p in floor}

    def interior(p, cells=2):
        cx, cy = round(p.x / STEP), round(p.y / STEP)
        return all((cx + dx, cy + dy) in floor_set for dx in range(-cells, cells + 1) for dy in range(-cells, cells + 1))

    def inside_walls(p):
        """Traço horizontal do Start até o ponto: se bater numa parede (pasta Border), está do outro lado."""
        a = unreal.Vector(start.x, start.y, start.z + 150)
        z = unreal.Vector(p.x, p.y, p.z + 150)
        hit = unreal.SystemLibrary.line_trace_single(world(), a, z, unreal.TraceTypeQuery.ECC_VISIBILITY, False, [],
                                                     unreal.DrawDebugTrace.NONE, True)
        if isinstance(hit, tuple):
            hit = hit[-1]
        if not hit:
            return True
        t = hit.to_tuple()
        return not (t[0] and t[9] and "Border" in str(t[9].get_folder_path()))

    inner = [p for p in floor if interior(p) and inside_walls(p)] or floor
    REPORT["inner_points"] = len(inner)

    transition = max(inner, key=lambda p: dist(p, start))
    horde = max(inner, key=lambda p: min(dist(p, start), dist(p, transition)))

    def near(anchor, lo, hi, avoid=(), k=0):
        cands = [p for p in inner if lo <= dist(p, anchor) <= hi and all(dist(p, a) > 600 for a in avoid)]
        cands.sort(key=lambda p: (dist(p, anchor), p.x, p.y))
        return cands[min(k, len(cands) - 1)] if cands else anchor

    used = [start, transition, horde]

    def take(anchor, lo, hi):
        p = near(anchor, lo, hi, used)
        used.append(p)
        return p

    mid = unreal.Vector((start.x + transition.x) / 2, (start.y + transition.y) / 2, start.z)
    layout = {
        "CP_Transition": transition,
        "HordeDirector_Final": horde,
        "Rescue_Victim01": take(horde, 1200, 2500),
        "ENM_Road_Archer_01": take(mid, 1500, 4000), "ENM_Road_Archer_02": take(mid, 1500, 4000),
        "ENM_Road_Melee_01": take(mid, 0, 2500), "ENM_Road_Melee_02": take(start, 2500, 4000),
        "ENM_Foot_Melee_01": take(transition, 1200, 2500), "ENM_Foot_Melee_02": take(transition, 1200, 2500),
        "ENM_Foot_Melee_03": take(transition, 1800, 3500), "ENM_Foot_Archer_01": take(transition, 2500, 4500),
        "ENM_Foot_Gunner_01": take(transition, 2500, 4500), "ENM_Foot_Melee_04": take(transition, 2000, 4000),
        "Horde_Spawn_01": take(horde, 1600, 3500), "Horde_Spawn_02": take(horde, 1600, 3500),
        "Horde_Spawn_03": take(horde, 1600, 3500), "Horde_Spawn_04": take(horde, 1600, 3500),
    }
    for label, loc in layout.items():
        actor = by_label.get(label)
        if not actor:
            REPORT["errors"].append({"label": label, "error": "não encontrado"})
            continue
        actor.set_actor_location(loc, False, False)
        REPORT["moved"][label] = [round(loc.x), round(loc.y), round(loc.z), round(dist(loc, start) / 100)]
    hd = by_label.get("HordeDirector_Final")
    if hd:
        hd.get_editor_property("activation_trigger").set_box_extent(unreal.Vector(600, 600, 400))
    nav = by_label.get("NavBounds_L01")
    if nav:
        xs = [p.x for p in floor]
        ys = [p.y for p in floor]
        nav.set_actor_location(unreal.Vector((min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2, 0), False, False)
        nav.set_actor_scale3d(unreal.Vector((max(xs) - min(xs)) / 200 + 5, (max(ys) - min(ys)) / 200 + 5, 30))
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)  # mapas World Partition: salva também os pacotes de atores externos


try:
    main()
except Exception as exc:  # noqa: BLE001
    REPORT["errors"].append({"label": "main", "error": str(exc), "trace": traceback.format_exc()[-800:]})
    unreal.log_error(f"[relayout_m1] {exc}")
path = os.path.join(REPO, "reports", "relayout_m1.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(REPORT, f, ensure_ascii=False, indent=2)
unreal.log(f"[relayout_m1] chão={REPORT['floor_points']} movidos={len(REPORT['moved'])} erros={len(REPORT['errors'])}")
