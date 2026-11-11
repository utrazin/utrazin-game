#!/usr/bin/env python3
"""Verifica links locais quebrados em arquivos Markdown do repositório.

Links externos (http/https/mailto) e âncoras puras são ignorados.

Exemplo:
  python tools/pipeline/validate_references.py
  python tools/pipeline/validate_references.py docs README.md
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, setup_logger  # noqa: E402

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)|!\[[^\]]*\]\(([^)\s]+)\)")
CODE_FENCE_RE = re.compile(r"```.*?```", re.S)
INLINE_CODE_RE = re.compile(r"`[^`\n]*`")
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "Intermediate", "Saved", "Binaries", "DerivedDataCache"}


def extract_links(markdown: str) -> list[str]:
    text = CODE_FENCE_RE.sub("", markdown)
    text = INLINE_CODE_RE.sub("", text)
    return [a or b for a, b in LINK_RE.findall(text)]


def broken_links(md_file: Path) -> list[str]:
    """Função pura sobre o sistema de arquivos: retorna alvos inexistentes."""
    out = []
    for target in extract_links(md_file.read_text(encoding="utf-8")):
        if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I) or target.startswith("#"):
            continue
        path_part = unquote(target.split("#", 1)[0])
        if not path_part:
            continue
        resolved = (md_file.parent / path_part).resolve()
        if not resolved.exists():
            out.append(target)
    return out


def iter_markdown(paths: list[Path]):
    for p in paths:
        if p.is_file() and p.suffix.lower() == ".md":
            yield p
        elif p.is_dir():
            for f in sorted(p.rglob("*.md")):
                if not (set(f.parts) & SKIP_DIRS):
                    yield f


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("paths", nargs="*", type=Path, default=[REPO_ROOT])
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    log = setup_logger("validate_references", args.verbose)
    total = bad = 0
    for md in iter_markdown(args.paths):
        total += 1
        for target in broken_links(md):
            bad += 1
            log.error("%s: link quebrado -> %s", md.as_posix(), target)
    log.info("%d arquivo(s) .md verificados, %d link(s) quebrado(s)", total, bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
