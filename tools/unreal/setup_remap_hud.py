"""HUD do Remap no estilo v2 (A-083): importa os ícones e peças de painel novos. Pode rodar de novo (substitui).

O que faz:
  1. Importa assets/work/ui/remap/T_HUD2_R_*.png para /Game/UI/HUD/V2 (mesma pasta e mesmos ajustes de UI das
     texturas da A-059: sem mipmaps, grupo UI, sem compressão com perda, sempre carregada, bilinear, clamp).
     A AJRRemapHUD acha cada uma pelo nome (HudTex("R_Coin") -> /Game/UI/HUD/V2/T_HUD2_R_Coin).
  2. Confere se /Game/UI/HUD/V2 está em "Directories to Always Cook" (o setup_hud_v2.py já põe).
  3. Confere se o C++ novo está compilado (classe JRRemapHUD).

Antes (opcional): python assets/work/ui/remap/_make_remap_hud.py (gera as PNG; já vêm prontas no repositório).
Depende de: setup_hud_v2.py já rodado uma vez (fonte Fredoka, pílulas, selo, anel e brilho da HUD v2).
RODA NO EDITOR (caixa Cmd do Output Log), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_remap_hud.py"
Relatório: reports/setup_remap_hud.json
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

SRC = os.path.join(REPO, "assets", "work", "ui", "remap")
DST = "/Game/UI/HUD/V2"
GAME_INI = os.path.join(REPO, "unreal", "JogoResgate", "Config", "DefaultGame.ini")
EXPECTED = 24


def log(m):
    R["steps"].append(m)
    unreal.log(f"[remap_hud] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[remap_hud] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[remap_hud] {where}: {exc}")


def setp(obj, prop, value, name):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:  # noqa: BLE001
        warn(f"{name}: não consegui ajustar {prop} ({exc})")


def textures():
    if not os.path.isdir(SRC):
        raise RuntimeError(f"pasta {SRC} não existe (rode assets/work/ui/remap/_make_remap_hud.py)")
    EAL.make_directory(DST)
    names = []
    for f in sorted(os.listdir(SRC)):
        if not (f.startswith("T_HUD2_R_") and f.endswith(".png")):
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
            warn(f"textura não importada: {f}")
            continue
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON, name)
        # [A-094] ícone (256 px) desenhado a ~28 a 48 px: sem mipmap ele serrilha/borra. Mipmap com nitidez e
        # trilinear nos ícones; painéis em 9 fatias, luz e bilhetes (desenhados grandes) continuam sem mipmap.
        is_icon = not any(k in name for k in ("Panel", "Light", "Note"))
        setp(t, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_SHARPEN2 if is_icon
             else unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, name)
        setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_UI, name)
        setp(t, "never_stream", True, name)
        setp(t, "srgb", True, name)
        setp(t, "filter", unreal.TextureFilter.TF_TRILINEAR if is_icon else unreal.TextureFilter.TF_BILINEAR, name)
        setp(t, "address_x", unreal.TextureAddress.TA_CLAMP, name)
        setp(t, "address_y", unreal.TextureAddress.TA_CLAMP, name)
        EAL.save_loaded_asset(t, only_if_is_dirty=False)
        names.append(name)
    R["info"]["textures"] = names
    log(f"{len(names)} texturas importadas em {DST}")
    if len(names) < EXPECTED:
        warn(f"esperava {EXPECTED} texturas T_HUD2_R_*, importou {len(names)}")
    # peças da HUD v2 que a HUD do Remap reaproveita
    for base in ("T_HUD2_Badge", "T_HUD2_Ring", "T_HUD2_Glow", "T_HUD2_PillTeal", "T_HUD2_PillNavy", "T_HUD2_PillLavender", "T_HUD2_Key"):
        if not EAL.does_asset_exist(f"{DST}/{base}"):
            warn(f"{base} não existe: rode antes tools/unreal/setup_hud_v2.py")


def always_cook():
    if not os.path.exists(GAME_INI):
        warn("DefaultGame.ini não encontrado")
        return
    text = open(GAME_INI, encoding="utf-8").read()
    if '+DirectoriesToAlwaysCook=(Path="/Game/UI/HUD/V2")' in text:
        log("DefaultGame.ini já cozinha /Game/UI/HUD/V2")
    else:
        warn("/Game/UI/HUD/V2 fora de Directories to Always Cook: rode tools/unreal/setup_hud_v2.py (ele põe)")


def check_cpp():
    if getattr(unreal, "JRRemapHUD", None) is None:
        warn("classe JRRemapHUD não encontrada: compile o C++ antes")
    else:
        log("classe JRRemapHUD encontrada")


def step(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        err(fn.__name__, exc)


try:
    step(textures)
    step(always_cook)
    step(check_cpp)
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_remap_hud.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[remap_hud] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
