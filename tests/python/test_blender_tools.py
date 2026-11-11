import json
from pathlib import Path

import pytest

import export_assets as ea
import validate_rig as vrig
import validate_scene as vs
from conftest import FIXTURES, ROOT

CONFIG = json.loads((ROOT / "tools/blender/validation_config.json").read_text(encoding="utf-8"))
REQUIRED = vrig.read_bone_list(ROOT / "tools/blender/ue5_required_bones.txt")


def load(name):
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def errors(issues):
    return [i["message"] for i in issues if i["level"] == "error"]


def test_valid_scene_passes():
    issues = vs.validate_snapshot(load("scene_valid.json"), CONFIG, "prop")
    assert errors(issues) == []
    assert any("triângulos: 14" in i["message"] for i in issues)  # 6 quads*2 + 2 tris, UCX excluído


def test_invalid_scene_reports_each_problem():
    msgs = " | ".join(errors(vs.validate_snapshot(load("scene_invalid.json"), CONFIG)))
    for fragment in ("sufixo automático", "prefixo inválido", "escala não aplicada", "n-gon",
                     "degenerada", "sem UV", "material vazio", "sem polígonos"):
        assert fragment in msgs, fragment


def test_category_triangle_limit():
    snap = load("scene_valid.json")
    snap["objects"][0]["polygons"] = [4] * 3000  # 6000 tris
    assert any("excedem o limite 5000" in m for m in errors(vs.validate_snapshot(snap, CONFIG, "prop")))
    assert errors(vs.validate_snapshot(snap, CONFIG, "vehicle")) == []


def test_empty_export_collection():
    assert any("EXPORT" in m for m in errors(vs.validate_snapshot({"objects": []}, CONFIG)))


def test_scene_cli_with_snapshot(tmp_path):
    report = tmp_path / "r.json"
    args = ["--config", str(ROOT / "tools/blender/validation_config.json"), "--report", str(report)]
    assert vs.main(args + ["--snapshot", str(FIXTURES / "scene_valid.json"), "--category", "prop"]) == 0
    assert vs.main(args + ["--snapshot", str(FIXTURES / "scene_invalid.json")]) == 1
    assert json.loads(report.read_text(encoding="utf-8"))["issues"]


def test_valid_rig_passes():
    assert errors(vrig.validate_rig_snapshot(load("rig_valid.json"), REQUIRED)) == []


def test_rig_problems():
    snap = load("rig_valid.json")
    bones = snap["armatures"][0]["bones"]
    del bones["hand_r"]
    bones["calf_l"] = "pelvis"
    bones["head_end"] = "head"
    snap["armatures"][0]["name"] = "Armature"
    snap["meshes"][0]["has_modifier"] = False
    snap["meshes"][0]["vertex_groups"].append("Bone.003")
    issues = vrig.validate_rig_snapshot(snap, REQUIRED)
    msgs = " | ".join(i["message"] for i in issues)
    for fragment in ("hand_r", "calf_l tem pai 'pelvis'", "leaf bone", "Armature modifier", "deveria se chamar 'root'",
                     "vertex groups sem osso", "osso obrigatório ausente: root"):
        assert fragment in msgs, fragment


def test_no_armature():
    assert errors(vrig.validate_rig_snapshot({"armatures": []}, REQUIRED))


def test_load_preset_and_animation_overrides():
    preset = ROOT / "blender/export-presets/fbx_unreal.json"
    static = ea.load_preset(preset)
    anim = ea.load_preset(preset, animation=True)
    assert static["add_leaf_bones"] is False and static["bake_anim"] is False
    assert anim["bake_anim"] is True and anim["axis_forward"] == "-Y"


def test_plan_exports():
    plan = ea.plan_exports(["SM_A", "SM_B"], Path("out"), "PRP-001", "object")
    assert [p["file"] for p in plan] == ["out/SM_A.fbx", "out/SM_B.fbx"]
    grouped = ea.plan_exports(["SM_A", "SM_B"], Path("out"), "PRP-001", "collection")
    assert grouped == [{"file": "out/PRP-001.fbx", "objects": ["SM_A", "SM_B"]}]
    for bad in ([], ["SM_A", "SM_A"], ["Cube"]):
        with pytest.raises(ValueError):
            ea.plan_exports(bad, Path("out"), "PRP-001", "object")
