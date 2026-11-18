"""[Remap F1] Protótipo cinza do loop cidade -> arena (docs/design/REMAP_CIDADE_ARENA.md, etapa F1).

RODA NO EDITOR (caixa Cmd, modo Python), sem Play, DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/build_remap_f1.py"
Opções (no fim da linha): --sem-npcs (não importa os GLB), --reimportar-npcs, --so-cidade, --so-arena

Monta e salva:
1. NPCs: importa SK_NPC_Krug/Kaar/IxVel (assets/work/characters/npc) em /Game/Characters/NPC/<Nome>
   (malha, esqueleto e as 9 animações). Já importado = pula (use --reimportar-npcs para refazer).
2. /Game/Levels/Remap/L_Cidade: chão 400 x 400 m, muralha, praça 60 x 60 m, quarteirões cinza,
   Armeiro (Krug, norte), Bancada (Ix-Vel, leste) e Portão da arena (Kaar, sul), placas, luz e céu.
3. /Game/Levels/Remap/L_Arena_F1: pátio 80 x 80 m com muro, 18 coberturas (semente fixa), 16 pontos de
   surgimento (tag ArenaSpawn), 4 pontos da nave (tag ArenaExtracao), AJRArenaDirector, navegação, luz.
Os dois mapas usam AJRRemapGameMode no World Settings. Play na cidade: fale com Kaar (E) para ir à arena.
Pode rodar de novo: apaga só o que ele criou (tag RemapF1) e refaz. Relatório: reports/build_remap_f1.json
"""
import json
import math
import os
import random
import sys
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
TAG = "RemapF1"
CUBE = "/Engine/BasicShapes/Cube"
GRID = "/Engine/EngineMaterials/WorldGridMaterial"
CITY_MAP = "/Game/Levels/Remap/L_Cidade"
ARENA_MAP = "/Game/Levels/Remap/L_Arena_F1"
NPC_DIR = os.path.join(REPO, "assets", "work", "characters", "npc")
ARGS = set(sys.argv[1:])
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "npcs": {}}

NPCS = {
    "Krug": {"glb": "SK_NPC_Krug.glb", "shop": "ARMEIRO", "nome": "Krug, o Armeiro", "cor": (0.85, 0.45, 0.15),
             "falas": ["Arma boa não é barata. Arma barata não volta.", "Fala logo, a forja está acesa.",
                       "Volta inteiro que eu te vendo mais."]},
    "IxVel": {"glb": "SK_NPC_IxVel.glb", "shop": "BANCADA", "nome": "Ix-Vel, a Bancada", "cor": (0.3, 0.85, 0.35),
              "falas": ["Clic-clic. Posso deixar isso mais forte.", "Cada ajuste, um pouco mais de estrago.",
                        "Não toque nas peças soltas."]},
    "Kaar": {"glb": "SK_NPC_Kaar.glb", "shop": "PORTAO", "nome": "Kaar, guarda do Portão", "cor": (0.25, 0.5, 1.0),
             "falas": ["O portão abre. Se voltar, eu conto sua história.", "Escolha o nível. Lá fora ninguém espera.",
                       "A nave passa a cada três ondas. Não perca."]},
}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[remap_f1] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[remap_f1] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[remap_f1] {where}: {exc}")


# ------------------------------------------------------------------ helpers de cena

def tagged(a, folder, label, extra_tags=()):
    a.set_editor_property("tags", [unreal.Name(TAG)] + [unreal.Name(t) for t in extra_tags])
    a.set_folder_path(folder)
    a.set_actor_label(label)
    return a


def box(label, center, size_cm, yaw=0.0, folder="Remap/Blocos"):
    cube = EAL.load_asset(CUBE)
    a = ACTORS.spawn_actor_from_object(cube, unreal.Vector(*center), unreal.Rotator(0.0, 0.0, yaw))
    if a is None:
        raise RuntimeError(f"falha ao criar {label}")
    a.set_actor_scale3d(unreal.Vector(size_cm[0] / 100.0, size_cm[1] / 100.0, size_cm[2] / 100.0))
    c = a.static_mesh_component
    c.set_collision_profile_name("BlockAll")
    grid = EAL.load_asset(GRID)
    if grid:
        c.set_material(0, grid)
    return tagged(a, folder, label)


