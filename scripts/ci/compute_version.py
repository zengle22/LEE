#!/usr/bin/env python3
"""Compute CI release versions and optionally rewrite pyproject.toml."""

from __future__ import annotations

import argparse
import datetime as dt
import os
import pathlib
import re
import sys


PYPROJECT_PATH = pathlib.Path("pyproject.toml")
VERSION_RE = re.compile(r'^(version\s*=\s*")([^"]+)(")$', re.MULTILINE)
RELEASE_RE = re.compile(r"^v?(?P<version>\d+\.\d+\.\d+(?:[A-Za-z0-9.\-]+)?)$")


def read_base_version(pyproject_path: pathlib.Path) -> tuple[str, str]:
    text = pyproject_path.read_text(encoding="utf-8")
    match = VERSION_RE.search(text)
    if not match:
        raise ValueError(f"Could not find project version in {pyproject_path}")
    return text, match.group(2)


def compute_version(mode: str, base_version: str, ref_name: str | None, sha: str | None) -> str:
    if mode == "candidate":
        short_sha = (sha or os.getenv("GITHUB_SHA", "local"))[:7]
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d")
        return f"{base_version}.dev{stamp}+{short_sha}"

    if not ref_name:
        raise ValueError("ref_name is required for release mode")
    match = RELEASE_RE.match(ref_name)
    if not match:
        raise ValueError(f"Release ref '{ref_name}' is not a supported tag format")
    return match.group("version")


def write_version(pyproject_path: pathlib.Path, text: str, version: str) -> None:
    updated, count = VERSION_RE.subn(rf'\1{version}\3', text, count=1)
    if count != 1:
        raise ValueError(f"Failed to update version in {pyproject_path}")
    pyproject_path.write_text(updated, encoding="utf-8")


def write_github_output(version: str) -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with open(output_path, "a", encoding="utf-8") as handle:
            handle.write(f"lee_version={version}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["candidate", "release"], required=True)
    parser.add_argument("--ref-name", help="Git ref or tag name used for release mode")
    parser.add_argument("--sha", help="Git SHA used for candidate mode")
    parser.add_argument(
        "--write-pyproject",
        action="store_true",
        help="Rewrite pyproject.toml with the computed version",
    )
    args = parser.parse_args()

    try:
        text, base_version = read_base_version(PYPROJECT_PATH)
        version = compute_version(args.mode, base_version, args.ref_name, args.sha)
        if args.write_pyproject:
            write_version(PYPROJECT_PATH, text, version)
        write_github_output(version)
    except Exception as exc:  # pragma: no cover - CLI guard
        print(str(exc), file=sys.stderr)
        return 1

    print(version)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
