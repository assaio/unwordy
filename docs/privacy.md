# Privacy and stored data

The Python checker and hook scripts make no network requests and call no model.
The host agent uses its usual model for setup and rewriting. Selected writing
samples are visible to that host and model under their own data policy.

The profile stores short preferences. Init asks which history entries to read
and does not store raw samples, private names, email addresses or links in it.
Hooks inspect proposed tool text; the Stop hook can read a local transcript tail.
They do not send it elsewhere. Denial state stores session IDs, target paths and
counts under the host plugin data directory or `~/.cache/unwordy/state`.
Old state is pruned after seven days at session start. Errors append tracebacks
to `unwordy.log`, capped by deleting a log above 1 MB before the next append.
Tracebacks can contain local paths and exception messages. Avoid private text in
exception messages and redact examples before opening public issues.

Unwordy has no telemetry. The third-party Skills CLI has installation telemetry
and an opt-out documented by its provider. Directory submissions and GitHub
traffic measurements are separate from the checker runtime.
