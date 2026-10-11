# unwordy

**Commits, PRs and reviews in your team's voice.**

Give your coding agent a writing style it can follow: direct, warm, formal or
as casual as a note to a teammate. unwordy preserves supplied facts, uncertainty
and test scope while cutting filler and repeated explanations. Required
repository templates and disclosure take precedence.

Start with a portable skill. Add a shared profile for your team, or use the
Python checker and host hooks to flag supported writes.

[Try the demo](https://assaio.github.io/unwordy/) ·
[Install a release](https://github.com/assaio/unwordy/releases/latest) ·
[Configuration](docs/configuration.md) · [Host support](docs/compatibility.md)

## See the difference

Input, including all the facts used below:

> This comprehensive update seamlessly improves webhook delivery. We retry
> three times, after 1s, 2s and 4s, because the receiver returns 502 after
> deploys. Duplicate delivery is a risk; the receiver is idempotent on event id.
> We tested a forced 502 in staging. Production was not tested.

Ready to paste:

```text
Retry webhook delivery three times: 1s, 2s, 4s. The receiver returns 502
after deploys.

Risk: duplicate delivery; the receiver is idempotent on event id.
Tested a forced 502 in staging. Production was not tested.
```

The same change can be concise or warm without losing its evidence. Missing
facts stay missing. Already useful text can stay unchanged.
[More examples](skills/write/references/examples.md) include incomplete bug
reports, required templates and code comments.

## Try it on your next PR

```sh
npx skills add assaio/unwordy --skill unwordy
```

Then ask your agent:

```text
Use unwordy to rewrite this PR description. Keep the risk, exact errors
and what was actually tested.
```

The standalone skill works without Python, a plugin or sibling skills.
It guides the model; it does not install the checker or hooks.

For a personal Claude Code installation across projects, add
`--global --agent claude-code`. To set up your voice, type:

```text
/unwordy Help me set up my personal writing style. Preview it before saving.
```

A personal profile lives at `~/.config/unwordy/style.md`, or under
`$XDG_CONFIG_HOME`; a team profile is `.unwordy.md` in the repository.
Installation does not create a profile automatically.
[Setup and permissions](docs/configuration.md#start-here).

## Install the full plugin

| Host | Install |
|---|---|
| Claude Code | `/plugin marketplace add assaio/unwordy`, then `/plugin install unwordy@unwordy` |
| Codex | `codex plugin marketplace add assaio/unwordy`, then `codex plugin add unwordy@unwordy` |
| Cursor | Copy the checkout to `~/.cursor/plugins/local/unwordy` and reload, if your organization allows local plugins |

The full plugin adds `init`, `setup`, `rewrite` and `sync`, plus local checks
and hook assets. In Claude Code, start with `/unwordy:init`; use
`/unwordy:setup lazy` for a preset or `/unwordy:setup --project team-design`
for a team template. The next session loads the voice.

The standalone skill has no `/unwordy:init` or `/unwordy:setup` commands.
Review and trust Codex hook definitions in `/hooks`. Codex and Cursor adapters
have fixture coverage; live enforcement remains unconfirmed. Cursor pre-tool
warnings are not guaranteed to reach the agent. See the
[dated host matrix](docs/compatibility.md).

## Make it sound like you

Role and tone are independent. This profile keeps a developer's facts in a
casual voice:

```markdown
---
preset: custom
role: developer
tone: lazy
language: auto
strict: warn
---
Keep lowercase openings and short notes. Preserve useful warmth.
Keep risk, conditions and exact test scope.
```

Write it to `.unwordy.md` for the team or the personal profile path above.
Choose `senior`, `qa`, `lead`, `formal` or `lazy` for a preset.
A custom body describes your rhythm, casing and punctuation.

| Role | What the message keeps |
|---|---|
| Developer | Reason, risk, test evidence and relevant code location |
| QA | Reproduction, expected/actual, environment, versions and frequency |
| Design | UI states, behavior, rationale, accessibility and constraints |
| Lead | Decision, trade-off, owner and next step when supplied |

Lazy allows fragments and casual punctuation, and turns off S1 punctuation
and S5 length/format suggestions by default. Explicit rule settings can restore
them. Required facts and repository sections still stay.

The first existing profile wins: `$UNWORDY_STYLE`, nearest `.unwordy.md` up
to the Git root, global profile, then built-in senior. Profiles replace each
other rather than merge. [Team templates](templates/) and the
[profile reference](docs/configuration.md) cover limits and rule overrides.

## Check before you publish

Python 3.9+, standard library only. From a checkout:

```sh
sh bin/unwordy doctor
sh bin/unwordy check --staged --explain
sh bin/unwordy check --message-file .git/COMMIT_EDITMSG --surface commit
sh bin/unwordy check --diff origin/main --commits origin/main
sh bin/unwordy check --explain --json
sh bin/unwordy voice
```

`--explain` shows the selected profile and effective rule and attribution
policies. JSON findings include rule ID, effect, target and line when known.
The checker and `voice` resolve the same profile from your current directory.

Use an absolute path to `bin/unwordy` from another repository.
Exit codes: 0 clean or warning, 1 block, 2 error; `--fail-on-warn` makes
warnings fail too. The checker reads tracked diffs or the index; untracked
files are not included. [CI example](docs/configuration.md#ci).

Stable rule IDs let you tune a finding: `rule.H4: off` disables the
restating-comment heuristic; `rule.H4: block` opts in. Required GitHub/GitLab
PR headings are respected. Literal quotes, code and URLs are protected from
style patterns. Recognized MCP PR, issue and comment operations use the same
policy as shell routes; unrelated operations are skipped.

## Evidence and limits

The [72-case corpus](benchmarks/README.md) covers PL/EN writing, custom and lazy
voices, required templates, missing details, protected strings and code.
Offline checks test bounded literals, case-specific fact relationships and
Python code preservation. They also report changes to text that should stay.
Blinded review sheets and rating summaries support human assessment of
naturalness and voice; no human quality score is claimed without collected
ratings. [Release evidence](docs/release-evidence.md) records actual checks.

Regexes cannot establish factual correctness or prove that text sounds natural.
The checker makes no network or model calls. Hook coverage depends on the host
and supported tool route. Unsupported editors and arbitrary scripts can bypass
checks.

Hard defaults are H1, H2a, H2c and H3. Other patterns follow `strict`;
explicit effects and disable lists take precedence, including Stop rules.
Soft pre-tool blocks downgrade after two denials for the same family and target.

The [seven-language demo](https://assaio.github.io/unwordy/) contains illustrative
outputs. Word-pattern coverage is strongest in English, partial in Polish and
German, and not localized for Spanish, French, Dutch or Finnish.

Setup and rewriting use your existing host/model. Profiles store short
preferences rather than raw samples; hook state stores denial counts and
targets. [Privacy and stored data](docs/privacy.md).
`enabled: false` disables unwordy preferences and checks; `UNWORDY_OFF=1`
disables the checker or hook process. Windows requires WSL.

## Help shape the next release

Report a [false positive](https://github.com/assaio/unwordy/issues/new?template=false-positive.yml)
with a redacted example and rule ID, or share a profile in
[Discussions](https://github.com/assaio/unwordy/discussions).
[CONTRIBUTING.md](CONTRIBUTING.md) covers tests and live smoke checks.

MIT licensed. Maintainer's sibling project:
[assaio](https://github.com/assaio/assaio), offline coding-agent cost analytics.
