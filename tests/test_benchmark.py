import csv
import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("benchmark", ROOT / "scripts/benchmark.py")
benchmark = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(benchmark)


def captured(case, output):
    return {"id": case["id"], "variant": "profile", "output": output,
            "model": "test-double", "host": "offline-unit-test", "host_version": "1", "date": "2026-09-27"}


def test_references_preserve_required_information_and_empty_output_cannot_pass():
    cases = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")
    assert len(cases) == 72 and len({row["id"] for row in cases}) == 72
    assert len({row["reference"] for row in cases}) >= 54
    assert all(row["complete"] for row in benchmark.score(cases, [captured(case, case["reference"]) for case in cases]))
    with pytest.raises(ValueError, match="missing output"):
        benchmark.score(cases, [captured(cases[0], "")])


def test_lost_negation_is_a_completeness_failure():
    cases = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")
    case = next(row for row in cases if "No user study" in row["reference"])
    output = case["reference"].replace("No user study was run.", "A user study was run.")
    assert benchmark.score(cases, [captured(case, output)])[0]["missing"] == ["No user study"]


def test_blind_sheet_omits_variant_and_keeps_separate_key(tmp_path):
    case = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")[0]
    benchmark.blind([captured(case, case["reference"])], tmp_path)
    assert "profile" not in (tmp_path / "review.csv").read_text()
    assert json.loads((tmp_path / "key.json").read_text())[0]["variant"] == "profile"


@pytest.mark.parametrize("change", [
    lambda text: text.replace("2/10", "12/100"),
    lambda text: text.replace("Expected: dashboard. Actual: login screen", "Expected: login screen. Actual: dashboard"),
])
def test_changed_frequency_or_expected_actual_does_not_pass(change):
    cases = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")
    case = next(row for row in cases if row["id"] == "qa-issue-en-clean")
    assert not benchmark.score(cases, [captured(case, change(case["reference"]))])[0]["complete"]


def test_retry_order_and_code_behavior_are_checked():
    cases = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")
    retry = next(row for row in cases if row["id"] == "retry-order-and-scope-en")
    assert not benchmark.score(cases, [captured(retry, retry["reference"].replace("1s, 2s, 4s", "4s, 2s, 1s"))])[0]["complete"]
    code = next(row for row in cases if row["id"] == "python-comment-contract-en")
    for output in ("# deleted", code["reference"].replace("return None", "return True")):
        assert not benchmark.score(cases, [captured(code, output)])[0]["complete"]
    assert benchmark.code_preserved(code, "```python\n" + code["reference"].rstrip() + "\n```")


def test_clean_changes_and_invented_known_claims_are_reported():
    cases = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")
    case = next(row for row in cases if row["id"] == "sparse-bug-source-en")
    result = benchmark.score(cases, [captured(case, case["reference"] + " HTTP 500 on Safari 18.")])[0]
    assert result["unchanged"] is False
    assert result["forbidden_patterns"] and not result["complete"]


def test_distinct_runs_are_accepted_and_duplicate_runs_are_rejected():
    case = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")[0]
    row = captured(case, case["reference"])
    assert len(benchmark.score([case], [row, dict(row, run=2)])) == 2
    with pytest.raises(ValueError, match="duplicate"):
        benchmark.score([case], [row, dict(row, run=1)])


def test_human_ratings_require_complete_matching_samples(tmp_path):
    case = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")[0]
    outputs = [captured(case, case["reference"])]
    benchmark.blind(outputs, tmp_path)
    path = tmp_path / "review.csv"
    with path.open(newline="") as handle:
        rows = list(csv.DictReader(handle))
    with pytest.raises(ValueError):
        benchmark.ratings(outputs, path)
    for row in rows:
        row.update(completeness_1_5="5", naturalness_1_5="4", readability_1_5="4", voice_1_5="3",
                   invented_claims="no", unnecessary_changes="no")
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    summary = benchmark.ratings(outputs, path)
    assert summary["profile"]["means"]["naturalness_1_5"] == 4
    with pytest.raises(ValueError, match="does not match"):
        benchmark.ratings([dict(outputs[0], output="a different answer")], path)


def test_clean_references_agree_with_their_checker_profiles(tmp_path):
    from unwordy import extract, lint, profile

    cases = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")
    for case in cases:
        if not case["clean_should_stay"]:
            continue
        (tmp_path / ".unwordy.md").write_text(case.get("profile", "---\n---\n"))
        prof = profile.resolve(tmp_path)
        text = case["reference"]
        if case["surface"] == "code":
            change = extract._diff(str(tmp_path / "sample.py"), "", text)
            findings = lint.lint_change(change, prof.settings, tmp_path)
        else:
            title, _, body = text.partition("\n") if case["surface"] == "commit" else ("", "", text)
            findings = lint.lint_message(extract.Message(case["surface"], "corpus", title, body), prof.settings)
        assert [f for f in findings if lint.action(f, prof.settings) != "ignore"] == [], case["id"]


def test_selected_arms_require_balanced_runs(tmp_path, monkeypatch, capsys):
    case = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")[0]
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(case) + "\n")
    path = tmp_path / "captured.jsonl"
    rows = [dict(captured(case, case["reference"]), variant=variant, run=run)
            for variant in ("baseline", "profile") for run in (1, 2)]
    monkeypatch.setattr(sys, "argv", ["benchmark.py", str(path), "--cases", str(cases), "--variants", "baseline", "profile"])
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    assert benchmark.main() == 0
    capsys.readouterr()
    path.write_text("\n".join(json.dumps(row) for row in rows[:-1]) + "\n")
    assert benchmark.main() == 1
    assert json.loads(capsys.readouterr().out)["missing_outputs"] == [{"id": case["id"], "variant": "profile", "run": 2}]


def test_model_host_mismatch_is_not_a_comparable_result(tmp_path, monkeypatch, capsys):
    case = benchmark.read_rows(ROOT / "benchmarks/cases.jsonl")[0]
    cases = tmp_path / "cases.jsonl"
    cases.write_text(json.dumps(case) + "\n")
    path = tmp_path / "captured.jsonl"
    rows = [dict(captured(case, case["reference"]), variant="baseline"),
            dict(captured(case, case["reference"]), host_version="different")]
    path.write_text("\n".join(json.dumps(row) for row in rows) + "\n")
    monkeypatch.setattr(sys, "argv", ["benchmark.py", str(path), "--cases", str(cases), "--variants", "baseline", "profile"])
    assert benchmark.main() == 1
    assert json.loads(capsys.readouterr().out)["same_model_and_host"] is False
