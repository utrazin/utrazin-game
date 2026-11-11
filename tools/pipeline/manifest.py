#!/usr/bin/env python3
"""Leitura, validação e atualização controlada do manifesto de assets.

Exemplos:
  python tools/pipeline/manifest.py validate
  python tools/pipeline/manifest.py list --status planned
  python tools/pipeline/manifest.py add PRP-001 --category prop --name "Barril" --description "..."
  python tools/pipeline/manifest.py set-status PRP-001 concept
  python tools/pipeline/manifest.py set-export PRP-001 assets/final/meshes/SM_Barrel.fbx
  python tools/pipeline/manifest.py approve PRP-001 --reviewer "utrazin"
"""
from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from common import REPO_ROOT, load_json, resolve_repo_path, setup_logger, sha256_file, write_json  # noqa: E402

DEFAULT_MANIFEST = REPO_ROOT / "assets" / "manifest" / "assets.json"
DEFAULT_SCHEMA = REPO_ROOT / "assets" / "manifest" / "manifest.schema.json"

STATUSES = ["planned", "concept", "approved_concept", "modeling", "rigging", "animation",
            "exported", "imported", "in_review", "approved", "rejected", "deprecated"]

# Transições permitidas por set-status. "approved" só via comando approve.
TRANSITIONS: dict[str, set[str]] = {
    "planned": {"concept", "modeling", "deprecated"},
    "concept": {"approved_concept", "rejected", "deprecated"},
    "approved_concept": {"modeling", "deprecated"},
    "modeling": {"rigging", "animation", "exported", "deprecated"},
    "rigging": {"animation", "exported", "modeling", "deprecated"},
    "animation": {"exported", "rigging", "deprecated"},
    "exported": {"imported", "modeling", "deprecated"},
    "imported": {"in_review", "exported", "deprecated"},
    "in_review": {"rejected", "imported", "deprecated"},
    "approved": {"deprecated", "in_review"},
    "rejected": {"concept", "modeling", "deprecated"},
    "deprecated": set(),
}
STATUS_NEEDS_EXPORT = {"exported", "imported", "in_review", "approved"}

PREFIX_CATEGORY = {
    "CHR": "character", "SKN": "skin", "ENM": "enemy", "VEH": "vehicle", "WPN": "weapon",
    "PRP": "prop", "ENV": "environment", "ANM": "animation", "SFX": "audio", "MUS": "music",
    "UI": "ui", "FNT": "font", "MAT": "material", "VFX": "vfx",
}

EMPTY_ASSET = {
    "id": None, "category": None, "name": None, "description": "", "source_file": None,
    "export_file": None, "engine_path": None, "author": None, "origin_url": None,
    "creation_method": "original", "generator_name": None, "generator_version": None,
    "license": None, "commercial_use_status": "unknown", "attribution": None, "hash": None,
    "art_bible_version": None, "status": "planned", "reviewer": None, "approved_at": None,
    "poly_budget": None, "texture_budget": None, "rig": None, "lods": None, "notes": "",
}


class ManifestError(Exception):
    """Erro de uso ou de consistência do manifesto."""


# ---------------------------------------------------------------- funções puras

def schema_errors(data: dict, schema: dict) -> list[str]:
    """Erros de JSON Schema (requer jsonschema)."""
    try:
        import jsonschema  # type: ignore
    except ImportError as exc:  # pragma: no cover - depende do ambiente
        raise ManifestError("pacote 'jsonschema' ausente: pip install -r tools/requirements.txt") from exc
    validator = jsonschema.Draft202012Validator(schema)
    out = []
    for err in sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path)):
        loc = "/".join(str(p) for p in err.absolute_path) or "<raiz>"
        out.append(f"schema: {loc}: {err.message}")
    return out


def semantic_errors(data: dict, root: Path = REPO_ROOT, check_files: bool = True) -> list[str]:
    """Regras que o JSON Schema não expressa bem."""
    errors: list[str] = []
    seen: set[str] = set()
    for i, asset in enumerate(data.get("assets", [])):
        aid = asset.get("id", f"#{i}")
        if aid in seen:
            errors.append(f"{aid}: id duplicado")
        seen.add(aid)
        prefix = str(aid).split("-")[0]
        expected = PREFIX_CATEGORY.get(prefix)
        if expected and asset.get("category") != expected:
            errors.append(f"{aid}: categoria '{asset.get('category')}' não combina com prefixo {prefix} (esperado '{expected}')")
        status = asset.get("status")
        if status in STATUS_NEEDS_EXPORT and not asset.get("export_file"):
            errors.append(f"{aid}: status '{status}' exige export_file")
        if status in STATUS_NEEDS_EXPORT and not asset.get("hash"):
            errors.append(f"{aid}: status '{status}' exige hash")
        if status == "approved" and asset.get("commercial_use_status") != "allowed":
            errors.append(f"{aid}: aprovado sem commercial_use_status=allowed")
        if check_files:
            for field in ("source_file", "export_file"):
                value = asset.get(field)
                if value and not resolve_repo_path(value, root).exists():
                    errors.append(f"{aid}: {field} inexistente: {value}")
            export = asset.get("export_file")
            if export and asset.get("hash"):
                path = resolve_repo_path(export, root)
                if path.exists() and sha256_file(path) != asset["hash"]:
                    errors.append(f"{aid}: hash diverge do arquivo {export}")
    return errors


def find_asset(data: dict, asset_id: str) -> dict:
    for asset in data.get("assets", []):
        if asset.get("id") == asset_id:
            return asset
    raise ManifestError(f"asset {asset_id} não encontrado")


