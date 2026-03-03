#!/usr/bin/env python3
"""
GitIgnore Updater - Cross-platform .gitignore updater

Usage:
    python gitignore_updater.py --workspace PATH --patterns '["*.tmp", "*.log"]' [--gitignore PATH]

This script:
1. Reads existing .gitignore (if exists)
2. Parses and analyzes existing patterns
3. Adds new patterns by category
4. Creates backup before modification
5. Writes updated .gitignore
"""

import argparse
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set


# Category headers for organization
CATEGORY_HEADERS = {
    "temporary_files": "# Temporary files",
    "build_artifacts": "# Build artifacts",
    "ide_files": "# IDE and editor files",
    "os_files": "# OS generated files",
    "dependencies": "# Dependencies",
    "logs": "# Logs",
    "cache": "# Cache",
    "other": "# Other",
}

# Default patterns by category
DEFAULT_PATTERNS = {
    "temporary_files": ["*.tmp", "*.temp", "*.swp", "*~"],
    "build_artifacts": ["*.pyc", "__pycache__/", "*.class", "*.o", "*.so", "*.dylib", "dist/", "build/"],
    "ide_files": [".vscode/", ".idea/", "*.sublime-*"],
    "os_files": [".DS_Store", "Thumbs.db", "desktop.ini"],
    "dependencies": ["node_modules/", "vendor/", ".pnp.*"],
    "logs": ["*.log", "logs/"],
    "cache": [".cache/", ".pytest_cache/", ".mypy_cache/"],
}


def parse_existing_gitignore(content: str) -> Dict[str, List[str]]:
    """Parse existing .gitignore content into categories."""
    patterns: Dict[str, List[str]] = {"uncategorized": []}
    current_category = "uncategorized"

    for line in content.splitlines():
        stripped = line.strip()

        # Skip empty lines
        if not stripped:
            continue

        # Check for category comments
        if stripped.startswith("#"):
            # Try to match category
            lower_comment = stripped.lower()
            for cat_key, cat_header in CATEGORY_HEADERS.items():
                if cat_key in lower_comment or cat_header.lower() in lower_comment:
                    current_category = cat_key
                    break
            else:
                # It's a regular comment, keep it with the next patterns
                if current_category not in patterns:
                    patterns[current_category] = []
                patterns[current_category].append(stripped)
            continue

        # It's a pattern
        if current_category not in patterns:
            patterns[current_category] = []
        patterns[current_category].append(stripped)

    return patterns


def get_all_existing_patterns(content: str) -> Set[str]:
    """Extract all existing patterns from .gitignore content."""
    patterns: Set[str] = set()

    for line in content.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.add(stripped)

    return patterns


def organize_patterns_by_category(
    new_patterns: List[Dict],
    existing_patterns: Set[str]
) -> Dict[str, List[str]]:
    """Organize new patterns by category, excluding already existing ones."""
    organized: Dict[str, List[str]] = {}

    for item in new_patterns:
        pattern = item.get("pattern", "")
        if not pattern:
            continue

        # Skip if already exists
        if pattern in existing_patterns:
            continue

        category = item.get("category", "other")
        comment = item.get("comment", "")

        if category not in organized:
            organized[category] = []

        # Add comment if provided
        if comment and comment not in organized[category]:
            organized[category].append(f"# {comment}")

        organized[category].append(pattern)

    return organized


