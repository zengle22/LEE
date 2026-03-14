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
    lint_ssot_workflow_provenance,
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


def is_formal_ssot_markdown_path(file_path: str) -> bool:
    path = Path(file_path)
    normalized = path.as_posix()
    return (
        path.suffix.lower() == ".md"
        and normalized.startswith(("spec/", "tests/", "docs/reports/"))
    )


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


def run_ssot_lint(changed_paths: Sequence[str] | None = None) -> tuple[bool, List[str]]:
    manager = ArtifactManager(project_root=REPO_ROOT, root_path=REPO_ROOT / ".artifacts")
    manager.rebuild_ssot_registry()
    selected_paths = [
        (REPO_ROOT / file_path)
        for file_path in (changed_paths or [])
        if is_formal_ssot_markdown_path(file_path) and (REPO_ROOT / file_path).exists()
    ]
    if changed_paths is not None and not selected_paths:
        return True, []

    errors: List[str] = lint_ssot_front_matter(
        REPO_ROOT,
        paths=selected_paths if changed_paths is not None else None,
    )

    validator = SSOTValidator(manager.registry)
    artifact_ids: List[str] = []
    if changed_paths is None:
        artifact_ids = [artifact.id for artifact in manager.registry.get_ssot_artifacts()]
    else:
        for path in selected_paths:
            try:
                front_matter, _ = parse_front_matter(path)
            except Exception:
                continue
            artifact_id = front_matter.get("id")
            if artifact_id:
                artifact_ids.append(str(artifact_id))

    for artifact_id in sorted(set(artifact_ids)):
        result = validator.validate_p0(artifact_id)
        errors.extend(f"{artifact_id}: {err}" for err in result.errors)

    if changed_paths:
        errors.extend(
            lint_ssot_workflow_provenance(
                REPO_ROOT,
                [Path(path) for path in changed_paths if is_ssot_related_path(path)],
            )
        )

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
