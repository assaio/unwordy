# unwordy: specification v0.1

Name: `unwordy`. Checked free on GitHub (handle and exact repo names), npm,
PyPI, crates.io and `unwordy.dev`; see `research.md` section 5.

## 1. One paragraph

unwordy is an open-source plugin for AI coding agents (Claude Code first, Codex
and Cursor through adapters) that makes the agent write like a developer on the
team: code comments only where the code cannot say why, commit messages and PR
bodies that fit on one screen, tracker and review comments in a human register,
chat replies that answer first. It works in three layers: a tiny always-loaded
voice instruction resolved from a style profile, on-demand skills for setup and
for the moments when the agent is about to write to people, and deterministic
hooks that block the worst patterns before they reach the repo or the tracker
at zero model-token cost.

## 2. Goals and non-goals

Goals

- Cut noise in five surfaces: code comments and docstrings, commit messages,
  PR titles and bodies, issue tracker and review comments (GitHub, GitLab, Jira
  via MCP or CLI), and the agent's own replies.
- Ship presets as developer personas plus a custom voice learned from the
  user's own writing samples.
- Respect project conventions: when the repo defines comment or commit rules,
  they win over the user's voice for code and commits.
- Global profile with per-project override, both plain files a human can edit.
- Add at most about 600 always-loaded tokens as reported by
  `claude plugin details unwordy`. Hooks add zero.
- Install in two commands. No account, no build step, no runtime beyond
  Python 3.9+.
- Same repo installs into Claude Code, Codex and Cursor.

Non-goals for v1

- Rewriting text inside hooks. Hooks block or warn; the model rewrites.
- AI-detection scoring or "humanness" percentages.
- Prose outside the developer workflow. `blader/humanizer` covers that.
- Windows without WSL.
- Perfect parity of Codex and Cursor hook behaviour with Claude Code.

## 3. User experience

Install (Claude Code):

```
/plugin marketplace add assaio/unwordy
/plugin install unwordy@unwordy
```

First run: `/unwordy:setup`. The wizard asks scope, preset or custom, and for
custom asks six short questions with examples and optionally takes writing
samples. It writes the profile, shows three previews (a commit message, a PR
body, a tracker comment), asks to confirm, and offers to sync into Codex and
Cursor if their config directories exist.

After that, nothing to do. Every session starts with the voice loaded. When
the agent tries to commit with an attribution trailer, write a comment that
says "This function returns the user", or post a Jira comment with six bold
bullets, the hook denies the call with a one-line reason and the agent rewrites.

Commands:

| Command | Does |
|---|---|
| `/unwordy:setup` | Wizard. `/unwordy:setup lazy` switches preset. `--project` writes the project file. `off` / `on` toggles. |
| `/unwordy:sync` | Renders the voice block into `AGENTS.md`, `.cursor/rules/unwordy.mdc`, `~/.codex/AGENTS.md`, installs Codex and Cursor hook configs. Idempotent, marker-delimited. |
| `/unwordy:rewrite` | De-slops existing text: pasted text, a file's comments, `--pr <n>` via `gh`, `--last` for the agent's previous reply. Model-invocable on "make this sound human". |
| `unwordy-write` (no slash) | Model-invocable reference the agent loads when about to write a commit, PR, or comment to people. Holds the detailed rules and examples so the always-on text stays tiny. |

## 4. Architecture

```
                 ┌──────────────── style profile ────────────────┐
                 │ .unwordy.md (project) > ~/.config/unwordy/style.md │
                 │ > preset (senior)                              │
                 └───────┬───────────────────────┬───────────────┘
                         │                       │
        SessionStart hook│                       │/unwordy:sync renders
        additionalContext│                       │marker blocks
                         ▼                       ▼
   Claude Code / Codex context        AGENTS.md, .cursor/rules/unwordy.mdc,
   (~250 tokens per session)          ~/.codex/AGENTS.md
                         │
     PreToolUse hooks    │  zero tokens, deterministic
     ├─ Edit|Write|MultiEdit  → comment lints on added lines
     ├─ Bash                  → git commit / gh pr / gh issue / glab message lints
     └─ mcp__.*               → text-field lints (Jira, GitHub, Linear, Slack)
```

