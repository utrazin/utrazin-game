import pytest

import ue_common as ue


def asset(**kw):
    a = {"id": "VEH-001", "category": "vehicle", "engine_path": "/Game/Vehicles/SUV", "export_file": "x.fbx",
         "status": "exported"}
    a.update(kw)
    return a


def test_destination():
    assert ue.import_destination(asset()) == "/Game/Vehicles/SUV/Meshes"
    assert ue.import_destination(asset(category="animation", engine_path="/Game/Animations/Hero")) == "/Game/Animations/Hero"
    with pytest.raises(ValueError):
        ue.import_destination(asset(engine_path="C:/Users/x"))


@pytest.mark.parametrize("kw,exists,hash_ok,approved_existing,expected", [
    ({}, True, True, False, "ok"),
    ({}, False, True, False, "inexistente"),
    ({}, True, False, False, "hash"),
    ({"status": "approved"}, True, True, False, "aprovado"),
    ({}, True, True, True, "aprovado"),
    ({"status": "modeling"}, True, True, False, "status"),
    ({"category": "audio"}, True, True, False, "categoria"),
    ({"export_file": None}, True, True, False, "export_file"),
])
def test_import_decision(kw, exists, hash_ok, approved_existing, expected):
    ok, reason = ue.import_decision(asset(**kw), approved_existing, exists, hash_ok)
    assert (expected == "ok") == ok
    assert expected in reason


@pytest.mark.parametrize("name,cls,problem", [
    ("SM_Rock", "StaticMesh", False), ("Rock", "StaticMesh", True), ("MI_Rock", "MaterialInstanceConstant", False),
    ("M_Rock_Inst", "MaterialInstanceConstant", True), ("L01_Zombies", "World", False), ("Map1", "World", True),
    ("Whatever", "UnknownClass", False), ("IMC_Vehicle", "InputMappingContext", False),
])
def test_check_asset_name(name, cls, problem):
    assert (ue.check_asset_name(name, cls) is not None) == problem


def test_level_problems():
    req = {"JRCheckpoint": 2, "JRRescueTarget": 1}
    assert ue.level_problems({"JRCheckpoint": 2, "JRRescueTarget": 1}, req) == []
    probs = ue.level_problems({"JRCheckpoint": 1}, req)
    assert len(probs) == 2 and "mínimo 2" in probs[0]
