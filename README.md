# unwordy

**Make your coding agent write like a developer, not like a chatbot.**

unwordy is a plugin for Claude Code, Codex and Cursor that cleans up the text
an AI agent writes around your code: commit messages, pull request
descriptions, code comments and tracker replies. It does not score your prose
and it does not send it to a second model. In Claude Code, hooks can deny a
matching tool call before it writes. Codex and Cursor hook enforcement still
need live verification; see their sections below.

```diff
- feat: Implement comprehensive retry mechanism for sync worker
-
- This commit adds a robust retry mechanism to handle transient failures
- seamlessly. Changes include:
- - Added retry logic with exponential backoff
- - Updated the worker configuration
-
- Co-Authored-By: Claude <noreply@anthropic.com>
+ sync: retry webhook delivery three times
+
+ The webhook host returns 502 for a few seconds after a deploy. Backoff is
+ 1s, 2s, 4s; after that the event id goes to the dead letter log.
```

With the Claude Code hook active, the first commit command is denied before
git runs and the agent receives three lines:

```text
unwordy H1: attribution in the commit message (Co-Authored-By: Claude). Remove it and commit again.
unwordy S2: 'comprehensive' in the commit message. Use a plain word.
unwordy S6c: opener 'This commit adds'. Start with the change itself.
```

The agent writes the second version instead. No model call is involved on the
way: every rule is a regular expression with an id you can look up, switch off
or point at a single surface.

## Why

An agent that writes `// This function returns the user`, opens a pull request
under `## Summary` and `## Test plan` headers and signs the commit
`Co-Authored-By: Claude` is not wrong. It is the house style of a chatbot,
the thing people have started calling AI slop, and a reviewer pays for it on
every diff.

Writing your conventions into `CLAUDE.md` or `AGENTS.md` helps until it does
not: it is advice competing for attention with the task, and it goes quiet
three turns into a long session. For tool calls it can intercept, an active
hook checks the proposed text on each call with regular expressions.

## Install

```
/plugin marketplace add assaio/unwordy
/plugin install unwordy@unwordy
/unwordy:init
```

Python 3.9 or newer, standard library only. No account, no build step, no
runtime dependency. `/unwordy:init` asks for a preset or examples of your own
writing, previews the result, then writes a profile. `/unwordy:setup lazy`
switches directly to a preset;
everything else happens on its own from the next session.

`claude plugin details unwordy` reports the current skill-listing cost. The
profile adds a short session instruction. The checks themselves call no model.

## How it works

| Layer | When | Cost |
|---|---|---|
| Style profile injected as context | every session start, and after `/compact` | short profile |
| Skills (`init`, `setup`, `sync`, `code`, `rewrite`, `write`) | when you or the agent invoke them | listing on startup, body on invoke |
| Hooks on `Edit`/`Write`, `Bash`, MCP calls, `Stop` | every matching tool call | no model call; brief feedback on a finding |

The skills are Agent Skills in the portable format that Claude Code,
Codex and Cursor all read, so one directory serves three hosts.

Hard rules (H1-H4) deny the tool call with a one-line reason and the agent
rewrites. Soft rules (S1-S7) warn by default; `strict: block` makes them deny
too, `strict: off` silences them. A soft rule blocked twice on the same target
falls back to a warning; hard rules keep denying. `attribution` can make H1
warn or allow where a repository requires disclosure.

## Without and with unwordy

Three layers change what the agent writes and only one of them can stop a
call: the voice injected at session start, the skills, and the hooks. Each
example below names the layer that did the work. Every quoted message is
literal hook output.

**Code comment** (denied by the hooks)

```diff
- # Step 1: Check if payload is empty
- # Updated for PROJ-142
  def parse(payload):
-     # Return None if empty
+     # The webhook host sends an empty body instead of a 404.
      if not payload:
          return None
```

```text
unwordy H2b: step number in a code comment (Step 1: Check if payload is empty). Say why the code is this way, or delete it.
unwordy H2c: code comment describes the edit, not the code (Updated for PROJ-142). Say why the code is this way, or delete it.
```

**A file written from the shell** (denied by the hooks)

A heredoc is not a way around the comment rules. The same lints run on what
`cat`, `tee`, `echo` and `printf` send into a file.

```diff
  cat > user.js <<'EOF'
- // This function returns the user
  export function getUser(id) {
    return users[id];
  }
  EOF
```

```text
unwordy H4a: comment restates the code (This function returns the user). Delete it or say why.
```

**PR body** (hooks deny the attribution and the scaffolding, the voice writes
the rest)

