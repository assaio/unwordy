"""Offline completeness checks and blinded review sheets for captured model output."""

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline", "profile", "hooks")


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def score(cases, outputs):
    indexed = {case["id"]: case for case in cases}
    seen, results = set(), []
    for row in outputs:
        key = (row["id"], row["variant"])
        if key in seen or row["variant"] not in VARIANTS or row["id"] not in indexed:
            raise ValueError(f"duplicate or unknown output: {key}")
        seen.add(key)
        for field in ("model", "host", "host_version", "date", "output"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{key}: missing {field}")
        text = row["output"]
        missing = [token for token in indexed[row["id"]]["required_literals"] if token.casefold() not in text.casefold()]
        results.append({"id": row["id"], "variant": row["variant"], "missing": missing,
                        "complete": not missing, "characters": len(text)})
    return results


def blind(outputs, directory):
    directory.mkdir(parents=True, exist_ok=True)
    ordered = sorted(outputs, key=lambda row: hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest())
    key = []
    with (directory / "review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "case", "output", "completeness_1_5", "naturalness_1_5", "readability_1_5", "voice_1_5", "notes"])
        for i, row in enumerate(ordered, 1):
            sample = f"sample-{i:03d}"
            writer.writerow([sample, row["id"], row["output"], "", "", "", "", ""])
            key.append({"sample": sample, "id": row["id"], "variant": row["variant"]})
    (directory / "key.json").write_text(json.dumps(key, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", type=Path)
    parser.add_argument("--cases", type=Path, default=ROOT / "benchmarks/cases.jsonl")
    parser.add_argument("--blind", type=Path, help="write a human review CSV and a separate variant key")
    args = parser.parse_args()
    try:
        outputs = read_rows(args.outputs)
        if not outputs:
            raise ValueError("no captured outputs")
        results = score(read_rows(args.cases), outputs)
        cases = read_rows(args.cases)
        present = {(row["id"], row["variant"]) for row in results}
        missing_outputs = [{"id": case["id"], "variant": variant} for case in cases
                           for variant in VARIANTS if (case["id"], variant) not in present]
        comparable = len({(row["model"], row["host"], row["host_version"]) for row in outputs}) == 1
        if args.blind:
            blind(outputs, args.blind)
        print(json.dumps({"results": results, "complete": sum(row["complete"] for row in results),
                          "total": len(results), "missing_outputs": missing_outputs,
                          "same_model_and_host": comparable}, ensure_ascii=False, indent=2))
        return 0 if all(row["complete"] for row in results) and not missing_outputs and comparable else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
