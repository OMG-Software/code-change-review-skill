#!/usr/bin/env python3
"""Map changed files to the language reference files a reviewer should load.

Only references for languages actually present in the change are reported, so
the review loads the guidance it needs and nothing else.

Usage:
  detect_languages.py --git main          # files changed since merge-base with main (incl. uncommitted + untracked)
  detect_languages.py --git HEAD          # uncommitted + untracked changes only
  detect_languages.py --git origin/main --head refs/review/pr-123   # a fetched PR; working tree ignored
  git diff --name-only A..B | detect_languages.py   # git-quoted names are decoded; -z output also works
  detect_languages.py path/a.py path/b.go
  detect_languages.py --json ...          # machine-readable output
  detect_languages.py --check             # verify mapping, reference files and SKILL.md table agree

Standard library only; works on Windows, macOS and Linux.
"""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath
from typing import Callable

SKILL_DIR = Path(__file__).resolve().parent.parent
LANG_DIR = SKILL_DIR / "references" / "languages"

# Reference file (without .md) -> lowercase file extensions.
EXTENSIONS: dict[str, set[str]] = {
    "python": {".py", ".pyi", ".pyw", ".ipynb"},
    "javascript-typescript": {".js", ".jsx", ".mjs", ".cjs", ".ts", ".tsx", ".mts", ".cts", ".vue", ".svelte", ".astro"},
    "go": {".go"},
    "rust": {".rs"},
    "java-kotlin": {".java", ".kt", ".kts", ".scala", ".sc", ".groovy", ".gradle"},
    "csharp-dotnet": {".cs", ".fs", ".fsx", ".vb", ".csproj", ".fsproj", ".vbproj", ".sln", ".razor", ".cshtml"},
    "c-cpp": {".c", ".h", ".cc", ".cpp", ".cxx", ".c++", ".hpp", ".hh", ".hxx", ".inl", ".ipp", ".m", ".mm"},
    "ruby": {".rb", ".erb", ".rake", ".gemspec", ".ru"},
    "php": {".php", ".phtml"},
    "swift": {".swift", ".pbxproj"},
    "sql": {".sql", ".psql", ".pgsql", ".ddl"},
    "shell": {".sh", ".bash", ".zsh", ".ksh", ".fish", ".ps1", ".psm1", ".psd1", ".bat", ".cmd"},
    "infrastructure": {".tf", ".tfvars", ".hcl", ".dockerfile"},
}

