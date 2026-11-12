"""Aplica as marcas feitas com mark_here.py (rode com o jogo PARADO e L01_Zombies aberto):
  py "E:/game/utrazin-game/tools/unreal/apply_marks.py"

transicao -> CP_Transition + zumbis "ENM_Foot_*" ao redor (10 a 25 m)
horda     -> HordeDirector_Final + 4 pontos de nascimento ao redor (15 a 25 m)
resgate   -> Rescue_Victim01
Os faróis coloridos são recolocados em cima de cada ponto. Só usa pontos com chão e sem parede no meio.
"""
import json
import math
import os

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SUB = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
with open(os.path.join(REPO, "reports", "marks.json"), encoding="utf-8") as f:
    MARKS = json.load(f)


def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def first_hit(a, b):
    hit = unreal.SystemLibrary.line_trace_single(world(), a, b, unreal.TraceTypeQuery.ECC_VISIBILITY, False, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    if not hit:
        return None
    t = hit.to_tuple()
    return t if t[0] else None


def floor_at(x, y, ref_z):
    t = first_hit(unreal.Vector(x, y, ref_z + 800), unreal.Vector(x, y, ref_z - 800))
    return t[5].z if t else None


def ring(center, r_min, r_max, count):
    """Pontos ao redor do centro com chão na mesma altura e linha livre a partir do centro."""
    out = []
    for r in (r_min, (r_min + r_max) / 2, r_max):
        for i in range(12):
            ang = 2 * math.pi * i / 12 + r  # desfasa por raio
            x, y = center.x + math.cos(ang) * r, center.y + math.sin(ang) * r
            z = floor_at(x, y, center.z)
            if z is None or abs(z - (center.z - 90)) > 250:
                continue
            blocked = first_hit(unreal.Vector(center.x, center.y, center.z + 50), unreal.Vector(x, y, z + 140))
            if blocked:
                continue
            p = unreal.Vector(x, y, z + 20)
            if all(math.hypot(p.x - q.x, p.y - q.y) > 400 for q in out):
                out.append(p)
            if len(out) >= count:
                return out
    return out


def main():
    by_label = {a.get_actor_label(): a for a in SUB.get_all_level_actors()}

    def move(label, loc, extra_z=0.0):
        a = by_label.get(label)
        if a:
            a.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z + extra_z), False, False)
            b = by_label.get(f"Beacon_{label}")
            if b:
                b.set_actor_location(unreal.Vector(loc.x, loc.y, loc.z), False, False)

    def ground_of(mark):
        v = unreal.Vector(*mark)
        z = floor_at(v.x, v.y, v.z)
        return unreal.Vector(v.x, v.y, (z if z is not None else v.z - 90) + 20), v

    if "transicao" in MARKS:
        g, raw = ground_of(MARKS["transicao"])
        move("CP_Transition", g)
        foot = sorted(l for l in by_label if l.startswith("ENM_Foot_"))
        for label, p in zip(foot, ring(raw, 1000, 2500, len(foot))):
            move(label, p, 100)
        # zumbis de estrada: no meio do caminho entre o início e a transição
        start = by_label["CP_Start"].get_actor_location()
        mid = unreal.Vector((start.x + raw.x) / 2, (start.y + raw.y) / 2, raw.z)
        road = sorted(l for l in by_label if l.startswith("ENM_Road_"))
        for label, p in zip(road, ring(mid, 500, 1500, len(road))):
            move(label, p, 100)
    if "horda" in MARKS:
        g, raw = ground_of(MARKS["horda"])
        move("HordeDirector_Final", g)
        spawns = sorted(l for l in by_label if l.startswith("Horde_Spawn_"))
        for label, p in zip(spawns, ring(raw, 1500, 2500, len(spawns))):
            move(label, p)
    if "resgate" in MARKS:
        g, _ = ground_of(MARKS["resgate"])
        move("Rescue_Victim01", g)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)  # mapas World Partition: salva também os pacotes de atores externos
    unreal.log(f"[apply_marks] aplicado: {sorted(MARKS)}")


main()
