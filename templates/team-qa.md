---
# A QA or support team: reproducible reports, exact strings, numbered steps.
preset: qa
strict: warn
language: auto              # tracker threads keep their own language
max_bullets: 10             # numbered steps are the point here
allow_ticket_refs: true     # test ids in fixtures and comments are fine
---
Bugs: steps, expected, actual, environment, and one exact error message in a
code block. Numbered steps allowed. No adjectives. Say when you are guessing.
Exact versions and exact messages, never paraphrased.
