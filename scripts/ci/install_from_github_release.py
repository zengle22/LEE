#!/usr/bin/env python3
"""Download and install a wheel from a GitHub Release."""

from __future__ import annotations

import argparse
import pathlib
import subprocess
import sys
import urllib.request


def run(*args: str) -> None:
    subprocess.run(args, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", required=True, help="owner/repo")
    parser.add_argument("--version", required=True, help="Version without or with leading v")
    parser.add_argument(
        "--output-dir",
        default=".tmp/github-release",
        help="Directory where the wheel will be downloaded",
    )
    parser.add_argument(
        "--asset-name",
        help="Optional explicit asset name; defaults to lee_framework-<version>-py3-none-any.whl",
    )
    args = parser.parse_args()

    version = args.version[1:] if args.version.startswith("v") else args.version
    tag = f"v{version}"
    asset_name = args.asset_name or f"lee_framework-{version}-py3-none-any.whl"

    output_dir = pathlib.Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / asset_name

    url = f"https://github.com/{args.repo}/releases/download/{tag}/{asset_name}"
    print(f"Downloading {url}")
    urllib.request.urlretrieve(url, output_path)
    print(f"Downloaded to {output_path}")

    run(sys.executable, "-m", "pip", "install", str(output_path))
    print(f"Installed {asset_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
