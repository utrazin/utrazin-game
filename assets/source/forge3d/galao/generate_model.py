"""Model authoring recipe for galao."""
from __future__ import annotations

from pathlib import Path
import sys

for _root in Path(__file__).resolve().parents:
    if (_root / "Tools" / "__init__.py").is_file():
        sys.path.insert(0, str(_root))
        break

from lib.model_builder import ModelBuilder
from lib.geometry_types import Placement
from Tools.recipe_context import recipe_paths

ASSET_BUILD_GEOMETRY = "recipe"


def build_galao_model() -> ModelBuilder:
    builder = ModelBuilder("galao", modeling_mode="free", require_integer_dimensions=False)

    # 1. Define group hierarchy with functional pivots
    builder.add_group("root") \
           .add_transform_group("body", "root", pivot=(0, 0, 0))

    # Galao de gasolina 20 L: 34 x 47 x 17 cm. Escala do forge: 16 unidades = 1 m.
    U = 16.0
    A = ("assembly:galao",)
    builder.add_box("corpo", "body", size=(0.34*U, 0.40*U, 0.17*U), at=(0, 0.20*U, 0), native=False, tags=A)
    builder.add_box("ombro", "body", size=(0.30*U, 0.05*U, 0.15*U), at=(0, 0.425*U, 0), native=False, tags=A)
    for i, x in enumerate((-0.09, 0.0, 0.09)):
        builder.add_box(f"alca_{i}", "body", size=(0.025*U, 0.05*U, 0.04*U), at=(x*U, 0.47*U, 0), native=False, tags=A)
    builder.add_box("alca_barra", "body", size=(0.21*U, 0.02*U, 0.04*U), at=(0, 0.505*U, 0), native=False, tags=A)
    builder.add_cylinder("bico", "body", radius=0.022*U, height=0.06*U, segments=10, tags=A, no_overlap_check=True,
                         placement=Placement.at((0.12*U, 0.47*U, 0), space="world"))
    return builder


def main():
    model_path = recipe_paths(__file__).model
    builder = build_galao_model()
    builder.export_bbmodel(model_path)
    print(f"[model] Exported to {model_path}")


if __name__ == "__main__":
    main()
