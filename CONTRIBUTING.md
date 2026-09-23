# Contributing

unwordy is a Python 3.9+ plugin with no runtime dependencies. The same
`skills/` directory serves Claude Code, Codex and Cursor. Host adapters live
in `unwordy/hook.py`; the standalone checker lives in `unwordy/cli.py`.

## Development

```sh
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/pytest -q
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/plugin.json
git diff --check
```

Tests feed host JSON to `hooks/run.sh` and check the output and exit code.
Fixtures under `tests/fixtures/slop/` and `tests/fixtures/clean/` pair a
matching example with a clean one. Tests run offline and make no model calls.

When adding a rule, give it a stable id, write a one-line reason that tells
the agent what to do, add matching and clean cases, and update the README rule
table. Hard rules (`H`) block unless a profile explicitly allows them. Soft
rules (`S`) follow `strict` in the profile.

## Manual host checks

Use a disposable repository and install the current plugin version. Test a
fresh session after changing hooks, skills or manifests. Installed copies are
cached by version, so reinstall after local changes.

| Host | Check |
|---|---|
| Claude Code | `claude plugin list --json` shows no errors; session voice loads; a restating code comment is denied on `Edit` and `Write`; a Claude co-author trailer is denied on `Bash`; `/unwordy:init`, `/unwordy:setup lazy` and `/unwordy:sync` work. |
| Codex | Skills appear in `codex debug prompt-input hello`; trust plugin hooks through `/hooks` in the TUI; check that `apply_patch` and shell tool calls reach the hook and can be denied. |
| Cursor | The plugin lists six skills and four hook events; `sessionStart` loads the voice; shell, `Write` and MCP text calls reach their hooks and can be denied. |

Codex and Cursor hook enforcement has fixture coverage but has not been
confirmed in a live session. Treat the local checker as the reliable route
until those smoke tests pass. Codex plugin hooks require trust in `/hooks`;
see the [Codex hooks documentation](https://developers.openai.com/codex/hooks).

The checker can run independently of a host:

```sh
sh bin/unwordy check --staged
sh bin/unwordy check --diff HEAD
sh bin/unwordy check --message-file .git/COMMIT_EDITMSG --surface commit
sh bin/unwordy doctor
```

For model-level checks, `evals/` contains five `claude plugin eval` cases.
They cover commit messages, PR bodies, code comments, tracker comments and
replies. They consume agent turns on your own account.
