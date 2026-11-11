"""Importa assets exportados (FBX) para o projeto Unreal a partir do manifesto.

EXECUTA SOMENTE NO PYTHON DO EDITOR UNREAL:
  UnrealEditor-Cmd.exe unreal/JogoResgate/JogoResgate.uproject -run=pythonscript \
      -script="tools/unreal/import_assets.py --manifest assets/manifest/assets.json --ids VEH-001" -unattended

Regras:
  - Verifica arquivo de origem e hash do manifesto.
  - Nunca substitui asset com status 'approved' (aborta o item).
  - Opções de import por categoria (static, skeletal, animation).
  - Relatório JSON em reports/import_<timestamp>.json.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ue_common import CATEGORY_IMPORT, import_decision, import_destination  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return "sha256:" + h.hexdigest()


def build_task(unreal, source: Path, destination: str, kind: str, skeleton_path: str | None):  # pragma: no cover
    options = unreal.FbxImportUI()
    options.set_editor_property("import_materials", True)
    options.set_editor_property("import_textures", True)
    if kind == "static":
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", False)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_STATIC_MESH)
        options.static_mesh_import_data.set_editor_property("combine_meshes", False)
        options.static_mesh_import_data.set_editor_property("auto_generate_collision", False)
    elif kind == "skeletal":
        options.set_editor_property("import_mesh", True)
        options.set_editor_property("import_as_skeletal", True)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_SKELETAL_MESH)
        if skeleton_path:
            options.set_editor_property("skeleton", unreal.load_asset(skeleton_path))
    elif kind == "animation":
        options.set_editor_property("import_mesh", False)
        options.set_editor_property("import_animations", True)
        options.set_editor_property("mesh_type_to_import", unreal.FBXImportType.FBXIT_ANIMATION)
        if not skeleton_path:
            raise ValueError("animação exige --skeleton")
        options.set_editor_property("skeleton", unreal.load_asset(skeleton_path))
    task = unreal.AssetImportTask()
    task.set_editor_property("filename", str(source))
    task.set_editor_property("destination_path", destination)
    task.set_editor_property("automated", True)
    task.set_editor_property("replace_existing", True)  # protegido por import_decision
    task.set_editor_property("save", True)
    task.set_editor_property("options", options)
    return task


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="import_assets.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--manifest", type=Path, default=REPO_ROOT / "assets/manifest/assets.json")
    ap.add_argument("--ids", nargs="+", required=True)
    ap.add_argument("--skeleton", help="/Game/... do Skeleton para skeletal/animação")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    try:
        import unreal  # type: ignore
    except ImportError:
        print("ERRO: este script roda apenas no Python do Editor Unreal.", file=sys.stderr)
        return 2

    manifest_path = args.manifest if args.manifest.is_absolute() else REPO_ROOT / args.manifest
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    by_id = {a["id"]: a for a in data["assets"]}
    report = {"time": datetime.now().isoformat(), "results": []}
    tasks = []
    for aid in args.ids:
        asset = by_id.get(aid)
        if asset is None:
            report["results"].append({"id": aid, "ok": False, "reason": "id não encontrado"})
            continue
        src = REPO_ROOT / asset["export_file"] if asset.get("export_file") else None
        exists = bool(src and src.is_file())
        hash_ok = exists and sha256(src) == asset.get("hash")
        try:
            dest = import_destination(asset)
        except ValueError as exc:
            report["results"].append({"id": aid, "ok": False, "reason": str(exc)})
            continue
        existing_approved = False  # o manifesto é a fonte do status de aprovação
        ok, reason = import_decision(asset, existing_approved, exists, hash_ok)
        if not ok:
            unreal.log_warning(f"[import_assets] {aid}: {reason}")
            report["results"].append({"id": aid, "ok": False, "reason": reason})
            continue
        if args.dry_run:
            report["results"].append({"id": aid, "ok": True, "dry_run": True, "destination": dest})
            continue
        kind = CATEGORY_IMPORT[asset["category"]]["kind"]
        tasks.append((aid, dest, build_task(unreal, src, dest, kind, args.skeleton)))

    if tasks:
        unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([t for _, _, t in tasks])
        for aid, dest, task in tasks:
            imported = list(task.get_editor_property("imported_object_paths") or [])
            report["results"].append({"id": aid, "ok": bool(imported), "destination": dest, "imported": imported,
                                      "reason": "ok" if imported else "import não gerou assets (ver Output Log)"})

    out = REPO_ROOT / "reports" / f"import_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log(f"[import_assets] relatório: {out}")
    return 0 if all(r["ok"] for r in report["results"]) else 1


if __name__ == "__main__":
    sys.exit(main())
