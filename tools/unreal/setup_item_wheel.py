"""Roda de itens (Tab / LB) e cura rápida (H / direcional para baixo), A-055. Pode rodar de novo.

O que faz:
  1. Cria IA_ItemWheel e IA_Heal (Boolean) em /Game/Core/Input.
  2. Liga as teclas no IMC_JR_Combat (contexto "a pé"): Tab + Gamepad_LeftShoulder -> IA_ItemWheel,
     H + Gamepad_DPad_Down -> IA_Heal. Procura conflitos dessas teclas em TODOS os IMC do projeto e relata.
     Confere se o IMC_JR_Combat está nos contextos "a pé" do BP_PlayerController (põe se faltar).
  3. Liga as ações nos BPs dos heróis (dono do input da roda = AJRCharacter): item_wheel_action e heal_action.
     Só relata HealAnim/HealUseTime/HealDuration (quem preenche a animação é o agente de animações).
  4. Importa assets/work/ui/wheel/T_UI_Wheel_*.png para /Game/UI/HUD/Wheel com ajustes de UI
     (sem mipmaps, grupo UI, sem compressão, sempre carregada), igual ao setup_wave1.py.
  5. Confere se o modelo do kit médico do usuário existe (/Game/Environment/User/Itens/SM_ITM_KitMedico):
     o C++ (AJRPickup) já usa essa malha sozinho para itens do tipo Medkit sem malha própria.

RODA NO EDITOR (caixa Cmd), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_item_wheel.py"
Relatório: reports/setup_item_wheel.json
"""
import json
import os
import traceback
from datetime import datetime

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"time": datetime.now().isoformat(), "steps": [], "warnings": [], "errors": [], "info": {}}

INPUT_DIR = "/Game/Core/Input"
IMC_COMBAT = INPUT_DIR + "/IMC_JR_Combat"
PC_BP = "/Game/Core/BP_PlayerController"
HEROES = {
    "Hero01": "/Game/Characters/Hero01/BP_Character_Hero01",
    "Hero02": "/Game/Characters/Hero02/BP_Character_Hero02",
}
ACTIONS = {
    # nome da IA: (teclas, propriedade no AJRCharacter)
    "IA_ItemWheel": (("Tab", "Gamepad_LeftShoulder"), "item_wheel_action"),
    "IA_Heal": (("H", "Gamepad_DPad_Down"), "heal_action"),
}
WHEEL_SRC = os.path.join(REPO, "assets", "work", "ui", "wheel")
WHEEL_DST = "/Game/UI/HUD/Wheel"
MEDKIT_MESH = "/Game/Environment/User/Itens/SM_ITM_KitMedico"


def log(m):
    R["steps"].append(m)
    unreal.log(f"[item_wheel] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[item_wheel] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[item_wheel] {where}: {exc}")


def setp(obj, k, v, where=""):
    try:
        obj.set_editor_property(k, v)
        return True
    except Exception as exc:  # noqa: BLE001
        warn(f"{where}.{k}: {exc}")
        return False


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


# ------------------------------------------------------------------ 1. ações
def input_actions():
    out = {}
    for name in ACTIONS:
        path = f"{INPUT_DIR}/{name}"
        if EAL.does_asset_exist(path):
            ia = EAL.load_asset(path)
            log(f"{name} já existe")
        else:
            fc = getattr(unreal, "InputAction_Factory", None)
            ia = TOOLS.create_asset(name, INPUT_DIR, unreal.InputAction, fc() if fc else None)
            log(f"{name} criada")
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
        EAL.save_loaded_asset(ia, only_if_is_dirty=False)
        out[name] = ia
    return out


# ------------------------------------------------------------------ 2. teclas e conflitos
def conflicts():
    """Avisa se alguma tecla nova já faz outra coisa em algum IMC do projeto (antes de ligar)."""
    wanted = {k: n for n, (keys, _) in ACTIONS.items() for k in keys}
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
                if key in wanted and act != wanted[key]:
                    found.append({"imc": path, "action": act, "key": key, "new_action": wanted[key],
                                  "same_context": path == IMC_COMBAT})
    except Exception as exc:  # noqa: BLE001
        warn(f"verificação de conflitos: {exc}")
    R["info"]["key_conflicts"] = found
    for c in found:
        where = "no MESMO contexto (as duas ações disparam juntas!)" if c["same_context"] else \
            "em outro contexto (só conflita se os dois estiverem ativos ao mesmo tempo)"
        warn(f"conflito: {c['key']} também faz {c['action']} em {c['imc']} {where}")
    if not found:
        log("nenhum conflito de teclas (Tab, LB, H, direcional para baixo)")


