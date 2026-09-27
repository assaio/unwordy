# Rules

IDs remain stable across versions. `disable` takes a family or sub-id.
`rule.<id>: warn|block|off` overrides defaults; a sub-id overrides its family.
Disable wins over an effect. For H1, explicit effect wins over attribution policy.

| ID | Default | Surface | Finding |
|---|---|---|---|
| H1 | block | supported text/commit metadata | unsolicited agent attribution or robot marker |
| H2a | block | code comments | references to the task/request |
| H2b | warn | code comments | step numbering; standard/algorithm context exempt |
| H2c | block | code comments | edit history rather than current behavior |
| H2d | warn | code comments | ticket IDs unless allow_ticket_refs |
| H3 | block | code comments and prose files | chat leakage |
| H4a/H4b | warn | code comments | restating patterns; contract and constraint context exempt |
| S1 | warn | supported prose | em dash or spaced en dash |
| S2 | warn | supported prose | configured filler words |
| S3 | warn | code | comment/code ratio over 30%, at least eight added code lines |
| S4 | warn | code | docstring longer than a short function body |
| S5a–f | warn | commits, PRs, issues, comments | configured lengths, bullets, headings and labels |
| S6a–c | warn | commits and PRs | unnecessary scaffolding or process opener |
| S7a/S7b | strict block only | replies | long answer to a simple question or closing offer |

`strict` controls heuristic defaults (H2b, H2d, H4, S1–S7). Two denials of a
heuristic family on the same target downgrade further denials to warnings.
Hard defaults H1/H2a/H2c/H3 keep blocking. H1 supports per-surface disclosure
policy. Repository-required disclosure should use allow or disable H1.

License headers, directives, generated files, fixture paths, snapshots and
lock files are exempt. Fenced code and inline code are excluded from prose
rules. These are syntax heuristics, not AI detection. A human can trigger them.

Known MCP publishing names include create/update PR or issue and add/post
comment/review. Text fields and titles are checked together. Read/search/list
operations and unknown operations are skipped. `gh api` supports literal text
fields and known PR/issue endpoints; JSON through --input and file-valued API
fields are not followed. Shell writes through cat/tee/echo/printf are inspected;
in-place editors such as sed and arbitrary scripts are not.

English pattern coverage is broader than Polish/German coverage. The model
can follow other languages; the local checker does not fully understand them.
