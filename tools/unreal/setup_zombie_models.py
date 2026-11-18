"""Troca os zumbis e a vítima do resgate pelos 4 personagens rigados pelo usuário (A-053). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS do setup_mixamo.py e do setup_zombie_skin.py:
  py "E:/game/utrazin-game/tools/unreal/setup_zombie_models.py"

Fonte: assets/work/characters_rig/CHR_<Nome>.fbx, preparados no Blender por tools/blender/prepare_character_rigs.py
       a partir de assets/raw/characters_rig/ (metros, escala 1, nomes mixamorig:, textura embutida; o tanque
       GLB virou FBX com 2,60 m) + characters.json (altura e cápsula sugerida).

Esqueleto: UM esqueleto POR personagem (não compartilhado). Motivo: as proporções vão de 1,70 a 2,60 m, o
Corredor/Sobrevivente estão em pose A e o tanque tem rig do Tripo (eixos de osso diferentes do Mixamo). Num
esqueleto só, a Unreal tocaria as translações de osso de um personagem no outro (corpo esticado) e isso só se
resolve com ajuste manual osso a osso. O IK Retargeter (como no Copzombie e nos heróis) resolve sozinho.

Passos (zumbis: TUDO OU NADA; se qualquer zumbi falhar, nenhum BP/DA muda):
1. Importa SK_<Nome> em /Game/Characters/Zombies/<Nome>/ (sobrevivente: /Game/Characters/Survivor/), com
   física (ragdoll) e materiais. Confere se o material tem textura (senão cria M_<Nome>_Tex com a textura solta
   de assets/work/characters_rig/textures) e mede as cápsulas do Physics Asset.
2. IK_<Nome> (automático) e retargeters RTG_Manny_<Nome> (ABP e montages) e RTG_Mixamo_<Nome> (andar de zumbi).
3. "Duplicar e retargetar" do ABP original dos zumbis (ABP_Unarmed, guiado pela velocidade) + montages dos DAs
   (ataque, reação, comer, variações) + Zombie Idle/Walk/Run do X Bot. Só o que FALTA, numa pasta nova
   (Anims, Anims_2, ...), salvando cada asset logo depois (a Unreal não sobrescreve no retarget).
4. Na blend space nova (BS_Idle_Walk_Run_<sufixo>) troca parado/andar/correr para frente pelas de zumbi.
5. Liga: Melee e Archer -> ZMB_Comum; Gunner -> ZMB_Corredor; Elite -> ZMB_Tanque (2,60 m, cápsula própria,
   escala 1). Sem materiais de override (textura do próprio modelo). DAs apontam para as montages do personagem.
   Se der erro no meio, volta os BPs/DAs como estavam antes desta execução.
6. Sobrevivente: SK_NPC_Sobrevivente tocando em loop o Rescued_InjuredWaveIdle (A_NPC_Sobrevivente_Idle) na
   vítima do L01 (e em BPs filhos de JRRescueTarget, se houver). O build_l01.py também usa (A-053).
Desfazer: UNDO = True no topo (BPs, DAs e vítima voltam ao estado de antes da 1a execução deste script).
Relatório: reports/setup_zombie_models.json  (estado para o UNDO: reports/setup_zombie_models_state.json)
Substitui o setup_zombie_chars.py (A-052): não precisa rodar os dois (este reaproveita o que aquele já criou).

Se a Unreal travar ao salvar (arquivo somente leitura), rode no PowerShell e tente de novo:
  attrib -R "E:\\game\\utrazin-game\\unreal\\JogoResgate\\Content\\*.*" /S /D
"""
import json
import os
import traceback
from datetime import datetime

import unreal

UNDO = False
SWAP_LOCOMOTION = True       # passo 4 (andar de zumbi na blend space nova)
WALK_SAMPLE_SPEED = 120.0    # cm/s da amostra "andar para frente" (média do vagar 90 a 140)
DO_SURVIVOR = True           # passo 6
DO_SURVIVOR_LEVEL = True     # passo 6 dentro do mapa L01 (abre, troca e salva o mapa)

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHR_DIR = os.path.join(REPO, "assets", "work", "characters_rig")
EAL = unreal.EditorAssetLibrary
MEL = unreal.MaterialEditingLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
RIGS = "/Game/Characters/Rigs"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
XBOT = "/Game/Characters/Mixamo/SK_XBot"
CZ_MESH = "/Game/Enemies/Copzombie/SK_Copzombie"
MAP_L01 = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
KINDS = ("Melee", "Archer", "Gunner", "Elite")
REPORT = os.path.join(REPO, "reports", "setup_zombie_models.json")
STATE = os.path.join(REPO, "reports", "setup_zombie_models_state.json")
OLD_STATE = os.path.join(REPO, "reports", "setup_zombie_chars_state.json")  # A-052, se alguém rodou
XBOT_HIPS_M = 1.043  # altura do quadril do X Bot (medida no Blender), para a velocidade do passo