```diff
- ## Summary
- This PR implements a retry mechanism for the sync worker.
- - **What:** adds retries with exponential backoff
- - **Why:** transient failures were causing data loss
- - **How:** the dispatcher wraps delivery
- ## Test plan
- - [x] Unit tests pass
-
- Generated with Claude Code
+ Retries webhook delivery three times with backoff (1s, 2s, 4s). The host
+ returns 502 for a few seconds after every deploy, and we were dropping
+ those events.
+
+ Risk: duplicate deliveries if the host answered late. The receiver is
+ idempotent on event id, see webhook/receiver.go:88.
+
+ Tested against staging with a forced 502, plus sync/retry_test.go.
```

```text
unwordy H1: attribution in the PR text (Generated with Claude). Remove it and try again.
unwordy S6a: '## Summary' plus '## Test plan' template in the PR text. Say what, why and how tested in plain lines.
```

**Tracker comment** (the voice, no hook fires)

Pleasantries in a tracker comment break no rule. They do not survive the
style profile either, because the voice loaded at session start says to
answer first and stop there.

```diff
- Thanks for the detailed review! Great catch on the retry logic. I've gone
- ahead and updated the implementation as requested. Let me know if you have
- any other feedback!
+ Moved the retry into the dispatcher so the receiver stays pure. Cap is 3
+ attempts, config in sync.toml:12.
```

The hooks do read tracker comments, for attribution, em dashes, banned words
and length, whether the comment goes out through `gh`, `glab` or an MCP tool
such as Jira or Linear:

```text
unwordy H1: attribution in the comment (Generated with Claude). Remove it and try again.
unwordy S5b: the comment is 15 lines, over 12. Cut it to what a reviewer needs.
```

**Reply** (the voice, plus the Stop hook under `strict: block`)

```diff
- The retry limit is a configuration option that controls how many times the
- worker will attempt delivery before giving up. It is defined in config.toml
- under the sync section. By default it is set to 3 attempts, and the range
- is 1 to 10. The backoff between attempts doubles each time, starting at one
- second. (... nine more lines ...)
- Let me know if you'd like me to walk you through the backoff calculation.
+ Yes, `sync.retry_limit` in config.toml. Default 3, range 1 to 10.
```

```text
unwordy S7a: 13-line reply to a yes/no question. Answer again in a few lines.
unwordy S7b: closing offer (Let me know if you'd like me to walk you through the back...). End when the answer ends.
```

Replies are the one surface nothing can deny before the fact: the Stop hook
sees the answer only once it exists, so it asks for a second one. It stays
silent unless the profile sets `strict: block`, and it never blocks twice in
a row.

**Session start** (the voice)

Every session receives the resolved profile. The `senior` default is brief and
direct; `/unwordy:init` can replace it with rules drawn from examples you
select. Repo instructions take precedence. The `code` skill asks the agent to
read nearby implementation, tests and type configuration before editing.

**Repeated denials**

After two denials of the same soft rule on the same target, the third attempt
gets a warning so a model cannot loop forever. Hard rules keep denying until
the text changes or the repository explicitly disables the rule.

## Rules

Every denial and warning names its rule, so you can search for it and turn it
off. A rule with several patterns numbers them (`H2d`, `S5b`); the reason
prints that sub-id, and `disable:` takes either the family (`H2`) or one
sub-id (`H2d`).

| id | Effect | Surface | Catches |
|---|---|---|---|
| H1 | deny | everything | attribution: `Co-Authored-By: Claude`, `Generated with ...`, `Claude-Session:`, the robot emoji, agent noreply addresses |
| H2 | deny | code comments | task leakage: `per the ticket` (H2a), `Step 1:` (H2b), `Updated this to ...` (H2c), ticket ids like `PROJ-142` (H2d) |
| H3 | deny | code comments, Markdown | chat leakage: `Here's the ...`, `Let me ...`, `As requested`, `Certainly` |
| H4 | deny | code comments | restating code: `This function returns the user` (H4a), `// Increment counter` above `counter++` (H4b) |
| S1 | warn | all text | em dash, spaced en dash |
| S2 | warn | all text | words from the banned list (English plus short Polish and German lists) |
| S3 | warn | code | more than 30% comment lines in an edit that adds 8 or more code lines |
| S4 | warn | code | docstring longer than the body it documents, over three lines |
| S5 | warn | commits, PRs, comments | subject over 72 characters (S5a), body over 12 lines (S5b), over 6 bullets (S5c), 3+ headers (S5d), 4+ bold-label bullets (S5e), emoji in a header (S5f) |
| S6 | warn | commits, PRs | `## Summary` plus `## Test plan` scaffolding (S6a), `Summary of changes` (S6b), `This PR adds ...` (S6c) |
| S7 | reply check | replies | over 12 lines in answer to a yes/no or one-fact question (S7a), a line opening with `Let me know if ...` or `Feel free to ...` (S7b). Only under `strict: block` |