def ground_box(label, x, y, sx, sy, h, folder="Remap/Blocos"):
    """Caixa apoiada no chão (base em z = 0)."""
    return box(label, (x, y, h / 2.0), (sx, sy, h), folder=folder)


def spawn_cls(cls, loc, yaw, label, folder, props=None, extra_tags=()):
    a = ACTORS.spawn_actor_from_class(cls, unreal.Vector(*loc), unreal.Rotator(0, 0, yaw))
    if a is None:
        raise RuntimeError(f"falha ao spawnar {label}")
    for k, v in (props or {}).items():
        try:
            a.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"{label}.{k}", exc)
    return tagged(a, folder, label, extra_tags)


def sign(label, text, loc, yaw, size=160.0, color=(255, 220, 120)):
    a = spawn_cls(unreal.TextRenderActor, loc, yaw, label, "Remap/Placas")
    try:
        comp = a.text_render
        comp.set_text(text)
        comp.set_editor_property("world_size", size)
        comp.set_editor_property("text_render_color", unreal.Color(color[0], color[1], color[2], 255))
        comp.set_editor_property("horizontal_alignment", unreal.HorizTextAligment.EHTA_CENTER)
    except Exception as exc:  # noqa: BLE001
        warn(f"placa {label}: {exc}")
    return a


def open_map(path):
    if EAL.does_asset_exist(path):
        LES.load_level(path)
        old = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
        for a in old:
            ACTORS.destroy_actor(a)
        log(f"{path}: aberto, {len(old)} atores antigos removidos")
    else:
        EAL.make_directory(path.rsplit("/", 1)[0])
        try:
            LES.new_level(path, False)
        except TypeError:
            LES.new_level(path)
        log(f"{path}: mapa novo")


def lights(folder, sun_pitch=-40.0, sun_yaw=30.0, intensity=7.0, fog_density=0.02):
    sun = spawn_cls(unreal.DirectionalLight, (0, 0, 5000), 0, "Sol", folder)
    sun.set_actor_rotation(unreal.Rotator(0, sun_pitch, sun_yaw), False)
    lc = sun.light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    for k, v in (("intensity", intensity), ("atmosphere_sun_light", True)):
        try:
            lc.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"sol.{k}: {exc}")
    spawn_cls(unreal.SkyAtmosphere, (0, 0, 0), 0, "Ceu", folder)
    sky = spawn_cls(unreal.SkyLight, (0, 0, 1000), 0, "LuzDoCeu", folder)
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    try:
        sky.light_component.set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001
        warn(f"skylight: {exc}")
    fog = spawn_cls(unreal.ExponentialHeightFog, (0, 0, 0), 0, "Neblina", folder)
    try:
        fog.component.set_editor_property("fog_density", fog_density)
    except Exception as exc:  # noqa: BLE001
        warn(f"neblina: {exc}")


def point_light(label, loc, color=(1.0, 0.85, 0.6), intensity=8000.0, radius=1800.0, folder="Remap/Luz"):
    a = spawn_cls(unreal.PointLight, loc, 0, label, folder)
    lc = a.point_light_component
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    lc.set_editor_property("intensity", intensity)
    lc.set_editor_property("attenuation_radius", radius)
    lc.set_editor_property("light_color", unreal.Color(int(color[0] * 255), int(color[1] * 255), int(color[2] * 255), 255))
    return a


def world_settings():
    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    for k, v in (("default_game_mode", unreal.JRRemapGameMode.static_class()),
                 ("kill_z", -3000.0), ("force_no_precomputed_lighting", True)):
        try:
            ws.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"WorldSettings.{k}", exc)


def save():
    LES.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)


# ------------------------------------------------------------------ NPCs

def find_assets(folder):
    out = {"mesh": None, "anims": {}}
    for path in EAL.list_assets(folder, recursive=True, include_folder=False):
        obj = EAL.load_asset(path.split(".")[0])
        if obj is None:
            continue
        if isinstance(obj, unreal.SkeletalMesh):
            out["mesh"] = obj
        elif isinstance(obj, unreal.AnimSequence):
            out["anims"][obj.get_name()] = obj
    return out


