# Directory submissions

Package: unwordy 0.6.0, MIT, https://github.com/assaio/unwordy.
Demo: https://assaio.github.io/unwordy/. Release artifacts:

- `unwordy-0.6.0.zip`: full plugin and local checker, including host hooks.
- `unwordy-skill-0.6.0.zip`: portable standalone skill.
- `unwordy-openai-0.6.0.zip`: directory candidate with the standalone skill,
  Codex listing metadata and icons; no lifecycle hooks or local checker.
- `SHA256SUMS`: checksums for all three archives.

Do not claim live Codex/Cursor enforcement. The OpenAI candidate is prepared
for upload; portal scans and review determine whether it can be published.

## Submission copy

Name: unwordy

Short description: Your team's writing voice

Description: Personal and team writing profiles for coding agents. Choose role
and tone independently for commits, PRs, reviews, QA reports and design handoffs.
Preserve facts, test evidence, required templates and disclosure. Local Python
checks flag filler; optional host hooks inspect supported writes. The portable
skill works without the plugin. Python 3.9+; no runtime dependencies.

Examples: rewrite a PR without losing risk or test scope; preserve reproduction
steps in a bug report; write a design handoff with states and accessibility.

Privacy: local checks make no model/network calls. Setup and rewrite use the
existing host/model; selected samples are not stored in the style profile.

Validation: use the release's test count and compatibility evidence, not the
unavailable model comparison or an uncollected human rating.

## Routes and constraints

| Route | How to submit | Constraint |
|---|---|---|
| Skills.sh | Real public installation through npx skills add assaio/unwordy --skill unwordy | Automatic installation telemetry; not a reviewed acceptance |
| ccplugins/awesome-claude-code-plugins | Existing [PR #557](https://github.com/ccplugins/awesome-claude-code-plugins/pull/557), under Git Workflow | Pending maintainer review; update the existing submission for this release |
| Claude | https://claude.ai/directory/manage, Plugin bundle | Authenticated paid account and relevant organization role |
| OpenAI | https://platform.openai.com/plugins, Skills only; upload unwordy-openai-0.6.0.zip | Verified developer identity, Apps Management Write, scans and review |
| Cursor | https://cursor.com/marketplace/publish | Authenticated form and local testing; disclose unconfirmed live hook routes |
| [Awesome Claude Code](https://github.com/hesreallyhim/awesome-claude-code/blob/main/CONTRIBUTING.md) | Human web issue form | Human recommendations only; gh submission is explicitly disallowed |
| [travisvn/awesome-claude-skills](https://github.com/travisvn/awesome-claude-skills/blob/main/CONTRIBUTING.md) | Human submission after community adoption | 10 stars minimum and explicit ban on AI-assisted submission |
| [VoltAgent/awesome-agent-skills](https://github.com/VoltAgent/awesome-agent-skills#-contributing) | PR after demonstrated community usage | Prioritize community-adopted skills; current adoption evidence is insufficient |

Authenticated directory forms are not completed by a GitHub release or a PR.
No browser automation integration is available in this workspace to fill those
portals with the user's account. Do not report a prepared bundle as a submission.

The full plugin archive is for direct installation. OpenAI's current conversion
guide requires lifecycle hooks to be removed from public submissions. The
separate directory archive includes only the self-contained `unwordy` skill;
it does not depend on sibling skills or package executables. Choose the owning
organization in the portal, upload this archive, resolve scans and submit for
review. [OpenAI conversion guide](https://developers.openai.com/plugins/guides/submit-claude-plugin).

## Launch text

Show HN title: Unwordy — writing profiles and local checks for coding agents

Post draft: Unwordy gives coding agents a personal or team writing profile for
commits, PRs, QA reports and design handoffs. It keeps supplied facts, uncertainty
and required templates. The portable skill works on its own; a local Python
checker adds rule IDs and optional host hooks. Release 0.6.0 improves literal
protection, configuration consistency and fact/code evaluations. Codex and Cursor
hook enforcement still needs live verification. Useful feedback includes valid
comments or detailed bug reports that the checker flags.

Use this copy only in a relevant community and check its current posting rules.
Publishing a release or submitting a directory PR does not authorize unrelated
messages, repeated community posts or vote requests.

Current official guidance: [Claude](https://claude.com/docs/directory/publish),
[OpenAI](https://developers.openai.com/plugins/deploy/submission),
[Cursor](https://prod.cursor.com/docs/reference/plugins),
[Skills](https://www.skills.sh/docs/faq).
