---
name: init
description: Build a personal or team unwordy profile from answers and selected examples of commits, PRs, review comments, messages or documentation.
disable-model-invocation: true
allowed-tools: Read Write Bash(git *) Bash(sh *) AskUserQuestion
---

Set up a custom voice. Read `skills/setup/SKILL.md` from this plugin and follow
its wizard, profile format and preview step. The user's examples are optional.

Before reading history, ask whether to inspect local commits. If yes, run
`sh "${CLAUDE_PLUGIN_ROOT}/bin/unwordy" examples --limit 10` to list only
subjects and IDs. Ask which IDs to use, then run `examples --show ID...` for
those IDs only. For PRs, review threads, tracker messages and email, ask for
pasted examples or paths. Do not search accounts or mailboxes without the
user choosing those sources. Do not store raw samples or put private names,
addresses or links in the profile.

Extract short rules per surface: code comments, commits, PRs, review/tracker
comments and replies. Repo and team conventions win over the personal voice.
Preview the same fictional change as a commit, PR and reply. Let the user
adjust before writing the profile. Keep the body under 250 tokens.
