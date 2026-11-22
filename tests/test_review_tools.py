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
    HEAD = "a" * 40
    BASE = "b" * 40
    NEW_BASE = "c" * 40
    MERGE_BASE = "d" * 40

    def _snapshot(self, head=None, base=None):
        return {"headRefOid": head or self.HEAD, "baseRefOid": base or self.BASE}

    @staticmethod
    def _completed(stdout: str):
        return subprocess.CompletedProcess(args=["gh"], returncode=0, stdout=stdout)

    def _call_main(self, *, first=None, merge_base=None, final=None,
                   error=None, strict=False):
        args = ["check_pr_revision.py", "--repo", "example/repo", "--pr", "7",
                "--reviewed-head", self.HEAD, "--reviewed-base", self.BASE,
                "--reviewed-merge-base", self.MERGE_BASE]
        if strict:
            args.append("--strict-base")
        if first is None:
            first = self._snapshot()
        responses = [self._completed(json.dumps(first))]
        if first.get("headRefOid") == self.HEAD and first.get("baseRefOid") != self.BASE and not strict:
            responses.append(self._completed(merge_base if merge_base is not None
                                              else self.MERGE_BASE))
            responses.append(self._completed(json.dumps(final if final is not None
                                                         else first)))
        if error is not None:
            responses = [error]
        with patch.object(sys, "argv", args), patch.object(
            check_pr_revision.subprocess, "run", side_effect=responses
        ) as mocked, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            exit_code = check_pr_revision.main()
        for call in mocked.call_args_list:
            self.assertEqual(call.kwargs["timeout"], 60)
        return exit_code, mocked.call_args_list

    def test_snapshot_logic(self):
        same = self._snapshot()
        advanced = self._snapshot(base=self.NEW_BASE)
        args = (self.HEAD, self.BASE, self.MERGE_BASE)
        self.assertTrue(check_snapshot(same, *args))
        self.assertTrue(check_snapshot(advanced, *args, self.MERGE_BASE))
        self.assertFalse(check_snapshot(advanced, *args))
        self.assertFalse(check_snapshot(advanced, *args, "e" * 40))
        self.assertFalse(check_snapshot(self._snapshot(head="f" * 40), *args))

    def test_unmoved_pr_needs_only_one_request(self):
        code, calls = self._call_main()
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 1)

    def test_unchanged_merge_base_allows_unrelated_main_commit(self):
        code, calls = self._call_main(first=self._snapshot(base=self.NEW_BASE))
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 3)
        self.assertEqual(
            calls[1].args[0],
            ["gh", "api", f"repos/example/repo/compare/{self.NEW_BASE}...{self.HEAD}",
             "--jq", ".merge_base_commit.sha"],
        )

    def test_changed_merge_base_blocks(self):
        code, _ = self._call_main(first=self._snapshot(base=self.NEW_BASE),
                                  merge_base="e" * 40)
        self.assertEqual(code, 3)

    def test_unknown_merge_base_fails_closed(self):
        code, _ = self._call_main(first=self._snapshot(base=self.NEW_BASE),
                                  merge_base="null")
        self.assertEqual(code, 2)

    def test_changed_head_blocks(self):
        code, calls = self._call_main(first=self._snapshot(head="f" * 40))
        self.assertEqual(code, 3)
        self.assertEqual(len(calls), 1)

    def test_base_move_during_compare_blocks(self):
        code, _ = self._call_main(
            first=self._snapshot(base=self.NEW_BASE), final=self._snapshot()
        )
        self.assertEqual(code, 3)

    def test_strict_base_blocks_even_when_diff_unchanged(self):
        code, calls = self._call_main(first=self._snapshot(base=self.NEW_BASE),
                                      strict=True)
        self.assertEqual(code, 3)
        self.assertEqual(len(calls), 1)

    def test_timeout_fails_closed(self):
        code, _ = self._call_main(error=subprocess.TimeoutExpired(["gh"], 60))
        self.assertEqual(code, 2)

    def test_compare_api_failure_fails_closed(self):
        first = self._snapshot(base=self.NEW_BASE)
        args = ["check_pr_revision.py", "--repo", "example/repo", "--pr", "7",
                "--reviewed-head", self.HEAD, "--reviewed-base", self.BASE,
                "--reviewed-merge-base", self.MERGE_BASE]
        with patch.object(sys, "argv", args), patch.object(
            check_pr_revision.subprocess, "run",
            side_effect=[self._completed(json.dumps(first)),
                         subprocess.CalledProcessError(1, ["gh", "api"])],
        ), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = check_pr_revision.main()
        self.assertEqual(code, 2)


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

    def test_corpus_diffs_are_actual_multiline_text(self):
        cases = json.loads((ROOT / "evals" / "cases.json").read_text())["cases"]
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertIn("\n", case["diff"])
                self.assertNotIn(r"\n", case["diff"])

    def test_prompt_injection_attempt_is_expected_finding(self):
        cases = json.loads((ROOT / "evals" / "cases.json").read_text())["cases"]
        attack = next(case for case in cases if case["id"] == "untrusted-comment")
        self.assertEqual([finding["id"] for finding in attack["expected"]],
                         ["review-instruction-injection"])

    def test_missing_case_is_error(self):
        with self.assertRaises(ValueError):
            score(self.cases, {"bug": ["broken"]})

    def test_duplicate_prediction_is_error(self):
        with self.assertRaises(ValueError):
            score(self.cases, {"bug": ["broken", "broken"], "clean": []})


if __name__ == "__main__":
    unittest.main()
