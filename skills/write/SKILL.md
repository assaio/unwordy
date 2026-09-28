---
name: write
description: Follow the team's writing conventions in commits, PRs, reviews, bug reports, design handoffs and work replies. Preserve evidence and personal voice.
user-invocable: false
---

Write for the person who will act on the message. Preserve facts, uncertainty,
negations, commitments, exact errors and test evidence. Never invent details,
experience or testing to make an answer sound natural.

## Resolve the voice

Repository requirements (AGENTS.md, CLAUDE.md, CONTRIBUTING, templates and
commitlint) win. Then use the active profile supplied at session start. If it
is missing, read `$UNWORDY_STYLE`, else the nearest `.unwordy.md` up to the git
root, else `$XDG_CONFIG_HOME/unwordy/style.md` (default `~/.config/unwordy/style.md`).
The first file wins. If the local unwordy CLI is available, `unwordy voice`
prints the resolved instructions. Otherwise interpret the profile directly.
With no profile, use a direct, specific voice and enough context for the task.
A custom body supplies the voice; role and tone are independent preferences.
Respect disabled rules and per-surface limits. Required content wins over brevity.

## Surfaces

- Commits: follow local subject conventions; add a body for a non-obvious reason.
  Keep the user's Git identity and required disclosure. Commit only when requested
  or required by the repository workflow.
- PRs: retain what changed, why, risk and observed test evidence. Use the repository
  template. Without one, choose paragraphs or bullets that help review.
- Reviews: identify the change needed and its reason. Keep a useful acknowledgement
  in a warm voice; remove praise that does not help the discussion.
- Bugs and test results: retain reproduction, expected/actual, environment,
  versions, frequency and exact errors. Numbered steps and descriptive terms help.
- Design handoffs: retain states, behavior, rationale, accessibility and constraints.
- Decisions: retain the decision, trade-off, owner and next step when supplied.
- Code comments: explain constraints, contracts and traps. Public API documentation,
  algorithm steps and workaround references may be necessary. Remove restatement.
- Replies: answer first, then enough context. Preserve intentional warmth, casing
  and punctuation from the profile. Length follows the reader's task.

Before sending, check that shortening did not lose a fact, qualification or
required section. Do not change technical strings, quotes or links for style.
