#!/usr/bin/env python
"""
Validate workflow provenance on changed formal SSOT files.
"""

from __future__ import annotations

import argparse

from git_ssot_hook_checks import run_ssot_lint


def main() -> int:
    parser = argparse.ArgumentParser(description="Check changed SSOT files for workflow provenance.")
    parser.add_argument("paths", nargs="*", help="Changed repository-relative paths.")
    args = parser.parse_args()

    if not args.paths:
        print("No changed paths provided, skipping SSOT governance check.")
        return 0

    passed, errors = run_ssot_lint(args.paths)
    if passed:
        print("SSOT governance check passed.")
        return 0

    print("SSOT governance check failed:")
    for err in errors:
        print(f"  - {err}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
