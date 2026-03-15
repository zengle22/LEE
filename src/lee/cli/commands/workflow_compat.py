from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple

from lee.orchestrator.execution.artifacts.placement import (
    resolve_ssot_relative_dir,
    resolve_transfer_package_relative_dir,
)
from lee.orchestrator.execution.artifacts.id_parser import parse_src_root
from lee.orchestrator.execution.artifacts.types import SSOTType


def resolve_registry_entry(
    workflows: Mapping[str, Any],
    workflow_key: str,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    raw_entry = deepcopy(dict((workflows or {}).get(workflow_key) or {}))
    canonical_key = raw_entry.get("canonical_workflow") or workflow_key
    canonical_entry = deepcopy(dict((workflows or {}).get(canonical_key) or raw_entry))
    return canonical_key, raw_entry, canonical_entry


def _resolve_first_existing_path(values: Any, project_root: Path | None) -> str | None:
    if not isinstance(values, list):
        return None

    for raw_value in values:
        if not isinstance(raw_value, str):
            continue
        candidate = raw_value.split("#", 1)[0].strip()
        if not candidate:
            continue
        path = Path(candidate)
        if path.is_absolute() and path.exists():
            return path.as_posix()
        if project_root is not None:
            resolved = (project_root / candidate).resolve()
            if resolved.exists():
                return resolved.as_posix()
    return None


def _resolve_formal_ssot_markdown(
    formal_ssot_id: str,
    project_root: Path | None,
    source_refs: Any,
) -> str | None:
    resolved = _resolve_first_existing_path(source_refs, project_root)
    if resolved:
        return resolved
    if not formal_ssot_id or project_root is None:
        return None

    src_root = parse_src_root(formal_ssot_id)
    search_roots = [project_root / "spec" / "requirements"]
    if src_root:
        search_roots.insert(0, project_root / "spec" / "requirements" / src_root)

    patterns = [
        f"{formal_ssot_id}__*.md",
        f"{formal_ssot_id}.md",
    ]
    for root in search_roots:
        if not root.exists():
            continue
        for pattern in patterns:
            matches = sorted(root.rglob(pattern))
            if matches:
                return matches[0].resolve().as_posix()
    return None


def _resolve_governing_adr_paths(governing_adrs: Any, project_root: Path | None) -> list[str]:
    if project_root is None or not isinstance(governing_adrs, list):
        return []

    adr_root = project_root / "spec" / "adr"
    resolved: list[str] = []
    if not adr_root.exists():
        return resolved

    for raw_adr in governing_adrs:
        if not isinstance(raw_adr, str):
            continue
        adr_id = raw_adr.split("#", 1)[0].strip()
        if not adr_id:
            continue
        matches = sorted(adr_root.glob(f"{adr_id}__*.md"))
        if matches:
            resolved.append(matches[0].resolve().as_posix())
    return resolved


def _derive_tech_design_paths(formal_ssot_id: str, project_root: Path | None) -> Dict[str, str]:
    if not formal_ssot_id:
        return {}

    src_root = parse_src_root(formal_ssot_id) or "shared"
    tech_root = resolve_ssot_relative_dir(
        ssot_type=SSOTType.TECH,
        parent_id=formal_ssot_id,
        artifact_id=f"TECH-{formal_ssot_id}",
    )
    bundle_root = resolve_transfer_package_relative_dir("tech_design", formal_ssot_id)

    def _repo_path(path: Path) -> str:
        return path.as_posix()

    return {
        "tech_src_root": src_root,
        "tech_root_dir": _repo_path(tech_root),
        "tech_bundle_dir": _repo_path(bundle_root),
        "frozen_architecture_path": _repo_path(bundle_root / "frozen-technical-architecture.yaml"),
        "design_analysis_path": _repo_path(bundle_root / "design_analysis.md"),
        "implementation_scope_path": _repo_path(bundle_root / "implementation_scope.md"),
        "decision_refs_path": _repo_path(bundle_root / "decision_refs.yaml"),
        "review_result_path": _repo_path(bundle_root / "review_result.md"),
        "risk_register_path": _repo_path(bundle_root / "risk_register.md"),
        "tech_package_path": _repo_path(bundle_root / "tech_package.yaml"),
        "handoff_notes_path": _repo_path(bundle_root / "handoff_notes.md"),
        "tech_spec_path": _repo_path(tech_root / f"TECH-{formal_ssot_id}__tech-design.md"),
    }


def adapt_params_for_workflow(
    workflow_key: str,
    params: Mapping[str, Any],
    *,
    project_root: Path | None = None,
) -> Dict[str, Any]:
    adapted = dict(params or {})

    if workflow_key == "dev.feature":
        feature_spec = adapted.get("feature_spec") or adapted.get("spec")
        feature_point_id = adapted.get("feature_point_id")
        project = adapted.get("project")
        module = adapted.get("module")

        if feature_point_id and "formal_ssot_id" not in adapted:
            adapted["formal_ssot_id"] = feature_point_id
        if feature_spec and "source_refs" not in adapted:
            adapted["source_refs"] = [feature_spec]
        if "governing_adrs" not in adapted:
            adapted["governing_adrs"] = ["ADR-008"]
        if "repo_context" not in adapted:
            repo_id = adapted.get("repo_backend") or adapted.get("repo_frontend") or project
            repo_context = {"repo_id": repo_id, "type": "backend"}
            branch = adapted.get("branch")
            if branch:
                repo_context["branch"] = branch
            adapted["repo_context"] = repo_context
        if "task_refs" not in adapted and project and module and feature_point_id:
            adapted["task_refs"] = [f"{project}:{module}:{feature_point_id}"]

    elif workflow_key == "dev.bugfix":
        bug_id = adapted.get("bug_id")
        bug_description = adapted.get("bug_description")
        reproduction_steps = adapted.get("reproduction_steps")
        repo = adapted.get("repo")

        if bug_id and "bug_ssot_id" not in adapted:
            adapted["bug_ssot_id"] = bug_id

        if "severity" in adapted:
            severity = adapted["severity"]
            if isinstance(severity, str):
                normalized = severity.upper()
                severity_map = {
                    "CRITICAL": "P0",
                    "HIGH": "P1",
                    "MEDIUM": "P2",
                    "LOW": "P2",
                }
                adapted["severity"] = severity_map.get(normalized, normalized)

        if "reproduction_evidence" not in adapted:
            evidence: Dict[str, Any] = {}
            if bug_description:
                evidence["description"] = bug_description
            if reproduction_steps:
                evidence["steps"] = reproduction_steps
            if bug_description or reproduction_steps:
                evidence["summary"] = reproduction_steps or bug_description
                adapted["reproduction_evidence"] = evidence

        if "repo_context" not in adapted and repo:
            adapted["repo_context"] = {"repo_id": repo, "type": "backend"}

    elif workflow_key in {"dev.tech-design-l3", "dev.tech_design_l3"}:
        formal_ssot_id = str(adapted.get("formal_ssot_id") or "").strip()
        if formal_ssot_id:
            derived_paths = _derive_tech_design_paths(formal_ssot_id, project_root)
            for key, value in derived_paths.items():
                adapted.setdefault(key, value)

            formal_ssot_path = _resolve_formal_ssot_markdown(
                formal_ssot_id,
                project_root,
                adapted.get("source_refs"),
            )
            if formal_ssot_path:
                adapted.setdefault("formal_ssot_path", formal_ssot_path)
                source_refs = adapted.get("source_refs")
                if not isinstance(source_refs, list):
                    source_refs = []
                if formal_ssot_path not in source_refs:
                    adapted["source_refs"] = [formal_ssot_path, *source_refs]

            governing_adr_paths = _resolve_governing_adr_paths(
                adapted.get("governing_adrs"),
                project_root,
            )
            if governing_adr_paths:
                adapted.setdefault("governing_adr_paths", governing_adr_paths)

    return adapted
