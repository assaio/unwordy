---
# Audit-friendly trackers: complete sentences, ticket ids allowed, English.
preset: formal
strict: warn
language: en
allow_ticket_refs: true     # the tracker id is the audit trail
commit.max_subject: 72
pr.max_body_lines: 16       # room for the risk and rollback lines reviewers expect
---
Complete sentences, neutral register, no slang. State decision, reason, next
step. Fit for Jira and audit trails. No marketing vocabulary, no emoji.
