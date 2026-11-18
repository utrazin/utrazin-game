#!/usr/bin/env python3
"""Valida a estrutura da pipeline de agentes e skills (somente biblioteca padrão).

Erros bloqueiam (código 1). Avisos informam. Verifica: frontmatter, nomes únicos, seções
obrigatórias, cobertura da tabela do roteador, links locais, travessões (preferência do projeto)
e donos de arquivos duplicados entre agentes.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
VALID_TOOLS = {"Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "Bash", "WebFetch", "WebSearch",
               "NotebookEdit", "Task", "TodoWrite"}
OWN_SKILL_SECTIONS = ("Pré-requisitos", "Passos", "Verificações", "Erros comuns", "Critério de sucesso")
AGENT_SECTIONS = ("Responsabilidades", "Proibições", "Exige aprovação humana", "Formato de retorno")
MAX_DESC, MAX_LINES = 1024, 500
EM_DASH = chr(0x2014)
MD_LINK = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
CODE_REL = re.compile(r"`((?:\.\./)?(?:blender-references|references|scripts)/[^`\s*<>{}]+)`")
BACKTICK_NAME = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)+)`")
ROUTER_TABLE = "gamedev-router/references/routing-table.md"


def parse_frontmatter(text: str) -> tuple[dict, str]:
    m = re.match(r"^---\r?\n(.*?)\r?\n---\r?\n?", text, re.S)
    if not m:
        return {}, text
    fm: dict[str, str] = {}
    key = None
    for line in m.group(1).splitlines():
        top = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
        if top and not line.startswith((" ", "\t")):
            key = top.group(1)
            val = top.group(2).strip()
            fm[key] = "" if val in (">", "|", ">-", "|-") else val.strip("\"'")
        elif key and line.startswith((" ", "\t")) and key in ("description",):
            fm[key] = (fm[key] + " " + line.strip()).strip()
    return fm, text[m.end():]


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, msg: str) -> None:
        self.errors.append(msg)

    def warn(self, msg: str) -> None:
        self.warnings.append(msg)


def load_vendored(root: Path) -> set[str]:
    p = root / "docs/pipeline/vendored_skills.json"
    if not p.is_file():
        return set()
    data = json.loads(p.read_text(encoding="utf-8"))
    return {s for src in data.get("sources", {}).values() for s in src.get("skills", [])}


def check(root: Path = ROOT) -> Report:
    rep = Report()
    skills_dir, agents_dir = root / ".claude/skills", root / ".claude/agents"
    vendored = load_vendored(root)
    skills: dict[str, Path] = {}
    agents: dict[str, Path] = {}

    for path in sorted(skills_dir.glob("*/SKILL.md")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        rel = path.relative_to(root).as_posix()
        name = fm.get("name", "")
        if not fm:
            rep.err(f"{rel}: sem frontmatter"); continue
        if name != path.parent.name:
            rep.err(f"{rel}: name '{name}' difere da pasta '{path.parent.name}'")
        if not NAME_RE.match(name):
            rep.err(f"{rel}: nome inválido '{name}'")
        if name in skills:
            rep.err(f"{rel}: nome duplicado '{name}'")
        skills[name] = path
        desc = fm.get("description", "")
        if not desc:
            rep.err(f"{rel}: description vazia")
        elif len(desc) > MAX_DESC:
            rep.err(f"{rel}: description com {len(desc)} caracteres (máx {MAX_DESC})")
        if len(text.splitlines()) > MAX_LINES:
            rep.err(f"{rel}: {len(text.splitlines())} linhas (máx {MAX_LINES}); mova detalhes para references/")
        if name not in vendored:
            for sec in OWN_SKILL_SECTIONS:
                if sec not in body:
                    rep.err(f"{rel}: falta a seção '{sec}'")
        for link in MD_LINK.findall(text):
            if link.startswith(("http", "#", "mailto:")):
                continue
            if not (path.parent / link.split("#")[0]).exists():
                rep.warn(f"{rel}: link local quebrado: {link}")
        for ref in CODE_REL.findall(text):
            if not (path.parent / ref).exists():
                rep.warn(f"{rel}: referência inexistente: {ref}")

    for path in sorted(agents_dir.glob("*.md")):
        text = path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text)
        rel = path.relative_to(root).as_posix()
        name = fm.get("name", "")
        if name != path.stem:
            rep.err(f"{rel}: name '{name}' difere do arquivo")
        if name in agents:
            rep.err(f"{rel}: agente duplicado '{name}'")
        agents[name] = path
        if len(fm.get("description", "")) < 40:
            rep.err(f"{rel}: description curta demais")
        tools = {t.strip() for t in fm.get("tools", "").split(",") if t.strip()}
        if not tools or not tools <= VALID_TOOLS:
            rep.err(f"{rel}: ferramentas inválidas {sorted(tools - VALID_TOOLS)}")
        for sec in AGENT_SECTIONS:
            if sec not in body:
                rep.err(f"{rel}: falta a seção '{sec}'")

    clash = sorted(set(skills) & set(agents))
    for n in clash:
        rep.err(f"nome usado por skill e agente: {n}")

    table = skills_dir / ROUTER_TABLE
    if not table.is_file():
        rep.err(f"tabela do roteador ausente: .claude/skills/{ROUTER_TABLE}")
    else:
        ttext = table.read_text(encoding="utf-8")
        listed = set(BACKTICK_NAME.findall(ttext)) | set(re.findall(r"`([a-z0-9]+)`", ttext))
        for n in sorted(set(skills) | set(agents)):
            if n not in listed:
                rep.err(f"'{n}' não está na tabela do roteador")
        known = set(skills) | set(agents)
        for n in sorted(set(BACKTICK_NAME.findall(ttext)) - known):
            rep.warn(f"tabela do roteador cita '{n}', que não existe como skill ou agente")

    owners: dict[str, str] = {}
    for name, path in agents.items():
        m = re.search(r"## Arquivos e diretórios sob sua responsabilidade\n(.*?)\n\n", path.read_text(encoding="utf-8"), re.S)
        for line in (m.group(1).splitlines() if m else []):
            if "(leitura" in line:
                continue
            p = line.lstrip("- ").split(" (")[0].strip()
            if p.endswith("/") and p in owners and owners[p] != name:
                rep.warn(f"diretório '{p}' é de '{owners[p]}' e de '{name}'")
            elif p.endswith("/"):
                owners[p] = name

    for base in (root / ".claude", root / "docs/pipeline"):
        for path in base.rglob("*"):
            if path.is_file() and path.suffix in (".md", ".json", ".py") and "__pycache__" not in path.parts:
                if EM_DASH in path.read_text(encoding="utf-8", errors="ignore"):
                    rep.err(f"{path.relative_to(root).as_posix()}: contém travessão (proibido neste projeto)")

    settings = root / ".claude/settings.json"
    if settings.is_file():
        try:
            json.loads(settings.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            rep.err(f".claude/settings.json inválido: {exc}")
    return rep


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--root", type=Path, default=ROOT)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)
    rep = check(args.root)
    if args.json:
        print(json.dumps({"errors": rep.errors, "warnings": rep.warnings}, ensure_ascii=False, indent=1))
    else:
        for w in rep.warnings:
            print("AVISO:", w)
        for e in rep.errors:
            print("ERRO:", e)
        print(f"{len(rep.errors)} erros, {len(rep.warnings)} avisos")
    return 1 if rep.errors else 0


if __name__ == "__main__":
    sys.exit(main())
