import json

from unwordy import hook


def payload(**fields):
    base = {"session_id": "s1", "cwd": fields.pop("cwd", "."), "hook_event_name": "PreToolUse"}
    base.update(fields)
    return base


def edit(project, name, content, **extra):
    fields = {"file_path": str(project / name), "content": content}
    fields.update(extra)
    return payload(cwd=str(project), tool_name="Write", tool_input=fields)


def commit(project, message):
    return payload(cwd=str(project), tool_name="Bash",
                   tool_input={"command": f'git commit -m "{message}"'})


def decision(out):
    return (out or {}).get("hookSpecificOutput", {})


def test_session_start_injects_the_voice(project):
    out = hook.run("session-start", payload(cwd=str(project), hook_event_name="SessionStart",
                                            source="startup"))
    context = decision(out)["additionalContext"]
    assert decision(out)["hookEventName"] == "SessionStart"
    assert context.startswith("Writing style the user set with unwordy (preset senior")
    assert "Write like a developer on this team" in context


def test_session_start_names_the_profile_file(project):
    (project / ".unwordy.md").write_text("---\npreset: lazy\n---\n")
    context = decision(hook.run("session-start", payload(cwd=str(project))))["additionalContext"]
    assert "preset lazy" in context and ".unwordy.md" in context


def test_disabled_profile_silences_every_mode(project):
    (project / ".unwordy.md").write_text("---\nenabled: false\n---\n")
    assert hook.run("session-start", payload(cwd=str(project))) is None
    assert hook.run("pre-edit", edit(project, "a.py", "# This function returns the user\n")) is None


def test_env_switch_silences_every_mode(project, monkeypatch):
    monkeypatch.setenv("UNWORDY_OFF", "1")
    assert hook.run("session-start", payload(cwd=str(project))) is None
    assert hook.run("pre-edit", edit(project, "a.py", "# This function returns the user\n")) is None


def test_unknown_mode_and_empty_payload():
    assert hook.run("nonsense", {}) is None
    assert hook.run("pre-edit", {}) is None
    assert hook.run("pre-bash", {"tool_input": None}) is None


def test_pre_edit_denies_a_restating_comment(project):
    out = hook.run("pre-edit", edit(project, "user.ts",
                                    "// This function returns the user\nexport function u() {}\n"))
    assert decision(out)["permissionDecision"] == "deny"
    assert decision(out)["permissionDecisionReason"].startswith("unwordy H4a: ")


def test_pre_edit_warns_on_soft_rules_without_a_decision(project):
    out = hook.run("pre-edit", edit(project, "notes.md", "We leverage the new schema.\n"))
    assert "permissionDecision" not in decision(out)
    assert decision(out)["additionalContext"].startswith("unwordy S2: ")


def test_strict_block_turns_soft_rules_into_denials(project):
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    out = hook.run("pre-edit", edit(project, "notes.md", "We leverage the new schema.\n"))
    assert decision(out)["permissionDecision"] == "deny"


def test_strict_off_drops_soft_rules(project):
    (project / ".unwordy.md").write_text("---\nstrict: off\n---\n")
    assert hook.run("pre-edit", edit(project, "notes.md", "We leverage the schema.\n")) is None


def test_disable_list_silences_a_rule(project):
    (project / ".unwordy.md").write_text("---\ndisable: H4\n---\n")
    assert hook.run("pre-edit", edit(project, "user.ts", "// This function returns the user\n")) is None


def test_pre_bash_denies_an_attribution_trailer(project):
    command = 'git commit -m "fix: retry" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'
    out = hook.run("pre-bash", payload(cwd=str(project), tool_name="Bash",
                                       tool_input={"command": command}))
    reason = decision(out)["permissionDecisionReason"]
    assert decision(out)["permissionDecision"] == "deny"
    assert reason.startswith("unwordy H1: ") and "commit again" in reason


def test_pre_bash_denies_agent_author(project):
    for command in ('git commit --author="Claude <claude@example.com>" -m "Fix retry"',
                    'GIT_AUTHOR_NAME=Claude git commit -m "Fix retry"'):
        out = hook.run("pre-bash", payload(cwd=str(project), tool_name="Bash",
                                           tool_input={"command": command}))
        assert decision(out)["permissionDecision"] == "deny"


def test_hard_rule_does_not_downgrade_after_two_denials(project):
    command = 'git commit -m "x" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'
    call = payload(cwd=str(project), tool_name="Bash", tool_input={"command": command})
    first = hook.run("pre-bash", call)
    second = hook.run("pre-bash", call)
    third = hook.run("pre-bash", call)
    assert decision(first)["permissionDecision"] == "deny"
    assert decision(second)["permissionDecision"] == "deny"
    assert decision(third)["permissionDecision"] == "deny"


