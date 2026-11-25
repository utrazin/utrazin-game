"""[A-098] Bicicleta: importa as malhas novas (quadro sem pedivela, pedivela, pedal, selim, guidão) e a pedalada
de cada herói. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play), DEPOIS de compilar o C++ novo do AJRBike:
  py "E:/game/utrazin-game/tools/unreal/setup_bike_anim.py"
  py "E:/game/utrazin-game/tools/unreal/setup_bike_anim.py" reimportar   (depois de rodar gerar_bike_anim.bat de novo)
Relatório: reports/setup_bike_anim.json

Entradas (geradas por tools/blender/gen_bike_rider.py / E:\\game\\gerar_bike_anim.bat):
  assets/work/tripo/SM_VEH_Bike{QuadroSemPedivela,Pedivela,Pedal,Selim,Guidao}.fbx
  assets/work/anims/bike/A_Bike_Pedal_Hero01.fbx e _Hero02.fbx (esqueleto PRÓPRIO de cada herói: sem retarget)
  assets/work/anims/bike/bike_rider_info.json (posições esperadas dos ossos para conferir o import)
Faz:
 1. malhas em /Game/Environment/User/Veiculos/ com o MI_VEH_BikeQuadro (mesma textura do quadro antigo);
    o SM_VEH_BikeQuadro antigo fica (o AJRBike usa ele de reserva se o novo faltar);
 2. pedalada em /Game/Characters/HeroNN/Anims/Bike/A_Bike_Pedal_HNN no esqueleto do SK_HeroNN, sem root motion;
 3. confere: avalia o quadro 0 da animação importada (AnimPose) e compara pelve, mãos e pés com o que o Blender
    calculou (tolerância 3 cm). Se não bater, o relatório diz quanto e em que eixo (FBX com eixo trocado).
Os caminhos batem com os padrões do AJRBike (RiderAnims, FrameMesh, CrankMesh...), então não mexe em Blueprint.
"""
import json
import os
import sys
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TRIPO = os.path.join(REPO, "assets", "work", "tripo")
ANIMS = os.path.join(REPO, "assets", "work", "anims", "bike")
VEH = "/Game/Environment/User/Veiculos"
MI = f"{VEH}/Materials/MI_VEH_BikeQuadro"
MESHES = ("SM_VEH_BikeQuadroSemPedivela", "SM_VEH_BikePedivela", "SM_VEH_BikePedal", "SM_VEH_BikeSelim",
          "SM_VEH_BikeGuidao")
HEROES = ("01", "02")
FORCE = any(a.lower() in ("reimportar", "force") for a in sys.argv[1:])
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "force": FORCE, "steps": [], "warnings": [], "errors": [], "meshes": {},
     "heroes": {}}


