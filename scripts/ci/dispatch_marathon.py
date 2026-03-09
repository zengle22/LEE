#!/usr/bin/env python3
"""Send a repository_dispatch event to the Marathon repository."""

from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--token", required=False, help="GitHub token with repo dispatch scope")
    parser.add_argument("--lee-version", required=True)
    parser.add_argument("--environment", required=True)
    parser.add_argument("--release-kind", required=True, choices=["candidate", "release"])
    parser.add_argument("--source-sha", required=True)
    parser.add_argument("--source-repo", default=os.getenv("GITHUB_REPOSITORY", ""))
    parser.add_argument("--event-type", default="lee_release_ready")
    args = parser.parse_args()

    token = args.token or os.getenv("GITHUB_TOKEN") or os.getenv("GH_TOKEN")
    if not token:
        print("Missing GitHub token for repository_dispatch", file=sys.stderr)
        return 1

    payload = {
        "event_type": args.event_type,
        "client_payload": {
            "lee_version": args.lee_version,
            "environment": args.environment,
            "release_kind": args.release_kind,
            "source_sha": args.source_sha,
            "source_repo": args.source_repo,
            "triggered_by": "github-actions",
        },
    }
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url=f"https://api.github.com/repos/{args.repo}/dispatches",
        data=data,
        method="POST",
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "lee-framework-ci",
        },
    )

    try:
        with urllib.request.urlopen(request) as response:
            print(f"repository_dispatch accepted with status {response.status}")
            return 0
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"Dispatch failed: HTTP {exc.code}: {body}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"Dispatch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