# Personagens: pasta, sufixo das animações, quais BPs usam
CHARS = {
    "ZMB_Comum": {"dst": "/Game/Characters/Zombies/ZMB_Comum", "suffix": "_Comum", "kinds": ("Melee", "Archer")},
    "ZMB_Corredor": {"dst": "/Game/Characters/Zombies/ZMB_Corredor", "suffix": "_Corredor", "kinds": ("Gunner",)},
    "ZMB_Tanque": {"dst": "/Game/Characters/Zombies/ZMB_Tanque", "suffix": "_Tanque", "kinds": ("Elite",),
                   "own_capsule": True},
    "NPC_Sobrevivente": {"dst": "/Game/Characters/Survivor", "suffix": "_Sobrev", "kinds": ()},
}
SURVIVOR_IDLE = "/Game/Characters/Survivor/A_NPC_Sobrevivente_Idle"  # nome fixo (o build_l01.py usa)
# Animações Mixamo (esqueleto do X Bot, importadas pelo setup_mixamo.py); reserva: versão Manny
ZOMBIE_LOCO = {
    "idle": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Idle", "/Game/Enemies/Anims/A_Zombie_Idle_Manny"),
    "walk": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Walk", "/Game/Enemies/Anims/A_Zombie_Walk_Manny"),
    "run": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Run", "/Game/Enemies/Anims/A_Zombie_Run_Manny"),
}
NPC_IDLE = ("/Game/Characters/Mixamo/Anims/npc/A_Rescued_InjuredWaveIdle",
            "/Game/Enemies/Anims/A_Rescued_InjuredWaveIdle_Manny")
# Amostras da blend space do template (sem sufixo) -> papel
HUMAN_SAMPLES = {"MM_Idle": "idle", "MF_Unarmed_Walk_Fwd": "walk", "MF_Unarmed_Jog_Fwd": "run"}
DA_MONTAGE_PROPS = ("attack_montage", "hit_react_montage", "feed_montage")

