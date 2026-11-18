"""Mirantes da L01 (A-077): recompensa no alto dos morros, no fim das trilhas do morros v2. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de:
  1. compilar o C++;  2. build_l01.py;  3. scatter_l01.py (com o scatter gerado com --morros-v2: ele grava
  assets/work/levels/L01/l01_mirantes_v2.json e limpa a vegetação em volta do topo e da trilha).
  py "E:/game/utrazin-game/tools/unreal/build_mirantes_l01.py"
Relatório: reports/build_mirantes_l01.json. Depois: Build > Build Paths.

O que coloca em cada topo (tag L01Mirante, pasta L01/Mirantes/<id>; roda de novo = apaga e refaz):
  bau     acampamento abandonado: barraca, barricada, barril, gerador e um baú (munição + kit médico)
  ruina   ruína: pedaços de cerca e ossos em volta de um cristal grande + baú (bandagens + munição)
  antena  antena: torre de rádio pequena, gerador, barril e um baú (munição + Fúria no chão)
  + uma luz quente fraca (dá para ver o topo da estrada à noite) e um gatilho de história só com mensagem.
Tudo com os modelos do usuário (Tripo, /Game/Environment/User); peça que faltar é pulada com aviso.
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
if HERE not in sys.path:
    sys.path.append(HERE)
import l01_user_dressing as U  # noqa: E402

MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
MIRANTES = os.path.join(REPO, "assets", "work", "levels", "L01", "l01_mirantes_v2.json")
TAG = "L01Mirante"
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
R = {"time": datetime.now().isoformat(), "mirantes": {}, "warnings": [], "errors": []}

# peças em volta do centro do topo: (modelo, frente_cm, lado_cm, yaw relativo, escala)
DRESS = {
    "bau": [("CON_Barraca", -380, 160, 200, 1.0), ("PRP_Barricada", 260, -320, 30, 1.0), ("PRP_Barril", -150, -260, 0, 1.0),
            ("PRP_Gerador", -420, -120, 90, 1.0), ("PRP_Barril", -200, -320, 40, 1.0)],
    "ruina": [("MRC_Cristal", -60, 0, 0, 1.6), ("CON_Cerca", 320, 120, 70, 1.0), ("CON_Cerca", -260, 300, 150, 1.0),
              ("CON_Cerca", 120, -340, 10, 1.0), ("PRP_Ossos", 180, 160, 30, 1.0), ("PRP_Ossos", -220, -180, 200, 1.0)],
    "antena": [("CON_TorreRadio", -380, 0, 0, 0.55), ("PRP_Gerador", -160, 260, 180, 1.0), ("PRP_Barril", -100, -300, 0, 1.0),
               ("PRP_Barril", -160, -340, 60, 1.0), ("PRP_Barricada", 300, 220, -40, 1.0)],
}
LOOT = {"bau": {"ammo_inside": 24, "medkits_inside": 1, "bandages_inside": 0},
        "ruina": {"ammo_inside": 18, "medkits_inside": 0, "bandages_inside": 2},
        "antena": {"ammo_inside": 30, "medkits_inside": 0, "bandages_inside": 1}}
MESSAGE = {"bau": "Um acampamento abandonado lá em cima. Dá pra ver o vale inteiro daqui.",
           "ruina": "Ruínas em volta de um cristal enorme... alguém tentou se esconder aqui.",
           "antena": "Uma antena velha no topo. O gerador ainda tem um pouco de combustível."}


def log(m):
    unreal.log(f"[build_mirantes] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[build_mirantes] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "error": str(exc), "trace": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[build_mirantes] {where}: {exc}")


def tagged(a, folder, label):
    a.set_editor_property("tags", [unreal.Name(TAG)])
    a.set_folder_path(folder)
    a.set_actor_label(label)
    return a


def terrain_actors():
    return [a for a in ACTORS.get_all_level_actors() if str(a.get_folder_path()).startswith("L01/Terreno")]


def chest_hinge_cm():
    try:
        h = json.load(open(U.PROCESSED, encoding="utf-8"))["PRP_Bau"]["parts"]["Tampa"]["hinge_m"]
        return [h[0] * 100.0, -h[1] * 100.0, h[2] * 100.0]
    except Exception:  # noqa: BLE001
        return [0.0, -36.1, 32.9]


def skin_chest(a):
    """Baú com a malha do usuário (base + tampa), como no build_l01.py."""
    base_m, lid_m = U.mesh("PRP_Bau_Base"), U.mesh("PRP_Bau_Tampa")
    if base_m is None or lid_m is None:
        return False
    base, lid, pivot = (a.get_editor_property(k) for k in ("base", "lid", "lid_pivot"))
    base.set_static_mesh(base_m)
    base.set_relative_location(unreal.Vector(0, 0, 0), False, False)
    base.set_relative_scale3d(unreal.Vector(1, 1, 1))
    pivot.set_relative_location(unreal.Vector(*chest_hinge_cm()), False, False)
    lid.set_static_mesh(lid_m)
    lid.set_relative_location(unreal.Vector(0, 0, 0), False, False)
    lid.set_relative_scale3d(unreal.Vector(1, 1, 1))
    return True


def build_one(m, tz):
    mid = m["id"]
    kind = m.get("recompensa", "bau")
    folder = f"L01/Mirantes/{mid}"
    cx, cy = m["topo_cm"][0], m["topo_cm"][1]
    # a frente do mirante olha para a estrada: do topo para o começo da trilha
    tr = m.get("trilha_cm") or []
    yaw = math.degrees(math.atan2(tr[0][1] - cy, tr[0][0] - cx)) if tr else 0.0
    info = {"recompensa": kind, "pecas": 0, "faltando": []}
    pts = [U.offset(cx, cy, yaw, f, s) for (_, f, s, _, _) in DRESS.get(kind, [])]
    zs = U.ground_z_batch([(cx, cy)] + pts + [U.offset(cx, cy, yaw, 120, 0)], tz)
    z0 = zs[0] if zs[0] is not None else m["topo_cm"][2]
    for k, (name, f, s, dyaw, sc) in enumerate(DRESS.get(kind, [])):
        sm = U.mesh(name)
        if sm is None:
            info["faltando"].append(name)
            continue
        x, y = pts[k]
        z = zs[1 + k] if zs[1 + k] is not None else z0
        d = U.dims_m(name) or [1, 1, 1]
        sink = min(30.0, 3.0 * max(d[0], d[1]) * sc)
        a = ACTORS.spawn_actor_from_object(sm, unreal.Vector(x, y, z - sink), unreal.Rotator(0, 0, yaw + dyaw))
        if a is None:
            warn(f"{mid}: {name} não nasceu")
            continue
        if sc != 1.0:
            a.set_actor_scale3d(unreal.Vector(sc, sc, sc))
        tagged(a, folder, f"{mid}_{name}_{k:02d}")
        info["pecas"] += 1
    # baú (recompensa), um pouco à frente do centro, virado para quem chega pela trilha
    bx, by = U.offset(cx, cy, yaw, 120, 0)
    bz = zs[-1] if zs[-1] is not None else z0
    ch = ACTORS.spawn_actor_from_class(unreal.JRLootChest, unreal.Vector(bx, by, bz), unreal.Rotator(0, 0, yaw + 180))
    if ch is not None:
        tagged(ch, folder, f"Bau_{mid}")
        props = dict(LOOT.get(kind, LOOT["bau"]))
        try:
            ch.set_editor_property("weapon_inside", unreal.JRWeaponSlot.NONE)
            for k, v in props.items():
                ch.set_editor_property(k, int(v))
        except Exception as exc:  # noqa: BLE001
            err(f"{mid}: baú", exc)
        if not skin_chest(ch):
            info["faltando"].append("PRP_Bau_Base/Tampa (baú fica com o cubo padrão)")
    if kind == "antena":
        try:
            fx, fy = U.offset(cx, cy, yaw, 40, 160)
            p = ACTORS.spawn_actor_from_class(unreal.JRPickup, unreal.Vector(fx, fy, z0 + 40.0))
            tagged(p, folder, f"Pickup_{mid}_Furia")
            p.set_editor_property("type", unreal.JRPickupType.FURY)
            p.set_editor_property("amount", 12.0)
        except Exception as exc:  # noqa: BLE001
            err(f"{mid}: Fúria", exc)
    # luz quente fraca (candelas), visível de longe à noite
    la = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(cx, cy, z0 + 260.0))
    tagged(la, folder, f"{mid}_Luz")
    pc = la.point_light_component
    pc.set_mobility(unreal.ComponentMobility.MOVABLE)
    pc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
    pc.set_editor_property("intensity", 40.0)
    pc.set_editor_property("attenuation_radius", 1400.0)
    pc.set_editor_property("light_color", unreal.Color(r=255, g=170, b=90, a=255))
    pc.set_editor_property("cast_shadows", False)
    # mensagem ao chegar (não troca a tarefa principal)
    try:
        st = ACTORS.spawn_actor_from_class(unreal.JRStoryTrigger, unreal.Vector(cx, cy, z0 + 150.0), unreal.Rotator(0, 0, yaw))
        tagged(st, folder, f"Historia_{mid}")
        st.set_editor_property("message", MESSAGE.get(kind, ""))
        st.set_editor_property("objective_hint", "")
        st.set_editor_property("on_foot_only", True)
        r = float(m.get("raio_cm", 900.0))
        st.get_editor_property("box").set_box_extent(unreal.Vector(r, r, 300.0), True)
    except Exception as exc:  # noqa: BLE001
        err(f"{mid}: gatilho de história", exc)
    info["centro_cm"] = [round(cx), round(cy), round(z0)]
    info["yaw"] = round(yaw, 1)
    if info["faltando"]:
        warn(f"{mid}: faltam {info['faltando']}")
    R["mirantes"][mid] = info


def main():
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    if w is None or w.get_path_name().split(".")[0] != MAP:
        LES.load_level(MAP)
    if not os.path.exists(MIRANTES):
        raise FileNotFoundError("falta l01_mirantes_v2.json (rode o scatter com --morros-v2)")
    data = json.load(open(MIRANTES, encoding="utf-8"))
    old = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for a in old:
        ACTORS.destroy_actor(a)
    log(f"removidos {len(old)} atores da versão anterior")
    tz = terrain_actors()
    if not tz:
        warn("terreno (pasta L01/Terreno) não achado: alturas vêm do JSON")
    for m in data.get("mirantes", []):
        try:
            build_one(m, tz)
        except Exception as exc:  # noqa: BLE001
            err(m.get("id", "?"), exc)
    LES.save_current_level()
    log(f"{len(R['mirantes'])} mirantes. Depois: Build > Build Paths")


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "build_mirantes_l01.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[build_mirantes] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