Exempt from the comment rules: license headers, shebangs, encoding lines,
linter directives (`noqa`, `eslint-disable`, `@ts-`, `type:`, `pragma`,
`nolint`), generated files, `tests/fixtures/**`, `*.snap`, lock files, and
anything in the profile's `ignore` list.

## The profile

One Markdown file with flat frontmatter, resolved in this order:
`$UNWORDY_STYLE`, then `.unwordy.md` walking up to the git root, then
`$XDG_CONFIG_HOME/unwordy/style.md` (default `~/.config/unwordy/style.md`),
then the built-in `senior` preset. The first file found wins.

```markdown
---
preset: senior            # lazy | senior | qa | lead | formal | custom
strict: warn              # warn | block | off   (soft rules only)
language: auto            # auto | en | pl | ...
banned_words: delve, leverage, seamless, robust, comprehensive
allow_ticket_refs: false
attribution: block      # block | warn | allow
commit.attribution: block
max_subject: 72
max_pr_body_lines: 12
max_bullets: 6
ignore: vendor/**, **/*.generated.*
disable: S1, S3
enabled: true
---
Dry, direct, explains why not what. Commit body only when the reason matters.
```

A body in the file replaces the preset text. Without a body you get the
preset, and preset wording improves with each release. `banned_words`
replaces the built-in list rather than extending it. The three limits take a
surface prefix for one surface only: `pr.max_body_lines: 20`,
`commit.max_subject: 60`, `comment.max_bullets: 10`; the flat key stays the
default for the others.
`attribution` applies to H1; `commit.attribution`, `pr.attribution`,
`comment.attribution`, `code.attribution` and `docs.attribution` can override
it. Use `warn` or `allow` if your project requires AI disclosure. This
controls text checks, not Git's cryptographic commit signing.

When the repository already governs commit messages, with `commitlint.config.*`,
`.commitlintrc*`, a `commitlint` key in `package.json`, a `commit.template` in
git config or a `.gitmessage` file, the subject-length check (S5a) and the
opener check (S6c) skip commits and leave the format to those rules.

Presets: `lazy` (fewest words that still work), `senior` (dry, why not what,
the default), `qa` (steps, expected, actual, environment), `lead` (brief and
warm), `formal` (complete sentences, audit friendly), `custom` (built from
answers and selected examples by `/unwordy:init`).

## Turning it down or off

| Want | Do |
|---|---|
| Silence one rule | `disable: S1, S3` in the profile; `disable: H2d` for one pattern of a rule |
| Only hard rules | `strict: off` |
| Make everything deny | `strict: block` |
| Skip paths | `ignore: vendor/**, docs/**` |
| Keep ticket ids in comments | `allow_ticket_refs: true` |
| Require AI disclosure in commits | `commit.attribution: allow` |
| Off in this repo | `enabled: false` in `.unwordy.md`, or `/unwordy:setup off` |
| Off for one command | `UNWORDY_OFF=1 <command>` |
| Off everywhere | `/plugin uninstall unwordy` |

## For a team

Commit `.unwordy.md` in the repository root. It wins over each developer's
global profile, so everyone's agent writes the same way in that repo:

```markdown
---
preset: qa
max_subject: 60
ignore: vendor/**, **/*.pb.go
---
Bug reports: steps, expected, actual, environment. No adjectives.
Commit subject: <area>: <imperative>, under 60 characters.
```

Developers who do not have unwordy installed are unaffected by the file, and
`/unwordy:sync` writes the same voice into `AGENTS.md`, which most other
agents read.

`templates/` holds three commented starting points: `team-strict` (senior
voice, soft rules deny, 60-character subjects), `team-qa` (steps, expected,
actual, ticket ids allowed) and `team-enterprise` (formal, English, audit
friendly). `/unwordy:setup --project team-strict` copies one into
`.unwordy.md`.

## Check before review

The local checker covers routes a host hook cannot see. Run it from a checkout
of unwordy, or use the absolute path to its `bin/unwordy` script:

```sh
sh /path/to/unwordy/bin/unwordy check --staged
sh /path/to/unwordy/bin/unwordy check --message-file .git/COMMIT_EDITMSG --surface commit
sh /path/to/unwordy/bin/unwordy check --diff origin/main --commits origin/main
sh /path/to/unwordy/bin/unwordy doctor
```

`--staged` checks the index; `--diff BASE` checks tracked worktree changes;
`--commits BASE` checks commit messages and authors in `BASE..HEAD`. The
checker exits 1 for a block, 0 for warnings or clean text, and 2 on an error.
Use `--fail-on-warn` for a stricter CI gate and `--json` for tooling. A Git
`commit-msg` hook can call the second command with its first argument in
place of `.git/COMMIT_EDITMSG`; a pre-commit hook can call `--staged`. Install
those hooks only in repositories whose owners want them.