### 4.1 Layer 1: voice, always loaded

A `SessionStart` hook (matcher `startup|resume|clear|compact`) runs
`hooks/run.sh session-start`, which resolves the profile and prints the core
rules plus the preset body as `hookSpecificOutput.additionalContext`. Budget:
250 tokens. Re-injection on `compact` keeps the voice after context
compaction.

Why a hook and not an output style: output styles occupy a single slot and
replace system-prompt sections; a hook stacks with whatever the user already
has and lets the project override resolve in a script. An optional
`output-styles/unwordy.md` ships unforced for users who want it.

### 4.2 Layer 2: skills, loaded on demand

Four skills under `skills/`. Descriptions are the only always-on cost, about
40 tokens each. Bodies stay under 800 tokens except `unwordy-write`, which may
reach 1200 because it carries examples.

- `unwordy-setup` (`disable-model-invocation: true`, `allowed-tools: Read Write Bash(mkdir *) AskUserQuestion`)
- `unwordy-sync` (`disable-model-invocation: true`, `allowed-tools: Read Write Edit Bash(ls *) Bash(test *)`)
- `unwordy-rewrite` (model-invocable; description scoped to "rewrite, de-slop, make human" requests about text the user or agent produced)
- `unwordy-write` (`user-invocable: false`; description: "Load before writing a commit message, PR title or body, issue, review or tracker comment, or a reply longer than three sentences.")

If `AskUserQuestion` is not callable from a skill, the wizard asks in plain
text, one question per turn.

### 4.3 Layer 3: hooks, zero tokens

`hooks/hooks.json` for Claude Code:

| Event | Matcher | Script mode | Effect |
|---|---|---|---|
| SessionStart | `startup\|resume\|clear\|compact` | `session-start` | additionalContext with the voice |
| PreToolUse | `Edit\|Write\|MultiEdit\|NotebookEdit` | `pre-edit` | Comment lints on added lines; deny on hard rules |
| PreToolUse | `Bash` | `pre-bash` | Extract message from `git commit`, `gh pr create\|edit\|comment\|review`, `gh issue create\|comment`, `glab mr\|issue`; deny on hard rules |
| PreToolUse | `mcp__.*` | `pre-mcp` | Lint string fields named like `body\|comment\|description\|summary\|text\|content\|message\|note` longer than 40 chars |
| PostToolUse | `Edit\|Write\|MultiEdit\|Bash\|mcp__.*` | `post-warn` | Soft findings as `additionalContext`, only when `strict: warn` |
| Stop | `*` | `stop` | Off by default. With `strict: block`, lints the last reply for length and format and asks for a shorter one once |

Denial output:

```json
{"hookSpecificOutput":{"hookEventName":"PreToolUse","permissionDecision":"deny",
 "permissionDecisionReason":"unwordy: attribution trailer in commit message (Co-Authored-By: Claude). Remove it and commit again."}}
```

Loop guard: the script keeps a small JSON state file under
`${CLAUDE_PLUGIN_DATA:-~/.cache/unwordy}/state/<session_id>.json`. After two
denials for the same rule on the same target in one session it downgrades that
rule to a warning and says so in the reason. Nothing may deny forever.

Exemptions: license headers, shebangs and encoding lines, linter directives
(`noqa`, `eslint-disable`, `type:`, `@ts-`, `pragma`, `nolint`), generated
files (`generated`, `DO NOT EDIT` in the first 5 lines), paths matching
`tests/fixtures/**`, `**/*.snap`, lock files, and any path listed under
`ignore:` in the profile. Markdown and text files get communication lints, not
comment lints. `UNWORDY_OFF=1` or `enabled: false` in the profile disables all
hooks.

Runtime: `hooks/run.sh` finds `python3`, then `python`, then `uv run python`,
sets `PYTHONPATH` to the plugin root and runs `python -m unwordy.hook <mode>`.
Standard library only. Exit 0 with no output when nothing is found. Any
internal exception exits 0 and logs to
`${CLAUDE_PLUGIN_DATA:-~/.cache/unwordy}/unwordy.log`; a bug in unwordy must never
block the user's work.

