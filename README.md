# unwordy

A plugin for Claude Code, Codex and Cursor that makes your coding agent write
like a developer on your team: comments only where the code cannot say why,
commits and PRs that fit on one screen, tracker replies that answer the
question. Deterministic hooks deny AI attribution trailers, `## Summary`
scaffolding and comments that restate the code before the tool call runs, so
the slop never reaches the diff.

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

The commit above is not a suggestion the agent can ignore. The hook denies the
call before git runs and hands the agent three lines:

```text
unwordy H1: attribution in the commit message (Co-Authored-By: Claude). Remove it and commit again.
unwordy S2: 'comprehensive' in the commit message. Use a plain word.
unwordy S6c: opener 'This commit adds'. Start with the change itself.
```

The agent writes the second version instead. No model call is involved on the
way: the rules are regular expressions with ids you can look up.

## Install

```
/plugin marketplace add assaio/unwordy
/plugin install unwordy@unwordy
/unwordy:setup
```

Python 3.9 or newer, standard library only. No account, no build step, no
runtime dependency. `/unwordy:setup` writes a profile and prints its path;
everything else happens on its own from the next session.

Cost: **~281 always-loaded tokens** as reported by
`claude plugin details unwordy` (skill listings), plus about 260 tokens of
style text injected at the start of each session. Hooks cost zero model
tokens: they are Python scripts that return a decision.

## How it works

| Layer | When | Cost |
|---|---|---|
| Style profile injected as context | every session start, and after `/compact` | ~260 tokens |
| Skills (`setup`, `sync`, `rewrite`, `write`) | when you or the agent invoke them | listing ~281 tokens, body on invoke |
| Hooks on `Edit`/`Write`, `Bash`, MCP calls, `Stop` | every matching tool call | zero tokens |

Hard rules (H1-H4) deny the tool call with a one-line reason and the agent
rewrites. Soft rules (S1-S7) warn by default; `strict: block` makes them deny
too, `strict: off` silences them. Nothing denies forever: after two denials of
the same rule on the same target in one session, that rule drops to a warning.

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

Every session opens with the resolved profile, about 260 tokens. With the
default `senior` preset and no profile file anywhere, that is:

```text
Writing style the user set with unwordy (preset senior, built-in default):

Write like a developer on this team, not an assistant. Short beats complete.
Code comments only where the code cannot say why: a constraint, an invariant,
a trap, an external contract. One line, timeless, no references to tasks,
tickets, sessions or what you just changed. Never restate the code. If the
repo defines comment or commit conventions (CLAUDE.md, AGENTS.md,
CONTRIBUTING, commitlint), those win over this style.
Commits: imperative subject, body only when the why is not obvious.
No attribution trailers, no emoji, no em dashes, no bold-label bullets, no
headers in anything under a screen, no "summary of changes".
Replies: answer first, one idea per sentence, plain words.
In trackers and review threads, write in the thread's language and register.

Dry, direct, why not what. Commit body when the reason matters.
PR body: what, why, risk, how tested, up to twelve lines, no headers. Point
at file and line instead of describing code.
```

The last three lines are the preset's voice; a body in your own profile
replaces them.

**When a rule has denied twice** (the loop guard)

Nothing denies forever. After two denials of the same rule on the same target
in one session, the third answer is a warning and the call goes through:

```text
unwordy H2c: code comment describes the edit, not the code (Updated for PROJ-142). Say why the code is this way, or delete it. Passed as a warning after two denials.
```

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

When the repository already governs commit messages, with `commitlint.config.*`,
`.commitlintrc*`, a `commitlint` key in `package.json`, a `commit.template` in
git config or a `.gitmessage` file, the subject-length check (S5a) and the
opener check (S6c) skip commits and leave the format to those rules.

Presets: `lazy` (fewest words that still work), `senior` (dry, why not what,
the default), `qa` (steps, expected, actual, environment), `lead` (brief and
warm), `formal` (complete sentences, audit friendly), `custom` (learned from
your own writing by `/unwordy:setup`).

