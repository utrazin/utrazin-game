"""HUD v2 (A-059): importa as texturas e a fonte do HUD novo. Pode rodar de novo (substitui).

O que faz:
  1. Importa assets/work/ui/v2/T_HUD2_*.png para /Game/UI/HUD/V2 com ajustes de UI (sem mipmaps, grupo UI,
     sem compressão com perda, sempre carregada, filtro bilinear), igual às texturas antigas do HUD.
  2. Importa a fonte Fredoka (OFL, assets/raw/fonts/fredoka) como Font Face em /Game/UI/HUD/V2/Fonts
     (FF_HUD2_FredokaBold e FF_HUD2_FredokaSemiBold, dados embutidos no asset). O AJRHUD cria as fontes de
     cada tamanho em tempo de execução a partir dessas Font Faces.
  3. Garante /Game/UI/HUD/V2 em "Directories to Always Cook" (DefaultGame.ini): o HUD carrega tudo pelo caminho.
  4. Confere se o C++ novo está compilado (AJRHUD com HudScale).

Não precisa de material para o minimapa: o C++ desenha o mapa recortado numa elipse com um leque de
triângulos (o Canvas não tem máscara) e a moldura por cima.
As texturas antigas (/Game/UI/HUD/T_UI_* e /Game/UI/HUD/Wheel) ficam no projeto, mas o HUD não usa mais.

Antes: python tools/pipeline/make_hud_v2.py (gera as texturas; já vêm prontas no repositório).
RODA NO EDITOR (caixa Cmd do Output Log), depois de compilar o C++ novo:
  py "E:/game/utrazin-game/tools/unreal/setup_hud_v2.py"
Relatório: reports/setup_hud_v2.json
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

SRC = os.path.join(REPO, "assets", "work", "ui", "v2")
DST = "/Game/UI/HUD/V2"
FONT_SRC = os.path.join(REPO, "assets", "raw", "fonts", "fredoka")
FONT_DST = DST + "/Fonts"
FONTS = {"Fredoka-Bold.ttf": "FF_HUD2_FredokaBold", "Fredoka-SemiBold.ttf": "FF_HUD2_FredokaSemiBold"}
GAME_INI = os.path.join(REPO, "unreal", "JogoResgate", "Config", "DefaultGame.ini")


def log(m):
    R["steps"].append(m)
    unreal.log(f"[hud_v2] {m}")


def warn(m):
    R["warnings"].append(m)
    unreal.log_warning(f"[hud_v2] {m}")


def err(where, exc):
    R["errors"].append({"where": where, "e": str(exc), "t": traceback.format_exc()[-1500:]})
    unreal.log_error(f"[hud_v2] {where}: {exc}")


def setp(obj, prop, value, name):
    try:
        obj.set_editor_property(prop, value)
    except Exception as exc:  # noqa: BLE001
        warn(f"{name}: não consegui ajustar {prop} ({exc})")


def import_file(path, folder, name):
    task = unreal.AssetImportTask()
    task.filename = path
    task.destination_path = folder
    task.destination_name = name
    task.automated = True
    task.replace_existing = True
    task.save = False
    TOOLS.import_asset_tasks([task])
    return EAL.load_asset(f"{folder}/{name}")


# ------------------------------------------------------------------ 1. texturas
def textures():
    if not os.path.isdir(SRC):
        raise RuntimeError(f"pasta {SRC} não existe (rode tools/pipeline/make_hud_v2.py)")
    EAL.make_directory(DST)
    names = []
    for f in sorted(os.listdir(SRC)):
        if not (f.startswith("T_HUD2_") and f.endswith(".png")):
            continue
        name = f[:-4]
        t = import_file(os.path.join(SRC, f), DST, name)
        if t is None:
            warn(f"textura não importada: {f}")
            continue
        setp(t, "compression_settings", unreal.TextureCompressionSettings.TC_EDITOR_ICON, name)
        setp(t, "mip_gen_settings", unreal.TextureMipGenSettings.TMGS_NO_MIPMAPS, name)
        setp(t, "lod_group", unreal.TextureGroup.TEXTUREGROUP_UI, name)
        setp(t, "never_stream", True, name)
        setp(t, "srgb", True, name)
        setp(t, "filter", unreal.TextureFilter.TF_BILINEAR, name)
        # bordas: pílulas e teclas são desenhadas em fatias; repetir a borda evita fiapos
        setp(t, "address_x", unreal.TextureAddress.TA_CLAMP, name)
        setp(t, "address_y", unreal.TextureAddress.TA_CLAMP, name)
        EAL.save_loaded_asset(t, only_if_is_dirty=False)
        names.append(name)
    R["info"]["textures"] = names
    log(f"{len(names)} texturas importadas em {DST}")
    if len(names) < 50:
        warn(f"esperava ~56 texturas, importou {len(names)}")


# ------------------------------------------------------------------ 2. fonte
def fonts():
    EAL.make_directory(FONT_DST)
    for file_name, asset in FONTS.items():
        path = os.path.join(FONT_SRC, file_name)
        if not os.path.exists(path):
            warn(f"fonte {path} não existe")
            continue
        obj = import_file(path, FONT_DST, asset)
        if obj is None:
            warn(f"fonte não importada: {file_name}")
            continue
        cls = obj.get_class().get_name()
        R["info"][asset] = cls
        if cls != "FontFace":
            warn(f"{asset} virou {cls} (o HUD espera FontFace; ele cai na fonte padrão se não achar)")
        else:
            # dados da fonte dentro do asset (vale também no jogo empacotado)
            try:
                setp(obj, "loading_policy", unreal.FontLoadingPolicy.INLINE, asset)
            except Exception as exc:  # noqa: BLE001
                warn(f"{asset}: loading_policy ({exc})")
        EAL.save_loaded_asset(obj, only_if_is_dirty=False)
        log(f"fonte {asset} ({cls})")


# ------------------------------------------------------------------ 3. empacotamento
def always_cook():
    if not os.path.exists(GAME_INI):
        warn("DefaultGame.ini não encontrado")
        return
    text = open(GAME_INI, encoding="utf-8").read()
    line = '+DirectoriesToAlwaysCook=(Path="/Game/UI/HUD/V2")'
    if line in text:
        log("DefaultGame.ini já cozinha /Game/UI/HUD/V2")
        return
    section = "[/Script/UnrealEd.ProjectPackagingSettings]"
    if section in text:
        text = text.replace(section, section + "\n" + line, 1)
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n" + line + "\n"
    with open(GAME_INI, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    log("DefaultGame.ini: /Game/UI/HUD/V2 em Directories to Always Cook")


# ------------------------------------------------------------------ 4. C++
def check_cpp():
    cls = getattr(unreal, "JRHUD", None)
    if cls is None:
        warn("classe JRHUD não encontrada: compile o C++ antes")
        return
    try:
        cdo = unreal.get_default_object(cls)
        R["info"]["hud_scale"] = cdo.get_editor_property("hud_scale")
        log("C++ novo do HUD encontrado (HudScale)")
    except Exception:  # noqa: BLE001
        warn("o HUD compilado ainda é o antigo (sem HudScale): feche o editor e compile de novo")


def step(fn):
    try:
        fn()
    except Exception as exc:  # noqa: BLE001
        err(fn.__name__, exc)


try:
    step(textures)
    step(fonts)
    step(always_cook)
    step(check_cpp)
except Exception as exc:  # noqa: BLE001
    err("main", exc)
finally:
    os.makedirs(os.path.join(REPO, "reports"), exist_ok=True)
    with open(os.path.join(REPO, "reports", "setup_hud_v2.json"), "w", encoding="utf-8") as fh:
        json.dump(R, fh, ensure_ascii=False, indent=1, default=str)
    unreal.log(f"[hud_v2] fim | avisos: {len(R['warnings'])} | erros: {len(R['errors'])}")
