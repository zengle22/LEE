"""
SSOT file parsing helpers.

Formal SSOT objects are stored as Markdown files with YAML front matter.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Tuple

import yaml

from .placement import resolve_ssot_relative_dir
from .types import SSOTType
from .id_parser import parse_src_root


def parse_front_matter(path: Path) -> Tuple[Dict[str, Any], str]:
    """
    Parse a Markdown file with YAML front matter.

    Returns:
        (front_matter, body)
    """
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path} missing YAML front matter")

    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{path} has invalid YAML front matter format")

    front_matter = yaml.safe_load(parts[1]) or {}
    body = parts[2].lstrip("\r\n")
    return front_matter, body


def iter_ssot_markdown_files(project_root: Path) -> Iterable[Path]:
    """Yield formal SSOT markdown files under managed directories."""
    candidate_dirs = [
        project_root / "spec",
        project_root / "tests",
        project_root / "docs" / "reports",
    ]
    for base_dir in candidate_dirs:
        if not base_dir.exists():
            continue
        for path in base_dir.rglob("*.md"):
            yield path


def is_formal_ssot_file(path: Path) -> bool:
    """Whether a markdown file should be treated as a formal SSOT object."""
    if "__" in path.name:
        return True
    try:
        front_matter, _ = parse_front_matter(path)
    except Exception:
        return False
    return bool(front_matter.get("ssot_type"))


def lint_ssot_front_matter(project_root: Path, paths: Iterable[Path] | None = None) -> List[str]:
    """Validate formal SSOT markdown files only."""
    errors: List[str] = []
    required_fields = {"id", "ssot_type", "title", "status", "version"}
    seen_ids: Dict[str, List[Path]] = {}
    candidates = list(paths) if paths is not None else list(iter_ssot_markdown_files(project_root))
    for path in candidates:
        if not is_formal_ssot_file(path):
            continue
        try:
            front_matter, _ = parse_front_matter(path)
        except Exception as exc:
            errors.append(str(exc))
            continue

        missing = sorted(field for field in required_fields if not front_matter.get(field))
        if missing:
            errors.append(f"{path}: missing fields {', '.join(missing)}")
        file_id = path.name.split("__", 1)[0]
        if front_matter.get("id") and file_id != front_matter["id"]:
            errors.append(f"{path}: filename ID {file_id} != front matter id {front_matter['id']}")
        artifact_id = front_matter.get("id")
        if artifact_id:
            seen_ids.setdefault(str(artifact_id), []).append(path)

        ssot_type_value = front_matter.get("ssot_type")
        if artifact_id and ssot_type_value:
            try:
                ssot_type = SSOTType(str(ssot_type_value))
            except ValueError:
                ssot_type = None
            if ssot_type is not None:
                properties = front_matter.get("properties") or {}
                requires_scoped_placement = bool(properties.get("src_root_id")) or bool(parse_src_root(str(artifact_id)))
                expected_dir = resolve_ssot_relative_dir(
                    ssot_type,
                    parent_id=front_matter.get("parent_id"),
                    source_refs=front_matter.get("source_refs") if requires_scoped_placement else None,
                    artifact_id=str(artifact_id),
                    properties=properties,
                )
                actual_dir = path.relative_to(project_root).parent.as_posix()
                if actual_dir != expected_dir.as_posix():
                    errors.append(
                        f"{path}: expected placement {expected_dir.as_posix()} for {artifact_id}, got {actual_dir}"
                    )

    for artifact_id, paths in sorted(seen_ids.items()):
        if len(paths) > 1:
            rendered = ", ".join(str(path) for path in sorted(paths))
            errors.append(f"duplicate SSOT id {artifact_id}: {rendered}")
    return errors