## Turning it down or off

| Want | Do |
|---|---|
| Silence one rule | `disable: S1, S3` in the profile; `disable: H2d` for one pattern of a rule |
| Only hard rules | `strict: off` |
| Make everything deny | `strict: block` |
| Skip paths | `ignore: vendor/**, docs/**` |
| Keep ticket ids in comments | `allow_ticket_refs: true` |
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

## Codex

The same repository is a Codex plugin:

```
codex plugin marketplace add assaio/unwordy
codex plugin add unwordy@unwordy
```

Codex installs the plugin under `~/.codex/plugins/cache/unwordy/` and lists
the skills as `unwordy:rewrite` and `unwordy:write`. `unwordy:setup` and
`unwordy:sync` are kept out of the model's list (`allow_implicit_invocation:
false`), so only you invoke them, as in Claude Code. Plugin hooks run only
after you review them once with `/hooks`. The hook contract is the same as
Claude Code's: `Bash` and `apply_patch` (matched as `Edit|Write`) on
`PreToolUse`, MCP tools, `SessionStart` with the same sources, `Stop` with
`stop_hook_active` and `last_assistant_message`, the same deny JSON, and
`CLAUDE_PLUGIN_ROOT` set for plugin hooks.

Checked against Codex 0.154 without a model call: the marketplace add and
install from this repo, the skill listing the model sees, and the manifests.
Still to run in a live Codex session: the voice at session start, the H4
denial on `apply_patch` and the H1 denial on `git commit`; the exact commands
are in `CONTRIBUTING.md`.

Without the plugin, `/unwordy:sync` from Claude Code writes the voice block
into `~/.codex/AGENTS.md` and offers to install the hook entries into
`~/.codex/hooks.json`.

## Cursor

The same repository is a Cursor plugin (`.cursor-plugin/plugin.json`). Until
it is on the Cursor marketplace, copy it into `~/.cursor/plugins/local/unwordy`
and reload the window; Customize then lists the four skills and two hooks. A
`sessionStart` hook injects the voice as session context and
`beforeShellExecution` runs the commit, PR and shell-write lints, answering in
Cursor's own `permission` shape. File edits are not intercepted in Cursor:
its edit tools do not pass through a hook that can deny before the write.

Two other routes exist. `/unwordy:sync` from Claude Code writes
`.cursor/rules/unwordy.mdc` with `alwaysApply: true` and offers the same two
hook entries for `~/.cursor/hooks.json`. And Cursor imports Claude Code hooks
from `.claude/settings.json` when third-party imports are on, but it matches
them against its own tool names (`Shell`, not `Bash`), so entries have to be
written for Cursor anyway. The plugin folder is the simplest of the three:
one copy, nothing to edit.

Unverified, because Cursor ships without a CLI here: whether
`${CURSOR_PLUGIN_ROOT}` expands inside a plugin hook command and whether an
empty hook response passes. `CONTRIBUTING.md` has the click-through checklist.

## What it does not do

- Hooks read `Edit`, `Write`, `NotebookEdit`, `apply_patch`, shell commands
  and MCP calls. A file written from the shell with `cat > file <<EOF`, `tee`,
  `echo` or `printf`, also through `>>` or a pipe, is linted like an edit.
  `sed -i` and other in-place editors are not followed.
- Hooks never rewrite text. They deny or warn; the agent rewrites.
- No AI-detection score. The rules are regular expressions with ids you can read.
- Prose outside the developer workflow is not the target; use a humanizer for that.
- Windows is supported only through WSL.

## Development

`CONTRIBUTING.md` has the dev setup, the test command, the eval suite and
the manual smoke tests. MIT licensed. Sibling project from the same
maintainer: [assaio](https://github.com/assaio/assaio), offline analytics for
what AI coding agents cost per project.
