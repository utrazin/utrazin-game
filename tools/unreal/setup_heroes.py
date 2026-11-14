"""Importa os rigs do Enzo (CHR-001) e da Victoria (CHR-002) e liga às animações do Manny.

RODA DENTRO DO EDITOR UNREAL (caixa Cmd, embaixo):
  py "E:/game/utrazin-game/tools/unreal/setup_heroes.py"

Passos:
  1. Importa assets/work/characters/CHR-00X/SK_HeroNN_rig.fbx -> /Game/Characters/HeroNN/Mesh
  2. Cria IK Rigs (Manny e heróis) e um IK Retargeter por herói (mapeamento automático).
  3. Duplica e retargeta ABP_Unarmed (+ animações que ele usa) para cada herói.
  4. Ajusta BP_Character_Hero01 (Enzo), cria BP_Character_Hero02 (Victoria),
     DA_Character_Hero02 e coloca os dois no BP_GameInstance.
Idempotente: pode rodar de novo. Relatório em reports/setup_heroes.json.
Para trocar de personagem jogando: console (tecla ') -> JRHeroi CHR-001 / JRHeroi CHR-002
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
REPORT = {"time": datetime.now().isoformat(), "steps": [], "errors": [], "warnings": [], "info": {}}

MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ABP = "/Game/Characters/Mannequins/Anims/Unarmed/ABP_Unarmed"
RIGS = "/Game/Characters/Rigs"
HEROES = [
    {"id": "CHR-001", "nn": "01", "name": "Enzo", "skin": "SKN-001",
     "fbx": os.path.join(REPO, "assets/work/characters/CHR-001/SK_Hero01_rig.fbx")},
    {"id": "CHR-002", "nn": "02", "name": "Victoria", "skin": "SKN-003",
     "fbx": os.path.join(REPO, "assets/work/characters/CHR-002/SK_Hero02_rig.fbx")},
]


def log(msg):
    REPORT["steps"].append(msg)
    unreal.log(f"[heroes] {msg}")


def warn(msg):
    REPORT["warnings"].append(msg)
    unreal.log_warning(f"[heroes] {msg}")


def err(where, exc):
    REPORT["errors"].append({"where": where, "error": str(exc), "trace": traceback.format_exc()[-1200:]})
    unreal.log_error(f"[heroes] {where}: {exc}")


def api(obj):
    return sorted(n for n in dir(obj) if not n.startswith("_"))


def save(asset):
    try:
        EAL.save_loaded_asset(asset)
    except Exception as exc:  # noqa: BLE001
        err(f"save {asset}", exc)


def assets_in(folder, cls_name):
    out = []
    for p in EAL.list_assets(folder, recursive=True, include_folder=False):
        data = EAL.find_asset_data(p)
        cname = str(data.asset_class_path.asset_name) if hasattr(data, "asset_class_path") else str(data.asset_class)
        if cname == cls_name:
            out.append(EAL.load_asset(p.split(".")[0]))
    return out


# ------------------------------------------------------------------ 1. import
def import_hero(h):
    folder = f"/Game/Characters/Hero{h['nn']}/Mesh"
    target = f"{folder}/SK_Hero{h['nn']}"
    if EAL.does_asset_exist(target):
        log(f"{h['name']}: malha já importada ({target})")
        return EAL.load_asset(target)
    if not os.path.exists(h["fbx"]):
        raise RuntimeError(f"FBX não encontrado: {h['fbx']}")
    task = unreal.AssetImportTask()
    task.filename = h["fbx"]
    task.destination_path = folder
    task.destination_name = f"SK_Hero{h['nn']}"
    task.automated = True
    task.replace_existing = True
    task.save = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = True
    opts.import_animations = False
    opts.import_materials = True
    opts.import_textures = True
    opts.create_physics_asset = True
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    sk = opts.skeletal_mesh_import_data
    for k, v in (("import_morph_targets", False), ("convert_scene", True), ("import_meshes_in_bone_hierarchy", True)):
        try:
            sk.set_editor_property(k, v)
        except Exception:  # noqa: BLE001
            pass
    task.options = opts
    TOOLS.import_asset_tasks([task])
    log(f"{h['name']}: importado -> {list(task.imported_object_paths)}")
    meshes = assets_in(folder, "SkeletalMesh")
    if not meshes:
        raise RuntimeError(f"nenhuma SkeletalMesh criada em {folder}")
    mesh = meshes[0]
    if mesh.get_path_name().split(".")[0] != target:
        EAL.rename_asset(mesh.get_path_name().split(".")[0], target)
        mesh = EAL.load_asset(target)
    save(mesh)
    return mesh


def mesh_info(mesh):
    try:
        b = mesh.get_bounds()
        return {"origin": [round(b.origin.x), round(b.origin.y), round(b.origin.z)],
                "extent": [round(b.box_extent.x), round(b.box_extent.y), round(b.box_extent.z)],
                "skeleton": mesh.skeleton.get_path_name() if mesh.skeleton else None}
    except Exception as exc:  # noqa: BLE001
        return {"error": str(exc)}


# ------------------------------------------------------------------ 2. IK rigs + retargeter
def ensure_ik_rig(name, mesh):
    path = f"{RIGS}/{name}"
    if EAL.does_asset_exist(path):
        rig = EAL.load_asset(path)
    else:
        EAL.make_directory(RIGS)
        rig = TOOLS.create_asset(name, RIGS, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    ctrl = unreal.IKRigController.get_controller(rig)
    ctrl.set_skeletal_mesh(mesh)
    ok = False
    for fn in ("apply_auto_generated_retarget_definition", "apply_auto_retarget_definition"):
        if hasattr(ctrl, fn):
            getattr(ctrl, fn)()
            ok = True
            break
    if not ok:
        warn(f"{name}: sem auto retarget definition. API: {api(ctrl)}")
    try:
        chains = [str(c.get_editor_property("chain_name")) for c in ctrl.get_retarget_chains()]
        REPORT["info"][f"{name}_chains"] = chains
        root = ctrl.get_retarget_root()
        REPORT["info"][f"{name}_root"] = str(root)
    except Exception as exc:  # noqa: BLE001
        warn(f"{name}: não listou cadeias ({exc})")
    save(rig)
    log(f"IK Rig {name} pronto")
    return rig


def ensure_retargeter(name, src_rig, tgt_rig, src_mesh, tgt_mesh):
    path = f"{RIGS}/{name}"
    if EAL.does_asset_exist(path):
        EAL.delete_asset(path)  # refaz sempre (config automática)
    rtg = TOOLS.create_asset(name, RIGS, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    REPORT["info"]["retargeter_api"] = api(rc)
    ST = unreal.RetargetSourceOrTarget
    rc.set_ik_rig(ST.SOURCE, src_rig)
    rc.set_ik_rig(ST.TARGET, tgt_rig)
    for fn, args in (("set_preview_mesh", (ST.SOURCE, src_mesh)), ("set_preview_mesh", (ST.TARGET, tgt_mesh))):
        try:
            getattr(rc, fn)(*args)
        except Exception:  # noqa: BLE001
            pass
    # UE 5.6+: pilha de operações
    for fn in ("add_default_ops",):
        if hasattr(rc, fn):
            try:
                getattr(rc, fn)()
                log(f"{name}: {fn}()")
            except Exception as exc:  # noqa: BLE001
                warn(f"{name}: {fn} falhou ({exc})")
    if hasattr(rc, "assign_ik_rig_to_all_ops"):
        for side, rig in ((ST.SOURCE, src_rig), (ST.TARGET, tgt_rig)):
            try:
                rc.assign_ik_rig_to_all_ops(side, rig)
            except Exception as exc:  # noqa: BLE001
                warn(f"{name}: assign_ik_rig_to_all_ops ({exc})")
    mapped = False
    for call in (lambda: rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True),
                 lambda: rc.auto_map_chains(unreal.AutoMapChainType.EXACT, True),
                 lambda: rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True, unreal.Name("None"))):
        try:
            call()
            mapped = True
            break
        except Exception as exc:  # noqa: BLE001
            last = exc
    if not mapped:
        warn(f"{name}: auto_map_chains falhou ({last})")
    for call in (lambda: rc.auto_align_all_bones(ST.TARGET),
                 lambda: rc.auto_align_all_bones(ST.TARGET, unreal.RetargetAutoAlignMethod.CHAIN_TO_CHAIN)):
        try:
            call()
            log(f"{name}: pose alinhada automaticamente")
            break
        except Exception:  # noqa: BLE001
            continue
    save(rtg)
    log(f"Retargeter {name} pronto")
    return rtg


# ------------------------------------------------------------------ 3. retarget ABP
def batch_retarget(assets, src_mesh, tgt_mesh, rtg, suffix, folder):
    fn = unreal.IKRetargetBatchOperation.duplicate_and_retarget
    doc = fn.__doc__ or ""
    REPORT["info"]["duplicate_and_retarget_doc"] = doc[:1500]
    EAL.make_directory(folder)
    kw = {"search": "", "replace": "", "prefix": "", "suffix": suffix}
    if "target_path" in doc:
        kw["target_path"] = folder
    if "include_referenced_assets" in doc:
        kw["include_referenced_assets"] = True
    if "overwrite_existing" in doc:
        kw["overwrite_existing_files"] = True if "overwrite_existing_files" in doc else None
        kw = {k: v for k, v in kw.items() if v is not None}
    return fn(assets, src_mesh, tgt_mesh, rtg, **kw)


def retarget_abp(h, src_mesh, tgt_mesh, rtg):
    suffix = f"_H{h['nn']}"
    new_path = f"/Game/Characters/Hero{h['nn']}/Anims/ABP_Unarmed{suffix}"
    if EAL.does_asset_exist(new_path):
        log(f"{h['name']}: {new_path} já existe")
        return EAL.load_asset(new_path)
    src = [EAL.find_asset_data(ABP)]
    out = batch_retarget(src, src_mesh, tgt_mesh, rtg, suffix, f"/Game/Characters/Hero{h['nn']}/Anims")
    log(f"{h['name']}: retarget de {len(out)} assets")
    REPORT["info"][f"retargeted_{h['nn']}"] = [str(a.package_name) for a in out]
    abp = EAL.load_asset(new_path) if EAL.does_asset_exist(new_path) else None
    if abp is None and EAL.does_asset_exist(f"{ABP}{suffix}"):
        abp = EAL.load_asset(f"{ABP}{suffix}")
    if abp is None:
        raise RuntimeError(f"ABP retargetado não encontrado: {new_path}")
    return abp


def retarget_montage(h, montage, src_mesh, tgt_mesh, rtg):
    if montage is None:
        return None
    suffix = f"_H{h['nn']}"
    folder = f"/Game/Characters/Hero{h['nn']}/Anims"
    p = f"{folder}/{montage.get_name()}{suffix}"
    if not EAL.does_asset_exist(p):
        batch_retarget([EAL.find_asset_data(montage.get_path_name().split(".")[0])], src_mesh, tgt_mesh, rtg, suffix, folder)
    return EAL.load_asset(p)


# ------------------------------------------------------------------ 4. blueprints / dados
def cdo_of(bp):
    return unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def ensure_char_bp(h):
    folder = f"/Game/Characters/Hero{h['nn']}"
    path = f"{folder}/BP_Character_Hero{h['nn']}"
    if not EAL.does_asset_exist(path):
        EAL.duplicate_asset("/Game/Characters/Hero01/BP_Character_Hero01", path)
        log(f"criado {path}")
    return EAL.load_asset(path)


def setup_char(h, bp, mesh, abp, src_mesh, rtg):
    cdo = cdo_of(bp)
    comp = cdo.get_editor_property("mesh")
    try:
        comp.set_skeletal_mesh_asset(mesh)
    except Exception:  # noqa: BLE001
        comp.set_editor_property("skeletal_mesh_asset", mesh)
    comp.set_editor_property("animation_mode", unreal.AnimationMode.ANIMATION_BLUEPRINT)
    comp.set_editor_property("anim_class", unreal.BlueprintEditorLibrary.generated_class(abp))
    comp.set_editor_property("relative_location", unreal.Vector(0, 0, -90))
    comp.set_editor_property("relative_rotation", unreal.Rotator(0, 0, -90))
    for prop in ("exit_vehicle_montage", "rescue_hug_montage", "death_montage"):
        try:
            m = cdo.get_editor_property(prop)
            if m is not None and m.get_editor_property("skeleton") != mesh.skeleton:
                nm = retarget_montage(h, m, src_mesh, mesh, rtg)
                if nm:
                    cdo.set_editor_property(prop, nm)
                    log(f"{h['name']}: {prop} retargetado")
        except Exception as exc:  # noqa: BLE001
            warn(f"{h['name']}.{prop}: {exc}")
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    save(bp)
    log(f"{h['name']}: BP configurado")


def ensure_def(h, bp, mesh):
    path = f"/Game/Data/DA_Character_Hero{h['nn']}"
    if not EAL.does_asset_exist(path):
        EAL.duplicate_asset("/Game/Data/DA_Character_Hero01", path)
    da = EAL.load_asset(path)
    skin = unreal.JRSkinDefinition()
    skin.set_editor_property("skin_id", h["skin"])
    skin.set_editor_property("mesh", mesh)
    for k, v in (("character_id", h["id"]), ("character_class", unreal.BlueprintEditorLibrary.generated_class(bp)),
                 ("skins", [skin])):
        try:
            da.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            err(f"{path}.{k}", exc)
    try:
        da.set_editor_property("display_name", h["name"])
    except Exception:  # noqa: BLE001
        pass
    save(da)
    return da


def main():
    src_mesh = EAL.load_asset(MANNY)
    src_rig = ensure_ik_rig("IK_Manny", src_mesh)
    defs = []
    for h in HEROES:
        try:
            mesh = import_hero(h)
            REPORT["info"][f"mesh_{h['nn']}"] = mesh_info(mesh)
            tgt_rig = ensure_ik_rig(f"IK_Hero{h['nn']}", mesh)
            rtg = ensure_retargeter(f"RTG_Manny_Hero{h['nn']}", src_rig, tgt_rig, src_mesh, mesh)
            abp = retarget_abp(h, src_mesh, mesh, rtg)
            bp = ensure_char_bp(h)
            setup_char(h, bp, mesh, abp, src_mesh, rtg)
            defs.append(ensure_def(h, bp, mesh))
        except Exception as exc:  # noqa: BLE001
            err(h["name"], exc)
    try:
        gi_bp = EAL.load_asset("/Game/Core/BP_GameInstance")
        cdo_of(gi_bp).set_editor_property("characters", defs)
        unreal.BlueprintEditorLibrary.compile_blueprint(gi_bp)
        save(gi_bp)
        log(f"BP_GameInstance: {len(defs)} personagens")
    except Exception as exc:  # noqa: BLE001
        err("BP_GameInstance", exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        REPORT["steps"].append("tudo salvo")
    except Exception as exc:  # noqa: BLE001
        err("save_dirty_packages", exc)
    out = os.path.join(REPO, "reports", "setup_heroes.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=2, default=str)
    unreal.log(f"[heroes] relatório: {out} | erros: {len(REPORT['errors'])}")
