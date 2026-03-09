#!/usr/bin/env python3
"""Fail if the provided tag commit is not reachable from origin/main."""

from __future__ import annotations

import argparse
import subprocess
import sys


def run_git(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tag-ref", required=True, help="Full GitHub ref, e.g. refs/tags/v0.2.1")
    parser.add_argument("--base-ref", default="origin/main", help="Base branch to validate against")
    args = parser.parse_args()

    fetch = run_git("fetch", "origin", "main")
    if fetch.returncode != 0:
        print(fetch.stderr.strip(), file=sys.stderr)
        return fetch.returncode

    tag_sha = run_git("rev-list", "-n", "1", args.tag_ref)
    if tag_sha.returncode != 0:
        print(tag_sha.stderr.strip(), file=sys.stderr)
        return tag_sha.returncode
    sha = tag_sha.stdout.strip()

    check = run_git("merge-base", "--is-ancestor", sha, args.base_ref)
    if check.returncode != 0:
        print(f"{args.tag_ref} ({sha}) is not contained in {args.base_ref}", file=sys.stderr)
        return 1

    print(f"{args.tag_ref} ({sha}) is contained in {args.base_ref}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
