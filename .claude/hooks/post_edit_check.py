#!/usr/bin/env python3
"""PostToolUse hook (Write|Edit): validação leve do arquivo alterado.

- .py  -> compila (sintaxe)
- .json -> parse
- assets/manifest/assets.json -> validação de schema (se jsonschema disponível)
Em falha, sai com código 2 para o Claude ver o erro e corrigir.
"""
from __future__ import annotations

import json
import os
import py_compile
import subprocess
import sys
from pathlib import Path


def check_file(path: Path) -> str | None:
    if not path.exists():
        return None
    suffix = path.suffix.lower()
    if suffix == ".py":
        try:
            py_compile.compile(str(path), doraise=True)
        except py_compile.PyCompileError as exc:
            return f"erro de sintaxe Python: {exc.msg}"
    elif suffix == ".json":
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            return f"JSON inválido: {exc}"
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    file_path = (payload.get("tool_input") or {}).get("file_path", "")
    if not file_path:
        return 0
    path = Path(file_path)
    error = check_file(path)
    if error:
        print(f"post_edit_check: {path}: {error}", file=sys.stderr)
        return 2
    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR") or os.getcwd())
    manifest = project_dir / "assets" / "manifest" / "assets.json"
    if path.resolve() == manifest.resolve():
        result = subprocess.run(
            [sys.executable, str(project_dir / "tools" / "pipeline" / "manifest.py"), "validate"],
            capture_output=True, text=True, cwd=project_dir,
        )
        if result.returncode != 0:
            print(f"post_edit_check: manifesto inválido:\n{result.stdout}{result.stderr}", file=sys.stderr)
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
