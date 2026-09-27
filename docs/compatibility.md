# Host support

Checked 2026-09-27 for release 0.4.0. Distinguish installed components, fixture
coverage and observed live behavior. Python 3.9+; Windows through WSL.

| Route | Skills | Session voice | Pre-write blocking | Warnings | Reply check |
|---|---|---|---|---|---|
| Claude Code plugin | packaged; manifest validated | adapter covered | adapter covered; earlier 0.3.0 observations, see release evidence | context adapter covered | Stop, strict block |
| Codex plugin | packaged | adapter covered | fixture coverage; live enforcement unconfirmed | context adapter covered; live unconfirmed | Stop fixture coverage |
| Cursor plugin | packaged | sessionStart fixture coverage | fixture coverage; live unconfirmed | pre-tool delivery not guaranteed; use checker | not packaged |
| Standalone unwordy skill | portable instructions | reads profile on use | none | model guidance only | none |
| Local checker | not applicable | voice command | exit status independent of host | terminal/JSON | not applicable |

A release smoke-test result is recorded in [release evidence](release-evidence.md).
No claim of end-to-end enforcement follows from validating a manifest.

## Codex

Review and trust plugin hooks in `/hooks`. A user or managed configuration can
disable hooks. Current official docs describe Bash aliases for exec_command,
Edit/Write aliases for apply_patch, MCP events and deny JSON. See
[Codex hooks](https://learn.chatgpt.com/docs/hooks).
Four earlier exec attempts recorded no invocation, including a restating
comment written through. They are evidence of an unresolved integration path,
not proof that Codex lacks hooks. An interactive TUI smoke check remains useful.
Git commit tests may hit the workspace sandbox before a text rule; use a
message-file check first to distinguish those failures.

## Cursor

Local plugin imports can be disabled by organization policy. Permission hooks
receive allow/deny results; soft findings return allow. Cursor documentation
only guarantees model feedback on denial for preToolUse. The plugin does not
pretend that warnings are delivered. See [Cursor hooks](https://prod.cursor.com/docs/hooks).
The checker remains available regardless of plugin loading.

## Live smoke checklist

In a disposable repo, start a fresh session with the current version. Confirm
voice load, then propose a comment with `rule.H4: block`, an agent attribution
trailer, a PR with its required template and an MCP title. Inspect host logs and
actual tool result. Record host/version, date, payload route and observed denial.
Restore a clean warn profile and confirm valid prose can pass. For Cursor also
confirm soft findings allow; do not infer warning delivery from permission allow.
