import json
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
MANIFESTS = ("plugin.json", ".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".cursor-plugin/plugin.json")


def load(path):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def test_manifests_agree_on_identity():
    first = load(MANIFESTS[0])
    for path in MANIFESTS[1:]:
        data = load(path)
        for key in ("name", "version", "description", "author", "homepage", "repository", "license"):
            assert data[key] == first[key], (path, key)


def test_codex_overlay_matches_the_portable_extension():
    portable = load("plugin.json")["extensions"]["com.openai"]
    overlay = load(".codex-plugin/plugin.json")
    assert overlay["interface"] == portable["interface"]
    assert overlay["hooks"] == portable["hooks"]


def test_claude_manifest_leaves_the_standard_hooks_file_alone():
    """Claude Code loads hooks/hooks.json by itself; naming it again fails the hook load."""
    assert "hooks" not in load(".claude-plugin/plugin.json")


def test_both_marketplaces_list_this_plugin_from_the_repo_root():
    name = load("plugin.json")["name"]
    claude = load(".claude-plugin/marketplace.json")
    codex = load(".agents/plugins/marketplace.json")
    assert [p["name"] for p in claude["plugins"]] == [name]
    assert [p["name"] for p in codex["plugins"]] == [name]
    assert claude["plugins"][0]["source"] == "./"
    assert codex["plugins"][0]["source"] == {"source": "local", "path": "./"}


def test_changelog_has_the_current_version():
    version = load("plugin.json")["version"]
    assert f"## v{version}" in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("skill", sorted(p.name for p in (ROOT / "skills").iterdir() if p.is_dir()))
def test_skill_name_matches_its_directory(skill):
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert re.search(rf"^name: {re.escape(skill)}$", text, re.M), skill
