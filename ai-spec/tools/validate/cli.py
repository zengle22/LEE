"""Command-line interface for the validator."""

import argparse
import sys
from pathlib import Path
from typing import Optional

from .engine import ValidationEngine
from .models import SpecType


def find_spec_root(start_path: Path) -> Path:
    """Find the ai-spec root directory.

    Walks up from start_path looking for a directory that contains
    'specs/' and 'cli/' subdirectories, or is named 'ai-spec'.
    """
    current = start_path.resolve()

    # If start_path is inside ai-spec, walk up
    while current != current.parent:
        if current.name == "ai-spec":
            return current
        if (current / "specs").is_dir() and (current / "cli").is_dir():
            return current
        current = current.parent

    # If we couldn't find it, use start_path's parent
    # This handles cases like: validate.py specs/agents/foo/v1/agent.yaml
    if "ai-spec" in str(start_path):
        parts = start_path.parts
        for i, part in enumerate(parts):
            if part == "ai-spec":
                return Path(*parts[: i + 1])

    # Fallback: use the start path's parent
    return start_path.parent if start_path.is_file() else start_path


def parse_spec_type(type_str: Optional[str]) -> Optional[SpecType]:
    """Parse spec type from string."""
    if not type_str:
        return None

    type_map = {
        "workflow": SpecType.WORKFLOW,
        "agent": SpecType.AGENT,
        "contract": SpecType.CONTRACT,
        "project": SpecType.PROJECT,
    }

    return type_map.get(type_str.lower())


def main(args: Optional[list[str]] = None) -> int:
    """Main entry point.

    Args:
        args: Command line arguments (defaults to sys.argv[1:])

    Returns:
        Exit code: 0 = success, 1 = validation failures, 2 = error
    """
    parser = argparse.ArgumentParser(
        prog="validate",
        description="Validate ai-spec files (workflows, agents, contracts)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Validate a single file
  python -m validate specs/workflows/product-pipeline/v1/workflow.yaml

  # Validate entire specs directory
  python -m validate specs/

  # Validate only agents
  python -m validate --type agent specs/

  # Output as JSON
  python -m validate --format json specs/

  # Validate from ai-spec root
  python -m validate .
        """,
    )

    parser.add_argument(
        "target",
        type=Path,
        help="File or directory to validate",
    )

    parser.add_argument(
        "--type", "-t",
        choices=["workflow", "agent", "contract", "project"],
        help="Filter by spec type (for directory validation)",
    )

    parser.add_argument(
        "--format", "-f",
        choices=["cli", "json"],
        default="cli",
        help="Output format (default: cli)",
    )

    parser.add_argument(
        "--spec-root",
        type=Path,
        help="Explicit ai-spec root directory (auto-detected if not provided)",
    )

    parser.add_argument(
        "--quiet", "-q",
        action="store_true",
        help="Only output failures",
    )

    parsed = parser.parse_args(args)

    # Resolve target path
    target = parsed.target.resolve()

    if not target.exists():
        print(f"Error: Target not found: {target}", file=sys.stderr)
        return 2

    # Find spec root
    spec_root = parsed.spec_root
    if spec_root:
        spec_root = spec_root.resolve()
    else:
        spec_root = find_spec_root(target)

    # Parse spec type filter
    spec_type = parse_spec_type(parsed.type)

    try:
        # Run validation
        engine = ValidationEngine(spec_root)
        report = engine.validate(target, spec_type)

        # Output results
        if parsed.format == "json":
            print(report.to_json())
        else:
            if parsed.quiet:
                # Only show failures
                for result in report.results:
                    if result.status.value == "FAIL":
                        print(result.format_cli())
            else:
                print(report.format_cli())

        # Return exit code
        return 0 if report.success else 1

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