## 5. Style profile

One Markdown file with flat frontmatter. Resolution order: `UNWORDY_STYLE`
env path, then `.unwordy.md` walking up from cwd to the git root, then
`$XDG_CONFIG_HOME/unwordy/style.md` (default `~/.config/unwordy/style.md`), then
the built-in `senior` preset.

```markdown
---
preset: senior            # lazy | senior | qa | lead | formal | custom
strict: warn              # warn | block | off   (applies to soft rules; hard rules always deny)
language: auto            # auto | en | pl | ...  auto = follow the thread
banned_words: delve, leverage, seamless, robust, comprehensive, streamline, utilize
allow_ticket_refs: false  # ticket ids inside code comments
max_subject: 72
max_pr_body_lines: 12
max_bullets: 6
ignore: vendor/**, **/*.generated.*
---
Dry, direct, explains why not what. Commit body only when the reason matters.
PR body: what, why, risk, how tested; up to twelve lines, no headers. Point at
the file and line instead of describing code.
```

A project `.unwordy.md` may hold only frontmatter (`preset: lazy`) to select a
preset, or a full body to define a team voice. It is meant to be committed.
Parsing is a 20-line regex parser: `key: value`, comma lists, booleans,
integers. No YAML library.

Core rules, prepended to every preset body (target 120 words, English):

```
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
```

Preset bodies (each under 60 words):

- `lazy`: Fewest words that still work. Lowercase is fine. Commit: subject
  only. PR body: one to three lines, or none when the title says it. Comments:
  almost never. One-line replies when one line is enough.
- `senior`: Dry, direct, why not what. Commit body when the reason matters.
  PR body: what, why, risk, how tested, up to twelve lines, no headers. Point
  at file and line instead of describing code.
- `qa`: Precise and reproducible. Bugs: steps, expected, actual, environment.
  Numbered steps allowed. No adjectives. Say when you are guessing. Exact
  versions and exact messages in code blocks.
- `lead`: Brief and warm. Address people, acknowledge the point, then decide.
  One sentence of context when someone joins mid-thread. Never longer than the
  message you answer.
- `formal`: Complete sentences, neutral register, no slang. Fit for enterprise
  Jira and audit trails. State decision, reason, next step. No marketing
  vocabulary.

## 6. Lint rules

Hard rules deny. Soft rules warn under `strict: warn`, deny under
`strict: block`, and are silent under `strict: off`. Rule ids are stable and
appear in every reason so users can search and disable them
(`disable: S1, S3` in the profile).

Hard

| id | Surface | Pattern |
|---|---|---|
| H1 | all | Attribution: `Co-Authored-By:.*(Claude\|Codex\|Cursor\|ChatGPT\|Copilot\|Gemini)`, `Generated with (Claude\|Codex\|Cursor\|AI)`, `Made-with: Cursor`, `Claude-Session:`, `🤖`, `noreply@anthropic.com`, `cursoragent@cursor.com`, `noreply@openai.com` |
| H2 | code comments | Task references: `(as\|per) (the )?(task\|ticket\|issue\|request\|spec\|instructions)`, `^(Step\|Task\|Phase) \d`, `(added\|updated\|changed\|removed\|fixed\|refactored) (this\|to\|for\|per\|as requested)`, ticket ids `\b[A-Z]{2,10}-\d+\b` unless `allow_ticket_refs` |
| H3 | code comments, files | Chat leakage: `^(Here's\|Here is\|Let me\|I've\|I have\|Note that I\|As requested\|Hope this helps\|Sure[,!]\|Certainly)` |
| H4 | code comments | Restating openers: `^(This\|The) (function\|method\|class\|file\|module\|component\|hook) (is\|does\|handles\|provides\|returns\|takes\|defines\|represents\|contains)`, `^(Import\|Return\|Increment\|Initialize\|Define\|Create\|Set\|Get\|Call\|Loop\|Check) (the\|a\|an)? ?\w+ *$` directly above a line that does exactly that |

