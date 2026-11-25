"""[A-088] Zumbi atirador segurando a arma "como estátua": animação de tiro de verdade.

Causa: o DA do atirador (DA_Enemy_ZombieGunner*) usa como "AttackMontage" o soco do zumbi. Ele parava, socava o ar com a
pistola presa na mão e o tiro saía sem o braço levantar. A pistola ficava dura na mão o resto do tempo.

O que este script faz (RODA NO EDITOR, caixa Cmd, sem Play, DEPOIS de compilar):
  py "E:/game/utrazin-game/tools/unreal/setup_zombie_gun.py"
1. Acha o BP do atirador (/Game/Enemies/BP_Enemy_ZombieGunner), a malha dele (ZMB_Corredor) e o DA.
2. Retargeta do X Bot (Mixamo) para essa malha: A_Shoot_Pistol (levanta, mira, atira) e A_Fire_Recoil.
   Usa o retargeter que já existe (RTG_Mixamo_<malha>).
3. Conserta a escala do Hips dessas cópias (mesma regra do fix_zombie_anim_scale.py).
4. Cria o montage AM_Zombie_ShootPistol_<malha> e põe no DA como AttackMontage.
O C++ (A-088) já espera RangedWindup (0,35 s) entre levantar a arma e o 1o tiro e dá um tranco na pistola a cada tiro.
Relatório: reports/setup_zombie_gun.json. Desfazer: o DA guarda o montage antigo no relatório ("before").
"""
import json
import os
import runpy
import sys
import traceback

import unreal

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
RIGS = "/Game/Characters/Rigs"
XBOT = "/Game/Characters/Mixamo/SK_XBot"
SOURCES = ["/Game/Characters/Mixamo/Anims/hero/A_Shoot_Pistol", "/Game/Characters/Mixamo/Anims/hero/A_Fire_Recoil"]
GUNNER_BP = "/Game/Enemies/BP_Enemy_ZombieGunner"
R = {"steps": [], "warnings": [], "errors": [], "before": {}, "after": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[zombie_gun] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[zombie_gun] {m}")


def pkg(obj_or_path):
    if obj_or_path is None:
        return None
    p = obj_or_path if isinstance(obj_or_path, str) else obj_or_path.get_path_name()
    return p.split(".")[0]


def save(a):
    if a is not None:
        EAL.save_loaded_asset(a, only_if_is_dirty=False)


def cdo_of(path):
    bp = EAL.load_asset(path)
    cls = unreal.BlueprintEditorLibrary.generated_class(bp)
    return bp, unreal.get_default_object(cls)


def main():
    if not EAL.does_asset_exist(GUNNER_BP):
        raise RuntimeError(f"não existe {GUNNER_BP}")
    bp, cdo = cdo_of(GUNNER_BP)
    mesh_comp = cdo.get_editor_property("mesh")
    mesh = mesh_comp.get_editor_property("skeletal_mesh_asset")
    if mesh is None:
        raise RuntimeError("atirador sem malha")
    mesh_path = pkg(mesh)
    name = mesh_path.split("/")[-1].replace("SK_", "")  # ex.: ZMB_Corredor
    R["mesh"] = mesh_path
    rtg_path = f"{RIGS}/RTG_Mixamo_{name}"
    if not EAL.does_asset_exist(rtg_path):
        raise RuntimeError(f"falta {rtg_path} (rode setup_zombie_chars.py)")
    rtg = EAL.load_asset(rtg_path)
    folder = mesh_path.rsplit("/", 1)[0] + "/Anims/Gun"
    sfx = "_" + name.replace("ZMB_", "")
    EAL.make_directory(folder)
    missing = [s for s in SOURCES if EAL.does_asset_exist(s) and not EAL.does_asset_exist(f"{folder}/{s.split('/')[-1]}{sfx}")]
    for s in SOURCES:
        if not EAL.does_asset_exist(s):
            warn(f"origem não existe (rode setup_mixamo.py): {s}")
    if missing:
        unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [EAL.find_asset_data(p) for p in missing], EAL.load_asset(XBOT), mesh, rtg,
            search="", replace="", prefix="", suffix=sfx, target_path=folder, use_source_path=False,
            include_referenced_assets=False, overwrite_existing_files=False)
        for a in EAL.list_assets(folder, recursive=True, include_folder=False):
            save(EAL.load_asset(pkg(a)))
        log(f"{len(missing)} animação(ões) retargetada(s) para {name} em {folder}")
    shoot = f"{folder}/A_Shoot_Pistol{sfx}"
    if not EAL.does_asset_exist(shoot):
        raise RuntimeError(f"retarget não gerou {shoot}")

    # Hips em escala 100 nesses rigs: sem o conserto o corpo encolhe e some durante o tiro.
    fix = os.path.join(HERE, "fix_zombie_anim_scale.py")
    if os.path.exists(fix):
        old_argv = sys.argv
        try:
            sys.argv = [fix]
            runpy.run_path(fix, run_name="__main__")
            log("fix_zombie_anim_scale rodado (Hips das animações novas)")
        finally:
            sys.argv = old_argv
    else:
        warn("fix_zombie_anim_scale.py não encontrado")

    mont_name = f"AM_Zombie_ShootPistol{sfx}"
    mont_path = f"{folder}/{mont_name}"
    if EAL.does_asset_exist(mont_path):
        mont = EAL.load_asset(mont_path)
    else:
        f = unreal.AnimMontageFactory()
        seq = EAL.load_asset(shoot)
        f.set_editor_property("source_animation", seq)
        try:
            f.set_editor_property("target_skeleton", seq.get_editor_property("skeleton"))
        except Exception:  # noqa: BLE001
            pass
        mont = TOOLS.create_asset(mont_name, folder, unreal.AnimMontage, f)
        try:
            mont.set_editor_property("blend_in", unreal.AlphaBlend(blend_time=0.15))
            mont.set_editor_property("blend_out", unreal.AlphaBlend(blend_time=0.25))
        except Exception as exc:  # noqa: BLE001
            warn(f"blend do montage: {exc}")
        save(mont)
        log(f"{mont_name} criado")

    da = cdo.get_editor_property("archetype")
    if da is None:
        raise RuntimeError("atirador sem DA (archetype)")
    R["before"]["da"] = pkg(da)
    R["before"]["attack_montage"] = pkg(da.get_editor_property("attack_montage"))
    da.set_editor_property("attack_montage", mont)
    save(da)
    R["after"]["attack_montage"] = pkg(mont)
    log(f"{pkg(da).split('/')[-1]}: AttackMontage = {mont_name}")


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append(str(exc))
    unreal.log_error(f"[zombie_gun] {exc}\n{traceback.format_exc()[-1500:]}")
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_zombie_gun.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[zombie_gun] fim | avisos {len(R['warnings'])} | erros {len(R['errors'])}")
