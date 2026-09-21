# Research notes

Collected September 2026 for the spec in `spec.md`. Every claim links to its
source; "unverified" marks things a second person should confirm before relying
on them.

## 1. The pain, in developers' words

### Code comments

- anthropics/claude-code issue [#65961](https://github.com/anthropics/claude-code/issues/65961):
  Claude writes comments that restate obvious code and keeps doing it despite
  CLAUDE.md rules and memory entries. Closed as stale, not fixed.
- Cory House on [X](https://x.com/housecor/status/2085125584615821723): the
  system prompt tells the model to match surrounding comment density, so a
  comment-heavy file snowballs.
- A shared [gist](https://gist.github.com/bavanws/123e0343f8a79cec825d9141124a0a83)
  pairs a CLAUDE.md rule with a post-hoc "comment cleanup" skill, which means the
  rule alone was not enough.
- Developers on [Threads](https://www.threads.com/@bryan.manuele/post/Da4Wc4zHNnM/)
  strip comments in post-processing rather than prompting.

### Commits and pull requests

- Attribution trailers are the most repeated complaint. Issues
  [#66602](https://github.com/anthropics/claude-code/issues/66602),
  [#79909](https://github.com/anthropics/claude-code/issues/79909) (trailer
  reappears after being told to stop; one leak needed an amend and force-push),
  [#45137](https://github.com/anthropics/claude-code/issues/45137)
  (`attribution.commit: ""` did not suppress it; users fall back to a `sed`
  strip in a git hook), [#53571](https://github.com/anthropics/claude-code/issues/53571).
  All closed "not planned" or stale.
- r/ExperiencedDevs thread on reviewing AI PRs, 1.9k upvotes, top comment
  "I gave up and just started hitting approve"
  ([summary](https://www.aibuilderclub.com/blog/reviewing-ai-generated-pull-requests)).
  Consensus: push back on size, not on AI origin.
- [gitfluff](https://github.com/Goldziher/gitfluff): a commit linter written
  specifically to strip AI signatures. Its existence is the evidence.
- Cursor has the same problem from the other side: `Co-authored-by: Cursor` is on
  by default and users file
  [complaints](https://forum.cursor.com/t/co-author-added-without-consent-and-cant-be-turned-off/150096).
  Codex introduced a `commit_attribution` key whose default is
  [in flux](https://github.com/openai/codex/issues/19799) (unverified final state).

### Issue trackers

- Evidence is thinner and mostly from the PM side:
  [Should you let AI write your Jira tickets?](https://japm.substack.com/p/should-you-let-ai-write-your-jira)
  ("too generic", acceptance criteria that "confuse your devs later").
  Treat Jira tone as a secondary use case in positioning, not the lead.

### Social cost: AI-looking output gets rejected

- Ghostty: "Drive-by AI PRs will be closed without question"
  ([Mitchell Hashimoto](https://x.com/mitchellh/status/2014433315261124760),
  [RedMonk](https://redmonk.com/kholterhoff/2026/02/03/ai-slopageddon-and-the-oss-maintainers/)).
- curl closed its bug bounty after the valid-report rate fell below 5 percent under
  AI slop ([LWN](https://lwn.net/Articles/1055996/)).
- Jazzband sunset citing AI spam PRs ([The New Stack](https://thenewstack.io/ai-slop-open-source/)).
- GitHub weighing a PR "kill switch" ([The Register](https://www.theregister.com/2026/02/03/github_kill_switch_pull_requests_ai/)).
- Godot "drowning in AI slop PRs" ([HN](https://news.ycombinator.com/item?id=47059779)).
- arXiv study of ~1,150 Reddit and HN posts on maintainer burden
  ([2603.27249](https://arxiv.org/html/2603.27249v2)).

## 2. What exists, and the gap

| Tool | Stars | Covers | Does not cover |
|---|---|---|---|
| [blader/humanizer](https://github.com/blader/humanizer) | 50k | Prose rewrite, 25 AI patterns, voice matching from samples | Explicitly excludes code, comments, docstrings, commits, PR text |
| [conorbronsdon/avoid-ai-writing](https://github.com/conorbronsdon/avoid-ai-writing) | 4.5k | 74 patterns, ships for Claude Code, Codex, Cursor, others | Prose and marketing focus; no code or VCS surface, no learned style |
| [numen-tech/slopornot](https://github.com/numen-tech/slopornot) | 48 | Humanizer + detector skills, multi-harness plugin | Prose and chat; paid Mac app for scoring |
| [aplaceforallmystuff/claude-slop-detector](https://github.com/aplaceforallmystuff/claude-slop-detector) | 9 | Slop score for drafts, rule-based | Prose only |
| [sirambrosio/humanink](https://github.com/sirambrosio/humanink) | small | Prose scoring and rewrite | Rejected from awesome-claude-code as a writer/marketer tool ([#1080](https://github.com/hesreallyhim/awesome-claude-code/issues/1080)) |
| [rlorenzo/humanize](https://github.com/rlorenzo/humanize) | 0 | Has a "commit" profile flagging AI verbs | No adoption, no comments or PR surface |
| [Goldziher/gitfluff](https://github.com/Goldziher/gitfluff) | 8 | Commit-message linter for AI signatures | Commits only |
| npm `deslop`, `unslop`, `slopstop`, `slopguard`, `LeoStehlik/no-slop-ui`, `iansmith/slopstop` | various | Code-quality slop: dead code, anti-patterns, low-quality PR detection | Voice, comments, communication; prevention at generation time |
| Claude Code built-in "Concise" output style ([docs](https://code.claude.com/docs/en/output-styles)) | n/a | Chat verbosity | Comments, commits, PRs, tracker text |
| Claude Code `attribution.*` settings ([docs](https://code.claude.com/docs/en/settings)) | n/a | Trailer and PR footer | Flaky per the issues above; not enforced |

The gap: nothing spans code comments, commit and PR text, tracker and review
comments, and chat replies in one package, enforces at generation time rather
than after the fact, and offers developer personas plus a style learned from the
user's own writing. Every humanizer-class tool explicitly disclaims the
code-adjacent surface. The "slop" name space, however, is saturated with
code-quality linters, so the name and the tagline must say "voice and noise",
not "slop detection".

## 3. Claude Code mechanics that shape the design

Verified against [code.claude.com/docs](https://code.claude.com/docs/en/plugins)
and the plugins cached under `~/.claude/plugins/cache/claude-plugins-official`
on this machine (Claude Code 2.1.278).

- Plugin layout: `.claude-plugin/plugin.json`, `skills/`, `hooks/hooks.json`,
  `agents/`, `output-styles/`, optional `settings.json` defaults, `bin/`.
  Plugins cannot ship CLAUDE.md. `${CLAUDE_PLUGIN_ROOT}` is the read-only
  install dir, `${CLAUDE_PLUGIN_DATA}` persists across updates
  ([reference](https://code.claude.com/docs/en/plugins-reference)).
- The Expo plugin in the official marketplace ships `.claude-plugin/`,
  `.codex-plugin/`, `.cursor-plugin/` and `.grok-plugin/` manifests side by side
  plus `agents/openai.yaml`. One repo, four hosts. That is the precedent for our
  cross-tool layout.
- Marketplace manifest: `.claude-plugin/marketplace.json` with `name`, `owner`,
  `plugins[]` each having `name`, `description`, `source` (`git-subdir` with
  `url`, `path`, `ref`, `sha`, or a relative path). Users run
  `/plugin marketplace add <owner>/<repo>` then `/plugin install <name>@<marketplace>`.
- Token cost: skill descriptions and output style text are always in the system
  prompt; skill bodies load on invocation; hook scripts cost zero tokens. No
  documented size limits, only "concise". `claude plugin details <name>` prints
  a projected token cost, which gives us a measurable budget.
- Hooks ([docs](https://code.claude.com/docs/en/hooks)): events include
  `SessionStart` (matchers `startup|resume|clear|compact|fork`),
  `UserPromptSubmit`, `UserPromptExpansion`, `PreToolUse`, `PostToolUse`,
  `Stop`, `PreCompact`, `PostCompact`, `SubagentStart/Stop`, `FileChanged`.
  `SessionStart`, `UserPromptSubmit` and `UserPromptExpansion` accept
  `hookSpecificOutput.additionalContext`. `PreToolUse` denies with
  `hookSpecificOutput.permissionDecision: "deny"` plus
  `permissionDecisionReason`, or exit code 2 with the reason on stderr.
  Matchers are unanchored JS regex when they contain regex characters, and
  match MCP tools as `mcp__<server>__<tool>`. `Edit` input carries `file_path`,
  `old_string`, `new_string`; `Write` carries `file_path`, `content`; `Bash`
  carries `command`.
- Output styles are still supported; a plugin can ship one and force it with
  `force-for-plugin: true`. It occupies the single output-style slot, so we do
  not force it in v1.
- Skills frontmatter: `name`, `description`, `disable-model-invocation`,
  `user-invocable`, `allowed-tools`, `context: fork`, `paths`, `model`.
  Whether `AskUserQuestion` is callable from a skill body is not documented;
  the wizard must degrade to plain questions.
- Settings precedence: managed > CLI > `.claude/settings.local.json` >
  `.claude/settings.json` > `~/.claude/settings.json`. Attribution keys:
  `attribution.commit`, `attribution.pr`, `attribution.sessionUrl`.
- CLI: `claude plugin validate --strict <path>` (manifest, skills, agents,
  hooks), `claude plugin details <name>` (token cost), `claude plugin eval`
  (scored eval cases under `evals/`).

## 4. Codex, Cursor and the cross-tool standards

- Codex reads `~/.codex/AGENTS.md` then `AGENTS.md` from git root down to cwd,
  32 KiB combined cap (`project_doc_max_bytes`)
  ([docs](https://learn.chatgpt.com/docs/agent-configuration/agents-md.md)).
  `config.toml` has `developer_instructions`, `model_verbosity`, profiles
  ([reference](https://learn.chatgpt.com/docs/config-file/config-reference)).
- Codex supports Agent Skills (`SKILL.md`) from `.agents/skills` (repo) and
  `~/.agents/skills` (user) per official docs; third-party guides also cite
  `~/.codex/skills`. Invoke with `$skill-name`
  ([docs](https://learn.chatgpt.com/docs/build-skills)). Path set unverified.
- Codex has lifecycle hooks with the same event names as Claude Code
  (`SessionStart`, `PreToolUse`, `PostToolUse`, `UserPromptSubmit`, `Stop`,
  `PreCompact`, ...), configured in `~/.codex/hooks.json` or
  `<repo>/.codex/hooks.json`; plugins can bundle `hooks/hooks.json`; non-managed
  hooks need trust via `/hooks` ([docs](https://learn.chatgpt.com/docs/hooks)).
  Stdin schema parity with Claude Code is unverified and must be checked.
- Codex plugin manifest `.codex-plugin/plugin.json` with `skills`, `mcpServers`,
  `interface` block, plus `agents/openai.yaml` (seen in the Expo plugin).
- Cursor reads `AGENTS.md` at the project root automatically, and
  `.cursor/rules/*.mdc` with `alwaysApply`, `globs`, `description`
  ([rules](https://cursor.com/docs/rules)). Hooks live in `.cursor/hooks.json`
  or `~/.cursor/hooks.json` with `beforeShellExecution`, `beforeMCPExecution`,
  `afterFileEdit`, `stop` ([hooks](https://cursor.com/docs/hooks)). Commit
  attribution is on by default; CLI users disable it with
  `attribution.attributeCommitsToAgent: false` in `~/.cursor/cli-config.json`.
- `AGENTS.md` is now stewarded by the Agentic AI Foundation under the Linux
  Foundation and read by Codex, Cursor, Copilot, Jules, Zed, Windsurf, Aider,
  Warp and others ([agents.md](https://agents.md/)). Gemini CLI uses
  `GEMINI.md`; Copilot reads `AGENTS.md` and `.github/copilot-instructions.md`.
- Agent Skills is an open spec ([agentskills.io](https://agentskills.io));
  `npx skills add <name>` from [vercel-labs/skills](https://github.com/vercel-labs/skills)
  installs one SKILL.md into every detected tool's directory. Two conventions
  coexist: tool-native dirs and the universal `.agents/skills`.

Design consequence: the same Python hook scripts can serve Claude Code and
Codex; Cursor gets a shell-execution hook for commits and an `AGENTS.md` block
for voice; every other AGENTS.md reader gets the voice block for free.

## 5. Names

Checked on GitHub, npm and by brand search. No GitHub API access this session,
so collisions may be under-reported.

| Name | GitHub | npm | Brand | Verdict |
|---|---|---|---|---|
| humai | user `humai` taken (inactive), `institutohumai` org | free | Several live companies named HumAI / Huma.AI | Crowded; poor search discoverability |
| noslop | several repos | taken (social media CLI) | none | Crowded |
| no-slop | `LeoStehlik/no-slop-ui` is close in concept | free | none | Crowded |
| devfilter | free | free | none | Clear |
| quietdev | inactive user | free | none | Mostly clear |
| humanskin | active unrelated user | free | none | Mostly clear |
| vibecheck | many | taken | VibeCheck app | Taken |
| deslop, unslop, slopstop, slopguard | many, same concept | taken | unslop.xyz | Taken |
| terse | generic | taken (2012, unrelated) | none | Crowded |
| plainspoken | active company org | free | Plainspoken Digital | Taken |
| noyap | inactive user, no repos | free | none | Mostly clear |
| yapstop | unrelated personal site | free | none | Mostly clear |
| degoop | free | free | none | Clear |
| curtcode | inactive user | free | none | Mostly clear |

Second pass on 2026-09-19 checked 56 more candidates against the GitHub
handle, exact-name repositories, npm, PyPI, crates.io and `.dev` DNS. Fully
clean: `antiyap`, `nopreamble`, `nofiller`, `tersemode`, `unwordy`, `yapoff`,
`degoop`, `gruffly` (a font shares the name), `devfilter` (one dead repo).
`drywit` is clean except a squatted empty GitHub org and a wine brand.
`devhush`, `sayless`, `nuffsaid`, `fullstop`, `zipit`, `nobot` are taken.

Decision: **unwordy**. GitHub handle free, no exact-name repositories, npm,
PyPI and crates.io free, `unwordy.dev` not registered at check time. Plain
English, no slang to age, reads as the opposite of what the plugin removes.

## 6. Style names

Presets named after the person on the team whose voice you want, not after
abstract tone words. Tone words ("concise", "professional") mean nothing to a
model that already thinks it is concise. Personas carry implicit rules.

| id | Display name | Voice |
|---|---|---|
| `lazy` | Lazy Dev | Fewest words that still work. Subject-only commits. Comments almost never. |
| `senior` | Grumpy Senior | Dry, direct, why not what. Points at file and line. Default preset. |
| `qa` | Precise QA | Steps, expected, actual, environment. No adjectives. |
| `lead` | Friendly Lead | Brief and warm. Names people, acknowledges, decides. |
| `formal` | Corporate | Complete sentences, neutral, audit-friendly. Still short. |
| `custom` | Your voice | Learned from the user's own messages, commits and comments. |
