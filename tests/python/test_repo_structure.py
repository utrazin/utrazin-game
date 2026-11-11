"""Garante que a fundação do repositório (M0) continua íntegra."""
import json
import re

import pytest

from conftest import ROOT

VALID_TOOLS = {"Read", "Write", "Edit", "MultiEdit", "Glob", "Grep", "Bash", "WebFetch", "WebSearch",
               "NotebookEdit", "Task", "TodoWrite"}
AGENTS = ["technical-architect", "art-director", "blender-specialist", "animation-specialist", "vehicle-engineer",
          "gameplay-engineer", "enemy-ai-engineer", "world-builder", "ui-audio-engineer", "performance-engineer",
          "qa-engineer", "asset-license-auditor"]
SKILLS = ["create-asset", "generate-concept", "export-blender", "import-unreal", "validate-asset", "review-art-style",
          "add-level", "add-character", "add-skin", "add-enemy", "test-gameplay", "profile-performance",
          "audit-licenses", "prepare-release"]
REQUIRED_FILES = [
    "README.md", "CLAUDE.md", "CONTRIBUTING.md", "LICENSE", "ASSET_LICENSES.md", ".gitignore", ".gitattributes",
    ".editorconfig", ".mcp.json.example", "GDD_jogo_resgate.md", ".claude/settings.json",
    ".github/PULL_REQUEST_TEMPLATE.md", ".github/workflows/validate.yml", "design/art-bible/ART_BIBLE.md",
    "design/audio-bible/AUDIO_BIBLE.md", "assets/manifest/assets.json", "assets/manifest/manifest.schema.json",
    "docs/decisions/ASSUMPTIONS.md", "docs/decisions/OPEN_DECISIONS.md", "docs/roadmap/ROADMAP.md",
    "docs/roadmap/DEFINITION_OF_DONE.md", "unreal/JogoResgate/JogoResgate.uproject",
    *[f"{d}/CLAUDE.md" for d in ("design", "assets", "blender", "unreal", "audio", "tools", "tests", "docs")],
    *[f".claude/rules/{r}.md" for r in ("cpp", "unreal-content", "blender-assets", "licenses", "safety")],
    *[f"tools/{p}" for p in ("blender/export_assets.py", "blender/validate_scene.py", "blender/validate_rig.py",
                             "unreal/import_assets.py", "unreal/validate_content.py", "unreal/validate_level.py",
                             "pipeline/manifest.py", "pipeline/check_licenses.py", "pipeline/validate_naming.py",
                             "pipeline/validate_references.py", "setup/check_environment.py", "setup/setup_windows.ps1")],
]


def frontmatter(path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    assert m, f"{path} sem frontmatter"
    return dict(line.split(": ", 1) for line in m.group(1).splitlines() if ": " in line), text


@pytest.mark.parametrize("rel", REQUIRED_FILES)
def test_required_file_exists(rel):
    assert (ROOT / rel).is_file(), rel


@pytest.mark.parametrize("name", AGENTS)
def test_agent_frontmatter(name):
    fm, body = frontmatter(ROOT / ".claude/agents" / f"{name}.md")
    assert fm["name"] == name
    assert len(fm["description"]) > 40
    tools = {t.strip() for t in fm["tools"].split(",")}
    assert tools <= VALID_TOOLS, tools - VALID_TOOLS
    for section in ("Responsabilidades", "Proibições", "Exige aprovação humana", "Formato de retorno"):
        assert section in body


@pytest.mark.parametrize("name", SKILLS)
def test_skill_frontmatter(name):
    fm, body = frontmatter(ROOT / ".claude/skills" / name / "SKILL.md")
    assert fm["name"] == name and len(fm["description"]) > 30
    for section in ("Pré-requisitos", "Passos", "Verificações", "Erros comuns", "Critério de sucesso"):
        assert section in body


def test_settings_hooks_point_to_existing_scripts():
    settings = json.loads((ROOT / ".claude/settings.json").read_text(encoding="utf-8"))
    for event in ("PreToolUse", "PostToolUse"):
        for group in settings["hooks"][event]:
            for hook in group["hooks"]:
                assert hook["type"] == "command"
                script = re.search(r"\.claude/hooks/(\w+\.py)", hook["command"]).group(1)
                assert (ROOT / ".claude/hooks" / script).is_file()
    assert any("rm -rf" in d for d in settings["permissions"]["deny"])


def test_gitattributes_lfs_patterns():
    text = (ROOT / ".gitattributes").read_text(encoding="utf-8")
    for ext in ("uasset", "umap", "blend", "fbx", "glb", "wav"):
        assert re.search(rf"^\*\.{ext}\s+filter=lfs", text, re.M), ext
    for ext in ("py", "md", "json", "cpp", "h"):
        assert not re.search(rf"^\*\.{ext}\s+filter=lfs", text, re.M), ext


def test_gitignore_unreal_dirs():
    text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for d in ("Binaries/", "Intermediate/", "DerivedDataCache/", "Saved/", ".env", ".mcp.json"):
        assert d in text


def test_uproject_is_valid_json_with_module_and_plugins():
    data = json.loads((ROOT / "unreal/JogoResgate/JogoResgate.uproject").read_text(encoding="utf-8"))
    assert data["EngineAssociation"] == "5.8"
    assert data["Modules"][0]["Name"] == "JogoResgate"
    plugins = {p["Name"] for p in data["Plugins"] if p.get("Enabled")}
    assert {"ChaosVehiclesPlugin", "EnhancedInput", "StateTree", "GameplayStateTree", "PythonScriptPlugin"} <= plugins


def test_cpp_headers_and_sources_pair_and_use_prefix():
    src = ROOT / "unreal/JogoResgate/Source/JogoResgate"
    headers = {p.stem for p in src.rglob("*.h")}
    sources = {p.stem for p in src.rglob("*.cpp")}
    # todo .cpp de classe tem header (exceto testes e módulo)
    orphans = {s for s in sources - headers if not s.endswith("Tests")}
    assert not orphans, orphans
    for h in src.rglob("*.h"):
        text = h.read_text(encoding="utf-8")
        assert text.lstrip().startswith(("#pragma once", "//", "/*")), h
        assert "#pragma once" in text, h
        if "UCLASS(" in text or "USTRUCT(" in text or "UINTERFACE(" in text or "UENUM(" in text:
            assert f'#include "{h.stem}.generated.h"' in text, h
        assert "Replicated" not in text and "bReplicates = true" not in text, h


def test_no_absolute_windows_paths_in_tools():
    for p in (ROOT / "tools").rglob("*.py"):
        assert not re.search(r"['\"][A-Za-z]:[\\/]", p.read_text(encoding="utf-8")) or p.name == "check_environment.py", p