def log(m):
    R["steps"].append(m)
    unreal.log(f"[bike_anim] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[bike_anim] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1200:]})
    unreal.log_error(f"[bike_anim] {where}: {exc}")


def setp(obj, k, v):
    try:
        obj.set_editor_property(k, v)
    except Exception as exc:  # noqa: BLE001
        warn(f"{k}: {exc}")


def save(a):
    if a is not None:
        EAL.save_loaded_asset(a, only_if_is_dirty=False)


def import_mesh(name):
    path = f"{VEH}/{name}"
    fbx = os.path.join(TRIPO, f"{name}.fbx")
    if EAL.does_asset_exist(path) and not FORCE:
        log(f"{name} já existe (use 'reimportar' para trocar)")
        return EAL.load_asset(path)
    if not os.path.exists(fbx):
        raise FileNotFoundError(f"falta {fbx} (rode E:\\game\\gerar_bike_anim.bat)")
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = VEH
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    o = unreal.FbxImportUI()
    o.import_mesh = True
    o.import_as_skeletal = False
    o.import_animations = False
    o.import_materials = False
    o.import_textures = False
    o.mesh_type_to_import = unreal.FBXImportType.FBXIT_STATIC_MESH
    d = o.static_mesh_import_data
    for k, v in (("combine_meshes", True), ("auto_generate_collision", False), ("generate_lightmap_u_vs", False),
                 ("build_nanite", False), ("one_convex_hull_per_ucx", True), ("import_uniform_scale", 1.0)):
        setp(d, k, v)
    task.options = o
    TOOLS.import_asset_tasks([task])
    sm = EAL.load_asset(path) if EAL.does_asset_exist(path) else None
    if not isinstance(sm, unreal.StaticMesh):
        raise RuntimeError(f"não virou StaticMesh: {path}")
    mi = EAL.load_asset(MI) if EAL.does_asset_exist(MI) else None
    if mi is None:
        warn(f"falta {MI}: {name} fica com o material padrão")
    else:
        for i in range(max(1, len(sm.get_editor_property("static_materials")))):
            sm.set_material(i, mi)
    if name == "SM_VEH_BikeQuadroSemPedivela":
        try:
            sub = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
            if sub.get_simple_collision_count(sm) == 0:
                sub.add_simple_collisions(sm, unreal.ScriptCollisionShapeType.BOX)
                warn(f"{name}: sem UCX; ganhou uma caixa")
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: colisão: {exc}")
    save(sm)
    b = sm.get_bounding_box()
    R["meshes"][name] = {"path": path, "size_cm": [round(b.max.x - b.min.x, 1), round(b.max.y - b.min.y, 1),
                                                   round(b.max.z - b.min.z, 1)]}
    log(f"importada {path}")
    return sm


def import_anim(nn, skeleton):
    folder = f"/Game/Characters/Hero{nn}/Anims/Bike"
    name = f"A_Bike_Pedal_H{nn}"
    target = f"{folder}/{name}"
    fbx = os.path.join(ANIMS, f"A_Bike_Pedal_Hero{nn}.fbx")
    if EAL.does_asset_exist(target) and not FORCE:
        log(f"{name} já importada (use 'reimportar' para trocar)")
        return EAL.load_asset(target)
    if not os.path.exists(fbx):
        raise FileNotFoundError(f"falta {fbx} (rode E:\\game\\gerar_bike_anim.bat)")
    EAL.make_directory(folder)
    task = unreal.AssetImportTask()
    task.filename = fbx
    task.destination_path = folder
    task.destination_name = name
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
    try:
        ad = o.anim_sequence_import_data
        ad.set_editor_property("animation_length", unreal.FBXAnimationLengthImportType.FBXALIT_EXPORTED_TIME)
        ad.set_editor_property("remove_redundant_keys", False)
    except Exception as exc:  # noqa: BLE001
        warn(f"opções da animação: {exc}")
    task.options = o
    TOOLS.import_asset_tasks([task])
    if not EAL.does_asset_exist(target):
        for p in task.imported_object_paths:
            p = p.split(".")[0]
            a = EAL.load_asset(p)
            if isinstance(a, unreal.AnimSequence):
                EAL.rename_asset(p, target)
                break
    if not EAL.does_asset_exist(target):
        raise RuntimeError(f"animação não importada: {fbx}")
    seq = EAL.load_asset(target)
    setp(seq, "enable_root_motion", False)
    save(seq)
    log(f"importada {target}")
    return seq


def check_pose(nn, seq, expected):
    """Compara o quadro 0 importado com o Blender (espaço do componente, cm)."""
    out = {}
    try:
        opts = unreal.AnimPoseEvaluationOptions()
        pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(seq, 0.0, opts)
        worst = 0.0
        for bone, want in expected.items():
            t = unreal.AnimPoseExtensions.get_bone_pose(pose, bone, unreal.AnimPoseSpaces.WORLD)
            got = t.translation
            d = [round(got.x - want[0], 1), round(got.y - want[1], 1), round(got.z - want[2], 1)]
            out[bone] = {"unreal": [round(got.x, 1), round(got.y, 1), round(got.z, 1)], "blender": want, "diff": d}
            worst = max(worst, max(abs(x) for x in d))
        out["worst_cm"] = worst
        if worst > 3.0:
            warn(f"Hero{nn}: pose importada difere do Blender em até {worst:.1f} cm (ver relatório: eixo trocado?)")
        else:
            log(f"Hero{nn}: pose importada bate com o Blender (pior {worst:.1f} cm)")
    except Exception as exc:  # noqa: BLE001
        warn(f"Hero{nn}: não deu para conferir a pose ({exc})")
    try:
        out["length_s"] = round(seq.get_play_length(), 3)
    except Exception:  # noqa: BLE001
        pass
    return out


def main():
    info_path = os.path.join(ANIMS, "bike_rider_info.json")
    info = json.load(open(info_path, encoding="utf-8")) if os.path.exists(info_path) else {}
    R["bike_scale_blender"] = info.get("bike_scale")
    R["cpp_blender"] = info.get("cpp")
    for name in MESHES:
        try:
            import_mesh(name)
        except Exception as exc:  # noqa: BLE001
            err(name, exc)
    for nn in HEROES:
        h = {}
        R["heroes"][f"Hero{nn}"] = h
        try:
            mesh = EAL.load_asset(f"/Game/Characters/Hero{nn}/Mesh/SK_Hero{nn}")
            if mesh is None:
                warn(f"falta SK_Hero{nn}")
                continue
            seq = import_anim(nn, mesh.skeleton)
            h["anim"] = seq.get_path_name().split(".")[0]
            exp = info.get("heroes", {}).get(f"Hero{nn}", {}).get("ue_component_cm_frame0")
            if exp:
                h["check"] = check_pose(nn, seq, exp)
        except Exception as exc:  # noqa: BLE001
            err(f"Hero{nn}", exc)


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
    with open(os.path.join(REPO, "reports", "setup_bike_anim.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[bike_anim] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
