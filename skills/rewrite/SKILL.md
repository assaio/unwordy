---
name: rewrite
description: Rewrite text so it reads like a terse developer wrote it. Use when asked to rewrite, de-slop, shorten or make human a commit message, PR body, comment, reply or pasted text.
---

Rewrite text into the user's unwordy voice. Keep every fact.

## What to rewrite

`$ARGUMENTS` picks the source:

- text in the message: rewrite that text
- a file path: rewrite only the comments and docstrings in it, never the code
- `--pr <n>`: read it with `gh pr view <n> --json title,body`, rewrite both
- `--last`: rewrite your own previous reply
- nothing: ask what to rewrite

## How

Load the `unwordy:write` skill for the target surface, then:

1. Keep facts, numbers, paths, error strings, links and code blocks exactly.
2. Cut preamble, restatement of the question, closing offers, "as requested",
   unsolicited attribution trailers and session links. Keep required disclosure.
3. Replace marketing words (`delve`, `leverage`, `seamless`, `robust`,
   `comprehensive`, `streamline`, `utilize`) with plain ones.
4. Replace em dashes with a comma, a colon or a full stop.
5. Turn bold-label bullets and header scaffolding into sentences, unless the
   repo's template requires them.
6. Keep the original language and the thread's register.
7. Cut the length by at least a third, or say in one line why you could not.

## Output

Print the rewrite only, in a code block when it is going somewhere else. Say
in one line what you dropped if you dropped anything that carried meaning.

Do not edit files, amend commits or update a pull request on your own: show
the rewrite, apply it after the user says so.
