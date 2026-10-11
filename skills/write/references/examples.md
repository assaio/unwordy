# Before and after

These fictional inputs contain every fact used in their rewrites. A rewrite
can remove filler; it cannot fill gaps with plausible details.

## Commit message

Before:

```text
feat: Implement comprehensive retry mechanism for sync worker

This commit adds retries for the webhook host's 502 responses after deploys.
We seamlessly retry three times: 1s, 2s, 4s. Then the event id goes to the
dead letter log. Unit tests were added but not run.
```

After:

```text
feat: retry webhook delivery three times

The webhook host returns 502 after deploys. Backoff is 1s, 2s, 4s;
after that the event id goes to the dead letter log.
Unit tests added; not run.
```

## PR body

Before, with no required PR template:

```text
## Summary

This PR implements comprehensive retries for webhook delivery: three times,
with backoff of 1s, 2s and 4s. The host returns 502 for a few seconds after
each deploy, and we were dropping those events. Late responses can cause
duplicate deliveries. The receiver is idempotent on event id; see
webhook/receiver.go:88.

## Test plan

Tested a forced 502 against staging and the unit cases in sync/retry_test.go.
Production was not tested.
```

After:

```text
Retry webhook delivery three times: 1s, 2s, 4s. The host returns 502 for a
few seconds after each deploy, and we were dropping those events.

Risk: duplicate deliveries after a late response. The receiver is idempotent
on event id; see webhook/receiver.go:88.

Tested a forced 502 in staging and the cases in sync/retry_test.go.
Production was not tested.
```

When the repository requires Summary and Test plan, keep those headings.

## Issue with missing details

Before:

```text
The application crashes unexpectedly during sync. This appears to be related
to empty payloads, but we have not confirmed the cause. The error, environment
and frequency are unknown. It would be great if this could be addressed.
```

After:

```text
The application crashes during sync. Empty payloads may be involved; the cause is unconfirmed.
The error, environment and frequency are unknown.
```

Do not add reproduction steps, HTTP statuses, a stack trace or a version.

## Tracker or review comment

Before:

```text
Thanks for checking the retry scope. I've comprehensively updated the
implementation: retry now lives in the dispatcher so the receiver stays pure.
Only 5xx and connection errors are retried, capped at 3 attempts; configuration
is in sync.toml:12. This change has not been tested.
```

After, in a warm voice:

```text
Thanks for checking the retry scope. Moved retry into the dispatcher so the
receiver stays pure. It retries only 5xx and connection errors, capped at
3 attempts; config is in sync.toml:12. Not tested.
```

## Code comment

Before:

```python
# This function processes the payload and returns its data.
def parse(payload):
    # Check if payload is empty.
    # The host sends an empty body instead of a 404 when an event was deleted.
    if not payload:
        return None
    return payload.get("data")
```

After:

```python
def parse(payload):
    # The host sends an empty body instead of a 404 when an event was deleted.
    if not payload:
        return None
    return payload.get("data")
```

The executable code is unchanged. Keep the documented constraint.

## Reply

Before:

```text
Yes. Let me explain how the configurable retry limit works. It is defined as
sync.retry_limit in config.toml. The default is 3, and accepted values range
from 1 to 10. Let me know if you'd like a walkthrough!
```

After:

```text
Yes, `sync.retry_limit` in config.toml. Default 3, range 1 to 10.
```
