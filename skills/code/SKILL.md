---
name: code
description: Load before editing code to follow the repository's naming, typing, comment, test and documentation conventions.
user-invocable: false
---

Read applicable AGENTS.md or CLAUDE.md, nearby implementation and tests, and
formatter, linter and type configuration. Prefer existing patterns unless the
task calls for change. Keep the diff limited to the task.

Comments explain constraints, contracts and traps. Keep necessary public API
docs, algorithm steps and useful workaround references; remove restatement.
Check documentation claims against current code. Report checks as passed only
when actually run. Inspect the final diff for unrelated changes and stale prose.
