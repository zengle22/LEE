from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


@dataclass(frozen=True)
class ConcurrencyScopeInfo:
    workflow_key: str
    concurrency_scope: str
    concurrency_key: str
    scope_source: str


def workflow_conflict_key(workflow_key: str, concurrency_scope: str) -> str:
    return f"{workflow_key}::{concurrency_scope}"


def _project_scope(project_root: Path, workflow_key: str, *, fallback: bool) -> ConcurrencyScopeInfo:
    project_token = str(project_root.resolve())
    if fallback:
        concurrency_scope = f"project:{project_token}:workflow:{workflow_key}"
        scope_source = "fallback:project+workflow_key"
    else:
        concurrency_scope = f"project:{project_token}"
        scope_source = "workflow_rule:project_root"
    return ConcurrencyScopeInfo(
        workflow_key=workflow_key,
        concurrency_scope=concurrency_scope,
        concurrency_key=workflow_conflict_key(workflow_key, concurrency_scope),
        scope_source=scope_source,
    )


def _extract_artifact_id(value: Any) -> str | None:
    if isinstance(value, Mapping):
        artifact_id = value.get("artifact_id")
        if isinstance(artifact_id, str) and artifact_id.strip():
            return artifact_id.strip()
    return None


def derive_concurrency_scope(
    workflow_key: str,
    params: Mapping[str, Any] | None,
    project_root: Path,
) -> ConcurrencyScopeInfo:
    params = params or {}

    if workflow_key == "product.src-to-epic":
        return _project_scope(project_root, workflow_key, fallback=False)

    if workflow_key == "product.epic-to-feat":
        artifact_id = _extract_artifact_id(params.get("epic_freeze"))
        if artifact_id:
            concurrency_scope = f"epic:{artifact_id}"
            return ConcurrencyScopeInfo(
                workflow_key=workflow_key,
                concurrency_scope=concurrency_scope,
                concurrency_key=workflow_conflict_key(workflow_key, concurrency_scope),
                scope_source="params.epic_freeze.artifact_id",
            )
        return _project_scope(project_root, workflow_key, fallback=True)

    return _project_scope(project_root, workflow_key, fallback=True)


def describe_conflict_scope(info: ConcurrencyScopeInfo) -> str:
    return (
        "检测到同一并发作用域的旧流程\n"
        f"workflow_key={info.workflow_key}\n"
        f"concurrency_scope={info.concurrency_scope}"
    )
