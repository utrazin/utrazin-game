"""Construções com interior na L01 (A-070): importa, troca os modelos antigos e mobilia. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), depois de compilar o C++ (AJRCameraZone) e SÓ DEPOIS DO OK do usuário
nas prévias (assets/work/interiors/previews):
  py "E:/game/utrazin-game/tools/unreal/build_interiors_l01.py"
Relatório: reports/build_interiors_l01.json. Depois: Build > Build Paths.

Entradas (geradas fora da Unreal):
  assets/work/interiors/SM_INT_*.fbx                  cascas e móveis (tools/blender/gen_interiors_l01.py)
  assets/work/interiors/interiors_l01.json             móveis, luzes, itens, zona de câmera de cada construção
  assets/work/interiors/interiors_placement_l01.json  onde cada uma fica (tools/unreal/l01_interiors.py)
Faz:
 1. importa as malhas em /Game/Environment/Interiors (colisão UCX do FBX) e põe os materiais: paredes e pisos com
    MI_User_<Nome> (texturas repetíveis do usuário, alinhadas ao mundo), vidro translúcido M_INT_Vidro, cores lisas
    MI_INT_<Nome> (filhas de M_INT_Flat);
 2. apaga os atores da versão anterior deste script (tag L01Interior) e os modelos trocados (loja do posto, casas e
    cabana da vila, contêiner, peças de blockout da sala trancada), além de enfeites que caíram dentro;
 3. coloca cada construção no chão (piso acima do ponto mais alto do terreno embaixo; a base funda e as rampas
    cobrem o lado baixo), os móveis, luminárias + luzes fracas (candelas), itens (JRPickup), zona de câmera
    (AJRCameraZone: braço de 1,9 m dentro) e o gatilho de história dos lugares novos (só mensagem, sem tarefa);
 3b. [A-076] coloca as portas (AJRDoor) em cada vão: folha de madeira, metal ou vidro, porta dupla nos vãos largos;
    portões de 3 m ou mais já começam abertos (o buggy passa);
 4. leva os baús que moram dentro (Bau_Pistola_Posto, Bau_Vila_Municao) para dentro;
 5. salva o mapa.
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
for p in (HERE, os.path.join(REPO, "tools", "pipeline")):
    if p not in sys.path:
        sys.path.append(p)
import l01_interiors as I  # noqa: E402
import l01_user_dressing as U  # noqa: E402

MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
DEST = "/Game/Environment/Interiors"
MATS = f"{DEST}/Materials"
USER_MATS = "/Game/Environment/User/Materials"
TAG = "L01Interior"
FOLDER = "L01/Interiores"
LIGHT_CD = 30.0
LIGHT_RADIUS_CM = 700.0
# [A-076] enfeites de chão/parede sem colisão (o herói passa por cima): sem caixa UCX de propósito
DECOR = {"SM_INT_Lixo", "SM_INT_Tapete", "SM_INT_Quadro", "SM_INT_Luminaria"}
AMOUNT = {"AMMO": 12.0, "HEALTH": 35.0, "BANDAGE": 1.0, "MEDKIT": 1.0, "FURY": 12.0, "REPAIR": 30.0, "NITRO": 0.3}
# o mesmo de gen_interiors_l01.FLAT (cor, rugosidade, emissão)
FLAT = {"Pintura": (0.78, 0.80, 0.84, 0.6, 0), "Metal": (0.42, 0.45, 0.50, 0.35, 0), "Escuro": (0.10, 0.11, 0.14, 0.5, 0),
        "Vermelho": (0.72, 0.16, 0.14, 0.5, 0), "Azul": (0.16, 0.34, 0.68, 0.5, 0), "Amarelo": (0.95, 0.70, 0.15, 0.5, 0),
        "Verde": (0.20, 0.55, 0.30, 0.5, 0), "Laranja": (0.92, 0.45, 0.12, 0.5, 0), "Branco": (0.92, 0.92, 0.90, 0.4, 0),
        "Tecido": (0.30, 0.36, 0.55, 0.9, 0), "Couro": (0.40, 0.20, 0.12, 0.7, 0), "Colchao": (0.85, 0.82, 0.74, 0.9, 0),
        "Tela": (0.10, 0.70, 0.75, 0.3, 2.0), "Geladeira": (0.70, 0.90, 1.00, 0.1, 0.6), "Cristal": (0.30, 0.95, 0.90, 0.2, 3.0),
        "Lampada": (1.00, 0.90, 0.70, 0.3, 6.0), "Borracha": (0.06, 0.06, 0.07, 0.8, 0), "Papel": (0.90, 0.87, 0.78, 0.9, 0)}

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "buildings": {}, "removed": [],
     "chests_moved": [], "materials": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[build_interiors] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[build_interiors] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-800:]})
    unreal.log_error(f"[build_interiors] {where}: {exc}")


# ---------------------------------------------------------------- materiais
def ensure_flat_master():
    path = f"{MATS}/M_INT_Flat"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    EAL.make_directory(MATS)
    m = TOOLS.create_asset("M_INT_Flat", MATS, unreal.Material, unreal.MaterialFactoryNew())
    col = MEL.create_material_expression(m, unreal.MaterialExpressionVectorParameter, -600, 0)
    col.set_editor_property("parameter_name", "Color")
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 200)
    rough.set_editor_property("parameter_name", "Roughness")
    rough.set_editor_property("default_value", 0.6)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    metal = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 300)
    metal.set_editor_property("parameter_name", "Metallic")
    MEL.connect_material_property(metal, "", unreal.MaterialProperty.MP_METALLIC)
    emi = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 400)
    emi.set_editor_property("parameter_name", "Emissive")
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 380)
    MEL.connect_material_expressions(col, "", mul, "A")
    MEL.connect_material_expressions(emi, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, only_if_is_dirty=False)
    return m


def ensure_glass():
    path = f"{MATS}/M_INT_Vidro"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    EAL.make_directory(MATS)
    m = TOOLS.create_asset("M_INT_Vidro", MATS, unreal.Material, unreal.MaterialFactoryNew())
    m.set_editor_property("blend_mode", unreal.BlendMode.BLEND_TRANSLUCENT)
    m.set_editor_property("two_sided", True)
    col = MEL.create_material_expression(m, unreal.MaterialExpressionConstant3Vector, -500, 0)
    col.set_editor_property("constant", unreal.LinearColor(0.55, 0.68, 0.72, 1))
    MEL.connect_material_property(col, "", unreal.MaterialProperty.MP_BASE_COLOR)
    op = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -500, 200)
    op.set_editor_property("r", 0.28)
    MEL.connect_material_property(op, "", unreal.MaterialProperty.MP_OPACITY)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -500, 300)
    rough.set_editor_property("r", 0.15)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, only_if_is_dirty=False)
    return m


_mat_cache = {}


def material_for(slot):
    """Nome do slot (o nome do material no Blender) -> material da Unreal."""
    if slot in _mat_cache:
        return _mat_cache[slot]
    m = None
    if slot.startswith("MI_User_"):
        if slot == "MI_User_VidroSujo":
            m = ensure_glass()
        else:
            p = f"{USER_MATS}/{slot}"
            m = EAL.load_asset(p) if EAL.does_asset_exist(p) else None
            if m is None:
                warn(f"{p} não existe (rode import_user_assets.py): usando cor lisa")
                m = flat_mi("Pintura")
    elif slot.startswith("M_INT_"):
        m = flat_mi(slot[len("M_INT_"):])
    _mat_cache[slot] = m
    R["materials"][slot] = m.get_path_name().split(".")[0] if m else None
    return m


def flat_mi(name):
    path = f"{MATS}/MI_INT_{name}"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    master = ensure_flat_master()
    mi = TOOLS.create_asset(f"MI_INT_{name}", MATS, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    MEL.set_material_instance_parent(mi, master)
    r, g, b, rough, emit = FLAT.get(name, FLAT["Pintura"])
    MEL.set_material_instance_vector_parameter_value(mi, "Color", unreal.LinearColor(r, g, b, 1))
    MEL.set_material_instance_scalar_parameter_value(mi, "Roughness", float(rough))
    MEL.set_material_instance_scalar_parameter_value(mi, "Metallic", 0.8 if name == "Metal" else 0.0)
    MEL.set_material_instance_scalar_parameter_value(mi, "Emissive", float(emit) * 0.25)   # exposição fixa: brilho leve
    EAL.save_loaded_asset(mi, only_if_is_dirty=False)
    return mi


# ---------------------------------------------------------------- malhas
def import_mesh(name):
    fbx = os.path.join(I.INT_DIR, f"{name}.fbx")
    path = f"{DEST}/{name}"
    if not os.path.exists(fbx):
        warn(f"falta {fbx}")
        return EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = DEST
    task.destination_name = name
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
    for k, v in (("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("build_nanite", False), ("one_convex_hull_per_ucx", True), ("import_uniform_scale", 1.0)):
        try:
            d.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: opção {k}: {exc}")
    task.options = o
    TOOLS.import_asset_tasks([task])
    sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if not isinstance(sm, unreal.StaticMesh):
        raise RuntimeError(f"{name} não virou StaticMesh")
    for i, slot in enumerate(sm.get_editor_property("static_materials")):
        sname = str(slot.get_editor_property("material_slot_name"))
        m = material_for(sname)
        if m:
            sm.set_material(i, m)
    try:
        cnt = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem).get_simple_collision_count(sm)
        if cnt == 0 and name not in DECOR:
            # [A-078] a UCX não vira colisão na importação deste projeto: usa a própria malha (parede com vão,
            # piso e móveis seguram o herói e os zumbis)
            bs = sm.get_editor_property("body_setup")
            if bs is not None:
                sm.modify()
                bs.modify()
                bs.set_editor_property("collision_trace_flag", unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)
                EAL.save_loaded_asset(sm, False)
            else:
                warn(f"{name}: sem colisão UCX (confira o FBX)")
    except Exception:  # noqa: BLE001
        pass
    EAL.save_loaded_asset(sm, only_if_is_dirty=False)
    return sm


# ---------------------------------------------------------------- mapa
def world():
    return unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()


def ground_z(x, y, ignore):
    hit = unreal.SystemLibrary.line_trace_single(world(), unreal.Vector(x, y, 60000), unreal.Vector(x, y, -60000),
                                                 unreal.TraceTypeQuery.TRACE_TYPE_QUERY1, True, ignore,
                                                 unreal.DrawDebugTrace.NONE, True)
    if isinstance(hit, tuple):
        hit = hit[-1]
    t = hit.to_tuple() if hit else None
    return t[5].z if t and t[0] else None


def terrain_actors():
    return [a for a in ACTORS.get_all_level_actors() if str(a.get_folder_path()).startswith("L01/Terreno")]


def floor_z(pl, b):
    """Piso acima do ponto mais alto do terreno dentro da área (grade de 1,5 m), traçando só contra o terreno."""
    others = [a for a in ACTORS.get_all_level_actors() if not str(a.get_folder_path()).startswith("L01/Terreno")]
    sx, sy = b["size_m"]
    zs = []
    nx, ny = max(2, int(sx / 1.5)), max(2, int(sy / 1.5))
    for i in range(nx + 1):
        for j in range(ny + 1):
            lx, ly = -sx / 2 + sx * i / nx, -sy / 2 + sy * j / ny
            x, y = I.to_world(pl["x"], pl["y"], pl["yaw"], lx, ly)
            z = ground_z(x, y, others)
            if z is not None:
                zs.append(z)
    if not zs:
        return None
    return max(zs) + 3.0


def tagged(a, folder, label):
    a.set_editor_property("tags", [unreal.Name(TAG)])
    a.set_folder_path(folder)
    a.set_actor_label(label)
    return a


def remove_old(P, L):
    gone = []
    old = [a for a in ACTORS.get_all_level_actors() if TAG in [str(t) for t in a.tags]]
    for a in old:
        ACTORS.destroy_actor(a)
    gone.append(f"{len(old)} atores da versão anterior")
    targets = [(f"SM_{r['name']}", r["x"], r["y"], 300.0) for r in P.get("replaced_user", [])]
    targets += [(f"SM_{c['name']}", c["x"], c["y"], 120.0) for c in P.get("culled", [])]
    poi = {p["key"]: p for p in L["pois"]}
    for (pk, i) in P["skip"]:
        e = poi[pk]["pieces"][i]
        ref = e.get("q") or e.get("mesh") or e.get("engine") or ""
        if pk in ("Posto", "SalaTrancada"):
            targets.append((f"SM_{ref.split('/')[-1]}", e["loc"][0], e["loc"][1], 150.0))
    for a in ACTORS.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        sm = a.static_mesh_component.get_editor_property("static_mesh")
        if sm is None:
            continue
        n = sm.get_name()
        loc = a.get_actor_location()
        for (tn, x, y, rad) in targets:
            if n == tn and math.hypot(loc.x - x, loc.y - y) < rad:
                gone.append(f"{a.get_actor_label()} ({n})")
                ACTORS.destroy_actor(a)
                break
    R["removed"] = gone
    log(f"removidos: {len(gone)}")


def spawn_static(sm, loc, yaw, folder, label):
    a = ACTORS.spawn_actor_from_object(sm, loc, unreal.Rotator(0, 0, yaw))
    if a is None:
        raise RuntimeError(f"falha ao colocar {label}")
    return tagged(a, folder, label)


def build_one(key, b, pl, meshes, P):
    folder = f"{FOLDER}/{key}"
    z = floor_z(pl, b)
    if z is None:
        raise RuntimeError("sem chão embaixo")
    yaw = pl["yaw"]
    info = {"x": pl["x"], "y": pl["y"], "z": round(z, 1), "yaw": yaw, "moveis": 0, "itens": 0, "luzes": 0}
    spawn_static(meshes[b["mesh"]], unreal.Vector(pl["x"], pl["y"], z), yaw, folder, f"INT_{key}")
    for k, f in enumerate(b["furniture"]):
        sm = meshes.get(f["mesh"])
        if sm is None:
            continue
        x, y = I.to_world(pl["x"], pl["y"], yaw, f["x"], f["y"])
        fa = spawn_static(sm, unreal.Vector(x, y, z), yaw - f["yaw"], folder, f"INT_{key}_{f['mesh'][7:]}_{k:02d}")
        if f["mesh"] in DECOR:
            fa.static_mesh_component.set_collision_profile_name("NoCollision")
            try:
                fa.static_mesh_component.set_editor_property("can_ever_affect_navigation", False)
            except Exception:  # noqa: BLE001
                pass
        info["moveis"] += 1
    # [A-076] portas de verdade (AJRDoor): E abre com animação; zumbis abrem sozinhos; portões largos já abertos
    info["portas"] = 0
    for k, d in enumerate(b.get("door_leaves", [])):
        x, y = I.to_world(pl["x"], pl["y"], yaw, d["x"], d["y"])
        try:
            da = ACTORS.spawn_actor_from_class(unreal.JRDoor, unreal.Vector(x, y, z), unreal.Rotator(0, 0, yaw - d["yaw"]))
        except Exception as exc:  # noqa: BLE001
            err(f"{key}: porta (compile o C++ novo: AJRDoor)", exc)
            break
        if da is None:
            warn(f"{key}: porta {k} não nasceu")
            continue
        tagged(da, folder, f"INT_{key}_Porta_{k:02d}")
        try:
            da.set_editor_property("leaf_mesh", meshes.get(d["mesh"]))
            da.set_editor_property("opening_width", float(d["width_m"]) * 100.0)
            da.set_editor_property("opening_height", float(d["height_m"]) * 100.0)
            da.set_editor_property("double", bool(d["double"]))
            da.set_editor_property("start_open", bool(d["start_open"]))
        except Exception as exc:  # noqa: BLE001
            err(f"{key}: porta {k} propriedades", exc)
        info["portas"] += 1
    lum = meshes.get(b.get("luminaire_mesh", ""))
    for k, li in enumerate(b["lights"]):
        x, y = I.to_world(pl["x"], pl["y"], yaw, li["x"], li["y"])
        if lum:
            la = spawn_static(lum, unreal.Vector(x, y, z + (b["h_m"] - 0.02) * 100.0), yaw, folder, f"INT_{key}_Luminaria_{k:02d}")
            la.static_mesh_component.set_collision_profile_name("NoCollision")
        pa = ACTORS.spawn_actor_from_class(unreal.PointLight, unreal.Vector(x, y, z + li["z"] * 100.0))
        tagged(pa, folder, f"INT_{key}_Luz_{k:02d}")
        pc = pa.point_light_component
        pc.set_mobility(unreal.ComponentMobility.MOVABLE)
        pc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        pc.set_editor_property("intensity", float(li.get("candelas", LIGHT_CD)))
        pc.set_editor_property("attenuation_radius", LIGHT_RADIUS_CM)
        pc.set_editor_property("light_color", unreal.Color(r=255, g=226, b=184, a=255))
        pc.set_editor_property("cast_shadows", k == 0)   # uma luz com sombra por construção (custo)
        info["luzes"] += 1
    for k, it in enumerate(b["pickups"]):
        x, y = I.to_world(pl["x"], pl["y"], yaw, it["x"], it["y"])
        t = it["type"].upper()
        act = ACTORS.spawn_actor_from_class(unreal.JRPickup, unreal.Vector(x, y, z + it["z"] * 100.0 + 40.0))
        tagged(act, folder, f"Pickup_INT_{key}_{k:02d}")
        try:
            act.set_editor_property("type", getattr(unreal.JRPickupType, t))
            act.set_editor_property("amount", float(AMOUNT.get(t, 1.0)))
        except Exception as exc:  # noqa: BLE001
            warn(f"{key} item {t}: {exc}")
        info["itens"] += 1
    # zona de câmera (interior)
    ext = b["camera_zone"]["extent_m"]
    cz = ACTORS.spawn_actor_from_class(unreal.JRCameraZone, unreal.Vector(pl["x"], pl["y"], z + ext[2] * 100.0), unreal.Rotator(0, 0, yaw))
    tagged(cz, folder, f"INT_{key}_ZonaCamera")
    try:
        cz.get_editor_property("box").set_box_extent(unreal.Vector(ext[0] * 100.0, ext[1] * 100.0, ext[2] * 100.0), True)
        cz.set_editor_property("arm_length", float(b["camera_zone"].get("arm_cm", 190.0)))
    except Exception as exc:  # noqa: BLE001
        err(f"{key}: zona de câmera (compile o C++ novo)", exc)
    # história (lugares novos): só a mensagem, sem trocar a tarefa principal
    st = b.get("story")
    if st:
        sa = ACTORS.spawn_actor_from_class(unreal.JRStoryTrigger, unreal.Vector(pl["x"], pl["y"], z + 150.0), unreal.Rotator(0, 0, yaw))
        tagged(sa, folder, st["label"])
        sa.set_editor_property("message", st["message"])
        sa.set_editor_property("objective_hint", "")
        sa.set_editor_property("on_foot_only", True)
        sa.get_editor_property("box").set_box_extent(unreal.Vector(ext[0] * 100.0, ext[1] * 100.0, 200.0), True)
    # baús que moram dentro
    for ch in b.get("chests", []):
        dest = P["chests"].get(ch["label"])
        found = [a for a in ACTORS.get_all_level_actors() if a.get_actor_label() == ch["label"]]
        if found and dest:
            found[0].set_actor_location_and_rotation(unreal.Vector(dest["x"], dest["y"], z), unreal.Rotator(0, 0, dest["yaw"]), False, True)
            R["chests_moved"].append(ch["label"])
        else:
            warn(f"{key}: baú {ch['label']} não achado no mapa")
    R["buildings"][key] = info


def main():
    world_now = world()
    if world_now is None or world_now.get_path_name().split(".")[0] != MAP:
        LES.load_level(MAP)
    L = json.load(open(os.path.join(I.LEVEL_DIR, "l01_layout_v3.json"), encoding="utf-8"))
    B = I.load_json(I.INTERIORS)
    PL = I.load_json(I.PLACEMENT)
    if not B or not PL:
        raise FileNotFoundError("faltam interiors_l01.json ou interiors_placement_l01.json")
    um = {}

    def have(n):
        if n not in um:
            um[n] = U.mesh(n) is not None
        return um[n]

    # rodar este script = construções aprovadas (OD-P07): liga os interiores no plano (build_l01, vegetação)
    with open(I.APPROVED, "w", encoding="utf-8") as fh:
        fh.write(f"aprovado e aplicado por build_interiors_l01.py em {datetime.now().isoformat()}\n")
    P = U.plan_v3(L, have)
    meshes = {}
    for name in sorted({b["mesh"] for b in B["buildings"].values()} | set(B["furniture"]) | {"SM_INT_Luminaria"}):
        try:
            meshes[name] = import_mesh(name)
        except Exception as exc:  # noqa: BLE001
            err(f"importar {name}", exc)
    log(f"{len([m for m in meshes.values() if m])} malhas importadas")
    remove_old(P, L)
    for key, b in B["buildings"].items():
        pl = PL["placements"].get(key)
        if not pl:
            warn(f"{key}: sem posição")
            continue
        try:
            build_one(key, b, pl, meshes, P)
        except Exception as exc:  # noqa: BLE001
            err(key, exc)
    LES.save_current_level()
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    log("mapa salvo. Depois: Build > Build Paths")


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "build_interiors_l01.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[build_interiors] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
