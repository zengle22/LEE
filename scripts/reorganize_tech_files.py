#!/usr/bin/env python
"""
Reorganize TECH files following SSOT placement rules.

TECH files should be placed in:
- spec/tech/SRC-XXX/ for files that can be traced to a SRC
- spec/tech/SRC-NO-SOURCE/ for files without SRC binding
"""

import os
import re
import shutil
from pathlib import Path
from datetime import datetime

REPO_ROOT = Path(__file__).resolve().parent.parent
TECH_DIR = REPO_ROOT / "spec" / "tech"
TARGET_BASE = REPO_ROOT / "spec" / "tech"

# FEAT to SRC mapping based on EPIC tracing
FEAT_TO_SRC_MAP = {
    # FEAT-SRC-001 through FEAT-SRC-012 (direct SRC references)
    "FEAT-SRC-001": "SRC-001",
    "FEAT-SRC-002": "SRC-002",
    "FEAT-SRC-003": "SRC-003",
    "FEAT-SRC-004": "SRC-004",
    "FEAT-SRC-005": "SRC-005",
    "FEAT-SRC-006": "SRC-006",
    "FEAT-SRC-007": "SRC-007",
    "FEAT-SRC-008": "SRC-008",
    "FEAT-SRC-009": "SRC-009",
    "FEAT-SRC-010": "SRC-010",
    "FEAT-SRC-011": "SRC-011",
    "FEAT-SRC-012": "SRC-012",

    # FEAT-012-xxx: Kimi executor (EPIC-044, no SRC) -> SRC-NO-SOURCE
    "FEAT-012-001": "SRC-NO-SOURCE",
    "FEAT-012-002": "SRC-NO-SOURCE",
    "FEAT-012-003": "SRC-NO-SOURCE",

    # FEAT-080~088: CLI refactoring (EPIC-017, no SRC) -> SRC-NO-SOURCE
    "FEAT-080-001": "SRC-NO-SOURCE",
    "FEAT-081-001": "SRC-NO-SOURCE",
    "FEAT-082-001": "SRC-NO-SOURCE",
    "FEAT-083-001": "SRC-NO-SOURCE",
    "FEAT-084-001": "SRC-NO-SOURCE",
    "FEAT-085-001": "SRC-NO-SOURCE",
    "FEAT-086-001": "SRC-NO-SOURCE",
    "FEAT-087-001": "SRC-NO-SOURCE",
    "FEAT-088-001": "SRC-NO-SOURCE",

    # FEAT-090-001: Branch/Worktree (EPIC-017, no SRC) -> SRC-NO-SOURCE
    "FEAT-090-001": "SRC-NO-SOURCE",

    # FEAT-SRC-009-*: SRC-009 frozen architecture docs
    "FEAT-SRC-009": "SRC-009",

    # FEAT-100~105: Workflow refactoring (SRC-009)
    "FEAT-100-001": "SRC-009",
    "FEAT-101-001": "SRC-009",
    "FEAT-102-001": "SRC-009",
    "FEAT-103-001": "SRC-009",
    "FEAT-104-001": "SRC-009",
    "FEAT-105-001": "SRC-009",

    # FEAT-143-xxx: QA execution (EPIC-141, no SRC) -> SRC-NO-SOURCE
    "FEAT-143-001": "SRC-NO-SOURCE",
    "FEAT-143-002": "SRC-NO-SOURCE",
    "FEAT-143-003": "SRC-NO-SOURCE",
    "FEAT-143-004": "SRC-NO-SOURCE",
    "FEAT-143-005": "SRC-NO-SOURCE",
    "FEAT-143-006": "SRC-NO-SOURCE",
    "FEAT-143-007": "SRC-NO-SOURCE",
    "FEAT-143-008": "SRC-NO-SOURCE",
    "FEAT-143-009": "SRC-NO-SOURCE",
    "FEAT-143-010": "SRC-NO-SOURCE",
    "FEAT-143-011": "SRC-NO-SOURCE",
    "FEAT-143-012": "SRC-NO-SOURCE",
    "FEAT-143-013": "SRC-NO-SOURCE",
    "FEAT-143-014": "SRC-NO-SOURCE",
    "FEAT-143-015": "SRC-NO-SOURCE",
    "FEAT-143-016": "SRC-NO-SOURCE",

    # FEAT-169-xxx: Qwen (EPIC-022 -> SRC-011)
    "FEAT-169-001": "SRC-011",
    "FEAT-169-002": "SRC-011",
    "FEAT-169-003": "SRC-011",
    "FEAT-169-004": "SRC-011",

    # FEAT-170~173: Qwen executor (EPIC-022 -> SRC-011)
    "FEAT-170-001": "SRC-011",
    "FEAT-171-001": "SRC-011",
    "FEAT-172-001": "SRC-011",
    "FEAT-173-001": "SRC-011",
}

