---
name: setup
description: Set up the unwordy writing style. Pick a preset (lazy, senior, qa, lead, formal), a team template, or build a custom voice from your own writing. Accepts a preset name, --project, off, on.
disable-model-invocation: true
allowed-tools: Read Write Bash(mkdir *) AskUserQuestion
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
- `--project <template>` where `${CLAUDE_PLUGIN_ROOT}/templates/<template>.md`
  exists (`team-strict`, `team-qa`, `team-enterprise`): copy that file to
  `.unwordy.md` as it is, comments included, since they explain each key to
  the team. Ask before overwriting an existing file. Print the path and stop.
- `off` or `on`: set `enabled: false` or `enabled: true`. Print the path and stop.

## Wizard

Ask with AskUserQuestion when it is available; otherwise ask one plain
question per message and wait for the answer. Offer two or three short sample
outputs as the choices, never adjectives.

1. Scope: global, this project, both.
2. Start from: lazy, senior, qa, lead, formal, or custom.

A preset answer ends the questions: write the file, then preview and confirm.

For `custom`, ask one at a time:

3. Reply length: one-liners / a few sentences / as long as it takes.
4. Formatting: none / occasional bullets / headers fine in long documents.
5. Casing and punctuation: lowercase casual / standard / formal.
6. Warmth: none / a bit / friendly.
7. Language: en / pl / follow the thread.
8. Optional: three to ten samples of their own writing, pasted or as paths.

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

Other keys: `banned_words`, `allow_ticket_refs`, `max_subject`,
`max_pr_body_lines`, `max_bullets`, `ignore`, `disable`, `enabled`.
`strict` is `warn`, `block` or `off` and applies to the soft rules only.

## Preview, confirm, write

Render one fictional change three ways in the new voice: a commit message, a
PR body and a tracker comment. Ask: keep, adjust, or start over. Write the
file only after the user keeps it, print the path, and say the voice loads
from the next session onwards.

Offer `/unwordy:sync` when `~/.codex` or `~/.cursor` exists, so Codex and
Cursor read the same voice.
