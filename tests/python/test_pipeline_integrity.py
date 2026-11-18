"""Integridade da pipeline de agentes e skills (inspirado em studio-tests do Claude Code Game Studios)."""
import textwrap

import pytest

import gen_catalog
import validate_pipeline as vp
from conftest import ROOT

NEW_AGENTS = ["studio-producer", "level-designer", "technical-artist", "cinematics-director", "sound-designer"]
NEW_SKILLS = ["gamedev-router", "team-orchestrate", "visual-qa-gate", "enterable-interior", "map-composition",
              "camera-shots-and-cutscenes", "intro-sequence", "character-pose-validation",
              "material-lighting-audit", "music-production-acestep", "facial-animation-lipsync",
              "validate-pipeline"]


def test_real_repo_has_no_pipeline_errors():
    rep = vp.check(ROOT)
    assert rep.errors == [], "\n".join(rep.errors)


@pytest.mark.parametrize("name", NEW_AGENTS)
def test_new_agent_exists(name):
    assert (ROOT / ".claude/agents" / f"{name}.md").is_file()


@pytest.mark.parametrize("name", NEW_SKILLS)
def test_new_skill_exists(name):
    assert (ROOT / ".claude/skills" / name / "SKILL.md").is_file()


def test_catalogs_are_current():
    for rel, content in gen_catalog.build(ROOT).items():
        assert (ROOT / rel).read_text(encoding="utf-8") == content, f"{rel} desatualizado: rode gen_catalog.py"


def test_optional_tools_are_not_mcp_enabled_by_default():
    assert not (ROOT / ".mcp.json").exists() or (ROOT / ".gitignore").read_text(encoding="utf-8").count(".mcp.json")


def _tree(tmp_path, skill_name="alpha", folder="alpha", body=None, extra_agent=None):
    sk = tmp_path / ".claude/skills" / folder
    sk.mkdir(parents=True)
    body = body or textwrap.dedent("""\
        # x
        ## Pré-requisitos
        a
        ## Passos
        b
        ## Verificações
        c
        ## Erros comuns
        d
        ## Critério de sucesso
        e
        """)
    (sk / "SKILL.md").write_text(f"---\nname: {skill_name}\ndescription: Faz alpha.\n---\n{body}", encoding="utf-8")
    (tmp_path / ".claude/agents").mkdir(parents=True)
    (tmp_path / ".claude/skills/gamedev-router/references").mkdir(parents=True)
    (tmp_path / ".claude/skills/gamedev-router/references/routing-table.md").write_text("`alpha`\n", encoding="utf-8")
    return tmp_path


def test_validator_flags_name_mismatch(tmp_path):
    rep = vp.check(_tree(tmp_path, skill_name="beta", folder="alpha"))
    assert any("difere da pasta" in e for e in rep.errors)


def test_validator_flags_missing_sections(tmp_path):
    rep = vp.check(_tree(tmp_path, body="# so titulo\n"))
    assert any("Passos" in e for e in rep.errors)


def test_validator_flags_skill_missing_from_router(tmp_path):
    root = _tree(tmp_path)
    (root / ".claude/skills/gamedev-router/references/routing-table.md").write_text("nada\n", encoding="utf-8")
    assert any("não está na tabela do roteador" in e for e in vp.check(root).errors)


def test_validator_flags_em_dash(tmp_path):
    root = _tree(tmp_path)
    (root / ".claude/rules").mkdir(parents=True)
    (root / ".claude/rules/x.md").write_text("texto " + chr(0x2014) + " texto", encoding="utf-8")
    assert any("travessão" in e for e in vp.check(root).errors)


def test_validator_accepts_good_tree(tmp_path):
    root = _tree(tmp_path)
    (root / ".claude/skills/gamedev-router/SKILL.md").write_text(
        "---\nname: gamedev-router\ndescription: roteia.\n---\n# r\n## Pré-requisitos\n## Passos\n## Verificações\n## Erros comuns\n## Critério de sucesso\n",
        encoding="utf-8")
    (root / ".claude/skills/gamedev-router/references/routing-table.md").write_text("`alpha` `gamedev-router`\n", encoding="utf-8")
    assert vp.check(root).errors == []
