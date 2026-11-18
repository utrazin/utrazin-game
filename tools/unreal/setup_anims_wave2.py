"""Animações da onda 2: escopeta, curar, interagir e vida dos zumbis (comer/gritar). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ novo (o HealAnim vem do agente "Roda de itens"):
  py "E:/game/utrazin-game/tools/unreal/setup_anims_wave2.py"

O que faz (cada parte é independente; ver reports/setup_anims_wave2.json):
 1. Escopeta: retarget das animações de RIFLE do template da Epic (esqueleto do Manny, já no Content em
    /Game/Characters/Mannequins/Anims/Rifle) para Enzo e Victoria em /Game/Characters/HeroNN/Anims/Wave2
    (sufixo _HNN). Hoje a escopeta usa as animações da pistola; as de rifle ficam prontas para quando o C++
    tiver ShotgunAimAnim/ShotgunFireAnim/ShotgunReloadAnim/ShotgunEquipAnim (o script tenta preencher e,
    se a propriedade não existir, só avisa no relatório).
 2. Mixamo (opcional): para cada FBX da lista MIXAMO que EXISTIR em assets/raw/mixamo/<grupo>/, importa no
    X Bot (/Game/Characters/Mixamo/Anims/<grupo>) e:
      - hero   -> retarget para os dois heróis (Wave2) e preenche a propriedade se existir
                  (ArmedIdleAnim, HealAnim, InteractAnim, PlantAnim)
      - zombie -> retarget para o esqueleto atual de cada DA_Enemy_Zombie* (Manny, Copzombie ou os zumbis
                  novos do setup_zombie_models.py), cria a montage e liga como FeedMontage (comer) ou
                  IdleVariationMontages (grito)
    Arquivo que não existe é só listado como "falta baixar" no relatório.
 3. A Unreal NÃO sobrescreve no retarget: só faz o que falta; se a pasta já tiver o asset, reaproveita.
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
RAW = os.path.join(REPO, "assets", "raw", "mixamo")
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
HEROES = ("01", "02")
RIGS = "/Game/Characters/Rigs"
XBOT = "/Game/Characters/Mixamo/SK_XBot"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
CZ_MESH = "/Game/Enemies/Copzombie/SK_Copzombie"
ZOMBIE_MESH_DIRS = ("/Game/Characters/Zombies", "/Game/Enemies")
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {},
     "missing_downloads": [], "cpp_needed": []}

# 1. Rifle do template (Manny) -> escopeta. (asset de origem, propriedade futura no C++)
RIFLE = (
    ("/Game/Characters/Mannequins/Anims/Rifle/MF_Rifle_Idle_ADS", "shotgun_aim_anim"),
    ("/Game/Characters/Mannequins/Anims/Rifle/MM_Rifle_Fire", "shotgun_fire_anim"),
    ("/Game/Characters/Mannequins/Anims/Rifle/MM_Rifle_Reload", "shotgun_reload_anim"),
    ("/Game/Characters/Mannequins/Anims/Rifle/MM_Rifle_Equip", "shotgun_equip_anim"),
)

# 2. Mixamo opcional: arquivo (sem .fbx), grupo, uso, propriedade/papel, o que procurar no mixamo.com
# (baixados em 2026-11-16 no personagem do usuário SM_NPC_Sobrevivente_mixamo: quadril 0,97 m, X Bot 1,04 m)
MIXAMO = (
    {"name": "Pistol_Idle_Low", "group": "hero", "prop": "armed_idle_anim",
     "search": "Pistol Idle (Idle Holding Pistol, Kicking Out And Shaking Legs): pistola baixa numa mão"},
    {"name": "Heal_Bandage", "group": "hero", "prop": "heal_anim",
     "search": "Drinking (Male Drinking): não há bandagem no Mixamo; beber o kit/estimulante"},
    {"name": "Interact_Button", "group": "hero", "prop": "interact_anim",
     "search": "Button Pushing (Pushing A Button With The Right Hand)"},
    {"name": "Plant_Kneel", "group": "hero", "prop": "plant_anim",
     "search": "Plant A Plant (Kneeling Planting A Plant): armar o explosivo"},
    {"name": "Zombie_Scream", "group": "zombie", "role": "idle_variation", "search": "Zombie Scream (Zombie Screaming)"},
    {"name": "Zombie_ScratchIdle", "group": "zombie", "role": "idle_variation", "search": "Zombie Scratch Idle"},
    {"name": "Zombie_Feed", "group": "zombie", "role": "feed", "search": "Zombie Biting (Zombie Biting Victim On The Ground)"},
    {"name": "Survivor_Terrified", "group": "npc", "role": "survivor",
     "search": "Terrified (Being Terrified While Standing)"},
)


def log(m):
    R["steps"].append(m)
    unreal.log(f"[anims_wave2] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[anims_wave2] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1200:]})
    unreal.log_error(f"[anims_wave2] {where}: {exc}")


def save(a):
    if a is not None:
        EAL.save_loaded_asset(a, only_if_is_dirty=False)


def pkg(obj_or_path):
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


def compile_save(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)


def setp(obj, k, v, where):
    """Preenche uma propriedade que pode ainda não existir (C++ não compilado)."""
    try:
        obj.set_editor_property(k, v)
        log(f"{where}.{k} = {v.get_name() if hasattr(v, 'get_name') else v}")
        return True
    except Exception as exc:  # noqa: BLE001
        R["cpp_needed"].append(f"{where}.{k} (não existe no C++: {str(exc)[:80]})")
        warn(f"{where}.{k} não existe (falta C++ ou compilar)")
        return False


def skeleton_of(path):
    a = EAL.load_asset(path)
    for prop in ("skeleton", "target_skeleton"):
        try:
            s = a.get_editor_property(prop)
            if s:
                return pkg(s)
        except Exception:  # noqa: BLE001
            pass
    try:
        v = EAL.find_asset_data(path).get_tag_value("Skeleton")
        if v and v != "None":
            return pkg(v)
    except Exception:  # noqa: BLE001
        pass
    return None


# ------------------------------------------------------------------ pastas (a Unreal não sobrescreve)

def folders(base):
    out = [base] if EAL.does_directory_exist(base) else []
    for k in range(2, 100):
        if EAL.does_directory_exist(f"{base}_{k}"):
            out.append(f"{base}_{k}")
    return out


def find_out(name, base):
    for f in folders(base):
        if EAL.does_asset_exist(f"{f}/{name}"):
            return f"{f}/{name}"
    return None


def fresh_folder(base):
    for f in [base] + [f"{base}_{k}" for k in range(2, 100)]:
        if not EAL.does_directory_exist(f) or not EAL.list_assets(f, recursive=True, include_folder=False):
            return f
    raise RuntimeError(f"sem pasta livre em {base}_N")


def retarget(sources, src_mesh, tgt_mesh, rtg, suffix, base):
    """Retarget só do que ainda não tem cópia. Retorna {origem: saída}."""
    out, missing = {}, []
    for s in sources:
        found = find_out(s.split("/")[-1] + suffix, base)
        if found:
            out[s] = found
        else:
            missing.append(s)
    if missing:
        folder = fresh_folder(base)
        EAL.make_directory(folder)
        unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [EAL.find_asset_data(p) for p in missing], src_mesh, tgt_mesh, rtg, search="", replace="", prefix="",
            suffix=suffix, target_path=folder, use_source_path=False, include_referenced_assets=False,
            overwrite_existing_files=False)
        for a in EAL.list_assets(folder, recursive=True, include_folder=False):
            save(EAL.load_asset(pkg(a)))
        for s in missing:
            p = f"{folder}/{s.split('/')[-1]}{suffix}"
            if EAL.does_asset_exist(p):
                out[s] = p
            else:
                warn(f"retarget não gerou {p}")
        log(f"{len(missing)} retarget(s) {suffix} -> {folder}")
    return out


def montage(seq_path, name):
    folder = seq_path.rsplit("/", 1)[0]
    path = f"{folder}/{name}"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    seq = EAL.load_asset(seq_path)
    f = unreal.AnimMontageFactory()
    f.set_editor_property("source_animation", seq)
    try:
        f.set_editor_property("target_skeleton", seq.get_editor_property("skeleton"))
    except Exception:  # noqa: BLE001
        pass
    m = TOOLS.create_asset(name, folder, unreal.AnimMontage, f)
    save(m)
    return m


# ------------------------------------------------------------------ import Mixamo (esqueleto do X Bot)

def import_anim(fbx, group, skeleton):
    name = "A_" + os.path.splitext(os.path.basename(fbx))[0]
    folder = f"/Game/Characters/Mixamo/Anims/{group}"
    target = f"{folder}/{name}"
    if EAL.does_asset_exist(target):
        return target
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = False
    o.import_as_skeletal = True
    o.import_animations = True
    o.import_materials = False
    o.import_textures = False
    o.skeleton = skeleton
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_ANIMATION
    task.options = o
    TOOLS.import_asset_tasks([task])
    if not EAL.does_asset_exist(target):
        for p in task.imported_object_paths:
            a = EAL.load_asset(pkg(p))
            if isinstance(a, unreal.AnimSequence):
                EAL.rename_asset(pkg(p), target)
                break
    if not EAL.does_asset_exist(target):
        raise RuntimeError(f"animação não importada: {fbx}")
    seq = EAL.load_asset(target)
    try:
        seq.set_editor_property("enable_root_motion", False)
    except Exception:  # noqa: BLE001
        pass
    save(seq)
    return target


# ------------------------------------------------------------------ 1. escopeta (rifle do template)

def shotgun_anims():
    manny = EAL.load_asset(MANNY)
    srcs = [p for p, _ in RIFLE if EAL.does_asset_exist(p)]
    if len(srcs) < len(RIFLE):
        warn(f"rifle do template incompleto: achei {srcs}")
    for nn in HEROES:
        rtg = EAL.load_asset(f"{RIGS}/RTG_Manny_Hero{nn}")
        mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
        if rtg is None or mesh is None:
            warn(f"Hero{nn}: falta RTG_Manny_Hero{nn} ou SK_Hero{nn}")
            continue
        out = retarget(srcs, manny, mesh, rtg, f"_H{nn}", f"/Game/Characters/Hero{nn}/Anims/Wave2")
        R["info"][f"shotgun_H{nn}"] = out
        bp, cdo = cdo_of(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
        changed = False
        for src, prop in RIFLE:
            if src in out:
                changed |= setp(cdo, prop, EAL.load_asset(out[src]), f"Hero{nn}")
        if changed:
            compile_save(bp)


# ------------------------------------------------------------------ 2. Mixamo opcional

def hero_mixamo(items, xbot):
    srcs = {}
    for it in items:
        try:
            srcs[it["name"]] = import_anim(os.path.join(RAW, it["group"], it["name"] + ".fbx"), it["group"], xbot.skeleton)
        except Exception as exc:  # noqa: BLE001
            err(f"import {it['name']}", exc)
    if not srcs:
        return
    for nn in HEROES:
        rtg = EAL.load_asset(f"{RIGS}/RTG_Mixamo_Hero{nn}")
        mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
        out = retarget(list(srcs.values()), xbot, mesh, rtg, f"_H{nn}", f"/Game/Characters/Hero{nn}/Anims/Wave2")
        R["info"][f"mixamo_H{nn}"] = out
        bp, cdo = cdo_of(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
        changed = False
        for it in items:
            src = srcs.get(it["name"])
            if src and src in out:
                changed |= setp(cdo, it["prop"], EAL.load_asset(out[src]), f"Hero{nn}")
        if changed:
            compile_save(bp)


def zombie_target(skel):
    """Esqueleto atual de um DA -> (malha, retargeter a partir do X Bot ou do Manny, sufixo, origem)."""
    if skel == skeleton_of(MANNY):
        return {"kind": "Manny"}
    if EAL.does_asset_exist(CZ_MESH) and skel == skeleton_of(CZ_MESH):
        return {"kind": "Copzombie", "mesh": CZ_MESH, "rtg": f"{RIGS}/RTG_Manny_Copzombie", "suffix": "_CZ",
                "base": "/Game/Enemies/Copzombie/Anims/Wave2"}
    for d in ZOMBIE_MESH_DIRS:
        for a in EAL.list_assets(d, recursive=True, include_folder=False):
            p = pkg(a)
            name = p.split("/")[-1]
            if not name.startswith("SK_") or name.endswith("_Skeleton") or name.endswith("_PhysicsAsset"):
                continue
            ad = EAL.find_asset_data(p)
            if str(ad.asset_class_path.asset_name) != "SkeletalMesh":
                continue
            if skeleton_of(p) == skel:
                short = name[3:]
                return {"kind": "Mixamo", "mesh": p, "rtg": f"{RIGS}/RTG_Mixamo_{short}", "suffix": f"_{short}",
                        "base": f"{p.rsplit('/', 1)[0]}/Anims/Wave2"}
    return None


def zombie_mixamo(items, xbot):
    srcs = {}
    for it in items:
        try:
            srcs[it["name"]] = import_anim(os.path.join(RAW, it["group"], it["name"] + ".fbx"), it["group"], xbot.skeleton)
        except Exception as exc:  # noqa: BLE001
            err(f"import {it['name']}", exc)
    if not srcs:
        return
    manny = EAL.load_asset(MANNY)
    # versão Manny (base para o Copzombie e reserva)
    manny_out = retarget(list(srcs.values()), xbot, manny, EAL.load_asset(f"{RIGS}/RTG_Mixamo_Manny"), "_Manny",
                         "/Game/Enemies/Anims/Wave2")
    R["info"]["zombie_manny"] = manny_out
    das = [pkg(a) for a in EAL.list_assets("/Game/Data", recursive=True, include_folder=False)
           if pkg(a).split("/")[-1].startswith("DA_Enemy_Zombie")]
    for dp in das:
        try:
            da = EAL.load_asset(dp)
            ref = da.get_editor_property("hit_react_montage") or da.get_editor_property("attack_montage")
            if ref is None:
                warn(f"{dp}: sem montage de referência (não sei o esqueleto)")
                continue
            skel = skeleton_of(pkg(ref))
            tgt = zombie_target(skel)
            if tgt is None:
                warn(f"{dp}: esqueleto {skel} sem retargeter conhecido")
                continue
            if tgt["kind"] == "Manny":
                out = {s: manny_out.get(s) for s in srcs.values()}
                sfx = "_Manny"
            elif tgt["kind"] == "Copzombie":
                rtg = EAL.load_asset(tgt["rtg"])
                if rtg is None:
                    warn(f"{dp}: falta {tgt['rtg']}")
                    continue
                m_out = retarget([v for v in manny_out.values()], manny, EAL.load_asset(tgt["mesh"]), rtg, tgt["suffix"],
                                 tgt["base"])
                out = {s: m_out.get(manny_out.get(s)) for s in srcs.values()}
                sfx = "_Manny" + tgt["suffix"]
            else:
                rtg = EAL.load_asset(tgt["rtg"])
                if rtg is None:
                    warn(f"{dp}: falta {tgt['rtg']} (rode setup_zombie_models.py antes)")
                    continue
                out = retarget(list(srcs.values()), xbot, EAL.load_asset(tgt["mesh"]), rtg, tgt["suffix"], tgt["base"])
                sfx = tgt["suffix"]
            for it in items:
                seq = out.get(srcs.get(it["name"]))
                if not seq:
                    continue
                m = montage(seq, f"AM_{it['name']}{sfx}")
                if it["role"] == "feed":
                    cur = da.get_editor_property("feed_montage")
                    if cur is None or "Zombie_Feed" in cur.get_name():
                        da.set_editor_property("feed_montage", m)
                        log(f"{dp}.FeedMontage = {m.get_name()}")
                    else:
                        warn(f"{dp}: FeedMontage já é {cur.get_name()} (mantido)")
                elif it["role"] == "idle_variation":
                    var = list(da.get_editor_property("idle_variation_montages") or [])
                    var = [x for x in var if x and it["name"] not in x.get_name()] + [m]
                    da.set_editor_property("idle_variation_montages", var)
                    log(f"{dp}.IdleVariationMontages += {m.get_name()}")
            save(da)
        except Exception as exc:  # noqa: BLE001
            err(dp, exc)


def mixamo():
    xbot = EAL.load_asset(XBOT)
    if xbot is None:
        raise RuntimeError("falta /Game/Characters/Mixamo/SK_XBot (rode setup_mixamo.py)")
    present = []
    for it in MIXAMO:
        f = os.path.join(RAW, it["group"], it["name"] + ".fbx")
        if os.path.exists(f):
            present.append(it)
        else:
            R["missing_downloads"].append(f"assets/raw/mixamo/{it['group']}/{it['name']}.fbx  <- mixamo.com: {it['search']}")
    log(f"Mixamo: {len(present)} de {len(MIXAMO)} arquivos presentes")
    hero_mixamo([i for i in present if i["group"] == "hero"], xbot)
    zombie_mixamo([i for i in present if i["group"] == "zombie"], xbot)
    for it in present:
        if it["group"] == "npc":
            import_anim(os.path.join(RAW, "npc", it["name"] + ".fbx"), "npc", xbot.skeleton)
            warn(f"{it['name']} importado no X Bot; para usar na sobrevivente troque SURVIVOR_IDLE no setup_zombie_models.py")


def main():
    for fn in (shotgun_anims, mixamo):
        try:
            fn()
        except Exception as exc:  # noqa: BLE001
            err(fn.__name__, exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    with open(os.path.join(REPO, "reports", "setup_anims_wave2.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[anims_wave2] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])} | "
               f"faltam baixar: {len(R['missing_downloads'])}")
