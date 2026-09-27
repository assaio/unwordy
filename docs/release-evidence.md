# Release evidence: 0.4.0

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
