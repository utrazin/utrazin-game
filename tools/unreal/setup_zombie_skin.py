"""Troca o boneco dos zumbis (Manny cinza) por um zumbi pronto do Mixamo (Copzombie, com texturas).

RODA NO EDITOR (caixa Cmd), DEPOIS do setup_wave1.py:
  py "E:/game/utrazin-game/tools/unreal/setup_zombie_skin.py"

Fonte: assets/raw/mixamo/zombie_chars/Copzombie.fbx (baixado do Mixamo, com pele)
1. Importa a malha em /Game/Enemies/Copzombie/SK_Copzombie (esqueleto próprio + física para o ragdoll)
2. Cria IK_Copzombie e RTG_Manny_Copzombie
3. Faz "duplicar e retargetar" do ABP atual dos zumbis e das montages (soco, reação) -> /Game/Enemies/Copzombie/Anims
4. SÓ SE TUDO DEU CERTO: os BPs dos zumbis passam a usar a malha/ABP novos e os DAs as montages novas.
   Se algo falhar, nada muda nos zumbis (continuam Manny com a pele alienígena do setup_wave1).
Desfazer: rode com UNDO=True no topo (volta para o Manny).
Relatório: reports/setup_zombie_skin.json
"""
import json
import os
import traceback
from datetime import datetime

import unreal

UNDO = False
REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
FBX = os.path.join(REPO, "assets", "raw", "mixamo", "zombie_chars", "Copzombie.fbx")
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
DST = "/Game/Enemies/Copzombie"
RIGS = "/Game/Characters/Rigs"
MANNY = "/Game/Characters/Mannequins/Meshes/SKM_Manny_Simple"
KINDS = ("Melee", "Archer", "Gunner", "Elite")
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[zombie_skin] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[zombie_skin] {m}")


def save(a):
    EAL.save_loaded_asset(a, only_if_is_dirty=False)


def cdo_of(path):
    bp = EAL.load_asset(path)
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def import_mesh():
    target = f"{DST}/SK_Copzombie"
    if EAL.does_asset_exist(target):
        log("SK_Copzombie já importado")
        return EAL.load_asset(target)
    task = unreal.AssetImportTask()
    task.filename = FBX
    task.destination_path = DST
    task.destination_name = "SK_Copzombie"
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = True
    o.import_animations = False
    o.import_materials = True
    o.import_textures = True
    o.create_physics_asset = True
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_SKELETAL_MESH
    task.options = o
    TOOLS.import_asset_tasks([task])
    paths = [p.split(".")[0] for p in task.imported_object_paths]
    R["info"]["imported"] = paths
    if not EAL.does_asset_exist(target):
        for p in paths:
            if isinstance(EAL.load_asset(p), unreal.SkeletalMesh):
                EAL.rename_asset(p, target)
                break
    m = EAL.load_asset(target)
    if m is None:
        raise RuntimeError(f"malha não importada: {paths}")
    log("SK_Copzombie importado")
    return m


def rigs(mesh):
    path = f"{RIGS}/IK_Copzombie"
    rig = EAL.load_asset(path) if EAL.does_asset_exist(path) else TOOLS.create_asset(
        "IK_Copzombie", RIGS, unreal.IKRigDefinition, unreal.IKRigDefinitionFactory())
    c = unreal.IKRigController.get_controller(rig)
    c.set_skeletal_mesh(mesh)
    c.apply_auto_generated_retarget_definition()
    save(rig)
    name = "RTG_Manny_Copzombie"
    if EAL.does_asset_exist(f"{RIGS}/{name}"):
        EAL.delete_asset(f"{RIGS}/{name}")
    rtg = TOOLS.create_asset(name, RIGS, unreal.IKRetargeter, unreal.IKRetargetFactory())
    rc = unreal.IKRetargeterController.get_controller(rtg)
    ST = unreal.RetargetSourceOrTarget
    src = EAL.load_asset(f"{RIGS}/IK_Manny")
    rc.set_ik_rig(ST.SOURCE, src)
    rc.set_ik_rig(ST.TARGET, rig)
    for side, m in ((ST.SOURCE, EAL.load_asset(MANNY)), (ST.TARGET, mesh)):
        try:
            rc.set_preview_mesh(side, m)
        except Exception:  # noqa: BLE001
            pass
    rc.add_default_ops()
    for side, r in ((ST.SOURCE, src), (ST.TARGET, rig)):
        rc.assign_ik_rig_to_all_ops(side, r)
    rc.auto_map_chains(unreal.AutoMapChainType.FUZZY, True)
    try:
        rc.auto_align_all_bones(ST.TARGET)
    except Exception as exc:  # noqa: BLE001
        warn(f"auto_align: {exc}")
    save(rtg)
    log("IK_Copzombie e RTG_Manny_Copzombie prontos")
    return rtg


