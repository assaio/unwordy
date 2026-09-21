---
name: write
description: Load before writing a commit message, PR title or body, issue, review or tracker comment, or a reply longer than three sentences.
user-invocable: false
---

Rules for text that reaches a person. Repo conventions (CLAUDE.md, AGENTS.md,
CONTRIBUTING, commitlint, the last twenty commits) win over everything here.

## Commits

- Imperative subject under 72 characters, no trailing period. Use a type
  prefix only where the repo already does.
- Body only when the why is not obvious from the diff: the constraint, the
  bug, the trade-off, the thing the next reader would get wrong.
- Never list the files you touched. The diff lists them.
- No attribution trailers, no session links, no emoji.

## PR title and body

- Title says the change, not the process.
- Body: what changed, why, risk, how you tested. Up to twelve lines, no
  headers, no `## Summary`, no `## Test plan`, unless the repo's template
  already has them.
- Point at `file:line` instead of describing code. Link the issue once.
- No check-box theatre, no bold-label bullets, no emoji.

## Issues, reviews and tracker comments

- Write in the thread's language and register. Answer the message you got.
- Bug reports: steps, expected, actual, environment, and one exact error
  message in a code block.
- Decisions: decision, reason, next step. One paragraph beats five bullets.
- Review comments: say what to change and why, in one or two sentences. Skip
  the compliment sandwich.

## Code comments and docstrings

- Only where the code cannot say why: a constraint, an invariant, a trap, an
  external contract.
- One line, timeless. No tickets, no dates, no "changed X to Y", no "as
  requested", no step numbers.
- Never restate the line below. Delete a stale comment instead of updating it.
- Docstrings: what it is for, in a sentence. Skip parameter lists that repeat
  the signature.

## Replies

- Answer first, then the reason if it is not obvious.
- One idea per sentence, plain words, no preamble, no closing offer.
- Say in one clause where you are unsure or where you guessed.

## Last pass

Cut every sentence that does not change what the reader does. A sentence that
survives only because it sounds thorough goes.

Before and after for each surface: [references/examples.md](references/examples.md).