def add_asset(data: dict, asset_id: str, category: str, name: str, description: str = "") -> dict:
    if any(a.get("id") == asset_id for a in data.get("assets", [])):
        raise ManifestError(f"asset {asset_id} já existe")
    prefix = asset_id.split("-")[0]
    if PREFIX_CATEGORY.get(prefix) != category:
        raise ManifestError(f"categoria '{category}' incompatível com prefixo {prefix}")
    asset = dict(EMPTY_ASSET, id=asset_id, category=category, name=name, description=description,
                 art_bible_version=data.get("art_bible_version"))
    data.setdefault("assets", []).append(asset)
    return asset


def set_status(data: dict, asset_id: str, new_status: str) -> dict:
    if new_status not in STATUSES:
        raise ManifestError(f"status inválido: {new_status}")
    if new_status == "approved":
        raise ManifestError("use o comando 'approve' (exige revisor humano)")
    asset = find_asset(data, asset_id)
    current = asset["status"]
    if new_status not in TRANSITIONS.get(current, set()):
        raise ManifestError(f"transição {current} -> {new_status} não permitida")
    if new_status in STATUS_NEEDS_EXPORT and not (asset.get("export_file") and asset.get("hash")):
        raise ManifestError(f"{new_status} exige export_file e hash (use set-export)")
    asset["status"] = new_status
    if current == "approved":
        asset["reviewer"] = None
        asset["approved_at"] = None
    return asset


def set_export(data: dict, asset_id: str, export_file: str, root: Path = REPO_ROOT) -> dict:
    asset = find_asset(data, asset_id)
    if asset["status"] == "approved":
        raise ManifestError(f"{asset_id} está aprovado; crie nova versão (set-status in_review antes)")
    path = resolve_repo_path(export_file, root)
    if not path.is_file():
        raise ManifestError(f"arquivo de export inexistente: {export_file}")
    asset["export_file"] = export_file.replace("\\", "/")
    asset["hash"] = sha256_file(path)
    if asset["status"] in {"modeling", "rigging", "animation", "approved_concept"}:
        asset["status"] = "exported"
    return asset


def approve(data: dict, asset_id: str, reviewer: str, now: datetime | None = None) -> dict:
    asset = find_asset(data, asset_id)
    if not reviewer.strip():
        raise ManifestError("reviewer obrigatório")
    if asset["status"] != "in_review":
        raise ManifestError(f"só assets em in_review podem ser aprovados (atual: {asset['status']})")
    if asset.get("creation_method") == "placeholder":
        raise ManifestError("placeholder não pode ser aprovado")
    if asset.get("commercial_use_status") != "allowed":
        raise ManifestError("licença não liberada (commercial_use_status != allowed)")
    asset["status"] = "approved"
    asset["reviewer"] = reviewer.strip()
    asset["approved_at"] = (now or datetime.now(timezone.utc)).replace(microsecond=0).isoformat()
    return asset


# ---------------------------------------------------------------- CLI

def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Gerencia assets/manifest/assets.json", epilog=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    p.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA)
    p.add_argument("--root", type=Path, default=REPO_ROOT, help="raiz para caminhos relativos")
    p.add_argument("-v", "--verbose", action="store_true")
    sub = p.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="valida schema + regras semânticas")
    v.add_argument("--no-files", action="store_true", help="não verifica existência/hash de arquivos")
    ls = sub.add_parser("list", help="lista assets")
    ls.add_argument("--status", choices=STATUSES)
    a = sub.add_parser("add", help="adiciona asset em 'planned'")
    a.add_argument("id"); a.add_argument("--category", required=True); a.add_argument("--name", required=True)
    a.add_argument("--description", default="")
    s = sub.add_parser("set-status", help="muda status respeitando transições")
    s.add_argument("id"); s.add_argument("status", choices=STATUSES)
    e = sub.add_parser("set-export", help="registra arquivo exportado e hash")
    e.add_argument("id"); e.add_argument("export_file")
    ap = sub.add_parser("approve", help="aprovação HUMANA de um asset em in_review")
    ap.add_argument("id"); ap.add_argument("--reviewer", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    log = setup_logger("manifest", args.verbose)
    try:
        data = load_json(args.manifest)
        if args.cmd == "validate":
            errors = schema_errors(data, load_json(args.schema)) + semantic_errors(data, args.root, not args.no_files)
            for err in errors:
                log.error(err)
            if errors:
                log.error("%d erro(s) no manifesto", len(errors))
                return 1
            log.info("manifesto válido (%d assets)", len(data.get("assets", [])))
            return 0
        if args.cmd == "list":
            for a in data.get("assets", []):
                if args.status is None or a["status"] == args.status:
                    print(f"{a['id']:8} {a['status']:16} {a['name']}")
            return 0
        if args.cmd == "add":
            add_asset(data, args.id, args.category, args.name, args.description)
        elif args.cmd == "set-status":
            set_status(data, args.id, args.status)
        elif args.cmd == "set-export":
            set_export(data, args.id, args.export_file, args.root)
        elif args.cmd == "approve":
            approve(data, args.id, args.reviewer)
        errors = schema_errors(data, load_json(args.schema))
        if errors:
            for err in errors:
                log.error(err)
            log.error("alteração não salva: manifesto ficaria inválido")
            return 1
        write_json(args.manifest, data)
        log.info("%s %s: ok", args.cmd, args.id)
        return 0
    except (ManifestError, FileNotFoundError) as exc:
        log.error(str(exc))
        return 1


if __name__ == "__main__":
    sys.exit(main())