def pick_anim(anims, *keys):
    for key in keys:
        for name, a in sorted(anims.items()):
            if key.lower() in name.lower():
                return a
    return None


def import_npcs():
    result = {}
    for name, info in NPCS.items():
        dest = f"/Game/Characters/NPC/{name}"
        found = find_assets(dest) if EAL.does_directory_exist(dest) else {"mesh": None, "anims": {}}
        if found["mesh"] is None or "--reimportar-npcs" in ARGS:
            src = os.path.join(NPC_DIR, info["glb"])
            if not os.path.exists(src):
                warn(f"{name}: {src} não existe; fica a cápsula")
                result[name] = found
                continue
            task = unreal.AssetImportTask()
            task.set_editor_property("filename", src)
            task.set_editor_property("destination_path", dest)
            task.set_editor_property("automated", True)
            task.set_editor_property("replace_existing", True)
            task.set_editor_property("save", True)
            unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
            found = find_assets(dest)
            log(f"{name}: importado ({'malha ok' if found['mesh'] else 'SEM malha'}, {len(found['anims'])} animações)")
        else:
            log(f"{name}: já importado ({len(found['anims'])} animações)")
        R["npcs"][name] = {"mesh": found["mesh"].get_path_name() if found["mesh"] else None,
                           "anims": sorted(found["anims"].keys())}
        result[name] = found
    return result


def shopkeeper(name, loc, yaw, npc_assets):
    info = NPCS[name]
    props = {
        "shop_type": getattr(unreal.JRShopType, info["shop"]),
        "display_name": info["nome"],
        "greetings": info["falas"],
        "placeholder_color": unreal.LinearColor(*info["cor"], 1.0),
    }
    a = spawn_cls(unreal.JRShopkeeper, loc, yaw, f"NPC_{name}", "Remap/NPCs", props)
    found = (npc_assets or {}).get(name) or {"mesh": None, "anims": {}}
    if found["mesh"] is not None:
        mesh_comp = a.get_editor_property("mesh")
        try:
            mesh_comp.set_skeletal_mesh_asset(found["mesh"])
        except Exception:  # noqa: BLE001
            mesh_comp.set_editor_property("skeletal_mesh_asset", found["mesh"])
        idle = pick_anim(found["anims"], "Breathing_Idle", "Idle")
        talk = pick_anim(found["anims"], "Talking_1", "Talking", "Head_Nod")
        if idle:
            a.set_editor_property("idle_anim", idle)
        if talk:
            a.set_editor_property("talk_anim", talk)
        if not idle:
            warn(f"{name}: animação parada não achada ({sorted(found['anims'].keys())})")
    try:
        a.rerun_construction_scripts()
    except Exception:  # noqa: BLE001
        pass
    return a


# ------------------------------------------------------------------ cidade

