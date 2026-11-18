"""Termina a troca das animações da Victoria (o update_victoria.py trocou 18 de 27 e não salvou as outras 9,
o que fez o Unreal fechar sozinho no setup_mixamo). Troca as que faltam, salvando uma por uma.

RODA NO EDITOR (caixa Cmd), logo depois de abrir o Unreal:
  py "E:/game/utrazin-game/tools/unreal/fix_victoria_anims.py"
Relatório: reports/fix_victoria_anims.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
ROOT = "/Game/Characters/Hero02/Anims"
R = {"steps": [], "errors": [], "ja_trocadas": [], "trocadas": []}

try:
    folders = sorted(p.rstrip("/") for p in EAL.list_assets(ROOT, recursive=False, include_folder=True)
                     if p.rstrip("/").split("/")[-1].startswith("R1") and EAL.does_directory_exist(p))
    if not folders:
        raise RuntimeError("pasta R... não encontrada em " + ROOT)
    new_dir = folders[-1]
    R["steps"].append(f"pasta nova: {new_dir}")
    for p in EAL.list_assets(new_dir, recursive=False, include_folder=False):
        new_path = p.split(".")[0]
        name = new_path.split("/")[-1]
        old_path = f"{ROOT}/{name}"
        if not EAL.does_asset_exist(old_path):
            continue
        old = EAL.load_asset(old_path)
        new = EAL.load_asset(new_path)
        if old is None or new is None:
            continue
        if old.get_path_name() == new.get_path_name():
            R["ja_trocadas"].append(name)  # já é um redirecionador para a nova
            continue
        if EAL.consolidate_assets(new, [old]):
            R["trocadas"].append(name)
            for q in (old_path, new_path):
                try:
                    EAL.save_asset(q, only_if_is_dirty=False)
                except Exception:  # noqa: BLE001
                    pass
        else:
            R["errors"].append({"consolidar": name})
    abp = f"{ROOT}/ABP_Unarmed_H02"
    EAL.load_asset(abp)
    EAL.save_asset(abp, only_if_is_dirty=False)
    unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    R["steps"].append(f"{len(R['trocadas'])} trocadas agora, {len(R['ja_trocadas'])} já estavam")
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1200:]})
finally:
    with open(os.path.join(REPO, "reports", "fix_victoria_anims.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[fix_victoria_anims] fim | erros: {len(R['errors'])}")
