#!/usr/bin/env python3
"""Valida convenções de nomes de arquivos de assets (Unreal, Blender, exports).

Regras em .claude/rules/unreal-content.md e .claude/rules/blender-assets.md.

Exemplos:
  python tools/pipeline/validate_naming.py assets/final unreal/JogoResgate/Content
  python tools/pipeline/validate_naming.py blender/scenes/vehicles/VEH-001_SUV_v001.blend
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import setup_logger  # noqa: E402

UNREAL_PREFIXES = (
    "BP_", "WBP_", "SM_", "SK_", "SKEL_", "PHYS_", "M_", "MI_", "MF_", "T_", "RT_", "ABP_", "A_", "AM_",
    "BS_", "IK_", "RTG_", "NS_", "NE_", "SFX_", "MUS_", "AMB_", "SC_", "MS_", "SCL_", "ATT_", "DA_", "DT_",
    "CF_", "CV_", "E_", "F_", "IA_", "IMC_", "ST_", "BT_", "BB_", "LS_", "FNT_", "UCX_",
)
MAP_RE = re.compile(r"^L\d{2}_[A-Z][A-Za-z0-9]*(_[A-Z][A-Za-z0-9]*)*$")
BLEND_RE = re.compile(r"^(CHR|SKN|ENM|VEH|WPN|PRP|ENV|ANM|MAT|VFX)-\d{3}_[A-Za-z0-9]+(_[A-Za-z0-9]+)*_v\d{3}$")
BODY_RE = re.compile(r"^[A-Za-z0-9_]+$")
TEXTURE_SUFFIX_RE = re.compile(r"_(BC|N|ORM|E|M|R|AO|H|D)(_\d{2})?$")
EXPORT_EXTS = {".fbx", ".glb", ".obj", ".abc"}
AUDIO_EXTS = {".wav", ".ogg", ".flac"}
IMAGE_EXTS = {".png", ".tga", ".exr", ".tif", ".tiff", ".jpg"}
IGNORED_NAMES = {".gitkeep", "README.md", "CLAUDE.md"}
IGNORED_DIRS = {"Developer", "Developers", "__pycache__", "raw", "licenses", "manifest"}


def check_name(path: Path) -> list[str]:
    """Função pura: lista de problemas no nome do arquivo (vazia = ok)."""
    name, ext = path.stem, path.suffix.lower()
    problems: list[str] = []
    if not BODY_RE.match(name) and ext != ".blend":
        problems.append("use apenas letras, números e _ (sem espaços/acentos/hífen)")
    if ext == ".umap":
        if not MAP_RE.match(name):
            problems.append("mapa deve seguir L<NN>_<Nome> (ex.: L01_Zombies)")
    elif ext == ".uasset":
        if not name.startswith(UNREAL_PREFIXES):
            problems.append("prefixo Unreal ausente/desconhecido (ver unreal-content.md)")
        elif name.startswith("T_") and not TEXTURE_SUFFIX_RE.search(name):
            problems.append("textura sem sufixo de tipo (_BC, _N, _ORM, _E, _M...)")
    elif ext == ".blend":
        if not BLEND_RE.match(name):
            problems.append("arquivo Blender deve ser <ID>_<Nome>_vNNN.blend (ex.: VEH-001_SUV_v001)")
    elif ext in EXPORT_EXTS:
        if not name.startswith(("SM_", "SK_", "A_", "UCX_")):
            problems.append("export 3D deve começar com SM_, SK_ ou A_")
    elif ext in AUDIO_EXTS:
        if not name.startswith(("SFX_", "MUS_", "AMB_")):
            problems.append("áudio deve começar com SFX_, MUS_ ou AMB_")
    elif ext in IMAGE_EXTS:
        if not name.startswith(("T_", "UI_")):
            problems.append("imagem de produção deve começar com T_ ou UI_")
        elif name.startswith("T_") and not TEXTURE_SUFFIX_RE.search(name):
            problems.append("textura sem sufixo de tipo (_BC, _N, _ORM, _E, _M...)")
    return problems


def iter_files(paths: list[Path]):
    for p in paths:
        if p.is_file():
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*")):
                if f.is_file() and f.name not in IGNORED_NAMES and not (set(f.relative_to(p).parts[:-1]) & IGNORED_DIRS):
                    yield f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="+", type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    log = setup_logger("validate_naming", args.verbose)
    checked = failures = 0
    for f in iter_files(args.paths):
        if f.suffix.lower() not in {".uasset", ".umap", ".blend", *EXPORT_EXTS, *AUDIO_EXTS, *IMAGE_EXTS}:
            continue
        checked += 1
        for problem in check_name(f):
            failures += 1
            log.error("%s: %s", f.as_posix(), problem)
    missing = [p for p in args.paths if not p.exists()]
    for p in missing:
        log.error("caminho inexistente: %s", p)
    log.info("%d arquivo(s) verificados, %d problema(s)", checked, failures)
    return 1 if failures or missing else 0


if __name__ == "__main__":
    sys.exit(main())