def extract_feat_id(filename: str) -> str:
    """Extract FEAT ID from filename."""
    # Pattern: TECH-{FEAT_ID}__...
    match = re.search(r"TECH-(FEAT[^_]+)", filename)
    if match:
        feat_id = match.group(1)
        # Handle TECH-FEAT-SRC-009-* pattern
        if feat_id.startswith("FEAT-SRC-009"):
            return "FEAT-SRC-009"
        return feat_id
    return ""

def add_workflow_instance_id(content: str, filename: str) -> str:
    """Add workflow_instance_id to YAML front matter if missing."""
    if "workflow_instance_id:" in content:
        return content

    # Generate a deterministic workflow_instance_id based on filename
    base_id = filename.replace(".md", "").upper()
    workflow_id = f"wf-{base_id.lower()}-{datetime.now().strftime('%Y%m%d')}"

    # Insert workflow_instance_id after the frozen_at line
    lines = content.split("\n")
    new_lines = []
    inserted = False

    for i, line in enumerate(lines):
        new_lines.append(line)
        if line.strip().startswith("frozen_at:") and not inserted:
            # Add workflow_instance_id after frozen_at
            new_lines.append(f"workflow_instance_id: {workflow_id}")
            inserted = True

    if inserted:
        return "\n".join(new_lines)

    # Fallback: add before the closing ---
    for i, line in enumerate(new_lines):
        if line.strip() == "---" and i > 0:
            new_lines.insert(i, f"workflow_instance_id: {workflow_id}")
            break

    return "\n".join(new_lines)

def reorganize_tech_files():
    """Main reorganization function."""
    print("=== TECH File Reorganization ===\n")

    # Collect all TECH files
    tech_files = []

    # Files directly in spec/tech/
    for f in TECH_DIR.glob("TECH-*.md"):
        tech_files.append(f)

    # Files in subdirectories (FEAT-143/, etc.)
    for subdir in TECH_DIR.iterdir():
        if subdir.is_dir():
            for f in subdir.glob("*.md"):
                tech_files.append(f)

    print(f"Found {len(tech_files)} TECH files\n")

    # Classify and move files
    moved_count = 0
    for tech_file in tech_files:
        filename = tech_file.name
        feat_id = extract_feat_id(filename)

        # Determine target SRC directory
        target_src = FEAT_TO_SRC_MAP.get(feat_id, "SRC-NO-SOURCE")
        target_dir = TARGET_BASE / target_src

        # Create target directory if needed
        target_dir.mkdir(parents=True, exist_ok=True)

        # Handle subdirectory files
        if tech_file.parent != TECH_DIR:
            # File is in a subdirectory
            target_path = target_dir / filename
        else:
            target_path = target_dir / filename

        # Read and update content
        content = tech_file.read_text(encoding="utf-8")
        content = add_workflow_instance_id(content, filename)

        # Handle merge conflicts
        if "<<<<<<" in content and "======" in content and ">>>>>>" in content:
            print(f"⚠️  Resolving merge conflict in {filename}")
            lines = content.split("\n")
            resolved_lines = []
            in_conflict = False
            keep_first = True

            for line in lines:
                if line.startswith("<<<<<<<"):
                    in_conflict = True
                    keep_first = True
                    continue
                elif line.startswith("======="):
                    keep_first = False
                    continue
                elif line.startswith(">>>>>>>"):
                    in_conflict = False
                    continue
                elif in_conflict:
                    if keep_first:
                        resolved_lines.append(line)
                else:
                    resolved_lines.append(line)

            content = "\n".join(resolved_lines)

        # Write to target location
        target_path.write_text(content, encoding="utf-8")
        print(f"✓ Moved {filename} → {target_src}/")
        moved_count += 1

        # Remove original file
        if tech_file.parent != TARGET_BASE:  # Don't delete if already in target
            tech_file.unlink()

    print(f"\n=== Summary ===")
    print(f"Moved {moved_count} TECH files to spec/tech/SRC-XXX/ directories")

    # Clean up empty subdirectories
    for subdir in TECH_DIR.iterdir():
        if subdir.is_dir() and not any(subdir.iterdir()):
            subdir.rmdir()
            print(f"Removed empty directory: {subdir.name}")

if __name__ == "__main__":
    reorganize_tech_files()
