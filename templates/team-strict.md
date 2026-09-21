---
# A team that wants the hooks to deny, not warn. Copy to .unwordy.md and commit.
preset: senior
strict: block               # soft rules deny too; use warn while people get used to it
max_subject: 60             # tighter than the default 72
pr.max_body_lines: 10       # only PR bodies; commits keep the default 12
disable: S3                 # comment density is noisy in generated clients
ignore: vendor/**, **/*.generated.*, **/*.pb.go
---
Dry and direct, why not what. Commit subject: <area>: <imperative>, under 60
characters, body only when the reason is not in the diff. PR body: what, why,
risk, how tested, no headers. Point at file and line instead of describing code.
