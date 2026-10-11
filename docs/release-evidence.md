# Release evidence

## 0.6.0

Date: 2026-10-11. Python: 3.9.6. Claude Code: 2.1.296. Codex CLI: 0.162.1.

- Offline Python suite: 355 passed. CI runs Python 3.9, 3.11 and 3.14.
- Claude marketplace and plugin strict validation passed.
- The standalone skill passed the Codex skill-creator frontmatter validator.
  Claude-specific invocation fields in sibling skills remain host-specific.
- All 29 JavaScript regex graders compiled; 39 behavior checks passed, including
  wrong values, lost code, reversed facts and blank-line handling.
- All 84 demo selections rendered source/output with matching language tags and
  preserved supplied numbers and identifiers in the Node DOM harness.
- Release packaging tests verified committed content, ignored-state exclusion,
  executable permissions, standalone isolation and checksums. The separate
  OpenAI candidate excludes lifecycle hooks and includes its referenced icons.
- `doctor`, `check --explain` and diff whitespace checks passed.

The live code-comment pilot completed one run per arm; both passed all five
graders. The exploratory five-case comparison exposed two test defects: the PR
grader required a risk absent from its prompt, and reply length counted blank
lines. The source and graders were corrected. The optional skill-use indicator
now accepts either bundled writing entrypoint. These observations improved the
tests; the exploratory aggregate is not a valid quality comparison.

The corrected five-case rerun failed all ten runs on the Claude account's
session limit. Error text can satisfy negative regexes, so its reported scores
are excluded. The host did not preserve the earlier response traces or record
the exact model version in its aggregate report. Future comparisons must retain
outputs with `--keep-temp` and record the actual model. See the
[structured observations](../benchmarks/observations/2026-10-11.json).

No measured overall improvement or human naturalness score is claimed.
The 72 authored references are offline evaluation inputs, not model outputs.
Codex and Cursor live hook enforcement remains unconfirmed; their adapters have
fixture coverage. Directory submission scans and human review remain separate
from local package validation.

## 0.4.0

Date: 2026-09-27. Local Python: 3.9. Claude Code: 2.1.283. Codex CLI: 0.157.1.

- Offline Python suite: 316 passed. CI also checks Python 3.9, 3.11 and 3.14.
- Claude marketplace and plugin strict validation passed.
- A separate bundled Codex scaffold validator rejects hooks and explicit-only
  skill metadata supported by the current host documentation. Those fields are
  retained; this old helper is not evidence of a host ingestion failure.
- Claude plugin eval was attempted with and without the plugin. The sandboxed
  run could not read authentication; an approved retry reached the account but
  every model run hit the session limit. No quality score or comparison is valid.
  Positive fact graders exposed a JavaScript regex syntax mismatch; it was
  corrected and checked offline before release.
- Codex and Cursor live enforcement remains unconfirmed. Fixture tests cover
  their adapters. Cursor permission allow does not imply warning delivery.
- Human ratings for the public corpus are not collected. Reference examples
  and offline completeness checks are not measured naturalness results.

Repeat model comparisons after account quota is available. Run the disposable
host checklist in compatibility.md to verify each actual host route.

- Clean Skills CLI install of the standalone skill succeeded in a temporary
  project, with no plugin root or sibling skills.
- Demo was inspected in headless Chrome; all 16 role/tone/language selections
  rendered source and output in a DOM harness. No human style ratings follow
  from this UI check.
