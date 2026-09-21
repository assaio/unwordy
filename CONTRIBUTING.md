# Contributing

## Layout

```
plugin.json         portable manifest (agent-plugins.org) with the Codex extension
.claude-plugin/     plugin.json, marketplace.json          .agents/plugins/  Codex marketplace
.codex-plugin/      Codex compatibility manifest          .cursor-plugin/   Cursor manifest
hooks/              hooks.json (Claude Code and Codex), codex/cursor templates for sync, run.sh
skills/             setup, sync, rewrite, write; setup and sync carry agents/openai.yaml
unwordy/            Python package, standard library only
  profile.py  resolution order, frontmatter parser, presets
  extract.py  added lines, comment scanner, shell messages, MCP fields
  lint.py     rules H1..H4, S1..S7
  state.py    loop guard      render.py  marker blocks      hook.py  entry point
  presets/    core.md plus one file per preset
output-styles/      optional, not forced
tests/              pytest, fixtures/slop and fixtures/clean
```

## Dev setup

```
python3 -m venv .venv
.venv/bin/pip install pytest
.venv/bin/pytest
```

Python 3.9 is the minimum and what the suite runs on. `pytest` is the only
dev dependency; users need nothing beyond Python. Tests are offline and
deterministic: no model calls, no network, no `claude -p`. Hook behaviour is
tested by feeding JSON on stdin to `hooks/run.sh` and asserting on stdout and
the exit code.

## Before a release

```
claude plugin validate --strict .                          # marketplace manifest
claude plugin validate --strict .claude-plugin/plugin.json  # plugin, hooks, skills
claude plugin details unwordy                               # always-on tokens, keep under 600
```

The first command only checks `marketplace.json` when the directory holds one,
so run the second as well.

## Adding a rule

1. Give it the next free id. Hard rules (`H`) deny, soft rules (`S`) follow
   `strict` in the profile. A new pattern inside an existing rule gets the
   next letter (`H2e`); the family id stays what `disable:` and the loop guard
   count on.
2. One line of reason, in the imperative, naming what to do instead.
3. Add a pair of fixtures: `tests/fixtures/slop/<id>.<surface>.<ext>` and the
   same name under `clean/`. The clean fixture must produce no findings at all.
4. Document it in the README rule table.

## Evals

`evals/` holds one `claude plugin eval` case per surface: `commit-message`,
`pr-body`, `code-comment`, `tracker-comment` and `reply`. Every grader is a
`regex` over the final message or a `tool_used` check for the `write` skill,
so a run pays for agent turns only, no judge calls. A full pass is
5 cases x 3 runs x 2 arms = 30 agent runs on your own credentials:

```bash
claude plugin eval . --trust-plugin            # both arms, prints WITH, W/OUT and the delta
claude plugin eval . --ablation none --runs 1  # 5 runs, while editing graders
```

The regexes mirror the hard rules and the length limits: no attribution, no
`## Summary` scaffolding, no bold-label bullets, no restating or task-bound
comments, answer first, under thirteen lines. `results/` is ignored by git.

Last recorded run, `--ablation none --runs 1`, five cases in 31 seconds for
$0.43:

| Case | Score | Graders |
|---|---|---|
| code-comment | 1.00 | 4 of 4 |
| commit-message | 1.00 | 5 of 5, `write` skill fired |
| pr-body | 1.00 | 6 of 6, `write` skill fired |
| reply | 1.00 | 4 of 4 |
| tracker-comment | 1.00 | 6 of 6, `write` skill fired |

No grader failed on good output, which is what the short form is for. The
no-plugin arm has not been run, so there is no WITH minus W/OUT delta to
quote; that needs the full pass and 30 agent runs.

## Manual smoke test

Run this against a real session after changing hooks, skills or the manifest.
It costs a handful of model turns. The run below is the one that shipped
v0.1.0, with the numbers refreshed for v0.2.0; each command is followed by
what it printed.

```bash
# 1. scratch repo
rm -rf /tmp/unwordy-smoke && mkdir -p /tmp/unwordy-smoke && cd /tmp/unwordy-smoke
git init -q
printf 'export function getUser(id) {\n  return users[id];\n}\n' > user.js
git add -A && git commit -qm init

# 2. install from the local marketplace, only for this repo
claude plugin marketplace add /path/to/unwordy --scope local
claude plugin install unwordy@unwordy --scope local
claude plugin details unwordy
#   Skills (4), Hooks (3) SessionStart, PreToolUse, Stop (harness-only)
#   Always-on: ~281 tok
```

The install copies the working tree into
`~/.claude/plugins/cache/unwordy/unwordy/<version>/` and pins it to the
version in `plugin.json`. After changing the plugin, reinstall it in the
scratch repo, otherwise the session keeps running the old copy:

