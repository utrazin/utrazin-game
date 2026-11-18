"""Troca a pistola dos heróis pelo modelo novo (assets/work/weapons/SM_AlienPistol.fbx) e reencaixa na mão.

RODA NO EDITOR (caixa Cmd):
  py "E:/game/utrazin-game/tools/unreal/update_weapon.py"
Relatório: reports/update_weapon.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"steps": [], "errors": [], "info": {}}


def grip(nn):
    seq = EAL.load_asset(f"/Game/Characters/Hero{nn}/Anims/Mixamo/A_Pistol_idle_H{nn}")
    p = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, 0.0, unreal.AnimPoseEvaluationOptions())
    W = unreal.AnimPoseSpaces.WORLD
    names = [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(p)]

    def t(b):
        return unreal.AnimPoseExtensions.get_bone_pose(p, b, W)
    hand = t("hand_r")
    h = hand.translation
    mid = t("middle_01_r").translation if "middle_01_r" in names else h
    chest = t(next((b for b in ("neck_01", "spine_05", "spine_03") if b in names), "pelvis")).translation
    fwd = unreal.MathLibrary.normal(unreal.Vector(h.x - chest.x, h.y - chest.y, 0.0))
    pos = unreal.Vector(h.x + (mid.x - h.x) * 0.5, h.y + (mid.y - h.y) * 0.5, h.z + (mid.z - h.z) * 0.5 - 2.0)
    gun = unreal.Transform(pos, unreal.MathLibrary.make_rot_from_xz(fwd, unreal.Vector(0, 0, 1)), unreal.Vector(1, 1, 1))
    return unreal.MathLibrary.make_relative_transform(gun, hand)


try:
    task = unreal.AssetImportTask()
    task.filename = os.path.join(REPO, "assets", "work", "weapons", "SM_AlienPistol.fbx")
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
    o.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    task.options = o
    TOOLS.import_asset_tasks([task])
    R["steps"].append(f"importado: {list(task.imported_object_paths)}")
    sm = EAL.load_asset("/Game/Weapons/SM_AlienPistol")
    for nn in ("01", "02"):
        bp = EAL.load_asset(f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}")
        cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
        wm = cdo.get_editor_property("weapon_mesh")
        wm.set_editor_property("static_mesh", sm)
        rel = grip(nn)
        wm.set_editor_property("relative_location", rel.translation)
        wm.set_editor_property("relative_rotation", rel.rotation.rotator())
        R["info"][f"H{nn}"] = {"loc": str(rel.translation), "rot": str(rel.rotation.rotator())}
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        EAL.save_loaded_asset(bp, only_if_is_dirty=False)
        R["steps"].append(f"Hero{nn}: pistola nova na mão")
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1200:]})
finally:
    with open(os.path.join(REPO, "reports", "update_weapon.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[update_weapon] fim | erros: {len(R['errors'])}")