R = {"time": datetime.now().isoformat(), "undo": UNDO, "skeleton_strategy": "um esqueleto por personagem + IK Retargeter",
     "steps": [], "warnings": [], "errors": [], "chars": {}, "applied": {}, "survivor": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[zombie_models] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[zombie_models] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[zombie_models] {where}: {exc}")


def save(a):
    if a is not None:
        EAL.save_loaded_asset(a, only_if_is_dirty=False)


def pkg(obj_or_path):
    """Caminho do pacote (/Game/.../Nome) de um objeto, classe ou texto."""
    if obj_or_path is None:
        return None
    p = obj_or_path if isinstance(obj_or_path, str) else obj_or_path.get_path_name()
    p = p.split("'")[1] if "'" in p else p
    return p.split(".")[0]


def cdo_of(path):
    bp = EAL.load_asset(path)
    if bp is None:
        raise RuntimeError(f"não existe: {path}")
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:  # noqa: BLE001
        return default


STATE_DATA = load_json(STATE, {"before": None, "maps": {}})


def write_state():
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as fh:
        json.dump(STATE_DATA, fh, ensure_ascii=False, indent=1)


# ------------------------------------------------------------------ esqueletos e origens

def skeleton_of(path):
    """Esqueleto (caminho do pacote) de uma malha, animação ou ABP."""
    a = EAL.load_asset(path)
    for prop in ("skeleton", "target_skeleton"):
        try:
            s = a.get_editor_property(prop)
            if s:
                return pkg(s)
        except Exception:  # noqa: BLE001
            pass
    d = EAL.find_asset_data(path)
    for tag in ("Skeleton", "TargetSkeleton"):
        try:
            v = d.get_tag_value(tag)
            if v and v != "None":
                return pkg(v)
        except Exception:  # noqa: BLE001
            pass
    return None


SRC = {}


def source_rigs():
    """Origens conhecidas: chave -> (malha, IK rig, esqueleto)."""
    out = {}
    for key, mesh, rig in (("Manny", MANNY, f"{RIGS}/IK_Manny"), ("Mixamo", XBOT, f"{RIGS}/IK_Mixamo"),
                           ("Copzombie", CZ_MESH, f"{RIGS}/IK_Copzombie")):
        if EAL.does_asset_exist(mesh) and EAL.does_asset_exist(rig):
            out[key] = (mesh, rig, pkg(EAL.load_asset(mesh).skeleton))
    R["sources_found"] = {k: v[0] for k, v in out.items()}
    return out


def source_key(path):
    sk = skeleton_of(path)
    for key, (_, _, s) in SRC.items():
        if s == sk:
            return key
    raise RuntimeError(f"{path}: esqueleto {sk} não é Manny, X Bot nem Copzombie (sem retargeter)")


def reverse_maps():
    """saída -> origem, juntando os retargets do setup_zombie_skin, do setup_zombie_chars (A-052) e deste script."""
    back = {}
    skin = load_json(os.path.join(REPO, "reports", "setup_zombie_skin.json"), {})
    info = skin.get("info", {})
    for src, out in info.get("map", {}).items():
        if src == "abp":
            if info.get("abp_src"):
                back[out] = info["abp_src"]
        else:
            back[out] = src
    for st in (load_json(OLD_STATE, {}), STATE_DATA):
        for char_map in st.get("maps", {}).values():
            for src, out in char_map.items():
                back[out] = src
    return back


def original_of(path, back):
    """Sobe a cadeia de retargets até a origem que ainda existe (Manny ou X Bot)."""
    seen = set()
    while path in back and path not in seen:
        seen.add(path)
        nxt = back[path]
        if not EAL.does_asset_exist(nxt):
            break
        path = nxt
    return path


# ------------------------------------------------------------------ 1. import + conferências

def import_mesh(name, cfg):
    dst = cfg["dst"]
    target = f"{dst}/SK_{name}"
    fbx = os.path.join(CHR_DIR, f"CHR_{name}.fbx")
    if EAL.does_asset_exist(target):
        mesh = EAL.load_asset(target)
        try:
            src = mesh.get_editor_property("asset_import_data").get_first_filename()
            R["chars"][name]["import_source"] = src
            if src and "characters_rig" not in src.replace("\\", "/"):
                warn(f"{name}: SK_{name} já existia importado de {src} (versão anterior, A-052). Para usar o "
                     f"arquivo novo apague a pasta {dst} no Content Browser e rode de novo")
        except Exception:  # noqa: BLE001
            pass
        log(f"{name}: SK_{name} já importado")
        return mesh
    if not os.path.exists(fbx):
        raise RuntimeError(f"falta {fbx} (rode tools/blender/prepare_character_rigs.py)")
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = dst
    task.destination_name = f"SK_{name}"
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = True
    o.import_animations = False
    o.import_materials = True
    o.import_textures = True
    o.create_physics_asset = True
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    try:
        o.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
    except Exception:  # noqa: BLE001
        pass
    task.options = o
    TOOLS.import_asset_tasks([task])
    paths = [pkg(p) for p in task.imported_object_paths]
    R["chars"][name]["imported"] = paths
    if not EAL.does_asset_exist(target):
        for p in paths:
            if isinstance(EAL.load_asset(p), unreal.SkeletalMesh):
                EAL.rename_asset(p, target)
                break
    mesh = EAL.load_asset(target)
    if mesh is None:
        raise RuntimeError(f"malha não importada: {paths}")
    for p in paths:
        if EAL.does_asset_exist(p):
            save(EAL.load_asset(p))
    log(f"{name}: SK_{name} importado")
    return mesh


def textures_of(mat):
    try:
        return [pkg(t) for t in MEL.get_used_textures(mat)]
    except Exception:  # noqa: BLE001
        return []


def fallback_material(name, cfg):
    """Material simples com a textura solta (quando a embutida no FBX não veio)."""
    mpath = f"{cfg['dst']}/M_{name}_Tex"
    if EAL.does_asset_exist(mpath):
        return EAL.load_asset(mpath)
    tex_file = None
    for ext in (".jpg", ".png"):
        f = os.path.join(CHR_DIR, "textures", f"T_{name}_D{ext}")
        if os.path.exists(f):
            tex_file = f
    if not tex_file:
        raise RuntimeError(f"{name}: sem textura embutida e sem {CHR_DIR}/textures/T_{name}_D.jpg")
    task = unreal.AssetImportTask()
    task.filename = tex_file
    task.destination_path = cfg["dst"]
    task.destination_name = f"T_{name}_D"
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    tex = EAL.load_asset(f"{cfg['dst']}/T_{name}_D")
    if tex is None:
        raise RuntimeError(f"{name}: textura {tex_file} não importou")
    mat = TOOLS.create_asset(f"M_{name}_Tex", cfg["dst"], unreal.Material, unreal.MaterialFactoryNew())
    ts = MEL.create_material_expression(mat, unreal.MaterialExpressionTextureSample, -400, 0)
    ts.set_editor_property("texture", tex)
    MEL.connect_material_property(ts, "RGB", unreal.MaterialProperty.MP_BASE_COLOR)
    rough = MEL.create_material_expression(mat, unreal.MaterialExpressionConstant, -400, 250)
    rough.set_editor_property("r", 0.8)
    MEL.connect_material_property(rough, "", unreal.MaterialProperty.MP_ROUGHNESS)
    MEL.recompile_material(mat)
    save(tex)
    save(mat)
    log(f"{name}: material de reserva M_{name}_Tex criado")
    return mat


def check_materials(name, cfg, mesh):
    """Nada de material branco: cada slot precisa ter textura."""
    mats = list(mesh.get_editor_property("materials"))
    info = R["chars"][name].setdefault("materials", [])
    changed = False
    for sm in mats:
        mi = sm.get_editor_property("material_interface")
        tex = textures_of(mi) if mi else []
        info.append({"slot": str(sm.get_editor_property("material_slot_name")), "material": pkg(mi), "textures": tex})
        if not tex:
            warn(f"{name}: material {pkg(mi)} sem textura: usando material de reserva")
            sm.set_editor_property("material_interface", fallback_material(name, cfg))
            changed = True
    if changed:
        mesh.set_editor_property("materials", mats)
        save(mesh)


def check_physics(name, mesh, height_cm):
    """Ragdoll: precisa de Physics Asset com corpos de tamanho razoável."""
    info = R["chars"][name]
    pa = None
    try:
        pa = mesh.get_editor_property("physics_asset")
    except Exception:  # noqa: BLE001
        pass
    info["physics_asset"] = pkg(pa)
    if pa is None:
        warn(f"{name}: sem Physics Asset (o ragdoll não funciona). Clique direito na malha > Create > Physics Asset")
        return
    bodies = []
    try:
        for b in pa.get_editor_property("skeletal_body_setups"):
            bone = str(b.get_editor_property("bone_name"))
            g = b.get_editor_property("agg_geom")
            shapes = []
            for e in g.get_editor_property("sphyl_elems"):
                shapes.append(("capsula", round(e.get_editor_property("radius")), round(e.get_editor_property("length"))))
            for e in g.get_editor_property("sphere_elems"):
                shapes.append(("esfera", round(e.get_editor_property("radius")), 0))
            for e in g.get_editor_property("box_elems"):
                shapes.append(("caixa", round(max(e.get_editor_property("x"), e.get_editor_property("y")) / 2),
                               round(e.get_editor_property("z"))))
            bodies.append({"bone": bone, "shapes": shapes})
    except Exception as exc:  # noqa: BLE001
        warn(f"{name}: não consegui ler os corpos do Physics Asset ({exc}); confira o ragdoll no jogo")
        return
    info["physics_bodies"] = bodies
    if len(bodies) < 8:
        warn(f"{name}: Physics Asset com só {len(bodies)} corpo(s): o ragdoll pode ficar duro")
    big = [b["bone"] for b in bodies for s in b["shapes"] if s[1] > height_cm * 0.22 or s[2] > height_cm * 0.6]
    if big:
        warn(f"{name}: corpos grandes demais no Physics Asset (confira no editor de física): {sorted(set(big))}")
    log(f"{name}: Physics Asset com {len(bodies)} corpos")


# ------------------------------------------------------------------ 2. rigs

def ik_rig(name, mesh):
    path = f"{RIGS}/IK_{name}"
    rig = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        f"IK_{name}", RIGS, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    c.apply_auto_generated_retarget_definition()
    try:
        R["chars"][name]["chains"] = [str(x.get_editor_property("chain_name")) for x in c.get_retarget_chains()]
    except Exception:  # noqa: BLE001
        pass
    save(rig)
    return rig


def retargeter(key, name, tgt_rig, tgt_mesh):
    """RTG_<origem>_<nome>. Já existindo, é reaproveitado (não apaga)."""
    rtg_name = f"RTG_{key}_{name}"
    path = f"{RIGS}/{rtg_name}"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    src_mesh, src_rig, _ = SRC[key]
    rtg = TOOLS.create_asset(rtg_name, RIGS, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    ST = unreal.RetargetSourceOrTarget
    src_rig_a = EAL.load_asset(src_rig)
    rc.set_ik_rig(ST.SOURCE, src_rig_a)
    rc.set_ik_rig(ST.TARGET, tgt_rig)
    for side, m in ((ST.SOURCE, EAL.load_asset(src_mesh)), (ST.TARGET, tgt_mesh)):
        try:
            rc.set_preview_mesh(side, m)
        except Exception:  # noqa: BLE001
            pass
    rc.add_default_ops()
    for side, r in ((ST.SOURCE, src_rig_a), (ST.TARGET, tgt_rig)):
        rc.assign_ik_rig_to_all_ops(side, r)
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    try:
        rc.auto_align_all_bones(ST.TARGET)  # corrige a pose A (Corredor, Sobrevivente, Tanque)
    except Exception as exc:  # noqa: BLE001
        warn(f"{rtg_name}: auto_align ({exc})")
    save(rtg)
    log(f"{rtg_name} criado")
    return rtg


# ------------------------------------------------------------------ 3. retarget

def anim_folders(base):
    out = [base] if EAL.does_directory_exist(base) else []
    for k in range(2, 100):
        f = f"{base}_{k}"
        if EAL.does_directory_exist(f):
            out.append(f)
    return out


def find_out(name, base):
    for f in anim_folders(base):
        if EAL.does_asset_exist(f"{f}/{name}"):
            return f"{f}/{name}"
    return None


def fresh_folder(base):
    for f in [base] + [f"{base}_{k}" for k in range(2, 100)]:
        if not EAL.does_directory_exist(f) or not EAL.list_assets(f, recursive=True, include_folder=False):
            return f
    raise RuntimeError(f"sem pasta livre em {base}_N")


def zombie_sources():
    """ABP original dos zumbis e montages dos DAs (sempre a origem Manny/X Bot, nunca uma cópia)."""
    back = reverse_maps()
    _, melee = cdo_of("/Game/Enemies/BP_Enemy_ZombieMelee")
    abp_cls = melee.get_editor_property("mesh").get_editor_property("anim_class")
    if abp_cls is None:
        raise RuntimeError("BP_Enemy_ZombieMelee sem ABP")
    abp_now = pkg(abp_cls)
    abp = original_of(abp_now, back)
    R["abp_now"] = abp_now
    R["abp_src"] = abp
    montages = {}  # caminho atual no DA -> origem
    for kind in KINDS:
        p = f"/Game/Data/DA_Enemy_Zombie{kind}"
        for dp in [p] + [f"{p}_{n}" for n in CHARS]:
            if not EAL.does_asset_exist(dp):
                continue
            da = EAL.load_asset(dp)
            cur = [da.get_editor_property(x) for x in DA_MONTAGE_PROPS]
            cur += list(da.get_editor_property("idle_variation_montages") or [])
            for m in cur:
                if m:
                    montages[pkg(m)] = original_of(pkg(m), back)
    return abp, montages


def loco_source(role):
    main, fallback = ZOMBIE_LOCO[role]
    if EAL.does_asset_exist(main) and "Mixamo" in SRC:
        return main
    return fallback if EAL.does_asset_exist(fallback) else None


def retarget_char(name, cfg, mesh, rig, sources):
    """Retargeta para o personagem só as origens que ainda não têm cópia. Retorna {origem: saída}."""
    base = f"{cfg['dst']}/Anims"
    sfx = cfg["suffix"]
    out, missing = {}, []
    for s in sources:
        found = find_out(s.split("/")[-1] + sfx, base)
        if found:
            out[s] = found
        else:
            missing.append(s)
    if missing:
        folder = fresh_folder(base)
        EAL.make_directory(folder)
        groups = {}
        for s in missing:
            groups.setdefault(source_key(s), []).append(s)
        for key, items in groups.items():
            rtg = retargeter(key, name, rig, mesh)
            unreal.IKRetargetBatchOperation.duplicate_and_retarget(
                [EAL.find_asset_data(p) for p in items], EAL.load_asset(SRC[key][0]), mesh, rtg,
                search="", replace="", prefix="", suffix=sfx, target_path=folder, use_source_path=False,
                include_referenced_assets=True, overwrite_existing_files=False)
            for a in EAL.list_assets(folder, recursive=True, include_folder=False):
                save(EAL.load_asset(pkg(a)))  # salva logo depois de criar
            log(f"{name}: {len(items)} asset(s) de {key} retargetados -> {folder}")
        for s in missing:
            p = f"{folder}/{s.split('/')[-1]}{sfx}"
            if EAL.does_asset_exist(p):
                out[s] = p
        R["chars"][name].setdefault("new_folders", []).append(folder)
    lost = [s for s in sources if s not in out]
    if lost:
        raise RuntimeError(f"retarget incompleto ({name}): {lost}")
    sk = pkg(mesh.skeleton)
    wrong = [p for p in out.values() if skeleton_of(p) not in (sk, None)]
    if wrong:
        raise RuntimeError(f"{name}: cópias em outro esqueleto (de uma versão antiga da malha?): {wrong}")
    return out


# ------------------------------------------------------------------ 4. blend space (andar de zumbi)

def describe(bs):
    out = []
    for s in bs.get_editor_property("sample_data"):
        a = s.get_editor_property("animation")
        v = s.get_editor_property("sample_value")
        out.append(f"{a.get_name() if a else 'NENHUMA'} @ ({v.x:.0f}, {v.y:.0f}) x{s.get_editor_property('rate_scale'):.2f}")
    return out


def speed_axis(bs):
    try:
        params = list(bs.get_editor_property("blend_parameters"))
    except Exception:  # noqa: BLE001
        return None
    for i, p in enumerate(params[:2]):
        n = str(p.get_editor_property("display_name")).lower()
        if "speed" in n or "velocidade" in n:
            return i
    return None


def swap_locomotion(name, cfg, out, scale_ratio):
    sfx = cfg["suffix"]
    bs_path = find_out(f"BS_Idle_Walk_Run{sfx}", f"{cfg['dst']}/Anims")
    if not bs_path:
        warn(f"{name}: não achei BS_Idle_Walk_Run{sfx} (o ABP usa outra blend space?): andar continua humano")
        return
    seqs = {}
    for role in ZOMBIE_LOCO:
        src = loco_source(role)
        if src and src in out:
            seqs[role] = EAL.load_asset(out[src])
    if len(seqs) < 3:
        warn(f"{name}: faltam animações de zumbi (rode setup_mixamo.py): andar continua humano")
        return
    bs = EAL.load_asset(bs_path)
    info = R["chars"][name].setdefault("blendspace", {"path": bs_path})
    info["antes"] = describe(bs)
    axis = speed_axis(bs)
    human = {k + sfx: v for k, v in HUMAN_SAMPLES.items()}
    zombie_names = {seqs[k].get_name(): k for k in seqs}
    rate = 1.0 / max(scale_ratio, 0.5)  # personagem maior dá passo maior: toca mais devagar (pé não escorrega)
    samples = list(bs.get_editor_property("sample_data"))
    changed = 0
    for s in samples:
        a = s.get_editor_property("animation")
        nm = a.get_name() if a else ""
        role = human.get(nm) or zombie_names.get(nm)
        if not role:
            continue
        if a != seqs[role]:
            s.set_editor_property("animation", seqs[role])
            changed += 1
        if role in ("walk", "run"):
            s.set_editor_property("rate_scale", round(rate, 3))
        if role == "walk" and WALK_SAMPLE_SPEED is not None and axis is not None:
            v = s.get_editor_property("sample_value")
            if axis == 0:
                v.x = WALK_SAMPLE_SPEED
            else:
                v.y = WALK_SAMPLE_SPEED
            s.set_editor_property("sample_value", v)
    bs.set_editor_property("sample_data", samples)
    save(bs)
    info["depois"] = describe(bs)
    info["rate_scale"] = round(rate, 3)
    log(f"{name}: blend space com andar de zumbi ({changed} amostra(s), passo x{rate:.2f})")


# ------------------------------------------------------------------ 5. ligar nos BPs/DAs

def bp_state(kind):
    _, cdo = cdo_of(f"/Game/Enemies/BP_Enemy_Zombie{kind}")
    m = cdo.get_editor_property("mesh")
    cap = cdo.get_editor_property("capsule_component")
    loc = m.get_editor_property("relative_location")
    msc = m.get_editor_property("relative_scale3d")
    sc = cap.get_editor_property("relative_scale3d")
    return {
        "mesh": pkg(m.get_editor_property("skeletal_mesh_asset")),
        "abp": pkg(m.get_editor_property("anim_class")),
        "override_materials": [pkg(x) for x in m.get_editor_property("override_materials")],
        "mesh_loc": [loc.x, loc.y, loc.z],
        "mesh_scale": [msc.x, msc.y, msc.z],
        "capsule_scale": [sc.x, sc.y, sc.z],
        "half_height": cap.get_editor_property("capsule_half_height"),
        "radius": cap.get_editor_property("capsule_radius"),
        "archetype": pkg(cdo.get_editor_property("archetype")),
        "muzzle_socket": str(cdo.get_editor_property("muzzle_socket")),
    }


def da_state(path):
    da = EAL.load_asset(path)
    st = {p: pkg(da.get_editor_property(p)) for p in DA_MONTAGE_PROPS}
    st["idle_variation_montages"] = [pkg(x) for x in da.get_editor_property("idle_variation_montages") or []]
    return st


def snapshot():
    snap = {"bps": {}, "das": {}}
    for kind in KINDS:
        if EAL.does_asset_exist(f"/Game/Enemies/BP_Enemy_Zombie{kind}"):
            st = bp_state(kind)
            snap["bps"][kind] = st
            if st["archetype"]:
                snap["das"][st["archetype"]] = da_state(st["archetype"])
    return snap


def restore(snap, tag):
    """Volta BPs e DAs para um retrato (UNDO ou falha no meio da troca)."""
    for kind, st in snap["bps"].items():
        bp, cdo = cdo_of(f"/Game/Enemies/BP_Enemy_Zombie{kind}")
        m = cdo.get_editor_property("mesh")
        m.set_editor_property("skeletal_mesh_asset", EAL.load_asset(st["mesh"]) if st["mesh"] else None)
        if st["abp"]:
            m.set_editor_property("anim_class", unreal.BlueprintEditorLibrary.generated_class(EAL.load_asset(st["abp"])))
        m.set_editor_property("override_materials", [EAL.load_asset(p) if p else None for p in st["override_materials"]])
        m.set_editor_property("relative_location", unreal.Vector(*st["mesh_loc"]))
        m.set_editor_property("relative_scale3d", unreal.Vector(*st.get("mesh_scale", [1.0, 1.0, 1.0])))
        cap = cdo.get_editor_property("capsule_component")
        cap.set_editor_property("relative_scale3d", unreal.Vector(*st["capsule_scale"]))
        cap.set_editor_property("capsule_radius", st["radius"])
        cap.set_editor_property("capsule_half_height", st["half_height"])
        if st["archetype"]:
            cdo.set_editor_property("archetype", EAL.load_asset(st["archetype"]))
        cdo.set_editor_property("muzzle_socket", st["muzzle_socket"])
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        log(f"{tag} BP_Enemy_Zombie{kind}")
    for path, st in snap["das"].items():
        da = EAL.load_asset(path)
        for p in DA_MONTAGE_PROPS:
            da.set_editor_property(p, EAL.load_asset(st[p]) if st[p] else None)
        da.set_editor_property("idle_variation_montages", [EAL.load_asset(x) for x in st["idle_variation_montages"]])
        save(da)
        log(f"{tag} {path}")


def hand_bone(mesh_comp, rig):
    """Osso da mão direita (o tiro do arqueiro/atirador sai da mão)."""
    try:
        b = str(unreal.IKRigController.get_controller(rig).get_retarget_chain_end_bone("RightArm"))
        if b and b != "None":
            return b
    except Exception:  # noqa: BLE001
        pass
    try:
        for i in range(mesh_comp.get_num_bones()):
            n = str(mesh_comp.get_bone_name(i))
            if n.endswith("RightHand"):
                return n
    except Exception:  # noqa: BLE001
        pass
    return None


def apply_bps(name, cfg, mesh, rig, out, abp_src, dims):
    abp = unreal.BlueprintEditorLibrary.generated_class(EAL.load_asset(out[abp_src]))
    cap_cfg = dims.get("capsule_cm", {})
    for kind in cfg["kinds"]:
        path = f"/Game/Enemies/BP_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(path):
            warn(f"{path} não existe")
            continue
        bp, cdo = cdo_of(path)
        m = cdo.get_editor_property("mesh")
        m.set_editor_property("skeletal_mesh_asset", mesh)
        m.set_editor_property("anim_class", abp)
        m.set_editor_property("override_materials", [])  # usa a textura do próprio modelo
        m.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))  # tamanho já vem certo do FBX
        cap = cdo.get_editor_property("capsule_component")
        cap.set_editor_property("relative_scale3d", unreal.Vector(1.0, 1.0, 1.0))  # o elite tinha 1,5x
        hh = float(cap_cfg.get("half_height") or cap.get_editor_property("capsule_half_height"))
        radius = float(cap.get_editor_property("capsule_radius"))
        if cfg.get("own_capsule") and cap_cfg.get("radius"):
            radius = float(cap_cfg["radius"])
        hh = max(hh, radius)
        cap.set_editor_property("capsule_radius", radius)
        cap.set_editor_property("capsule_half_height", hh)
        loc = m.get_editor_property("relative_location")
        m.set_editor_property("relative_location", unreal.Vector(loc.x, loc.y, -hh))  # pé no chão da cápsula
        bone = hand_bone(m, rig)
        if bone:
            cdo.set_editor_property("muzzle_socket", bone)
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        R["applied"][kind] = {"char": name, "half_height": hh, "radius": radius, "muzzle": bone}
        log(f"BP_Enemy_Zombie{kind}: {name} (cápsula r={radius:.0f} meia-altura={hh:.0f} cm)")


