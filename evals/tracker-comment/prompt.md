---
description: A reply to a reviewer in a tracker thread, without pleasantries.
max_turns: 6
allowed_tools: [Skill]
---
Write my reply to this Jira comment from a reviewer, ready to paste: "The retry logic looks off, it retries on 4xx too." What I did: moved the retry into the dispatcher, it now retries only on 5xx and connection errors, the cap is 3 attempts, and the config lives in sync.toml at line 12.
