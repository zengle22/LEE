#!/usr/bin/env python
"""
Shared SSOT checks for local git hooks.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Iterable, List, Sequence


REPO_ROOT = Path(__file__).resolve().parent.parent
SRC_ROOT = REPO_ROOT / "src"
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTValidator
from lee.orchestrator.execution.artifacts.ssot_files import (
    lint_ssot_front_matter,
    parse_front_matter,
)
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService


def is_ssot_related_path(file_path: str) -> bool:
    path = Path(file_path)
    normalized = path.as_posix()

    if normalized.startswith(("spec/", "tests/", "docs/reports/")) and path.suffix.lower() == ".md":
        return True

    if normalized.startswith("src/lee/orchestrator/execution/artifacts/"):
        return True

    if normalized == "src/lee/cli/commands/ssot.py":
        return True

    if normalized.startswith("spec-global/core/contracts/ssot-agent-output/"):
        return True

    return False


def collect_release_ids(paths: Iterable[str]) -> List[str]:
    release_ids = []
    for file_path in paths:
        path = REPO_ROOT / file_path
        if not path.exists() or path.suffix.lower() != ".md":
            continue
        try:
            front_matter, _ = parse_front_matter(path)
        except Exception:
            continue
        if front_matter.get("ssot_type") == "release" and front_matter.get("id"):
            release_ids.append(front_matter["id"])
    return sorted(set(release_ids))


def run_ssot_lint() -> tuple[bool, List[str]]:
    manager = ArtifactManager(project_root=REPO_ROOT, root_path=REPO_ROOT / ".artifacts")
    manager.rebuild_ssot_registry()
    errors: List[str] = lint_ssot_front_matter(REPO_ROOT)

    validator = SSOTValidator(manager.registry)
    for artifact in manager.registry.get_ssot_artifacts():
        result = validator.validate_p0(artifact.id)
        errors.extend(f"{artifact.id}: {err}" for err in result.errors)

    return len(errors) == 0, errors


def run_release_checks(release_ids: Sequence[str]) -> tuple[bool, List[str]]:
    if not release_ids:
        return True, []

    manager = ArtifactManager(project_root=REPO_ROOT, root_path=REPO_ROOT / ".artifacts")
    service = SSOTService(manager)
    errors: List[str] = []

    for release_id in release_ids:
        result = service.release_check(release_id)
        errors.extend(f"{release_id}: {err}" for err in result["errors"])

    return len(errors) == 0, errors
