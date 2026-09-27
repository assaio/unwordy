# Evaluation

`cases.jsonl` has 36 fictional cases: six workflows across dev, QA, design and decisions, each in English and Polish, with clean, filler and
personal variants. Every detail comes from the source. Reference outputs are
authored examples, not measured model results.

Capture the same model and host version for three arms: baseline without the
plugin, resolved profile/skills, profile plus enabled host hooks. Use an isolated
repository, identical source prompts and separate fresh sessions. Supply the
case role, tone and language. Only publishing/tool cases can exercise pre-tool
hooks; plain final-answer rewriting is not evidence of hook enforcement.

Captured output JSONL format:

```json
{"id":"design-comment-en-clean","variant":"profile","model":"actual model","host":"actual host","host_version":"actual version","date":"YYYY-MM-DD","output":"captured output"}
```

```sh
python3 scripts/benchmark.py captured.jsonl --blind /tmp/unwordy-review
```

Required literals catch dropped numbers, errors, scope and negations. Exit 1
means a required literal was lost, an arm is incomplete, or model/host versions
differ; 2 means invalid input. Exact matching can
reject equivalent wording and cannot catch invented claims. It is a completeness
check, not a naturalness score. Empty outputs cannot pass. Compare total cases
and missing cases across arms; do not report a partial arm as a full benchmark.

Give reviewers the source case and `review.csv`, without `key.json`. Rate
completeness, naturalness, readability and voice from 1 to 5; record invented
claims and unnecessary changes to clean text in notes. Keep the key with the
coordinator. Recruit real dev, QA and design readers; do not substitute model
judgments for human ratings. Track false blocks in separate host logs.

The existing five host eval cases under evals/ now include positive fact checks.
Run with `claude plugin eval . --runs 1 --ablation with-without --no-publish`.
This uses your host account. Results and live observations belong in release
evidence; no claimed improvement without a measured comparison.