def build_city(npc_assets):
    open_map(CITY_MAP)
    half = 20000.0
    # chão e praça
    box("Chao", (0, 0, -50), (2 * half, 2 * half, 100), folder="Remap/Chao")
    box("Praca", (0, 0, 5), (6000, 6000, 10), folder="Remap/Chao")
    box("Monumento", (0, 0, 150), (400, 400, 300), folder="Remap/Praca")
    # muralha (8 m), com a abertura do portão ao sul (futuro)
    t, h = 200.0, 800.0
    box("Muralha_N", (0, half - t / 2, h / 2), (2 * half, t, h), folder="Remap/Muralha")
    box("Muralha_L", (half - t / 2, 0, h / 2), (t, 2 * half, h), folder="Remap/Muralha")
    box("Muralha_O", (-half + t / 2, 0, h / 2), (t, 2 * half, h), folder="Remap/Muralha")
    gap = 1200.0
    seg = (2 * half - gap) / 2
    box("Muralha_S1", (-half + seg / 2, -half + t / 2, h / 2), (seg, t, h), folder="Remap/Muralha")
    box("Muralha_S2", (half - seg / 2, -half + t / 2, h / 2), (seg, t, h), folder="Remap/Muralha")

    # 3 prédios com função em volta da praça; o vendedor fica na frente, virado para a praça
    shops = [
        ("Krug", "ARMEIRO", (0, 4600), 270.0),     # norte, olhando para o sul (-Y)
        ("IxVel", "BANCADA", (4600, 0), 180.0),    # leste, olhando para o oeste (-X)
        ("Kaar", "PORTÃO DA ARENA", (0, -4600), 90.0),  # sul, olhando para o norte (+Y)
    ]
    for name, title, (x, y), yaw in shops:
        dx, dy = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
        # prédio atrás do vendedor (do lado oposto à praça)
        bx, by = x - dx * 900, y - dy * 900
        if name == "Kaar":
            # portão: dois pilares e uma viga, para se ler como passagem
            px, py = -dy, dx  # perpendicular
            ground_box("Portao_PilarA", bx + px * 700, by + py * 700, 300, 300, 1200, folder="Remap/Portao")
            ground_box("Portao_PilarB", bx - px * 700, by - py * 700, 300, 300, 1200, folder="Remap/Portao")
            box("Portao_Viga", (bx, by, 1300), (1700 if abs(px) > 0.5 else 300, 1700 if abs(py) > 0.5 else 300, 200),
                folder="Remap/Portao")
            box("Portao_Fechado", (bx - dx * 150, by - dy * 150, 500),
                (1100 if abs(px) > 0.5 else 60, 1100 if abs(py) > 0.5 else 60, 1000), folder="Remap/Portao")
        else:
            ground_box(f"Predio_{name}", bx, by, 1400 if abs(dy) > 0.5 else 1000, 1000 if abs(dy) > 0.5 else 1400, 900,
                       folder="Remap/Predios")
            # toldo/balcão ao lado (não na frente: o E precisa achar o vendedor)
            ground_box(f"Balcao_{name}", x + (-dy) * 380, y + dx * 380, 300 if abs(dx) > 0.5 else 120,
                       120 if abs(dx) > 0.5 else 300, 110, folder="Remap/Predios")
        sign(f"Placa_{name}", title, (bx + dx * 520, by + dy * 520, 1050 if name != "Kaar" else 1550), yaw)
        point_light(f"Luz_{name}", (x + dx * 200, y + dy * 200, 450))
        shopkeeper(name, (x, y, 130), yaw, npc_assets)

    # quarteirões cinza (semente fixa): grade de 40 m, sem a praça e sem as 2 avenidas
    rng = random.Random(4242)
    n = 0
    cell = 4000.0
    for gx in range(-4, 5):
        for gy in range(-4, 5):
            if (abs(gx) <= 1 and abs(gy) <= 1) or gx == 0 or gy == 0:
                continue
            cx, cy = gx * cell, gy * cell
            sx, sy = rng.uniform(1800, 2900), rng.uniform(1800, 2900)
            hgt = rng.choice([600, 800, 1000, 1400, 1800, 2400])
            ground_box(f"Quarteirao_{gx}_{gy}", cx + rng.uniform(-300, 300), cy + rng.uniform(-300, 300), sx, sy, hgt)
            n += 1
    log(f"cidade: {n} quarteirões, 3 vendedores, muralha e praça")

    lights("Remap/Luz", sun_pitch=-35.0, sun_yaw=40.0, intensity=8.0, fog_density=0.01)
    spawn_cls(unreal.PlayerStart, (0, -2400, 120), 90.0, "PlayerStart", "Remap/Gameplay")
    sign("Placa_VillaStar", "VILLA STAR", (0, 0, 520), 270.0, size=260.0, color=(120, 240, 255))
    world_settings()
    save()


# ------------------------------------------------------------------ arena

