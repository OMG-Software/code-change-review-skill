#!/usr/bin/env python3
"""Score manually adjudicated code-review findings against evals/cases.json."""
from __future__ import annotations

import json
from pathlib import Path
import sys

# Do not accept filesystem paths from CLI/LLM arguments. Only this fixed, versioned
# repository corpus is opened; caller-supplied predictions are read as JSON data on stdin.
CASES_PATH = Path(__file__).resolve().parent.parent / "evals" / "cases.json"


def score(cases: list[dict], predictions: dict[str, list[str]]) -> dict:
    ids = {case["id"] for case in cases}
    if len(ids) != len(cases):
        raise ValueError("Duplicate case id")
    if set(predictions) != ids:
        raise ValueError(f"Expected exactly these case ids: {sorted(ids)}")
    tp = fp = fn = 0
    for case in cases:
        expected = {finding["id"] for finding in case["expected"]}
        reported = predictions[case["id"]]
        if not isinstance(reported, list) or any(not isinstance(value, str) for value in reported):
            raise ValueError(f"Invalid predictions for {case['id']}")
        if len(set(reported)) != len(reported):
            raise ValueError(f"Duplicate predictions for {case['id']}")
        found = set(reported)
        tp += len(expected & found)
        fp += len(found - expected)
        fn += len(expected - found)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    return {"cases": len(cases), "true_positives": tp, "false_positives": fp,
            "false_negatives": fn, "precision": round(precision, 4),
            "recall": round(recall, 4), "f1": round(f1, 4)}


def main() -> None:
    """Use a fixed checked-in corpus and predictions from stdin (no path arguments)."""
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))["cases"]
    predictions = json.load(sys.stdin)
    print(json.dumps(score(cases, predictions), indent=2))


if __name__ == "__main__":
    main()
