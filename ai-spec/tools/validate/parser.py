"""Spec file parser - handles YAML, JSON, and extracts metadata."""

import json
import re
from pathlib import Path
from typing import Any, Optional, Tuple

import yaml

from .models import SpecType, ValidationIssue


class ParseError(Exception):
    """Error during parsing."""

    def __init__(self, message: str, line: Optional[int] = None, column: Optional[int] = None):
        super().__init__(message)
        self.line = line
        self.column = column


def parse_file(path: Path) -> Tuple[Any, Optional[ValidationIssue]]:
    """Parse a YAML or JSON file.

    Returns:
        Tuple of (parsed_content, error_issue)
        If parsing succeeds, error_issue is None.
        If parsing fails, parsed_content is None and error_issue contains details.
    """
    suffix = path.suffix.lower()

    try:
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()

        if suffix in (".yaml", ".yml"):
            return yaml.safe_load(content), None
        elif suffix == ".json":
            return json.loads(content), None
        else:
            # Try YAML first (more permissive), then JSON
            try:
                return yaml.safe_load(content), None
            except yaml.YAMLError:
                try:
                    return json.loads(content), None
                except json.JSONDecodeError:
                    return None, ValidationIssue(
                        message=f"Unknown file format: {suffix}",
                        validator="parser",
                        severity="error",
                    )

    except yaml.YAMLError as e:
        line = getattr(e, "problem_mark", None)
        return None, ValidationIssue(
            message=f"YAML syntax error: {e}",
            validator="parser",
            severity="error",
            line=line.line + 1 if line else None,
            column=line.column + 1 if line else None,
        )

    except json.JSONDecodeError as e:
        return None, ValidationIssue(
            message=f"JSON syntax error: {e.msg}",
            validator="parser",
            severity="error",
            line=e.lineno,
            column=e.colno,
        )

    except FileNotFoundError:
        return None, ValidationIssue(
            message=f"File not found: {path}",
            validator="parser",
            severity="error",
        )

    except Exception as e:
        return None, ValidationIssue(
            message=f"Failed to read file: {e}",
            validator="parser",
            severity="error",
        )


def detect_spec_type(path: Path, content: dict) -> SpecType:
    """Detect the type of spec from path and content.

    Detection rules:
    1. Path-based: /workflows/ → workflow, /agents/ → agent, /contracts/ → contract
    2. Content-based: presence of specific keys or 'kind' field
    """
    path_str = str(path)

    # Project detection (by filename or kind)
    if path.name == "project.yaml" or path.name == "project.yml":
        return SpecType.PROJECT

    # Content-based: check 'kind' field first (most reliable)
    if content and isinstance(content, dict):
        kind = content.get("kind")
        if kind == "project":
            return SpecType.PROJECT
        if kind == "workflow":
            return SpecType.WORKFLOW
        if kind == "agent":
            return SpecType.AGENT
        if kind == "contract":
            return SpecType.CONTRACT

    # Path-based detection
    if "/workflows/" in path_str or "workflow.yaml" in path_str:
        return SpecType.WORKFLOW

    if "/agents/" in path_str or path_str.endswith("agent.yaml"):
        return SpecType.AGENT

    if "/contracts/" in path_str or "schema.yaml" in path_str:
        return SpecType.CONTRACT

    # Content-based detection (fallback for legacy files without 'kind')
    if content:
        if "stages" in content or "pipeline" in content:
            return SpecType.WORKFLOW
        if "responsibility" in content or "downstream" in content:
            return SpecType.AGENT
        if "properties" in content or "required" in content:
            return SpecType.CONTRACT
        if "repositories" in content or "path_aliases" in content:
            return SpecType.PROJECT

    return SpecType.UNKNOWN


def extract_spec_id(path: Path, content: dict) -> Tuple[str, str]:
    """Extract spec ID and version from path and content.

    Returns:
        Tuple of (spec_id, version)

    Path patterns:
    - specs/agents/<name>/v1/agent.yaml → (<name>, v1)
    - specs/workflows/<name>/v1/workflow.yaml → (<name>, v1)
    - specs/contracts/<name>/v1/schema.yaml → (<name>, v1)
    """
    # Try to extract from path pattern: <type>/<name>/v<num>/
    parts = path.parts
    version = "v1"  # default

    # Look for version pattern in path
    for i, part in enumerate(parts):
        if re.match(r"v\d+", part):
            version = part
            # ID is typically the part before version
            if i > 0:
                spec_id = parts[i - 1]
                return spec_id, version

    # Fallback: try to get from content
    if content:
        spec_id = content.get("id") or content.get("name") or path.stem
        version = content.get("version", version)
        return str(spec_id), str(version)

    # Last resort: use filename
    return path.stem, version


def find_spec_files(root: Path, spec_type: Optional[SpecType] = None) -> list[Path]:
    """Find all spec files under root directory.

    Args:
        root: Directory to search
        spec_type: Optional filter by spec type

    Returns:
        List of paths to spec files
    """
    patterns = {
        SpecType.WORKFLOW: ["**/workflow.yaml", "**/workflow.yml"],
        SpecType.AGENT: ["**/agent.yaml", "**/agent.yml"],
        SpecType.CONTRACT: ["**/schema.yaml", "**/schema.yml"],
        SpecType.PROJECT: ["**/project.yaml", "**/project.yml"],
    }

    if spec_type and spec_type != SpecType.UNKNOWN:
        globs = patterns.get(spec_type, [])
    else:
        globs = []
        for p in patterns.values():
            globs.extend(p)

    files = []
    for pattern in globs:
        files.extend(root.glob(pattern))

    # Deduplicate and sort
    return sorted(set(files))
