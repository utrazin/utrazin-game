"""Monta a Fase 1 "Vale Alienígena" (2 x 2 km): L01_ZombieValley.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++:
  py "E:/game/utrazin-game/tools/unreal/build_l01.py"          (usa a v3 se existir l01_layout_v3.json)
  py "E:/game/utrazin-game/tools/unreal/build_l01.py" v2       (força a v2 antiga, corredor fechado)

v3 (Etapa 5, vale aberto; docs/gameplay/L01_STORYBOARD.md):
  Entradas (tools/blender/gen_l01_v3.py + plot_l01_v3.py):
    assets/work/levels/L01/L01_Terrain_v3.fbx    terreno 2 x 2 km (64 pedaços) + estrada com a ponte
    assets/work/levels/L01/l01_layout_v3.json    zonas, POIs (blockout), portões, checkpoints, itens...
    assets/work/levels/L01/L01_Props*.fbx        props próprios (arco, ponte, disco, cela, rampas...)
    assets/raw/quaternius/**.fbx                 modelos CC0 (importados por tools/unreal/quaternius_lib.py
                                                 em /Game/Environment/Quaternius/<Pack>/)
  Faz: terreno, blockouts dos POIs, saltos, luzes, buggy estacionado no acampamento (jogador começa a pé
  e precisa da chave), checkpoints (armas, itens-chave, carro estacionado), zumbis, itens, baús (chave,
  galão, explosivos), histórias, portões (árvore na ponte = AJRBlockingGate), barricada de corpos,
  rio e lago tóxico (cair = checkpoint), zonas do diretor + UM AJRAIDirector, horda da vila, resgate,
  paredes invisíveis SÓ na borda, navegação por zona, céu alienígena (setup_alien_sky, se existir).
  NÃO espalha vegetação (é do agente Densidade: ver "veg_hints" no layout e l01_veg_density_v3.png).

v2 (histórico): gen_l01.py + L01_Terrain.fbx + l01_layout.json (corredor com paredes invisíveis).
Modelos do usuário (Tripo, assets/raw/tripo/CATALOG.md): se import_user_assets.py já rodou, a v3 troca barracas,
  posto (cobertura, 2 bombas, loja), torre, nave, arco, árvore-mãe, colmeia, disco, casas da vila, cercas,
  barricadas, carros batidos, cela, baús (PRP_Bau, chave DENTRO da barraca), itens (kit médico, munição, graveto,
  escopeta), portão da vila e árvore da ponte pelos modelos dele, em tamanho real, e espalha grupos de cenário
  pelas rotas (tools/unreal/l01_user_dressing.py). Sem o import, usa as peças Quaternius/blockout de antes.
Antes de tudo: setup_wave1.py (cria os materiais M_L01_Terrain, M_L01_Road, M_L01_Glow, M_L01_Toxic).
Pode rodar de novo: apaga o que ele mesmo criou (tag L01Gen) e refaz. Relatório: reports/build_l01.json
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "levels", "L01")
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
MEL = unreal.MaterialEditingLibrary
MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
ENV = "/Game/Environment/L01"
MAT = f"{ENV}/Materials/M_L01_VertexColor"
TAG = "L01Gen"
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "counts": {}}

COMPLEX = {"SM_Ruin_House", "SM_Ruin_Wall", "SM_Watchtower", "SM_Cage", "SM_ArenaWall", "SM_Barricade",
           "SM_CarWreck", "SM_Fence", "SM_Ramp", "SM_RampLanding", "SM_GuardRail", "SM_RockWall", "SM_Container",
           "SM_BusWreck", "SM_BridgePlanks", "SM_BoneRibs", "SM_UFOWreck", "SM_AlienArch", "SM_FarmhouseRuin",
           "SM_StonePlatform", "SM_StonePlatformTall", "SM_ToxicPoolRim"}
NO_COLLISION = {"SM_Bush", "SM_Rock_Small", "SM_Sign", "SM_GrassAlienTuft", "SM_AlienFlowerGlow", "SM_SpikeStrip"}
PHYSICS = {"SM_Crate", "SM_Barrel", "SM_Roadblock"}   # tiro/carro empurram
# [A-063] o mesmo para as peças Quaternius do layout e os modelos do usuário (barril, caixa)
PHYSICS_Q = {"ZombieKit/Barrel", "SpaceKit/Pickup_Crate"}
PHYSICS_USER = {"PRP_Barril"}
# [A-063] luzes do layout em candelas. Os valores do l01_layout_v3.json (9000 a 30000) foram pensados sem unidade;
# com a exposição fixa do céu (sol do entardecer ~5 lux) eles estouravam tudo (print_08: sofá branco).
# 0,006: fogueira 54 cd (~6 lux a 3 m), fogo da nave 150 cd, árvore-mãe 180 cd.
LIGHT_CD_PER_LAYOUT = 0.006
GLOW_MAT = f"{ENV}/Materials/M_L01_Glow"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[build_l01] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[build_l01] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-900:]})
    unreal.log_error(f"[build_l01] {where}: {exc}")


def V(a):
    return unreal.Vector(float(a[0]), float(a[1]), float(a[2]))


# ------------------------------------------------------------------ material
def load_mat(path):
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    warn(f"material ausente: {path} (rode setup_wave1.py antes); usando M_L01_VertexColor")
    return material()


def material():
    if EAL.does_asset_exist(MAT):
        return EAL.load_asset(MAT)
    EAL.make_directory(f"{ENV}/Materials")
    m = TOOLS.create_asset("M_L01_VertexColor", f"{ENV}/Materials", unreal.Material, unreal.MaterialFactoryNew())
    vc = MEL.create_material_expression(m, unreal.MaterialExpressionVertexColor, -400, 0)
    MEL.connect_material_property(vc, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -400, 220)
    rough.set_editor_property("r", 0.9)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m)
    log("material M_L01_VertexColor criado")
    return m


# ------------------------------------------------------------------ import
def import_fbx(fbx, folder, collision):
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", False), ("auto_generate_collision", collision), ("generate_lightmap_u_vs", False),
                 ("transform_vertex_to_absolute", True), ("build_nanite", False),
                 ("vertex_color_import_option", unreal.VertexColorImportOption.REPLACE)):
        try:
            d.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"import option {k}: {exc}")
    task.options = o
    TOOLS.import_asset_tasks([task])
    paths = [p.split(".")[0] for p in task.imported_object_paths]
    log(f"{os.path.basename(fbx)}: {len(paths)} malhas")
    return paths


def prep_mesh(path, mat, complex_collision, glow=None):
    sm = EAL.load_asset(path)
    if not isinstance(sm, unreal.StaticMesh):
        return None
    slots = sm.get_editor_property("static_materials")
    for i in range(max(1, len(slots))):
        try:
            slot = str(slots[i].get_editor_property("material_slot_name")) if i < len(slots) else ""
            sm.set_material(i, glow if (glow and "Glow" in slot) else mat)
        except Exception as exc:  # noqa: BLE001
            warn(f"{path} material: {exc}")
    try:
        R.setdefault("vertex_colors", {})
        if len(R["vertex_colors"]) < 6:
            sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            R["vertex_colors"][path.split("/")[-1]] = bool(sub.has_vertex_colors(sm))
    except Exception:  # noqa: BLE001
        pass
    if complex_collision:
        try:
            bs = sm.get_editor_property("body_setup")
            bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
        except Exception as exc:  # noqa: BLE001
            warn(f"{path} colisão: {exc}")
    EAL.save_loaded_asset(sm, only_if_is_dirty=False)
    return sm


# ------------------------------------------------------------------ mapa
def open_map():
    if EAL.does_asset_exist(MAP):
        LES.load_level(MAP)
        # também o diretor posto por add_ai_director.py (senão ficariam dois diretores)
        old = [a for a in ACTORS.get_all_level_actors() if {TAG, "AIDirectorGen"} & {str(t) for t in a.tags}]
        for a in old:
            ACTORS.destroy_actor(a)
        log(f"mapa existente aberto; {len(old)} atores antigos removidos")
    else:
        EAL.make_directory("/Game/Levels/L01_ZombieValley")
        try:
            LES.new_level(MAP, False)
        except TypeError:
            LES.new_level(MAP)
        log("mapa novo criado")


def tagged(a, folder, label=None):
    a.set_editor_property("tags", [unreal.Name(TAG)])
    a.set_folder_path(folder)
    if label:
        a.set_actor_label(label)
    return a


def spawn_mesh(sm, loc, yaw=0.0, scale=1.0, folder="L01", cull_m=0, nocol=False, physics=False):
    a = ACTORS.spawn_actor_from_object(sm, V(loc), unreal.Rotator(0, 0, yaw))
    if a is None:
        raise RuntimeError(f"falha ao colocar {sm.get_name()}")
    if isinstance(scale, (list, tuple)):
        a.set_actor_scale3d(unreal.Vector(*[float(x) for x in scale]))
    elif scale != 1.0:
        a.set_actor_scale3d(unreal.Vector(scale, scale, scale))
    c = a.static_mesh_component
    if cull_m:
        try:
            c.set_editor_property("ld_max_draw_distance", float(cull_m) * 100)
        except Exception:  # noqa: BLE001
            pass
    if nocol:
        c.set_collision_profile_name("NoCollision")
    if physics:
        try:
            c.set_mobility(unreal.ComponentMobility.MOVABLE)
            c.set_simulate_physics(True)
            c.set_collision_profile_name("PhysicsActor")
        except Exception as exc:  # noqa: BLE001
            warn(f"física {sm.get_name()}: {exc}")
    return tagged(a, folder)


def make_physics(c, name=""):
    """[A-063] Empurrável por tiro e carro: móvel, física ligada, mas DORMINDO até levar um esbarrão
    (senão rola morro abaixo assim que o jogo começa)."""
    try:
        c.set_mobility(unreal.ComponentMobility.MOVABLE)
        c.set_collision_profile_name("PhysicsActor")
        bi = c.get_editor_property("body_instance")
        bi.set_editor_property("start_awake", False)
        bi.set_editor_property("linear_damping", 0.4)
        bi.set_editor_property("angular_damping", 1.0)
        c.set_editor_property("body_instance", bi)
        c.set_simulate_physics(True)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"física {name}: {exc}")
        return False


def spawn_cls(cls, loc, yaw, label, folder, props=None):
    a = ACTORS.spawn_actor_from_class(cls, V(loc), unreal.Rotator(0, 0, yaw))
    if a is None:
        raise RuntimeError(f"falha ao spawnar {label}")
    for k, v in (props or {}).items():
        try:
            a.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"{label}.{k}", exc)
    return tagged(a, folder, label)


def trace_z(x, y):
    w = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    hit = unreal.SystemLibrary.line_trace_single(w, unreal.Vector(x, y, 100000), unreal.Vector(x, y, -100000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, [],
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    t = hit.to_tuple() if hit else None
    return round(t[5].z, 1) if t and t[0] else None


PICKUP = {"AMMO": "AMMO", "HEALTH": "HEALTH", "NITRO": "NITRO", "FURY": "FURY", "REPAIR": "REPAIR",
          "WEAPON_MELEE": "WEAPON_MELEE", "WEAPON_PISTOL": "WEAPON_PISTOL", "WEAPON_SHOTGUN": "WEAPON_SHOTGUN"}


def set_box(actor, comp, extent, label):
    try:
        actor.get_editor_property(comp).set_box_extent(unreal.Vector(*[float(x) for x in extent]), True)
    except Exception as exc:  # noqa: BLE001
        err(f"{label}.{comp}.extent", exc)


def set_comp_mesh(actor, comp, sm, label):
    if sm is None:
        return
    try:
        actor.get_editor_property(comp).set_static_mesh(sm)
    except Exception as exc:  # noqa: BLE001
        warn(f"{label}.{comp}.mesh: {exc}")


def spawn_actors(L, props, cls):
    """Itens, barris, pregos, buracos, lago, baú, histórias e spawner (lista "actors" do layout v2)."""
    counts = {}
    toxic = EAL.load_asset(f"{ENV}/Materials/M_L01_Toxic") if EAL.does_asset_exist(f"{ENV}/Materials/M_L01_Toxic") else None
    plane = EAL.load_asset("/Engine/BasicShapes/Plane")
    for a in L.get("actors", []):
        kind, label, p = a["cls"], a.get("label") or a["cls"], a.get("props", {})
        try:
            if kind == "pickup":
                act = spawn_cls(unreal.JRPickup, a["loc"], a["yaw"], label, "L01/Itens",
                                {"type": getattr(unreal.JRPickupType, PICKUP[p["type"]]), "amount": float(p.get("amount", 1))})
                if p.get("display") and props.get(p["display"]):
                    act.set_editor_property("display_mesh", props[p["display"]])
                    act.set_editor_property("display_scale", 1.0)
            elif kind == "barrel":
                act = spawn_cls(unreal.JRExplosiveBarrel, a["loc"], a["yaw"], label, "L01/Perigos")
                set_comp_mesh(act, "mesh", props.get("SM_ExplosiveBarrel"), label)
            elif kind == "spike":
                act = spawn_cls(unreal.JRSpikeStrip, a["loc"], a["yaw"], label, "L01/Perigos")
                set_comp_mesh(act, "mesh", props.get("SM_SpikeStrip"), label)
            elif kind == "hazard":
                act = spawn_cls(unreal.JRHazardVolume, a["loc"], a["yaw"], label, "L01/Perigos",
                                {"instant_fail": bool(p.get("instant_fail", False)),
                                 "damage_per_second": float(p.get("damage_per_second", 30))})
                set_box(act, "box", p["box_extent"], label)
            elif kind == "story":
                act = spawn_cls(unreal.JRStoryTrigger, a["loc"], a["yaw"], label, "L01/Historia",
                                {"message": p["message"], "objective_hint": p.get("objective_hint", ""),
                                 "on_foot_only": bool(p.get("on_foot_only", False))})
                set_box(act, "box", p.get("box_extent", [1500, 1500, 600]), label)
            elif kind == "chest":
                act = spawn_cls(unreal.JRLootChest, a["loc"], a["yaw"], label, "L01/Itens",
                                {"weapon_inside": getattr(unreal.JRWeaponSlot, p.get("weapon", "PISTOL")),
                                 "ammo_inside": int(p.get("ammo", 24))})
            elif kind == "spawner":
                act = spawn_cls(unreal.JRAmbientSpawner, a["loc"], a["yaw"], label, "L01/Gameplay",
                                {"enemy_classes": [cls["melee"], cls["melee"], cls["archer"]],
                                 "active_stage": getattr(unreal.JRLevelStage, p.get("stage", "ON_FOOT"))})
            elif kind == "toxic_plane":
                act = spawn_mesh(plane, a["loc"], a["yaw"], [p["size_m"][0], p["size_m"][1], 1.0], "L01/Perigos", 0, True)
                act.set_actor_label(label)
                if toxic:
                    act.static_mesh_component.set_material(0, toxic)
            else:
                warn(f"tipo desconhecido no layout: {kind}")
                continue
            counts[kind] = counts.get(kind, 0) + 1
        except Exception as exc:  # noqa: BLE001
            err(label, exc)
    R["counts"]["actors"] = counts
    log(f"atores de jogo: {counts}")


def spawn_walls(L):
    """Paredes invisíveis do corredor: bloqueiam carro e personagem, não aparecem no jogo."""
    cube = EAL.load_asset("/Engine/BasicShapes/Cube")
    n = 0
    for i, w in enumerate(L.get("walls", [])):
        try:
            a = ACTORS.spawn_actor_from_object(cube, V(w["loc"]), unreal.Rotator(0, 0, w["yaw"]))
            a.set_actor_scale3d(unreal.Vector(w["len_cm"] / 100.0, 1.0, w["h_cm"] / 100.0))
            c = a.static_mesh_component
            c.set_collision_profile_name("InvisibleWall")
            a.set_actor_hidden_in_game(True)
            try:
                c.set_editor_property("cast_shadow", False)
            except Exception:  # noqa: BLE001
                pass
            tagged(a, "L01/Limites", f"Limite_{i:03d}")
            n += 1
        except Exception as exc:  # noqa: BLE001
            err(f"parede {i}", exc)
    R["counts"]["walls"] = n
    log(f"{n} paredes invisíveis")


def main():
    L = json.load(open(os.path.join(SRC, "l01_layout.json"), encoding="utf-8"))
    mat = material()
    glow = load_mat(GLOW_MAT)
    mat_terrain = load_mat(f"{ENV}/Materials/M_L01_Terrain")
    mat_road = load_mat(f"{ENV}/Materials/M_L01_Road")
    terrain_paths = import_fbx(os.path.join(SRC, "L01_Terrain.fbx"), f"{ENV}/Terrain", False)
    prop_paths = []
    for f in ("L01_Props.fbx", "L01_Props2.fbx", "L01_Props3.fbx"):
        if os.path.exists(os.path.join(SRC, f)):
            prop_paths += import_fbx(os.path.join(SRC, f), f"{ENV}/Props", True)
        else:
            warn(f"faltando {f}")
    terrain = [prep_mesh(p, mat_road if "_Road_" in p else mat_terrain, True) for p in terrain_paths]
    props = {}
    for p in prop_paths:
        name = p.split("/")[-1]
        sm = prep_mesh(p, mat, name in COMPLEX, glow)
        if sm:
            props[name] = sm
    if EAL.does_asset_exist("/Game/Weapons/SM_AlienStick"):
        props["SM_AlienStick"] = EAL.load_asset("/Game/Weapons/SM_AlienStick")
    R["counts"]["prop_meshes"] = sorted(props)

    open_map()
    for sm in terrain:
        if sm:
            spawn_mesh(sm, (0, 0, 0), folder="L01/Terreno")
    R["counts"]["terrain_actors"] = len([t for t in terrain if t])

    n = 0
    for p in L["props"]:
        sm = props.get(p["mesh"])
        if sm is None:
            warn(f"malha ausente: {p['mesh']}")
            continue
        veg = ("SM_Tree", "SM_Bush", "SM_Rock", "SM_Alien", "SM_Mushroom", "SM_Crystal", "SM_Spore", "SM_Grass", "SM_Egg")
        sub = "Vegetacao" if p["mesh"].startswith(veg) else "Construcoes"
        try:
            spawn_mesh(sm, p["loc"], p["yaw"], p["scale"], f"L01/Cenario/{sub}", p.get("cull_m", 0),
                       p["mesh"] in NO_COLLISION or p.get("nocol", False), p["mesh"] in PHYSICS)
        except Exception as exc:  # noqa: BLE001
            err(p["mesh"], exc)
            continue
        n += 1
    R["counts"]["props"] = n
    log(f"{n} objetos de cenário colocados")

    # ---- luz e céu (tudo dinâmico: o projeto não usa luz bakeada)
    sun = spawn_cls(unreal.DirectionalLight, (0, 0, 50000), 0, "Sol", "L01/Luz")
    sun.set_actor_rotation(unreal.Rotator(0, -38, 125), False)
    lc = sun.light_component
    for k, v in (("intensity", 7.0), ("light_color", unreal.Color(255, 214, 200, 255)),
                 ("atmosphere_sun_light", True), ("dynamic_shadow_distance_movable_light", 25000.0)):
        try:
            lc.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"sol.{k}: {exc}")
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    spawn_cls(unreal.SkyAtmosphere, (0, 0, 0), 0, "Ceu", "L01/Luz")
    sky = spawn_cls(unreal.SkyLight, (0, 0, 2000), 0, "LuzDoCeu", "L01/Luz")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    try:
        sky.light_component.set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001
        warn(f"skylight: {exc}")
    fog = spawn_cls(unreal.ExponentialHeightFog, (0, 0, 0), 0, "Neblina", "L01/Luz")
    try:
        fc = fog.component
        fc.set_editor_property("fog_density", 0.006)
        fc.set_editor_property("start_distance", 3000.0)
        fc.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.45, 0.32, 0.6, 1))  # névoa roxa
    except Exception as exc:  # noqa: BLE001
        warn(f"neblina: {exc}")
    try:
        spawn_cls(unreal.VolumetricCloud, (0, 0, 0), 0, "Nuvens", "L01/Luz")
    except Exception as exc:  # noqa: BLE001
        warn(f"nuvens: {exc}")

    # ---- gameplay
    stage = unreal.JRLevelStage
    spawn_cls(unreal.JRCheckpoint, L["cp_start"]["loc"], L["cp_start"]["yaw"], "CP_Start", "L01/Gameplay",
              {"checkpoint_id": "Start", "stage_on_respawn": stage.DRIVING, "is_level_start": True})
    spawn_cls(unreal.JRCheckpoint, L["cp_transition"]["loc"], L["cp_transition"]["yaw"], "CP_Transition", "L01/Gameplay",
              {"checkpoint_id": "Transition", "stage_on_respawn": stage.ON_FOOT, "is_vehicle_transition": True})
    spawn_cls(unreal.PlayerStart, L["start"]["loc"], L["start"]["yaw"], "PlayerStart", "L01/Gameplay")
    for c in L.get("checkpoints", []):
        props_cp = {"checkpoint_id": c["id"], "stage_on_respawn": getattr(stage, c["stage"])}
        props_cp.update(c.get("props", {}))
        spawn_cls(unreal.JRCheckpoint, c["loc"], c["yaw"], c["label"], "L01/Gameplay", props_cp)

    cls = {"melee": EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieMelee"),
           "archer": EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieArcher"),
           "gunner": EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieGunner")}
    cls["elite"] = (EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieElite")
                    if EAL.does_asset_exist("/Game/Enemies/BP_Enemy_ZombieElite") else cls["melee"])
    for e in L["enemies"]:
        try:
            spawn_cls(cls.get(e["type"], cls["melee"]), e["loc"], 0, e["label"], "L01/Inimigos")
        except Exception as exc:  # noqa: BLE001
            err(e["label"], exc)
    R["counts"]["enemies"] = len(L["enemies"])

    points = [spawn_cls(unreal.TargetPoint, p, 0, f"Horde_Spawn_{i + 1:02d}", "L01/Gameplay") for i, p in enumerate(L["horde_points"])]
    waves = []
    for c, count, interval in (("melee", 6, 0.8), ("melee", 8, 0.6), ("gunner", 3, 1.5), ("melee", 10, 0.5)):
        w = unreal.JRWave()
        w.set_editor_property("enemy_class", cls[c])
        w.set_editor_property("count", count)
        w.set_editor_property("spawn_interval", interval)
        waves.append(w)
    spawn_cls(unreal.JRHordeDirector, L["horde_director"]["loc"], 0, "HordeDirector_Final", "L01/Gameplay",
              {"waves": waves, "spawn_points": points, "is_final_horde": True, "min_spawn_distance": 1500.0, "max_alive": 30})

    # Diretor de IA (Etapa 3): grupos/hordas nos estágios Driving e OnFoot. Maioria melee, elite raro.
    table = []
    for c, weight in (("melee", 8.0), ("archer", 1.0), ("gunner", 1.0), ("elite", 0.3)):
        if cls.get(c) is None or (c == "elite" and cls["elite"] == cls["melee"]):
            continue
        e = unreal.JRDirectorEnemyEntry()
        e.set_editor_property("enemy_class", cls[c])
        e.set_editor_property("weight", weight)
        table.append(e)
    spawn_cls(unreal.JRAIDirector, L["horde_director"]["loc"], 0, "AIDirector", "L01/Gameplay", {"enemy_table": table})

    spawn_actors(L, props, cls)
    spawn_walls(L)

    rescue = spawn_cls(unreal.JRRescueTarget, L["rescue"]["loc"], L["rescue"]["yaw"], "Rescue_Victim01", "L01/Gameplay",
                       {"rescue_id": "Victim01"})
    try:
        cage = rescue.get_editor_property("cage_mesh")
        cage.set_static_mesh(props["SM_Cage"])
        cage.set_relative_scale3d(unreal.Vector(1, 1, 1))
        cage.set_relative_location(unreal.Vector(0, 0, 0), False, False)
        victim = rescue.get_editor_property("victim_mesh")
        victim.set_skeletal_mesh_asset(EAL.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"))
        victim.set_relative_location(unreal.Vector(0, 0, 15), False, False)
    except Exception as exc:  # noqa: BLE001
        err("Rescue_Victim01.meshes", exc)

    nb = [L["nav_bounds"]] + L["road_nav_bounds"]
    for i, b in enumerate(nb):
        a = spawn_cls(unreal.NavMeshBoundsVolume, b["center"], 0, f"NavBounds_{i:02d}", "L01/Gameplay")
        a.set_actor_scale3d(unreal.Vector(b["size_cm"][0] / 200, b["size_cm"][1] / 200, b["size_cm"][2] / 200))

    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    for k, v in (("default_game_mode", EAL.load_blueprint_class("/Game/Core/BP_GameMode_L01")),
                 ("kill_z", float(L["kill_z_cm"])), ("force_no_precomputed_lighting", True)):
        try:
            ws.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"WorldSettings.{k}", exc)

    # ---- conferência: o terreno bate com o layout? (detecta eixo Y espelhado)
    checks = []
    for c in L["checks"]:
        checks.append({"esperado": c[2], "real": trace_z(c[0], c[1]), "espelhado": trace_z(c[0], -c[1])})
    R["checks"] = checks
    ok = sum(1 for c in checks if c["real"] is not None and abs(c["real"] - c["esperado"]) < 150)
    log(f"conferência do terreno: {ok}/{len(checks)} pontos batem")
    if ok < len(checks):
        warn("terreno não bate com o layout (ver 'checks')")

    LES.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    try:
        da = EAL.load_asset("/Game/Data/DA_Level_L01_Zombies")
        da.set_editor_property("map", EAL.load_asset(MAP))
        EAL.save_loaded_asset(da, only_if_is_dirty=False)
        log("DA_Level_L01_Zombies agora aponta para L01_ZombieValley")
    except Exception as exc:  # noqa: BLE001
        err("DA_Level.map", exc)


# ====================================================================== v3: vale aberto (l01_layout_v3.json)
V3_LAYOUT = os.path.join(SRC, "l01_layout_v3.json")
V3_TERRAIN = os.path.join(SRC, "L01_Terrain_v3.fbx")
# [A-078] peças do blockout que não entram (pedido do usuário: "item aleatório", sofá flutuando no começo)
DROP_Q = {("Acampamento", "ZombieKit/Couch"), ("Acampamento", "ZombieKit/Wheels_Stack")}
STAGES = {"DRIVING": "DRIVING", "ON_FOOT": "ON_FOOT"}
WEAPON = {"NONE": "NONE", "MELEE": "MELEE", "PISTOL": "PISTOL", "SHOTGUN": "SHOTGUN", "SNIPER": "SNIPER"}
# [A-058] rifle de precisão: o baú da vila (zona 6) passa a ter o rifle (arma tardia da fase).
SNIPER_CHEST = "Bau_Vila_Municao"
VEHICLE_CANDIDATES = ["/Game/Vehicles/BP_Vehicle_Buggy", "/Game/Vehicles/Buggy/BP_Vehicle_Buggy",
                      "/Game/Vehicles/BP_Vehicle_SUV", "/Game/Vehicles/SUV/BP_Vehicle_SUV"]


def quaternius():
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.append(here)
    import quaternius_lib  # noqa: E402
    return quaternius_lib


def rot3(r):
    """[pitch, yaw, roll] do layout -> unreal.Rotator(roll, pitch, yaw)."""
    return unreal.Rotator(float(r[2]), float(r[0]), float(r[1]))


def spawn_piece(sm, e, folder):
    a = ACTORS.spawn_actor_from_object(sm, V(e["loc"]), rot3(e["rot"]))
    if a is None:
        raise RuntimeError(f"falha ao colocar {sm.get_name()}")
    s = e["scale"]
    a.set_actor_scale3d(unreal.Vector(*[float(x) for x in s]) if isinstance(s, list) else unreal.Vector(s, s, s))
    c = a.static_mesh_component
    if e.get("cull_m"):
        try:
            c.set_editor_property("ld_max_draw_distance", float(e["cull_m"]) * 100)
        except Exception:  # noqa: BLE001
            pass
    if e.get("col") == "none":
        c.set_collision_profile_name("NoCollision")
    elif e.get("q") in PHYSICS_Q:
        make_physics(c, e["q"])
    return tagged(a, folder)


# ---------------------------------------------------------------- modelos do usuário (Tripo; ver l01_user_dressing.py)
def user_lib():
    import sys
    here = os.path.dirname(os.path.abspath(__file__))
    if here not in sys.path:
        sys.path.append(here)
    import l01_user_dressing  # noqa: E402
    return l01_user_dressing


class UserMeshes:
    """Cache das malhas /Game/Environment/User/... (None = não importada: o build usa a peça original)."""

    def __init__(self, U):
        self.U = U
        self.cache = {}

    def get(self, name):
        if name not in self.cache:
            self.cache[name] = self.U.mesh(name)
        return self.cache[name]

    def have(self, name):
        return self.get(name) is not None


def user_plan(L, terrain_actors):
    """Plano + altura do terreno de tudo que vai ser colocado (antes de existir qualquer outra peça)."""
    U = user_lib()
    um = UserMeshes(U)
    try:
        P = U.plan_v3(L, um.have)
    except Exception as exc:  # noqa: BLE001
        err("plano dos modelos do usuário", exc)
        return None, um
    pts = [(p["x"], p["y"]) for p in P["place"]]
    pts += [(c["x"], c["y"]) for c in P["chests"].values()]
    pts += [(c["x"], c["y"]) for c in P["pickups"].values()]
    zs = U.ground_z_batch(pts, terrain_actors) if pts else []
    i = 0
    for p in P["place"]:
        p["ground"] = zs[i]
        i += 1
    for c in P["chests"].values():
        c["ground"] = zs[i]
        i += 1
    for c in P["pickups"].values():
        c["ground"] = zs[i]
        i += 1
    missing = sorted({p["name"] for p in P["place"]} - {n for n in um.cache if um.cache[n]})
    R["user_assets"] = {"placed_planned": len(P["place"]), "skip_pieces": len(P["skip"]), "notes": P["notes"],
                        "groups": P.get("group_counts", {}), "no_ground": sum(1 for z in zs if z is None),
                        "missing_meshes": missing,
                        "imported": sorted(n for n, v in um.cache.items() if v)}
    log(f"modelos do usuário: {len(P['place'])} peças planejadas, {len(P['skip'])} peças originais trocadas")
    # [A-062] registro anti-sobreposição do plano (blockout + modelos + baús/itens): auditoria no relatório
    try:
        reg = P.get("registry")
        if reg is not None:
            ov = reg.find_overlaps()
            R["placement"] = {"itens": len(reg.items), "sobreposicoes": len(ov),
                              "recusados": P.get("placement_rejected", []),
                              "arquivo": "reports/placement_L01_plan.json",
                              "exemplos": [f"{a.id or a.tag} x {b.id or b.tag}" for a, b in ov[:20]]}
            reg.save(os.path.join(REPO, "reports", "placement_L01_plan.json"))
            if ov:
                warn(f"plano: {len(ov)} sobreposições (ver 'placement' no relatório)")
            log(f"registro de posicionamento: {len(reg.items)} itens, {len(ov)} sobreposições, "
                f"{len(P.get('placement_rejected', []))} enfeites recusados por bater em algo")
    except Exception as exc:  # noqa: BLE001
        warn(f"registro de posicionamento: {exc}")
    return P, um


def spawn_user(um, p, fallback_z):
    """Coloca um modelo do usuário no chão (afunda um pouco os grandes para não flutuar em rampa)."""
    sm = um.get(p["name"])
    if sm is None:
        return None
    z = p["ground"] if p.get("ground") is not None else fallback_z
    if p.get("z") is not None:
        z = p["z"]
    d = um.U.dims_m(p["name"]) or [1, 1, 1]
    sink = min(40.0, 3.0 * max(d[0], d[1])) if p["name"] not in ("CON_PostoBomba",) else 0.0
    a = ACTORS.spawn_actor_from_object(sm, unreal.Vector(p["x"], p["y"], z - sink + p.get("dz", 0.0)),
                                       unreal.Rotator(float(p.get("roll", 0)), float(p.get("pitch", 0)), float(p["yaw"])))
    if a is None:
        raise RuntimeError(f"falha ao colocar {p['name']}")
    s = p["scale"]
    if isinstance(s, list):
        a.set_actor_scale3d(unreal.Vector(*[float(x) for x in s]))
    elif s != 1.0:
        a.set_actor_scale3d(unreal.Vector(s, s, s))
    c = a.static_mesh_component
    if p.get("cull_m"):
        try:
            c.set_editor_property("ld_max_draw_distance", float(p["cull_m"]) * 100)
        except Exception:  # noqa: BLE001
            pass
    if p.get("nocol"):
        c.set_collision_profile_name("NoCollision")
    elif p["name"] in PHYSICS_USER:
        make_physics(c, p["name"])
    tagged(a, p["folder"], p.get("label"))
    return a


def user_chest(um, a, info, hinge_cm):
    """Baú com a malha do usuário: base + tampa (dobradiça atrás) ou a bomba de gasolina (sem tampa)."""
    base, lid, pivot = (a.get_editor_property(k) for k in ("base", "lid", "lid_pivot"))
    if info["kind"] == "bomba":
        base.set_static_mesh(um.get("CON_PostoBomba"))
        base.set_relative_location(unreal.Vector(0, 0, 0), False, False)
        base.set_relative_scale3d(unreal.Vector(1, 1, 1))
        lid.set_visibility(False, False)
        return
    if um.get("PRP_Bau_Base") is None or um.get("PRP_Bau_Tampa") is None:
        return
    base.set_static_mesh(um.get("PRP_Bau_Base"))
    base.set_relative_location(unreal.Vector(0, 0, 0), False, False)
    base.set_relative_scale3d(unreal.Vector(1, 1, 1))
    pivot.set_relative_location(unreal.Vector(*hinge_cm), False, False)
    lid.set_static_mesh(um.get("PRP_Bau_Tampa"))
    lid.set_relative_location(unreal.Vector(0, 0, 0), False, False)
    lid.set_relative_scale3d(unreal.Vector(1, 1, 1))


def chest_hinge_cm(U):
    """Dobradiça da tampa (Blender +Y = Unreal -Y), em cm."""
    try:
        h = json.load(open(U.PROCESSED, encoding="utf-8"))["PRP_Bau"]["parts"]["Tampa"]["hinge_m"]
        return [h[0] * 100.0, -h[1] * 100.0, h[2] * 100.0]
    except Exception:  # noqa: BLE001
        return [0.0, -36.1, 32.9]


def user_bridge(um, B):
    """Ponte de corda do usuário por cima do tabuleiro (só visual; o tabuleiro e os corrimãos dão a colisão)."""
    sm = um.get("CON_Ponte")
    if sm is None or not B:
        return
    a, b = unreal.Vector(*B["a"]), unreal.Vector(*B["b"])
    mid = unreal.Vector((a.x + b.x) / 2, (a.y + b.y) / 2, (a.z + b.z) / 2 - B["deck_end_m"] * 100.0 - 15.0)
    rot = unreal.MathLibrary.find_look_at_rotation(a, b)
    act = ACTORS.spawn_actor_from_object(sm, mid, rot)
    act.set_actor_scale3d(unreal.Vector(*B["scale"]))
    act.static_mesh_component.set_collision_profile_name("NoCollision")
    tagged(act, "L01/POI/Z4_Ponte", "U_PonteCorda")


def load_vehicle_class():
    """Classe do carro da fase (DA_Level_L01_Zombies.VehicleClass) ou um BP conhecido."""
    try:
        da = EAL.load_asset("/Game/Data/DA_Level_L01_Zombies")
        v = da.get_editor_property("vehicle_class")
        if isinstance(v, unreal.Class):
            return v
        path = str(v.export_text() if hasattr(v, "export_text") else v).strip().strip("'\"")
        if path and path != "None":
            cls = unreal.load_class(None, path)
            if cls:
                return cls
            bp = path.split(".")[0]
            if EAL.does_asset_exist(bp):
                return EAL.load_blueprint_class(bp)
    except Exception as exc:  # noqa: BLE001
        warn(f"VehicleClass do DA_Level: {exc}")
    for p in VEHICLE_CANDIDATES:
        if EAL.does_asset_exist(p):
            return EAL.load_blueprint_class(p)
    reg = unreal.AssetRegistryHelpers.get_asset_registry()
    for ad in reg.get_assets_by_path("/Game/Vehicles", recursive=True):
        n = str(ad.asset_name)
        if n.startswith("BP_Vehicle"):
            return EAL.load_blueprint_class(str(ad.package_name))
    return None


def director_tables(cls):
    def entries(rows):
        out = []
        for c, w, mx in rows:
            if cls.get(c) is None or (c == "elite" and cls["elite"] == cls["melee"]):
                continue
            e = unreal.JRDirectorEnemyEntry()
            e.set_editor_property("enemy_class", cls[c])
            e.set_editor_property("weight", float(w))
            try:
                e.set_editor_property("max_alive", int(mx))
            except Exception:  # noqa: BLE001
                pass
            out.append(e)
        return out
    # mesmas tabelas do tools/unreal/setup_ai_director.py
    return (entries([("melee", 8.0, 0), ("archer", 1.0, 0), ("gunner", 1.0, 0)]),
            entries([("melee", 10.0, 0), ("archer", 1.5, 0), ("gunner", 1.5, 0), ("elite", 0.3, 1)]))


def basic_lighting_if_missing():
    """O céu é do script setup_alien_sky.py (agente Céu). Só cria luz básica se o mapa não tiver nenhuma."""
    others = [a for a in ACTORS.get_all_level_actors()
              if isinstance(a, unreal.DirectionalLight) and TAG not in [str(t) for t in a.tags]]
    if others:
        log("luz/céu já existem (setup_alien_sky.py): não criei outros")
        return
    sun = spawn_cls(unreal.DirectionalLight, (0, 0, 50000), 0, "Sol", "L01/Luz")
    sun.set_actor_rotation(unreal.Rotator(0, -38, 125), False)
    lc = sun.light_component
    for k, v in (("intensity", 7.0), ("atmosphere_sun_light", True), ("dynamic_shadow_distance_movable_light", 25000.0)):
        try:
            lc.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"sol.{k}: {exc}")
    lc.set_mobility(unreal.ComponentMobility.MOVABLE)
    spawn_cls(unreal.SkyAtmosphere, (0, 0, 0), 0, "Ceu", "L01/Luz")
    sky = spawn_cls(unreal.SkyLight, (0, 0, 2000), 0, "LuzDoCeu", "L01/Luz")
    sky.light_component.set_mobility(unreal.ComponentMobility.MOVABLE)
    try:
        sky.light_component.set_editor_property("real_time_capture", True)
    except Exception as exc:  # noqa: BLE001
        warn(f"skylight: {exc}")
    fog = spawn_cls(unreal.ExponentialHeightFog, (0, 0, 0), 0, "Neblina", "L01/Luz")
    try:
        fog.component.set_editor_property("fog_density", 0.004)
        fog.component.set_editor_property("fog_inscattering_luminance", unreal.LinearColor(0.45, 0.32, 0.6, 1))
    except Exception as exc:  # noqa: BLE001
        warn(f"neblina: {exc}")
    log("luz básica criada (rode setup_alien_sky.py para o céu alienígena)")


def main_v3():
    L = json.load(open(V3_LAYOUT, encoding="utf-8"))
    R["layout"] = "v3"
    Q = quaternius()
    mat = material()
    glow = load_mat(GLOW_MAT)
    mat_terrain = load_mat(f"{ENV}/Materials/M_L01_Terrain")
    mat_road = load_mat(f"{ENV}/Materials/M_L01_Road")
    toxic = EAL.load_asset(f"{ENV}/Materials/M_L01_Toxic") if EAL.does_asset_exist(f"{ENV}/Materials/M_L01_Toxic") else None

    # ---- malhas: terreno v3, props L01 (arco, ponte, disco...), Quaternius
    terrain_paths = import_fbx(V3_TERRAIN, f"{ENV}/TerrainV3", False)
    terrain = [prep_mesh(p, mat_road if "_Road_" in p else mat_terrain, True) for p in terrain_paths]
    props = {}
    for f in ("L01_Props.fbx", "L01_Props2.fbx", "L01_Props3.fbx"):
        fp = os.path.join(SRC, f)
        if not os.path.exists(fp):
            warn(f"faltando {f}")
            continue
        for p in import_fbx(fp, f"{ENV}/Props", True):
            name = p.split("/")[-1]
            sm = prep_mesh(p, mat, name in COMPLEX, glow)
            if sm:
                props[name] = sm
    if EAL.does_asset_exist("/Game/Weapons/SM_AlienStick"):
        props["SM_AlienStick"] = EAL.load_asset("/Game/Weapons/SM_AlienStick")
    want = {}
    for poi in L["pois"]:
        for e in poi["pieces"]:
            if e.get("q"):
                cur = want.get(e["q"], "none")
                want[e["q"]] = "complex" if "complex" in (cur, e["col"]) else ("simple" if "simple" in (cur, e["col"]) else "none")
    for g in L["gates"]:
        for key in ("mesh_q", "pieces_q"):
            if g.get(key):
                want.setdefault(g[key], "simple")
    qmesh, qsize = {}, {}
    for ref, col in sorted(want.items()):
        sm = Q.load_static(ref, collision=col)
        if sm:
            qmesh[ref] = sm
            qsize[ref] = Q.size_m(sm)
        else:
            warn(f"Quaternius ausente: {ref}")
    R["quaternius_sizes_m"] = qsize
    R["quaternius_log"] = Q.LOG[-60:]
    engine = {n: EAL.load_asset(f"/Engine/BasicShapes/{n}") for n in ("Cone", "Cube", "Plane", "Cylinder")}

    open_map()
    terrain_actors = []
    for sm in terrain:
        if sm:
            terrain_actors.append(spawn_mesh(sm, (0, 0, 0), folder="L01/Terreno"))
    R["counts"]["terrain_actors"] = len([t for t in terrain if t])

    # ---- modelos do usuário: plano + altura do chão (só o terreno existe agora)
    UP, um = user_plan(L, terrain_actors)
    skip = UP["skip"] if UP else set()
    hide = UP["hide"] if UP else set()

    # ---- blockouts dos pontos de interesse (peças trocadas por modelos do usuário são puladas)
    n = 0
    for poi in L["pois"]:
        folder = f"L01/POI/Z{poi['zone']}_{poi['key']}"
        for i, e in enumerate(poi["pieces"]):
            if (poi["key"], i) in skip:
                continue
            if (poi["key"], e.get("q")) in DROP_Q:   # [A-078] sofá e pneus no acampamento: sem sentido
                continue
            sm = qmesh.get(e["q"]) if e.get("q") else (props.get(e["mesh"]) if e.get("mesh") else engine.get(e.get("engine")))
            if sm is None:
                warn(f"{poi['key']}: malha ausente {e.get('q') or e.get('mesh') or e.get('engine')}")
                continue
            try:
                a = spawn_piece(sm, e, folder)
                if (poi["key"], i) in hide:      # corrimão da ponte: some no jogo, a colisão fica
                    a.set_actor_hidden_in_game(True)
                    a.set_is_temporarily_hidden_in_editor(True)
                n += 1
            except Exception as exc:  # noqa: BLE001
                err(f"{poi['key']} peça", exc)
    R["counts"]["poi_pieces"] = n
    log(f"{n} peças de blockout nos POIs")

    # ---- modelos do usuário (Tripo) em tamanho real: POIs, marcos, portões e grupos de cenário
    nu = 0
    if UP:
        for p in UP["place"]:
            try:
                # sem chão achado: usa a altura do POI mais perto
                near = min(L["pois"], key=lambda q: (q["loc"][0] - p["x"]) ** 2 + (q["loc"][1] - p["y"]) ** 2)
                if spawn_user(um, p, near["loc"][2]):
                    nu += 1
            except Exception as exc:  # noqa: BLE001
                err(f"usuário {p['name']}", exc)
        try:
            user_bridge(um, UP["bridge"])
        except Exception as exc:  # noqa: BLE001
            err("ponte de corda", exc)
    R["counts"]["user_pieces"] = nu
    log(f"{nu} modelos do usuário colocados")

    # ---- saltos (rampa + aterrissagem) nas rotas alternativas
    for j in L.get("jumps", []):
        for key, mesh in (("ramp", "SM_Ramp"), ("landing", "SM_RampLanding")):
            if props.get(mesh):
                spawn_mesh(props[mesh], j[key]["loc"], j[key]["yaw"], [1.0, 1.4, 1.0], "L01/Saltos", 900)

    # ---- luzes pontuais (fogo da nave, árvore-mãe, colmeia, disco...)
    for li in L["lights"]:
        try:
            a = spawn_cls(unreal.PointLight, li["loc"], 0, li["label"], "L01/Luz/Pontos")
            pc = a.point_light_component
            pc.set_mobility(unreal.ComponentMobility.MOVABLE)
            pc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)   # [A-063]
            pc.set_editor_property("intensity", float(li["intensity"]) * LIGHT_CD_PER_LAYOUT)
            pc.set_editor_property("attenuation_radius", float(li["radius_cm"]))
            c = li["color"]
            pc.set_editor_property("light_color", unreal.Color(r=int(c[0] * 255), g=int(c[1] * 255), b=int(c[2] * 255), a=255))
            pc.set_editor_property("cast_shadows", False)
        except Exception as exc:  # noqa: BLE001
            err(li["label"], exc)
    basic_lighting_if_missing()

    # ---- carro da fase (buggy estacionado no acampamento; o jogador começa a pé)
    vcls = load_vehicle_class()
    if vcls:
        vs = L["vehicle_start"]
        try:
            car = spawn_cls(vcls, vs["loc"], vs["yaw"], "Buggy_Fase", "L01/Gameplay")
            try:
                car.set_editor_property("auto_possess_ai", unreal.AutoPossessAI.DISABLED)
            except Exception as exc:  # noqa: BLE001
                warn(f"auto_possess_ai: {exc}")
            try:
                car.set_editor_property("required_key_item", "CarKey")
            except Exception as exc:  # noqa: BLE001
                warn(f"required_key_item (compile o C++ novo): {exc}")
        except Exception as exc:  # noqa: BLE001
            err("Buggy_Fase", exc)
    else:
        err("Buggy_Fase", RuntimeError("classe do carro não encontrada (DA_Level_L01_Zombies.VehicleClass)"))

    # ---- checkpoints (o primeiro é o início, a pé)
    for c in L["checkpoints"]:
        props_cp = {"checkpoint_id": c["id"], "stage_on_respawn": getattr(unreal.JRLevelStage, c["stage"]),
                    "is_vehicle_transition": bool(c["transition"]), "is_level_start": bool(c["level_start"]),
                    "respawn_with_melee": c["respawn_melee"], "respawn_with_pistol": c["respawn_pistol"],
                    "respawn_with_shotgun": c["respawn_shotgun"]}
        extra = {"respawn_key_items": [unreal.Name(x) for x in c["respawn_key_items"]]}
        if c.get("park_vehicle"):
            extra.update({"park_vehicle_on_respawn": True, "vehicle_park_location": V(c["park_vehicle"]["loc"]),
                          "vehicle_park_yaw": float(c["park_vehicle"]["yaw"])})
        if c.get("vehicle_needs_item"):
            extra.update({"vehicle_needs_item": unreal.Name(c["vehicle_needs_item"]),
                          "vehicle_needs_item_label": "o galão de gasolina"})
        a = spawn_cls(unreal.JRCheckpoint, c["loc"], c["yaw"], c["label"], "L01/Gameplay/Checkpoints", props_cp)
        for k, v in extra.items():
            try:
                a.set_editor_property(k, v)
            except Exception as exc:  # noqa: BLE001
                err(f"{c['label']}.{k} (compile o C++ novo)", exc)
        if c["level_start"]:
            spawn_cls(unreal.PlayerStart, c["loc"], c["yaw"], "PlayerStart", "L01/Gameplay")

    cls = {"melee": EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieMelee"),
           "archer": EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieArcher"),
           "gunner": EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieGunner")}
    cls["elite"] = (EAL.load_blueprint_class("/Game/Enemies/BP_Enemy_ZombieElite")
                    if EAL.does_asset_exist("/Game/Enemies/BP_Enemy_ZombieElite") else cls["melee"])
    for e in L["enemies"]:
        try:
            spawn_cls(cls.get(e["type"], cls["melee"]), e["loc"], 0, e["label"], "L01/Inimigos")
        except Exception as exc:  # noqa: BLE001
            err(e["label"], exc)
    R["counts"]["enemies"] = len(L["enemies"])

    # ---- itens, baús, histórias
    shown = UP["pickup_display"] if UP else {}
    for p in L["pickups"]:
        try:
            loc = list(p["loc"])
            mv = UP["pickups"].get(p["label"]) if UP else None
            if mv:      # item que estava dentro de prédio trocado por um fechado
                # [A-063] no chão (era +80 cm); o JRPickup ainda se apoia sozinho no BeginPlay
                loc = [mv["x"], mv["y"], (mv["ground"] + 20.0) if mv.get("ground") is not None else loc[2]]
            act = spawn_cls(unreal.JRPickup, loc, 0, p["label"], "L01/Itens",
                            {"type": getattr(unreal.JRPickupType, PICKUP[p["type"]]), "amount": float(p["amount"])})
            if shown.get(p["type"]) and um.get(shown[p["type"]]):
                # malha do usuário em tamanho real (itens 1,3x para ler de longe; precisa do C++ novo do JRPickup)
                act.set_editor_property("display_mesh", um.get(shown[p["type"]]))
                act.set_editor_property("display_scale", 1.0 if p["type"].startswith("WEAPON") else 1.3)
            elif p.get("display") and props.get(p["display"]):
                act.set_editor_property("display_mesh", props[p["display"]])
        except Exception as exc:  # noqa: BLE001
            err(p["label"], exc)
    hinge = chest_hinge_cm(um.U) if UP else None
    for ch in L["chests"]:
        try:
            loc, yaw = list(ch["loc"]), ch["yaw"]
            info = UP["chests"].get(ch["label"]) if UP else None
            if info:    # dentro da barraca / na boca da colmeia / no lugar da bomba
                loc = [info["x"], info["y"], info["ground"] if info.get("ground") is not None else loc[2]]
                yaw = info["yaw"]
            a = spawn_cls(unreal.JRLootChest, loc, yaw, ch["label"], "L01/Itens",
                          {"weapon_inside": getattr(unreal.JRWeaponSlot, WEAPON[ch["weapon"]]),
                           "ammo_inside": int(ch["ammo"]), "health_inside": float(ch["health"])})
            if UP:
                try:
                    user_chest(um, a, info or {"kind": "bau"}, hinge)
                except Exception as exc:  # noqa: BLE001
                    warn(f"{ch['label']}: malha do baú do usuário: {exc}")
            if ch["label"] == SNIPER_CHEST:  # [A-058] (precisa do C++ com EJRWeaponSlot::Sniper)
                try:
                    a.set_editor_property("weapon_inside", unreal.JRWeaponSlot.SNIPER)
                except Exception as exc:  # noqa: BLE001
                    warn(f"{SNIPER_CHEST}: sem rifle ({exc})")
            if ch.get("key_item"):
                a.set_editor_property("key_item_inside", unreal.Name(ch["key_item"]))
                a.set_editor_property("key_item_label", ch["key_label"])
            if ch.get("horde"):
                a.set_editor_property("trigger_horde_on_open", True)
                a.set_editor_property("horde_size", int(ch["horde"]["size"]))
                a.set_editor_property("horde_duration", float(ch["horde"]["duration"]))
        except Exception as exc:  # noqa: BLE001
            err(f"{ch['label']} (compile o C++ novo)", exc)
    for s in L["story"]:
        try:
            a = spawn_cls(unreal.JRStoryTrigger, s["loc"], 0, s["label"], "L01/Historia",
                          {"message": s["message"], "objective_hint": s["objective_hint"], "on_foot_only": bool(s["on_foot_only"])})
            set_box(a, "box", s["box_extent"], s["label"])
            if s.get("completes_level"):
                a.set_editor_property("completes_level", True)
        except Exception as exc:  # noqa: BLE001
            err(s["label"], exc)

    # ---- portões
    for g in L["gates"]:
        try:
            if g["type"] == "explosive":
                a = spawn_cls(unreal.JRBlockingGate, g["loc"], g["yaw"], g["label"], "L01/Gameplay/Portoes",
                              {"required_item": unreal.Name(g["required_item"]), "horde_size": int(g["horde"]["size"]),
                               "horde_duration": float(g["horde"]["duration"])})
                set_box(a, "block_volume", g["block_extent_cm"], g["label"])
                mc = a.get_editor_property("blocker_mesh")
                ug = UP["gates"].get(g["label"]) if UP else None
                if isinstance(ug, dict) and um.get(ug["mesh"]):
                    # árvore morta do usuário (8 m x 2 = 16 m) deitada atravessando a ponte
                    s = float(ug["scale"])
                    mc.set_static_mesh(um.get(ug["mesh"]))
                    mc.set_relative_location(V(ug["rel_loc"]), False, False)
                    mc.set_relative_rotation(rot3(ug["rel_rot"]), False, False)
                    mc.set_relative_scale3d(unreal.Vector(s, s, s))
                elif qmesh.get(g["mesh_q"]):
                    mc.set_static_mesh(qmesh[g["mesh_q"]])
                    mc.set_relative_location(V(g["mesh_rel_loc_cm"]), False, False)
                    mc.set_relative_rotation(rot3(g["mesh_rel_rot"]), False, False)
                    mc.set_relative_scale3d(unreal.Vector(g["mesh_scale"], g["mesh_scale"], g["mesh_scale"]))
            elif UP and isinstance(UP["gates"].get(g["label"]), list):
                log(f"{g['label']}: portão + barricada do usuário (vão de 1,7 m a pé)")
            elif g.get("pieces_q") and qmesh.get(g["pieces_q"]):
                import math
                yaw = math.radians(g["yaw"])
                # eixo lateral (Unreal: y para o sul) do portão
                ox, oy = -math.sin(yaw), math.cos(yaw)
                for i, off in enumerate(g["offsets_m"]):
                    loc = [g["loc"][0] + ox * off * 100, g["loc"][1] + oy * off * 100, g["loc"][2]]
                    spawn_mesh(qmesh[g["pieces_q"]], loc, g["yaw"] + 90, 1.0, "L01/Gameplay/Portoes")
        except Exception as exc:  # noqa: BLE001
            err(f"{g['label']} (compile o C++ novo)", exc)

    # ---- barricada de corpos (Z3)
    for b in L["barricades"]:
        try:
            a = spawn_cls(unreal.JRZombieBarricade, b["loc"], b["yaw"], b["label"], "L01/Gameplay",
                          {"enemy_classes": [cls["melee"]], "count": int(b["count"]), "width": float(b["width_cm"]),
                           "break_speed_kmh": float(b["break_speed_kmh"])})
            meshes = [um.get(m) for m in (UP["barricade_meshes"] if UP else []) if um.get(m)]
            if not meshes:
                meshes = [props[m] for m in ("SM_CarWreck", "SM_Crate", "SM_Barricade") if props.get(m)]
            if meshes:
                a.set_editor_property("prop_meshes", meshes)
        except Exception as exc:  # noqa: BLE001
            err(b["label"], exc)

    # ---- perigos: lago tóxico e rio (cair = voltar ao checkpoint), com plano visível
    plane = engine["Plane"]
    for h in L["hazards"]:
        try:
            a = spawn_cls(unreal.JRHazardVolume, h["loc"], h["yaw"], h["label"], "L01/Perigos",
                          {"instant_fail": bool(h["instant_fail"]), "damage_per_second": float(h["damage_per_second"])})
            set_box(a, "box", h["box_extent_cm"], h["label"])
            if h["kind"] == "toxic_lake":
                pa = spawn_mesh(plane, h["plane_loc"], 0, [h["plane_size_m"][0], h["plane_size_m"][1], 1.0], "L01/Perigos", 0, True)
            else:   # rio: plano 1,2 m acima do leito
                ex = h["box_extent_cm"]
                pa = spawn_mesh(plane, [h["loc"][0], h["loc"][1], h["loc"][2] + 20], h["yaw"],
                                [ex[0] / 50.0, 30.0, 1.0], "L01/Perigos", 0, True)
            if toxic:
                pa.static_mesh_component.set_material(0, toxic)
        except Exception as exc:  # noqa: BLE001
            err(h["label"], exc)

    # ---- zonas do diretor + UM diretor de IA
    for dz in L["director_zones"]:
        try:
            a = spawn_cls(unreal.JRDirectorZone, dz["loc"], dz["yaw"], dz["label"], "L01/Gameplay/Diretor",
                          {"no_spawns": dz["no_spawns"], "block_event_hordes": dz["block_event_hordes"],
                           "density_multiplier": float(dz["density"]), "intensity_decay_multiplier": float(dz["decay"]),
                           "priority": int(dz["priority"])})
            set_box(a, "box", dz["extent_cm"], dz["label"])
        except Exception as exc:  # noqa: BLE001
            err(dz["label"], exc)
    old = [a for a in ACTORS.get_all_level_actors() if isinstance(a, unreal.JRAIDirector)]
    for a in old:
        ACTORS.destroy_actor(a)
    build_up, peak = director_tables(cls)
    z0 = L["zones"][0]["center"]
    spawn_cls(unreal.JRAIDirector, [z0[0], z0[1], z0[2] + 500], 0, "AIDirector", "L01/Gameplay/Diretor",
              {"build_up_table": build_up, "peak_table": peak, "enemy_table": []})

    # ---- horda da vila (defesa) + resgate (não termina a fase: ainda tem a saída de carro)
    hd = L["horde"]
    points = [spawn_cls(unreal.TargetPoint, p, 0, f"Horde_Spawn_{i + 1:02d}", "L01/Gameplay") for i, p in enumerate(hd["spawn_points"])]
    waves = []
    for c, count, interval in hd["waves"]:
        w = unreal.JRWave()
        w.set_editor_property("enemy_class", cls[c])
        w.set_editor_property("count", int(count))
        w.set_editor_property("spawn_interval", float(interval))
        waves.append(w)
    horde = spawn_cls(unreal.JRHordeDirector, hd["loc"], 0, "HordeDirector_Vila", "L01/Gameplay",
                      {"waves": waves, "spawn_points": points, "is_final_horde": True, "min_spawn_distance": 1500.0, "max_alive": 30})
    set_box(horde, "activation_trigger", hd["trigger_extent_cm"], "HordeDirector_Vila")
    rs = L["rescue"]
    rescue = spawn_cls(unreal.JRRescueTarget, rs["loc"], rs["yaw"], "Rescue_Victim01", "L01/Gameplay", {"rescue_id": "Victim01"})
    try:
        rescue.set_editor_property("complete_level_on_rescue", bool(rs["complete_level_on_rescue"]))
    except Exception as exc:  # noqa: BLE001
        err("Rescue.complete_level_on_rescue (compile o C++ novo)", exc)
    try:
        cage = rescue.get_editor_property("cage_mesh")
        if UP and UP["cage"] and um.get(UP["cage"]):
            # cela do usuário (3 x 3 x 3 m, porta em +X). Sem colisão: o abraço do resgate põe o herói a 80 cm
            # do centro, ou seja, DENTRO da cela; com colisão ele ficaria preso.
            cage.set_static_mesh(um.get(UP["cage"]))
            cage.set_relative_scale3d(unreal.Vector(1, 1, 1))
            cage.set_relative_location(unreal.Vector(0, 0, 0), False, False)
            cage.set_collision_profile_name("NoCollision")
        elif props.get("SM_Cage"):
            cage.set_static_mesh(props["SM_Cage"])
        victim = rescue.get_editor_property("victim_mesh")
        # A-053 (setup_zombie_models.py): sobrevivente rigado em loop se já importado; senão a Quinn de antes
        sv_mesh, sv_idle = "/Game/Characters/Survivor/SK_NPC_Sobrevivente", "/Game/Characters/Survivor/A_NPC_Sobrevivente_Idle"
        if EAL.does_asset_exist(sv_mesh) and EAL.does_asset_exist(sv_idle):
            victim.set_skeletal_mesh_asset(EAL.load_asset(sv_mesh))
            victim.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
            sv_data = unreal.SingleAnimationPlayData()
            sv_data.set_editor_property("anim_to_play", EAL.load_asset(sv_idle))
            sv_data.set_editor_property("saved_looping", True)
            sv_data.set_editor_property("saved_playing", True)
            victim.set_editor_property("animation_data", sv_data)
        else:
            victim.set_skeletal_mesh_asset(EAL.load_asset("/Game/Characters/Mannequins/Meshes/SKM_Quinn_Simple"))
        # fim A-053
        victim.set_relative_location(unreal.Vector(0, 0, 15), False, False)
    except Exception as exc:  # noqa: BLE001
        err("Rescue_Victim01.meshes", exc)

    # ---- paredes invisíveis só na borda do mapa
    spawn_walls(L)
    # ---- navegação: uma caixa por zona
    for i, b in enumerate(L["nav_bounds"]):
        a = spawn_cls(unreal.NavMeshBoundsVolume, b["center"], 0, f"NavBounds_Z{b['zone']}", "L01/Gameplay")
        a.set_actor_scale3d(unreal.Vector(b["size_cm"][0] / 200, b["size_cm"][1] / 200, b["size_cm"][2] / 200))

    ws = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world().get_world_settings()
    for k, v in (("default_game_mode", EAL.load_blueprint_class("/Game/Core/BP_GameMode_L01")),
                 ("kill_z", float(L["kill_z_cm"])), ("force_no_precomputed_lighting", True)):
        try:
            ws.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"WorldSettings.{k}", exc)

    # ---- [A-064] tarefas: cada gatilho de história aponta para o seu alvo (item, baú, carro, ponto)
    try:
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.append(here)
        import l01_tasks  # noqa: E402
        R["tasks"] = l01_tasks.apply(L, log, warn)
    except Exception as exc:  # noqa: BLE001
        err("tarefas (l01_tasks)", exc)

    checks = [{"esperado": c[2], "real": trace_z(c[0], c[1]), "espelhado": trace_z(c[0], -c[1])} for c in L["checks"]]
    R["checks"] = checks
    ok = sum(1 for c in checks if c["real"] is not None and abs(c["real"] - c["esperado"]) < 150)
    log(f"conferência do terreno: {ok}/{len(checks)} pontos batem")
    if ok < len(checks):
        warn("terreno não bate com o layout (ver 'checks')")

    # ---- céu alienígena (agente Céu), se o script existir
    try:
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.append(here)
        import setup_alien_sky  # noqa: E402
        setup_alien_sky.apply_to_current_level(save=False)
        log("céu alienígena aplicado (setup_alien_sky.apply_to_current_level)")
    except Exception as exc:  # noqa: BLE001
        warn(f"céu alienígena não aplicado ({exc}); rode setup_alien_sky.py depois")

    LES.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    try:
        da = EAL.load_asset("/Game/Data/DA_Level_L01_Zombies")
        da.set_editor_property("map", EAL.load_asset(MAP))
        EAL.save_loaded_asset(da, only_if_is_dirty=False)
    except Exception as exc:  # noqa: BLE001
        err("DA_Level.map", exc)
    # ---- [A-078] enfeites pequenos no chão (nada flutuando nem enterrado)
    try:
        import sys
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.append(here)
        import l01_ground_snap  # noqa: E402
        R["ground_snap"] = len(l01_ground_snap.snap_all(log=log))
    except Exception as exc:  # noqa: BLE001
        warn(f"assentar enfeites no chão falhou ({exc}); rode fix_l01_props_a078.py")
    # ---- [A-070] construções com interior: só depois de aprovadas (assets/work/interiors/APROVADO.txt)
    try:
        import sys
        import runpy
        here = os.path.dirname(os.path.abspath(__file__))
        if here not in sys.path:
            sys.path.append(here)
        import l01_interiors  # noqa: E402
        if l01_interiors.enabled():
            runpy.run_path(os.path.join(here, "build_interiors_l01.py"), run_name="build_interiors_via_build_l01")
            log("construções com interior aplicadas (reports/build_interiors_l01.json)")
    except Exception as exc:  # noqa: BLE001
        warn(f"construções com interior não aplicadas ({exc}); rode build_interiors_l01.py depois")
    # ---- [A-060] vegetação densa (agente Densidade): tools/unreal/scatter_l01.py, se os dados existirem
    try:
        if os.path.exists(os.path.join(SRC, "l01_scatter_v3.json")):
            import sys
            here = os.path.dirname(os.path.abspath(__file__))
            if here not in sys.path:
                sys.path.append(here)
            import scatter_l01  # noqa: E402
            sr = scatter_l01.run(open_level=False, save=True)
            scatter_l01.write_report()
            R["counts"]["scatter_instances"] = sr.get("total", 0)
            log(f"vegetação: {sr.get('total', 0)} instâncias (reports/scatter_l01.json)")
    except Exception as exc:  # noqa: BLE001
        warn(f"vegetação não aplicada ({exc}); rode tools/unreal/scatter_l01.py depois")
    # ---- [A-060] fim
    # ---- [A-077] mirantes no alto dos morros e [A-074] abertura: os dois dependem do mapa recém-montado
    try:
        import runpy
        here = os.path.dirname(os.path.abspath(__file__))
        if os.path.exists(os.path.join(SRC, "l01_mirantes_v2.json")):
            runpy.run_path(os.path.join(here, "build_mirantes_l01.py"), run_name="build_mirantes_via_build_l01")
            log("mirantes aplicados (reports/build_mirantes_l01.json)")
        if hasattr(unreal, "JRIntroDirector") and os.path.exists(os.path.join(here, "setup_intro.py")):
            runpy.run_path(os.path.join(here, "setup_intro.py"), run_name="setup_intro_via_build_l01")
            log("abertura ligada (reports/setup_intro.json)")
    except Exception as exc:  # noqa: BLE001
        warn(f"mirantes/abertura não aplicados ({exc}); rode build_mirantes_l01.py e setup_intro.py depois")
    log("v3 pronto. Depois: setup_minimap.py (minimapa v3) e setup_alien_sky.py (céu)")


def run_build():
    import sys
    force_v2 = any(a.lower() == "v2" for a in sys.argv[1:])
    if os.path.exists(V3_LAYOUT) and not force_v2:
        main_v3()
    else:
        R["layout"] = "v2"
        main()


try:
    run_build()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    with open(os.path.join(REPO, "reports", "build_l01.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[build_l01] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
