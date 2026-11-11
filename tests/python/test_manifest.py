import copy
import json
from datetime import datetime, timezone

import pytest

import manifest as m
from conftest import FIXTURES, ROOT


@pytest.fixture
def data():
    return json.loads((FIXTURES / "manifest_minimal.json").read_text(encoding="utf-8"))


@pytest.fixture
def schema():
    return json.loads((ROOT / "assets/manifest/manifest.schema.json").read_text(encoding="utf-8"))


def test_repo_manifest_is_valid(schema):
    data = json.loads((ROOT / "assets/manifest/assets.json").read_text(encoding="utf-8"))
    assert m.schema_errors(data, schema) == []
    assert m.semantic_errors(data, ROOT) == []


def test_fixture_is_valid(data, schema):
    assert m.schema_errors(data, schema) == []


def test_schema_rejects_bad_status_and_id(data, schema):
    data["assets"][0]["status"] = "done"
    data["assets"][0]["id"] = "barrel"
    errors = m.schema_errors(data, schema)
    assert any("status" in e for e in errors)
    assert any("id" in e for e in errors)


def test_schema_rejects_approved_without_reviewer(data, schema):
    data["assets"][0]["status"] = "approved"
    assert any("reviewer" in e for e in m.schema_errors(data, schema))


def test_semantic_duplicate_and_prefix(data):
    dup = copy.deepcopy(data["assets"][0])
    data["assets"].append(dup)
    data["assets"][0]["category"] = "weapon"
    errors = m.semantic_errors(data, ROOT, check_files=False)
    assert any("duplicado" in e for e in errors)
    assert any("prefixo PRP" in e for e in errors)


def test_semantic_missing_file(data):
    data["assets"][0]["source_file"] = "blender/scenes/props/nao_existe.blend"
    assert any("inexistente" in e for e in m.semantic_errors(data, ROOT))


def test_add_asset_rejects_duplicate_and_wrong_category(data):
    with pytest.raises(m.ManifestError):
        m.add_asset(data, "PRP-001", "prop", "x")
    with pytest.raises(m.ManifestError):
        m.add_asset(data, "PRP-002", "weapon", "x")
    asset = m.add_asset(data, "PRP-002", "prop", "Caixa")
    assert asset["status"] == "planned" and asset["art_bible_version"] == "0.1"


def test_set_status_transitions(data):
    with pytest.raises(m.ManifestError, match="approve"):
        m.set_status(data, "PRP-001", "approved")
    with pytest.raises(m.ManifestError, match="não permitida"):
        m.set_status(data, "PRP-001", "concept")
    with pytest.raises(m.ManifestError, match="export_file"):
        m.set_status(data, "PRP-001", "exported")


def test_set_export_hash_and_approve_flow(data, tmp_path):
    fbx = tmp_path / "SM_Barrel.fbx"
    fbx.write_bytes(b"fbx-bytes")
    asset = m.set_export(data, "PRP-001", "SM_Barrel.fbx", root=tmp_path)
    assert asset["status"] == "exported"
    assert asset["hash"].startswith("sha256:") and len(asset["hash"]) == 71
    m.set_status(data, "PRP-001", "imported")
    with pytest.raises(m.ManifestError, match="in_review"):
        m.approve(data, "PRP-001", "utrazin")
    m.set_status(data, "PRP-001", "in_review")
    with pytest.raises(m.ManifestError, match="reviewer"):
        m.approve(data, "PRP-001", "  ")
    now = datetime(2026, 11, 11, 12, 0, tzinfo=timezone.utc)
    asset = m.approve(data, "PRP-001", "utrazin", now=now)
    assert asset["status"] == "approved" and asset["approved_at"] == "2026-11-11T12:00:00+00:00"
    with pytest.raises(m.ManifestError, match="aprovado"):
        m.set_export(data, "PRP-001", "SM_Barrel.fbx", root=tmp_path)
    fbx.write_bytes(b"changed")
    assert any("hash diverge" in e for e in m.semantic_errors(data, tmp_path))


def test_placeholder_cannot_be_approved(data):
    a = data["assets"][0]
    a.update(status="in_review", creation_method="placeholder")
    with pytest.raises(m.ManifestError, match="placeholder"):
        m.approve(data, "PRP-001", "x")


def test_cli_validate_and_add(tmp_path):
    target = tmp_path / "assets.json"
    target.write_text((FIXTURES / "manifest_minimal.json").read_text(encoding="utf-8"), encoding="utf-8")
    assert m.main(["--manifest", str(target), "validate"]) == 0
    assert m.main(["--manifest", str(target), "add", "PRP-002", "--category", "prop", "--name", "Caixa"]) == 0
    saved = json.loads(target.read_text(encoding="utf-8"))
    assert [a["id"] for a in saved["assets"]] == ["PRP-001", "PRP-002"]
    before = target.read_text(encoding="utf-8")
    assert m.main(["--manifest", str(target), "add", "PRP-002", "--category", "prop", "--name", "X"]) == 1
    assert target.read_text(encoding="utf-8") == before