def test_soft_rule_downgrades_after_two_denials(project):
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    call = payload(cwd=str(project), tool_name="Bash",
                   tool_input={"command": 'git commit -m "A comprehensive retry change"'})
    assert decision(hook.run("pre-bash", call))["permissionDecision"] == "deny"
    assert decision(hook.run("pre-bash", call))["permissionDecision"] == "deny"
    third = decision(hook.run("pre-bash", call))
    assert "permissionDecision" not in third
    assert "Passed as a warning after two denials." in third["additionalContext"]


def test_attribution_can_warn_or_allow_per_surface(project):
    (project / ".unwordy.md").write_text(
        "---\nattribution: warn\ncommit.attribution: allow\n---\n"
    )
    commit_call = payload(cwd=str(project), tool_name="Bash", tool_input={
        "command": 'git commit -m "fix" -m "Co-Authored-By: Claude"'
    })
    assert hook.run("pre-bash", commit_call) is None
    mcp_call = payload(cwd=str(project), tool_name="mcp__github__comment",
                       tool_input={"body": "Generated with Claude"})
    warning = decision(hook.run("pre-mcp", mcp_call))["additionalContext"]
    assert warning.startswith("unwordy H1:")


def test_loop_guard_is_per_session(project):
    command = 'git commit -m "x" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'
    call = payload(cwd=str(project), tool_name="Bash", tool_input={"command": command})
    hook.run("pre-bash", call)
    hook.run("pre-bash", call)
    other = dict(call, session_id="s2")
    assert decision(hook.run("pre-bash", other))["permissionDecision"] == "deny"


def test_pre_mcp_lints_long_text_fields(project):
    out = hook.run("pre-mcp", payload(
        cwd=str(project), tool_name="mcp__jira__add_comment",
        tool_input={"issueKey": "PROJ-1", "body": "We leverage a seamless approach here, truly."},
    ))
    assert decision(out)["additionalContext"].startswith("unwordy S2: ")


def test_pre_mcp_ignores_short_and_unnamed_fields(project):
    out = hook.run("pre-mcp", payload(cwd=str(project), tool_name="mcp__jira__search",
                                      tool_input={"jql": "project = X", "body": "leverage"}))
    assert out is None


def test_stop_is_quiet_unless_strict_blocks(project, tmp_path):
    reply = "line\n" * 20 + "Let me know if you want more."
    call = payload(cwd=str(project), hook_event_name="Stop", last_assistant_message=reply,
                   transcript_path=str(tmp_path / "missing.jsonl"))
    assert hook.run("stop", call) is None
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    out = hook.run("stop", call)
    assert out["decision"] == "block"
    assert out["reason"].startswith("unwordy S7b: ")


def test_stop_does_not_block_twice(project):
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    call = payload(cwd=str(project), hook_event_name="Stop", stop_hook_active=True,
                   last_assistant_message="Let me know if you want more.")
    assert hook.run("stop", call) is None


def test_stop_reads_the_transcript_for_the_question(project, tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(entry) for entry in [
        {"type": "user", "message": {"role": "user", "content": "Does the worker retry?"}},
        {"type": "assistant", "message": {"role": "assistant",
                                          "content": [{"type": "text", "text": "line\n" * 20}]}},
    ]) + "\n")
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    out = hook.run("stop", payload(cwd=str(project), hook_event_name="Stop",
                                   transcript_path=str(transcript)))
    assert "yes/no question" in out["reason"]


def test_cursor_shell_payload_is_normalised_and_denied(project):
    command = 'git commit -m "x" -m "Co-Authored-By: Cursor <cursoragent@cursor.com>"'
    out = hook.run("pre-bash", {"hook_event_name": "beforeShellExecution", "command": command,
                                "cwd": str(project), "conversation_id": "c1"})
    assert out["permission"] == "deny"
    assert out["agent_message"].startswith("unwordy H1: ")


def test_cursor_gets_no_output_for_soft_findings(project):
    out = hook.run("pre-bash", {"hook_event_name": "beforeShellExecution", "cwd": str(project),
                                "command": 'git commit -m "leverage the new schema"'})
    assert out is None


def test_codex_apply_patch_is_linted(project):
    patch = "*** Begin Patch\n*** Add File: user.ts\n+// This function returns the user\n*** End Patch\n"
    out = hook.run("pre-edit", payload(cwd=str(project), tool_name="apply_patch",
                                       tool_input={"command": patch}))
    assert decision(out)["permissionDecision"] == "deny"


def test_odd_cwd_shapes_are_tolerated(project):
    command = 'git commit -m "x" -m "Co-Authored-By: Claude <noreply@anthropic.com>"'
    for index, odd in enumerate(({"cwd": ["not", "a", "string"]}, {"cwd": 7},
                                 {"workspace_roots": {"a": 1}},
                                 {"cwd": "", "workspace_roots": [str(project)]})):
        call = dict(payload(tool_name="Bash", tool_input={"command": command}), **odd)
        call["session_id"] = f"odd{index}"
        assert decision(hook.run("pre-bash", call))["permissionDecision"] == "deny"