def build_arena():
    open_map(ARENA_MAP)
    half = 4000.0
    box("Chao", (0, 0, -50), (2 * half + 2000, 2 * half + 2000, 100), folder="Remap/Chao")
    t, h = 200.0, 400.0
    for label, c, s in (("Muro_N", (0, half, h / 2), (2 * half + t, t, h)), ("Muro_S", (0, -half, h / 2), (2 * half + t, t, h)),
                        ("Muro_L", (half, 0, h / 2), (t, 2 * half + t, h)), ("Muro_O", (-half, 0, h / 2), (t, 2 * half + t, h))):
        box(label, c, s, folder="Remap/Muro")

    # coberturas: baixas (1 m, dá para atirar por cima) e altas (3 m), longe do centro e da borda
    rng = random.Random(1717)
    placed = []
    tries = 0
    while len(placed) < 18 and tries < 500:
        tries += 1
        x, y = rng.uniform(-half + 700, half - 700), rng.uniform(-half + 700, half - 700)
        if math.hypot(x, y) < 900:
            continue
        if any(math.hypot(x - px, y - py) < 900 for px, py in placed):
            continue
        tall = rng.random() < 0.4
        sx, sy = rng.choice([(400, 120), (120, 400), (300, 300), (600, 150), (150, 600)])
        ground_box(f"Cobertura_{len(placed):02d}", x, y, sx, sy, 300 if tall else 100, folder="Remap/Coberturas")
        placed.append((x, y))

    # pontos de surgimento: anel quadrado perto do muro
    k = 0
    inner = half - 400
    for i in range(4):
        for frac in (-0.6, -0.2, 0.2, 0.6):
            if i == 0:
                p = (frac * inner, inner)
            elif i == 1:
                p = (inner, frac * inner)
            elif i == 2:
                p = (frac * inner, -inner)
            else:
                p = (-inner, frac * inner)
            spawn_cls(unreal.TargetPoint, (p[0], p[1], 20), 0, f"Spawn_{k:02d}", "Remap/Spawn", extra_tags=("ArenaSpawn",))
            k += 1
    for i, (x, y) in enumerate(((-2500, -2500), (2500, -2500), (2500, 2500), (-2500, 2500))):
        spawn_cls(unreal.TargetPoint, (x, y, 20), 0, f"Extracao_{i}", "Remap/Extracao", extra_tags=("ArenaExtracao",))

    spawn_cls(unreal.JRArenaDirector, (0, 0, 60), 0, "ArenaDirector", "Remap/Gameplay")
    spawn_cls(unreal.PlayerStart, (0, -600, 120), 90.0, "PlayerStart", "Remap/Gameplay")
    nav = spawn_cls(unreal.NavMeshBoundsVolume, (0, 0, 200), 0, "NavBounds", "Remap/Gameplay")
    nav.set_actor_scale3d(unreal.Vector((2 * half) / 200.0, (2 * half) / 200.0, 1000 / 200.0))
    # Dados da navegação: sem um RecastNavMesh no mapa os zumbis não acham caminho (a geração é Dynamic,
    # então ele se monta sozinho no Play a partir do NavBounds).
    if not [x for x in ACTORS.get_all_level_actors() if isinstance(x, unreal.RecastNavMesh)]:
        try:
            ACTORS.spawn_actor_from_class(unreal.RecastNavMesh, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
            log("RecastNavMesh criado")
        except Exception as exc:  # noqa: BLE001
            warn(f"RecastNavMesh: {exc} (use Build > Build Paths)")
    for i, (x, y) in enumerate(((-2000, 0), (2000, 0), (0, 2000), (0, -2000))):
        point_light(f"Luz_{i}", (x, y, 600), color=(1.0, 0.55, 0.4), intensity=2500.0, radius=2200.0)
    lights("Remap/Luz", sun_pitch=-35.0, sun_yaw=200.0, intensity=2.5, fog_density=0.015)
    world_settings()
    try:
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        unreal.SystemLibrary.execute_console_command(world, "RebuildNavigation")
    except Exception as exc:  # noqa: BLE001
        warn(f"RebuildNavigation: {exc} (use Build > Build Paths)")
    log(f"arena: {len(placed)} coberturas, {k} pontos de surgimento, 4 pontos da nave")
    save()


def main():
    npc_assets = {}
    if "--sem-npcs" not in ARGS:
        try:
            npc_assets = import_npcs()
        except Exception as exc:  # noqa: BLE001
            err("import_npcs", exc)
    if "--so-arena" not in ARGS:
        try:
            build_city(npc_assets)
        except Exception as exc:  # noqa: BLE001
            err("build_city", exc)
    if "--so-cidade" not in ARGS:
        try:
            build_arena()
        except Exception as exc:  # noqa: BLE001
            err("build_arena", exc)
    # termina com a cidade aberta (é por onde o loop começa)
    if "--so-arena" not in ARGS and EAL.does_asset_exist(CITY_MAP):
        LES.load_level(CITY_MAP)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "build_remap_f1.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[remap_f1] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
