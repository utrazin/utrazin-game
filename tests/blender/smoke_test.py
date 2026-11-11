"""Smoke test de integração (requer Blender 5.2):
  blender -b --factory-startup --python tests/blender/smoke_test.py

Cria uma cena mínima válida, roda validate_scene e exporta um FBX para pasta temporária.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools" / "blender"))

import bpy  # type: ignore  # noqa: E402

import export_assets  # noqa: E402
import validate_rig  # noqa: E402
import validate_scene  # noqa: E402
import json  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)
coll = bpy.data.collections.new("EXPORT")
bpy.context.scene.collection.children.link(coll)
bpy.ops.mesh.primitive_cube_add(size=1.0)
cube = bpy.context.active_object
cube.name = "SM_SmokeCube"
for c in cube.users_collection:
    c.objects.unlink(cube)
coll.objects.link(cube)
mat = bpy.data.materials.new("M_Smoke")
cube.data.materials.append(mat)

config = json.loads((ROOT / "tools/blender/validation_config.json").read_text(encoding="utf-8"))
issues = validate_scene.validate_snapshot(validate_scene.snapshot_from_blender(), config, "prop")
errors = [i for i in issues if i["level"] == "error"]
assert not errors, errors

with tempfile.TemporaryDirectory() as tmp:
    kwargs = export_assets.load_preset(ROOT / "blender/export-presets/fbx_unreal.json")
    plan = export_assets.plan_exports(export_assets.export_root_names("EXPORT"), Path(tmp), "PRP-999", "object")
    results = export_assets.run_export(plan, kwargs, overwrite=False, dry_run=False)
    assert all(r["ok"] for r in results), results
    assert Path(results[0]["file"]).stat().st_size > 0
# Rig: cria armature 'root' com a hierarquia UE5 obrigatória e valida via snapshot real do Blender.
arm_data = bpy.data.armatures.new("root")
arm = bpy.data.objects.new("root", arm_data)
bpy.context.scene.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
created = {}
for bone, parent in validate_rig.EXPECTED_PARENTS.items():
    eb = arm_data.edit_bones.new(bone)
    eb.head = (0.0, 0.0, len(created) * 0.05)
    eb.tail = (0.0, 0.02, len(created) * 0.05 + 0.04)
    created[bone] = eb
for bone, parent in validate_rig.EXPECTED_PARENTS.items():
    if parent != "root":
        created[bone].parent = created[parent]
bpy.ops.object.mode_set(mode="OBJECT")
required = validate_rig.read_bone_list(ROOT / "tools/blender/ue5_required_bones.txt")
rig_issues = validate_rig.validate_rig_snapshot(validate_rig.snapshot_from_blender(), required)
rig_errors = [i for i in rig_issues if i["level"] == "error"]
assert not rig_errors, rig_errors
# Caso negativo: remove um osso obrigatório e confirma que o validador acusa.
bpy.ops.object.mode_set(mode="EDIT")
arm_data.edit_bones.remove(arm_data.edit_bones["hand_r"])
bpy.ops.object.mode_set(mode="OBJECT")
bad = validate_rig.validate_rig_snapshot(validate_rig.snapshot_from_blender(), required)
assert any("hand_r" in i["message"] for i in bad), bad
print("SMOKE OK")
