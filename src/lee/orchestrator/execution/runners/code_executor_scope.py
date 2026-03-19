from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

from lee.orchestrator.execution.runners.base import StepRunnerBase
from lee.orchestrator.storage.models import StepResult, TaskExecutionStatus


def collect_declared_output_paths(step, project_root: Optional[str] = None) -> List[str]:
    """
    Collect declared output paths from step outputs.

    Handles three types of outputs:
    1. Dict with type="file"/"dir" and path: returns the explicit path
    2. Dict with type="symbol" or no type: symbolic output, allows project root
    3. String (symbolic name): symbolic output, allows project root

    For symbolic outputs, project root is added to allow writes to standard locations.
    """
    declared_output_files: List[str] = []
    has_symbolic_output = False

    for output in (getattr(step, "outputs", None) or []):
        if isinstance(output, dict):
            output_type = output.get("type")
            output_path = output.get("path", "")
            # Symbolic output (type="symbol" or no type with symbol name)
            if output_type == "symbol" or (output_type is None and "symbol" in output):
                has_symbolic_output = True
                continue
        else:
            # Check if it's a SimpleNamespace or similar object
            output_type = getattr(output, "type", None)
            output_path = getattr(output, "path", "")
            # Check for symbolic output
            if output_type == "symbol":
                has_symbolic_output = True
                continue
            # String output is a symbolic name
            if isinstance(output, str):
                has_symbolic_output = True
                continue

        normalized_path = str(output_path or "").strip()
        if output_type in {"file", "dir"} and normalized_path:
            declared_output_files.append(normalized_path)

    # If there are symbolic outputs, add project root to allow standard location writes
    if has_symbolic_output and project_root:
        declared_output_files.append(project_root)

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
    project_root: Optional[str] = None,
) -> dict[str, Any]:
    step_workspace = str(Path(workspace) / ".workflow" / "workspace" / workflow_id / step_id)
    declared_output_files = collect_declared_output_paths(step, params, project_root)
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
            # FIX: Check if original path is absolute before normalization
            # _normalize_project_relative_path strips leading / which breaks absolute path detection
            original_path = Path(normalized)
            if original_path.is_absolute():
                try:
                    # If already under base_dir, use it directly
                    original_path.relative_to(base_dir)
                    resolved = original_path.resolve()
                except ValueError:
                    # Absolute but not under base_dir, use as-is
                    resolved = original_path.resolve()
            else:
                # Relative path: normalize and join with base_dir
                candidate = Path(StepRunnerBase._normalize_project_relative_path(normalized))
                resolved = (base_dir / candidate).resolve()
            if resolved not in allowed_paths:
                allowed_paths.append(resolved)

    if not allowed_paths:
        return None

    blocked: List[str] = []
    for raw_path in changed_files or []:
        normalized = str(raw_path or "").strip()
        if not normalized:
            continue
        # FIX: Check if original path is absolute before normalization
        # _normalize_project_relative_path strips leading / which breaks absolute path detection
        original_path = Path(normalized)
        if original_path.is_absolute():
            try:
                # If already under base_dir, use it directly
                original_path.relative_to(base_dir)
                resolved = original_path.resolve()
            except ValueError:
                # Absolute but not under base_dir, use as-is
                resolved = original_path.resolve()
        else:
            # Relative path: normalize and join with base_dir
            candidate = Path(StepRunnerBase._normalize_project_relative_path(normalized))
            resolved = (base_dir / candidate).resolve()
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
