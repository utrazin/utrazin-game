"""Valida armature(s) de uma cena Blender.

Uso:
  blender -b arquivo.blend --python tools/blender/validate_rig.py -- \
      --required-bones tools/blender/ue5_required_bones.txt [--report reports/x.json]

Checa: armature chamada 'root', ossos obrigatórios, hierarquia (pai esperado),
nomes duplicados/com sufixo, leaf bones, malhas vinculadas sem Armature
modifier e vertex groups sem osso correspondente (possível problema de
deformação).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blender_cli import script_args  # noqa: E402

EXPECTED_PARENTS = {
    "pelvis": "root", "spine_01": "pelvis", "spine_02": "spine_01", "spine_03": "spine_02",
    "neck_01": "spine_03", "head": "neck_01",
    "clavicle_l": "spine_03", "upperarm_l": "clavicle_l", "lowerarm_l": "upperarm_l", "hand_l": "lowerarm_l",
    "clavicle_r": "spine_03", "upperarm_r": "clavicle_r", "lowerarm_r": "upperarm_r", "hand_r": "lowerarm_r",
    "thigh_l": "pelvis", "calf_l": "thigh_l", "foot_l": "calf_l", "ball_l": "foot_l",
    "thigh_r": "pelvis", "calf_r": "thigh_r", "foot_r": "calf_r", "ball_r": "foot_r",
}


def read_bone_list(path: Path) -> list[str]:
    return [ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip() and not ln.startswith("#")]


def validate_rig_snapshot(snapshot: dict, required: list[str]) -> list[dict]:
    """snapshot = {"armatures":[{name, bones:{bone: parent|None}}], "meshes":[{name, armature, has_modifier, vertex_groups:[...]}]}"""
    issues: list[dict] = []

    def add(level: str, obj: str, msg: str) -> None:
        issues.append({"level": level, "object": obj, "message": msg})

    arms = snapshot.get("armatures", [])
    if not arms:
        add("error", "-", "nenhuma armature na cena")
        return issues
    for arm in arms:
        name, bones = arm["name"], arm.get("bones", {})
        if name != "root":
            add("warning", name, "armature deveria se chamar 'root' (evita osso extra na Unreal)")
        for req in required:
            if req == "root" and name == "root" and "root" not in bones:
                continue  # o objeto armature 'root' cumpre o papel
            if req not in bones:
                add("error", name, f"osso obrigatório ausente: {req}")
        for bone, parent in bones.items():
            if bone.endswith("_end") or bone.endswith(".end"):
                add("error", name, f"leaf bone '{bone}' (desligue Add Leaf Bones)")
            if "." in bone:
                add("error", name, f"nome com sufixo/ponto: {bone}")
            expected = EXPECTED_PARENTS.get(bone)
            if expected and parent != expected and not (expected == "root" and parent is None and name == "root"):
                add("error", name, f"hierarquia: {bone} tem pai '{parent}', esperado '{expected}'")
    bone_names = {b for a in arms for b in a.get("bones", {})}
    for mesh in snapshot.get("meshes", []):
        if mesh.get("armature") and not mesh.get("has_modifier"):
            add("error", mesh["name"], "parent em armature sem Armature modifier")
        orphan = [g for g in mesh.get("vertex_groups", []) if g not in bone_names]
        if orphan:
            add("warning", mesh["name"], f"vertex groups sem osso (deformação suspeita): {', '.join(orphan[:8])}")
        if mesh.get("armature") and not mesh.get("vertex_groups"):
            add("error", mesh["name"], "malha skinned sem vertex groups")
    return issues


def snapshot_from_blender() -> dict:  # pragma: no cover - requer Blender
    import bpy  # type: ignore

    arms, meshes = [], []
    for obj in bpy.data.objects:
        if obj.type == "ARMATURE":
            arms.append({"name": obj.name,
                         "bones": {b.name: (b.parent.name if b.parent else None) for b in obj.data.bones}})
        elif obj.type == "MESH":
            arm_mod = next((m for m in obj.modifiers if m.type == "ARMATURE"), None)
            arm_parent = obj.parent.name if obj.parent and obj.parent.type == "ARMATURE" else None
            meshes.append({"name": obj.name, "armature": arm_parent or (arm_mod.object.name if arm_mod and arm_mod.object else None),
                           "has_modifier": arm_mod is not None, "vertex_groups": [g.name for g in obj.vertex_groups]})
    return {"file": bpy.data.filepath, "armatures": arms, "meshes": meshes}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="validate_rig.py", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--required-bones", type=Path, required=True)
    ap.add_argument("--report", type=Path)
    ap.add_argument("--snapshot", type=Path, help="(teste) snapshot JSON sem Blender")
    args = ap.parse_args(script_args(argv) if argv is None else argv)
    snapshot = json.loads(args.snapshot.read_text(encoding="utf-8")) if args.snapshot else snapshot_from_blender()
    issues = validate_rig_snapshot(snapshot, read_bone_list(args.required_bones))
    for i in issues:
        print(f"[{i['level'].upper()}] {i['object']}: {i['message']}")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps({"file": snapshot.get("file"), "issues": issues}, ensure_ascii=False, indent=2), encoding="utf-8")
    return 1 if any(i["level"] == "error" for i in issues) else 0


if __name__ == "__main__":
    sys.exit(main())
