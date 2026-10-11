"""Offline completeness checks and blinded review sheets for captured model output."""

import argparse
import ast
import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VARIANTS = ("baseline", "profile", "hooks")


def read_rows(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def literal_present(text, token):
    return re.search(r"(?<!\w)" + re.escape(token) + r"(?!\w)", text, re.I) is not None


def code_preserved(case, text):
    if "code_source" not in case:
        return True
    fenced = re.fullmatch(r"\s*```(?:python)?\s*\n(.*?)\n```\s*", text, re.S)
    code = fenced.group(1) if fenced else text
    try:
        return ast.dump(ast.parse(code)) == ast.dump(ast.parse(case["code_source"]))
    except SyntaxError:
        return False


def ordered(outputs):
    return sorted(outputs, key=lambda row: hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest())


def score(cases, outputs):
    indexed = {case["id"]: case for case in cases}
    seen, results = set(), []
    for row in outputs:
        run = row.get("run", 1)
        if not isinstance(run, int) or isinstance(run, bool) or not 1 <= run <= 100:
            raise ValueError("run must be an integer from 1 to 100")
        key = (row["id"], row["variant"], run)
        if key in seen or row["variant"] not in VARIANTS or row["id"] not in indexed:
            raise ValueError(f"duplicate or unknown output: {key}")
        seen.add(key)
        for field in ("model", "host", "host_version", "date", "output"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{key}: missing {field}")
        text = row["output"]
        case = indexed[row["id"]]
        missing = [token for token in case["required_literals"] if not literal_present(text, token)]
        failed = [pattern for pattern in case.get("required_patterns", []) if not re.search(pattern, text, re.I | re.S)]
        forbidden = [pattern for pattern in case.get("forbidden_patterns", []) if re.search(pattern, text, re.I | re.S)]
        preserves_code = code_preserved(case, text)
        results.append({"id": row["id"], "variant": row["variant"], "run": run, "missing": missing,
                        "failed_patterns": failed, "forbidden_patterns": forbidden,
                        "code_preserved": preserves_code,
                        "unchanged": text == case["source"] if case.get("clean_should_stay") else None,
                        "complete": not missing and not failed and not forbidden and preserves_code,
                        "characters": len(text)})
    return results


def blind(outputs, directory):
    directory.mkdir(parents=True, exist_ok=True)
    key = []
    with (directory / "review.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["sample", "case", "output", "completeness_1_5", "naturalness_1_5", "readability_1_5", "voice_1_5", "invented_claims", "unnecessary_changes", "notes"])
        for i, row in enumerate(ordered(outputs), 1):
            sample = f"sample-{i:03d}"
            writer.writerow([sample, row["id"], row["output"], "", "", "", "", "", "", ""])
            key.append({"sample": sample, "id": row["id"], "variant": row["variant"], "run": row.get("run", 1)})
    (directory / "key.json").write_text(json.dumps(key, indent=2) + "\n")


def ratings(outputs, path):
    fields = ("completeness_1_5", "naturalness_1_5", "readability_1_5", "voice_1_5")
    samples = {f"sample-{i:03d}": row for i, row in enumerate(ordered(outputs), 1)}
    groups, seen = {}, set()
    with path.open(newline="", encoding="utf-8") as handle:
        for rating in csv.DictReader(handle):
            sample = rating.get("sample")
            if sample not in samples or sample in seen:
                raise ValueError(f"unknown or duplicate rating: {sample}")
            row = samples[sample]
            if rating.get("case") != row["id"] or rating.get("output") != row["output"]:
                raise ValueError(f"{sample}: rating does not match the captured output")
            values = {field: int(rating[field]) for field in fields}
            if any(value not in range(1, 6) for value in values.values()):
                raise ValueError(f"{sample}: ratings must be from 1 to 5")
            flags = {field: rating[field].strip().lower() for field in ("invented_claims", "unnecessary_changes")}
            if any(value not in ("yes", "no") for value in flags.values()):
                raise ValueError(f"{sample}: claim and change flags must be yes or no")
            seen.add(sample)
            groups.setdefault(row["variant"], []).append(dict(values, **flags))
    if seen != set(samples):
        raise ValueError("ratings are incomplete")
    return {variant: {"count": len(rows),
                      "means": {field: sum(row[field] for row in rows) / len(rows) for field in fields},
                      "invented_claims": sum(row["invented_claims"] == "yes" for row in rows),
                      "unnecessary_changes": sum(row["unnecessary_changes"] == "yes" for row in rows)}
            for variant, rows in groups.items()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("outputs", type=Path)
    parser.add_argument("--cases", type=Path, default=ROOT / "benchmarks/cases.jsonl")
    parser.add_argument("--blind", type=Path, help="write a human review CSV and a separate variant key")
    parser.add_argument("--variants", nargs="+", choices=VARIANTS, default=list(VARIANTS))
    parser.add_argument("--ratings", type=Path, help="summarize a completed blinded human review CSV")
    args = parser.parse_args()
    try:
        outputs = read_rows(args.outputs)
        if not outputs:
            raise ValueError("no captured outputs")
        results = score(read_rows(args.cases), outputs)
        cases = read_rows(args.cases)
        if any(row["variant"] not in args.variants for row in outputs):
            raise ValueError("captured variant is not selected by --variants")
        runs = range(1, max(row["run"] for row in results) + 1)
        present = {(row["id"], row["variant"], row["run"]) for row in results}
        missing_outputs = [{"id": case["id"], "variant": variant, "run": run} for case in cases
                           for variant in args.variants for run in runs if (case["id"], variant, run) not in present]
        comparable = len({(row["model"], row["host"], row["host_version"]) for row in outputs}) == 1
        if args.blind:
            blind(outputs, args.blind)
        data = {"results": results, "complete": sum(row["complete"] for row in results),
                          "total": len(results), "missing_outputs": missing_outputs,
                          "same_model_and_host": comparable,
                          "unnecessary_clean_changes": sum(row["unchanged"] is False for row in results)}
        if args.ratings:
            data["human_ratings"] = ratings(outputs, args.ratings)
        print(json.dumps(data, ensure_ascii=False, indent=2))
        return 0 if all(row["complete"] for row in results) and not missing_outputs and comparable else 1
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"benchmark: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
