"""Áudio do jogo (Etapa 10, A-061): importa os WAVs, cria atenuações, classes de som e o DA_SoundBank. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd do Output Log, sem Play), DEPOIS de compilar o C++ novo (Audio/JRSoundBank,
Audio/JRAudioSubsystem, Audio/JRAudio):
  py "E:/game/utrazin-game/tools/unreal/setup_audio.py"
Relatório: reports/setup_audio.json

Antes (já vem pronto no repositório): python tools/pipeline/gen_game_audio.py  -> assets/work/audio/<grupo>/*.wav

O que faz (cada parte independente):
 1. Importa assets/work/audio/{vehicle,zombie,hero,world,ambience,ui,music}/*.wav para /Game/Audio/<Grupo>/
    (os sons das armas continuam em /Game/Audio/SFX/Weapons pelo setup_combat_feel.py). *_Loop = Looping ligado.
 2. Atenuações em /Game/Audio/Attenuation: ATT_JR_Default (cheio até 4 m, some em 40 m), ATT_JR_Near (passos),
    ATT_JR_Vehicle (carro), ATT_JR_Far (explosões, rugido do elite).
 3. Classes de som em /Game/Audio/Classes: SCL_Music, SCL_SFX, SCL_Ambience, SCL_UI (cada som recebe a sua; servem
    para um menu de volume no futuro). Os volumes de agora ficam no DA_SoundBank (Mix).
 4. /Game/Audio/DA_SoundBank (UJRSoundBank): lista id -> variações/volume/tom/atenuação, zonas de ambiente e
    emissores fixos tirados de assets/work/levels/L01/l01_layout_v3.json (só no mapa L01_ZombieValley).
 5. BP_Vehicle_SUV: limpa explosion_sound (o subsistema já toca Car.Explosion; evita som dobrado).
 6. DefaultGame.ini: /Game/Audio em "Directories to Always Cook" (o C++ carrega o banco pelo caminho).
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "audio")
LAYOUT = os.path.join(REPO, "assets", "work", "levels", "L01", "l01_layout_v3.json")
GAME_INI = os.path.join(REPO, "unreal", "JogoResgate", "Config", "DefaultGame.ini")
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
AUDIO = "/Game/Audio"
ATT_DIR = f"{AUDIO}/Attenuation"
CLS_DIR = f"{AUDIO}/Classes"
BANK = f"{AUDIO}/DA_SoundBank"
VEHICLE_BP = "/Game/Vehicles/SUV/BP_Vehicle_SUV"
L01_MAP = "L01_ZombieValley"
GROUPS = {"vehicle": "Vehicle", "zombie": "Zombie", "hero": "Hero", "world": "World", "ambience": "Ambience",
          "ui": "UI", "music": "Music"}
CLASS_OF_GROUP = {"music": "SCL_Music", "ambience": "SCL_Ambience", "ui": "SCL_UI"}  # resto = SCL_SFX
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}, "cpp_needed": [],
     "missing_files": []}

# Atenuações: nome -> (cheio até cm, some em cm)
ATTENUATIONS = {
    "ATT_JR_Default": (400.0, 4000.0),
    "ATT_JR_Near": (150.0, 1800.0),
    "ATT_JR_Vehicle": (700.0, 7000.0),
    "ATT_JR_Far": (2000.0, 20000.0),
}

# id, grupo, arquivos (sem .wav; "Nome_0#" com n = expande _01.._0n), volume, tom mín., tom máx., atenuação,
# intervalo mínimo (s), voz de zumbi (conta no limite de 6)
def V(base, n):
    return [f"{base}_{i:02d}" for i in range(1, n + 1)]

SOUNDS = [
    # ---- carro
    ("Car.Engine", "vehicle", ["SFX_Vehicle_Engine_Loop"], 0.55, 1.0, 1.0, "ATT_JR_Vehicle", 0.0, False),
    ("Car.Nitro.Start", "vehicle", ["SFX_Vehicle_Nitro_Start"], 0.8, 0.95, 1.05, "ATT_JR_Vehicle", 0.5, False),
    ("Car.Nitro", "vehicle", ["SFX_Vehicle_Nitro_Loop"], 0.45, 1.0, 1.0, "ATT_JR_Vehicle", 0.0, False),
    ("Car.Skid", "vehicle", ["SFX_Vehicle_Skid_Loop"], 0.4, 1.0, 1.0, "ATT_JR_Vehicle", 0.0, False),
    ("Car.Impact.Light", "vehicle", V("SFX_Vehicle_Impact_Light", 3), 0.8, 0.92, 1.08, "ATT_JR_Vehicle", 0.12, False),
    ("Car.Impact.Heavy", "vehicle", V("SFX_Vehicle_Impact_Heavy", 3), 1.0, 0.9, 1.05, "ATT_JR_Vehicle", 0.2, False),
    ("Car.TireFlat", "vehicle", ["SFX_Vehicle_TireBurst_01"], 1.0, 0.95, 1.05, "ATT_JR_Vehicle", 0.3, False),
    ("Car.Land", "vehicle", V("SFX_Vehicle_Land", 2), 0.9, 0.9, 1.05, "ATT_JR_Vehicle", 0.3, False),
    ("Car.Door.Open", "vehicle", ["SFX_Vehicle_Door_Open"], 0.8, 0.95, 1.05, "ATT_JR_Near", 0.3, False),
    ("Car.Door.Close", "vehicle", ["SFX_Vehicle_Door_Close"], 0.8, 0.95, 1.05, "ATT_JR_Near", 0.3, False),
    ("Car.Fire", "vehicle", ["SFX_Vehicle_Fire_Loop"], 0.6, 1.0, 1.0, "ATT_JR_Default", 0.0, False),
    ("Car.Explosion", "vehicle", V("SFX_Vehicle_Explosion", 2), 1.0, 0.9, 1.05, "ATT_JR_Far", 0.3, False),
    ("Car.Horn", "vehicle", ["SFX_Vehicle_Horn"], 0.9, 1.0, 1.0, "ATT_JR_Vehicle", 0.3, False),
    ("Car.Scrape", "vehicle", V("SFX_Vehicle_Scrape", 2), 0.6, 0.9, 1.1, "ATT_JR_Vehicle", 0.2, False),
    # ---- zumbis
    ("Zombie.Moan", "zombie", V("SFX_Zombie_Moan", 4), 0.55, 0.85, 1.15, "ATT_JR_Default", 0.8, True),
    ("Zombie.Growl", "zombie", V("SFX_Zombie_Growl", 3), 0.75, 0.85, 1.15, "ATT_JR_Default", 0.25, True),
    ("Zombie.Horde", "zombie", V("SFX_Zombie_HordeScream", 2), 0.8, 0.9, 1.1, "ATT_JR_Far", 5.0, False),
    ("Zombie.Step", "zombie", V("SFX_Zombie_Step", 4), 0.35, 0.85, 1.15, "ATT_JR_Near", 0.0, False),
    ("Zombie.Attack", "zombie", V("SFX_Zombie_Attack", 3), 0.6, 0.85, 1.15, "ATT_JR_Near", 0.15, True),
    ("Zombie.Pain", "zombie", V("SFX_Zombie_Pain", 3), 0.6, 0.85, 1.2, "ATT_JR_Default", 0.2, True),
    ("Zombie.Death", "zombie", V("SFX_Zombie_Death", 3), 0.75, 0.85, 1.15, "ATT_JR_Default", 0.15, True),
    ("Zombie.HitCar", "zombie", V("SFX_Zombie_HitCar", 3), 0.9, 0.9, 1.1, "ATT_JR_Vehicle", 0.08, False),
    ("Zombie.Nails", "zombie", V("SFX_Zombie_Nails", 3), 0.6, 0.9, 1.15, "ATT_JR_Near", 0.4, False),
    ("Zombie.EliteRoar", "zombie", V("SFX_Zombie_EliteRoar", 2), 1.0, 0.95, 1.05, "ATT_JR_Far", 2.0, False),
    # ---- herói
    ("Hero.Step.Dirt", "hero", V("SFX_Hero_Step_Dirt", 5), 0.45, 0.9, 1.1, "ATT_JR_Near", 0.0, False),
    ("Hero.Step.Grass", "hero", V("SFX_Hero_Step_Grass", 4), 0.45, 0.9, 1.1, "ATT_JR_Near", 0.0, False),
    ("Hero.Step.Sand", "hero", V("SFX_Hero_Step_Sand", 4), 0.45, 0.9, 1.1, "ATT_JR_Near", 0.0, False),
    ("Hero.Step.Stone", "hero", V("SFX_Hero_Step_Stone", 4), 0.45, 0.9, 1.1, "ATT_JR_Near", 0.0, False),
    ("Hero.Step.Metal", "hero", V("SFX_Hero_Step_Metal", 4), 0.45, 0.9, 1.1, "ATT_JR_Near", 0.0, False),
    ("Hero.Step.Wood", "hero", V("SFX_Hero_Step_Wood", 4), 0.45, 0.9, 1.1, "ATT_JR_Near", 0.0, False),
    ("Hero.Jump", "hero", V("SFX_Hero_Jump", 3), 0.5, 0.95, 1.05, "ATT_JR_Near", 0.2, False),
    ("Hero.Land", "hero", V("SFX_Hero_Land", 2), 0.7, 0.95, 1.05, "ATT_JR_Near", 0.2, False),
    ("Hero.Hurt", "hero", V("SFX_Hero_Hurt", 3), 0.8, 0.95, 1.08, "ATT_JR_Near", 0.35, False),
    ("Hero.Death", "hero", ["SFX_Hero_Death"], 0.9, 1.0, 1.0, "ATT_JR_Near", 1.0, False),
    ("Hero.LowHealth", "hero", ["SFX_Hero_LowHealth_Loop"], 0.6, 1.0, 1.0, "", 0.0, False),
    ("Hero.Pickup", "hero", V("SFX_Hero_Pickup", 2), 0.7, 0.95, 1.05, "", 0.05, False),
    ("Hero.Bandage", "hero", ["SFX_Hero_Bandage"], 0.8, 1.0, 1.0, "", 0.5, False),
    ("Hero.Fury", "hero", ["SFX_Hero_Fury"], 0.85, 1.0, 1.0, "", 0.5, False),  # [A-075] fúria ativada
    # ---- mundo
    ("World.Pickup", "world", V("SFX_World_Pickup", 2), 0.6, 0.97, 1.03, "", 0.05, False),
    ("World.Pickup.Ammo", "world", ["SFX_World_Pickup_Ammo"], 0.7, 0.95, 1.05, "", 0.05, False),
    ("World.Pickup.Weapon", "world", ["SFX_World_Pickup_Weapon"], 0.7, 0.97, 1.03, "", 0.1, False),
    ("World.Chest.Open", "world", ["SFX_World_Chest_Open"], 0.8, 0.95, 1.05, "", 0.3, False),
    ("World.Fuel.Fill", "world", ["SFX_World_Fuel_Fill"], 0.8, 1.0, 1.0, "ATT_JR_Default", 1.0, False),
    ("World.Barrel.Explode", "world", V("SFX_World_Barrel_Explode", 2), 1.0, 0.9, 1.05, "ATT_JR_Far", 0.1, False),
    ("World.Spikes", "world", ["SFX_World_Spikes"], 0.8, 0.95, 1.05, "ATT_JR_Vehicle", 0.5, False),
    ("World.Toxic", "world", ["SFX_World_Toxic_Loop"], 0.6, 1.0, 1.0, "ATT_JR_Default", 0.0, False),
    ("World.Gate.Open", "world", ["SFX_World_Gate_Open"], 1.0, 0.95, 1.05, "ATT_JR_Far", 0.5, False),
    ("World.Bridge.Creak", "world", V("SFX_World_Bridge_Creak", 3), 0.6, 0.85, 1.1, "ATT_JR_Near", 0.6, False),
    ("World.Barricade.Break", "world", V("SFX_World_Barricade_Break", 2), 0.9, 0.9, 1.1, "ATT_JR_Vehicle", 0.2, False),
    # [A-075] portas dos interiores (AJRDoor, A-076)
    ("World.Door.Open", "world", ["SFX_World_Door_Open"], 0.8, 0.93, 1.07, "ATT_JR_Default", 0.2, False),
    ("World.Door.Close", "world", ["SFX_World_Door_Close"], 0.85, 0.93, 1.07, "ATT_JR_Default", 0.2, False),
    # ---- ambiente (2D; os emissores fixos usam atenuação própria do C++)
    ("Amb.Wind", "ambience", ["AMB_Valley_Wind_Loop"], 1.0, 1.0, 1.0, "", 0.0, False),
    ("Amb.Insects", "ambience", ["AMB_Forest_Insects_Loop"], 0.9, 1.0, 1.0, "", 0.0, False),
    ("Amb.Plants", "ambience", ["AMB_Forest_PlantPulse_Loop"], 0.7, 1.0, 1.0, "", 0.0, False),
    ("Amb.Ship", "ambience", ["AMB_Ship_Hum_Loop"], 0.8, 1.0, 1.0, "", 0.0, False),
    ("Amb.Spores", "ambience", ["AMB_Spore_Rain_Loop"], 0.8, 1.0, 1.0, "", 0.0, False),
    ("Amb.Thunder", "ambience", V("AMB_Thunder_Distant", 3), 0.8, 0.9, 1.05, "", 10.0, False),
    # ---- interface
    ("UI.Wheel.Open", "ui", ["SFX_UI_Wheel_Open"], 0.6, 1.0, 1.0, "", 0.05, False),
    ("UI.Wheel.Close", "ui", ["SFX_UI_Wheel_Close"], 0.6, 1.0, 1.0, "", 0.05, False),
    ("UI.Wheel.Hover", "ui", ["SFX_UI_Wheel_Hover"], 0.45, 0.97, 1.03, "", 0.03, False),
    ("UI.Wheel.Tab", "ui", ["SFX_UI_Wheel_Tab"], 0.6, 1.0, 1.0, "", 0.05, False),
    ("UI.Objective", "ui", ["SFX_UI_Objective"], 0.7, 1.0, 1.0, "", 1.0, False),
    ("UI.LowFuel", "ui", ["SFX_UI_LowFuel"], 0.8, 1.0, 1.0, "", 2.0, False),
    ("UI.Toast", "ui", ["SFX_UI_Toast"], 0.4, 1.0, 1.0, "", 0.15, False),
    ("UI.Radio", "ui", ["SFX_UI_Radio"], 0.7, 1.0, 1.0, "", 1.0, False),
    # ---- música
    ("Music.Explore", "music", ["MUS_L01_Explore_Loop"], 1.0, 1.0, 1.0, "", 0.0, False),
    ("Music.Tension", "music", ["MUS_L01_Tension_Loop"], 0.9, 1.0, 1.0, "", 0.0, False),
    ("Music.Horde", "music", ["MUS_L01_Horde_Loop"], 0.9, 1.0, 1.0, "", 0.0, False),
    ("Music.Victory", "music", ["MUS_Stinger_Victory"], 1.0, 1.0, 1.0, "", 2.0, False),
    ("Music.Defeat", "music", ["MUS_Stinger_Defeat"], 1.0, 1.0, 1.0, "", 2.0, False),
]

# Ambiente por zona do L01 (chave da zona no layout -> loops, volumes, piso, peso do trovão)
ZONE_AMBIENCE = {
    "Z0_Acampamento": (["Amb.Wind", "Amb.Ship"], [0.6, 0.5], "Dirt", 0.2),
    "Z1_EstradaVale": (["Amb.Wind"], [1.0], "Sand", 0.4),
    "Z2_Posto": (["Amb.Wind", "Amb.Insects"], [0.7, 0.3], "Stone", 0.3),
    "Z3_Floresta": (["Amb.Insects", "Amb.Plants", "Amb.Spores"], [1.0, 0.8, 0.6], "Grass", 0.1),
    "Z4_PonteColmeia": (["Amb.Insects", "Amb.Plants", "Amb.Spores"], [0.8, 1.0, 1.0], "Grass", 0.1),
    "Z5_FugaHorda": (["Amb.Wind", "Amb.Insects"], [0.8, 0.3], "Dirt", 0.5),
    "Z6_Vila": (["Amb.Wind", "Amb.Ship"], [0.5, 0.3], "Dirt", 0.3),
    "Z7_Saida": (["Amb.Wind"], [1.0], "Sand", 0.5),
}
# Pontos de interesse com som fixo (prefixo do nome do POI -> (id do loop, raio cm, volume))
POI_EMITTERS = {
    "Nave de resgate caída": [("Car.Fire", 3500.0, 1.0), ("Amb.Ship", 4500.0, 0.8)],
    "Disco voador enterrado": [("Amb.Ship", 4000.0, 0.7)],
    "Árvore-mãe gigante": [("Amb.Plants", 5000.0, 1.0)],
    "Colmeia alienígena": [("Amb.Insects", 4000.0, 1.0)],
}
BRIDGE_POI = "Ponte sobre a ravina"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[setup_audio] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[setup_audio] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[setup_audio] {where}: {exc}")


def save(asset):
    EAL.save_loaded_asset(asset, only_if_is_dirty=False)


def setp(obj, names, value, where):
    """Tenta cada nome (a Python da Unreal tira o 'b' dos bool: bLoop -> loop)."""
    for n in ([names] if isinstance(names, str) else names):
        try:
            obj.set_editor_property(n, value)
            return True
        except Exception:  # noqa: BLE001
            continue
    R["cpp_needed"].append(f"{where}.{names}")
    warn(f"{where}: propriedade {names} não existe (compilou o C++ novo?)")
    return False


def load(path):
    return EAL.load_asset(path) if EAL.does_asset_exist(path) else None


def import_file(path, folder, name):
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    asset = EAL.load_asset(f"{folder}/{name}")
    if asset is None:
        raise RuntimeError(f"não importou {path}")
    return asset


# ------------------------------------------------------------------ 3. classes de som

def sound_classes():
    EAL.make_directory(CLS_DIR)
    out = {}
    factory_cls = getattr(unreal, "SoundClassFactory", None)
    for name in ("SCL_Music", "SCL_SFX", "SCL_Ambience", "SCL_UI"):
        path = f"{CLS_DIR}/{name}"
        cls = load(path)
        if cls is None and factory_cls is not None:
            try:
                cls = TOOLS.create_asset(name, CLS_DIR, unreal.SoundClass, factory_cls())
                save(cls)
            except Exception as exc:  # noqa: BLE001
                warn(f"{name}: não criei a classe de som ({exc})")
        out[name] = cls
    if factory_cls is None:
        warn("SoundClassFactory indisponível: sons ficam sem classe (não afeta o jogo)")
    log(f"classes de som: {[k for k, v in out.items() if v]}")
    return out


# ------------------------------------------------------------------ 1. sons

def import_sounds(classes):
    done, loops = [], []
    for group, folder_name in GROUPS.items():
        src = os.path.join(SRC, group)
        if not os.path.isdir(src):
            warn(f"falta {src} (rode tools/pipeline/gen_game_audio.py)")
            continue
        folder = f"{AUDIO}/{folder_name}"
        EAL.make_directory(folder)
        cls = classes.get(CLASS_OF_GROUP.get(group, "SCL_SFX"))
        for f in sorted(os.listdir(src)):
            if not f.lower().endswith(".wav"):
                continue
            name = os.path.splitext(f)[0]
            try:
                wave = import_file(os.path.join(src, f), folder, name)
                is_loop = name.endswith("_Loop")
                wave.set_editor_property("looping", is_loop)
                if is_loop:
                    loops.append(name)
                    try:  # loop fora do alcance continua "andando" em silêncio (volta no ponto certo)
                        wave.set_editor_property("virtualization_mode", unreal.VirtualizationMode.PLAY_WHEN_SILENT)
                    except Exception:  # noqa: BLE001
                        pass
                if cls is not None:
                    try:
                        wave.set_editor_property("sound_class_object", cls)
                    except Exception as exc:  # noqa: BLE001
                        warn(f"{name}: classe de som não aplicada ({exc})")
                save(wave)
                done.append(f"{folder}/{name}")
            except Exception as exc:  # noqa: BLE001
                err(f"som {name}", exc)
    R["info"]["imported"] = len(done)
    R["info"]["loops"] = loops
    log(f"sons importados: {len(done)} ({len(loops)} loops)")


def find_wave(group, name):
    return load(f"{AUDIO}/{GROUPS[group]}/{name}")


# ------------------------------------------------------------------ 2. atenuações

def attenuations():
    EAL.make_directory(ATT_DIR)
    out = {}
    for name, (inner, falloff) in ATTENUATIONS.items():
        path = f"{ATT_DIR}/{name}"
        att = load(path) or TOOLS.create_asset(name, ATT_DIR, unreal.SoundAttenuation, unreal.SoundAttenuationFactory())
        try:
            s = att.get_editor_property("attenuation")
            s.set_editor_property("attenuation_shape_extents", unreal.Vector(inner, 0.0, 0.0))
            s.set_editor_property("falloff_distance", falloff)
            att.set_editor_property("attenuation", s)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: não ajustei a distância ({exc}); fica o padrão")
        save(att)
        out[name] = att
    log(f"atenuações: {list(out)}")
    return out


# ------------------------------------------------------------------ 4. banco

def zones_and_emitters():
    zones, emitters = [], []
    if not os.path.exists(LAYOUT):
        warn(f"sem {LAYOUT}: banco sem zonas (só o vento de base)")
        return zones, emitters
    with open(LAYOUT, encoding="utf-8") as fh:
        lay = json.load(fh)
    for z in lay.get("zones", []):
        cfg = ZONE_AMBIENCE.get(z.get("key"))
        if not cfg:
            continue
        ids, vols, surface, thunder = cfg
        zones.append({"name": z["key"], "center": z["center"], "radius": float(z.get("radius_cm", 10000)),
                      "loops": ids, "vols": vols, "surface": surface, "extra": "", "chance": 0.0, "thunder": thunder})
    for p in lay.get("pois", []):
        label = p.get("label") or p.get("name") or ""
        loc = p.get("loc")
        if not loc:
            continue
        if label.startswith(BRIDGE_POI):
            zones.append({"name": "Ponte_Ravina", "center": loc, "radius": 2500.0, "loops": [], "vols": [],
                          "surface": "Wood", "extra": "World.Bridge.Creak", "chance": 0.3, "thunder": 0.0})
        for prefix, items in POI_EMITTERS.items():
            if label.startswith(prefix):
                for loop_id, radius, vol in items:
                    emitters.append({"name": f"{prefix}:{loop_id}", "loc": loc, "loop": loop_id, "radius": radius, "vol": vol})
    for h in lay.get("hazards", []):
        if h.get("kind") == "toxic_lake":
            ext = h.get("box_extent_cm", [5000, 5000, 100])
            emitters.append({"name": h.get("label", "toxico"), "loc": h["loc"], "loop": "World.Toxic",
                             "radius": float(max(ext[0], ext[1])) + 3000.0, "vol": 1.0})
    R["info"]["zones"] = [z["name"] for z in zones]
    R["info"]["emitters"] = [e["name"] for e in emitters]
    return zones, emitters


def vec(v):
    return unreal.Vector(float(v[0]), float(v[1]), float(v[2]))


def make_bank(atts):
    bank_cls = getattr(unreal, "JRSoundBank", None)
    if bank_cls is None:
        R["cpp_needed"].append("UJRSoundBank")
        warn("classe JRSoundBank não encontrada: compile o C++ (Audio/JRSoundBank.h) e rode de novo")
        return
    bank = load(BANK)
    if bank is None:
        factory = unreal.DataAssetFactory()
        factory.set_editor_property("data_asset_class", bank_cls)
        bank = TOOLS.create_asset("DA_SoundBank", AUDIO, bank_cls, factory)
    entries, mapped, missing = [], [], []
    for (sid, group, files, vol, pmin, pmax, att, min_int, zvoice) in SOUNDS:
        waves = []
        for f in files:
            w = find_wave(group, f)
            if w is None:
                R["missing_files"].append(f"{group}/{f}")
            else:
                waves.append(w)
        if not waves:
            missing.append(sid)
            continue
        e = unreal.JRSoundEntry()
        setp(e, "id", sid, "JRSoundEntry")
        try:
            e.set_editor_property("variations", waves)
        except Exception:  # noqa: BLE001
            e.set_editor_property("variations", [unreal.SoftObjectPath(w.get_path_name()) for w in waves])
        setp(e, "volume", float(vol), "JRSoundEntry")
        setp(e, "pitch_min", float(pmin), "JRSoundEntry")
        setp(e, "pitch_max", float(pmax), "JRSoundEntry")
        if att and atts.get(att):
            setp(e, "attenuation", atts[att], "JRSoundEntry")
        setp(e, ["loop", "b_loop"], any(f.endswith("_Loop") for f in files), "JRSoundEntry")
        setp(e, "min_interval", float(min_int), "JRSoundEntry")
        setp(e, ["zombie_voice", "b_zombie_voice"], bool(zvoice), "JRSoundEntry")
        entries.append(e)
        mapped.append(sid)
    bank.set_editor_property("sounds", entries)
    if atts.get("ATT_JR_Default"):
        bank.set_editor_property("default_attenuation", atts["ATT_JR_Default"])
    zones, emitters = zones_and_emitters()
    zs = []
    for z in zones:
        a = unreal.JRAmbienceZone()
        a.set_editor_property("name", z["name"])
        setp(a, "map_name", L01_MAP, "JRAmbienceZone")
        a.set_editor_property("center", vec(z["center"]))
        a.set_editor_property("radius", z["radius"])
        a.set_editor_property("loop_ids", z["loops"])
        a.set_editor_property("loop_volumes", [float(x) for x in z["vols"]])
        a.set_editor_property("foot_surface", z["surface"])
        a.set_editor_property("foot_extra_id", z["extra"])
        a.set_editor_property("foot_extra_chance", float(z["chance"]))
        a.set_editor_property("thunder_weight", float(z["thunder"]))
        zs.append(a)
    bank.set_editor_property("ambience_zones", zs)
    es = []
    for em in emitters:
        a = unreal.JRAudioEmitter()
        a.set_editor_property("name", em["name"])
        setp(a, "map_name", L01_MAP, "JRAudioEmitter")
        a.set_editor_property("location", vec(em["loc"]))
        a.set_editor_property("loop_id", em["loop"])
        a.set_editor_property("radius", float(em["radius"]))
        a.set_editor_property("volume", float(em["vol"]))
        es.append(a)
    bank.set_editor_property("emitters", es)
    save(bank)
    R["info"]["sound_ids_mapped"] = mapped
    R["info"]["sound_ids_missing"] = missing
    log(f"DA_SoundBank: {len(mapped)} ids, {len(zs)} zonas, {len(es)} emissores; faltando: {missing}")


# ------------------------------------------------------------------ 5. carro

def vehicle_explosion_sound():
    bp = load(VEHICLE_BP)
    if bp is None:
        warn(f"{VEHICLE_BP} não existe (pulei)")
        return
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    try:
        old = cdo.get_editor_property("explosion_sound")
    except Exception:  # noqa: BLE001
        return
    if old is not None:
        R["info"]["vehicle_explosion_sound_cleared"] = old.get_path_name()
        cdo.set_editor_property("explosion_sound", None)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        log(f"BP_Vehicle_SUV: explosion_sound ({old.get_name()}) limpo; o subsistema toca Car.Explosion")


# ------------------------------------------------------------------ 6. cozinhar

def always_cook():
    if not os.path.exists(GAME_INI):
        warn("DefaultGame.ini não encontrado")
        return
    text = open(GAME_INI, encoding="utf-8").read()
    line = '+DirectoriesToAlwaysCook=(Path="/Game/Audio")'
    if line in text:
        log("DefaultGame.ini já cozinha /Game/Audio")
        return
    section = "[/Script/UnrealEd.ProjectPackagingSettings]"
    if section in text:
        text = text.replace(section, section + "\n" + line, 1)
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n" + line + "\n"
    with open(GAME_INI, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    log("DefaultGame.ini: /Game/Audio em Directories to Always Cook")


def main():
    classes, atts = {}, {}
    try:
        classes = sound_classes()
    except Exception as exc:  # noqa: BLE001
        err("sound_classes", exc)
    try:
        import_sounds(classes)
    except Exception as exc:  # noqa: BLE001
        err("import_sounds", exc)
    try:
        atts = attenuations()
    except Exception as exc:  # noqa: BLE001
        err("attenuations", exc)
    for fn, args in ((make_bank, (atts,)), (vehicle_explosion_sound, ()), (always_cook, ())):
        try:
            fn(*args)
        except Exception as exc:  # noqa: BLE001
            err(fn.__name__, exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_audio.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[setup_audio] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
