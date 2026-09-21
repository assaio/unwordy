---
description: A PR title and body for a retry change, without template scaffolding.
max_turns: 6
allowed_tools: [Skill]
---
Write the pull request title and body for my branch. The change: the webhook dispatcher now retries delivery three times with backoff of 1s, 2s and 4s, because the receiving host returns 502 for a few seconds after each of its deploys and we were dropping those events. The receiver is idempotent on event id, see webhook/receiver.go line 88. Tested against staging with a forced 502 and with the new cases in sync/retry_test.go.
