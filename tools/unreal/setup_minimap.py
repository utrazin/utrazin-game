"""Minimapa da L01: importa a imagem de cima, liga no DA_Level_L01 e cria a tecla M (mapa grande).
Usa T_L01_Minimap_v4.png (A-067, gerado por tools/pipeline/gen_minimap_l01.py) quando existir, senão a v3,
senão a v2. Com a v4 também importa T_L01_Map_v4.png (com nomes) para o mapa grande (BigMapTexture).

RODA NO EDITOR (caixa Cmd), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_minimap.py"
Relatório: reports/setup_minimap.json
"""
import json
import os
import traceback

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()
R = {"steps": [], "errors": []}
PNG = os.path.join(REPO, "assets", "work", "levels", "L01", "T_L01_Minimap.png")
LAYOUT = os.path.join(REPO, "assets", "work", "levels", "L01", "l01_layout.json")
# v3 (vale aberto, Etapa 5): usa a imagem e o layout novos quando existirem
_V3_PNG = os.path.join(REPO, "assets", "work", "levels", "L01", "T_L01_Minimap_v3.png")
_V3_LAYOUT = os.path.join(REPO, "assets", "work", "levels", "L01", "l01_layout_v3.json")
if os.path.exists(_V3_PNG) and os.path.exists(_V3_LAYOUT):
    PNG, LAYOUT = _V3_PNG, _V3_LAYOUT
# [A-067] v4 estilizada (mesmo enquadramento da v3) + versão com nomes para o mapa grande
_V4_PNG = os.path.join(REPO, "assets", "work", "levels", "L01", "T_L01_Minimap_v4.png")
_V4_BIG = os.path.join(REPO, "assets", "work", "levels", "L01", "T_L01_Map_v4.png")
BIG_PNG = None
if os.path.exists(_V4_PNG) and os.path.exists(_V3_LAYOUT):
    PNG, LAYOUT = _V4_PNG, _V3_LAYOUT
    BIG_PNG = _V4_BIG if os.path.exists(_V4_BIG) else None


def log(m):
    R["steps"].append(m)
    unreal.log(f"[minimap] {m}")


def key(name):
    k = unreal.Key()
    k.import_text(name)
    return k


def import_ui_texture(png, name):
    task = unreal.AssetImportTask()
    task.filename = png
    task.destination_path = "/Game/UI/Minimap"
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = True
    TOOLS.import_asset_tasks([task])
    t = EAL.load_asset(f"/Game/UI/Minimap/{name}")
    for k, v in (("compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON),
                 ("mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS),
                 ("lod_group", unreal.TextureGroup.TEXTUREGROUP_UI), ("never_stream", True), ("srgb", True)):
        try:
            t.set_editor_property(k, v)
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({"tex": k, "e": str(exc)})
    EAL.save_loaded_asset(t, only_if_is_dirty=False)
    return t


try:
    tex = import_ui_texture(PNG, "T_L01_Minimap")
    log(f"textura do minimapa importada ({os.path.basename(PNG)})")
    big = import_ui_texture(BIG_PNG, "T_L01_Map") if BIG_PNG else None
    if big:
        log(f"textura do mapa grande importada ({os.path.basename(BIG_PNG)})")

    half = json.load(open(LAYOUT, encoding="utf-8"))["map_half_cm"]
    da = EAL.load_asset("/Game/Data/DA_Level_L01_Zombies")
    da.set_editor_property("minimap_texture", tex)
    if big:
        try:
            da.set_editor_property("big_map_texture", big)   # [A-067] precisa do C++ novo
        except Exception as exc:  # noqa: BLE001
            R["errors"].append({"big_map_texture (compile o C++ novo)": str(exc)})
    da.set_editor_property("minimap_world_min", unreal.Vector2D(-half, -half))
    da.set_editor_property("minimap_world_max", unreal.Vector2D(half, half))
    EAL.save_loaded_asset(da, only_if_is_dirty=False)
    log("DA_Level_L01 ligado ao minimapa")

    ia_path = "/Game/Core/Input/IA_ToggleMap"
    if EAL.does_asset_exist(ia_path):
        ia = EAL.load_asset(ia_path)
    else:
        fc = getattr(unreal, "InputAction_Factory", None)
        ia = TOOLS.create_asset("IA_ToggleMap", "/Game/Core/Input", unreal.InputAction, fc() if fc else None)
        ia.set_editor_property("value_type", unreal.InputActionValueType.BOOLEAN)
        EAL.save_loaded_asset(ia, only_if_is_dirty=False)
    imc_path = "/Game/Core/Input/IMC_JR_Global"
    if EAL.does_asset_exist(imc_path):
        imc = EAL.load_asset(imc_path)
    else:
        fc = getattr(unreal, "InputMappingContext_Factory", None)
        imc = TOOLS.create_asset("IMC_JR_Global", "/Game/Core/Input", unreal.InputMappingContext, fc() if fc else None)
    have = [str(m.get_editor_property("key").get_editor_property("key_name"))
            for m in imc.get_editor_property("default_key_mappings").get_editor_property("mappings")]
    imc.modify()
    for k in ("M", "Gamepad_Special_Left"):
        if k not in have:
            imc.map_key(ia, key(k))
    EAL.save_loaded_asset(imc, only_if_is_dirty=False)
    log("tecla M criada (IMC_JR_Global)")

    bp = EAL.load_asset("/Game/Core/BP_PlayerController")
    cdo = unreal.get_default_object(unreal.BlueprintEditorLibrary.generated_class(bp))
    cdo.set_editor_property("toggle_map_action", ia)
    glob = list(cdo.get_editor_property("global_mapping_contexts"))
    if imc not in glob:
        glob.append(imc)
        cdo.set_editor_property("global_mapping_contexts", glob)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    EAL.save_loaded_asset(bp, only_if_is_dirty=False)
    log("BP_PlayerController com a tecla do mapa")
    R["check_imc"] = [str(m.get_editor_property("key").get_editor_property("key_name"))
                      for m in EAL.load_asset(imc_path).get_editor_property("default_key_mappings").get_editor_property("mappings")]
except Exception as exc:  # noqa: BLE001
    R["errors"].append({"e": str(exc), "t": traceback.format_exc()[-1500:]})
finally:
    with open(os.path.join(REPO, "reports", "setup_minimap.json"), "w", encoding="utf-8") as f:
        json.dump(R, f, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[minimap] fim | erros: {len(R['errors'])}")
