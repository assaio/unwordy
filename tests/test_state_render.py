import os
import time

from unwordy import profile, render, state


def test_guard_counts_per_rule_and_target():
    guard = state.Guard("abc")
    assert not guard.exhausted("H1", "bash:git commit")
    guard.record([("H1", "bash:git commit")])
    assert not guard.exhausted("H1", "bash:git commit")
    guard.record([("H1", "bash:git commit")])
    assert guard.exhausted("H1", "bash:git commit")
    assert not guard.exhausted("H1", "bash:gh pr create")
    assert not guard.exhausted("H3", "bash:git commit")


def test_guard_survives_a_new_process_and_isolates_sessions():
    state.Guard("abc").record([("H1", "t")] * 2)
    assert state.Guard("abc").exhausted("H1", "t")
    assert not state.Guard("other").exhausted("H1", "t")


def test_guard_ignores_a_corrupt_state_file():
    guard = state.Guard("abc")
    guard.path.parent.mkdir(parents=True, exist_ok=True)
    guard.path.write_text("not json")
    assert state.Guard("abc").denials == {}


def test_guard_sanitises_the_session_id():
    guard = state.Guard("../../etc/passwd")
    assert guard.path.parent.name == "state"
    assert "/" not in guard.path.name


def test_prune_removes_stale_sessions():
    fresh, stale = state.Guard("fresh"), state.Guard("stale")
    fresh.record([("H1", "t")])
    stale.record([("H1", "t")])
    os.utime(stale.path, (time.time() - state.MAX_AGE_SECONDS - 60,) * 2)
    state.prune()
    assert fresh.path.exists() and not stale.path.exists()


def test_data_dir_prefers_plugin_data(tmp_path):
    assert state.data_dir({"CLAUDE_PLUGIN_DATA": str(tmp_path)}) == tmp_path
    assert state.data_dir({"HOME": str(tmp_path)}) == tmp_path / ".cache" / "unwordy"


def voice():
    return profile.Profile(dict(profile.DEFAULTS), profile.preset_body("senior")).voice()


def test_block_is_marker_delimited():
    text = render.block(voice())
    assert text.startswith(render.START) and text.endswith(render.END)
    assert "edit .unwordy.md" in render.START


def test_upsert_appends_to_existing_content():
    result = render.upsert("# Team notes\n\nRun the tests.\n", voice())
    assert result.startswith("# Team notes")
    assert render.START in result and result.endswith(render.END + "\n")


def test_upsert_is_idempotent():
    once = render.upsert("# Team notes\n", voice())
    assert render.upsert(once, voice()) == once


def test_upsert_replaces_an_old_block():
    stale = render.upsert("# Team notes\n", "Old voice.")
    fresh = render.upsert(stale, "New voice.")
    assert "Old voice." not in fresh and "New voice." in fresh
    assert fresh.count(render.START) == 1


def test_upsert_into_an_empty_file():
    assert render.upsert("", "Voice.").startswith(render.START)


def test_mdc_carries_cursor_frontmatter_and_is_idempotent():
    text = render.mdc(voice())
    assert text.startswith("---\ndescription: unwordy writing style\nalwaysApply: true\n---\n")
    assert render.mdc(voice()) == text
    assert render.START in text


def test_remove_takes_the_block_out():
    text = render.upsert("# Team notes\n", voice())
    assert render.remove(text) == "# Team notes\n"
    assert render.remove("") == ""
