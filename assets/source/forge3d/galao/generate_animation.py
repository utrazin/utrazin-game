"""Animation authoring recipe for galao."""
from __future__ import annotations

from pathlib import Path
import sys

for _root in Path(__file__).resolve().parents:
    if (_root / "Tools" / "__init__.py").is_file():
        sys.path.insert(0, str(_root))
        break

from lib.animation import AnimationEditor
from Tools.recipe_context import recipe_paths


def animate():
    model_path = recipe_paths(__file__).model

    editor = AnimationEditor.from_bbmodel(model_path)

    # 1. Idle loop
    idle = editor.animation("idle", duration=2.0, loop=True)
    if "body" in editor.group_names:
        idle.group("body").key(0.0, position=(0, 0, 0)) \
                          .key(1.0, position=(0, -0.2, 0), interpolation="catmullrom") \
                          .key(2.0, position=(0, 0, 0), interpolation="catmullrom")

    editor.save()
    print(f"[animation] Saved clips to {model_path}")


if __name__ == "__main__":
    animate()
