# Release evidence

## 0.6.0

Checked 2026-10-11 with Python 3.9.6, Claude Code 2.1.296 and Codex CLI 0.162.1.

- 355 Python tests passed locally. [CI](https://github.com/assaio/unwordy/actions/runs/38173030212) passed on Python 3.9, 3.11 and 3.14.
- Claude marketplace and plugin strict validation passed.
- The standalone skill passed frontmatter validation and a clean Skills CLI installation.
- All 29 regex graders compiled; 39 valid/invalid behavior checks passed.
- All 84 demo selections rendered with correct language tags and supplied numbers and identifiers.
- Archive checks verified checksums, executable permissions and exclusion of local state. The checker ran from the extracted plugin ZIP.
- `doctor`, `check --explain` and whitespace checks passed.

## Writing quality

The live code-comment pilot ran once with the plugin and once without it.
Both passed all five graders. The exploratory full suite exposed grader defects,
which were corrected. The corrected rerun hit the Claude account session limit.
[Recorded observations](../benchmarks/observations/2026-10-11.json) distinguish
these outcomes from a valid comparison.

No measured improvement in answer quality or human naturalness score is
available. The 72 reference cases are authored evaluation inputs, not captured
model outputs. Technical checks and reference completeness do not establish
writing quality.

## Host enforcement

Codex and Cursor adapters have fixture coverage; live hook enforcement remains
unconfirmed. Installation and manifest validation do not prove invocation.
Use the [host smoke checklist](compatibility.md#live-smoke-checklist) to verify a route.
