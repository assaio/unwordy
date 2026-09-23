---
name: code
description: Load before editing code to follow the repository's naming, typing, comment, test and documentation conventions.
user-invocable: false
---

Before editing, read the applicable `AGENTS.md` or `CLAUDE.md`, the nearest
implementation and test files, and the project's formatter, linter and type
checker configuration. If available, `sh "${CLAUDE_PLUGIN_ROOT}/bin/unwordy"
conventions --path <target>` lists candidates; read the relevant files, not
just their names. Prefer the existing pattern unless the task calls for a
change. Keep the diff limited to the task.

Add a comment only for a constraint or invariant the code cannot express.
Check every new or edited docstring and documentation claim against the
current code. Say that a check passed only when you ran it and saw its result.
Before finishing, inspect the diff for unrelated edits, repeated explanations
and stale comments.
