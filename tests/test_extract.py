import json

from unwordy import extract


def change_for(tool, tool_input, cwd):
    changes = extract.edit_changes(tool, tool_input, str(cwd))
    return changes[0] if changes else None


def added_text(change):
    return [change.lines[i] for i in sorted(change.added)]


def test_edit_added_lines_keep_file_context(project):
    path = project / "app.py"
    path.write_text("import os\n\n\ndef main():\n    return os.getcwd()\n")
    change = change_for("Edit", {
        "file_path": str(path),
        "old_string": "def main():\n    return os.getcwd()",
        "new_string": "def main():\n    # Return the path\n    return os.getcwd()",
    }, project)
    assert added_text(change) == ["    # Return the path"]
    assert change.lines[0] == "import os"
    assert change.partial is False


def test_edit_replace_all_marks_every_copy(project):
    path = project / "app.py"
    path.write_text("a = 1\nb = 1\n")
    change = change_for("Edit", {"file_path": str(path), "old_string": "1",
                                 "new_string": "2", "replace_all": True}, project)
    assert added_text(change) == ["a = 2", "b = 2"]


def test_edit_falls_back_to_fragment_when_old_string_is_missing(project):
    path = project / "app.py"
    path.write_text("a = 1\n")
    change = change_for("Edit", {"file_path": str(path), "old_string": "zzz",
                                 "new_string": "# new comment\nzzz"}, project)
    assert change.partial is True
    assert added_text(change) == ["# new comment"]


def test_write_new_file_adds_every_line(project):
    change = change_for("Write", {"file_path": str(project / "new.py"),
                                  "content": "a = 1\nb = 2\n"}, project)
    assert added_text(change) == ["a = 1", "b = 2"]


def test_write_existing_file_diffs_against_disk(project):
    path = project / "app.py"
    path.write_text("a = 1\nb = 2\n")
    change = change_for("Write", {"file_path": str(path), "content": "a = 1\nb = 3\nc = 4\n"}, project)
    assert added_text(change) == ["b = 3", "c = 4"]


def test_multiedit_applies_edits_in_order(project):
    path = project / "app.py"
    path.write_text("one\ntwo\n")
    change = change_for("MultiEdit", {"file_path": str(path), "edits": [
        {"old_string": "one", "new_string": "uno"},
        {"old_string": "two", "new_string": "dos"},
    ]}, project)
    assert added_text(change) == ["uno", "dos"]


def test_notebook_edit_diffs_the_cell(project):
    path = project / "notes.ipynb"
    path.write_text(json.dumps({
        "metadata": {"language_info": {"name": "python"}},
        "cells": [{"id": "c1", "cell_type": "code", "source": ["x = 1\n"]}],
    }))
    change = change_for("NotebookEdit", {"notebook_path": str(path), "cell_id": "c1",
                                         "new_source": "x = 1\n# added here\n"}, project)
    assert added_text(change) == ["# added here"]
    assert change.path.endswith(".ipynb.py")


def test_notebook_markdown_cell_is_prose(project):
    path = project / "notes.ipynb"
    path.write_text(json.dumps({"cells": [{"id": "c1", "cell_type": "markdown", "source": "hi"}]}))
    change = change_for("NotebookEdit", {"notebook_path": str(path), "cell_id": "c1",
                                         "cell_type": "markdown", "new_source": "hi\nthere\n"}, project)
    assert change.path.endswith(".ipynb.md")


def test_apply_patch_add_and_update(project):
    patch = (
        "*** Begin Patch\n"
        "*** Add File: new.py\n"
        "+# fresh\n"
        "+x = 1\n"
        "*** Update File: old.py\n"
        "@@ def main():\n"
        " def main():\n"
        "-    return 1\n"
        "+    # Return two\n"
        "+    return 2\n"
        "*** End Patch\n"
    )
    changes = extract.edit_changes("apply_patch", {"command": patch}, str(project))
    assert [c.path.split("/")[-1] for c in changes] == ["new.py", "old.py"]
    assert added_text(changes[0]) == ["# fresh", "x = 1"]
    assert added_text(changes[1]) == ["    # Return two", "    return 2"]
    assert changes[1].lines[0] == "def main():"
    assert changes[1].partial is True


def test_scan_python_comments_strings_and_docstrings():
    lines = [
        "#!/usr/bin/env python3",
        "def f():",
        '    """Doc line.',
        "",
        '    More doc."""',
        "    url = \"http://example.com#anchor\"",
        "    return 1  # trailing note",
        "    text = '''",
        "# not a comment",
        "'''",
    ]
    info = extract.scan(lines, extract.PYTHON)
    assert [line.kind for line in info] == [
        "comment", "code", "comment", "comment", "comment", "code", "mixed", "code", "code", "code"
    ]
    assert info[2].comment == "Doc line."
    assert info[2].doc and info[4].doc
    assert info[6].comment == "trailing note"