def da_for(kind, name, owners):
    """DA deste BP; se outro personagem também usa o mesmo DA, este personagem ganha uma cópia."""
    bp, cdo = cdo_of(f"/Game/Enemies/BP_Enemy_Zombie{kind}")
    da = cdo.get_editor_property("archetype")
    if da is None:
        return None
    path = pkg(da)
    if owners.setdefault(path, name) == name:
        return da
    base = path
    for n in CHARS:
        if base.endswith(f"_{n}"):
            base = base[: -len(n) - 1]
    copy = f"{base}_{name}"
    if not EAL.does_asset_exist(copy):
        EAL.duplicate_asset(path, copy)
        save(EAL.load_asset(copy))
        log(f"{path.split('/')[-1]} é usado por outro personagem: cópia {copy.split('/')[-1]}")
    new = EAL.load_asset(copy)
    owners[copy] = name
    cdo.set_editor_property("archetype", new)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    return new


def apply_das(name, cfg, out, montage_src, owners):
    for kind in cfg["kinds"]:
        da = da_for(kind, name, owners)
        if da is None:
            continue
        for prop in DA_MONTAGE_PROPS:
            m = da.get_editor_property(prop)
            if m:
                src = montage_src.get(pkg(m), pkg(m))
                if src in out:
                    da.set_editor_property(prop, EAL.load_asset(out[src]))
        var = []
        for m in da.get_editor_property("idle_variation_montages") or []:
            src = montage_src.get(pkg(m), pkg(m))
            var.append(EAL.load_asset(out[src]) if src in out else m)
        da.set_editor_property("idle_variation_montages", var)
        save(da)
        R["applied"].setdefault(kind, {})["da"] = da_state(pkg(da))
        log(f"{pkg(da).split('/')[-1]}: montages de {name}")


