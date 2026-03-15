from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, Mapping, Tuple


def resolve_registry_entry(
    workflows: Mapping[str, Any],
    workflow_key: str,
) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
    raw_entry = deepcopy(dict((workflows or {}).get(workflow_key) or {}))
    canonical_key = raw_entry.get("canonical_workflow") or workflow_key
    canonical_entry = deepcopy(dict((workflows or {}).get(canonical_key) or raw_entry))
    return canonical_key, raw_entry, canonical_entry


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

    return adapted