def retarget(mesh, rtg):
    _, melee = cdo_of("/Game/Enemies/BP_Enemy_ZombieMelee")
    abp_cls = melee.get_editor_property("mesh").get_editor_property("anim_class")
    if abp_cls is None:
        raise RuntimeError("BP_Enemy_ZombieMelee sem ABP")
    abp_path = abp_cls.get_path_name().split(".")[0]
    R["info"]["abp_src"] = abp_path
    montages = {}
    for kind in ("Melee", "Archer", "Gunner"):
        da = EAL.load_asset(f"/Game/Data/DA_Enemy_Zombie{kind}")
        for prop in ("attack_montage", "hit_react_montage"):
            m = da.get_editor_property(prop)
            if m:
                montages[m.get_path_name().split(".")[0]] = True
    srcs = [abp_path] + list(montages)
    folder = f"{DST}/Anims"
    EAL.make_directory(folder)
    abp_name = abp_path.split("/")[-1] + "_CZ"
    if not EAL.does_asset_exist(f"{folder}/{abp_name}"):
        unreal.IKRetargetBatchOperation.duplicate_and_retarget(
            [EAL.find_asset_data(p) for p in srcs], EAL.load_asset(MANNY), mesh, rtg, search="", replace="", prefix="",
            suffix="_CZ", target_path=folder, use_source_path=False, include_referenced_assets=True,
            overwrite_existing_files=True)
    out = {"abp": f"{folder}/{abp_name}"}
    for p in montages:
        out[p] = f"{folder}/{p.split('/')[-1]}_CZ"
    missing = [v for v in out.values() if not EAL.does_asset_exist(v)]
    if missing:
        raise RuntimeError(f"retarget incompleto, nada foi trocado: {missing}")
    for a in EAL.list_assets(folder, recursive=True, include_folder=False):
        save(EAL.load_asset(a.split(".")[0]))
    R["info"]["map"] = out
    log(f"ABP e {len(montages)} montages retargetados")
    return out


def apply(mesh, out):
    abp = unreal.BlueprintEditorLibrary.generated_class(EAL.load_asset(out["abp"]))
    for kind in KINDS:
        path = f"/Game/Enemies/BP_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(path):
            continue
        bp, cdo = cdo_of(path)
        m = cdo.get_editor_property("mesh")
        m.set_editor_property("skeletal_mesh_asset", mesh)
        m.set_editor_property("anim_class", abp)
        m.set_editor_property("override_materials", [])  # usa as texturas do próprio zumbi
        unreal.BlueprintEditorLibrary.compile_blueprint(bp)
        save(bp)
        log(f"BP_Enemy_Zombie{kind}: Copzombie")
    for kind in ("Melee", "Archer", "Gunner", "Elite"):
        p = f"/Game/Data/DA_Enemy_Zombie{kind}"
        if not EAL.does_asset_exist(p):
            continue
        da = EAL.load_asset(p)
        for prop in ("attack_montage", "hit_react_montage"):
            m = da.get_editor_property(prop)
            if m:
                new = out.get(m.get_path_name().split(".")[0])
                if new:
                    da.set_editor_property(prop, EAL.load_asset(new))
        save(da)
    log("DAs apontam para as montages novas")


def undo():
    manny = EAL.load_asset(MANNY)
    prev = json.load(open(os.path.join(REPO, "reports", "setup_zombie_skin.json"), encoding="utf-8"))
    abp = unreal.BlueprintEditorLibrary.generated_class(EAL.load_asset(prev["info"]["abp_src"]))
    R["steps"].append("UNDO: voltando para o Manny (refaça o setup_wave1 para a pele alienígena e as montages)")
    for kind in KINDS:
        path = f"/Game/Enemies/BP_Enemy_Zombie{kind}"
        if EAL.does_asset_exist(path):
            bp, cdo = cdo_of(path)
            cdo.get_editor_property("mesh").set_editor_property("skeletal_mesh_asset", manny)
            cdo.get_editor_property("mesh").set_editor_property("anim_class", abp)
            unreal.BlueprintEditorLibrary.compile_blueprint(bp)
            save(bp)
    back = {v: k for k, v in prev["info"].get("map", {}).items() if k != "abp"}
    for kind in KINDS:
        p = f"/Game/Data/DA_Enemy_Zombie{kind}"
        if EAL.does_asset_exist(p):
            da = EAL.load_asset(p)
            for prop in ("attack_montage", "hit_react_montage"):
                m = da.get_editor_property(prop)
                if m and m.get_path_name().split(".")[0] in back:
                    da.set_editor_property(prop, EAL.load_asset(back[m.get_path_name().split(".")[0]]))
            save(da)


def main():
    if UNDO:
        undo()
        return
    if not os.path.exists(FBX):
        raise RuntimeError(f"falta {FBX}")
    mesh = import_mesh()
    rtg = rigs(mesh)
    out = retarget(mesh, rtg)
    apply(mesh, out)


try:
    main()
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1500:]})
finally:
    try:
        unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
    except Exception as exc:  # noqa: BLE001
        R["errors"].append({"save": str(exc)})
    with open(os.path.join(REPO, "reports", "setup_zombie_skin" + ("_undo" if UNDO else "") + ".json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[zombie_skin] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
