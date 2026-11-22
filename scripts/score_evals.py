#!/usr/bin/env python3
"""Score manually adjudicated code-review findings against evals/cases.json."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


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
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, required=True)
    parser.add_argument("--predictions", type=Path, required=True)
    args = parser.parse_args()
    cases = json.loads(args.cases.read_text(encoding="utf-8"))["cases"]
    predictions = json.loads(args.predictions.read_text(encoding="utf-8"))
    print(json.dumps(score(cases, predictions), indent=2))


if __name__ == "__main__":
    main()
