"""Atualiza só a Victoria (CHR-002) no Unreal com o rig novo, sem refazer o ABP.

RODA DENTRO DO EDITOR UNREAL (caixa Cmd):
  py "E:/game/utrazin-game/tools/unreal/update_victoria.py"

v2 (2026-11-15): o Unreal não sobrescreve animações existentes (cria cópias com outro nome e não salva).
Agora o retarget vai para uma pasta NOVA (Anims/R<data>) e as antigas são "consolidadas" nas novas
(o ABP passa a usar as novas e as antigas são apagadas). A pasta Anims/Mixamo é apagada para o
setup_mixamo.py refazer do zero.

1. Reimporta assets/work/characters/CHR-002/SK_Hero02_rig.fbx por cima de /Game/Characters/Hero02/Mesh/SK_Hero02
2. Refaz IK_Hero02 e RTG_Manny_Hero02
3. Refaz (sobrescreve) as 21 animações _H02 a partir do Manny. O ABP_Unarmed_H02 é mantido
   (o Alpha 0 do Control Rig continua valendo).
Relatório: reports/update_victoria.json
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "steps": [], "errors": []}
FBX = os.path.join(REPO, "assets/work/characters/CHR-002/SK_Hero02_rig.fbx")
MESH = "/Game/Characters/Hero02/Mesh/SK_Hero02"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ANIMS_SRC = "/Game/Characters/Mannequins/Anims/Unarmed"
ANIMS_DST = "/Game/Characters/Hero02/Anims"
RIGS = "/Game/Characters/Rigs"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[victoria] {m}")


def reimport():
    task = unreal.AssetImportTask()
    task.filename = FBX
    task.destination_path = "/Game/Characters/Hero02/Mesh"
    task.destination_name = "SK_Hero02"
    task.automated = True
    task.replace_existing = True
    task.save = True
    opts = unreal.FbxImportUI()
    opts.import_mesh = True
    opts.import_as_skeletal = True
    opts.import_animations = False
    opts.import_materials = False
    opts.import_textures = False
    opts.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    mesh = EAL.load_asset(MESH)
    if mesh and mesh.skeleton:
        opts.skeleton = mesh.skeleton
    try:
        opts.skeletal_mesh_import_data.set_editor_property("import_morph_targets", False)
        opts.skeletal_mesh_import_data.set_editor_property("update_skeleton_reference_pose", True)
    except Exception:  # noqa: BLE001
        pass
    task.options = opts
    TOOLS.import_asset_tasks([task])
    log(f"reimportado: {list(task.imported_object_paths)}")
    return EAL.load_asset(MESH)


def ik_rig(name, mesh):
    path = f"{RIGS}/{name}"
    rig = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        name, RIGS, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    c.apply_auto_generated_retarget_definition()
    EAL.save_loaded_asset(rig)
    return rig


def retargeter(src_rig, tgt_rig, src_mesh, tgt_mesh):
    name = "RTG_Manny_Hero02"
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
        log(f"auto_align falhou: {exc}")
    EAL.save_loaded_asset(rtg)
    log("retargeter refeito")
    return rtg


def main():
    src_mesh = EAL.load_asset(MANNY)
    mesh = reimport()
    src_rig = EAL.load_asset(f"{RIGS}/IK_Manny")
    tgt_rig = ik_rig("IK_Hero02", mesh)
    rtg = retargeter(src_rig, tgt_rig, src_mesh, mesh)
    srcs = []
    for p in EAL.list_assets(ANIMS_SRC, recursive=True, include_folder=False):
        d = EAL.find_asset_data(p)
        cls = str(d.asset_class_path.asset_name)
        if cls in ("AnimSequence", "BlendSpace"):
            srcs.append(d)
    stamp = datetime.now().strftime("R%m%d%H%M")
    folder = f"{ANIMS_DST}/{stamp}"
    EAL.make_directory(folder)
    out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        srcs, src_mesh, mesh, rtg, search="", replace="", prefix="", suffix="_H02",
        target_path=folder, use_source_path=False, include_referenced_assets=True,
        overwrite_existing_files=True)
    log(f"animações refeitas em {folder}: {len(out)}")
    R["anims"] = [str(a.package_name) for a in out]
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    # troca as antigas (raiz de Anims) pelas novas em todas as referências (ABP, BS...)
    done = 0
    for a in out:
        name = str(a.asset_name)
        old_path = f"{ANIMS_DST}/{name}"
        if not EAL.does_asset_exist(old_path):
            continue
        new = EAL.load_asset(str(a.package_name))
        old = EAL.load_asset(old_path)
        if new and old and EAL.consolidate_assets(new, [old]):
            done += 1
            for q in (old_path, str(a.package_name)):
                try:
                    EAL.save_asset(q, only_if_is_dirty=False)  # salvar na hora evita pacote "corrompido"
                except Exception:  # noqa: BLE001
                    pass
    log(f"{done} animações antigas substituídas pelas novas")
    mix = f"{ANIMS_DST}/Mixamo"
    if EAL.does_directory_exist(mix):
        EAL.delete_directory(mix)
        log("pasta Mixamo apagada (rode setup_mixamo.py depois)")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1500:]})
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        R["steps"].append("tudo salvo")
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    with open(os.path.join(REPO, "reports", "update_victoria.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2, default=str)
    unreal.log(f"[victoria] fim | erros: {len(R['errors'])}")
