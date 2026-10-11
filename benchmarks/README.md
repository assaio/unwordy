# Evaluation

`cases.jsonl` contains 72 fictional cases, split evenly between English and
Polish, with 59 distinct reference outputs. It covers developer, QA, design and
lead writing; lazy and personal voices; required PR templates and disclosure;
sparse inputs, long reports, exact errors and URLs; and four Python comment
cases that must preserve code behavior. Reference outputs are authored
examples, not captured model results. All reference facts come from the source.

## Capture comparable output

Use the same model and host version for baseline without the plugin, resolved
profile/skills, and profile plus enabled host hooks. Use an isolated repository,
identical source prompts and separate fresh sessions. Supply the case role,
tone, language and any `profile` settings. Tool publishing cases can exercise
pre-tool hooks; plain final-answer rewriting does not demonstrate enforcement.

Record each captured output as JSONL:

```json
{"id":"design-comment-en-clean","variant":"profile","run":1,"model":"actual model","host":"actual host","host_version":"actual version","date":"YYYY-MM-DD","output":"captured output"}
```

`run` defaults to 1. For repeated comparisons, number runs consecutively from
1 and capture every selected case and arm in each run. Default arms are
`baseline`, `profile`, `hooks`; select two when the host cannot exercise hooks.

```sh
python3 scripts/benchmark.py captured.jsonl --blind /tmp/unwordy-review
python3 scripts/benchmark.py captured.jsonl --variants baseline profile
```

## What the offline score checks

Required literals use word boundaries, so `12/100` cannot satisfy `2/10`.
Case-specific patterns check expected/actual bindings, ordered retry delays
and selected unsupported claims. Python cases compare parsed ASTs with the
source, allowing comment edits while rejecting deleted or changed executable
code. Clean cases marked `clean_should_stay` report unnecessary changes.

The JSON report records each failure, missing case/arm/run combinations and
whether model and host versions match. Exit 0 means the selected comparison is
complete and all fact/code checks pass; 1 means a failed check, incomplete arm
or version mismatch; 2 means invalid input. Empty outputs cannot pass.

These checks can reject equivalent wording and catch only known relationships
and inventions. AST equality checks structure, not general program equivalence.
Changes to clean text are reported separately and do not fail completeness.
Do not call this a naturalness score or report a partial arm as a full benchmark.

## Collect human ratings

Give reviewers the source cases and `review.csv`, without `key.json`. The sheet
orders captured samples without variant labels. Keep the key with the
coordinator and use the same captured JSONL when aggregating ratings.

Recruit actual developer, QA and design readers. Rate completeness, naturalness,
readability and voice from 1 to 5. Fill `invented_claims` and
`unnecessary_changes` with `yes` or `no`; use notes for concrete examples.
Do not substitute model judgments for human ratings.

```sh
python3 scripts/benchmark.py captured.jsonl --ratings /tmp/unwordy-review/review.csv
```

Aggregation requires every sample exactly once and verifies that its case and
output still match the capture. It reports means and claim/change counts per
variant. For two selected arms, also pass `--variants baseline profile`.
Track false blocks in separate host logs and assess them against valid text.

## Host evals

Five cases under `evals/` exercise commit, PR, tracker, code-comment and reply
guidance. Their 29 regex graders include positive retention checks;
`node scripts/check-evals.mjs` also runs 39 valid/invalid behavior assertions.
These reject known false passes such as `# deleted`, a changed retry schedule
or a default value removed from a reply.

```sh
claude plugin eval . --runs 1 --ablation with-without --no-publish --keep-temp
```

This uses your host account. Authentication errors and quota failures are
failed runs, not quality measurements. Record actual versions, outputs and
observations in release evidence. Keep the captured outputs so grader failures
can be reviewed; the host deletes temporary traces without `--keep-temp`.
No improvement claim follows from passing
reference examples or grader checks. Human ratings have not been collected.