```bash
claude plugin uninstall unwordy --scope local && claude plugin install unwordy@unwordy --scope local
```

Then a fresh session in that directory. Type each line and check the result.
The transcript below used `claude -p` with `--continue`, which is the same
session and the same hooks.

| Step | Type | Expect |
|---|---|---|
| Voice loads | `In one line: what writing style is loaded in this session, and which profile did it come from?` | names the preset and the profile source, for example `unwordy "senior" preset (built-in default)` |
| H4 denies | `Use Edit on user.js to add the line '// This function returns the user.' above getUser` | `unwordy H4: comment restates the code (This function returns the user.). Delete it or say why.` and the file is unchanged |
| H1 denies | `Run exactly: git commit -am "add user lookup" -m "Co-Authored-By: Claude <noreply@anthropic.com>"` | `unwordy H1: attribution in the commit message (Co-Authored-By: Claude). Remove it and commit again.` and no commit |
| Soft rule warns | `Use the Write tool to write notes.md with the line: We leverage the new schema and it is seamless.` | file is written, and the agent reports `PreToolUse:Write hook additional context: unwordy S2: 'leverage' in notes.md. Use a plain word.` |
| Setup writes a profile | `/unwordy:setup lazy` | writes `~/.config/unwordy/style.md` with `preset: lazy` and prints the path |
| Sync renders | `/unwordy:sync` | writes `AGENTS.md` and `.cursor/rules/unwordy.mdc`, lists the home-directory files it would write, and asks before writing them |
| Sync is idempotent | `/unwordy:sync` | reports both files unchanged; `md5 AGENTS.md` matches the previous run |

The block that `/unwordy:sync` writes must equal
`sh hooks/run.sh render` byte for byte:

```bash
cd /tmp/unwordy-smoke
CLAUDE_PLUGIN_ROOT=/path/to/unwordy sh /path/to/unwordy/hooks/run.sh render > /tmp/rendered.txt
diff <(cat AGENTS.md) /tmp/rendered.txt   # no output
```

## Skill and Stop hook run under -p

The paths the table above does not cover were run once with `claude -p` in the
same scratch repo, with the plugin reinstalled first. Each call started
`claude -p --setting-sources project,local --strict-mcp-config --mcp-config
'{"mcpServers":{}}' --permission-mode acceptEdits --output-format json`, so
no unrelated MCP servers or user-scope plugins loaded; follow-up turns added
`--continue`. Sixteen calls in total; the setup wizard alone takes nine.

| Path | Turns | Result |
|---|---|---|
| `/unwordy:setup custom` under `-p` | 9 | first reply: `No AskUserQuestion here, so one question at a time.` then scope, reply length, formatting, casing, warmth, language and samples one per turn, each with two or three sample outputs; `skip` for samples; a preview of a commit, a PR body and a tracker comment; `keep` wrote `.unwordy.md` with `preset: custom`, `strict: warn`, `language: en` and a five-line body, and offered `/unwordy:sync` because `.cursor/` exists |
| `/unwordy:rewrite <pasted tracker comment>` | 1 | returned the rewrite in a code block and `Dropped the closing offer and "as requested".`; it kept the word `robust`, which S2 would flag on the way out |
| `/unwordy:rewrite slop.py` | 1 | returned the file with every comment removed and said why; the file on disk was untouched |
| `/unwordy:rewrite --last` | 1 | rewrote its own four-paragraph reply from the previous turn, a third shorter, and named what it dropped |
| Stop hook, `strict: block`, `Is HTTP keep-alive on by default in HTTP/1.1, with ... over 25 lines?` | 2 | the first answer had 25 lines; the transcript shows `Stop hook feedback: unwordy S7a: 25-line reply to a yes/no question. Answer again in a few lines.`; the second answer was one paragraph and the turn ended, no loop |

Two earlier Stop attempts produced no block because the question was longer
than 25 words or did not end with `?`, which the S7a classifier requires. The
`unwordy:write` skill loaded on its own before both long answers.

The interactive wizard uses `AskUserQuestion` instead, which `-p` cannot
answer. To check it by hand in a normal session in the scratch repo:

1. `/unwordy:setup custom`: a question dialog for scope with three options,
   not a plain-text question.
2. Pick `this project`, then `custom`, then any answers; each step is a
   dialog with sample outputs as the option labels.
3. `skip` at the samples step, `keep` at the preview: `.unwordy.md` appears
   with `preset: custom` and the skill prints its path.
4. `/unwordy:setup lazy` afterwards switches `preset:` in that file and asks
   before dropping the custom body.

## The published install path

What a new user runs, checked against the published repository with no model
call. Both hosts install the tagged version and report it:

