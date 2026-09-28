# unwordy

**Clear commits, PRs and reviews in your team's voice.**

unwordy helps coding agents follow your team's writing conventions in commits,
pull requests, code comments and work replies. Use a preset or a profile from
selected examples of your own writing. Choose a role and tone independently.
Local checks flag filler and repeated explanations; host hooks can intercept
matching writes. Required templates, disclosure and useful evidence stay.

[Try the demo](https://assaio.github.io/unwordy/) ·
[Configuration](docs/configuration.md) · [Rules](docs/rules.md) ·
[Host support](docs/compatibility.md) · [Evaluation](benchmarks/README.md)

```diff
- This comprehensive update seamlessly improves delivery reliability.
- We added retry logic and extensively tested the implementation.
+ Retry delivery three times: 1s, 2s, 4s. The receiver returns 502 after deploys.
+ Risk: duplicate delivery; the receiver is idempotent on event id.
+ Tested a forced 502 in staging. Production was not tested.
```

The source notes supplied the retry schedule, risk and exact test scope.
A rewrite must preserve those facts; it cannot invent evidence to sound specific.

## Start with your agent

### Claude Code plugin

```text
/plugin marketplace add assaio/unwordy
/plugin install unwordy@unwordy
/unwordy:init
```

`init` previews a personal or team profile before saving. For a direct preset
switch use `/unwordy:setup senior`; for a team use
`/unwordy:setup --project team-design`. The next session loads the voice.

### Codex plugin

```sh
codex plugin marketplace add assaio/unwordy
codex plugin add unwordy@unwordy
```

Review and trust the hook definition in `/hooks`. **Live Codex hook enforcement
is not confirmed.** Use the checker below as the host-independent route.

### Cursor plugin

Until a marketplace listing is approved, copy this repository to
`~/.cursor/plugins/local/unwordy` and reload Cursor. Local plugin imports must
be allowed by your organization. **Live Cursor hook enforcement is not confirmed.**
Cursor pre-tool warnings are not guaranteed to reach the agent; use the checker.

### Skill only, including other agents

```sh
npx skills add assaio/unwordy --skill unwordy
```

The standalone `unwordy` skill reads the same profile and covers dev, QA,
design and decision messages. It has no plugin paths or sibling-skill dependency.
It guides the model; this installation does not install Python checks or hooks.
Read the [host matrix](docs/compatibility.md) for what each route supplies.

## Check independently of the agent

Python 3.9+, standard library only. From a checkout:

```sh
sh bin/unwordy doctor
sh bin/unwordy check --staged
sh bin/unwordy check --message-file .git/COMMIT_EDITMSG --surface commit
sh bin/unwordy check --diff origin/main --commits origin/main
sh bin/unwordy voice
```

Use an absolute path to `bin/unwordy` from another repository. `--json` returns
rule IDs, effects and targets. Exit codes: 0 clean or warning, 1 block, 2 error.
`--fail-on-warn` also exits 1 for warnings. The checker reads tracked diffs or
the index; untracked files are not included. A [CI example](docs/configuration.md#ci)
checks a commit range without relying on a host hook.

## Your role, your tone

```markdown
---
preset: custom
role: design
tone: warm
language: auto
strict: warn
pr.max_body_lines: 20
allow_ticket_refs: true
disable: S1
---
Direct but friendly. Keep useful acknowledgements and occasional dashes.
Preserve uncertainty, accessibility requirements and implementation constraints.
```

Write this to `.unwordy.md` for a team, or `~/.config/unwordy/style.md` for
personal defaults. The first matching profile
wins: `$UNWORDY_STYLE`, nearest project file up to the git root, global file,
then built-in `senior`. Repository requirements always win over voice preferences.

| Role | Retain |
|---|---|
| Developer | Reason, risk, test evidence and relevant code location |
| QA | Reproduction, expected/actual, environment, versions and frequency |
| Design | UI states, behavior, rationale, accessibility and constraints |
| Lead | Decision, trade-off, owner and next step when supplied |

Tone is separate: neutral, direct, warm, formal or lazy. The custom body can
describe personal rhythm, casing and punctuation. Already useful text can stay
unchanged.
Choose `preset: lazy` or `tone: lazy` for plain notes with casual punctuation
and no suggested length or formatting limits. Facts, required templates and
test evidence still stay. The [demo](https://assaio.github.io/unwordy/) shows
lazy alongside direct and warm in seven languages.
The multilingual demo shows model-guided examples. Local word-pattern checks
are strongest in English, partial in Polish and German, and not localized for
Spanish, French, Dutch or Finnish.
See [PL/EN examples](skills/write/references/roles.md),
[team templates](templates/) and the [profile format](docs/configuration.md).

## What makes this useful in a repository

- A shared `.unwordy.md` gives agents the team's voice; `sync` carries it into
  AGENTS.md or Cursor rules when needed.
- Required PR templates and disclosure take precedence. The checker recognizes
  GitHub and GitLab template headings, or `pr_template: respect` for external requirements.
- Stable rule IDs make each finding explainable and configurable. For example,
  `rule.H4: off` disables the restating-comment heuristic; `rule.H4: block` opts in.
- Contract descriptions and standard algorithm steps are preserved. Ticket references
  and restating heuristics warn by default rather than treating syntax as proof.
- Known MCP publishing operations apply the same PR/issue/comment policy as shell
  routes, including titles. Read operations and unrecognized tool names are skipped.

## Limits, evidence and privacy

Regexes do not assess factual correctness or prove naturalness. Hook coverage
is not a security boundary: unsupported editors and tool routes can bypass it.
Hard defaults are H1, H2a, H2c and H3. H2b, H2d, H4 and S rules follow `strict`;
explicit effects and disable lists take precedence. Soft blocks downgrade after
two denials for the same family and target; hard defaults keep blocking.

`doctor` validates configuration and reports local readiness. It does not claim
that a host invoked a hook. [Dated compatibility notes](docs/compatibility.md)
separate fixture tests from observed sessions.

The checker makes no network or model calls. `init` and `rewrite` run in your
existing agent: selected samples are visible to that host/model. Profiles store
short preferences, not raw writing samples. Local hook state stores denial
counts and targets; error logs store tracebacks. See [privacy](docs/privacy.md).

`enabled: false` disables a profile, `UNWORDY_OFF=1` disables a checker or hook
process, and the plugin can be uninstalled through its host. Windows requires WSL.

## Help improve it

Report a [false positive](https://github.com/assaio/unwordy/issues/new?template=false-positive.yml)
with a redacted example and rule ID. Share profiles or workflow feedback in
[Discussions](https://github.com/assaio/unwordy/discussions).

The public [36-case evaluation corpus](benchmarks/README.md) covers dev, QA,
design and decisions in PL/EN, including clean text and personal voice. Offline
checks catch missing required literals; blinded human ratings assess naturalness
and voice. No human quality score is claimed without collected ratings.

[CONTRIBUTING.md](CONTRIBUTING.md) has tests, evals and live smoke checks.
MIT licensed. Maintainer's sibling project:
[assaio](https://github.com/assaio/assaio), offline coding-agent cost analytics.
