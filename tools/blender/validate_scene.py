"""Valida uma cena Blender antes do export.

Uso (dentro do Blender):
  blender -b arquivo.blend --python tools/blender/validate_scene.py -- \
      --config tools/blender/validation_config.json [--category vehicle] [--report reports/x.json]

Checa: nomes/prefixos, duplicados, escala/transformações aplicadas, geometria
inválida (n-gons, faces degeneradas, sem polígonos), UVs ausentes, materiais
vazios e limite de triângulos. A lógica de validação é pura (opera sobre um
"snapshot" em dicionário) e é testada sem Blender em tests/python.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_cli import script_args  # noqa: E402

# ------------------------------------------------------------- lógica pura


def effective_config(config: dict, category: str | None) -> dict:
    cfg = {k: v for k, v in config.items() if k != "categories"}
    if category:
        cfg.update(config.get("categories", {}).get(category, {}))
    return cfg


def validate_snapshot(snapshot: dict, config: dict, category: str | None = None) -> list[dict]:
    """snapshot = {"objects": [{name, type, collection, scale, rotation, polygons:[n_sides...],
    degenerate_faces, uv_layers, materials:[nomes|None]}]}"""
    cfg = effective_config(config, category)
    issues: list[dict] = []

    def add(level: str, obj: str, msg: str) -> None:
        issues.append({"level": level, "object": obj, "message": msg})

    export_objs = [o for o in snapshot.get("objects", []) if o.get("collection") == cfg.get("export_collection", "EXPORT")]
    if not export_objs:
        add("error", "-", f"coleção {cfg.get('export_collection', 'EXPORT')} vazia ou ausente")
    names = [o["name"] for o in export_objs]
    for dup in sorted({n for n in names if names.count(n) > 1}):
        add("error", dup, "nome duplicado")
    for o in export_objs:
        base = o["name"].split(".")[0]
        if o["name"] != base:
            add("error", o["name"], "sufixo automático do Blender (.001); renomeie")
        if not o["name"].startswith(tuple(cfg.get("allowed_prefixes", []))):
            add("error", o["name"], f"prefixo inválido (permitidos: {', '.join(cfg.get('allowed_prefixes', []))})")
        tol = cfg.get("scale_tolerance", 1e-4)
        if any(abs(s - 1.0) > tol for s in o.get("scale", (1, 1, 1))):
            add("error", o["name"], f"escala não aplicada {tuple(o.get('scale'))}")
        if any(abs(r) > tol for r in o.get("rotation", (0, 0, 0))):
            add("warning", o["name"], "rotação não aplicada")
        if o.get("type") != "MESH":
            continue
        polys = o.get("polygons", [])
        if not polys:
            add("error", o["name"], "malha sem polígonos")
        max_sides = cfg.get("max_ngon_sides", 4)
        ngons = sum(1 for n in polys if n > max_sides)
        if ngons and not cfg.get("allow_ngons", False):
            add("error", o["name"], f"{ngons} n-gon(s) com mais de {max_sides} lados")
        if o.get("degenerate_faces", 0):
            add("error", o["name"], f"{o['degenerate_faces']} face(s) degenerada(s) (área ~0)")
        if o["name"].startswith("UCX_"):
            continue
        if cfg.get("require_uv", True) and not o.get("uv_layers"):
            add("error", o["name"], "sem UV")
        mats = o.get("materials", [])
        if cfg.get("require_material", True) and (not mats or any(m is None for m in mats)):
            add("error", o["name"], "slot de material vazio ou sem material")
    tris = sum(max(0, n - 2) for o in export_objs if o.get("type") == "MESH" and not o["name"].startswith("UCX_")
               for n in o.get("polygons", []))
    limit = cfg.get("max_triangles")
    if limit and tris > limit:
        add("error", "-", f"{tris} triângulos excedem o limite {limit}")
    snapshot_stats = {"triangles": tris}
    issues.append({"level": "info", "object": "-", "message": f"triângulos: {snapshot_stats['triangles']}"})
    return issues


def has_errors(issues: list[dict]) -> bool:
    return any(i["level"] == "error" for i in issues)


# ------------------------------------------------------------- Blender


def snapshot_from_blender() -> dict:  # pragma: no cover - requer Blender
    import bpy  # type: ignore

    objs = []
    for obj in bpy.data.objects:
        colls = [c.name for c in obj.users_collection]
        entry = {
            "name": obj.name, "type": obj.type, "collection": colls[0] if colls else None,
            "scale": tuple(round(v, 6) for v in obj.scale),
            "rotation": tuple(round(v, 6) for v in obj.rotation_euler),
        }
        if obj.type == "MESH":
            mesh = obj.data
            entry["polygons"] = [len(p.vertices) for p in mesh.polygons]
            entry["degenerate_faces"] = sum(1 for p in mesh.polygons if p.area < 1e-8)
            entry["uv_layers"] = [uv.name for uv in mesh.uv_layers]
            entry["materials"] = [s.material.name if s.material else None for s in obj.material_slots]
        objs.append(entry)
    return {"file": bpy.data.filepath, "objects": objs}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_scene.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--config", type=Path, required=True)
    ap.add_argument("--category")
    ap.add_argument("--report", type=Path)
    ap.add_argument("--snapshot", type=Path, help="(teste) valida um snapshot JSON sem Blender")
    args = ap.parse_args(script_args(argv) if argv is None else argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else snapshot_from_blender()
    issues = validate_snapshot(snapshot, config, args.category)
    for i in issues:
        print(f"[{i['level'].upper()}] {i['object']}: {i['message']}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"file": snapshot.get("file"), "issues": issues}, ensure_ascii=False, indent=2),
                               encoding="utf-8")
    return 1 if has_errors(issues) else 0


if __name__ == "__main__":
    sys.exit(main())
