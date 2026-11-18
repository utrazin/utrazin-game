"""Primeira pessoa (tecla V): cria IA_ToggleView, liga V e o clique do analógico direito no IMC_JR_Global
e conecta a ação no BP_PlayerController. Confere o osso "head" dos heróis (a câmera em primeira pessoa
segue esse osso) e ajusta FPHeadBone/HiddenBones só se o esqueleto usar outro nome. Pode rodar de novo.

Não cria socket: a câmera é calculada no C++ (AJRCharacter::CalcCamera) a partir do osso da cabeça
+ EyeOffset no sentido do olhar, então não depende do eixo do osso de cada esqueleto.

RODA NO EDITOR (caixa Cmd), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_first_person.py"
Relatório: reports/setup_first_person.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"steps": [], "warnings": [], "errors": [], "info": {}}

INPUT_DIR = "/Game/Core/Input"
IA_PATH = INPUT_DIR + "/IA_ToggleView"
IMC_PATH = INPUT_DIR + "/IMC_JR_Global"
PC_BP = "/Game/Core/BP_PlayerController"
HEROES = {
    "Hero01": "/Game/Characters/Hero01/BP_Character_Hero01",
    "Hero02": "/Game/Characters/Hero02/BP_Character_Hero02",
}
KEYS = ("V", "Gamepad_RightThumbstick")


def log(m):
    R["steps"].append(m)
    unreal.log(f"[first_person] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[first_person] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[first_person] {where}: {exc}")


def make_key(name):
    k = unreal.Key()
    try:
        k.set_editor_property("key_name", name)
    except Exception:  # noqa: BLE001
        k.import_text(name)
    return k


def mappings_of(imc):
    """Lista (nome da ação, nome da tecla) de um IMC (API nova e antiga)."""
    maps = None
    try:
        maps = imc.get_editor_property("default_key_mappings").get_editor_property("mappings")
    except Exception:  # noqa: BLE001
        try:
            maps = imc.get_editor_property("mappings")
        except Exception as exc:  # noqa: BLE001
            warn(f"não li as teclas de {imc.get_name()}: {exc}")
            return []
    out = []
    for m in maps:
        try:
            act = m.get_editor_property("action")
            key = str(m.get_editor_property("key").get_editor_property("key_name"))
            out.append((act.get_name() if act else "None", key))
        except Exception:  # noqa: BLE001
            pass
    return out


def cdo_of(bp_path):
    bp = EAL.load_asset(bp_path)
    if bp is None:
        raise RuntimeError(f"não existe {bp_path}")
    return bp, unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))


def compile_save(bp):
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)


def input_action():
    if EAL.does_asset_exist(IA_PATH):
        ia = EAL.load_asset(IA_PATH)
        log("IA_ToggleView já existe")
    else:
        fc = getattr(unreal, "InputAction_Factory", None)
        ia = TOOLS.create_asset("IA_ToggleView", INPUT_DIR, unreal.InputAction, fc() if fc else None)
        log("IA_ToggleView criada")
    ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
    EAL.save_loaded_asset(ia, only_if_is_dirty=False)
    return ia


def mapping(ia):
    if EAL.does_asset_exist(IMC_PATH):
        imc = EAL.load_asset(IMC_PATH)
    else:
        fc = getattr(unreal, "InputMappingContext_Factory", None)
        imc = TOOLS.create_asset("IMC_JR_Global", INPUT_DIR, unreal.InputMappingContext, fc() if fc else None)
        log("IMC_JR_Global criado")
    have = mappings_of(imc)
    imc.modify()
    for k in KEYS:
        if ("IA_ToggleView", k) in have:
            continue
        imc.map_key(ia, make_key(k))
        log(f"tecla {k} -> IA_ToggleView (IMC_JR_Global)")
    EAL.save_loaded_asset(imc, only_if_is_dirty=False)
    R["info"]["imc_global"] = mappings_of(EAL.load_asset(IMC_PATH))
    return imc


def conflicts():
    """Avisa se V ou o clique do analógico direito já fazem outra coisa em algum IMC do projeto."""
    found = []
    try:
        reg = unreal.AssetRegistryHelpers.get_asset_registry()
        assets = reg.get_assets_by_class(unreal.TopLevelAssetPath("/Script/EnhancedInput", "InputMappingContext"))
        for data in assets:
            path = str(data.package_name)
            if not path.startswith("/Game/"):
                continue
            imc = EAL.load_asset(path)
            if imc is None:
                continue
            for act, key in mappings_of(imc):
                if key in KEYS and act != "IA_ToggleView":
                    found.append({"imc": path, "action": act, "key": key})
    except Exception as exc:  # noqa: BLE001
        warn(f"verificação de conflitos: {exc}")
    R["info"]["key_conflicts"] = found
    for c in found:
        warn(f"conflito: {c['key']} também faz {c['action']} em {c['imc']} (as duas ações disparam)")


def player_controller(ia, imc):
    bp, cdo = cdo_of(PC_BP)
    cdo.set_editor_property("toggle_view_action", ia)
    glob = list(cdo.get_editor_property("global_mapping_contexts"))
    if imc not in glob:
        glob.append(imc)
        cdo.set_editor_property("global_mapping_contexts", glob)
        log("IMC_JR_Global adicionado aos contextos globais")
    compile_save(bp)
    log("BP_PlayerController: toggle_view_action = IA_ToggleView")


def bone_names_from(anim):
    pose = unreal.AnimPoseExtensions.get_anim_pose_at_time(anim, 0.0, unreal.AnimPoseEvaluationOptions())
    return pose, [str(n) for n in unreal.AnimPoseExtensions.get_bone_names(pose)]


def heroes():
    for name, path in HEROES.items():
        info = {}
        R["info"][name] = info
        try:
            bp, cdo = cdo_of(path)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: {exc}")
            continue
        anim = None
        for prop in ("aim_anim", "driving_anim", "open_chest_anim", "pickup_anim"):
            try:
                anim = cdo.get_editor_property(prop)
            except Exception:  # noqa: BLE001
                anim = None
            if anim:
                info["anim_for_bones"] = anim.get_path_name()
                break
        if not anim:
            warn(f"{name}: sem animação no BP para ler os ossos; mantendo FPHeadBone = head")
            continue
        try:
            pose, names = bone_names_from(anim)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: não li os ossos ({exc}); mantendo FPHeadBone = head")
            continue
        info["neck_head_bones"] = [n for n in names if "head" in n.lower() or "neck" in n.lower()]
        head = "head" if "head" in names else next(
            (n for n in names if n.lower().endswith("head") and "top" not in n.lower()), None)
        if head is None:
            warn(f"{name}: nenhum osso de cabeça encontrado; primeira pessoa usa a altura dos olhos da cápsula")
            continue
        try:
            W = unreal.AnimPoseSpaces.WORLD
            info["head_height_cm"] = round(float(unreal.AnimPoseExtensions.get_bone_pose(pose, head, W).translation.z), 1)
        except Exception:  # noqa: BLE001
            pass
        if head != "head":
            cdo.set_editor_property("fp_head_bone", unreal.Name(head))
            cdo.set_editor_property("hidden_bones", [unreal.Name(head)])
            compile_save(bp)
            log(f"{name}: osso da cabeça = {head} (FPHeadBone e HiddenBones ajustados)")
        else:
            log(f"{name}: osso 'head' ok (padrão do C++)")
        try:
            info["eye_offset"] = str(cdo.get_editor_property("eye_offset"))
            info["stabilize_alpha"] = float(cdo.get_editor_property("stabilize_alpha"))
            info["fp_fov"] = float(cdo.get_editor_property("fp_fov"))
            info["hidden_bones"] = [str(b) for b in cdo.get_editor_property("hidden_bones")]
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: propriedades Camera|FirstPerson não encontradas (o C++ novo foi compilado?): {exc}")


try:
    action = input_action()
    context = mapping(action)
    conflicts()
    player_controller(action, context)
    heroes()
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_first_person.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[first_person] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
