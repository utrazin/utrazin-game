"""Sobrevivente do L01: anda/corre atrás do herói e senta no buggy (A-075). Pode rodar de novo.

RODA NO EDITOR (caixa Cmd), sem Play, DEPOIS de compilar o C++ novo e do setup_zombie_models.py
(que importou SK_NPC_Sobrevivente e criou IK_NPC_Sobrevivente / RTG_Mixamo_NPC_Sobrevivente):
  py E:/game/utrazin-game/tools/unreal/setup_passenger.py

Faz (só cria o que FALTA; nunca apaga):
 1. RTG_Manny_NPC_Sobrevivente (IK_Manny -> IK_NPC_Sobrevivente), se ainda não existir.
 2. Retarget para a sobrevivente, em /Game/Characters/Survivor/Anims/:
      A_NPC_Sobrevivente_Andar   <- Manny MF_Unarmed_Walk_Fwd
      A_NPC_Sobrevivente_Correr  <- Manny MF_Unarmed_Jog_Fwd
      A_NPC_Sobrevivente_Sentada <- X Bot A_Driving (pose sentada; mãos para frente, como no painel)
    Os nomes são fixos: o C++ (AJRRescueTarget) acha por caminho. Sem eles ela espera parada e embarca com fade.
Relatório: reports/setup_passenger.json
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
RIGS = "/Game/Characters/Rigs"
SV_MESH = "/Game/Characters/Survivor/SK_NPC_Sobrevivente"
SV_RIG = f"{RIGS}/IK_NPC_Sobrevivente"
OUT = "/Game/Characters/Survivor/Anims"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
XBOT = "/Game/Characters/Mixamo/SK_XBot"
JOBS = (  # (destino, origem, retargeter)
    ("A_NPC_Sobrevivente_Andar", "/Game/Characters/Mannequins/Anims/Unarmed/Walk/MF_Unarmed_Walk_Fwd", "Manny"),
    ("A_NPC_Sobrevivente_Correr", "/Game/Characters/Mannequins/Anims/Unarmed/Jog/MF_Unarmed_Jog_Fwd", "Manny"),
    ("A_NPC_Sobrevivente_Sentada", "/Game/Characters/Mixamo/Anims/hero/A_Driving", "Mixamo"),
)
SOURCES = {"Manny": (MANNY, f"{RIGS}/IK_Manny"), "Mixamo": (XBOT, f"{RIGS}/IK_Mixamo")}
REPORT = os.path.join(REPO, "reports", "setup_passenger.json")
R = {"time": datetime.now().isoformat(), "made": [], "skipped": [], "warnings": [], "errors": []}


def log(m):
    unreal.log(f"[passenger] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[passenger] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "error": str(exc), "trace": traceback.format_exc()})
    unreal.log_error(f"[passenger] {where}: {exc}")


def retargeter(key):
    path = f"{RIGS}/RTG_{key}_NPC_Sobrevivente"
    if EAL.does_asset_exist(path):
        return EAL.load_asset(path)
    src_mesh, src_rig = SOURCES[key]
    for p in (src_mesh, src_rig, SV_MESH, SV_RIG):
        if not EAL.does_asset_exist(p):
            raise RuntimeError(f"falta {p} (rode setup_zombie_models.py antes)")
    rtg = TOOLS.create_asset(f"RTG_{key}_NPC_Sobrevivente", RIGS, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    ST = unreal.RetargetSourceOrTarget
    a_src, a_tgt = EAL.load_asset(src_rig), EAL.load_asset(SV_RIG)
    rc.set_ik_rig(ST.SOURCE, a_src)
    rc.set_ik_rig(ST.TARGET, a_tgt)
    for side, m in ((ST.SOURCE, src_mesh), (ST.TARGET, SV_MESH)):
        try:
            rc.set_preview_mesh(side, EAL.load_asset(m))
        except Exception:  # noqa: BLE001
            pass
    rc.add_default_ops()
    for side, r in ((ST.SOURCE, a_src), (ST.TARGET, a_tgt)):
        rc.assign_ik_rig_to_all_ops(side, r)
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    try:
        rc.auto_align_all_bones(ST.TARGET)  # a sobrevivente está em pose A
    except Exception as exc:  # noqa: BLE001
        warn(f"auto_align: {exc}")
    EAL.save_loaded_asset(rtg, only_if_is_dirty=False)
    R["made"].append(path)
    return rtg


def retarget(dst_name, src, key):
    dst = f"{OUT}/{dst_name}"
    if EAL.does_asset_exist(dst):
        R["skipped"].append(dst)
        return
    if not EAL.does_asset_exist(src):
        raise RuntimeError(f"origem não existe: {src}")
    rtg = retargeter(key)
    EAL.make_directory(OUT)
    src_mesh = EAL.load_asset(SOURCES[key][0])
    tmp = f"{OUT}/_tmp_{dst_name}"
    EAL.make_directory(tmp)
    out = unreal.IKRetargetBatchOperation.duplicate_and_retarget(
        [EAL.find_asset_data(src)], src_mesh, EAL.load_asset(SV_MESH), rtg, search="", replace="", prefix="",
        suffix="_Sv", target_path=tmp, use_source_path=False, include_referenced_assets=False,
        overwrite_existing_files=False)
    made = None
    for o in out:
        p = str(getattr(o, "package_name", "") or "")
        if p and EAL.does_asset_exist(p) and isinstance(EAL.load_asset(p), unreal.AnimSequence):
            made = p
            break
    if not made:
        for p in EAL.list_assets(tmp, recursive=True, include_folder=False):
            if isinstance(EAL.load_asset(p.split(".")[0]), unreal.AnimSequence):
                made = p.split(".")[0]
                break
    if not made:
        raise RuntimeError(f"retarget não gerou animação para {dst_name}")
    if not EAL.rename_asset(made, dst):
        raise RuntimeError(f"não consegui renomear {made} -> {dst}")
    a = EAL.load_asset(dst)
    for prop, val in (("enable_root_motion", False), ("force_root_lock", True)):
        try:
            a.set_editor_property(prop, val)
        except Exception as exc:  # noqa: BLE001
            warn(f"{dst_name}.{prop}: {exc}")
    EAL.save_loaded_asset(a, only_if_is_dirty=False)
    R["made"].append(dst)
    log(f"{dst} criado")


def main():
    if not EAL.does_asset_exist(SV_MESH):
        raise RuntimeError(f"falta {SV_MESH}: rode setup_zombie_models.py primeiro")
    for dst_name, src, key in JOBS:
        try:
            retarget(dst_name, src, key)
        except Exception as exc:  # noqa: BLE001
            err(dst_name, exc)


try:
    main()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.dirname(REPORT), exist_ok=True)
    with open(REPORT, "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1)
    unreal.log(f"[passenger] fim | criados: {len(R['made'])} | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