```bash
claude plugin marketplace add assaio/unwordy
claude plugin install unwordy@unwordy --scope local
claude plugin list --json          # enabled true, errors none
claude plugin details unwordy      # Skills (4), Hooks (3), always-on ~281 tok

codex plugin marketplace add assaio/unwordy
codex plugin add unwordy@unwordy
codex debug prompt-input hello | grep -o 'unwordy:[a-z]*:'
#   unwordy:rewrite:
#   unwordy:write:
```

Read `errors` from `claude plugin list --json`, not the inventory. A hook
file that fails to load leaves the plugin enabled and still counted as three
hooks in `details`, with every rule silent; only the JSON says so.

## Codex smoke test

Codex 0.154.0 with the repo registered as a local marketplace. The commands
below need no model; each one is followed by what it printed.

```bash
codex plugin marketplace add /path/to/unwordy
#   Added marketplace `unwordy` from /path/to/unwordy.
codex plugin list | head -6
#   Marketplace `unwordy`
#   /path/to/unwordy/.agents/plugins/marketplace.json
#   unwordy@unwordy  not installed
codex plugin add unwordy@unwordy
#   Installed plugin root: ~/.codex/plugins/cache/unwordy/unwordy/0.1.0
cd /tmp/unwordy-codex-smoke && codex debug prompt-input hello | grep -o 'unwordy:[a-z]*:'
#   unwordy:rewrite:
#   unwordy:write:
```

The last command renders the prompt the model sees. `setup` and `sync` are
missing from it on purpose: their `agents/openai.yaml` sets
`allow_implicit_invocation: false`, the Codex counterpart of
`disable-model-invocation`. With the `.agents/plugins/marketplace.json`
removed, Codex falls back to `.claude-plugin/marketplace.json` and prints the
same listing. Codex copies the whole directory into its cache, `.venv`
included, so install from a clean checkout when size matters.

The live part spends model turns on the Codex account. Plugin hooks run only
after `/hooks` in the TUI has trusted them once, or with
`--dangerously-bypass-hook-trust` for a single `codex exec`:

```bash
cd /tmp/unwordy-codex-smoke
codex exec --dangerously-bypass-hook-trust --sandbox read-only \
  "Answer in one line: what writing style instructions were loaded into this session, and which profile did they come from?"
codex exec --dangerously-bypass-hook-trust --sandbox workspace-write \
  "Using apply_patch only, add the line '// This function returns the user' above getUser in user.js. If the call is denied, do not retry; report the denial verbatim."
codex exec --dangerously-bypass-hook-trust --sandbox workspace-write \
  "Run exactly: git commit --allow-empty -m 'add user lookup' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'. If it is denied, do not retry; report the denial verbatim."
XDG_CONFIG_HOME=/tmp/unwordy-codex-home codex exec --dangerously-bypass-hook-trust --sandbox workspace-write '$unwordy:setup lazy'
```

Expected: the first names the `senior` preset and the built-in default; the
second reports `unwordy H4a: comment restates the code`; the third reports
`unwordy H1: attribution in the commit message` and `git log` shows no new
commit; the fourth writes `/tmp/unwordy-codex-home/unwordy/style.md` with
`preset: lazy`, which shows that a skill hidden from implicit invocation still
answers to an explicit mention.

What actually happened, Codex 0.155.1, four `codex exec` runs with the
installed copy's `hooks/run.sh` teeing its stdin to a log:

| Run | Flags | Result |
|---|---|---|
| session voice | `--sandbox read-only` | answered from its own profile, said the unwordy profiles "were available but not loaded"; no hook ran |
| `git commit` with attribution | `--sandbox workspace-write` | `fatal: Unable to create '.git/index.lock': Operation not permitted`; no hook ran |
| `git commit` with attribution | `--enable hooks --dangerously-bypass-hook-trust` | same sandbox error; no hook ran |
| `apply_patch` adding a restating comment | `--enable hooks --dangerously-bypass-hook-trust` | the patch applied, `// This function returns the user` landed in the file; no hook ran |

The log stayed empty in all four, and Codex's own log database holds no hook
entry for those sessions, so this is not a silent failure inside `run.sh`:
Codex never invoked it.

Two causes, one documented and one open:

- `features.hooks` is off by default. Without `[features] hooks = true` in
  `~/.codex/config.toml`, Codex loads no lifecycle hooks at all. The repo did
  not mention this before and it is the first thing to set.
- Even with the feature on and `--dangerously-bypass-hook-trust`, nothing
  fired in `codex exec`. The documented trust step is `/hooks` in the TUI,
  which is interactive, so the untested path is a TUI session after trusting
  the hooks once. Whether the bypass flag is meant to cover plugin-bundled
  hooks in `exec` is not something this repo can settle.

