"""Atualiza um herói no Unreal com o rig novo, sem refazer o ABP.

RODA DENTRO DO EDITOR UNREAL (caixa Cmd):
  py "E:/game/utrazin-game/tools/unreal/update_hero.py" 01   (Enzo)
  py "E:/game/utrazin-game/tools/unreal/update_hero.py" 02   (Victoria)

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

import sys

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "steps": [], "errors": []}
NN = (sys.argv[1] if len(sys.argv) > 1 else "02").zfill(2)
FBX = os.path.join(REPO, f"assets/work/characters/CHR-0{NN}/SK_Hero{NN}_rig.fbx")
MESH = f"/Game/Characters/Hero{NN}/Mesh/SK_Hero{NN}"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
ANIMS_SRC = "/Game/Characters/Mannequins/Anims/Unarmed"
ANIMS_DST = f"/Game/Characters/Hero{NN}/Anims"
RIGS = "/Game/Characters/Rigs"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[hero] {m}")


def reimport():
    task = unreal.AssetImportTask()
    task.filename = FBX
    task.destination_path = f"/Game/Characters/Hero{NN}/Mesh"
    task.destination_name = f"SK_Hero{NN}"
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
    name = f"RTG_Manny_Hero{NN}"
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
    tgt_rig = ik_rig(f"IK_Hero{NN}", mesh)
    rtg = retargeter(src_rig, tgt_rig, src_mesh, mesh)
    srcs = []
    for p in EAL.list_assets(ANIMS_SRC, recursive=True, include_folder=False):
        d = EAL.find_asset_data(p)
        cls = str(d.asset_class_path.asset_name)
        if cls in ("AnimSequence", "BlendSpace"):
            srcs.append(d)
    out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        srcs, src_mesh, mesh, rtg, search="", replace="", prefix="", suffix=f"_H{NN}",
        target_path=ANIMS_DST, use_source_path=False, include_referenced_assets=False,
        overwrite_existing_files=True)
    log(f"animações refeitas: {len(out)}")
    R["anims"] = [str(a.package_name) for a in out]


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
    with open(os.path.join(REPO, "reports", f"update_hero{NN}.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=2, default=str)
    unreal.log(f"[hero] fim | erros: {len(R['errors'])}")
