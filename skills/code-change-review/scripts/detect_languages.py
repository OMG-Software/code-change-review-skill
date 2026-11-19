#!/usr/bin/env python3
"""Map changed files to the language reference files a reviewer should load.

Only references for languages actually present in the change are reported, so
the review loads the guidance it needs and nothing else.

Usage:
  detect_languages.py --git main          # files changed since merge-base with main (incl. uncommitted + untracked)
  detect_languages.py --git HEAD          # uncommitted + untracked changes only
  git diff --name-only A..B | detect_languages.py
  detect_languages.py path/a.py path/b.go
  detect_languages.py --json ...          # machine-readable output
  detect_languages.py --check             # verify mapping, reference files and SKILL.md table agree

Standard library only; works on Windows, macOS and Linux.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path, PurePosixPath

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
}

# Path regexes (matched against the lowercase POSIX path) for files whose type
# depends on location rather than name.
PATH_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("sql", re.compile(r"(^|/)(migrations?|migrate|db/migrate|alembic/versions|flyway|liquibase)/")),
    ("infrastructure", re.compile(r"(^|/)\.github/(workflows|actions)/.+\.ya?ml$")),
    ("infrastructure", re.compile(r"(^|/)\.circleci/")),
    ("infrastructure", re.compile(r"(^|/)(k8s|kubernetes|helm|charts|manifests|deploy|deployment|kustomize|argocd)/.+\.ya?ml$")),
    ("infrastructure", re.compile(r"(^|/)(docker-)?compose[\w.-]*\.ya?ml$")),
    ("infrastructure", re.compile(r"(^|/)dockerfile[\w.-]*$")),
]

# Shebang interpreter -> reference, for extensionless scripts.
SHEBANGS: list[tuple[str, re.Pattern[str]]] = [
    ("python", re.compile(r"python")),
    ("javascript-typescript", re.compile(r"\b(node|deno|bun|ts-node|tsx)\b")),
    ("ruby", re.compile(r"\bruby\b")),
    ("php", re.compile(r"\bphp\b")),
    ("shell", re.compile(r"\b(ba|z|k|da|fi)?sh\b|\bpwsh\b")),
]

# Files that carry no reviewable language-specific risk on their own.
IGNORED_EXTENSIONS = {".md", ".txt", ".rst", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".lock", ".gitignore",
                      ".gitattributes", ".editorconfig", ".license"}


def classify(path: str, abs_path: Path | None = None) -> list[str]:
    """Return every reference that applies to one file (usually one, sometimes two).

    `path` is repo-root-relative where possible (path patterns match against it);
    `abs_path` is where the file actually is on disk, used only to read a shebang.

    A migration written in Ruby or Python needs both its language notes and the
    SQL/migration notes, so path patterns add to the result rather than replacing it.
    """
    posix = PurePosixPath(path.replace("\\", "/"))
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
    for ref, pattern in PATH_PATTERNS:
        if pattern.search(lower):
            add(ref)
    if not refs and not ext and abs_path is not None:
        add(_from_shebang(abs_path))
    return refs


def _from_shebang(file: Path) -> str | None:
    try:
        with file.open("rb") as fh:
            first = fh.readline(200).decode("utf-8", "replace")
    except OSError:
        return None
    if not first.startswith("#!"):
        return None
    for ref, pattern in SHEBANGS:
        if pattern.search(first):
            return ref
    return None


def _git(args: list[str], cwd: Path) -> list[str]:
    """Run git and return stripped output lines (for refs and paths git never quotes)."""
    out = subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True, check=True).stdout
    return [line.strip() for line in out.splitlines() if line.strip()]


def _git_paths(args: list[str], cwd: Path) -> list[str]:
    """Run a git pathname command with -z so unusual names (non-ASCII, quotes, newlines) arrive verbatim."""
    out = subprocess.run(["git", *args, "-z"], cwd=cwd, capture_output=True, check=True).stdout
    return [p.decode("utf-8", "surrogateescape") for p in out.split(b"\0") if p]


def files_from_git(ref: str, cwd: Path) -> tuple[list[str], Path]:
    root = Path(_git(["rev-parse", "--show-toplevel"], cwd)[0])
    base = _git(["merge-base", ref, "HEAD"], root)[0]
    changed = _git_paths(["diff", "--name-only", base], root)      # committed since base + uncommitted
    untracked = _git_paths(["ls-files", "--others", "--exclude-standard"], root)
    return sorted(set(changed) | set(untracked)), root


def resolve_inputs(paths: list[str], first_base: Path, other_base: Path, repo_root: Path) -> list[tuple[str, Path | None]]:
    """Pair each path with a repo-root-relative name (for path patterns) and its location on disk.

    Paths are tried against `first_base`, then `other_base`. Command-line arguments are
    relative to the invocation directory, while git output is relative to the repo root,
    so callers choose the order. Files that don't exist (deleted in the change) keep a
    name computed from `first_base` and get no on-disk path.
    """
    root = repo_root.resolve()
    out: list[tuple[str, Path | None]] = []
    for p in paths:
        p_norm = p.replace("\\", "/")
        found: Path | None = None
        for base in (first_base, other_base):
            candidate = base / p_norm
            if candidate.is_file():
                found = candidate.resolve()
                break
        try:
            rel = (found or (first_base / p_norm).resolve()).relative_to(root).as_posix()
        except ValueError:
            rel = p_norm  # outside the repo; match on the path as given
        out.append((rel, found))
    return out


def detect(entries: list[tuple[str, Path | None]]) -> dict:
    matched: dict[str, list[str]] = {}
    unmapped: list[str] = []
    for rel, abs_path in entries:
        refs = classify(rel, abs_path)
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

    The table is the no-Python fallback, so it must route every extension and filename
    the detector knows, and must not point at references that don't exist.
    """
    problems: list[str] = []
    mapped = set(EXTENSIONS) | set(FILENAMES) | {ref for ref, _ in PATH_PATTERNS} | {ref for ref, _ in SHEBANGS}
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
    for ref in sorted(tabled & mapped):
        missing = sorted((EXTENSIONS.get(ref, set()) | FILENAMES.get(ref, set())) - table[ref])
        if missing:
            problems.append(f"SKILL.md row for {ref}.md is missing: {', '.join(missing)}")

    for p in problems:
        print(f"FAIL  {p}")
    if not problems:
        print(f"OK  {len(present)} language references; detector, files and SKILL.md table agree.")
    return 1 if problems else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="changed file paths (otherwise read from stdin or --git)")
    ap.add_argument("--git", metavar="REF", help="diff the working tree against merge-base(REF, HEAD)")
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

    cwd = Path.cwd()
    if args.git:
        try:
            files, repo_root = files_from_git(args.git, cwd)
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
            files = [line.strip() for line in sys.stdin if line.strip()]
        else:
            ap.print_help()
            return 2

    # git output is root-relative; command-line arguments are relative to where you ran
    # the script. Piped lists usually come from `git diff --name-only` (root-relative).
    if args.files and not args.git:
        entries = resolve_inputs(files, cwd, repo_root, repo_root)
    else:
        entries = resolve_inputs(files, repo_root, cwd, repo_root)

    result = detect(entries)
    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print_human(result)
    return 0


if __name__ == "__main__":
    sys.exit(main())
