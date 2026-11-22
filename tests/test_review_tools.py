"""Regression tests for revision guard and manual review-quality scorer."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "code-change-review" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
from check_pr_revision import check_snapshot
from score_evals import score


class RevisionGuardTests(unittest.TestCase):
    def test_requires_both_shas(self):
        head = "a" * 40
        base = "b" * 40
        self.assertTrue(check_snapshot({"headRefOid": head, "baseRefOid": base}, head, base))
        self.assertFalse(check_snapshot({"headRefOid": "c" * 40, "baseRefOid": base}, head, base))
        self.assertFalse(check_snapshot({"headRefOid": head, "baseRefOid": "c" * 40}, head, base))
        self.assertFalse(check_snapshot({}, head, base))


class ReviewScorerTests(unittest.TestCase):
    cases = [
        {"id": "bug", "expected": [{"id": "broken"}]},
        {"id": "clean", "expected": []},
    ]

    def test_metrics(self):
        result = score(self.cases, {"bug": ["broken", "extra"], "clean": []})
        self.assertEqual((result["true_positives"], result["false_positives"], result["false_negatives"]),
                         (1, 1, 0))
        self.assertEqual(result["precision"], 0.5)
        self.assertEqual(result["recall"], 1.0)

    def test_missing_case_is_error(self):
        with self.assertRaises(ValueError):
            score(self.cases, {"bug": ["broken"]})

    def test_duplicate_prediction_is_error(self):
        with self.assertRaises(ValueError):
            score(self.cases, {"bug": ["broken", "broken"], "clean": []})


if __name__ == "__main__":
    unittest.main()