# Exact (lowercase) basenames that identify a file type regardless of extension.
FILENAMES: dict[str, set[str]] = {
    "python": {"pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "pipfile", "pipfile.lock", "poetry.lock", "uv.lock"},
    "javascript-typescript": {"package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "tsconfig.json", "bun.lockb"},
    "go": {"go.mod", "go.sum", "go.work"},
    "rust": {"cargo.toml", "cargo.lock"},
    "java-kotlin": {"pom.xml", "build.gradle", "settings.gradle", "gradle.properties"},
    "csharp-dotnet": {"directory.build.props", "directory.packages.props", "nuget.config", "global.json"},
    "c-cpp": {"cmakelists.txt", "makefile", "meson.build", "conanfile.txt", "vcpkg.json"},
    "ruby": {"gemfile", "gemfile.lock", "rakefile", "config.ru"},
    "php": {"composer.json", "composer.lock"},
    "swift": {"package.swift", "package.resolved", "podfile"},
    "infrastructure": {"dockerfile", "containerfile", ".dockerignore", "chart.yaml", "values.yaml", "kustomization.yaml",
                       ".gitlab-ci.yml", "azure-pipelines.yml", "jenkinsfile", "bitbucket-pipelines.yml"},
    "instructions": {"skill.md", "claude.md", "agents.md", "gemini.md", "copilot-instructions.md", ".cursorrules"},
}

YAML = frozenset({".yml", ".yaml"})
MARKDOWN = frozenset({".md", ".mdc"})

# Location-based rules for files whose type depends on where they live. Each label is
# the rule itself (not a description of a regex), and the SKILL.md table must list it
# verbatim, so the fallback table and the detector can't drift apart:
#   "dir/"  -> any file under a directory of that name (or that subpath), at any depth
#   "glob*" -> a basename glob (fnmatch, lowercase)
# (reference, labels, only_exts) - only_exts, when set, restricts the rule to files with
# those extensions (YAML under k8s/, Markdown under skills/); None matches any file.
PATH_RULES: list[tuple[str, tuple[str, ...], frozenset[str] | None]] = [
    ("sql", ("migration/", "migrations/", "migrate/", "alembic/versions/", "flyway/", "liquibase/"), None),
    ("infrastructure", (".github/workflows/", ".github/actions/", "k8s/", "kubernetes/", "helm/", "charts/",
                        "manifests/", "deploy/", "deployment/", "kustomize/", "argocd/"), YAML),
    ("infrastructure", (".circleci/", "dockerfile*", "compose*.yml", "compose*.yaml",
                        "docker-compose*.yml", "docker-compose*.yaml"), None),
    # Markdown a model follows as instructions. Not every .md: a README or docs/ page is prose.
    ("instructions", ("skills/", ".claude/", "prompts/", "agents/", ".cursor/rules/"), MARKDOWN),
]

# Shebang interpreter (basename, version suffix stripped) -> reference, for extensionless scripts.
SHEBANGS: dict[str, set[str]] = {
    "python": {"python"},
    "javascript-typescript": {"node", "deno", "bun", "ts-node", "tsx"},
    "ruby": {"ruby"},
    "php": {"php"},
    "shell": {"sh", "bash", "zsh", "ksh", "dash", "fish", "pwsh"},
}


def _path_rule_matches(label: str, lower_path: str, name: str) -> bool:
    if label.endswith("/"):
        return f"/{label}" in f"/{lower_path}"
    return fnmatch.fnmatchcase(name, label)


def shebang_ref(first_line: str) -> str | None:
    """'#!/usr/bin/env -S deno run' -> 'javascript-typescript'; '#!/usr/bin/python3.12' -> 'python'."""
    if not first_line.startswith("#!"):
        return None
    words = first_line[2:].split()
    if words and PurePosixPath(words[0]).name == "env":
        words = [w for w in words[1:] if not w.startswith("-") and "=" not in w]
    if not words:
        return None
    interpreter = re.sub(r"[\d.]+$", "", PurePosixPath(words[0]).name.lower())
    for ref, names in SHEBANGS.items():
        if interpreter in names:
            return ref
    return None

# Files that carry no reviewable language-specific risk on their own.
IGNORED_EXTENSIONS = {".md", ".txt", ".rst", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".lock", ".gitignore",
                      ".gitattributes", ".editorconfig", ".license"}


def _native_to_posix(path: str) -> str:
    """Turn `\\` into `/` only where it is a path separator (Windows).

    On POSIX a backslash is an ordinary filename character: `tools\\review` is one file.
    """
    return path.replace("\\", "/") if os.sep == "\\" else path


def classify(path: str, abs_path: Path | None = None,
             read_old_first_line: Callable[[str], str | None] | None = None) -> list[str]:
    """Return every reference that applies to one file (usually one, sometimes two).

    `path` is repo-root-relative where possible (path patterns match against it);
    `abs_path` is where the file actually is on disk, used only to read a shebang.
    `read_old_first_line` returns a deleted file's first line from the base revision,
    so a deleted extensionless script still routes by its shebang.

    A migration written in Ruby or Python needs both its language notes and the
    SQL/migration notes, so path patterns add to the result rather than replacing it.
    """
    posix = PurePosixPath(_native_to_posix(path))
    lower = str(posix).lower()
    name = posix.name.lower()
    ext = posix.suffix.lower()
    refs: list[str] = []

    def add(ref: str | None) -> None:
        if ref and ref not in refs:
            refs.append(ref)

    for ref, names in FILENAMES.items():
        if name in names:
            add(ref)
    for ref, exts in EXTENSIONS.items():
        if ext in exts:
            add(ref)
    for ref, labels, only_exts in PATH_RULES:
        if (only_exts is None or ext in only_exts) and any(_path_rule_matches(lb, lower, name) for lb in labels):
            add(ref)
    # Probe extensionless files even when a path rule already matched: an extensionless
    # Python script under migrations/ needs python.md as well as sql.md.
    if not ext:
        if abs_path is not None:
            add(_from_shebang(abs_path))
        elif read_old_first_line is not None:              # deleted: read it from the base
            add(shebang_ref(read_old_first_line(path) or ""))
    return refs


def _from_shebang(file: Path) -> str | None:
    try:
        with file.open("rb") as fh:
            first = fh.readline(200).decode("utf-8", "replace")
    except OSError:
        return None
    return shebang_ref(first)


def _git(args: list[str], cwd: Path) -> list[str]:
    """Run git and return stripped output lines (for refs and paths git never quotes)."""
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


_C_ESCAPES = {ord(k): v for k, v in {"a": 7, "b": 8, "t": 9, "n": 10, "v": 11, "f": 12, "r": 13, '"': 34, "\\": 92}.items()}


def _unquote_git_path(raw: bytes) -> bytes:
    """Undo git's C-style quoting (`"caf\\303\\251.py"` -> `café.py`); return other names unchanged.

    Git quotes a pathname that contains non-ASCII bytes, control characters, `"` or `\\`
    unless core.quotePath is off or -z is used.
    """
    if len(raw) < 2 or raw[:1] != b'"' or raw[-1:] != b'"':
        return raw
    body, out, i = raw[1:-1], bytearray(), 0
    while i < len(body):
        c = body[i]
        if c != 0x5C or i + 1 >= len(body):           # not a backslash escape
            out.append(c)
            i += 1
        elif body[i + 1 : i + 4].isdigit() and len(body[i + 1 : i + 4]) == 3:
            out.append(int(body[i + 1 : i + 4], 8) & 0xFF)  # \NNN octal byte
            i += 4
        else:
            out.append(_C_ESCAPES.get(body[i + 1], body[i + 1]))
            i += 2
    return bytes(out)


def read_stdin_paths(data: bytes) -> list[str]:
    """Split piped pathnames: NUL-delimited (`git diff -z`) or one per line, git quoting undone.

    Only the line ending is removed, and only empty lines are skipped. Spaces are legal
    anywhere in a filename (a name can even be all spaces) and git never pads its output,
    so stripping them would point at a different file or drop one.
    """
    if b"\0" in data:
        names = [p for p in data.split(b"\0") if p]
    else:
        names = [_unquote_git_path(line) for line in data.splitlines() if line]
    return [n.decode("utf-8", "surrogateescape") for n in names if n]


def _git_paths(args: list[str], cwd: Path) -> list[str]:
    """Run a git pathname command with -z so unusual names (non-ASCII, quotes, newlines) arrive verbatim."""
    out = subprocess.run(["git", *args, "-z"], cwd=cwd, capture_output=True, check=True).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


_COMMIT_SHA = re.compile(r"[0-9a-f]{40}(?:[0-9a-f]{24})?")   # SHA-1 or SHA-256


def resolve_commit(ref: str, root: Path) -> str:
    """Turn a caller-supplied ref (`main`, `refs/review/pr-12`, a SHA) into a commit SHA.

    The ref goes to git on stdin (`cat-file --batch-check`), never on the command line,
    so a value such as `--output=x` can't be read as an option whoever supplied it. Only
    the resulting SHA is passed on to other git commands.
    """
    if not ref or "\n" in ref or "\r" in ref:
        raise ValueError(f"not a git revision: {ref!r}")
    out = subprocess.run(["git", "cat-file", "--batch-check=%(objectname) %(objecttype)"],
                         cwd=root, input=f"{ref}^{{commit}}\n", capture_output=True, text=True)
    sha, _, kind = out.stdout.strip().partition(" ")
    if out.returncode != 0 or kind != "commit" or not _COMMIT_SHA.fullmatch(sha):
        raise ValueError(f"not a commit: {ref!r}")
    return sha


def files_from_git(ref: str, cwd: Path, head: str | None = None) -> tuple[list[str], Path, str, str | None]:
    """Changed paths since merge-base(ref, head or HEAD), plus the repo root, that base commit
    and the resolved head commit.

    Without `head`, the working tree is compared (uncommitted and untracked files count).
    With `head` (a fetched pull request, say), only commits are compared and the working
    tree is ignored. `--no-renames` lists a rename as delete + add, so moving a file out of
    `migrations/` still reports the old path and its migration guidance.
    """
    root = Path(_git(["rev-parse", "--show-toplevel"], cwd)[0])
    ref_sha = resolve_commit(ref, root)
    head_sha = resolve_commit(head, root) if head else None
    base = _git(["merge-base", ref_sha, head_sha or "HEAD"], root)[0]
    if head_sha:
        changed = _git_paths(["diff", "--name-only", "--no-renames", base, head_sha], root)
        return sorted(changed), root, base, head_sha
    changed = _git_paths(["diff", "--name-only", "--no-renames", base], root)  # committed + uncommitted
    untracked = _git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return sorted(set(changed) | set(untracked)), root, base, None


def first_line_at(rev: str, root: Path) -> Callable[[str], str | None]:
    """Return a reader for a file's first line at `rev` (deleted files, or a commit under review).

    Only the first 200 bytes are read from git; the process is then stopped, so a large
    deleted binary is never buffered just to look for a shebang.
    """
    def read(path: str) -> str | None:
        proc = subprocess.Popen(["git", "cat-file", "blob", f"{rev}:{path}"], cwd=root,
                                stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        try:
            head = proc.stdout.read(200)               # empty if the blob doesn't exist
        finally:
            proc.stdout.close()
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        return head.split(b"\n", 1)[0].decode("utf-8", "replace") if head else None
    return read


def _first_of(*readers: Callable[[str], str | None]) -> Callable[[str], str | None]:
    """Combine first-line readers: the first one that finds the file wins."""
    def read(path: str) -> str | None:
        for reader in readers:
            line = reader(path)
            if line is not None:
                return line
        return None
    return read


def _without_final_symlink(path: Path) -> Path:
    """Make `path` absolute and canonical, resolving its directories but not its final name.

    `Path.resolve()` would follow a symlinked file to its target and classify the target's
    path instead of the one that changed.
    """
    if path.name in ("", ".", ".."):
        return path.resolve()
    return path.parent.resolve() / path.name


def resolve_inputs(paths: list[str], first_base: Path, other_base: Path, repo_root: Path) -> list[tuple[str, Path | None]]:
    """Pair each path with a repo-root-relative name (for path patterns) and its location on disk.

    Paths are tried against `first_base`, then `other_base`. Command-line arguments are
    relative to the invocation directory, while git output is relative to the repo root,
    so callers choose the order. Files that don't exist (deleted in the change) keep a
    name computed from `first_base` and get no on-disk path.

    The name always comes from the path that was given, not from where a symlink points:
    a changed `migrations/001.py` that links to `../helpers/001.py` is still a migration.
    """
    root = repo_root.resolve()
    out: list[tuple[str, Path | None]] = []
    for p in paths:
        p_norm = _native_to_posix(p)
        selected = first_base / p_norm
        found: Path | None = None
        for base in (first_base, other_base):
            candidate = base / p_norm
            if candidate.is_file():
                selected, found = candidate, candidate.resolve()
                break
        try:
            rel = _without_final_symlink(selected).relative_to(root).as_posix()
        except ValueError:
            rel = p_norm  # outside the repo; match on the path as given
        out.append((rel, found))
    return out


def detect(entries: list[tuple[str, Path | None]],
           read_old_first_line: Callable[[str], str | None] | None = None) -> dict:
    matched: dict[str, list[str]] = {}
    unmapped: list[str] = []
    for rel, abs_path in entries:
        refs = classify(rel, abs_path, read_old_first_line)
        for ref in refs:
            matched.setdefault(ref, []).append(rel)
        if not refs and PurePosixPath(rel).suffix.lower() not in IGNORED_EXTENSIONS:
            unmapped.append(rel)
    return {
        "references": [
            {"file": f"references/languages/{ref}.md", "triggered_by": sorted(paths)}
            for ref, paths in sorted(matched.items(), key=lambda kv: -len(kv[1]))
        ],
        "unmapped": sorted(unmapped),
        "total_files": len(entries),
    }


def print_human(result: dict) -> None:
    refs = result["references"]
    print(f"{result['total_files']} changed file(s).")
    if refs:
        print("\nLoad these language references:")
        for r in refs:
            shown = r["triggered_by"][:5]
            more = len(r["triggered_by"]) - len(shown)
            print(f"  {r['file']}  ({len(r['triggered_by'])} file(s): {', '.join(shown)}{f', +{more} more' if more else ''})")
    else:
        print("\nNo language references needed; apply references/review-angles.md only.")
    if result["unmapped"]:
        print("\nNo reference file for (review with general angles and your own language knowledge):")
        for f in result["unmapped"][:20]:
            print(f"  {f}")
        if len(result["unmapped"]) > 20:
            print(f"  ... +{len(result['unmapped']) - 20} more")


TABLE_ROW = re.compile(r"^\|(?P<cell>.+?)\|\s*`references/languages/(?P<ref>[\w.-]+)\.md`\s*\|\s*$", re.MULTILINE)


def parse_routing_table(skill_md: str) -> dict[str, set[str]]:
    """SKILL.md routing table -> {reference: lowercase backticked tokens in its 'Changed files' cell}."""
    table: dict[str, set[str]] = {}
    for m in TABLE_ROW.finditer(skill_md):
        tokens = {t.strip().lower() for t in re.findall(r"`([^`]+)`", m.group("cell"))}
        table.setdefault(m.group("ref"), set()).update(tokens)
    return table


def check() -> int:
    """Catch drift between this script, the reference files and the SKILL.md routing table.

    The table is the no-Python fallback, so it must route every extension, filename,
    path rule and shebang interpreter the detector knows, and must not point at
    references that don't exist.
    """
    problems: list[str] = []
    mapped = set(EXTENSIONS) | set(FILENAMES) | {ref for ref, _, _ in PATH_RULES} | set(SHEBANGS)
    present = {p.stem for p in LANG_DIR.glob("*.md")}
    table = parse_routing_table((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"))
    tabled = set(table)

    for ref in sorted(mapped - present):
        problems.append(f"detector maps to a missing file: references/languages/{ref}.md")
    for ref in sorted(present - mapped):
        problems.append(f"reference file never selected by the detector: references/languages/{ref}.md")
    for ref in sorted(present - tabled):
        problems.append(f"SKILL.md routing table has no row for references/languages/{ref}.md")
    for ref in sorted(tabled - present):
        problems.append(f"SKILL.md routing table points to a missing file: references/languages/{ref}.md")
    for ref in sorted(tabled - mapped):
        problems.append(f"SKILL.md routing table row not known to the detector: references/languages/{ref}.md")
    path_labels: dict[str, set[str]] = {}
    for ref, labels, _ in PATH_RULES:
        path_labels.setdefault(ref, set()).update(labels)
    for ref in sorted(tabled & mapped):
        rules = (EXTENSIONS.get(ref, set()) | FILENAMES.get(ref, set())
                 | path_labels.get(ref, set()) | SHEBANGS.get(ref, set()))
        missing = sorted(rules - table[ref])
        if missing:
            problems.append(f"SKILL.md tables for {ref}.md are missing: {', '.join(missing)}")
        stale = sorted(table[ref] - rules)
        if stale:
            problems.append(f"SKILL.md tables for {ref}.md list entries the detector doesn't route: {', '.join(stale)}")

    for p in problems:
        print(f"FAIL  {p}")
    if not problems:
        print(f"OK  {len(present)} language references; detector, files and SKILL.md table agree.")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="changed file paths (otherwise read from stdin or --git)")
    ap.add_argument("--git", metavar="REF", help="diff the working tree against merge-base(REF, HEAD)")
    ap.add_argument("--head", metavar="REV", help="with --git: diff REV (e.g. a fetched PR) against merge-base(REF, REV) "
                                                  "and read file contents from REV, ignoring the working tree")
    ap.add_argument("--json", action="store_true", help="emit JSON")
    ap.add_argument("--check", action="store_true", help="validate the skill's language mapping and exit")
    args = ap.parse_args()

    # Filenames can hold characters the console encoding can't show (e.g. cp1252 on
    # Windows); escape them instead of crashing mid-report.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    if args.check:
        return check()

    if args.head and not args.git:
        ap.error("--head needs --git BASE")

    cwd = Path.cwd()
    read_old: Callable[[str], str | None] | None = None
    if args.git:
        try:
            files, repo_root, base, head_sha = files_from_git(args.git, cwd, args.head)
            read_old = first_line_at(base, repo_root)
            if head_sha:
                # The working tree isn't the code under review: read each file from REV,
                # or from the base if REV deleted it.
                read_old = _first_of(first_line_at(head_sha, repo_root), read_old)
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            err = getattr(e, "stderr", None)
            msg = (err.decode(errors="replace") if isinstance(err, bytes) else err or str(e)).strip()
            print(f"git failed: {msg}", file=sys.stderr)
            return 2
    else:
        try:
            repo_root = Path(_git(["rev-parse", "--show-toplevel"], cwd)[0])
        except (subprocess.CalledProcessError, FileNotFoundError, IndexError):
            repo_root = cwd
        if args.files:
            files = args.files
        elif not sys.stdin.isatty():
            files = read_stdin_paths(sys.stdin.buffer.read())
        else:
            ap.print_help()
            return 2

    # git output is root-relative; command-line arguments are relative to where you ran
    # the script. Piped lists usually come from `git diff --name-only` (root-relative).
    if args.head:
        entries = [(f, None) for f in files]   # never look at local files for a commit under review
    elif args.files and not args.git:
        entries = resolve_inputs(files, cwd, repo_root, repo_root)
    else:
        entries = resolve_inputs(files, repo_root, cwd, repo_root)

    result = detect(entries, read_old)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