def test_scan_c_like_block_and_url():
    lines = [
        "const url = 'https://example.com'; // real comment",
        "/** doc start",
        " * doc body",
        " */",
        "int x = 1; /* inline */ int y = 2;",
    ]
    info = extract.scan(lines, extract.JS_LIKE)
    assert info[0].kind == "mixed" and info[0].comment == "real comment"
    assert [line.doc for line in info[1:4]] == [True, True, True]
    assert info[2].comment == "doc body"
    assert info[4].kind == "mixed" and info[4].comment == "inline"


def test_scan_go_backtick_string_hides_comment_markers():
    lines = ["var q = `", "// not a comment", "`", "// a comment"]
    info = extract.scan(lines, extract.JS_LIKE)
    assert [line.kind for line in info] == ["code", "code", "code", "comment"]


def test_scan_sql_lua_and_markup():
    assert extract.scan(["select 1 -- note"], extract.SQL)[0].comment == "note"
    assert extract.scan(["--[[ block", "still block ]]"], extract.LUA)[0].kind == "comment"
    assert extract.scan(["<!-- hi -->"], extract.MARKUP)[0].comment == "hi"


def test_syntax_lookup_by_name_and_suffix():
    assert extract.syntax_for("/x/Dockerfile") is extract.HASH
    assert extract.syntax_for("/x/README.md") is extract.TEXT
    assert extract.syntax_for("/x/data.json") is None


def test_shell_git_commit_message(project):
    message = extract.shell_messages('git commit -m "fix: drop the retry"', str(project))[0]
    assert (message.surface, message.target) == ("commit", "git commit")
    assert message.title == "fix: drop the retry"


def test_shell_repeated_m_joins_paragraphs(project):
    message = extract.shell_messages('git commit -m "subject" -m "body line"', str(project))[0]
    assert message.title == "subject"
    assert message.body == "body line"


def test_shell_clustered_short_flags(project):
    message = extract.shell_messages("git commit -am 'quick fix'", str(project))[0]
    assert message.title == "quick fix"


def test_shell_heredoc_in_command_substitution(project):
    command = 'git commit -m "$(cat <<\'EOF\'\nsubject here\n\nbody here\nEOF\n)"'
    message = extract.shell_messages(command, str(project))[0]
    assert message.title == "subject here"
    assert message.body == "body here"


def test_shell_commit_file_flag(project):
    (project / "msg.txt").write_text("subject from file\n\nbody from file\n")
    message = extract.shell_messages("git commit -F msg.txt", str(project))[0]
    assert message.title == "subject from file"
    assert message.body == "body from file"


def test_shell_commit_stdin_heredoc(project):
    command = "git commit -F - <<'EOF'\nsubject from stdin\nEOF"
    message = extract.shell_messages(command, str(project))[0]
    assert message.title == "subject from stdin"


def test_shell_commit_trailer_and_author_go_to_meta(project):
    command = ('git commit -m "subject" --trailer "Co-authored-by: Claude <noreply@anthropic.com>"')
    message = extract.shell_messages(command, str(project))[0]
    assert "Co-authored-by" in message.meta


def test_shell_git_global_options_and_chaining(project):
    command = 'cd sub && git -C sub -c user.name=x commit -m "subject"'
    assert extract.shell_messages(command, str(project))[0].title == "subject"


def test_shell_gh_pr_create(project):
    command = 'gh pr create --title "Add retry" --body "Because 502s."'
    message = extract.shell_messages(command, str(project))[0]
    assert (message.surface, message.title, message.body) == ("pr", "Add retry", "Because 502s.")


def test_shell_gh_pr_create_body_file(project):
    (project / "body.md").write_text("PR body from a file\n")
    message = extract.shell_messages("gh pr create -t Title --body-file body.md", str(project))[0]
    assert message.body.strip() == "PR body from a file"


def test_shell_gh_issue_comment(project):
    message = extract.shell_messages('gh issue comment 12 --body "on it"', str(project))[0]
    assert (message.surface, message.body) == ("comment", "on it")


def test_shell_gh_pr_review_boolean_flags(project):
    message = extract.shell_messages('gh pr review -c -b "looks fine"', str(project))[0]
    assert message.body == "looks fine"


def test_shell_gh_api_field(project):
    command = 'gh api repos/o/r/issues/1/comments -f body="a longer comment body here"'
    message = extract.shell_messages(command, str(project))[0]
    assert message.body.startswith("a longer comment")


