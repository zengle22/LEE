#!/usr/bin/env python3
"""Write build metadata for CI artifacts."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import pathlib
import subprocess


def git_output(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--release-kind", required=True, choices=["candidate", "release"])
    args = parser.parse_args()

    output_path = pathlib.Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "name": "lee-framework",
        "version": args.version,
        "release_kind": args.release_kind,
        "git_sha": os.getenv("GITHUB_SHA") or git_output("rev-parse", "HEAD"),
        "git_ref": os.getenv("GITHUB_REF") or git_output("rev-parse", "--abbrev-ref", "HEAD"),
        "built_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "workflow": os.getenv("GITHUB_WORKFLOW", ""),
        "workflow_run_id": os.getenv("GITHUB_RUN_ID", ""),
        "run_attempt": os.getenv("GITHUB_RUN_ATTEMPT", ""),
    }

    output_path.write_text(json.dumps(payload, ensure_ascii=True, indent=2) + "\n", encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
