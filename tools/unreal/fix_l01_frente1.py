"""Frente 1 da limpeza da L01 (A-063): brilho, céu, colisão e física, SEM refazer o mapa. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ (JRPickup novo):
  py "E:/game/utrazin-game/tools/unreal/fix_l01_frente1.py"

O que faz (cada parte segue sozinha se outra falhar; tudo vai para reports/fix_l01_frente1.json):
 1. Brilho: refaz M_L01_Glow com o parâmetro GlowStrength = 1,5 (era cor x 6, estourava; item 8 / print_08).
 2. Luzes do layout (pasta L01/Luz/Pontos): passa para candelas na escala certa (fogueira 9000 -> 54 cd).
 3. Céu: reaplica setup_alien_sky.apply_to_current_level() (planeta e luas sem "Is Sky": some o aviso
    "SKYDOME MESH"; item 15).
 4. Colisão das malhas (item 1): modelos do usuário marcados "box" e peças Quaternius/L01 "simple" que estão
    SEM NENHUMA forma de colisão ganham uma caixa do tamanho da malha. Troncos ("trunk") sem colisão só
    entram no relatório (precisam da caixa UCX do Blender).
 5. Física (item 1): barris e caixas já colocados no mapa ficam empurráveis (dormindo até levar um esbarrão).
 6. Tarefas (item 13, A-064): cada gatilho de história aponta para o seu alvo (l01_tasks.py); o painel
    OBJETIVO mostra a tarefa atual e o marcador vai até ela.
 7. Salva as malhas mudadas e o mapa.
Os itens (JRPickup) param de girar e se apoiam no chão sozinhos no Play: isso é o C++ (compile antes).
Depois: Build > Build Paths (colisão nova muda a navegação dos zumbis).
"""
import json
import os
import sys
import traceback
from datetime import datetime

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
if HERE not in sys.path:
    sys.path.append(HERE)

MAP = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
GLOW_MAT = "/Game/Environment/L01/Materials/M_L01_Glow"
GLOW_STRENGTH = 1.5
LAYOUT = os.path.join(REPO, "assets", "work", "levels", "L01", "l01_layout_v3.json")
PROCESSED = os.path.join(REPO, "assets", "work", "tripo", "tripo_processed.json")
LIGHT_CD_PER_LAYOUT = 0.006          # o mesmo do build_l01.py
LIGHT_FOLDER = "L01/Luz"
PROPS_DIR = "/Game/Environment/L01/Props"
# peças L01 (FBX próprios) que podem ficar sem colisão de propósito (o build_l01 já desliga no ator)
PROPS_NO_COLLISION = {"SM_Bush", "SM_Rock_Small", "SM_Sign", "SM_GrassAlienTuft", "SM_AlienFlowerGlow", "SM_SpikeStrip"}
PHYSICS_MESHES = {"SM_PRP_Barril", "SM_Barrel", "SM_Pickup_Crate", "SM_Crate"}

EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
ACTORS = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
LES = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
SMES = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "glow": {}, "lights": [],
     "sky": None, "collision_added": [], "trunk_without_collision": [], "physics": [], "saved_meshes": 0,
     "tasks": None}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[fix_l01_frente1] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[fix_l01_frente1] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-700:]})
    unreal.log_error(f"[fix_l01_frente1] {where}: {exc}")


def open_map():
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    cur = world.get_path_name().split(".")[0] if world else ""
    if cur != MAP:
        LES.load_level(MAP)
        log("mapa L01_ZombieValley aberto")


