#!/usr/bin/env python3
"""PreToolUse hook (Write|Edit): impede escrita fora do repositório e em binários.

- Bloqueia (exit 2) escrita fora do diretório do projeto.
- Bloqueia escrita de binários Unreal/Blender por texto (.uasset, .umap, .blend...).
- Bloqueia arquivos de segredo (.env, .mcp.json).
- Avisa (exit 0 + stdout) ao tocar em áreas sensíveis (arte aprovada, LICENSE).
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

BINARY_EXTS = {".uasset", ".umap", ".blend", ".fbx", ".glb", ".wav", ".png", ".jpg", ".psd", ".exr"}
SECRET_NAMES = {".env", ".mcp.json", "settings.local.json"}
SENSITIVE_PREFIXES = ("design/art-bible/approved/", "assets/final/", "LICENSE", "ASSET_LICENSES.md")


def classify(file_path: str, project_dir: str) -> tuple[str, str]:
    """Retorna (decisão, motivo). decisão em {"allow", "warn", "block"}."""
    root = Path(project_dir).resolve()
    target = Path(file_path)
    if not target.is_absolute():
        target = root / target
    target = target.resolve()
    try:
        rel = target.relative_to(root).as_posix()
    except ValueError:
        return "block", f"escrita fora do repositório: {target}"
    if target.name in SECRET_NAMES or target.name.startswith(".env"):
        return "block", f"arquivo de segredo: {rel}"
    if target.suffix.lower() in BINARY_EXTS:
        return "block", f"binário não deve ser escrito por texto: {rel}"
    if rel.startswith(SENSITIVE_PREFIXES):
        return "warn", f"área sensível ({rel}): confirme que há aprovação humana"
    return "allow", ""


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return 0
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or os.getcwd()
    decision, reason = classify(file_path, project_dir)
    if decision == "block":
        print(f"Bloqueado pelo guard_paths: {reason}", file=sys.stderr)
        return 2
    if decision == "warn":
        print(f"Aviso guard_paths: {reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
