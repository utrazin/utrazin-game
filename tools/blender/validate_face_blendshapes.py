#!/usr/bin/env python3
"""Valida shape keys faciais (nomes ARKit) para lip sync. Funções puras testáveis sem Blender.

Fora do Blender:  python tools/blender/validate_face_blendshapes.py --names nomes.txt
Dentro do Blender: blender -b arq.blend --python tools/blender/validate_face_blendshapes.py -- --object Head
"""
from __future__ import annotations

import argparse
import json
import sys

ARKIT_52 = [
    "browDownLeft", "browDownRight", "browInnerUp", "browOuterUpLeft", "browOuterUpRight", "cheekPuff",
    "cheekSquintLeft", "cheekSquintRight", "eyeBlinkLeft", "eyeBlinkRight", "eyeLookDownLeft",
    "eyeLookDownRight", "eyeLookInLeft", "eyeLookInRight", "eyeLookOutLeft", "eyeLookOutRight",
    "eyeLookUpLeft", "eyeLookUpRight", "eyeSquintLeft", "eyeSquintRight", "eyeWideLeft", "eyeWideRight",
    "jawForward", "jawLeft", "jawOpen", "jawRight", "mouthClose", "mouthDimpleLeft", "mouthDimpleRight",
    "mouthFrownLeft", "mouthFrownRight", "mouthFunnel", "mouthLeft", "mouthLowerDownLeft",
    "mouthLowerDownRight", "mouthPressLeft", "mouthPressRight", "mouthPucker", "mouthRight",
    "mouthRollLower", "mouthRollUpper", "mouthShrugLower", "mouthShrugUpper", "mouthSmileLeft",
    "mouthSmileRight", "mouthStretchLeft", "mouthStretchRight", "mouthUpperUpLeft", "mouthUpperUpRight",
    "noseSneerLeft", "noseSneerRight", "tongueOut",
]
MIN_SPEECH = [
    "jawOpen", "mouthClose", "mouthFunnel", "mouthPucker", "mouthSmileLeft", "mouthSmileRight",
    "mouthStretchLeft", "mouthStretchRight", "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthUpperUpLeft", "mouthUpperUpRight", "eyeBlinkLeft", "eyeBlinkRight", "browInnerUp",
]


def evaluate(names: list[str]) -> dict:
    have = set(names)
    missing_min = [n for n in MIN_SPEECH if n not in have]
    missing_full = [n for n in ARKIT_52 if n not in have]
    lower = {n.lower(): n for n in names}
    near = {m: lower[m.lower()] for m in missing_min if m.lower() in lower}
    level = "full" if not missing_full else "speech" if not missing_min else "insufficient"
    return {"level": level, "missing_for_speech": missing_min, "missing_for_full": missing_full,
            "case_mismatch": near, "count": len(names)}


def _blender_names(object_name: str) -> list[str]:
    import bpy  # type: ignore
    obj = bpy.data.objects[object_name]
    keys = obj.data.shape_keys
    return [k.name for k in keys.key_blocks] if keys else []


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[sys.argv.index("--") + 1:] if argv is None and "--" in sys.argv else argv
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--names", help="arquivo texto com um nome de shape key por linha")
    ap.add_argument("--object", help="objeto de malha no Blender")
    args = ap.parse_args(argv)
    if args.names:
        with open(args.names, encoding="utf-8") as fh:
            names = [ln.strip() for ln in fh if ln.strip()]
    elif args.object:
        names = _blender_names(args.object)
    else:
        ap.error("informe --names ou --object")
    result = evaluate(names)
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return 0 if result["level"] != "insufficient" else 1


if __name__ == "__main__":
    sys.exit(main())
