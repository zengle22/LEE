from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.runners.base import StepRunnerBase
from lee.orchestrator.storage.models import StepResult, TaskExecutionStatus


def _render_template_path(path: str, params: Dict[str, Any]) -> str:
    """
    Render Jinja2-style template variables in a path string.

    Supports:
    - {{ params.xxx }} -> params['xxx']
    - {{ params.xxx | default('yyy') }} -> params['xxx'] or 'yyy'
    """
    if not isinstance(path, str):
        return str(path) if path else ""

    # Pattern to match {{ params.xxx }} or {{ params.xxx | default('yyy') }}
    template_pattern = r'\{\{\s*params\.(\w+)(?:\s*\|\s*default\(\s*[\'"]([^\'"]*)[\'"]\s*\))?\s*\}\}'

    def replace_param(match):
        param_name = match.group(1)
        default_value = match.group(2)
        value = params.get(param_name, default_value)
        return str(value) if value is not None else (default_value or '')

    rendered = re.sub(template_pattern, replace_param, path)
    return rendered


def collect_declared_output_paths(step, params: Optional[Dict[str, Any]] = None) -> List[str]:
    """
    Collect declared output file paths from step outputs.

    Args:
        step: Step object with outputs attribute
        params: Optional params dict for rendering template variables

    Returns:
        List of normalized output paths (with template variables rendered if params provided)
    """
    declared_output_files: List[str] = []
    for output in (getattr(step, "outputs", None) or []):
        if isinstance(output, dict):
            output_type = output.get("type")
            output_path = output.get("path", "")
        else:
            output_type = getattr(output, "type", None)
            output_path = getattr(output, "path", "")

        # Render template variables if params provided
        if params and isinstance(output_path, str):
            output_path = _render_template_path(output_path, params)

        normalized_path = str(output_path or "").strip()
        if output_type in {"file", "dir"} and normalized_path:
            declared_output_files.append(normalized_path)
    return declared_output_files


def build_code_executor_write_scope(
    *,
    workspace: str,
    workflow_id: str,
    step_id: str,
    configured_write_scope: Any,
    declared_output_files: Optional[List[str]] = None,
) -> List[str]:
    merged: List[str] = [
        str(Path(workspace) / ".workflow" / "workspace" / workflow_id / step_id)
    ]
    for raw_path in declared_output_files or []:
        normalized = str(raw_path or "").strip()
        if normalized and normalized not in merged:
            merged.append(normalized)
    if isinstance(configured_write_scope, list):
        for raw_path in configured_write_scope:
            normalized = str(raw_path or "").strip()
            if normalized and normalized not in merged:
                merged.append(normalized)
    return merged


def build_code_executor_io_config(
    *,
    workspace: str,
    workflow_id: str,
    step_id: str,
    step,
    configured_write_scope: Any,
    params: Optional[Dict[str, Any]] = None,
) -> dict[str, Any]:
    step_workspace = str(Path(workspace) / ".workflow" / "workspace" / workflow_id / step_id)
    declared_output_files = collect_declared_output_paths(step, params)
    return {
        "step_workspace": step_workspace,
        "declared_output_files": declared_output_files,
        "write_scope": build_code_executor_write_scope(
            workspace=workspace,
            workflow_id=workflow_id,
            step_id=step_id,
            configured_write_scope=configured_write_scope,
            declared_output_files=declared_output_files,
        ),
    }


def validate_code_executor_write_scope(
    *,
    changed_files: Optional[List[str]],
    project_root: Optional[str],
    write_scope: Any,
) -> Optional[str]:
    if not changed_files:
        return None

    base_dir = Path(project_root or ".").resolve()
    allowed_paths: List[Path] = []
    if isinstance(write_scope, list):
        for raw_path in write_scope:
            normalized = str(raw_path or "").strip()
            if not normalized:
                continue
            candidate = Path(StepRunnerBase._normalize_project_relative_path(normalized))
            resolved = (
                (base_dir / candidate).resolve()
                if not candidate.is_absolute()
                else candidate.resolve()
            )
            if resolved not in allowed_paths:
                allowed_paths.append(resolved)

    if not allowed_paths:
        return None

    blocked: List[str] = []
    for raw_path in changed_files or []:
        normalized = str(raw_path or "").strip()
        if not normalized:
            continue
        candidate = Path(StepRunnerBase._normalize_project_relative_path(normalized))
        resolved = (
            (base_dir / candidate).resolve()
            if not candidate.is_absolute()
            else candidate.resolve()
        )
        if any(path_within_scope(resolved, allowed) for allowed in allowed_paths):
            continue
        blocked.append(str(resolved))

    if not blocked:
        return None
    return (
        "Unauthorized write(s) outside step workspace / declared outputs: "
        + ", ".join(blocked)
    )


def path_within_scope(candidate: Path, allowed: Path) -> bool:
    if candidate == allowed:
        return True
    try:
        candidate.relative_to(allowed)
        return True
    except ValueError:
        return False


async def fail_code_executor_scope_violation(
    *,
    ctx,
    workflow_id: str,
    step,
    execution_id: str,
    message: str,
    output_data: Any,
    include_output: bool = False,
) -> StepResult:
    await ctx.state_machine.fail_step(workflow_id, step.id, message)
    await ctx.store.update_task_execution(
        execution_id,
        TaskExecutionStatus.FAILED,
        output_data=output_data,
        error_message=message,
        completed_at=datetime.now(),
    )
    if hasattr(ctx.event_log, "log_step_failed"):
        ctx.event_log.log_step_failed(
            step_id=step.id,
            agent_id=step.agent_id or "claude_code",
            error=message,
        )
    result = {
        "status": "failed",
        "step_id": step.id,
        "workflow_id": workflow_id,
        "message": message,
    }
    if include_output:
        result["output"] = output_data
    return StepResult(**result)
