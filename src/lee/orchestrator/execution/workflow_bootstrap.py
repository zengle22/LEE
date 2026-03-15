from __future__ import annotations

from typing import Any, Dict, Mapping


_CONTEXT_KEYS = (
    "project",
    "module",
    "module_version",
    "prd_path",
    "feature_point_id",
    "feature_spec",
    "formal_ssot_id",
    "source_refs",
    "governing_adrs",
    "repo_context",
    "repo_frontend",
    "repo_backend",
    "task_refs",
    "acceptance_brief_ref",
    "decision_refs",
    "decision_constraints",
    "architecture_constraints",
    "process_constraints",
    "env_ref",
    "bug_ssot_id",
    "severity",
    "reproduction_evidence",
    "test_case_refs",
    "batch_mode",
    "batch_context",
    "batch_approval_record",
    "repo",
)


def _normalize_repos(raw_repos: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_repos, list):
        return []

    repos: list[dict[str, Any]] = []
    for item in raw_repos:
        if not isinstance(item, dict):
            continue
        repo_id = item.get("id")
        if not isinstance(repo_id, str) or not repo_id:
            continue
        repos.append(dict(item))
    return repos


def _append_repo(repos: list[dict[str, Any]], repo_id: Any, repo_type: str) -> None:
    if not isinstance(repo_id, str) or not repo_id:
        return
    if any(repo.get("id") == repo_id for repo in repos):
        return
    repos.append({"id": repo_id, "type": repo_type})


def build_runtime_context_from_params(
    params: Mapping[str, Any],
    existing_context: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    context: Dict[str, Any] = dict(existing_context or {})

    for key in _CONTEXT_KEYS:
        value = params.get(key)
        if value is not None and key not in context:
            context[key] = value

    repos = _normalize_repos(context.get("repos"))
    _append_repo(repos, params.get("repo_frontend"), "frontend")
    _append_repo(repos, params.get("repo_backend"), "backend")
    _append_repo(repos, params.get("repo"), "backend")

    repo_context = params.get("repo_context")
    if isinstance(repo_context, dict):
        repo_id = repo_context.get("repo_id") or repo_context.get("id")
        repo_type = repo_context.get("repo_type") or repo_context.get("type") or "backend"
        _append_repo(repos, repo_id, str(repo_type))
    elif isinstance(repo_context, list):
        for item in repo_context:
            if not isinstance(item, dict):
                continue
            repo_id = item.get("repo_id") or item.get("id")
            repo_type = item.get("repo_type") or item.get("type") or "backend"
            _append_repo(repos, repo_id, str(repo_type))

    if repos:
        context["repos"] = repos

    return context


def hydrate_l2_bootstrap(
    workflow_bootstrap: Mapping[str, Any],
    params: Mapping[str, Any],
) -> Dict[str, Any]:
    hydrated = dict(workflow_bootstrap or {})
    context = build_runtime_context_from_params(params, hydrated.get("context"))
    if context:
        hydrated["context"] = context
    return hydrated
