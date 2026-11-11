import json

import check_licenses as cl
from conftest import FIXTURES


def base(**kw):
    a = {"id": "SFX-001", "license": "CC0-1.0", "creation_method": "library", "origin_url": "https://example.org/x",
         "status": "planned", "commercial_use_status": "allowed", "attribution": None,
         "generator_name": None, "generator_version": None}
    a.update(kw)
    return a


def test_cc0_ok():
    assert cl.audit_asset(base()).level == "ok"


def test_noncommercial_blocked():
    f = cl.audit_asset(base(license="CC BY-NC 4.0", attribution="Autor X"))
    assert f.level == "block" and any("NonCommercial" in r for r in f.reasons)


def test_nd_and_personal_use_blocked():
    assert cl.audit_asset(base(license="CC BY-ND 4.0", attribution="a")).level == "block"
    assert cl.audit_asset(base(license="Free for personal use")).level == "block"


def test_cc_by_requires_attribution():
    assert cl.audit_asset(base(license="CC BY 4.0")).level == "block"
    assert cl.audit_asset(base(license="CC BY 4.0", attribution="Som por Fulano (freesound)")).level == "ok"


def test_missing_license_and_origin_blocked():
    f = cl.audit_asset(base(license=None, origin_url=None))
    assert f.level == "block"
    assert any("licença ausente" in r for r in f.reasons) and any("origin_url" in r for r in f.reasons)


def test_unknown_license_blocked():
    assert cl.audit_asset(base(license="unknown")).level == "block"


def test_ai_requires_generator():
    assert cl.audit_asset(base(creation_method="ai_assisted", license="Apache-2.0")).level == "block"
    ok = cl.audit_asset(base(creation_method="ai_assisted", license="Apache-2.0", generator_name="X", generator_version="1"))
    assert ok.level == "ok"


def test_platform_terms_need_review():
    assert cl.audit_asset(base(license="Mixamo terms")).level == "review"


def test_production_with_unknown_commercial_status_blocked():
    assert cl.audit_asset(base(status="imported", commercial_use_status="unknown")).level == "block"


def test_ids_filter_reports_missing():
    data = json.loads((FIXTURES / "manifest_minimal.json").read_text(encoding="utf-8"))
    findings = cl.audit(data, ["PRP-001", "XXX-000"])
    assert {f.asset_id: f.level for f in findings} == {"XXX-000": "block", "PRP-001": "ok"}


def test_cli_report_and_credits(tmp_path):
    data = json.loads((FIXTURES / "manifest_minimal.json").read_text(encoding="utf-8"))
    data["assets"][0]["attribution"] = "Modelo por Fulano"
    data["assets"][0]["license"] = "CC BY 4.0"
    data["assets"][0]["creation_method"] = "library"
    data["assets"][0]["origin_url"] = "https://example.org"
    mf = tmp_path / "m.json"
    mf.write_text(json.dumps(data), encoding="utf-8")
    rep, cred = tmp_path / "r.md", tmp_path / "c.md"
    assert cl.main(["--manifest", str(mf), "--report", str(rep), "--credits", str(cred)]) == 0
    assert "OK: **1**" in rep.read_text(encoding="utf-8")
    assert "Modelo por Fulano" in cred.read_text(encoding="utf-8")
    data["assets"][0]["license"] = "CC BY-NC 4.0"
    mf.write_text(json.dumps(data), encoding="utf-8")
    assert cl.main(["--manifest", str(mf)]) == 1
