"""Cura com a animação nova "enrolar bandagem" (item 10 do handoff 2026-11-17, A-069). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play):
  py "E:/game/utrazin-game/tools/unreal/setup_bandage_anim.py"
  py "E:/game/utrazin-game/tools/unreal/setup_bandage_anim.py" reimportar   (depois de gerar o FBX de novo)
Relatório: reports/setup_bandage_anim.json

Entrada: assets/work/anims/A_Hero_Bandage_Mixamo.fbx, gerado fora da Unreal por tools/blender/gen_bandage_anim.py
(mesmo esqueleto mixamorig dos FBX do Mixamo, 30 fps, 72 quadros = 2,4 s).
Faz, do mesmo jeito que o setup_anims_wave2.py fez com a "Drinking":
 1. importa no esqueleto do X Bot em /Game/Characters/Mixamo/Anims/hero/A_Heal_Bandage_Wrap;
 2. retarget para Enzo e Victoria (RTG_Mixamo_HeroNN) em /Game/Characters/HeroNN/Anims/Wave3 (sufixo _HNN).
    A Unreal NUNCA sobrescreve no retarget: só faz o que falta; com "reimportar" vai para uma pasta nova
    (Wave3_2, Wave3_3...) e salva na hora;
 3. troca HealAnim no BP_Character_HeroNN para a nova. A antiga (A_Heal_Bandage_HNN, a "Drinking") continua
    no projeto: se algo der errado com a nova, o script não mexe e a antiga fica.
A cura toca HealAnim só na parte de cima do corpo (slot UpperBody): na Victoria o ABP_Unarmed_H02 ainda não
tem esse slot (passo manual antigo), então nela a animação pode não aparecer até o slot ser criado.
"""
import json
import os
import sys
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
FBX = os.path.join(REPO, "assets", "work", "anims", "A_Hero_Bandage_Mixamo.fbx")
NAME = "A_Heal_Bandage_Wrap"
SRC_FOLDER = "/Game/Characters/Mixamo/Anims/hero"
XBOT = "/Game/Characters/Mixamo/SK_XBot"
RIGS = "/Game/Characters/Rigs"
HEROES = ("01", "02")
FORCE = any(a.lower() in ("reimportar", "force") for a in sys.argv[1:])
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "force": FORCE, "steps": [], "warnings": [], "errors": [], "heroes": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[bandage_anim] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[bandage_anim] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1200:]})
    unreal.log_error(f"[bandage_anim] {where}: {exc}")


def pkg(obj_or_path):
    p = obj_or_path if isinstance(obj_or_path, str) else obj_or_path.get_path_name()
    p = p.split("'")[1] if "'" in p else p
    return p.split(".")[0]


def save(a):
    if a is not None:
        EAL.save_loaded_asset(a, only_if_is_dirty=False)


def import_anim(skeleton):
    target = f"{SRC_FOLDER}/{NAME}"
    if EAL.does_asset_exist(target) and not FORCE:
        log(f"{NAME} já importada (use 'reimportar' para trocar)")
        return target
    if not os.path.exists(FBX):
        raise FileNotFoundError(f"falta {FBX} (rode tools/blender/gen_bandage_anim.py)")
    task = unreal.AssetImportTask()
    task.filename = FBX
    task.destination_path = SRC_FOLDER
    task.destination_name = NAME
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
        raise RuntimeError(f"animação não importada: {FBX}")
    seq = EAL.load_asset(target)
    try:
        seq.set_editor_property("enable_root_motion", False)
    except Exception:  # noqa: BLE001
        pass
    save(seq)
    try:
        R["source_length_s"] = round(seq.get_play_length(), 3)
    except Exception:  # noqa: BLE001
        pass
    log(f"importada {target}")
    return target


def folders(base):
    out = [base] if EAL.does_directory_exist(base) else []
    for k in range(2, 100):
        if EAL.does_directory_exist(f"{base}_{k}"):
            out.append(f"{base}_{k}")
    return out


def fresh_folder(base):
    for f in [base] + [f"{base}_{k}" for k in range(2, 100)]:
        if not EAL.does_directory_exist(f) or not EAL.list_assets(f, recursive=True, include_folder=False):
            return f
    raise RuntimeError(f"sem pasta livre em {base}_N")


def retarget_one(src, xbot, mesh, rtg, suffix, base):
    """Retarget só se ainda não existe (ou com 'reimportar', numa pasta nova). Retorna o caminho da cópia."""
    out_name = src.split("/")[-1] + suffix
    if not FORCE:
        for f in reversed(folders(base)):        # a pasta mais nova primeiro
            if EAL.does_asset_exist(f"{f}/{out_name}"):
                return f"{f}/{out_name}"
    folder = fresh_folder(base)
    EAL.make_directory(folder)
    unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        [EAL.find_asset_data(src)], xbot, mesh, rtg, search="", replace="", prefix="", suffix=suffix,
        target_path=folder, use_source_path=False, include_referenced_assets=False, overwrite_existing_files=False)
    for a in EAL.list_assets(folder, recursive=True, include_folder=False):
        save(EAL.load_asset(pkg(a)))
    p = f"{folder}/{out_name}"
    if not EAL.does_asset_exist(p):
        raise RuntimeError(f"retarget não gerou {p}")
    log(f"retarget {out_name} -> {folder}")
    return p


def main():
    xbot = EAL.load_asset(XBOT)
    if xbot is None:
        raise RuntimeError(f"falta {XBOT} (rode setup_mixamo.py)")
    src = import_anim(xbot.skeleton)
    for nn in HEROES:
        info = {}
        R["heroes"][f"Hero{nn}"] = info
        try:
            rtg = EAL.load_asset(f"{RIGS}/RTG_Mixamo_Hero{nn}")
            mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
            if rtg is None or mesh is None:
                warn(f"Hero{nn}: falta RTG_Mixamo_Hero{nn} ou SK_Hero{nn}: HealAnim não mudou")
                continue
            out = retarget_one(src, xbot, mesh, rtg, f"_H{nn}", f"/Game/Characters/Hero{nn}/Anims/Wave3")
            bp_path = f"/Game/Characters/Hero{nn}/BP_Character_Hero{nn}"
            bp = EAL.load_asset(bp_path)
            cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
            old = cdo.get_editor_property("heal_anim")
            info["antes"] = pkg(old) if old else None
            new = EAL.load_asset(out)
            if new is None:
                warn(f"Hero{nn}: {out} não carregou: HealAnim não mudou")
                continue
            cdo.set_editor_property("heal_anim", new)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            save(bp)
            info["depois"] = out
            for k in ("heal_duration", "heal_use_time"):
                try:
                    info[k] = round(float(cdo.get_editor_property(k)), 3)
                except Exception:  # noqa: BLE001
                    pass
            log(f"Hero{nn}.heal_anim: {info['antes']} -> {out}")
        except Exception as exc:  # noqa: BLE001
            err(f"Hero{nn}", exc)
    if R["heroes"].get("Hero02", {}).get("depois"):
        warn("Victoria: a cura toca no slot UpperBody, que ainda falta no ABP_Unarmed_H02 (passo manual antigo)")


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_bandage_anim.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[bandage_anim] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