# ------------------------------------------------------------------ 6. sobrevivente

def set_victim(v, mesh, anim):
    v.set_editor_property("skeletal_mesh_asset", mesh)
    v.set_editor_property("override_materials", [])
    if anim:
        v.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        d = unreal.SingleAnimationPlayData()
        d.set_editor_property("anim_to_play", anim)
        d.set_editor_property("saved_looping", True)
        d.set_editor_property("saved_playing", True)
        v.set_editor_property("animation_data", d)


def victims_in_level(mesh, anim):
    n = 0
    for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
        if not isinstance(a, unreal.JRRescueTarget):
            continue
        v = a.get_editor_property("victim_mesh")
        prev = {"actor": a.get_actor_label(), "mesh": pkg(v.get_editor_property("skeletal_mesh_asset")),
                "mode": str(v.get_editor_property("animation_mode"))}
        STATE_DATA.setdefault("victims_before", {}).setdefault(a.get_actor_label(), prev)
        a.modify()
        v.modify()
        set_victim(v, mesh, anim)
        n += 1
    return n


def with_level(fn):
    """Abre o L01, roda fn() e volta para o mapa que estava aberto."""
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = pkg(world.get_path_name()) if world else None
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    if current != MAP_L01 and not les.load_level(MAP_L01):
        raise RuntimeError(f"não abri {MAP_L01}")
    try:
        fn()
        if not les.save_current_level():
            warn("save_current_level retornou False (salve o L01 com Ctrl+S)")
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    finally:
        if current and current != MAP_L01 and current.startswith("/Game/"):
            les.load_level(current)