def test_shell_glab_mr_and_issue(project):
    mr = extract.shell_messages('glab mr create -t "Add retry" -d "why"', str(project))[0]
    note = extract.shell_messages('glab issue note 4 -m "on it"', str(project))[0]
    assert (mr.surface, mr.title) == ("pr", "Add retry")
    assert (note.surface, note.body) == ("comment", "on it")


def test_shell_unknown_and_broken_commands(project):
    assert extract.shell_messages("npm test && ls -la", str(project)) == []
    assert extract.shell_messages('echo "unterminated', str(project)) == []
    assert extract.shell_messages("git commit --amend --no-edit", str(project)) == []
    assert extract.shell_messages("", str(project)) == []


def test_shell_subshell_does_not_swallow_next_command(project):
    command = '(cd sub && git commit -m "a"); gh pr create --title "T" --body "b"'
    surfaces = [m.surface for m in extract.shell_messages(command, str(project))]
    assert surfaces == ["commit", "pr"]


def test_mcp_fields_by_name_even_when_short():
    fields = extract.mcp_fields({
        "issueKey": "PROJ-1",
        "commentBody": "x" * 50,
        "context": "y" * 50,
        "title": "short",
    })
    assert [key for key, _ in fields] == ["commentBody"]
    assert extract.mcp_fields({"body": "Generated with Claude"}) == [("body", "Generated with Claude")]


def test_mcp_fields_walk_nested_documents():
    payload = {"fields": {"description": {"content": [{"type": "text", "text": "z" * 60}]}}}
    assert extract.mcp_fields(payload)[0][0] == "text"


def test_mcp_fields_accept_json_string():
    assert extract.mcp_fields(json.dumps({"body": "q" * 60}))[0][0] == "body"


def test_scan_triple_quoted_argument_is_a_string_not_a_docstring():
    lines = [
        "cursor.execute(",
        '    """',
        "    SELECT * FROM t WHERE ticket = 'ABC-123'",
        '    """,',
        ")",
    ]
    info = extract.scan(lines, extract.PYTHON)
    assert [line.kind for line in info] == ["code", "code", "code", "code", "code"]
    assert not any(line.doc for line in info)


def test_scan_docstrings_in_docstring_positions():
    lines = [
        "#!/usr/bin/env python3",
        '"""Module doc."""',
        "",
        "def f(",
        "    a,",
        "):",
        '    """Function doc.',
        "",
        '    More."""',
        "    return a",
        "class C:",
        "    '''Class doc.'''",
    ]
    info = extract.scan(lines, extract.PYTHON)
    assert [i for i, line in enumerate(info) if line.doc] == [1, 6, 7, 8, 11]


def test_scan_marks_string_continuation_lines():
    lines = ['sql = """', "SELECT 1", '"""', "x = 1"]
    info = extract.scan(lines, extract.PYTHON)
    assert [line.cont for line in info] == [False, True, True, False]


def test_scan_apostrophe_inside_a_word_is_not_a_quote():
    info = extract.scan(["title: Don't do it  # trailing"], extract.HASH)
    assert info[0].kind == "mixed" and info[0].comment == "trailing"
    assert extract.scan(["echo 'a # b'"], extract.HASH)[0].kind == "code"


def test_scan_escaped_comment_marker_is_code():
    info = extract.scan([r"50\% of the total", "x % note"], extract.PERCENT)
    assert info[0].kind == "code"
    assert info[1].comment == "note"


def test_shell_line_continuations_are_joined(project):
    command = 'gh pr create \\\n  --title "Add retry" \\\n  --body "Because 502s."'
    message = extract.shell_messages(command, str(project))[0]
    assert (message.title, message.body) == ("Add retry", "Because 502s.")
    commit = extract.shell_messages('git commit \\\n  -m "subject"', str(project))[0]
    assert commit.title == "subject"


def test_shell_shift_operator_is_not_a_heredoc(project):
    command = 'python3 -c "\nx = 1 << 2\nprint(x)\n"\ngit commit -m "after shift"'
    assert [m.title for m in extract.shell_messages(command, str(project))] == ["after shift"]


def test_shell_heredoc_delimiter_may_contain_a_hyphen(project):
    command = "git commit -F - <<'END-MSG'\nreal subject\nEND-MSG"
    assert extract.shell_messages(command, str(project))[0].title == "real subject"


def test_repetitive_files_diff_quickly(project):
    import time
    path = project / "rows.py"
    body = "row = 1\n" * 8000
    path.write_text(body)
    started = time.time()
    change = change_for("Write", {"file_path": str(path), "content": body + "# new\n"}, project)
    assert time.time() - started < 1.0
    assert added_text(change) == ["# new"]


