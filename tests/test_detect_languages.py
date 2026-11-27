"""Behavioral tests for the detector and its Git snapshot routing (stdlib only)."""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "code-change-review" / "scripts"))
import detect_languages as dl
import review_axes as ra


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


@contextlib.contextmanager
def isolated_git_repo():
    """Yield an empty, configured Git repository in a temporary directory.

    Global/system Git hooks, templates and config are not inherited; the
    detector invokes git itself, so the environment stays patched until exit.
    """
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        repo = root / "repo"
        repo.mkdir()
        template = root / "empty-git-template"
        template.mkdir()
        with patch.dict(os.environ, {
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_COUNT": "0",
            "GIT_CONFIG_PARAMETERS": "",
            "GIT_TEMPLATE_DIR": str(template),
        }):
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "Test")
            git(repo, "config", "user.email", "test@example.invalid")
            yield repo


class LanguageDetectionTests(unittest.TestCase):
    def test_interpreters_and_env_options(self):
        cases = {
            "#!/usr/bin/env -S -u HOME python3": "python",
            "#!/usr/bin/env -S --unset HOME --chdir /tmp python3.12 -u": "python",
            "#!/usr/bin/env --unset=HOME -C/tmp node": "javascript-typescript",
            "#!/usr/bin/env -i FOO=bar deno run": "javascript-typescript",
            "#!/usr/bin/env -- FOO=bar python3": "python",
            "#!/usr/bin/env -- FOO=bar BAR=baz python3 -u": "python",
            "#!/usr/bin/env -- FOO=bar node": "javascript-typescript",
            "#!/usr/bin/env -- =invalid python3": None,
            "#!/usr/bin/env - python3": "python",
            "#!/usr/bin/env -S 'python3 -u'": "python",
            "#!/usr/bin/env --split-string=python3 -u": "python",
            "#!/usr/bin/env --split-string='python3 -u'": "python",
            "#!/usr/bin/env -Spython3 -u": "python",
            "#!/usr/bin/env -iS python3 -u": "python",
            "#!/usr/bin/env -iSpython3": "python",
            "#!/usr/bin/env -vSpython3": "python",
            "#!/usr/bin/env -iS'python3 -u'": "python",
            "#!/usr/bin/env -S LABEL='x node' python3": "python",
            "#!/usr/bin/env --split-string=LABEL='x node' python3": "python",
            "#!/usr/bin/env -S LABEL='x node' node": "javascript-typescript",
            "#!/usr/bin/env -S 'FOO=bar python3 -u'": "python",
            "#!/usr/bin/env --split-string='FOO=bar python3'": "python",
            "#!/usr/bin/env -iS'FOO=bar python3 -u'": "python",
            "#!/usr/bin/env -S FOO=bar python3 -u": "python",
            "#!/usr/bin/env -S LABEL='x node' -u HOME python3": "python",
            "#!/usr/bin/env -S -u HOME python3.12": "python",
            "#!/usr/bin/env --split-string=": None,
            "#!/usr/bin/python3.12": "python",
            "#!/bin/bash": "shell",
            "#!/usr/bin/env -Z python3": None,  # unknown option: don't guess
            "#!/usr/bin/env -u": None,  # missing option argument
            "#!/usr/bin/env 'python3": None,  # invalid quoting
        }
        for line, expected in cases.items():
            with self.subTest(line=line):
                self.assertEqual(dl.shebang_ref(line), expected)

    def test_schema_and_infrastructure_routing(self):
        cases = {
            "api/thing.proto": ["schemas"],
            "api/schema.graphql": ["schemas"],
            "db/schema.prisma": ["schemas"],
            "infra/main.tf.json": ["infrastructure"],
            "infra/prod.tfvars.json": ["infrastructure"],
            "BUILD.bazel": ["infrastructure"],
            "BUILD": ["infrastructure"],
            "WORKSPACE": ["infrastructure"],
            "build": [],
            "workspace": [],
            "docs/build": [],
            "scripts/workspace": [],
            "tools/rules.bzl": ["infrastructure"],
            "flake.nix": ["infrastructure"],
            "flake.lock": ["infrastructure"],
            "MODULE.bazel.lock": ["infrastructure"],
            "nested/MODULE.bazel.lock": ["infrastructure"],
            "random.lock": [],
            "migrations/001.py": ["python", "sql"],
            "skills/other/references/rules.md": ["instructions"],
        }
        for path, expected in cases.items():
            with self.subTest(path=path):
                self.assertCountEqual(dl.classify(path), expected)

    def test_table_and_detector_stay_in_sync(self):
        with contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(dl.check(), 0)

    def test_quoted_git_paths_and_nul_delimited_paths(self):
        self.assertEqual(dl.read_stdin_paths(b'"caf\\303\\251.py"\n'), ["café.py"])
        self.assertEqual(dl.read_stdin_paths(b"file with spaces.py\0a\nb.go\0"),
                         ["file with spaces.py", "a\nb.go"])

    @unittest.skipIf(os.name == "nt", "symlink creation may require elevated privileges")
    def test_internal_symlink_preserves_shebang_classification(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            real = repo / "tool.py"
            real.write_text("#!/usr/bin/env python3\nprint('ok')\n")
            (repo / "tool").symlink_to(real)
            entries = dl.resolve_inputs(["tool"], repo, repo, repo)
            self.assertEqual(entries, [("tool", real.resolve())])
            result = dl.detect(entries)
            self.assertEqual(
                [x["file"] for x in result["references"]],
                ["references/languages/python.md"],
            )

    @unittest.skipIf(os.name == "nt", "symlink creation may require elevated privileges")
    def test_symlinks_do_not_read_external_targets(self):
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            repo = base / "repo"
            repo.mkdir()
            outside = base / "outside"
            outside.write_text("#!/usr/bin/python3\n")
            (repo / "script").symlink_to(outside)
            entries = dl.resolve_inputs(["script"], repo, repo, repo)
            self.assertEqual(entries, [("script", None)])
            self.assertEqual(dl.detect(entries)["references"], [])

    @unittest.skipIf(os.name == "nt", "symlink creation may require elevated privileges")
    def test_broken_symlinks_are_not_dereferenced(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "tool").symlink_to("missing.py")
            entries = dl.resolve_inputs(["tool"], repo, repo, repo)
            self.assertEqual(entries, [("tool", None)])
            self.assertEqual(dl.detect(entries)["references"], [])


_CASE_EXT = {"python": ".py", "typescript": ".ts", "javascript": ".js", "go": ".go", "rust": ".rs", "proto": ".proto"}


def _diff_files(case: dict) -> list[tuple[str, str]]:
    """Split an eval case's diff into (path, text) pairs; a header-less snippet gets a name from its language."""
    out: list[tuple[str | None, list[str]]] = []
    path: str | None = None
    buf: list[str] = []
    for line in case["diff"].split("\n"):
        if line.startswith("--- "):
            continue
        if line.startswith("+++ "):
            if path is not None or buf:
                out.append((path, buf))
            path, buf = line[4:].removeprefix("b/"), []
            continue
        if not line.startswith("@@"):
            buf.append(line[1:] if line[:1] in "+- " else line)
    out.append((path, buf))
    fallback = "snippet" + _CASE_EXT.get(case["language"], "")
    return [(p if p and p != "/dev/null" else fallback, "\n".join(b)) for p, b in out]


class AxisRoutingTests(unittest.TestCase):
    def test_eval_cases_route_to_their_axes(self):
        cases = json.loads((ROOT / "evals" / "cases.json").read_text(encoding="utf-8"))["cases"]
        routed = [c for c in cases if c["axes"]]
        self.assertGreaterEqual(len(routed), len(ra.AXES) - 6)   # most axes have a case
        for case in cases:
            with self.subTest(case=case["id"]):
                self.assertTrue(set(case["axes"]) <= set(ra.AXES), case["axes"])
                selected: set[str] = set()
                for path, text in _diff_files(case):
                    selected.update(ra.classify_axes(path, text, dl.classify(path)))
                self.assertTrue(set(case["axes"]) <= selected,
                                f"{case['id']} needs {case['axes']}, detector chose {sorted(selected)}")

    def test_unrelated_code_does_not_load_domain_axes(self):
        library = ("package mathutil\n\n// Clamp limits v to [lo, hi].\n"
                   "func clamp(v, lo, hi int) int {\n\tif v < lo {\n\t\treturn lo\n\t}\n\treturn min(v, hi)\n}\n")
        cli = ("import argparse\nfrom pathlib import Path\n\n"
               "def main():\n    p = argparse.ArgumentParser()\n    p.add_argument('src')\n"
               "    print(Path(p.parse_args().src).read_text(encoding='utf-8').count('x'))\n")
        for path, text in (("mathutil/clamp.go", library), ("tools/count.py", cli)):
            with self.subTest(path=path):
                chosen = set(ra.classify_axes(path, text, dl.classify(path)))
                for axis in ("web", "caching", "messaging", "money", "llm-calls", "data-ml", "privacy"):
                    self.assertNotIn(axis, chosen)

    def test_path_and_language_rules_need_no_contents(self):
        cases = {
            "package-lock.json": "dependencies",
            "third_party/zlib/inflate.c": "dependencies",
            "api/userpb/user.pb.go": "generated-output",
            "web/__snapshots__/app.test.ts.snap": "generated-output",
            "db/migrations/0042_add_index.py": "data-migrations",
            "scripts/release.sh": "cross-platform",
            "infra/main.tf": "cloud-cost",
            "app/src/main/AndroidManifest.xml": "mobile",
            "notebooks/explore.ipynb": "data-ml",
            "src/components/Button.tsx": "ui",
        }
        for path, axis in cases.items():
            with self.subTest(path=path):
                self.assertIn(axis, ra.classify_axes(path, None, dl.classify(path)))
        self.assertNotIn("cloud-cost", ra.classify_axes(".github/workflows/ci.yml", None,
                                                        dl.classify(".github/workflows/ci.yml")))

    def test_signals_ignore_case_except_where_case_carries_meaning(self):
        self.assertIn("web", ra.classify_axes("app.py", "from Flask import request"))
        self.assertNotIn("money", ra.classify_axes("fmt.py", "round to one decimal place"))
        self.assertIn("money", ra.classify_axes("fmt.py", "from decimal import Decimal"))

    def test_long_words_scan_in_linear_time(self):
        for word in ("unitCents", "surcharges", "chargeback"):
            self.assertIn("money", ra.classify_axes("fees.py", f"x = {word}"), word)
        # A base64 blob or minified bundle is one long word. A signal that is not anchored at a
        # word boundary rescans it from every character; at 50,000 characters that takes minutes.
        start = time.perf_counter()
        ra.classify_axes("bundle.js", "a" * 50_000)
        self.assertLess(time.perf_counter() - start, 2.0)

    def test_binary_content_is_not_scanned(self):
        self.assertIsNone(ra.decode_text(b"\x89PNG\r\n\x1a\n\0\0flask"))
        self.assertEqual(ra.decode_text(b"import flask\n"), "import flask\n")

    def test_detect_reads_contents_from_disk_but_not_prose(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            (repo / "worker.py").write_text("import pika\nchannel.basic_ack(tag)\n")
            (repo / "NOTES.md").write_text("We cache invoices per tenant in Redis.\n")
            entries = dl.resolve_inputs(["worker.py", "NOTES.md"], repo, repo, repo)
            result = dl.detect(entries)
            axes = {a["file"]: a["triggered_by"] for a in result["axes"]}
            self.assertEqual(axes.get("references/axes/messaging.md"), ["worker.py"])
            self.assertNotIn("references/axes/caching.md", axes)

    @unittest.skipUnless(shutil.which("git"), "git required")
    def test_paths_only_ignores_local_files_with_the_same_path(self):
        script = ROOT / "skills" / "code-change-review" / "scripts" / "detect_languages.py"
        with isolated_git_repo() as repo:
            # A local checkout that happens to hold files at the remote PR's paths.
            (repo / "app.py").write_text("from flask import Flask\n")
            (repo / "tool").write_text("#!/usr/bin/env python3\n")

            def run(*flags: str) -> dict:
                out = subprocess.run([sys.executable, str(script), "--json", *flags], cwd=repo,
                                     input=b"app.py\ntool\n", stdout=subprocess.PIPE, check=True).stdout
                return json.loads(out)

            local = run()
            self.assertIn("references/axes/web.md", [a["file"] for a in local["axes"]])
            remote = run("--paths-only")
            self.assertNotIn("references/axes/web.md", [a["file"] for a in remote["axes"]])
            self.assertIn("tool", remote["unmapped"])   # its shebang was not read either


@unittest.skipUnless(shutil.which("git"), "git required")
class GitSnapshotTests(unittest.TestCase):
    def test_pinned_head_excludes_worktree_and_untracked_files(self):
        with isolated_git_repo() as repo:
            (repo / "original.py").write_text("x = 1\n")
            git(repo, "add", ".")
            git(repo, "commit", "-qm", "base")
            base = git(repo, "rev-parse", "HEAD")
            (repo / "original.py").write_text("x = 2\n")
            (repo / "thing.proto").write_text('syntax = "proto3";\n')
            git(repo, "add", ".")
            git(repo, "commit", "-qm", "head")
            head = git(repo, "rev-parse", "HEAD")
            (repo / "scratch.go").write_text("package scratch\n")
            (repo / "original.py").write_text("x = 3\n")
            changed, actual_root, merge_base, head_sha = dl.files_from_git(base, repo, head)
            self.assertEqual(changed, ["original.py", "thing.proto"])
            self.assertEqual((actual_root, merge_base, head_sha), (repo, base, head))
            working, _, _, no_head = dl.files_from_git("HEAD", repo)
            self.assertEqual(working, ["original.py", "scratch.go"])
            self.assertIsNone(no_head)

    def test_axis_signals_come_from_the_pinned_head(self):
        with isolated_git_repo() as repo:
            (repo / "app.py").write_text("x = 1\n")
            (repo / "old_billing.py").write_text("import stripe\n")
            git(repo, "add", ".")
            git(repo, "commit", "-qm", "base")
            base = git(repo, "rev-parse", "HEAD")
            (repo / "app.py").write_text("from flask import Flask\n")
            (repo / "old_billing.py").unlink()
            git(repo, "add", "-A")
            git(repo, "commit", "-qm", "head")
            head = git(repo, "rev-parse", "HEAD")
            (repo / "app.py").write_text("import anthropic\n")   # working tree differs from head
            files, actual_root, merge_base, head_sha = dl.files_from_git(base, repo, head)
            read_text = dl._first_of(dl.text_at(head_sha, actual_root), dl.text_at(merge_base, actual_root))
            result = dl.detect([(f, None) for f in files], None, read_text)
            axes = {a["file"].rsplit("/", 1)[1]: a["triggered_by"] for a in result["axes"]}
            self.assertEqual(axes.get("web.md"), ["app.py"])
            self.assertEqual(axes.get("money.md"), ["old_billing.py"])   # deleted: read from the base
            self.assertNotIn("llm-calls.md", axes)


if __name__ == "__main__":
    unittest.main()
