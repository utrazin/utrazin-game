#!/usr/bin/env python3
"""Gera docs/pipeline/AGENT_CATALOG.md e SKILL_CATALOG.md a partir dos frontmatters."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from validate_pipeline import ROOT, parse_frontmatter  # noqa: E402


def short(text: str, n: int = 170) -> str:
    text = " ".join(text.split()).replace("|", "/")
    return text if len(text) <= n else text[: n - 3].rstrip() + "..."


def origins(root: Path) -> dict[str, str]:
    p = root / "docs/pipeline/vendored_skills.json"
    out: dict[str, str] = {}
    if p.is_file():
        for src, info in json.loads(p.read_text(encoding="utf-8")).get("sources", {}).items():
            for s in info.get("skills", []):
                out[s] = f"{src} ({info.get('license', '?')})"
    return out


def build(root: Path = ROOT) -> dict[str, str]:
    org = origins(root)
    sk = ["# Catálogo de skills", "", "Gerado por `python tools/pipeline/gen_catalog.py`. Não edite à mão.", "",
          "| Skill | Origem | Quando usar |", "|---|---|---|"]
    for p in sorted((root / ".claude/skills").glob("*/SKILL.md")):
        fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        sk.append(f"| `{fm.get('name', p.parent.name)}` | {org.get(p.parent.name, 'este projeto')} | {short(fm.get('description', ''))} |")
    ag = ["# Catálogo de agentes", "", "Gerado por `python tools/pipeline/gen_catalog.py`. Não edite à mão.", "",
          "| Agente | Ferramentas | Escopo |", "|---|---|---|"]
    for p in sorted((root / ".claude/agents").glob("*.md")):
        fm, _ = parse_frontmatter(p.read_text(encoding="utf-8"))
        ag.append(f"| `{fm.get('name', p.stem)}` | {fm.get('tools', '')} | {short(fm.get('description', ''))} |")
    return {"docs/pipeline/SKILL_CATALOG.md": "\n".join(sk) + "\n", "docs/pipeline/AGENT_CATALOG.md": "\n".join(ag) + "\n"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--check", action="store_true", help="falha se os catálogos estiverem desatualizados")
    args = ap.parse_args(argv)
    stale = False
    for rel, content in build(args.root).items():
        target = args.root / rel
        if args.check:
            if not target.is_file() or target.read_text(encoding="utf-8") != content:
                print(f"DESATUALIZADO: {rel}")
                stale = True
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(content, encoding="utf-8")
            print("gerado", rel)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())
