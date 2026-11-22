#!/usr/bin/env python3
"""Fail closed if a GitHub PR has changed since a review was performed."""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys

SHA = re.compile(r"(?:[a-fA-F0-9]{40}|[a-fA-F0-9]{64})\Z")
REPO = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


def check_snapshot(current: dict, reviewed_head: str, reviewed_base: str) -> bool:
    """Only exact HEAD and BASE matches are suitable for publishing old findings."""
    return (current.get("headRefOid") == reviewed_head
            and current.get("baseRefOid") == reviewed_base)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", required=True, help="owner/repo of the PR")
    parser.add_argument("--pr", type=int, required=True)
    parser.add_argument("--reviewed-head", required=True)
    parser.add_argument("--reviewed-base", required=True)
    args = parser.parse_args()
    if not REPO.fullmatch(args.repo) or args.pr < 1:
        parser.error("--repo must be owner/repo and --pr must be positive")
    if not SHA.fullmatch(args.reviewed_head) or not SHA.fullmatch(args.reviewed_base):
        parser.error("reviewed head/base must be full commit SHAs")
    try:
        result = subprocess.run(
            ["gh", "pr", "view", str(args.pr), "--repo", args.repo,
             "--json", "headRefOid,baseRefOid"],
            text=True, capture_output=True, check=True, timeout=60,
        )
        current = json.loads(result.stdout)
    except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired, ValueError) as exc:
        print(f"Cannot check PR revision: {exc}", file=sys.stderr)
        return 2
    if not check_snapshot(current, args.reviewed_head, args.reviewed_base):
        print("PR head or base changed since inspection: do not post this review; re-review.", file=sys.stderr)
        return 3
    print("PR revision matches the reviewed head and base.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
