import importlib.util
import json
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
    assert len(cases) == 36 and len({row["id"] for row in cases}) == 36
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
