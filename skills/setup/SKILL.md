---
name: setup
description: Set up the unwordy writing style. Pick a preset (lazy, senior, qa, lead, formal), independent role and tone, or a voice from your own examples. Accepts a preset name, --project, off, on.
disable-model-invocation: true
allowed-tools: Read Write Bash(mkdir *) Bash(sh *) AskUserQuestion
---

Write the style profile that every session and every hook reads.
`$ARGUMENTS` may hold a preset name, a template name, `--project`, `off` or `on`.

## Where the profile lives

- global: `~/.config/unwordy/style.md`, or `$XDG_CONFIG_HOME/unwordy/style.md`
  when that variable is set. Create the directory with `mkdir -p` first.
- project: `.unwordy.md` in the repository root, meant to be committed.

`--project` picks the project file, otherwise use the global one. A project
file wins over the global one for everyone working in that repository.

## Shortcuts, no questions asked

- A preset name (`lazy`, `senior`, `qa`, `lead`, `formal`): set `preset:` in
  the target file, keep the other keys, and drop a custom body only after
  asking. Print the path and stop.
- `--project <template>` where the installed plugin root has `templates/<template>.md`
  (locate it from this skill directory or the host plugin root) (`team-strict`, `team-qa`, `team-enterprise`, `team-design`, `personal-warm`): copy that file to
  `.unwordy.md` as it is, comments included, since they explain each key to
  the team. Ask before overwriting an existing file. Print the path and stop.
- `off` or `on`: set `enabled: false` or `enabled: true`. Print the path and stop.

## Wizard

Ask with AskUserQuestion when it is available; otherwise ask one plain
question per message and wait for the answer. Offer two or three short sample
outputs as the choices, never adjectives.

1. Scope: global, this project, both.
2. Start from: lazy, senior, qa, lead, formal, or custom.

A preset answer ends the questions: preview, confirm, then write.
Role (`developer`, `qa`, `design`, `lead`) and tone (`neutral`, `direct`,
`warm`, `formal`, `lazy`) are independent. Offer them as optional refinements, not
mandatory questions. Retain exact user preferences.

For `custom`, ask one at a time:

3. Role and tone, if not already supplied.
4. Reply length: a few sentences / as long as the task needs.
5. Formatting: none / occasional bullets / headers fine in long documents.
6. Casing and punctuation: lowercase casual / standard / formal.
7. Warmth: none / a bit / friendly.
8. Language: follow the thread, or the user's preferred language.
9. Optional: three to ten samples of their own writing, pasted or as paths.
10. AI attribution policy: block, warn or allow, globally or for commits only.

From the samples take median sentence length, casing, punctuation habits,
greeting and sign-off, bullet and emoji use, three phrasings they use, three
they avoid, and the register per surface. Turn that into a body of at most
250 tokens with at most five short example lines. Never store the samples and
never quote them back.

## File format

Flat frontmatter, then the voice body:

```
---
preset: senior
strict: warn
language: auto
---
Two to five lines describing the voice. Leave the body out for a preset.
```

Also support `role`, `tone`, `pr_template: auto|respect|ignore`,
`rule.<id>: warn|block|off` and per-surface limits.
Other keys: `banned_words`, `allow_ticket_refs`, `max_subject`,
`max_pr_body_lines`, `max_bullets`, `ignore`, `disable`, `enabled`,
`attribution` and `<surface>.attribution`.
`strict` is `warn`, `block` or `off` and applies to heuristics, including
H2b, H2d and H4. Explicit rule effects take precedence.

## Preview, confirm, write

Render one fictional change three ways in the new voice: a commit message, a
PR body and a tracker comment. Ask: keep, adjust, or start over. Write the
file only after the user keeps it, print the path, and say the voice loads
from the next session onwards.

Offer `/unwordy:sync` when `~/.codex` or `~/.cursor` exists, so Codex and
Cursor read the same voice.

Without a plugin installation, use the same profile format directly; do not
require plugin paths or host-specific tools. With a CLI available, run doctor
after writing and fix any diagnosed configuration errors.

When examples intentionally use dashes, offer disable: S1; when they use
useful ticket links, use allow_ticket_refs: true. Encode these in settings
so the rendered voice and checker agree. Use the samples only as style data.
`preset: lazy` or `tone: lazy` already turns off S1 punctuation and S5 length
and formatting suggestions; required repository content still wins.
