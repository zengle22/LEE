"""Workflow launch helpers for canonical QA execution entry."""

from __future__ import annotations

import random
import string
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import yaml

from lee.cli.commands.workflow_registry import load_workflow_registry, resolve_workflow_template_path
from lee.orchestrator.core.template_engine import TemplateEngine

from .chain_validator import ChainValidator


def build_test_plan_execution_params(validator: ChainValidator, task_ref: str) -> Dict[str, Any]:
    """Build old L2 workflow params from the canonical TASK -> TESTPLAN -> RELEASE chain."""

    task = validator.resolve_artifact(task_ref)
    if task is None:
        raise ValueError(f"TASK not found: {task_ref}")
    testplan_ref = (task.properties or {}).get("parent_id")
    if not testplan_ref:
        raise ValueError(f"TASK missing parent TESTPLAN: {task_ref}")
    testplan = validator.resolve_artifact(testplan_ref)
    if testplan is None:
        raise ValueError(f"TESTPLAN not found: {testplan_ref}")
    release_ref = (testplan.properties or {}).get("parent_id")
    if not release_ref:
        raise ValueError(f"TESTPLAN missing parent RELEASE: {testplan_ref}")
    release = validator.resolve_artifact(release_ref)
    if release is None:
        raise ValueError(f"RELEASE not found: {release_ref}")

    testplan_props = dict(testplan.properties or {})
    release_props = dict(release.properties or {})
    return {
        "test_plan_id": testplan_ref,
        "build_version": str(
            release_props.get("build_version")
            or release_props.get("release_version")
            or ""
        ),
        "build_commit": str(release_props.get("build_commit") or ""),
        "environment": _resolve_environment(testplan_props),
        "base_url": str(testplan_props.get("base_url") or release_props.get("base_url") or ""),
        "target_test_sets": _resolve_target_test_sets(testplan_props),
        "release_ref": release_ref,
        "task_ref": task_ref,
    }


def render_test_plan_execution_template(project_root: Path, params: Dict[str, Any]) -> Path:
    """Render the canonical QA test-plan execution template for runtime use."""

    registry = load_workflow_registry()
    workflow_key = "qa.test-plan-execution"
    workflows = registry.get("workflows", {})
    workflow_entry = workflows.get(workflow_key)
    if workflow_entry is None:
        raise FileNotFoundError(f"Workflow not found: {workflow_key}")
    template_path = resolve_workflow_template_path(workflow_entry.get("path", ""))
    if not template_path.exists():
        raise FileNotFoundError(f"Workflow template not found: {template_path}")

    content = template_path.read_text(encoding="utf-8")
    runtime = {
        "test_run_id": _generate_test_run_id(),
    }
    rendered = TemplateEngine().render_string(
        content,
        {
            "params": params,
            "runtime": runtime,
            "current_test_set": {"test_set_id": ""},
        },
    )
    yaml.safe_load(rendered)

    rendered_dir = project_root / ".workflow" / "rendered"
    rendered_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    rendered_path = rendered_dir / f"{template_path.stem}-{stamp}.yaml"
    rendered_path.write_text(rendered, encoding="utf-8")
    return rendered_path


def _generate_test_run_id() -> str:
    suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"TR-{datetime.now().strftime('%Y-%m-%d')}-{suffix}"


def _resolve_environment(testplan_props: Dict[str, Any]) -> str:
    environment = testplan_props.get("environment")
    if isinstance(environment, str) and environment.strip():
        return environment.strip()
    matrix = testplan_props.get("environment_matrix")
    if isinstance(matrix, list):
        for item in matrix:
            if isinstance(item, str) and item.strip():
                return item.strip()
    return "test"


def _resolve_target_test_sets(testplan_props: Dict[str, Any]) -> List[str]:
    derived_from_ids = testplan_props.get("derived_from_ids", [])
    normalized: List[str] = []
    for item in derived_from_ids:
        if isinstance(item, dict):
            candidate = str(item.get("id") or "").strip()
        else:
            candidate = str(item).strip()
        if candidate.startswith("TESTSET-"):
            normalized.append(candidate)
    return normalized