def test_unlintable_files_are_not_diffed(project):
    import time
    path = project / "rows.csv"
    body = "a,b,c\n" * 20000
    path.write_text(body)
    started = time.time()
    out = hook.run("pre-edit", edit(project, "rows.csv", body + "x,y,z\n"))
    assert time.time() - started < 0.5
    assert out is None


def test_pre_bash_lints_a_file_written_through_the_shell(project):
    command = "cat > user.ts <<'EOF'\n// This function returns the user\nexport function u() {}\nEOF"
    out = hook.run("pre-bash", payload(cwd=str(project), tool_name="Bash", tool_input={"command": command}))
    assert decision(out)["permissionDecision"] == "deny"
    assert decision(out)["permissionDecisionReason"].startswith("unwordy H4a: ")


def test_pre_bash_warns_on_prose_written_through_the_shell(project):
    command = "echo 'We leverage the new schema.' > notes.md"
    out = hook.run("pre-bash", payload(cwd=str(project), tool_name="Bash", tool_input={"command": command}))
    assert "permissionDecision" not in decision(out)
    assert decision(out)["additionalContext"].startswith("unwordy S2: ")


def test_pre_bash_skips_exempt_and_unknown_files_written_through_the_shell(project):
    for command in ("cat > tests/fixtures/x.ts <<'EOF'\n// This function returns the user\nEOF",
                    "cat > data.csv <<'EOF'\n// This function returns the user\nEOF"):
        assert hook.run("pre-bash", payload(cwd=str(project), tool_name="Bash",
                                            tool_input={"command": command})) is None


def test_disable_family_silences_every_sub_rule(project):
    (project / ".unwordy.md").write_text("---\ndisable: H2\n---\n")
    assert hook.run("pre-edit", edit(project, "a.py", "# see PROJ-142\n# Step 1: go\nx = 1\n")) is None


def test_disable_sub_rule_keeps_its_siblings(project):
    (project / ".unwordy.md").write_text("---\ndisable: h2b, S7b\n---\n")
    out = hook.run("pre-edit", edit(project, "a.py", "# see PROJ-142\n# Step 1: go\nx = 1\n"))
    reason = decision(out)["permissionDecisionReason"]
    assert decision(out)["permissionDecision"] == "deny"
    assert reason.startswith("unwordy H2d: ") and "H2b" not in reason


def test_loop_guard_counts_the_family(project):
    calls = [edit(project, "a.py", "# see PROJ-142\nx = 1\n"), edit(project, "a.py", "# see PROJ-143\nx = 1\n"),
             edit(project, "a.py", "# Step 1: go\nx = 1\n")]
    results = [hook.run("pre-edit", call) for call in calls]
    assert [decision(r).get("permissionDecision") for r in results] == ["deny", "deny", "deny"]
    assert decision(results[2])["permissionDecisionReason"].startswith("unwordy H2b: ")


def test_cursor_session_start_answers_in_its_own_shape(project):
    out = hook.run("session-start", {"hook_event_name": "sessionStart", "session_id": "c1",
                                     "workspace_roots": [str(project)], "composer_mode": "agent"})
    assert list(out) == ["additional_context"]
    assert out["additional_context"].startswith("Writing style the user set with unwordy (preset senior")


def test_cursor_pre_tool_use_shell_payload_is_denied(project):
    command = 'git commit -m "x" -m "Co-Authored-By: Cursor <cursoragent@cursor.com>"'
    out = hook.run("pre-bash", {"hook_event_name": "preToolUse", "tool_name": "Shell", "conversation_id": "c2",
                                "tool_input": {"command": command, "working_directory": str(project)},
                                "cwd": str(project)})
    assert out["permission"] == "deny" and out["agent_message"].startswith("unwordy H1: ")


def test_cursor_pre_tool_use_write_payload_is_denied(project):
    out = hook.run("pre-edit", {"hook_event_name": "preToolUse", "tool_name": "Write",
                                 "tool_input": {"file_path": str(project / "a.ts"),
                                                "content": "// This function returns the user\n"},
                                 "cwd": str(project)})
    assert out["permission"] == "deny"
    assert "H4a" in out["agent_message"]


def test_cursor_before_mcp_execution_checks_short_attribution(project):
    out = hook.run("pre-mcp", {"hook_event_name": "beforeMCPExecution",
                                "tool_name": "create_comment", "tool_input": '{"body":"Generated with Claude"}',
                                "cwd": str(project)})
    assert out["permission"] == "deny"


def test_commitlint_repo_keeps_hard_rules_but_not_subject_length(project):
    (project / ".unwordy.md").write_text("---\nstrict: block\n---\n")
    (project / ".commitlintrc.yml").write_text("extends: ['@commitlint/config-conventional']\n")
    long_subject = "feat(sync): " + "x" * 70
    assert hook.run("pre-bash", commit(project, long_subject)) is None
    out = hook.run("pre-bash", commit(project, "feat: x\" -m \"Co-Authored-By: Claude <noreply@anthropic.com>"))
    assert decision(out)["permissionDecision"] == "deny"