# ---------------------------------------------------------------- 1. brilho
def fix_glow():
    if not EAL.does_asset_exist(GLOW_MAT):
        warn(f"{GLOW_MAT} não existe (setup_wave1.py não rodou?)")
        return
    m = EAL.load_asset(GLOW_MAT)
    MEL.delete_all_material_expressions(m)
    vc = MEL.create_material_expression(m, unreal.MaterialExpressionVertexColor, -600, 0)
    MEL.connect_material_property(vc, "", unreal.MaterialProperty.MP_BASE_COLOR)
    gs = MEL.create_material_expression(m, unreal.MaterialExpressionScalarParameter, -600, 200)
    gs.set_editor_property("parameter_name", "GlowStrength")
    gs.set_editor_property("default_value", GLOW_STRENGTH)
    mul = MEL.create_material_expression(m, unreal.MaterialExpressionMultiply, -300, 120)
    MEL.connect_material_expressions(vc, "", mul, "A")
    MEL.connect_material_expressions(gs, "", mul, "B")
    MEL.connect_material_property(mul, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)
    rough = MEL.create_material_expression(m, unreal.MaterialExpressionConstant, -300, 320)
    rough.set_editor_property("r", 0.4)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(m)
    EAL.save_loaded_asset(m, only_if_is_dirty=False)
    R["glow"] = {"material": GLOW_MAT, "GlowStrength": GLOW_STRENGTH, "antes": "cor do vértice x 6"}
    log(f"M_L01_Glow refeito (GlowStrength {GLOW_STRENGTH})")


# ---------------------------------------------------------------- 2. luzes
def fix_lights():
    L = json.load(open(LAYOUT, encoding="utf-8"))
    want = {li["label"]: li for li in L.get("lights", [])}
    seen = set()
    for a in ACTORS.get_all_level_actors():
        if not isinstance(a, unreal.PointLight):
            continue
        label = a.get_actor_label()
        folder = str(a.get_folder_path())
        li = want.get(label)
        if li is None:
            if folder.startswith(LIGHT_FOLDER):
                warn(f"luz {label} na pasta {folder} sem par no layout: não mexi")
            continue
        pc = a.point_light_component
        before = {"intensity": pc.get_editor_property("intensity"),
                  "units": str(pc.get_editor_property("intensity_units"))}
        pc.set_editor_property("intensity_units", unreal.LightUnits.CANDELAS)
        pc.set_editor_property("intensity", float(li["intensity"]) * LIGHT_CD_PER_LAYOUT)
        R["lights"].append({"label": label, "antes": before, "depois_cd": round(float(li["intensity"]) * LIGHT_CD_PER_LAYOUT, 1)})
        seen.add(label)
    missing = sorted(set(want) - seen)
    if missing:
        warn(f"luzes do layout não achadas no mapa: {missing}")
    log(f"{len(seen)} luzes em candelas (escala {LIGHT_CD_PER_LAYOUT})")


# ---------------------------------------------------------------- 3. céu
def fix_sky():
    import setup_alien_sky  # noqa: E402
    setup_alien_sky.apply_to_current_level(save=False)
    R["sky"] = {"body_is_sky": setup_alien_sky.BODY_IS_SKY, "fog_cutoff_cm": setup_alien_sky.FOG_CUTOFF_CM}
    log("céu reaplicado (planeta e luas sem Is Sky)")


# ---------------------------------------------------------------- 4. colisão
def simple_count(sm):
    try:
        return SMES.get_simple_collision_count(sm)
    except Exception:  # noqa: BLE001
        return -1


def trace_flag(sm):
    try:
        return sm.get_editor_property("body_setup").get_editor_property("collision_trace_flag")
    except Exception:  # noqa: BLE001
        return None


def add_box(sm, why):
    SMES.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
    EAL.save_loaded_asset(sm, only_if_is_dirty=False)
    R["collision_added"].append({"mesh": sm.get_path_name().split(".")[0], "motivo": why})
    R["saved_meshes"] += 1


def needs_box(sm):
    return (simple_count(sm) == 0
            and trace_flag(sm) != unreal.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE)


