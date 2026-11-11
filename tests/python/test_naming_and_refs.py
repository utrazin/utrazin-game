from pathlib import Path

import pytest

import validate_naming as vn
import validate_references as vr


@pytest.mark.parametrize("name", [
    "BP_Vehicle_SUV.uasset", "T_SUV_Body_BC.uasset", "T_SUV_Body_N.png", "L01_Zombies.umap",
    "L01_Zombies_Drive.umap", "VEH-001_SUV_v001.blend", "SM_Barrel.fbx", "SFX_Vehicle_TireBurst_01.wav",
    "IMC_OnFoot.uasset", "DA_Level_L01_Zombies.uasset",
])
def test_valid_names(name):
    assert vn.check_name(Path(name)) == []


@pytest.mark.parametrize("name,fragment", [
    ("Vehicle SUV.uasset", "letras"),
    ("SUV.uasset", "prefixo"),
    ("T_SUV_Body.uasset", "sufixo"),
    ("Level1.umap", "L<NN>"),
    ("suv_final.blend", "<ID>"),
    ("VEH-001_SUV.blend", "<ID>"),
    ("Barrel.fbx", "SM_"),
    ("explosion.wav", "SFX_"),
    ("texture.png", "T_"),
])
def test_invalid_names(name, fragment):
    problems = vn.check_name(Path(name))
    assert problems and any(fragment in p for p in problems)


def test_naming_cli(tmp_path):
    (tmp_path / "ok").mkdir()
    (tmp_path / "ok" / "SM_Rock.fbx").write_bytes(b"x")
    (tmp_path / "ok" / "notes.txt").write_text("ignorado")
    assert vn.main([str(tmp_path / "ok")]) == 0
    (tmp_path / "ok" / "rock.fbx").write_bytes(b"x")
    assert vn.main([str(tmp_path / "ok")]) == 1
    assert vn.main([str(tmp_path / "nao_existe")]) == 1


def test_extract_links_ignores_code():
    md = "Veja [a](docs/a.md) e `[b](b.md)`\n```\n[c](c.md)\n```\n![img](i.png) [ext](https://x.org) [ancora](#sec)"
    assert vr.extract_links(md) == ["docs/a.md", "i.png", "https://x.org", "#sec"]


def test_broken_links(tmp_path):
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "a.md").write_text("ok")
    md = tmp_path / "README.md"
    md.write_text("[a](docs/a.md#topo) [b](docs/b.md) [web](https://example.org) [espaco](docs/a%20b.md)", encoding="utf-8")
    assert vr.broken_links(md) == ["docs/b.md", "docs/a%20b.md"]
    assert vr.main([str(tmp_path)]) == 1
    md.write_text("[a](docs/a.md)", encoding="utf-8")
    assert vr.main([str(tmp_path)]) == 0
