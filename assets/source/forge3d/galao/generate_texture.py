"""Pixel-art texture authoring recipe for galao."""
from __future__ import annotations

from pathlib import Path
import sys

for _root in Path(__file__).resolve().parents:
    if (_root / "Tools" / "__init__.py").is_file():
        sys.path.insert(0, str(_root))
        break

from Tools.TexturePainter import TexturePainter
from Tools.recipe_context import recipe_paths


def paint():
    paths = recipe_paths(__file__)
    model_path, texture_path = paths.model, paths.texture

    painter = TexturePainter.from_bbmodel(model_path)

    # 1. Base solid coat
    painter.fill_all((150, 28, 22, 255))

    # 2. Geometric crease shadows
    creases = painter.creases(max_internal_angle=100)
    creases.paint(lambda hit: (20, 20, 30, 160), blend="multiply")

    # 3. Save and register texture (edge_dilation=1 fills 1px island padding)
    painter.save(texture_path, edge_dilation=1)
    print(f"[texture] Saved to {texture_path}")


if __name__ == "__main__":
    paint()
