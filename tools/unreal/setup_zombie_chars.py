# OBSOLETO: use setup_zombie_models.py (A-053). Este script nao deve ser rodado.
raise SystemExit("setup_zombie_chars.py esta obsoleto: rode setup_zombie_models.py")
"""Troca os zumbis (Copzombie/Manny) pelos 4 personagens do usuário (Tripo 3D + rig Mixamo). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS do setup_mixamo.py e do setup_zombie_skin.py:
  py "E:/game/utrazin-game/tools/unreal/setup_zombie_chars.py"

Fonte: assets/raw/mixamo/characters/CHR_*.fbx (preparados no Blender: metros, escala 1, textura embutida)
       + characters.json (altura e cápsula sugerida de cada um).
Para cada personagem (tudo ou nada POR PERSONAGEM: se algo falha, aquele personagem não muda nada):
1. Importa a malha em /Game/Characters/Zombies/<Nome>/SK_<Nome> (o sobrevivente vai em /Game/Characters/NPC/Sobrevivente),
   com esqueleto próprio, física (ragdoll) e materiais/texturas.
2. Cria IK_<Nome> (definição automática) e os retargeters necessários:
   RTG_Manny_<Nome> (ABP e montages do Manny), RTG_Mixamo_<Nome> (animações Mixamo do X Bot)
   e RTG_Copzombie_<Nome> (só se algum DA ainda tiver montage que só existe no Copzombie).
3. "Duplicar e retargetar" do ABP atual dos zumbis + montages dos DA_Enemy_Zombie* (ataque, reação, comer,
   variações de parado) + andar/correr/parado de zumbi do Mixamo. Só o que FALTA, numa pasta nova
   (Anims, Anims_2, ...), salvando cada asset logo depois (a Unreal não sobrescreve no retarget).
4. "Zumbi vivo": na blend space nova (BS_Idle_Walk_Run_<sufixo>) troca parado/andar/correr para frente
   pelas animações de zumbi (mesma ideia do setup_zombie_life.py, que só cuida do Copzombie).
5. Liga: BP_Enemy_ZombieMelee -> ZMB_Comum; Archer e Gunner -> ZMB_Corredor; Elite -> ZMB_Tanque
   (cápsula volta para escala 1 e ganha raio/altura do tanque). Tira os materiais de override
   (usa a textura do próprio modelo). DAs apontam para as montages do personagem; se um DA for usado
   por personagens diferentes, cria uma cópia por personagem (DA_..._<Nome>).
6. Sobrevivente: a vítima do JRRescueTarget no L01_ZombieValley (e BPs filhos de JRRescueTarget, se houver)
   vira SK_NPC_Sobrevivente tocando em loop o "Rescued_InjuredWaveIdle" do Mixamo.
Desfazer: UNDO = True no topo (volta BPs, DAs e vítima ao estado de antes da 1a execução).
Relatório: reports/setup_zombie_chars.json  (estado para o UNDO: reports/setup_zombie_chars_state.json)

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
DO_SURVIVOR_LEVEL = True     # passo 6 (mexe no mapa L01)
ONLY = None                  # ex.: ("ZMB_Tanque",) para rodar só um personagem

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CHR_DIR = os.path.join(REPO, "assets", "raw", "mixamo", "characters")
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
RIGS = "/Game/Characters/Rigs"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
XBOT = "/Game/Characters/Mixamo/SK_XBot"
CZ_MESH = "/Game/Enemies/Copzombie/SK_Copzombie"
MAP_L01 = "/Game/Levels/L01_ZombieValley/L01_ZombieValley"
KINDS = ("Melee", "Archer", "Gunner", "Elite")
REPORT = os.path.join(REPO, "reports", "setup_zombie_chars.json")
STATE = os.path.join(REPO, "reports", "setup_zombie_chars_state.json")
XBOT_HIPS_M = 1.043  # altura do quadril do X Bot (medida no Blender), para a velocidade do passo

# Personagens: nome, fbx, pasta, sufixo das animações, quais BPs usam
CHARS = {
    "ZMB_Comum": {"fbx": "CHR_ZMB_Comum.fbx", "dst": "/Game/Characters/Zombies/ZMB_Comum", "suffix": "_Comum",
                  "kinds": ("Melee",)},
    # Corredor: magro e de braços longos, combina com os zumbis "à distância" (arqueiro/atirador)
    "ZMB_Corredor": {"fbx": "CHR_ZMB_Corredor.fbx", "dst": "/Game/Characters/Zombies/ZMB_Corredor",
                     "suffix": "_Corredor", "kinds": ("Archer", "Gunner")},
    "ZMB_Tanque": {"fbx": "CHR_ZMB_Tanque.fbx", "dst": "/Game/Characters/Zombies/ZMB_Tanque", "suffix": "_Tanque",
                   "kinds": ("Elite",), "own_capsule": True},
    "NPC_Sobrevivente": {"fbx": "CHR_NPC_Sobrevivente.fbx", "dst": "/Game/Characters/NPC/Sobrevivente",
                         "suffix": "_Sobrev", "kinds": ()},
}
# Animações Mixamo (esqueleto do X Bot, importadas pelo setup_mixamo.py); reserva: versão Manny
ZOMBIE_LOCO = {
    "idle": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Idle", "/Game/Enemies/Anims/A_Zombie_Idle_Manny"),
    "walk": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Walk", "/Game/Enemies/Anims/A_Zombie_Walk_Manny"),
    "run": ("/Game/Characters/Mixamo/Anims/zombie/A_Zombie_Run", "/Game/Enemies/Anims/A_Zombie_Run_Manny"),
}
NPC_IDLE = ("/Game/Characters/Mixamo/Anims/npc/A_Rescued_InjuredWaveIdle", "/Game/Enemies/Anims/A_Rescued_InjuredWaveIdle_Manny")
# Amostras da blend space do template (sem sufixo) -> papel
HUMAN_SAMPLES = {"MM_Idle": "idle", "MF_Unarmed_Walk_Fwd": "walk", "MF_Unarmed_Jog_Fwd": "run"}
DA_MONTAGE_PROPS = ("attack_montage", "hit_react_montage", "feed_montage")

R = {"time": datetime.now().isoformat(), "undo": UNDO, "steps": [], "warnings": [], "errors": [], "chars": {},
     "applied": {}, "survivor": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[zombie_chars] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[zombie_chars] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[zombie_chars] {where}: {exc}")


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


def source_rigs():
    """Origens conhecidas: chave -> (malha, IK rig, esqueleto)."""
    out = {}
    for key, mesh, rig in (("Manny", MANNY, f"{RIGS}/IK_Manny"), ("Mixamo", XBOT, f"{RIGS}/IK_Mixamo"),
                           ("Copzombie", CZ_MESH, f"{RIGS}/IK_Copzombie")):
        if EAL.does_asset_exist(mesh) and EAL.does_asset_exist(rig):
            out[key] = (mesh, rig, pkg(EAL.load_asset(mesh).skeleton))
    R["sources_found"] = {k: v[0] for k, v in out.items()}
    return out


SRC = {}


def source_key(path):
    sk = skeleton_of(path)
    for key, (_, _, s) in SRC.items():
        if s == sk:
            return key
    raise RuntimeError(f"{path}: esqueleto {sk} não é Manny, X Bot nem Copzombie (sem retargeter)")


def reverse_maps():
    """saída -> origem: dos retargets deste script (todos os personagens) e do setup_zombie_skin (Copzombie -> Manny)."""
    back = {}
    skin = load_json(os.path.join(REPO, "reports", "setup_zombie_skin.json"), {})
    info = skin.get("info", {})
    m = info.get("map", {})
    for src, out in m.items():
        if src == "abp":
            if info.get("abp_src"):
                back[out] = info["abp_src"]
        else:
            back[out] = src
    for char_map in STATE_DATA.get("maps", {}).values():
        for src, out in char_map.items():
            back[out] = src
    return back


def original_of(path, back):
    """Sobe a cadeia de retargets até a origem que ainda existe (de preferência Manny ou X Bot)."""
    seen = set()
    while path in back and path not in seen:
        seen.add(path)
        nxt = back[path]
        if not EAL.does_asset_exist(nxt):
            break
        path = nxt
    return path


# ------------------------------------------------------------------ 1. import

def import_mesh(name, cfg):
    dst = cfg["dst"]
    target = f"{dst}/SK_{name}"
    if EAL.does_asset_exist(target):
        log(f"{name}: SK_{name} já importado")
        return EAL.load_asset(target)
    fbx = os.path.join(CHR_DIR, cfg["fbx"])
    if not os.path.exists(fbx):
        raise RuntimeError(f"falta {fbx}")
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
        save(EAL.load_asset(p))
    if not any(isinstance(EAL.load_asset(p), unreal.Texture2D) for p in paths if EAL.does_asset_exist(p)):
        warn(f"{name}: nenhuma textura importada (o modelo pode ficar sem cor)")
    log(f"{name}: SK_{name} importado")
    return mesh


def check_mesh(name, mesh):
    info = R["chars"][name]
    try:
        info["physics_asset"] = pkg(mesh.get_editor_property("physics_asset"))
    except Exception:  # noqa: BLE001
        info["physics_asset"] = None
    if not info.get("physics_asset"):
        warn(f"{name}: sem Physics Asset (o ragdoll não funciona). Clique direito na malha > Create > Physics Asset")
    try:
        b = mesh.get_bounds()
        info["bounds_cm"] = [round(b.box_extent.x * 2), round(b.box_extent.y * 2), round(b.box_extent.z * 2)]
    except Exception:  # noqa: BLE001
        pass


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
        rc.auto_align_all_bones(ST.TARGET)
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
    """ABP atual dos zumbis, montages dos DAs e animações de andar de zumbi (origens, não cópias)."""
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
        das = [p]
        das += [f"{p}_{n}" for n in CHARS if EAL.does_asset_exist(f"{p}_{n}")]
        for dp in das:
            if not EAL.does_asset_exist(dp):
                continue
            da = EAL.load_asset(dp)
            cur = [da.get_editor_property(x) for x in DA_MONTAGE_PROPS]
            cur += list(da.get_editor_property("idle_variation_montages") or [])
            for m in cur:
                if m:
                    montages[pkg(m)] = original_of(pkg(m), back)
    return abp, montages, back


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
            # salva tudo que nasceu na pasta nova logo depois de criar
            for a in EAL.list_assets(folder, recursive=True, include_folder=False):
                save(EAL.load_asset(pkg(a)))
            log(f"{name}: {len(items)} asset(s) de {key} retargetados -> {folder}")
        for s in missing:
            p = f"{folder}/{s.split('/')[-1]}{sfx}"
            if EAL.does_asset_exist(p):
                out[s] = p
        R["chars"][name]["new_folder"] = folder
    lost = [s for s in sources if s not in out]
    if lost:
        raise RuntimeError(f"retarget incompleto ({name}), nada foi trocado neste personagem: {lost}")
    # tudo precisa estar no esqueleto do personagem
    sk = pkg(mesh.skeleton)
    wrong = [p for p in out.values() if skeleton_of(p) not in (sk, None)]
    if wrong:
        raise RuntimeError(f"{name}: cópias em outro esqueleto: {wrong}")
    return out


# ------------------------------------------------------------------ 4. blend space (zumbi vivo)

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
    base = f"{cfg['dst']}/Anims"
    bs_path = find_out(f"BS_Idle_Walk_Run{sfx}", base)
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
    # personagem maior dá passo maior: toca mais devagar para o pé não escorregar
    rate = 1.0 / max(scale_ratio, 0.5)
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
    bp, cdo = cdo_of(f"/Game/Enemies/BP_Enemy_Zombie{kind}")
    m = cdo.get_editor_property("mesh")
    cap = cdo.get_editor_property("capsule_component")
    loc = m.get_editor_property("relative_location")
    sc = cap.get_editor_property("relative_scale3d")
    return {
        "mesh": pkg(m.get_editor_property("skeletal_mesh_asset")),
        "abp": pkg(m.get_editor_property("anim_class")),
        "override_materials": [pkg(x) for x in m.get_editor_property("override_materials")],
        "mesh_loc": [loc.x, loc.y, loc.z],
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


def snapshot_before():
    if STATE_DATA.get("before"):
        return
    before = {"bps": {}, "das": {}}
    for kind in KINDS:
        if EAL.does_asset_exist(f"/Game/Enemies/BP_Enemy_Zombie{kind}"):
            st = bp_state(kind)
            before["bps"][kind] = st
            if st["archetype"]:
                before["das"][st["archetype"]] = da_state(st["archetype"])
    STATE_DATA["before"] = before
    write_state()
    log("estado de antes guardado (para o UNDO)")


def hand_bone(mesh_comp, rig):
    """Osso da mão direita (para o tiro do arqueiro/atirador sair da mão)."""
    try:
        c = unreal.IKRigController.get_controller(rig)
        b = str(c.get_retarget_chain_end_bone("RightArm"))
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
    owner = owners.setdefault(path, name)
    if owner == name:
        return da
    base = path
    for n in CHARS:  # se já é cópia de outro personagem, volta ao nome base
        if base.endswith(f"_{n}"):
            base = base[: -len(n) - 1]
    copy = f"{base}_{name}"
    if not EAL.does_asset_exist(copy):
        EAL.duplicate_asset(path, copy)
        save(EAL.load_asset(copy))
        log(f"{pkg(da).split('/')[-1]} é usado por outro personagem: cópia {copy.split('/')[-1]}")
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


# ------------------------------------------------------------------ 6. sobrevivente na cela

def rescue_victims_in_level(mesh, anim):
    ss = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    n = 0
    for a in ss.get_all_level_actors():
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


def survivor_level(mesh, anim):
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
    les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
    world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
    current = pkg(world.get_path_name()) if world else None
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    if current != MAP_L01 and not les.load_level(MAP_L01):
        raise RuntimeError(f"não abriu {MAP_L01}")
    try:
        n = rescue_victims_in_level(mesh, anim)
        R["survivor"]["victims"] = n
        if n == 0:
            warn("nenhum JRRescueTarget no L01 (rode build_l01.py)")
        elif not les.save_current_level():
            warn("save_current_level retornou False (salve o L01 com Ctrl+S)")
        log(f"L01: {n} vítima(s) = sobrevivente em loop")
        write_state()
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
    anim = EAL.load_asset(out[src])
    R["survivor"]["idle"] = out[src]
    survivor_level(mesh, anim)


# ------------------------------------------------------------------ desfazer

def undo():
    before = STATE_DATA.get("before")
    if not before:
        raise RuntimeError("não há estado de antes (o script nunca aplicou nada)")
    for kind, st in before["bps"].items():
        bp, cdo = cdo_of(f"/Game/Enemies/BP_Enemy_Zombie{kind}")
        m = cdo.get_editor_property("mesh")
        m.set_editor_property("skeletal_mesh_asset", EAL.load_asset(st["mesh"]) if st["mesh"] else None)
        if st["abp"]:
            m.set_editor_property("anim_class", unreal.BlueprintEditorLibrary.generated_class(EAL.load_asset(st["abp"])))
        m.set_editor_property("override_materials", [EAL.load_asset(p) if p else None for p in st["override_materials"]])
        m.set_editor_property("relative_location", unreal.Vector(*st["mesh_loc"]))
        cap = cdo.get_editor_property("capsule_component")
        cap.set_editor_property("relative_scale3d", unreal.Vector(*st["capsule_scale"]))
        cap.set_editor_property("capsule_radius", st["radius"])
        cap.set_editor_property("capsule_half_height", st["half_height"])
        if st["archetype"]:
            cdo.set_editor_property("archetype", EAL.load_asset(st["archetype"]))
        cdo.set_editor_property("muzzle_socket", st["muzzle_socket"])
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        log(f"UNDO BP_Enemy_Zombie{kind}")
    for path, st in before["das"].items():
        da = EAL.load_asset(path)
        for p in DA_MONTAGE_PROPS:
            da.set_editor_property(p, EAL.load_asset(st[p]) if st[p] else None)
        da.set_editor_property("idle_variation_montages", [EAL.load_asset(x) for x in st["idle_variation_montages"]])
        save(da)
        log(f"UNDO {path}")
    vb = STATE_DATA.get("victims_before", {})
    if vb and EAL.does_asset_exist(MAP_L01):
        les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        current = pkg(world.get_path_name()) if world else None
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        if current == MAP_L01 or les.load_level(MAP_L01):
            for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
                st = vb.get(a.get_actor_label()) if isinstance(a, unreal.JRRescueTarget) else None
                if st:
                    v = a.get_editor_property("victim_mesh")
                    a.modify()
                    v.modify()
                    v.set_editor_property("skeletal_mesh_asset", EAL.load_asset(st["mesh"]) if st["mesh"] else None)
                    v.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT
                                          if "BLUEPRINT" in st["mode"].upper() else unreal.AnimationMode.ANIMATION_SINGLE_NODE)
                    v.set_editor_property("animation_data", unreal.SingleAnimationPlayData())
            les.save_current_level()
            log("UNDO vítima do L01")
            if current and current != MAP_L01 and current.startswith("/Game/"):
                les.load_level(current)
    log("UNDO feito (as malhas/animações novas continuam no Content, sem uso)")


# ------------------------------------------------------------------ principal

def main():
    if UNDO:
        undo()
        return
    SRC.update(source_rigs())
    for k in ("Manny", "Mixamo"):
        if k not in SRC:
            warn(f"origem {k} não encontrada (rode setup_mixamo.py): algumas animações podem faltar")
    dims_all = load_json(os.path.join(CHR_DIR, "characters.json"), {})
    abp_src, montages, _ = zombie_sources()
    montage_src = dict(montages)  # caminho atual -> origem
    zsources = [abp_src] + sorted(set(montages.values()))
    loco = [s for s in (loco_source(r) for r in ZOMBIE_LOCO) if s]
    R["zombie_sources"] = zsources + loco
    snapshot_before()
    owners = {}
    for name, cfg in CHARS.items():
        if ONLY and name not in ONLY:
            continue
        R["chars"][name] = {}
        try:
            mesh = import_mesh(name, cfg)
            check_mesh(name, mesh)
            rig = ik_rig(name, mesh)
            dims = dims_all.get(f"CHR_{name}", {})
            if not cfg["kinds"]:
                survivor(name, cfg, mesh, rig)
                continue
            out = retarget_char(name, cfg, mesh, rig, zsources + loco)
            STATE_DATA.setdefault("maps", {})[name] = out
            write_state()
            R["chars"][name]["map"] = out
            if SWAP_LOCOMOTION:
                ratio = float(dims.get("hips_z_m") or XBOT_HIPS_M) / XBOT_HIPS_M
                try:
                    swap_locomotion(name, cfg, out, ratio)
                except Exception as exc:  # noqa: BLE001
                    err(f"{name}.swap_locomotion (personagem aplicado mesmo assim)", exc)
            # só agora (tudo pronto) mexe nos BPs e DAs
            apply_bps(name, cfg, mesh, rig, out, abp_src, dims)
            apply_das(name, cfg, out, montage_src, owners)
            R["chars"][name]["ok"] = True
        except Exception as exc:  # noqa: BLE001
            R["chars"][name]["ok"] = False
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
    unreal.log(f"[zombie_chars] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
