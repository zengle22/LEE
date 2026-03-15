#!/usr/bin/env python
"""
Push the current branch, create or reuse a PR, and watch GitHub checks.

Prerequisites:
  - git is installed and configured for the repo remote
  - GITHUB_TOKEN is available in the environment

Examples:
  python scripts/pr_flow.py --base dev
  python scripts/pr_flow.py --base main --body-file .pr_description.md
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


SUCCESS_CONCLUSIONS = {"success", "neutral", "skipped"}
FAILURE_CONCLUSIONS = {"failure", "timed_out", "cancelled", "action_required", "stale"}


def run_git(*args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or f"git {' '.join(args)} failed")
    return result.stdout.strip()


def parse_github_repo(remote_url: str) -> tuple[str, str]:
    normalized = remote_url.strip()
    if normalized.startswith("git@"):
        _, rest = normalized.split(":", 1)
        path = rest.removesuffix(".git")
        owner, repo = path.split("/", 1)
        return owner, repo

    parsed = urllib.parse.urlparse(normalized)
    if parsed.netloc.lower() != "github.com":
        raise ValueError(f"unsupported remote host: {parsed.netloc or normalized}")

    path = parsed.path.lstrip("/").removesuffix(".git")
    owner, repo = path.split("/", 1)
    return owner, repo


def github_request(
    method: str,
    url: str,
    token: str,
    payload: dict | None = None,
) -> dict | list:
    data = None
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "LEE-pr-flow",
    }
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"GitHub API {exc.code}: {body}") from exc


def get_pr_body(body_file: str | None, body_text: str | None) -> str:
    if body_text is not None:
        return body_text.strip()

    if not body_file:
        default_body = Path(".pr_description.md")
        if default_body.exists():
            return default_body.read_text(encoding="utf-8").strip()
        return ""

    path = Path(body_file)
    if not path.exists():
        raise FileNotFoundError(f"body file not found: {path}")
    return path.read_text(encoding="utf-8").strip()


def infer_repo() -> tuple[str, str]:
    remote_url = run_git("remote", "get-url", "origin")
    return parse_github_repo(remote_url)


def current_branch() -> str:
    branch = run_git("rev-parse", "--abbrev-ref", "HEAD")
    if branch == "HEAD":
        raise RuntimeError("detached HEAD is not supported; switch to a branch first")
    return branch


def current_sha() -> str:
    return run_git("rev-parse", "HEAD")


def current_title() -> str:
    return run_git("log", "-1", "--pretty=%s")


def push_branch(branch: str, remote: str) -> None:
    subprocess.run(
        ["git", "push", "-u", remote, branch],
        check=True,
    )


def find_existing_pr(owner: str, repo: str, branch: str, base: str, token: str) -> dict | None:
    query = urllib.parse.urlencode({"state": "open", "base": base, "per_page": 100})
    url = f"https://api.github.com/repos/{owner}/{repo}/pulls?{query}"
    data = github_request("GET", url, token)
    for pr in data:
        if pr.get("head", {}).get("ref") == branch and pr.get("base", {}).get("ref") == base:
            return pr
    return None


def create_pr(
    owner: str,
    repo: str,
    branch: str,
    base: str,
    token: str,
    title: str,
    body: str,
) -> dict:
    payload = {
        "title": title,
        "head": branch,
        "base": base,
        "body": body,
    }
    return github_request("POST", f"https://api.github.com/repos/{owner}/{repo}/pulls", token, payload)


def ensure_pr(
    owner: str,
    repo: str,
    branch: str,
    base: str,
    token: str,
    title: str,
    body: str,
) -> tuple[dict, bool]:
    existing = find_existing_pr(owner, repo, branch, base, token)
    if existing is not None:
        return existing, False
    return create_pr(owner, repo, branch, base, token, title, body), True


def summarize_checks(check_runs: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    pending: list[dict] = []
    failed: list[dict] = []
    passed: list[dict] = []

    for check in check_runs:
        status = check.get("status")
        conclusion = check.get("conclusion")
        if status != "completed":
            pending.append(check)
        elif conclusion in FAILURE_CONCLUSIONS:
            failed.append(check)
        elif conclusion in SUCCESS_CONCLUSIONS:
            passed.append(check)
        else:
            failed.append(check)

    return pending, failed, passed


def load_check_runs(owner: str, repo: str, sha: str, token: str) -> list[dict]:
    url = f"https://api.github.com/repos/{owner}/{repo}/commits/{sha}/check-runs"
    data = github_request("GET", url, token)
    return data.get("check_runs", [])


def watch_checks(owner: str, repo: str, sha: str, token: str, poll_seconds: int, timeout_minutes: int) -> int:
    deadline = time.time() + timeout_minutes * 60
    seen_names: set[str] = set()

    while time.time() < deadline:
        check_runs = load_check_runs(owner, repo, sha, token)
        pending, failed, passed = summarize_checks(check_runs)

        for check in check_runs:
            seen_names.add(check.get("name", "<unknown>"))

        if check_runs:
            print(f"Checks for {sha[:7]}:")
            for check in check_runs:
                print(
                    f"- {check.get('name')}: status={check.get('status')} "
                    f"conclusion={check.get('conclusion')} url={check.get('html_url')}"
                )

        if failed:
            print("\nFailing checks:")
            for check in failed:
                print(f"- {check['name']}: {check.get('html_url')}")
            return 1

        if check_runs and not pending:
            print("\nAll checks passed.")
            return 0

        if not check_runs:
            print("No check-runs visible yet; waiting for GitHub Actions to attach checks...")
        else:
            print(f"Waiting on {len(pending)} check(s)...")

        time.sleep(poll_seconds)

    if seen_names:
        print("\nTimed out while waiting for checks to finish.")
    else:
        print("\nTimed out before any checks became visible.")
    return 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", required=True, help="Base branch for the pull request")
    parser.add_argument("--remote", default="origin", help="Git remote to push")
    parser.add_argument("--branch", help="Branch to push and open as PR; defaults to current branch")
    parser.add_argument("--title", help="PR title; defaults to HEAD commit subject")
    parser.add_argument("--body", help="Inline PR body text; overrides --body-file")
    parser.add_argument("--body-file", help="Markdown file for the PR body; defaults to .pr_description.md")
    parser.add_argument("--no-push", action="store_true", help="Skip git push")
    parser.add_argument("--no-watch", action="store_true", help="Skip check polling")
    parser.add_argument("--poll-seconds", type=int, default=15, help="Seconds between check polls")
    parser.add_argument("--timeout-minutes", type=int, default=30, help="Minutes to wait for checks")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print("GITHUB_TOKEN is not set.", file=sys.stderr)
        return 2

    owner, repo = infer_repo()
    branch = args.branch or current_branch()
    title = args.title or current_title()
    body = get_pr_body(args.body_file, args.body)

    if not args.no_push:
        print(f"Pushing {branch} to {args.remote}...")
        push_branch(branch, args.remote)

    sha = current_sha()
    pr, created = ensure_pr(owner, repo, branch, args.base, token, title, body)
    action = "Created" if created else "Reusing"
    print(f"{action} PR #{pr['number']}: {pr['html_url']}")

    if args.no_watch:
        return 0

    return watch_checks(owner, repo, sha, token, args.poll_seconds, args.timeout_minutes)


if __name__ == "__main__":
    sys.exit(main())
