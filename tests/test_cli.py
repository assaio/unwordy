import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / "hooks" / "run.sh"


def run(mode, payload, env_extra=None, cwd=None):
    env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"],
           "XDG_CONFIG_HOME": os.environ["XDG_CONFIG_HOME"],
           "CLAUDE_PLUGIN_DATA": os.environ["CLAUDE_PLUGIN_DATA"],
           "CLAUDE_PLUGIN_ROOT": str(ROOT)}
    env.update(env_extra or {})
    raw = payload if isinstance(payload, (str, bytes)) else json.dumps(payload)
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    return subprocess.run(["sh", str(RUN), mode], input=raw, capture_output=True,
                          env=env, cwd=str(cwd or ROOT))


def out_json(result):
    assert result.returncode == 0, result.stderr.decode()
    return json.loads(result.stdout.decode())


def base(project, **fields):
    payload = {"session_id": "cli", "cwd": str(project), "hook_event_name": "PreToolUse"}
    payload.update(fields)
    return payload


def test_session_start_prints_context(project):
    result = run("session-start", base(project, hook_event_name="SessionStart", source="startup"))
    context = out_json(result)["hookSpecificOutput"]["additionalContext"]
    assert "Write like a developer on this team" in context


def test_edit_matcher_denies(project):
    (project / "user.ts").write_text("export function u() {}\n")
    payload = base(project, tool_name="Edit", tool_input={
        "file_path": str(project / "user.ts"),
        "old_string": "export function u() {}",
        "new_string": "// This function returns the user\nexport function u() {}",
    })
    decision = out_json(run("pre-edit", payload))["hookSpecificOutput"]
    assert decision["permissionDecision"] == "deny"


def test_write_matcher_denies(project):
    payload = base(project, tool_name="Write", tool_input={
        "file_path": str(project / "user.py"), "content": "# This function returns the user\n"})
    assert out_json(run("pre-edit", payload))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_multiedit_matcher_denies(project):
    (project / "a.py").write_text("x = 1\n")
    payload = base(project, tool_name="MultiEdit", tool_input={
        "file_path": str(project / "a.py"),
        "edits": [{"old_string": "x = 1", "new_string": "# This class handles the user\nx = 1"}]})
    assert out_json(run("pre-edit", payload))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_notebook_matcher_denies(project):
    (project / "n.ipynb").write_text(json.dumps({"cells": []}))
    payload = base(project, tool_name="NotebookEdit", tool_input={
        "notebook_path": str(project / "n.ipynb"), "cell_id": "c1",
        "new_source": "# This function returns the user\n"})
    assert out_json(run("pre-edit", payload))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_bash_matcher_denies(project):
    payload = base(project, tool_name="Bash", tool_input={
        "command": 'git commit -m "fix" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'})
    assert out_json(run("pre-bash", payload))["hookSpecificOutput"]["permissionDecision"] == "deny"


def test_mcp_matcher_warns(project):
    payload = base(project, tool_name="mcp__jira__add_comment",
                   tool_input={"body": "We leverage a seamless approach in this comment."})
    context = out_json(run("pre-mcp", payload))["hookSpecificOutput"]["additionalContext"]
    assert context.startswith("unwordy S2: ")


def test_stop_matcher_blocks_under_strict(project):
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    payload = base(project, hook_event_name="Stop",
                   last_assistant_message="Feel free to ping me if it breaks.")
    assert out_json(run("stop", payload))["decision"] == "block"


def test_clean_calls_say_nothing(project):
    payload = base(project, tool_name="Bash", tool_input={"command": 'git commit -m "fix: retry"'})
    result = run("pre-bash", payload)
    assert (result.returncode, result.stdout) == (0, b"")


@pytest.mark.parametrize("raw", [b"", b"   ", b"not json at all", b"[1, 2, 3]", b'{"broken": ',
                                 b"\x00\xff\xfe binary", b'{"tool_input": "not an object"}'])
def test_malformed_input_never_fails(project, raw):
    for mode in ("session-start", "pre-edit", "pre-bash", "pre-mcp", "stop"):
        result = run(mode, raw)
        assert result.returncode == 0
        assert result.stdout in (b"",) or json.loads(result.stdout.decode())


def test_unknown_mode_is_silent(project):
    result = run("not-a-mode", base(project))
    assert (result.returncode, result.stdout) == (0, b"")


def test_env_switch_disables_the_hook(project):
    payload = base(project, tool_name="Write", tool_input={
        "file_path": str(project / "a.py"), "content": "# This function returns the user\n"})
    result = run("pre-edit", payload, env_extra={"UNWORDY_OFF": "1"})
    assert (result.returncode, result.stdout) == (0, b"")


def test_render_prints_a_block_and_an_mdc(project):
    env = {"PATH": os.environ["PATH"], "HOME": os.environ["HOME"],
           "XDG_CONFIG_HOME": os.environ["XDG_CONFIG_HOME"],
           "PYTHONPATH": str(ROOT)}
    block = subprocess.run([sys.executable, "-m", "unwordy.hook", "render"], capture_output=True,
                           env=env, cwd=str(project)).stdout.decode()
    mdc = subprocess.run([sys.executable, "-m", "unwordy.hook", "render", "mdc"], capture_output=True,
                         env=env, cwd=str(project)).stdout.decode()
    assert block.startswith("<!-- unwordy:start") and block.rstrip().endswith("-->")
    assert mdc.startswith("---\ndescription: unwordy writing style")


def test_internal_errors_are_logged_and_swallowed(project, monkeypatch, capsysbinary):
    from unwordy import hook, lint

    def boom(*_args, **_kwargs):
        raise RuntimeError("boom")

    raw = json.dumps(base(project, tool_name="Write", tool_input={
        "file_path": str(project / "a.py"), "content": "# hi\n"})).encode()

    class FakeStdin:
        buffer = type("Buffer", (), {"read": staticmethod(lambda: raw)})

    monkeypatch.setattr(lint, "lint_change", boom)
    monkeypatch.setattr(sys, "stdin", FakeStdin)
    assert hook.main(["pre-edit"]) == 0
    assert capsysbinary.readouterr().out == b""
    assert "RuntimeError: boom" in (Path(os.environ["CLAUDE_PLUGIN_DATA"]) / "unwordy.log").read_text()
