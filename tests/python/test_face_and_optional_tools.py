import json

import check_optional_ai_tools as co
import validate_face_blendshapes as vf


def test_arkit_has_52_unique_names():
    assert len(vf.ARKIT_52) == 52 and len(set(vf.ARKIT_52)) == 52
    assert set(vf.MIN_SPEECH) <= set(vf.ARKIT_52)


def test_levels():
    assert vf.evaluate(vf.ARKIT_52)["level"] == "full"
    assert vf.evaluate(vf.MIN_SPEECH)["level"] == "speech"
    r = vf.evaluate(["jawOpen", "Basis"])
    assert r["level"] == "insufficient" and "mouthClose" in r["missing_for_speech"]


def test_case_mismatch_is_reported():
    names = [n.lower() if n == "jawOpen" else n for n in vf.MIN_SPEECH]
    assert vf.evaluate(names)["case_mismatch"] == {"jawOpen": "jawopen"}


def test_cli_names_file(tmp_path, capsys):
    f = tmp_path / "n.txt"
    f.write_text("\n".join(vf.MIN_SPEECH), encoding="utf-8")
    assert vf.main(["--names", str(f)]) == 0
    assert json.loads(capsys.readouterr().out)["level"] == "speech"


def test_acestep_tiers():
    assert "sem GPU" in co.acestep_tier(None)
    assert co.acestep_tier(4000).startswith("ate 6 GB")
    assert co.acestep_tier(8192).startswith("8-16 GB")
    assert co.acestep_tier(24576).startswith("24 GB+")


def test_collect_is_read_only_and_reports_optional(tmp_path):
    info = co.collect(tmp_path, None)
    assert info["acestep_servidor_ativo"] is None and "opcional" in info["observacao"]