def survivor(name, cfg, mesh, rig):
    src = NPC_IDLE[0] if (EAL.does_asset_exist(NPC_IDLE[0]) and "Mixamo" in SRC) else NPC_IDLE[1]
    if not EAL.does_asset_exist(src):
        raise RuntimeError("falta A_Rescued_InjuredWaveIdle (rode setup_mixamo.py)")
    out = retarget_char(name, cfg, mesh, rig, [src])
    STATE_DATA.setdefault("maps", {})[name] = out
    write_state()
    if not EAL.does_asset_exist(SURVIVOR_IDLE):
        EAL.duplicate_asset(out[src], SURVIVOR_IDLE)  # nome fixo para o build_l01.py
        save(EAL.load_asset(SURVIVOR_IDLE))
    anim = EAL.load_asset(SURVIVOR_IDLE)
    R["survivor"]["idle"] = SURVIVOR_IDLE
    # BPs filhos de JRRescueTarget (se alguém criou)
    for p in EAL.list_assets("/Game", recursive=True, include_folder=False):
        if "Rescue" not in p.split("/")[-1]:
            continue
        a = EAL.load_asset(pkg(p))
        if not isinstance(a, unreal.Blueprint):
            continue
        cls = unreal.BlueprintEditorLibrary.generated_class(a)
        try:
            if cls and unreal.MathLibrary.class_is_child_of(cls, unreal.JRRescueTarget):
                set_victim(unreal.get_default_object(cls).get_editor_property("victim_mesh"), mesh, anim)
                unreal.BlueprintEditorLibrary.compile_blueprint(a)
                save(a)
                log(f"{pkg(p)}: vítima padrão = sobrevivente")
        except Exception as exc:  # noqa: BLE001
            warn(f"{pkg(p)}: {exc}")
    if not DO_SURVIVOR_LEVEL:
        return
    if not EAL.does_asset_exist(MAP_L01):
        warn(f"mapa não existe: {MAP_L01}")
        return

    def edit():
        n = victims_in_level(mesh, anim)
        R["survivor"]["victims"] = n
        write_state()
        if n == 0:
            warn("nenhum JRRescueTarget no L01 (rode build_l01.py)")
        log(f"L01: {n} vítima(s) = sobrevivente em loop")
    with_level(edit)