Also worth knowing: `--sandbox workspace-write` denies writes inside `.git`,
so the `git commit` cases above can never reach a hook decision. Use
`--sandbox danger-full-access` for that one, in a scratch repo.

To capture payloads on the next attempt, put a `tee -a <log>` in front of the
Python call in the *installed copy's* `hooks/run.sh`, never the repo's, and
compare what arrives with `tests/test_hook.py`. Reinstall afterwards
(`codex plugin remove unwordy@unwordy && codex plugin add unwordy@unwordy`)
so the patched copy is gone.

## Cursor smoke test

Cursor has no CLI on this machine, so this one is clicked through by hand.
Copy the plugin into Cursor's local plugin folder first (symlinks to a
directory outside that folder are skipped):

```bash
rm -rf ~/.cursor/plugins/local/unwordy
rsync -a --exclude .git --exclude .venv --exclude .pytest_cache --exclude __pycache__ \
  /path/to/unwordy/ ~/.cursor/plugins/local/unwordy/
```

Then in Cursor, with Settings, Agents, Third-Party Imports left at its default
(imports on), open `/tmp/unwordy-smoke` and go through the steps. Each step
says what to expect; the result column holds what happened on the last run.

| # | Do | Expect | Result |
|---|---|---|---|
| 1 | Developer: Reload Window, then open Customize | `unwordy` is listed with skills `setup`, `sync`, `rewrite`, `write` and hooks `sessionStart`, `beforeShellExecution`. Skills only means Cursor read the root `plugin.json` as an Agent Plugin instead of `.cursor-plugin/plugin.json` | unverified |
| 2 | New Agent chat: `In one line: what writing style instructions do you have for this session, and where do they come from?` | names the unwordy `senior` preset (the `sessionStart` hook's `additional_context`) | unverified |
| 3 | `Run exactly, do not retry, report the result verbatim: git commit --allow-empty -m 'add user lookup' -m 'Co-Authored-By: Claude <noreply@anthropic.com>'` | the command is denied and the chat shows `unwordy H1: attribution in the commit message (Co-Authored-By: Claude). Remove it and commit again.`; `git log` shows no new commit. This also proves `${CURSOR_PLUGIN_ROOT}` expanded, since a wrong path fails open and the commit goes through | unverified |
| 4 | `Run exactly: git status` | runs normally; an empty hook response passes | unverified |
| 5 | `Run exactly: printf '// This function returns the user\n' > note.ts` | denied with `unwordy H4a: comment restates the code` | unverified |
| 6 | Type `/` in the chat | the four skills appear; note the exact names Cursor shows (`/setup` or `/unwordy:setup`) | unverified |
| 7 | `/setup --project lazy` (or the name from step 6) | `.unwordy.md` with `preset: lazy` appears in the repo and the skill prints its path | unverified |
| 8 | `/sync` | `AGENTS.md` and `.cursor/rules/unwordy.mdc` are written; Customize lists the rule as Always | unverified |
| 9 | View, Output, pick the Hooks channel | no errors from the two unwordy hooks | unverified |
| 10 | Disable the plugin in Customize, write `.claude/settings.json` below into the repo, reload, repeat step 3 | the commit is denied the same way through Cursor's Claude Code hook import; if it goes through, that route needs the flat `permission` output or fails on the tool-name matcher | unverified |

`.claude/settings.json` for step 10, with the absolute path filled in:

```json
{
  "hooks": {
    "PreToolUse": [
      {
        "matcher": "Shell",
        "hooks": [
          {"type": "command", "command": "sh /absolute/path/.cursor/plugins/local/unwordy/hooks/run.sh pre-bash"}
        ]
      }
    ]
  }
}
```

Cursor matches imported Claude Code hooks against its own tool names, so the
matcher is `Shell`, and it accepts both the nested `hookSpecificOutput` and
the flat `permission` answer; unwordy answers flat when it sees `Shell`.

## Clean up after the smoke test

```bash
rm -rf /tmp/unwordy-smoke /tmp/unwordy-codex-smoke /tmp/unwordy-codex-home ~/.cursor/plugins/local/unwordy
claude plugin marketplace remove unwordy    # keep it if you develop against the local path
codex plugin remove unwordy@unwordy && codex plugin marketplace remove unwordy
rm -rf ~/.config/unwordy                    # only when the wizard created it for the test
rm -rf ~/.claude/plugins/data/unwordy-unwordy
```

The loop-guard state lives in
`${CLAUDE_PLUGIN_DATA:-~/.cache/unwordy}/state/<session>.json` and internal
errors are appended to `unwordy.log` beside it. Both are safe to delete; the
log is the first place to look when a hook stays silent.
