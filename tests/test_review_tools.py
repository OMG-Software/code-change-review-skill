"""Regression tests for revision guard and manual review-quality scorer."""
from __future__ import annotations

import io
import json
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "code-change-review" / "scripts"))
sys.path.insert(0, str(ROOT / "scripts"))
import check_pr_revision
from check_pr_revision import check_snapshot
import score_evals
from score_evals import score


class RevisionGuardTests(unittest.TestCase):
    def test_requires_both_shas(self):
        head = "a" * 40
        base = "b" * 40
        self.assertTrue(check_snapshot({"headRefOid": head, "baseRefOid": base}, head, base))
        self.assertFalse(check_snapshot({"headRefOid": "c" * 40, "baseRefOid": base}, head, base))
        self.assertFalse(check_snapshot({"headRefOid": head, "baseRefOid": "c" * 40}, head, base))
        self.assertFalse(check_snapshot({}, head, base))


    def _call_main(self, gh_result=None, error=None):
        head = "a" * 40
        base = "b" * 40
        argv = ["check_pr_revision.py", "--repo", "example/repo", "--pr", "7",
                "--reviewed-head", head, "--reviewed-base", base]
        output = json.dumps(gh_result if gh_result is not None else
                            {"headRefOid": head, "baseRefOid": base})
        run_value = subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=output)
        with patch.object(sys, "argv", argv), patch.object(
            check_pr_revision.subprocess, "run", return_value=run_value, side_effect=error
        ) as mocked, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            exit_code = check_pr_revision.main()
        mocked.assert_called_once()
        self.assertEqual(mocked.call_args.kwargs["timeout"], 60)
        return exit_code

    def test_success_path(self):
        self.assertEqual(self._call_main(), 0)

    def test_changed_head_fails_closed(self):
        self.assertEqual(self._call_main(gh_result={
            "headRefOid": "c" * 40, "baseRefOid": "b" * 40
        }), 3)

    def test_timeout_fails_closed(self):
        self.assertEqual(self._call_main(error=subprocess.TimeoutExpired(["gh"], 60)), 2)


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

    def test_main_uses_fixed_cases_and_stdin(self):
        corpus = (ROOT / "evals" / "cases.json")
        case_ids = [case["id"] for case in json.loads(corpus.read_text())["cases"]]
        predictions = {case_id: [] for case_id in case_ids}
        with patch.object(score_evals.sys, "stdin", io.StringIO(json.dumps(predictions))):
            with redirect_stdout(io.StringIO()) as output:
                score_evals.main()
        result = json.loads(output.getvalue())
        self.assertEqual(result["cases"], len(case_ids))

    def test_missing_case_is_error(self):
        with self.assertRaises(ValueError):
            score(self.cases, {"bug": ["broken"]})

    def test_duplicate_prediction_is_error(self):
        with self.assertRaises(ValueError):
            score(self.cases, {"bug": ["broken", "broken"], "clean": []})


if __name__ == "__main__":
    unittest.main()
