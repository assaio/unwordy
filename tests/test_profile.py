import pytest

from unwordy import profile

from conftest import TEMPLATES


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def test_parse_without_frontmatter():
    settings, body = profile.parse("Dry and direct.\n")
    assert settings == {}
    assert body == "Dry and direct."


def test_parse_frontmatter_only():
    settings, body = profile.parse("---\npreset: lazy\n---\n")
    assert settings == {"preset": "lazy"}
    assert body == ""


def test_parse_empty_frontmatter():
    assert profile.parse("---\n---\nbody\n") == ({}, "body")


def test_parse_strips_inline_comment():
    settings, _ = profile.parse("---\npreset: senior            # lazy | senior\n---\n")
    assert settings["preset"] == "senior"


def test_parse_keeps_hash_inside_value():
    settings, _ = profile.parse("---\nbanned_words: c#, foo\n---\n")
    assert settings["banned_words"] == ["c#", "foo"]


def test_parse_lists_and_brackets():
    settings, _ = profile.parse(
        "---\nignore: [vendor/**, '**/*.generated.*']\ndisable: s1, S3\n---\n"
    )
    assert settings["ignore"] == ["vendor/**", "**/*.generated.*"]
    assert settings["disable"] == ["s1", "S3"]


def test_parse_booleans():
    for raw, expected in (("yes", True), ("on", True), ("1", True), ("true", True),
                          ("no", False), ("off", False), ("0", False), ("false", False)):
        settings, _ = profile.parse(f"---\nenabled: {raw}\n---\n")
        assert settings["enabled"] is expected


def test_parse_invalid_values_fall_back_to_defaults(tmp_path):
    path = write(tmp_path / ".unwordy.md", "---\nmax_subject: soon\nenabled: maybe\n---\n")
    resolved = profile.resolve(tmp_path, {"UNWORDY_STYLE": str(path)})
    assert resolved.settings["max_subject"] == 72
    assert resolved.settings["enabled"] is True


def test_parse_unclosed_frontmatter_is_body():
    settings, body = profile.parse("---\npreset: lazy\nstill open\n")
    assert settings == {}
    assert body.startswith("---")


def test_parse_crlf_and_bom():
    settings, body = profile.parse("﻿---\r\npreset: qa\r\n---\r\nTerse.\r\n")
    assert settings == {"preset": "qa"}
    assert body == "Terse."


def test_parse_quoted_value_and_hyphen_key():
    settings, _ = profile.parse("---\nlanguage: \"pl\"\nallow-ticket-refs: true\n---\n")
    assert settings["language"] == "pl"
    assert settings["allow_ticket_refs"] is True


def test_parse_ignores_junk_lines():
    settings, _ = profile.parse("---\n# a comment\n\n- item\npreset: lead\n---\n")
    assert settings == {"preset": "lead"}


def test_resolve_falls_back_to_senior(project):
    resolved = profile.resolve(project, {"HOME": str(project)})
    assert resolved.path is None
    assert resolved.settings["preset"] == "senior"
    assert resolved.body == profile.preset_body("senior")


def test_resolve_walks_up_to_git_root(project):
    write(project / ".unwordy.md", "---\npreset: lazy\n---\n")
    deep = project / "src" / "api"
    deep.mkdir(parents=True)
    assert profile.resolve(deep, {"HOME": str(project)}).settings["preset"] == "lazy"


def test_resolve_stops_at_git_root(tmp_path):
    write(tmp_path / ".unwordy.md", "---\npreset: lazy\n---\n")
    inner = tmp_path / "repo"
    (inner / ".git").mkdir(parents=True)
    assert profile.resolve(inner, {"HOME": str(tmp_path)}).path is None


def test_resolve_reads_xdg_config(project, isolated):
    path = write(isolated / ".config" / "unwordy" / "style.md", "---\npreset: qa\n---\n")
    resolved = profile.resolve(project, {"XDG_CONFIG_HOME": str(isolated / ".config")})
    assert resolved.path == path
    assert resolved.settings["preset"] == "qa"


def test_project_file_beats_global(project, isolated):
    write(isolated / ".config" / "unwordy" / "style.md", "---\npreset: qa\n---\n")
    write(project / ".unwordy.md", "---\npreset: formal\n---\n")
    resolved = profile.resolve(project, {"XDG_CONFIG_HOME": str(isolated / ".config")})
    assert resolved.settings["preset"] == "formal"