Soft

| id | Surface | Heuristic |
|---|---|---|
| S1 | text | Em dash U+2014, or spaced en dash used as a dash |
| S2 | text | Word from `banned_words` (case-insensitive, word-bounded); ships with an English list and a short Polish list |
| S3 | code | Comment density: added comment lines / added code lines > 0.3 when added code lines >= 8 |
| S4 | code | Docstring longer than the function body it documents, and > 3 lines |
| S5 | commit, PR, comment | Subject > `max_subject`; body > `max_pr_body_lines`; bullets > `max_bullets`; > 2 markdown headers; > 3 `**Label:**` bullets; emoji in headers |
| S6 | commit, PR | Boilerplate sections: `## Summary` together with `## Test plan`; a `Summary of changes` block; opener `This (PR\|commit) (adds\|implements\|introduces)` |
| S7 | reply (Stop) | Reply > 12 lines for a yes/no or one-fact question; closing offer lines (`Let me know if`, `Feel free to`) |

Comment detection is per language by file extension: `//`, `#`, `--`, `;`,
`/* */`, `<!-- -->`, `"""`, `'''`, `///`, `/** */`. Only added lines are
linted (for `Edit`, the lines in `new_string` not present in `old_string`;
for `Write` on an existing file, a line diff against the current content; for a
new file, everything).

Message extraction for `Bash`: `-m` (repeated, joined with blank lines),
`--message=`, `-F <file>` and `--body-file <file>` (read when the file
exists), `--title`, `--body`, and a heredoc inside `$(cat <<'EOF' ... EOF)`.
Quoting handled with `shlex`. Unknown shapes produce no finding.

## 7. Cross-tool adapters

- Codex: `.codex-plugin/plugin.json` and `agents/openai.yaml` at the repo root;
  skills reused as-is (Agent Skills format). `/unwordy:sync` writes the voice
  block into `~/.codex/AGENTS.md` and, when the Codex hooks stdin schema matches
  Claude Code's (verify; see `research.md` section 4), installs
  `~/.codex/hooks.json` entries pointing at `hooks/run.sh`. If the schema
  differs, `unwordy/hook.py` normalises the input in one adapter function.
- Cursor: `.cursor-plugin/plugin.json`; `/unwordy:sync` writes
  `.cursor/rules/unwordy.mdc` with `alwaysApply: true` and a
  `.cursor/hooks.json` entry for `beforeShellExecution` that runs the same
  `pre-bash` lint. Cursor also reads `AGENTS.md`, so the block there suffices
  for voice.
- Everything else that reads `AGENTS.md` (Copilot, Jules, Zed, Windsurf,
  Aider): the synced block.
- Marker format in every rendered file:

```
<!-- unwordy:start (managed by unwordy; edit .unwordy.md or ~/.config/unwordy/style.md instead) -->
...
<!-- unwordy:end -->
```

## 8. Repository layout

```
unwordy/
├── .claude-plugin/plugin.json
├── .claude-plugin/marketplace.json     self-hosted marketplace listing this plugin
├── .codex-plugin/plugin.json
├── .cursor-plugin/plugin.json
├── agents/openai.yaml
├── skills/
│   ├── unwordy-setup/SKILL.md
│   ├── unwordy-sync/SKILL.md
│   ├── unwordy-rewrite/SKILL.md
│   └── unwordy-write/SKILL.md, references/examples.md
├── hooks/
│   ├── hooks.json                       Claude Code
│   ├── codex.hooks.json                 template installed by sync
│   ├── cursor.hooks.json                template installed by sync
│   └── run.sh
├── unwordy/                               Python package, stdlib only
│   ├── __init__.py
│   ├── hook.py                          stdin JSON in, decision JSON out, mode dispatch
│   ├── profile.py                       resolution, frontmatter parser, presets
│   ├── lint.py                          rules H1..H4, S1..S7
│   ├── extract.py                       added lines, shell messages, MCP text fields
│   ├── render.py                        marker blocks for AGENTS.md and .mdc
│   ├── state.py                         loop guard
│   └── presets/{core,lazy,senior,qa,lead,formal}.md
├── output-styles/unwordy.md               optional, not forced
├── tests/                               pytest, fixtures/slop and fixtures/clean
├── evals/                               claude plugin eval cases (v0.2)
├── README.md  LICENSE (MIT)  CHANGELOG.md  CONTRIBUTING.md
```

