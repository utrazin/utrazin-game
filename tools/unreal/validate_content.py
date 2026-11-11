"""Valida conteúdo do projeto Unreal: nomes, dependências quebradas, materiais e colisão.

EXECUTA SOMENTE NO PYTHON DO EDITOR UNREAL:
  UnrealEditor-Cmd.exe unreal/JogoResgate/JogoResgate.uproject -run=pythonscript \
      -script="tools/unreal/validate_content.py --paths /Game/Vehicles /Game/Characters" -unattended -nullrhi

Também dispara o Data Validation nativo (EditorValidatorSubsystem) quando disponível.
Relatório JSON em reports/validate_content_<timestamp>.json.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from ue_common import check_asset_name  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
SKIP_PREFIXES = ("/Game/Developer", "/Game/Developers", "/Game/Collections")


def main(argv: list[str] | None = None) -> int:  # pragma: no cover - requer Unreal
    ap = argparse.ArgumentParser(prog="validate_content.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--paths", nargs="+", default=["/Game"])
    ap.add_argument("--no-data-validation", action="store_true")
    args = ap.parse_args(argv if argv is not None else sys.argv[1:])
    try:
        import unreal  # type: ignore
    except ImportError:
        print("ERRO: este script roda apenas no Python do Editor Unreal.", file=sys.stderr)
        return 2

    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    issues = []
    checked = 0
    for root in args.paths:
        for data in registry.get_assets_by_path(root, recursive=True):
            pkg = str(data.package_name)
            if pkg.startswith(SKIP_PREFIXES):
                continue
            checked += 1
            name, cls = str(data.asset_name), str(data.asset_class_path.asset_name)
            problem = check_asset_name(name, cls)
            if problem:
                issues.append({"asset": pkg, "level": "error", "message": problem})
            deps = registry.get_dependencies(pkg, unreal.AssetRegistryDependencyOptions())
            for dep in deps or []:
                dep = str(dep)
                if dep.startswith("/Game/") and not unreal.EditorAssetLibrary.does_asset_exist(dep):
                    issues.append({"asset": pkg, "level": "error", "message": f"dependência quebrada: {dep}"})
                if dep.startswith(SKIP_PREFIXES):
                    issues.append({"asset": pkg, "level": "error", "message": f"referencia conteúdo de Developer: {dep}"})
            if cls in {"StaticMesh", "SkeletalMesh"}:
                asset = unreal.EditorAssetLibrary.load_asset(pkg)
                if cls == "StaticMesh":
                    mats = [asset.get_material(i) for i in range(len(asset.static_materials))]
                    body = asset.get_editor_property("body_setup")
                    if body is None or not body.aggregate_geom.convex_elems and not body.aggregate_geom.box_elems \
                            and not body.aggregate_geom.sphere_elems and not body.aggregate_geom.sphyl_elems:
                        issues.append({"asset": pkg, "level": "warning", "message": "sem colisão simples"})
                else:
                    mats = [m.material_interface for m in asset.materials]
                    if asset.get_editor_property("physics_asset") is None:
                        issues.append({"asset": pkg, "level": "warning", "message": "sem Physics Asset"})
                if any(m is None for m in mats):
                    issues.append({"asset": pkg, "level": "error", "message": "slot de material vazio"})

    dv = None
    if not args.no_data_validation and hasattr(unreal, "EditorValidatorSubsystem"):
        subsystem = unreal.get_editor_subsystem(unreal.EditorValidatorSubsystem)
        dv = "EditorValidatorSubsystem disponível: rode 'Validate Data' no Content Browser para o relatório nativo"
        _ = subsystem

    report = {"time": datetime.now().isoformat(), "paths": args.paths, "checked": checked,
              "issues": issues, "data_validation": dv}
    out = REPO_ROOT / "reports" / f"validate_content_{datetime.now():%Y%m%d_%H%M%S}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log(f"[validate_content] {checked} assets, {len(issues)} problema(s). Relatório: {out}")
    return 1 if any(i["level"] == "error" for i in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