def test_edit_changes_honours_the_want_filter(project):
    path = project / "data.csv"
    path.write_text("a,b\n" * 10)
    tool_input = {"file_path": str(path), "content": "a,b\n" * 11}
    assert extract.edit_changes("Write", tool_input, str(project), want=lambda p: False) == []
    assert extract.edit_changes("Write", tool_input, str(project)) != []


def test_transcript_ignores_non_string_text_blocks(tmp_path):
    transcript = tmp_path / "t.jsonl"
    transcript.write_text("\n".join(json.dumps(entry) for entry in [
        {"type": "user", "message": {"content": "Does it retry?"}},
        {"type": "assistant", "message": {"content": [{"type": "text", "text": 123},
                                                      {"type": "text", "text": "Yes."}]}},
    ]) + "\n")
    assert extract.read_transcript_tail(str(transcript)) == ("Does it retry?", "Yes.")


def write_for(command, cwd):
    changes = extract.shell_writes(command, str(cwd))
    return [(c.path.split("/")[-1], added_text(c), c.lines) for c in changes]


def test_shell_write_cat_heredoc_before_and_after_the_redirect(project):
    assert write_for("cat > notes.md <<'EOF'\nfirst\nsecond\nEOF", project) == [
        ("notes.md", ["first", "second"], ["first", "second"])
    ]
    assert write_for("cat <<EOF > notes.md\nhello\nEOF", project) == [("notes.md", ["hello"], ["hello"])]


def test_shell_write_heredoc_body_is_not_a_command(project):
    command = "cat > runbook.md <<'EOF'\nRelease steps:\ngit commit -m \"cut release\"\ngh pr create --title x\nEOF"
    assert extract.shell_messages(command, str(project)) == []
    assert write_for(command, project) == [(
        "runbook.md",
        ["Release steps:", 'git commit -m "cut release"', "gh pr create --title x"],
        ["Release steps:", 'git commit -m "cut release"', "gh pr create --title x"],
    )]


def test_shell_write_tee_and_tee_append(project):
    (project / "notes.md").write_text("old line\n")
    assert write_for("tee notes.md <<'EOF'\nvia tee\nEOF", project) == [("notes.md", ["via tee"], ["via tee"])]
    assert write_for("sudo tee -a notes.md <<'EOF'\nappended\nEOF", project) == [
        ("notes.md", ["appended"], ["old line", "appended"])
    ]


def test_shell_write_echo_and_printf(project):
    assert write_for("echo 'one line' > notes.md", project) == [("notes.md", ["one line"], ["one line"])]
    assert write_for("echo -e 'a\\nb' > notes.md", project)[0][1] == ["a", "b"]
    assert write_for("printf '%s\\n' one two > notes.md", project)[0][1] == ["one", "two"]
    assert write_for("printf 'done %d%%\\n' 5 > notes.md", project)[0][1] == ["done 5%"]


def test_shell_write_append_keeps_file_context(project):
    (project / "app.py").write_text("x = 1\n")
    assert write_for("echo '# a note' >> app.py", project) == [("app.py", ["# a note"], ["x = 1", "# a note"])]


def test_shell_write_through_a_pipe(project):
    assert write_for("cat <<'EOF' | tee notes.md\npiped\nEOF", project) == [("notes.md", ["piped"], ["piped"])]
    assert write_for("echo hi | tee -a notes.md | cat", project) == [("notes.md", ["hi"], ["hi"])]


def test_shell_write_ignores_unknown_content_stderr_and_in_place_editors(project):
    assert write_for("ls > out.md", project) == []
    assert write_for("cat src.py > copy.py", project) == []
    assert write_for("echo x 2> err.md", project) == []
    assert write_for("echo x >&2", project) == []
    assert write_for("sed -i 's/a/b/' notes.md", project) == []
    assert write_for("echo x > /dev/null", project) == []


def test_shell_write_stdout_with_stderr_merged_and_a_following_commit(project):
    assert write_for("echo x > out.md 2>&1", project) == [("out.md", ["x"], ["x"])]
    command = "echo x > a.md && git commit -m 'after the write'"
    assert write_for(command, project) == [("a.md", ["x"], ["x"])]
    assert [m.title for m in extract.shell_messages(command, str(project))] == ["after the write"]


def test_shell_write_here_string_and_dashed_heredoc(project):
    assert write_for("cat <<< 'here string' > notes.md", project) == [("notes.md", ["here string"], ["here string"])]
    assert write_for("cat > notes.md <<-EOF\n\t\ttabbed\n\tEOF", project) == [("notes.md", ["tabbed"], ["tabbed"])]


def test_shell_write_honours_the_want_filter(project):
    command = "echo x > a.md; echo y > b.md"
    paths = [c.path.split("/")[-1] for c in extract.shell_writes(command, str(project), want=lambda p: p.endswith("b.md"))]
    assert paths == ["b.md"]
