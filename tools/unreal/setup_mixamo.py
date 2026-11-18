"""Importa as animações do Mixamo e passa (retarget) para os heróis e para o Manny (zumbis).

RODA DENTRO DO EDITOR UNREAL (caixa Cmd), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_mixamo.py"

Fonte: assets/raw/mixamo (XBot.fbx + pastas hero, pistol, npc, zombie).
1. Importa o X Bot em /Game/Characters/Mixamo/SK_XBot e as animações em /Game/Characters/Mixamo/Anims/<grupo>/A_<nome>
2. Cria IK_Mixamo e os retargeters RTG_Mixamo_Hero01, RTG_Mixamo_Hero02, RTG_Mixamo_Manny
3. hero + pistol -> Enzo e Victoria (/Game/Characters/HeroNN/Anims/Mixamo, sufixo _HNN)
   zombie + npc  -> Manny (/Game/Enemies/Anims, sufixo _Manny)
4. Cria montages (AM_*) e preenche os BPs dos heróis e os DAs dos zumbis.
Pode rodar de novo: refaz tudo por cima. Relatório: reports/setup_mixamo.json
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
RAW = os.path.join(REPO, "assets", "raw", "mixamo")
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}}

MIX = "/Game/Characters/Mixamo"
RIGS = "/Game/Characters/Rigs"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ENEMY_ANIMS = "/Game/Enemies/Anims"
HEROES = ("01", "02")

# montages dos heróis: (propriedade no BP, animação, é montage?)
HERO_PROPS = (
    ("aim_anim", "Pistol_idle", False),
    ("fire_anim", "Fire_Recoil", False),
    ("equip_anim", "Equip_Pistol", False),
    ("unequip_anim", "Unequip_Pistol", False),
    ("reload_anim", "Reload_Pistol", False),
    ("hit_react_anim", "HitReact_Pistol", False),
    ("death_montage", "Death_Backwards", True),
    ("exit_vehicle_montage", "Car_Exit", True),
    ("rescue_hug_montage", "Rescue_HelpIntoVehicle", True),
)
ZOMBIE_PROPS = (("attack_montage", "Zombie_Punching"), ("hit_react_montage", "Zombie_ReactionHit"))


def log(m):
    R["steps"].append(m)
    unreal.log(f"[mixamo] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[mixamo] {m}")


def save(a):
    EAL.save_loaded_asset(a, only_if_is_dirty=False)


def obj_path(p):
    return p.split(".")[0]


# ------------------------------------------------------------------ 1. import
def import_xbot():
    target = f"{MIX}/SK_XBot"
    if EAL.does_asset_exist(target):
        log("X Bot já importado")
        return EAL.load_asset(target)
    task = unreal.AssetImportTask()
    task.filename = os.path.join(RAW, "XBot.fbx")
    task.destination_path = MIX
    task.destination_name = "SK_XBot"
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = True
    o.import_animations = False
    o.import_materials = False
    o.import_textures = False
    o.create_physics_asset = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    task.options = o
    TOOLS.import_asset_tasks([task])
    paths = list(task.imported_object_paths)
    log(f"X Bot importado: {paths}")
    if not EAL.does_asset_exist(target):
        for p in paths:
            a = EAL.load_asset(obj_path(p))
            if isinstance(a, unreal.SkeletalMesh):
                EAL.rename_asset(obj_path(p), target)
                break
    return EAL.load_asset(target)


def import_anim(fbx, group, skeleton):
    name = "A_" + os.path.splitext(os.path.basename(fbx))[0]
    folder = f"{MIX}/Anims/{group}"
    target = f"{folder}/{name}"
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
            a = EAL.load_asset(obj_path(p))
            if isinstance(a, unreal.AnimSequence):
                EAL.rename_asset(obj_path(p), target)
                break
    if not EAL.does_asset_exist(target):
        raise RuntimeError(f"animação não importada: {fbx} -> {list(task.imported_object_paths)}")
    return target


def import_all(skeleton):
    out = {}
    for group in ("hero", "pistol", "npc", "zombie"):
        d = os.path.join(RAW, group)
        if not os.path.isdir(d):
            warn(f"pasta ausente: {d}")
            continue
        out[group] = []
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(".fbx"):
                try:
                    out[group].append(import_anim(os.path.join(d, f), group, skeleton))
                except Exception as exc:  # noqa: BLE001
                    R["errors"].append({"import": f, "e": str(exc)})
        log(f"{group}: {len(out[group])} animações importadas")
    R["info"]["imported"] = out
    return out


# ------------------------------------------------------------------ 2. rigs
def ik_rig(name, mesh):
    path = f"{RIGS}/{name}"
    rig = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, RIGS, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    c.apply_auto_generated_retarget_definition()
    try:
        R["info"][f"{name}_chains"] = [str(x.get_editor_property("chain_name")) for x in c.get_retarget_chains()]
    except Exception:  # noqa: BLE001
        pass
    save(rig)
    return rig


def retargeter(name, src_rig, tgt_rig, src_mesh, tgt_mesh):
    path = f"{RIGS}/{name}"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    rtg = TOOLS.create_asset(name, RIGS, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    ST = unreal.RetargetSourceOrTarget
    rc.set_ik_rig(ST.SOURCE, src_rig)
    rc.set_ik_rig(ST.TARGET, tgt_rig)
    for side, m in ((ST.SOURCE, src_mesh), (ST.TARGET, tgt_mesh)):
        try:
            rc.set_preview_mesh(side, m)
        except Exception:  # noqa: BLE001
            pass
    rc.add_default_ops()
    for side, rig in ((ST.SOURCE, src_rig), (ST.TARGET, tgt_rig)):
        rc.assign_ik_rig_to_all_ops(side, rig)
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    try:
        rc.auto_align_all_bones(ST.TARGET)
    except Exception as exc:  # noqa: BLE001
        warn(f"{name}: auto_align falhou ({exc})")
    save(rtg)
    log(f"retargeter {name} pronto")
    return rtg


def retarget(paths, src_mesh, tgt_mesh, rtg, suffix, folder):
    EAL.make_directory(folder)
    datas = [EAL.find_asset_data(p) for p in paths]
    out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        datas, src_mesh, tgt_mesh, rtg, search="", replace="", prefix="", suffix=suffix,
        target_path=folder, use_source_path=False, include_referenced_assets=False,
        overwrite_existing_files=True)
    log(f"retarget {suffix}: {len(out)} animações -> {folder}")
    return folder


# ------------------------------------------------------------------ 3. montages / BPs
def montage(seq_path, folder, name, auto_blend_out=True):
    path = f"{folder}/{name}"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)
    seq = EAL.load_asset(seq_path)
    f = unreal.AnimMontageFactory()
    f.set_editor_property("source_animation", seq)
    try:
        f.set_editor_property("target_skeleton", seq.get_editor_property("skeleton"))
    except Exception:  # noqa: BLE001
        pass
    m = TOOLS.create_asset(name, folder, unreal.AnimMontage, f)
    if not auto_blend_out:
        try:
            m.set_editor_property("enable_auto_blend_out", False)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: enable_auto_blend_out ({exc})")
    save(m)
    return m


PISTOL_FBX = os.path.join(REPO, "assets", "work", "weapons", "SM_AlienPistol.fbx")
PISTOL = "/Game/Weapons/SM_AlienPistol"


def import_pistol():
    task = unreal.AssetImportTask()
    task.filename = PISTOL_FBX
    task.destination_path = "/Game/Weapons"
    task.destination_name = "SM_AlienPistol"
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = True
    o.import_textures = True
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    task.options = o
    TOOLS.import_asset_tasks([task])
    log(f"pistola importada: {list(task.imported_object_paths)}")
    return EAL.load_asset(PISTOL)


def toggle_weapon_action():
    path = "/Game/Core/Input/IA_ToggleWeapon"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    fc = getattr(unreal, "InputAction_Factory", None)
    ia = TOOLS.create_asset("IA_ToggleWeapon", "/Game/Core/Input", unreal.InputAction, fc() if fc else None)
    ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    save(ia)
    imc = EAL.load_asset("/Game/Core/Input/IMC_JR_Combat")
    for key in ("One", "Q", "Gamepad_FaceButton_Right"):
        k = unreal.Key()
        try:
            k.set_editor_property("key_name", key)
        except Exception:  # noqa: BLE001
            k.import_text(key)
        imc.map_key(ia, k)
    save(imc)
    log("IA_ToggleWeapon criado (teclas 1 e Q)")
    return ia


def weapon_grip(nn, folder):
    """Transform da pistola relativo ao osso hand_r, a partir da pose de mira (cano para frente, cima = +Z)."""
    seq = EAL.load_asset(f"{folder}/A_Pistol_idle_H{nn}")
    opts = unreal.AnimPoseEvaluationOptions()
    p = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, 0.0, opts)
    W = unreal.AnimPoseSpaces.WORLD

    def t(b):
        return unreal.AnimPoseExtensions.get_bone_pose(p, b, W)
    hand = t("hand_r")
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(p)]
    mid = t("middle_01_r").translation if "middle_01_r" in names else hand.translation
    chest_bone = next((b for b in ("neck_01", "spine_05", "spine_03") if b in names), "pelvis")
    chest = t(chest_bone).translation
    h = hand.translation
    fwd = unreal.Vector(h.x - chest.x, h.y - chest.y, 0.0)
    fwd = unreal.MathLibrary.normal(fwd)
    grip = unreal.Vector(h.x + (mid.x - h.x) * 0.5, h.y + (mid.y - h.y) * 0.5, h.z + (mid.z - h.z) * 0.5 - 2.0)
    rot = unreal.MathLibrary.make_rot_from_xz(fwd, unreal.Vector(0, 0, 1))
    gun = unreal.Transform(grip, rot, unreal.Vector(1, 1, 1))
    rel = unreal.MathLibrary.make_relative_transform(gun, hand)
    R["info"][f"grip_H{nn}"] = {"loc": str(rel.translation), "rot": str(rel.rotation.rotator()), "fwd": str(fwd)}
    return rel


def setup_hero(nn, folder):
    suffix = f"_H{nn}"
    bp_path = f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}"
    bp = EAL.load_asset(bp_path)
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    for prop, anim, is_montage in HERO_PROPS:
        seq_path = f"{folder}/A_{anim}{suffix}"
        if not EAL.does_asset_exist(seq_path):
            warn(f"Hero{nn}: falta {seq_path}")
            continue
        try:
            if is_montage:
                value = montage(seq_path, folder, f"AM_{anim}{suffix}", auto_blend_out=(prop != "death_montage"))
            else:
                value = EAL.load_asset(seq_path)
            cdo.set_editor_property(prop, value)
            log(f"Hero{nn}.{prop} = {value.get_name()}")
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({"hero": nn, "prop": prop, "e": str(exc)})
    try:
        cdo.set_editor_property("toggle_weapon_action", toggle_weapon_action())
        wm = cdo.get_editor_property("weapon_mesh")
        wm.set_editor_property("static_mesh", EAL.load_asset(PISTOL))
        rel = weapon_grip(nn, folder)
        wm.set_editor_property("relative_location", rel.translation)
        wm.set_editor_property("relative_rotation", rel.rotation.rotator())
        log(f"Hero{nn}: pistola na mão configurada")
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"hero": nn, "weapon": str(exc), "t": traceback.format_exc()[-800:]})
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)


def setup_zombies():
    made = {}
    for prop, anim in ZOMBIE_PROPS:
        seq_path = f"{ENEMY_ANIMS}/A_{anim}_Manny"
        if EAL.does_asset_exist(seq_path):
            made[prop] = montage(seq_path, ENEMY_ANIMS, f"AM_{anim}")
        else:
            warn(f"falta {seq_path}")
    for da in ("DA_Enemy_ZombieMelee", "DA_Enemy_ZombieArcher", "DA_Enemy_ZombieGunner"):
        p = f"/Game/Data/{da}"
        if not EAL.does_asset_exist(p):
            continue
        a = EAL.load_asset(p)
        for prop, m in made.items():
            if prop == "attack_montage" and da != "DA_Enemy_ZombieMelee":
                continue  # atirador e arqueiro não socam
            try:
                a.set_editor_property(prop, m)
            except Exception as exc:  # noqa: BLE001
                R["errors"].append({"da": da, "prop": prop, "e": str(exc)})
        save(a)
        log(f"{da}: montages preenchidas")


def main():
    xbot = import_xbot()
    anims = import_all(xbot.skeleton)
    import_pistol()
    src_rig = ik_rig("IK_Mixamo", xbot)
    for nn in HEROES:
        mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
        tgt_rig = EAL.load_asset(f"{RIGS}/IK_Hero{nn}")
        rtg = retargeter(f"RTG_Mixamo_Hero{nn}", src_rig, tgt_rig, xbot, mesh)
        folder = retarget(anims.get("hero", []) + anims.get("pistol", []), xbot, mesh, rtg,
                          f"_H{nn}", f"/Game/Characters/Hero{nn}/Anims/Mixamo")
        setup_hero(nn, folder)
    manny = EAL.load_asset(MANNY)
    rtg = retargeter("RTG_Mixamo_Manny", src_rig, EAL.load_asset(f"{RIGS}/IK_Manny"), xbot, manny)
    retarget(anims.get("zombie", []) + anims.get("npc", []), xbot, manny, rtg, "_Manny", ENEMY_ANIMS)
    setup_zombies()


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-2000:]})
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        R["steps"].append("tudo salvo")
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    with open(os.path.join(REPO, "reports", "setup_mixamo.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=2, default=str)
    unreal.log(f"[mixamo] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
