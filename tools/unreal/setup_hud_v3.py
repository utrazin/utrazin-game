"""[A-087] Importa a arte nova da HUD pintada pelo usuário (Gemini, 22/11): cartas, faixas de onda, placa de nível,
janela e botões das lojas, ícones de cartas e de itens. Pode rodar de novo.

RODA NO EDITOR (caixa Cmd, sem Play):  py "E:/game/utrazin-game/tools/unreal/setup_hud_v3.py"
Entrada: assets/work/ui/v3/T_HUD2_V3_*.png (recortados do fundo branco; originais em assets/raw/ui_refs/v3/)
Saída:   /Game/UI/HUD/V2/T_HUD2_V3_*  (o AJRHUD acha por HudTex("V3_..."))
"""
import os

import unreal

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SRC = os.path.join(REPO, "assets", "work", "ui", "v3")
DST = "/Game/UI/HUD/V2"
EAL = unreal.EditorAssetLibrary
TOOLS = unreal.AssetToolsHelpers.get_asset_tools()


def setp(obj, prop, value):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:  # noqa: BLE001
        unreal.log_warning(f"[hud_v3] {obj.get_name()}.{prop}: {exc}")


EAL.make_directory(DST)
n = 0
for f in sorted(os.listdir(SRC)):
    if not (f.startswith("T_HUD2_V3_") and f.endswith(".png")):
        continue
    name = f[:-4]
    task = unreal.AssetImportTask()
    task.filename = os.path.join(SRC, f)
    task.destination_path = DST
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    t = EAL.load_asset(f"{DST}/{name}")
    if t is None:
        unreal.log_warning(f"[hud_v3] não importou {f}")
        continue
    setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON)
    setp(t, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS)
    setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_UI)
    setp(t, "never_stream", True)
    setp(t, "srgb", True)
    setp(t, "filter", unreal.TextureFilter.TF_BILINEAR)
    setp(t, "address_x", unreal.TextureAddress.TA_CLAMP)
    setp(t, "address_y", unreal.TextureAddress.TA_CLAMP)
    EAL.save_loaded_asset(t, only_if_is_dirty=False)
    n += 1
unreal.log(f"[hud_v3] {n} texturas importadas em {DST} (esperado 27)")
