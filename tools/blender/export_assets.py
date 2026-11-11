"""Exporta objetos da coleção EXPORT de um .blend para FBX com preset do projeto.

Uso:
  blender -b arquivo.blend --python tools/blender/export_assets.py -- \
      --preset blender/export-presets/fbx_unreal.json --out assets/final/meshes \
      --asset-id VEH-001 [--group-by object|collection] [--animation] [--dry-run] [--report reports/x.json]

Comportamento:
  - Exporta cada objeto raiz da coleção EXPORT (com filhos, ex.: UCX_ e LODs) em um FBX
    `<NomeDoObjeto>.fbx`, ou a coleção inteira em `<asset-id>.fbx` com --group-by collection.
  - Valida a seleção (nome com prefixo, sem duplicados) antes de exportar.
  - Não sobrescreve arquivo existente sem --overwrite.
  - Registra log, erros e SHA-256 dos arquivos gerados no relatório JSON.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_cli import script_args  # noqa: E402

VALID_PREFIXES = ("SM_", "SK_", "A_")

# ------------------------------------------------------------- lógica pura


def load_preset(path: Path, animation: bool = False) -> dict:
    preset = json.loads(path.read_text(encoding="utf-8"))
    if preset.get("format") != "fbx":
        raise ValueError(f"formato não suportado: {preset.get('format')}")
    kwargs = dict(preset.get("operator_kwargs", {}))
    if animation:
        kwargs.update(preset.get("animation_overrides", {}))
    return kwargs


def plan_exports(roots: list[str], out_dir: Path, asset_id: str, group_by: str) -> list[dict]:
    """Decide o que vira cada arquivo. roots = nomes dos objetos raiz da coleção EXPORT."""
    if not roots:
        raise ValueError("coleção EXPORT sem objetos raiz")
    dups = sorted({r for r in roots if roots.count(r) > 1})
    if dups:
        raise ValueError(f"nomes duplicados: {dups}")
    bad = [r for r in roots if not r.startswith(VALID_PREFIXES)]
    if bad:
        raise ValueError(f"objetos raiz sem prefixo {VALID_PREFIXES}: {bad}")
    if group_by == "collection":
        return [{"file": (out_dir / f"{asset_id}.fbx").as_posix(), "objects": list(roots)}]
    return [{"file": (out_dir / f"{r}.fbx").as_posix(), "objects": [r]} for r in roots]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


# ------------------------------------------------------------- Blender


def export_root_names(collection: str) -> list[str]:  # pragma: no cover - requer Blender
    import bpy  # type: ignore

    coll = bpy.data.collections.get(collection)
    if coll is None:
        raise ValueError(f"coleção {collection} não existe")
    return [o.name for o in coll.all_objects if o.parent is None or o.parent.name not in coll.all_objects]


def run_export(plan: list[dict], kwargs: dict, overwrite: bool, dry_run: bool) -> list[dict]:  # pragma: no cover
    import bpy  # type: ignore

    results = []
    for item in plan:
        target = Path(item["file"])
        if target.exists() and not overwrite:
            results.append({**item, "ok": False, "error": "arquivo existe (use --overwrite ou nova versão)"})
            continue
        if dry_run:
            results.append({**item, "ok": True, "dry_run": True})
            continue
        bpy.ops.object.select_all(action="DESELECT")
        for name in item["objects"]:
            root = bpy.data.objects[name]
            root.select_set(True)
            for child in root.children_recursive:
                child.select_set(True)
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            bpy.ops.export_scene.fbx(filepath=str(target), **kwargs)
            results.append({**item, "ok": True, "hash": sha256(target)})
        except Exception as exc:  # noqa: BLE001 - relatar qualquer falha do operador
            results.append({**item, "ok": False, "error": str(exc)})
    return results


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - requer Blender
    ap = argparse.ArgumentParser(prog="export_assets.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--preset", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--asset-id", required=True)
    ap.add_argument("--collection", default="EXPORT")
    ap.add_argument("--group-by", choices=["object", "collection"], default="object")
    ap.add_argument("--animation", action="store_true")
    ap.add_argument("--overwrite", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--report", type=Path)
    args = ap.parse_args(script_args(argv) if argv is None else argv)
    import bpy  # type: ignore

    report = {"asset_id": args.asset_id, "source": bpy.data.filepath, "blender": bpy.app.version_string,
              "preset": args.preset.as_posix(), "time": datetime.now(timezone.utc).isoformat(), "results": [], "errors": []}
    code = 0
    try:
        kwargs = load_preset(args.preset, args.animation)
        plan = plan_exports(export_root_names(args.collection), args.out, args.asset_id, args.group_by)
        report["results"] = run_export(plan, kwargs, args.overwrite, args.dry_run)
        code = 0 if all(r["ok"] for r in report["results"]) else 1
    except (ValueError, KeyError) as exc:
        report["errors"].append(str(exc))
        code = 1
    for r in report["results"]:
        print(("[OK] " if r["ok"] else "[ERRO] ") + r["file"] + (f" {r.get('error')}" if not r["ok"] else ""))
    for e in report["errors"]:
        print(f"[ERRO] {e}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return code


if __name__ == "__main__":
    sys.exit(main())