def generate_gitignore_content(
    existing_content: str,
    new_patterns_by_category: Dict[str, List[str]],
    preserve_structure: bool = True
) -> str:
    """Generate updated .gitignore content."""
    lines: List[str] = []

    # Add header with timestamp
    lines.append("# .gitignore")
    lines.append(f"# Updated by LEE gitignore-updater at {datetime.now().isoformat()}")
    lines.append("")

    # Preserve existing content if requested and not empty
    if preserve_structure and existing_content.strip():
        lines.append(existing_content.rstrip())
        lines.append("")

    # Add new patterns organized by category
    if new_patterns_by_category:
        lines.append("# === Patterns added by LEE ===")
        lines.append("")

        for category in ["temporary_files", "build_artifacts", "ide_files", "os_files",
                        "dependencies", "logs", "cache", "other"]:
            if category in new_patterns_by_category:
                patterns = new_patterns_by_category[category]

                # Add category header
                header = CATEGORY_HEADERS.get(category, f"# {category.title()}")
                lines.append(header)
                lines.append("")

                for pattern in patterns:
                    lines.append(pattern)

                lines.append("")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="Update .gitignore file with new patterns"
    )
    parser.add_argument(
        "--workspace",
        required=True,
        help="Workspace directory path"
    )
    parser.add_argument(
        "--patterns",
        required=True,
        help="JSON array of patterns to add, each with 'pattern', 'category', and optional 'comment'"
    )
    parser.add_argument(
        "--gitignore",
        default=".gitignore",
        help="Path to .gitignore file (relative to workspace, default: .gitignore)"
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating backup of existing .gitignore"
    )
    parser.add_argument(
        "--output-json",
        action="store_true",
        help="Output result as JSON"
    )

    args = parser.parse_args()

    # Resolve paths
    workspace_path = Path(args.workspace).resolve()
    gitignore_path = workspace_path / args.gitignore

    # Parse input patterns - use defaults if parsing fails
    patterns_to_add = []
    try:
        if args.patterns and args.patterns.strip():
            patterns_to_add = json.loads(args.patterns)
            if not isinstance(patterns_to_add, list):
                patterns_to_add = []
    except json.JSONDecodeError as e:
        print(f"Warning: Invalid JSON in patterns, using defaults: {e}", file=sys.stderr)
        patterns_to_add = []

    # If no patterns provided, use sensible defaults
    if not patterns_to_add:
        print("Info: No patterns provided, using default recommendations", file=sys.stderr)
        patterns_to_add = [
            {"pattern": "__pycache__/", "category": "build_artifacts", "comment": "Python cache"},
            {"pattern": "*.pyc", "category": "build_artifacts", "comment": "Python bytecode"},
            {"pattern": "*.pyo", "category": "build_artifacts", "comment": "Python optimized bytecode"},
            {"pattern": ".Python", "category": "build_artifacts", "comment": "Python virtual env"},
            {"pattern": "*.so", "category": "build_artifacts", "comment": "Shared object files"},
            {"pattern": ".env", "category": "environment", "comment": "Environment variables"},
            {"pattern": ".env.local", "category": "environment", "comment": "Local environment"},
            {"pattern": "*.log", "category": "logs", "comment": "Log files"},
            {"pattern": ".DS_Store", "category": "os_files", "comment": "macOS folder info"},
            {"pattern": "Thumbs.db", "category": "os_files", "comment": "Windows thumbnail cache"},
            {"pattern": ".vscode/", "category": "ide_files", "comment": "VS Code config"},
            {"pattern": ".idea/", "category": "ide_files", "comment": "IntelliJ IDEA config"},
        ]

    # Read existing .gitignore
    existing_content = ""
    if gitignore_path.exists():
        try:
            existing_content = gitignore_path.read_text(encoding="utf-8")
        except Exception as e:
            print(f"Error reading .gitignore: {e}", file=sys.stderr)
            sys.exit(1)

    # Get existing patterns
    existing_patterns = get_all_existing_patterns(existing_content)

    # Organize new patterns by category
    new_patterns_by_category = organize_patterns_by_category(
        patterns_to_add,
        existing_patterns
    )

    # Check if there are any new patterns to add
    total_new = sum(len(p) for p in new_patterns_by_category.values())
    # Filter out comments from count
    actual_new_patterns = [
        p for patterns in new_patterns_by_category.values()
        for p in patterns
        if not p.startswith("#")
    ]

    if not actual_new_patterns:
        result = {
            "updated": False,
            "patterns_added": [],
            "message": "No new patterns to add (all patterns already exist)",
            "gitignore_path": str(gitignore_path),
        }
        if args.output_json:
            print(json.dumps(result, indent=2))
        else:
            print("No new patterns to add - .gitignore is up to date")
        sys.exit(0)

    # Create backup
    backup_path = None
    if not args.no_backup and gitignore_path.exists():
        backup_path = gitignore_path.with_suffix(".gitignore.backup")
        try:
            shutil.copy2(gitignore_path, backup_path)
        except Exception as e:
            print(f"Warning: Could not create backup: {e}", file=sys.stderr)
            backup_path = None

    # Generate new content
    new_content = generate_gitignore_content(
        existing_content,
        new_patterns_by_category,
        preserve_structure=True
    )

    # Write new .gitignore
    try:
        # Ensure parent directory exists
        gitignore_path.parent.mkdir(parents=True, exist_ok=True)
        gitignore_path.write_text(new_content, encoding="utf-8")
    except Exception as e:
        print(f"Error writing .gitignore: {e}", file=sys.stderr)
        sys.exit(1)

    result = {
        "updated": True,
        "patterns_added": actual_new_patterns,
        "total_added": len(actual_new_patterns),
        "gitignore_path": str(gitignore_path),
        "gitignore_content": new_content,
        "backup_path": str(backup_path) if backup_path else None,
        "message": f"Successfully added {len(actual_new_patterns)} new patterns to .gitignore",
    }

    if args.output_json:
        print(json.dumps(result, indent=2))
    else:
        print(f"Updated .gitignore with {len(actual_new_patterns)} new patterns:")
        for pattern in actual_new_patterns:
            print(f"  + {pattern}")
        if backup_path:
            print(f"Backup created: {backup_path}")


if __name__ == "__main__":
    main()
