# Profile reference

Profiles use flat frontmatter and an optional voice body. The first existing
profile wins; project and personal profiles do not merge. Repository rules,
required templates and disclosure take priority. A body supplies personal
voice. Disabled rules and explicit preferences win over preset defaults.

Supported keys:

- `preset`: lazy, senior, qa, lead, formal, custom
- `role`: developer, qa, design, lead, auto
- `tone`: neutral, direct, warm, formal, lazy, auto
- `language`, `enabled`, `allow_ticket_refs`
- `strict`: warn, block, off
- `disable`: comma-separated rule IDs
- `attribution`: allow, warn, block
- `max_subject`, `max_pr_body_lines`, `max_bullets`
- Per-surface overrides such as `pr.max_body_lines` and `commit.attribution`
- `pr_template`: auto, respect, ignore
- Per-rule effects such as `rule.H4: warn` or `rule.H2d: off`
- `banned_words` and `ignore`

Treat configured length limits as preferences when required content needs
space. For S1, prefer comma, colon or period unless it is disabled; an
intentional personal dash may be preserved when S1 is disabled. Do not infer
that `strict: off` permits dropping required facts or disclosure.
`preset: lazy` and `tone: lazy` turn off S1 and S5 by default. An explicit
`rule.S1` or `rule.S5` setting can restore either check.
