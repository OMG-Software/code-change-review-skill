"""Behavioral tests for the detector and its Git snapshot routing (stdlib only)."""
from __future__ import annotations

import contextlib
import io
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "skills" / "code-change-review" / "scripts"))
import detect_languages as dl


def git(repo: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=repo, text=True, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE).stdout.strip()


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


@unittest.skipUnless(shutil.which("git"), "git required")
class GitSnapshotTests(unittest.TestCase):
    def test_pinned_head_excludes_worktree_and_untracked_files(self):
        with tempfile.TemporaryDirectory() as temp:
            repo = Path(temp)
            git(repo, "init", "-q")
            git(repo, "config", "user.name", "Test")
            git(repo, "config", "user.email", "test@example.invalid")
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
            changed, root, merge_base, head_sha = dl.files_from_git(base, repo, head)
            self.assertEqual(changed, ["original.py", "thing.proto"])
            self.assertEqual((root, merge_base, head_sha), (repo, base, head))
            working, _, _, no_head = dl.files_from_git("HEAD", repo)
            self.assertEqual(working, ["original.py", "scratch.go"])
            self.assertIsNone(no_head)


if __name__ == "__main__":
    unittest.main()