# ------------------------------------------------------------------ desfazer

def undo():
    before = STATE_DATA.get("before")
    if not before:
        raise RuntimeError("não há estado de antes (o script nunca aplicou nada)")
    restore(before, "UNDO")
    vb = STATE_DATA.get("victims_before", {})
    if vb and EAL.does_asset_exist(MAP_L01):
        def edit():
            for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
                st = vb.get(a.get_actor_label()) if isinstance(a, unreal.JRRescueTarget) else None
                if not st:
                    continue
                v = a.get_editor_property("victim_mesh")
                a.modify()
                v.modify()
                v.set_editor_property("skeletal_mesh_asset", EAL.load_asset(st["mesh"]) if st["mesh"] else None)
                v.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT
                                      if "BLUEPRINT" in st["mode"].upper() else unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                v.set_editor_property("animation_data", unreal.SingleAnimationPlayData())
            log("UNDO vítima do L01")
        with_level(edit)
    log("UNDO feito (malhas/animações novas continuam no Content, sem uso). "
        "Atenção: o build_l01.py usa o sobrevivente enquanto /Game/Characters/Survivor/SK_NPC_Sobrevivente existir")


# ------------------------------------------------------------------ principal

def prepare_char(name, cfg, dims, sources):
    """Import, conferências, rigs, retarget e blend space. Não mexe em BP nem DA."""
    mesh = import_mesh(name, cfg)
    check_materials(name, cfg, mesh)
    check_physics(name, mesh, float(dims.get("height_m") or 1.8) * 100.0)
    try:
        b = mesh.get_bounds()
        R["chars"][name]["bounds_cm"] = [round(b.box_extent.x * 2), round(b.box_extent.y * 2), round(b.box_extent.z * 2)]
        hz = b.box_extent.z * 2
        want = float(dims.get("height_m") or 0) * 100
        if want and abs(hz - want) > want * 0.15:
            warn(f"{name}: altura na Unreal {hz:.0f} cm, esperado {want:.0f} cm (escala do FBX?)")
    except Exception:  # noqa: BLE001
        pass
    rig = ik_rig(name, mesh)
    if not cfg["kinds"]:
        return mesh, rig, None
    out = retarget_char(name, cfg, mesh, rig, sources)
    STATE_DATA.setdefault("maps", {})[name] = out
    write_state()
    R["chars"][name]["map"] = out
    if SWAP_LOCOMOTION:
        ratio = float(dims.get("hips_z_m") or XBOT_HIPS_M) / XBOT_HIPS_M
        try:
            swap_locomotion(name, cfg, out, ratio)
        except Exception as exc:  # noqa: BLE001
            err(f"{name}.swap_locomotion (segue com o andar humano)", exc)
    return mesh, rig, out