`plugin.json` declares `name: unwordy`, `version`, `description`, `author`,
`license`, `repository`, `hooks: ./hooks/hooks.json`, `skills: ./skills/`.
`marketplace.json` lists one plugin with a relative source so
`/plugin marketplace add assaio/unwordy` works from the repo itself.

## 9. Setup wizard specification

Inputs, in order. Each question shows two or three concrete examples of the
choices as short sample outputs, not adjectives.

1. Scope: global, this project, both.
2. Start from: lazy, senior, qa, lead, formal, custom.
3. (custom) Reply length: one-liners; a few sentences; as long as needed.
4. (custom) Formatting: none; occasional bullets; headers fine in long docs.
5. (custom) Casing and punctuation: lowercase casual; standard; formal.
6. (custom) Warmth: none; a bit; friendly.
7. (custom) Language: en; pl; follow the thread.
8. (custom, optional) Samples: paste text or give paths to 3 to 10 of your own
   messages, commits, PR bodies, tracker comments.

From samples the skill body instructs the model to extract: median sentence
length, casing, punctuation habits, greeting and sign-off, bullet and emoji
use, three characteristic phrasings, three avoided phrasings, language and
register per surface. It writes a body of at most 250 tokens and at most five
short example lines. It never stores the samples.

Preview and confirm: the wizard renders a commit message, a PR body and a
tracker comment for a fixed fictional change in the new voice, asks
"keep, adjust, or start over", then writes the file and prints its path.

## 10. Acceptance criteria for v0.1

1. `claude plugin validate --strict .` passes.
2. `claude plugin details unwordy` reports at most 600 always-loaded tokens.
   Record the number in the README.
3. `pytest` green with at least 40 cases: every rule with one slop and one
   clean fixture; extraction for `git commit -m`, repeated `-m`, heredoc, `-F`,
   `gh pr create --body`, `--body-file`, `gh issue comment`; profile
   resolution order and env overrides; frontmatter parser edge cases; render
   idempotence (running sync twice changes nothing); loop guard downgrade
   after two denials; every exemption.
4. Hook scripts never exit non-zero on malformed input; a test feeds garbage
   and an empty stdin.
5. Manual smoke, documented in `CONTRIBUTING.md`: install from the local
   marketplace; new session shows the voice in context; a commit with a
   Claude trailer is denied with rule id H1; an Edit adding
   `// This function returns the user` is denied with H4;
   `/unwordy:setup lazy` writes the profile; `/unwordy:sync` produces the
   AGENTS.md block and a second run is a no-op.
6. README: one-screen install, a before/after for each surface, the token
   number, the rule table with ids, how to disable a rule, how a team commits
   `.unwordy.md`.
7. No live model calls in tests and no `claude -p` anywhere in scripts or CI.

## 11. Open points to verify during implementation

- Whether `PreToolUse` output may carry `additionalContext` alongside an
  allow decision; if not, soft warnings go through `PostToolUse`.
- Exact `Stop` hook input and output schema, and whether `stop_hook_active`
  is provided to prevent re-entry.
- Codex hooks stdin schema and the skills directory set.
- Whether `marketplace.json` accepts a relative `source` for a plugin in the
  same repo; otherwise point at the repo URL with `git-subdir`.
- `AskUserQuestion` availability inside skill execution.

## 12. Later

- v0.2: `evals/` for `claude plugin eval`; Polish and German banned-word lists;
  detection of `commitlint` and `.gitmessage` to defer subject-format rules;
  `--project` templates for teams.
- v0.3: Codex hook parity tests; `npx skills add unwordy` listing; per-surface
  overrides in the profile (`pr:`, `jira:` sub-blocks).
