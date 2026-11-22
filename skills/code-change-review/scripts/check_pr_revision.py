#!/usr/bin/env python3
"""Fail closed if a GitHub PR's reviewed diff changed before publication."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

SHA = re.compile(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")
GH_TIMEOUT_SECONDS = 60


def check_snapshot(current: dict, reviewed_head: str, reviewed_base: str,
                   reviewed_merge_base: str, current_merge_base: str | None = None) -> bool:
    """Permit base advances only if the original diff's merge-base is unchanged."""
    head = current.get("headRefOid")
    base = current.get("baseRefOid")
    if not isinstance(head, str) or not isinstance(base, str):
        return False
    if head.lower() != reviewed_head.lower():
        return False
    if base.lower() == reviewed_base.lower():
        return True
    return (isinstance(current_merge_base, str)
            and current_merge_base.lower() == reviewed_merge_base.lower())


def _gh(*args: str) -> str:
    """Run GitHub CLI with a bound wait time; callers validate its output."""
    return subprocess.run(
        ["gh", *args], text=True, capture_output=True, check=True,
        timeout=GH_TIMEOUT_SECONDS,
    ).stdout


def _pr_revision(repo: str, pr: int) -> dict:
    data = json.loads(_gh("pr", "view", str(pr), "--repo", repo,
                          "--json", "headRefOid,baseRefOid"))
    if not isinstance(data, dict):
        raise ValueError("Invalid GitHub PR revision response")
    for field in ("headRefOid", "baseRefOid"):
        value = data.get(field)
        if not isinstance(value, str) or not SHA.fullmatch(value):
            raise ValueError(f"Missing or invalid {field} in PR revision")
        data[field] = value.lower()
    return data


def _merge_base(repo: str, base: str, head: str) -> str:
    """Ask GitHub to compare the current base with the pinned PR head.

    This reads the current merge-base on the server and does not mutate the
    working tree or require refs to have been fetched locally. It fails closed
    if the PR commit is not accessible to the base repository's compare API.
    """
    value = _gh("api", f"repos/{repo}/compare/{base}...{head}",
                "--jq", ".merge_base_commit.sha").strip()
    if not SHA.fullmatch(value):
        raise ValueError("GitHub did not return a valid merge-base SHA")
    return value.lower()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo of the PR")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--reviewed-head", required=True)
    parser.add_argument("--reviewed-base", required=True)
    parser.add_argument("--reviewed-merge-base", required=True,
                        help="merge-base used to construct the inspected PR diff")
    parser.add_argument("--strict-base", action="store_true",
                        help="also reject any base-tip movement, even with identical diff")
    args = parser.parse_args()
    if not REPO.fullmatch(args.repo) or args.pr < 1:
        parser.error("--repo must be owner/repo and --pr must be positive")
    if any(not SHA.fullmatch(value) for value in
           (args.reviewed_head, args.reviewed_base, args.reviewed_merge_base)):
        parser.error("reviewed head, base and merge-base must be full commit SHAs")
    # Git object IDs are hexadecimal values: case is not part of their identity.
    args.reviewed_head = args.reviewed_head.lower()
    args.reviewed_base = args.reviewed_base.lower()
    args.reviewed_merge_base = args.reviewed_merge_base.lower()

    try:
        current = _pr_revision(args.repo, args.pr)
        if current["headRefOid"] != args.reviewed_head:
            print(f"PR head changed: reviewed {args.reviewed_head[:12]}, "
                  f"current {current['headRefOid'][:12]}; re-review.", file=sys.stderr)
            return 3

        current_merge_base = None
        if current["baseRefOid"] != args.reviewed_base:
            if args.strict_base:
                print(f"PR base tip changed (strict-base): reviewed "
                      f"{args.reviewed_base[:12]}, current {current['baseRefOid'][:12]}; "
                      "re-review.", file=sys.stderr)
                return 3
            current_merge_base = _merge_base(
                args.repo, current["baseRefOid"], args.reviewed_head,
            )
            # A base update during the compare must not be approved using an
            # obsolete base revision. There is still a non-atomic POST window.
            if _pr_revision(args.repo, args.pr) != current:
                print("PR head or base moved during merge-base verification; "
                      "recheck the PR and re-review.", file=sys.stderr)
                return 3
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired,
            ValueError) as exc:
        # capture_output=True means CalledProcessError has GitHub CLI's stderr.
        # Include a bounded, escaped excerpt so the operator can distinguish
        # auth failures, missing commits and transient API errors.
        detail = ""
        if isinstance(exc, subprocess.CalledProcessError) and isinstance(exc.stderr, str):
            if exc.stderr.strip():
                detail = f" GitHub CLI stderr: {exc.stderr.strip()[:400]!r}."
        print(f"Cannot verify PR {args.repo}#{args.pr}: {exc}.{detail} Check GitHub CLI "
              "authentication, repository permissions and commit availability; "
              "do not publish.", file=sys.stderr)
        return 2

    if not check_snapshot(current, args.reviewed_head, args.reviewed_base,
                          args.reviewed_merge_base, current_merge_base):
        print(f"PR merge-base changed: reviewed {args.reviewed_merge_base[:12]}, "
              f"current {(current_merge_base or 'unavailable')[:12]}; re-review.",
              file=sys.stderr)
        return 3
    if current_merge_base is None:
        print("PR head and base match the reviewed snapshot.")
    else:
        print("PR head and merge-base match the reviewed diff (base tip advanced).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