def main():
    if UNDO:
        undo()
        return
    SRC.update(source_rigs())
    for k in ("Manny", "Mixamo"):
        if k not in SRC:
            warn(f"origem {k} não encontrada (rode setup_mixamo.py): algumas animações podem faltar")
    dims_all = load_json(os.path.join(CHR_DIR, "characters.json"), {})
    abp_src, montages = zombie_sources()
    loco = [s for s in (loco_source(r) for r in ZOMBIE_LOCO) if s]
    sources = [abp_src] + sorted(set(montages.values())) + loco
    R["zombie_sources"] = sources
    if not STATE_DATA.get("before"):
        STATE_DATA["before"] = snapshot()
        write_state()
        log("estado de antes guardado (para o UNDO)")

    # fase 1: prepara TODOS os zumbis sem mexer nos BPs
    ready = {}
    for name, cfg in CHARS.items():
        if not cfg["kinds"]:
            continue
        R["chars"][name] = {}
        try:
            ready[name] = prepare_char(name, cfg, dims_all.get(name, {}), sources)
            R["chars"][name]["ready"] = True
        except Exception as exc:  # noqa: BLE001
            R["chars"][name]["ready"] = False
            err(name, exc)
    zombies = [n for n, c in CHARS.items() if c["kinds"]]
    if len(ready) != len(zombies):
        warn("algum zumbi falhou: NENHUM BP/DA foi trocado (veja 'errors'). Corrija e rode de novo")
    else:
        # fase 2: liga tudo; se falhar no meio, volta ao retrato desta execução
        run_before = snapshot()
        owners = {}
        try:
            for name, (mesh, rig, out) in ready.items():
                cfg = CHARS[name]
                apply_bps(name, cfg, mesh, rig, out, abp_src, dims_all.get(name, {}))
                apply_das(name, cfg, out, montages, owners)
            log("zumbis trocados: Melee/Archer = ZMB_Comum, Gunner = ZMB_Corredor, Elite = ZMB_Tanque")
        except Exception as exc:  # noqa: BLE001
            err("apply (voltando os BPs/DAs)", exc)
            restore(run_before, "ROLLBACK")
    if DO_SURVIVOR:
        name = "NPC_Sobrevivente"
        cfg = CHARS[name]
        R["chars"][name] = {}
        try:
            mesh, rig, _ = prepare_char(name, cfg, dims_all.get(name, {}), [])
            survivor(name, cfg, mesh, rig)
            R["chars"][name]["ready"] = True
        except Exception as exc:  # noqa: BLE001
            R["chars"][name]["ready"] = False
            err(name, exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT.replace(".json", "_undo.json") if UNDO else REPORT, "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[zombie_models] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
