# Profiles and local checks

## Start here

The full Claude Code plugin provides `/unwordy:init` to build a profile from
selected writing examples and `/unwordy:setup lazy` for a quick preset. These
commands are installed with the plugin, not with the standalone skill.

If you installed only the global `unwordy` skill in Claude Code, run:

```text
/unwordy Help me set up my personal writing style. Ask about my role and tone, show a preview, then save it after I approve.
```

For a shared project profile, ask for “a team profile for this repository”
instead. Claude Code also accepts ordinary language such as “Use unwordy to
configure my style.” A personal profile is stored at
`~/.config/unwordy/style.md` (or `$XDG_CONFIG_HOME/unwordy/style.md`); a team
profile is `.unwordy.md` at the repository root. A global skill installation
does not create either profile by itself.

The standalone skill's own `SKILL.md` already contains its instructions. It
should not read files under `~/.claude/skills/unwordy/references/` during normal
use. If an older installation asks to read one of those files outside the
project, update it with `npx skills update unwordy --global` or reinstall from
GitHub. There is no need to grant broad access to files outside the project
for that read. Claude Code may still ask before reading or saving an actual
personal profile under `~/.config/unwordy/`; that is a separate permission
decision. If desired, add only `Read(~/.config/unwordy/style.md)` to
`permissions.allow` in `~/.claude/settings.json`; keep existing entries. A
custom `$XDG_CONFIG_HOME` or `$UNWORDY_STYLE` path needs its own narrow rule.

## Resolution and precedence

The first existing profile wins: `$UNWORDY_STYLE`, nearest `.unwordy.md` up to
the git root, `$XDG_CONFIG_HOME/unwordy/style.md` (default `~/.config/unwordy/style.md`),
built-in senior. A project profile replaces personal defaults; it does not merge.
Repository instructions, required templates and disclosure take precedence.

Profiles use flat frontmatter, not general YAML. Lists are comma-separated;
inline comments are supported. A body replaces preset prose. Omit the body to
receive updated preset wording. Raw samples should never be saved in a profile.

```markdown
---
preset: senior
role: developer
tone: warm
language: auto
strict: warn
banned_words: delve, seamless, comprehensive
allow_ticket_refs: true
attribution: warn
commit.attribution: allow
max_subject: 72
max_pr_body_lines: 12
max_bullets: 6
pr.max_body_lines: 20
pr_template: auto
rule.H4: warn
rule.H2d: off
disable: S1, S3
ignore: vendor/**, **/*.generated.*
enabled: true
---
```

| Key | Values |
|---|---|
| preset | lazy, senior, qa, lead, formal, custom |
| role | auto, developer, qa, design, lead |
| tone | auto, neutral, direct, warm, formal, lazy |
| language | auto or a language requested for replies/tracker text |
| strict | warn, block, off for heuristics |
| attribution | block, warn, allow; also `<surface>.attribution` |
| rule.<id> | warn, block, off; family or sub-id |
| pr_template | auto detects template headings; respect preserves all PR headings; ignore checks all headings |
| limits | positive integers; `<surface>.max_subject`, `.max_body_lines`, `.max_bullets` override defaults |

Surfaces: commit, pr, issue, comment, code, docs, reply. Limits currently apply
to commit, PR, issue and comment messages; reply checks have separate S7 logic.
`banned_words` replaces the built-in English/Polish/German list. Disabling S1
allows personal dashes without a conflicting session instruction. Explicit role
refines a preset; explicit tone replaces built-in tone prose while retaining a
custom body. Auto uses QA/lead role for those presets, developer otherwise.

`preset: lazy` or `tone: lazy` keeps fragments, lowercase and casual punctuation.
It turns off S1 punctuation and S5 length/format suggestions by default. Use
`rule.S1: warn` or `rule.S5: warn` to restore either check. Required templates,
disclosure, technical facts and test evidence still apply.

Unknown keys, invalid enums, unknown rule IDs, duplicate entries and invalid
limits are diagnosed. `doctor`, `voice` and `check` fail with exit 2; hooks pause
checks and provide configuration feedback rather than unpredictably blocking.
Cursor can receive this diagnosis at session start; its pre-tool route only allows.

## Repository conventions

Commitlint files, a commitlint package configuration or a Git commit template
skip S5a/S6c for commits. GitHub root, docs and `.github` templates, including
multiple `PULL_REQUEST_TEMPLATE/*.md`, and `.gitlab/merge_request_templates/*.md`
provide required headings. If every heading in a PR matches that set, S5d/S5f/S6a
are skipped. Extra headings are still checked. Body length and content rules remain.
Use `pr_template: respect` when requirements live outside the repository.

## CI

Install the checker from a pinned release checkout. The PR checkout needs full
history. Use the PR base commit, rather than assuming origin/main exists:

```sh
sh /path/to/unwordy/bin/unwordy check --diff "$PR_BASE_SHA" --commits "$PR_BASE_SHA" --fail-on-warn
```

CI executes the checker only; do not run untrusted PR code. `--diff` compares
tracked worktree contents with the base; `--staged` compares the index with HEAD.
A `commit-msg` hook can pass its `$1` to `--message-file --surface commit`.
Enable repository hooks only when that repository wants them.

## Switching off

`disable: S1` silences a family or pattern, `rule.H4: off` disables a heuristic,
`strict: off` silences heuristic defaults, and `enabled: false` silences the profile.
`UNWORDY_OFF=1` affects the process receiving it; setting it on an agent's child
command does not retroactively change the environment of the host hook process.
Remove a previously synced managed block when disabling voice in another host.