def test_env_override_beats_project(project, tmp_path):
    write(project / ".unwordy.md", "---\npreset: formal\n---\n")
    override = write(tmp_path / "team.md", "---\npreset: lead\n---\n")
    resolved = profile.resolve(project, {"UNWORDY_STYLE": str(override)})
    assert resolved.path == override
    assert resolved.settings["preset"] == "lead"


def test_env_override_missing_file_falls_through(project):
    write(project / ".unwordy.md", "---\npreset: formal\n---\n")
    resolved = profile.resolve(project, {"UNWORDY_STYLE": str(project / "gone.md")})
    assert resolved.settings["preset"] == "formal"


def test_custom_body_wins_over_preset(project):
    write(project / ".unwordy.md", "---\npreset: custom\n---\nAll lowercase, no bullets.\n")
    resolved = profile.resolve(project, {})
    assert resolved.body == "All lowercase, no bullets."


def test_custom_preset_without_body_falls_back(project):
    write(project / ".unwordy.md", "---\npreset: custom\n---\n")
    assert profile.resolve(project, {}).body == profile.preset_body("senior")


def test_voice_has_core_rules_and_body(project):
    write(project / ".unwordy.md", "---\npreset: lazy\nlanguage: pl\n---\n")
    voice = profile.resolve(project, {}).voice()
    assert voice.startswith(profile.core_rules())
    assert profile.preset_body("lazy") in voice
    assert "Default language for replies and tracker text: pl." in voice


def test_voice_omits_language_when_auto(project):
    assert "Default language" not in profile.resolve(project, {}).voice()


def test_disabled_profile(project):
    write(project / ".unwordy.md", "---\nenabled: false\n---\n")
    assert profile.resolve(project, {}).enabled is False


def test_every_preset_ships_and_is_short():
    for name in profile.PRESETS:
        body = profile.preset_body(name)
        assert body and len(body.split()) < 60
    assert len(profile.core_rules().split()) <= 130


def test_banned_words_default_has_both_languages(project):
    words = profile.resolve(project, {}).settings["banned_words"]
    assert "delve" in words and "kompleksowy" in words


def test_banned_words_override_replaces_defaults(project):
    write(project / ".unwordy.md", "---\nbanned_words: foo, bar\n---\n")
    assert profile.resolve(project, {}).settings["banned_words"] == ["foo", "bar"]


def test_disable_ids_are_normalised(project):
    (project / ".unwordy.md").write_text("---\ndisable: h2, s5F, H4b\n---\n")
    assert profile.resolve(str(project)).settings["disable"] == ["H2", "S5f", "H4b"]


def test_dotted_keys_are_typed_by_their_base_name():
    settings, _ = profile.parse("---\npr.max_body_lines: 20\ncommit.max_subject: 60\ncommit.max_subject: x\n---\n")
    assert settings == {"pr.max_body_lines": 20, "commit.max_subject": 60}


def test_german_words_are_banned_by_default():
    assert "nahtlos" in profile.DEFAULTS["banned_words"]


def test_commit_conventions_from_commitlint_files(project):
    assert not profile.commit_conventions(str(project))
    (project / "commitlint.config.js").write_text("module.exports = {}\n")
    assert profile.commit_conventions(str(project / "sub-dir-not-there-yet"))
    (project / "commitlint.config.js").unlink()
    (project / ".commitlintrc.json").write_text("{}\n")
    assert profile.commit_conventions(str(project))
    (project / ".commitlintrc.json").unlink()
    (project / "package.json").write_text('{"commitlint": {"extends": ["@commitlint/config-conventional"]}}\n')
    assert profile.commit_conventions(str(project))


def test_commit_conventions_from_git_templates(project, isolated):
    (project / ".git" / "config").write_text("[core]\n\tbare = false\n[commit]\n\ttemplate = ~/.gitmessage\n")
    assert profile.commit_conventions(str(project))
    (project / ".git" / "config").write_text("[core]\n\tbare = false\n[commit]\n\tgpgsign = true\n")
    assert not profile.commit_conventions(str(project))
    (isolated / ".gitmessage").write_text("subject\n")
    assert profile.commit_conventions(str(project))


@pytest.mark.parametrize("name", ["team-strict", "team-qa", "team-enterprise"])
def test_templates_parse_and_resolve(project, name):
    text = (TEMPLATES / f"{name}.md").read_text(encoding="utf-8")
    settings, body = profile.parse(text)
    assert settings["preset"] in profile.PRESETS and body
    (project / ".unwordy.md").write_text(text)
    resolved = profile.resolve(str(project))
    assert resolved.settings["preset"] == settings["preset"] and resolved.body == body
