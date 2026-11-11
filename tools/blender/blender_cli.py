"""Helpers para scripts rodando via `blender -b --python script.py -- args`."""
from __future__ import annotations

import sys


def script_args(argv: list[str] | None = None) -> list[str]:
    """Argumentos depois de '--' (Blender consome os anteriores)."""
    argv = sys.argv if argv is None else argv
    return argv[argv.index("--") + 1:] if "--" in argv else []


def in_blender() -> bool:
    try:
        import bpy  # type: ignore  # noqa: F401
    except ImportError:
        return False
    return True