`sh /path/to/unwordy/bin/unwordy conventions --path src/file.py` lists
nearby instructions and configuration. `examples` lists your recent commit
subjects and IDs; `examples --show ID...` reveals only the commits you pick
for `/unwordy:init`. Pasted text and file paths also work for PRs, review
comments and messages. Raw samples stay out of the generated profile.

## Codex

The same repository is a Codex plugin:

```
codex plugin marketplace add assaio/unwordy
codex plugin add unwordy@unwordy
```

Codex installs the plugin under `~/.codex/plugins/cache/unwordy/` and lists
`unwordy:code`, `unwordy:rewrite` and `unwordy:write` for model invocation.
`init`, `setup` and `sync` are reserved for explicit invocation through their
`allow_implicit_invocation: false` policy. The older `rewrite` and `write`
listings were verified on Codex 0.155; the new skills need a live check.

Current Codex documentation says lifecycle hooks are enabled by default. It
skips plugin hooks until you review and trust their current definition in
`/hooks` in the TUI. Check `codex features list` if hooks do not run; a user
or managed configuration can disable them. Installing the plugin alone does
not enforce any rule.

The hook contract is written to match Claude Code's: `Bash` and `apply_patch`
(matched as `Edit|Write`) on `PreToolUse`, MCP tools, `SessionStart` with the
same sources, `Stop` with `stop_hook_active` and `last_assistant_message`, the
same deny JSON, and `CLAUDE_PLUGIN_ROOT` set for plugin hooks, which Codex
still sets next to its own `PLUGIN_ROOT`.

Not verified: no unwordy hook has yet been observed firing inside Codex. Four
`codex exec` runs, including runs with `--enable hooks` and
`--dangerously-bypass-hook-trust`, produced no hook invocation, with the
payload logged from the installed copy; the `apply_patch` in that test wrote
the restating comment straight through. The trust step is interactive, so the
remaining path to check is a TUI session after `/hooks`. `CONTRIBUTING.md` has
the commands and what each one printed.

Two more things to know before you test it by hand: Codex's `workspace-write`
sandbox denies writes inside `.git`, so a `git commit` test needs
`--sandbox danger-full-access` or an approval, and it will fail on the
sandbox rather than on a rule.

Without the plugin, `/unwordy:sync` from Claude Code writes the voice block
into `~/.codex/AGENTS.md` and offers to install the hook entries into
`~/.codex/hooks.json`.

## Cursor

The same repository is a Cursor plugin (`.cursor-plugin/plugin.json`). Until
it is on the Cursor marketplace, copy it into `~/.cursor/plugins/local/unwordy`
and reload the window. It declares `sessionStart`, `beforeShellExecution`,
`preToolUse` for Write, and `beforeMCPExecution`. The adapters return Cursor's
`permission` shape. These paths pass fixture tests; a live Cursor session has
not yet confirmed that the host invokes them with the expected payload.

Two other routes exist. `/unwordy:sync` from Claude Code writes
`.cursor/rules/unwordy.mdc` with `alwaysApply: true` and offers the same hooks
hook entries for `~/.cursor/hooks.json`. And Cursor imports Claude Code hooks
from `.claude/settings.json` when third-party imports are on, but it matches
them against its own tool names (`Shell`, not `Bash`), so entries have to be
written for Cursor anyway. The plugin folder is the simplest of the three:
one copy, nothing to edit.

`CONTRIBUTING.md` has the live smoke-test checklist. The local `check` command
works independently of Cursor's hook loading.

## What it does not do

- Hooks read `Edit`, `Write`, `NotebookEdit`, `apply_patch`, shell commands
  and MCP calls. A file written from the shell with `cat > file <<EOF`, `tee`,
  `echo` or `printf`, also through `>>` or a pipe, is linted like an edit.
  `sed -i` and other in-place editors are not followed.
- Hooks never rewrite text. They deny or warn; the agent rewrites.
- Regexes cannot establish that code or documentation is factually correct.
- The checker only sees tracked diffs or staged changes, not untracked files.
- No AI-detection score. The rules are regular expressions with ids you can read.
- Prose outside the developer workflow is not the target; use a humanizer for that.
- Windows is supported only through WSL.

## Development

`CONTRIBUTING.md` has the dev setup, the test command, the eval suite and
the manual smoke tests. MIT licensed. Sibling project from the same
maintainer: [assaio](https://github.com/assaio/assaio), offline analytics for
what AI coding agents cost per project.