def fix_collision():
    # 4a. modelos do usuário (tripo_processed.json: collision box / trunk / complex / none)
    import l01_user_dressing as U  # noqa: E402
    proc = json.load(open(PROCESSED, encoding="utf-8"))
    for name, info in sorted(proc.items()):
        kind = (info or {}).get("collision")
        if kind not in ("box", "trunk"):
            continue
        try:
            path = U.asset_path(name)
        except KeyError:
            continue
        if not EAL.does_asset_exist(path):
            continue
        sm = EAL.load_asset(path)
        if not isinstance(sm, unreal.StaticMesh) or not needs_box(sm):
            continue
        if kind == "box":
            add_box(sm, "usuário 'box' sem caixa UCX")
        else:
            R["trunk_without_collision"].append(path)
    # 4b. peças Quaternius do layout marcadas "simple"
    import quaternius_lib as Q  # noqa: E402
    L = json.load(open(LAYOUT, encoding="utf-8"))
    refs = sorted({e["q"] for p in L["pois"] for e in p["pieces"] if e.get("q") and e.get("col") == "simple"})
    for g in L.get("gates", []):
        for k in ("mesh_q", "pieces_q"):
            if g.get(k):
                refs.append(g[k])
    for ref in sorted(set(refs)):
        path = Q.asset_path(ref)
        if not EAL.does_asset_exist(path):
            continue
        sm = EAL.load_asset(path)
        if isinstance(sm, unreal.StaticMesh) and needs_box(sm):
            add_box(sm, f"Quaternius {ref} 'simple' sem caixa")
    # 4c. peças L01 próprias (L01_Props*.fbx)
    for p in EAL.list_assets(PROPS_DIR, recursive=False, include_folder=False):
        sm = EAL.load_asset(p.split(".")[0])
        if not isinstance(sm, unreal.StaticMesh) or sm.get_name() in PROPS_NO_COLLISION:
            continue
        if needs_box(sm):
            add_box(sm, "peça L01 sem colisão")
    log(f"colisão: {len(R['collision_added'])} malhas ganharam caixa; "
        f"{len(R['trunk_without_collision'])} troncos sem colisão (ver relatório)")


# ---------------------------------------------------------------- 5. física
def make_physics(c, name):
    c.set_mobility(unreal.ComponentMobility.MOVABLE)
    c.set_collision_profile_name("PhysicsActor")
    bi = c.get_editor_property("body_instance")
    bi.set_editor_property("start_awake", False)
    bi.set_editor_property("linear_damping", 0.4)
    bi.set_editor_property("angular_damping", 1.0)
    c.set_editor_property("body_instance", bi)
    c.set_simulate_physics(True)


def fix_physics():
    n = 0
    for a in ACTORS.get_all_level_actors():
        if not isinstance(a, unreal.StaticMeshActor):
            continue
        c = a.static_mesh_component
        sm = c.get_editor_property("static_mesh")
        if sm is None or sm.get_name() not in PHYSICS_MESHES:
            continue
        if str(c.get_collision_profile_name()) == "NoCollision":
            continue
        if simple_count(sm) == 0:
            warn(f"{a.get_actor_label()}: {sm.get_name()} sem caixa de colisão, física não ligada")
            continue
        try:
            if not c.is_simulating_physics():
                make_physics(c, sm.get_name())
                n += 1
                R["physics"].append(a.get_actor_label())
        except Exception as exc:  # noqa: BLE001
            warn(f"física {a.get_actor_label()}: {exc}")
    log(f"física ligada em {n} barris/caixas")


def fix_tasks():
    import l01_tasks  # noqa: E402
    R["tasks"] = l01_tasks.apply(json.load(open(LAYOUT, encoding="utf-8")), log, warn)


def main():
    open_map()
    for name, fn in (("brilho", fix_glow), ("luzes", fix_lights), ("céu", fix_sky), ("colisão", fix_collision),
                     ("física", fix_physics), ("tarefas", fix_tasks)):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            err(name, exc)
    try:
        LES.save_current_level()
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        log("mapa e assets salvos. Depois: Build > Build Paths")
    except Exception as exc:  # noqa: BLE001
        err("salvar", exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "fix_l01_frente1.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[fix_l01_frente1] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
