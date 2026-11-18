"""Refaz BS_Idle_Walk_Run_H01/H02 com as animações de andar/correr certas (o erro
"BlendSpace ... animação inválida" fazia o herói encolher e sumir ao andar).

RODA NO EDITOR (caixa Cmd):
  py "E:/game/utrazin-game/tools/unreal/fix_blendspaces.py"
Relatório: reports/fix_blendspaces.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
R = {"steps": [], "errors": [], "samples": {}}
SRC_BS = "/Game/Characters/Mannequins/Anims/Unarmed/BS_Idle_Walk_Run"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"


def samples(bs_path):
    bs = EAL.load_asset(bs_path)
    out = []
    try:
        for s in bs.get_editor_property("sample_data"):
            a = s.get_editor_property("animation")
            out.append(f"{a.get_path_name() if a else 'NENHUMA'} | {a.get_editor_property('skeleton').get_name() if a else '-'}")
    except Exception as exc:  # noqa: BLE001
        out.append(f"ERR {exc}")
    return out


try:
    manny = EAL.load_asset(MANNY)
    for nn in ("01", "02"):
        bs_path = f"/Game/Characters/Hero{nn}/Anims/BS_Idle_Walk_Run_H{nn}"
        R["samples"][f"antes_{nn}"] = samples(bs_path)
        mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
        rtg = EAL.load_asset(f"/Game/Characters/Rigs/RTG_Manny_Hero{nn}")
        out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [EAL.find_asset_data(SRC_BS)], manny, mesh, rtg, search="", replace="", prefix="",
            suffix=f"_H{nn}", target_path=f"/Game/Characters/Hero{nn}/Anims", use_source_path=False,
            include_referenced_assets=True, overwrite_existing_files=True)
        R["steps"].append(f"Hero{nn}: {len(out)} assets refeitos")
        R["samples"][f"depois_{nn}"] = samples(bs_path)
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1500:]})
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
        R["steps"].append("salvo")
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    with open(os.path.join(REPO, "reports", "fix_blendspaces.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[fix_bs] fim | erros: {len(R['errors'])}")