def mapping(actions):
    imc = EAL.load_asset(IMC_COMBAT)
    if imc is None:
        raise RuntimeError(f"não existe {IMC_COMBAT} (rode setup_m1_assets.py antes)")
    have = mappings_of(imc)
    imc.modify()
    for name, (keys, _) in ACTIONS.items():
        for k in keys:
            if (name, k) in have:
                continue
            imc.map_key(actions[name], make_key(k))
            log(f"tecla {k} -> {name} (IMC_JR_Combat)")
    EAL.save_loaded_asset(imc, only_if_is_dirty=False)
    R["info"]["imc_combat"] = mappings_of(EAL.load_asset(IMC_COMBAT))
    return imc


def player_controller(imc):
    """A roda só funciona a pé: o IMC_JR_Combat precisa estar nos contextos a pé (e não no carro)."""
    try:
        bp, cdo = cdo_of(PC_BP)
    except Exception as exc:  # noqa: BLE001
        warn(f"BP_PlayerController: {exc}")
        return
    on_foot = list(cdo.get_editor_property("on_foot_mapping_contexts"))
    vehicle = list(cdo.get_editor_property("vehicle_mapping_contexts"))
    R["info"]["on_foot_contexts"] = [c.get_path_name() if c else None for c in on_foot]
    R["info"]["vehicle_contexts"] = [c.get_path_name() if c else None for c in vehicle]
    if imc in vehicle:
        warn("IMC_JR_Combat também está nos contextos do carro: a roda abriria no carro (o C++ ignora, o herói não está possuído)")
    if imc not in on_foot:
        on_foot.append(imc)
        cdo.set_editor_property("on_foot_mapping_contexts", on_foot)
        compile_save(bp)
        log("IMC_JR_Combat adicionado aos contextos a pé do BP_PlayerController")
    else:
        log("IMC_JR_Combat já está nos contextos a pé")


# ------------------------------------------------------------------ 3. heróis
def heroes(actions):
    for name, path in HEROES.items():
        info = {}
        R["info"][name] = info
        try:
            bp, cdo = cdo_of(path)
        except Exception as exc:  # noqa: BLE001
            warn(f"{name}: {exc}")
            continue
        ok = True
        for ia_name, (_, prop) in ACTIONS.items():
            ok = setp(cdo, prop, actions[ia_name], name) and ok
        if not ok:
            warn(f"{name}: propriedades da roda não encontradas (o C++ novo foi compilado?)")
            continue
        compile_save(bp)
        log(f"{name}: item_wheel_action = IA_ItemWheel, heal_action = IA_Heal")
        for prop in ("heal_anim", "heal_use_time", "heal_duration", "item_wheel_time_dilation"):
            try:
                v = cdo.get_editor_property(prop)
                info[prop] = v.get_path_name() if hasattr(v, "get_path_name") else v
            except Exception as exc:  # noqa: BLE001
                info[prop] = f"? ({exc})"
        if not info.get("heal_anim"):
            warn(f"{name}: HealAnim vazio (a cura funciona sem animação; o agente de animações preenche)")


# ------------------------------------------------------------------ 4. texturas
def import_png(path, folder):
    name = os.path.splitext(os.path.basename(path))[0]
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    t = EAL.load_asset(f"{folder}/{name}")
    if t is None:
        raise RuntimeError(f"textura não importada: {path}")
    setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON, name)
    setp(t, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, name)
    setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_UI, name)
    setp(t, "never_stream", True, name)
    EAL.save_loaded_asset(t, only_if_is_dirty=False)
    return t


def wheel_textures():
    if not os.path.isdir(WHEEL_SRC):
        warn(f"pasta {WHEEL_SRC} não existe (rode tools/pipeline/make_item_wheel_ui.py)")
        return
    EAL.make_directory(WHEEL_DST)
    names = []
    for f in sorted(os.listdir(WHEEL_SRC)):
        if f.startswith("T_UI_Wheel_") and f.endswith(".png"):
            import_png(os.path.join(WHEEL_SRC, f), WHEEL_DST)
            names.append(f[:-4])
    R["info"]["wheel_textures"] = names
    log(f"{len(names)} texturas da roda importadas em {WHEEL_DST}")


# ------------------------------------------------------------------ 5. kit médico
def medkit_mesh():
    exists = EAL.does_asset_exist(MEDKIT_MESH)
    R["info"]["medkit_display_mesh"] = MEDKIT_MESH if exists else None
    if exists:
        log("SM_ITM_KitMedico encontrado: itens Medkit (drops e baús) aparecem com o modelo do usuário")
    else:
        warn("SM_ITM_KitMedico não importado (rode import_user_assets.py): o kit médico aparece como cubo vermelho")


def step(fn, *args):
    try:
        return fn(*args)
    except Exception as exc:  # noqa: BLE001
        err(fn.__name__, exc)
        return None


try:
    acts = step(input_actions)
    step(conflicts)
    if acts:
        ctx = step(mapping, acts)
        if ctx:
            step(player_controller, ctx)
        step(heroes, acts)
    step(wheel_textures)
    step(medkit_mesh)
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_item_wheel.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[item_wheel] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
