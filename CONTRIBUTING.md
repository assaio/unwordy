# Contributing

Python 3.9+, standard library at runtime. Prefer the existing naming and small
functions. Tests use pytest; Python 3.9 uses pytest 8. Match nearby test patterns.

```sh
python3 -m venv .venv
.venv/bin/python -m pip install 'pytest>=8,<9'
.venv/bin/python -m pytest -q
claude plugin validate --strict .
claude plugin validate --strict .claude-plugin/plugin.json
git diff --check
```

Tests run offline, with isolated homes and profiles. For a new rule or adapter,
add a meaningful matching case and a valid-text case, keep its stable ID, and
update docs/rules.md. Preserve required content, quotes, uncertainty and evidence.
Do not assert a hard denial for a heuristic unless the test config opts in.

The profile resolves voice and configuration in unwordy/profile.py. Surface
extraction is in extract.py, findings in lint.py, host decisions in hook.py,
and standalone commands in cli.py. Independent role and tone avoid separate
copies of writing instructions. The standalone skill must work when copied
alone; references belong inside its own directory.

Host payload tests do not prove host invocation. Follow the disposable live
smoke checklist in docs/compatibility.md, record exact versions and results in
docs/release-evidence.md, and do not infer enforcement from installation.
New installed versions are cached; reinstall or start a fresh local-plugin run.

The five existing eval cases use the host model and positive fact graders;
benchmarks/ has a 36-case corpus and offline completeness/blinded-review tooling.
Run model evals only when intended; keep private samples out of public artifacts.
See benchmarks/README.md for comparison methodology.

For release, keep all four manifests and CHANGELOG in agreement, run CI and
package only tracked release files. Exclude local environments, logs, results
and Git metadata. Keep compatibility claims scoped to observed evidence.
