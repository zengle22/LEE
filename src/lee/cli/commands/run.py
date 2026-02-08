"""lee run command"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

import click
import yaml

from lee.orchestrator.api import pm_workflow
from lee.orchestrator.core.template_engine import TemplateEngine


REGISTRY_PATH = Path("config/workflow-registry.yaml")


def _load_registry() -> Dict[str, Any]:
    if not REGISTRY_PATH.exists():
        raise FileNotFoundError(f"Workflow registry not found: {REGISTRY_PATH}")
    with open(REGISTRY_PATH, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _render_workflow_template(template_path: Path, params: Dict[str, Any], project_dir: Path) -> Path:
    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    engine = TemplateEngine()
    rendered = engine.render_string(content, {"params": params})

    # Validate YAML is parseable
    yaml.safe_load(rendered)

    out_dir = project_dir / ".workflow" / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = out_dir / f"{template_path.stem}-{stamp}.yaml"
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


@click.command()
@click.argument("workflow_key")
@click.option("--spec", help="Spec 文件路径")
@click.option("--env", help="目标环境")
@click.option("--version", help="版本/commit")
@click.option("--branch", help="目标分支")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=10, show_default=True, help="最大执行步数")
def run(workflow_key: str, spec: str | None, env: str | None, version: str | None,
        branch: str | None, project_dir: str, max_steps: int) -> None:
    """运行指定工作流"""
    registry = _load_registry()
    workflows = registry.get("workflows", {})
    if workflow_key not in workflows:
        raise click.ClickException(f"Unknown workflow: {workflow_key}")

    entry = workflows[workflow_key]
    template_path = Path(entry.get("path", ""))
    if not template_path.is_absolute():
        template_path = (REGISTRY_PATH.parent.parent / template_path).resolve()
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    params: Dict[str, Any] = {}
    if spec:
        params["spec"] = spec
    if env:
        params["env"] = env
    if version:
        params["version"] = version
    if branch:
        params["branch"] = branch

    required = entry.get("required_params", []) or []
    missing = [p for p in required if p not in params]
    if missing:
        raise click.ClickException(f"Missing required params: {', '.join(missing)}")

    project_root = Path(project_dir).resolve()
    rendered_path = _render_workflow_template(template_path, params, project_root)

    # Create workflow instance (L3 task)
    create_result = pm_workflow(
        "create",
        project_dir=str(project_root),
        level="task",
        template_id=str(rendered_path),
        data={"params": params, "workflow_key": workflow_key},
    )

    workflow_id = create_result.get("workflow_id")
    click.echo(f"Created workflow: {workflow_id}")
    click.echo(f"Template: {rendered_path}")

    # Run until blocked
    summary = pm_workflow(
        "run_until_blocked",
        project_dir=str(project_root),
        workflow_id=workflow_id,
        max_steps=max_steps,
    )

    click.echo(f"Status: {summary.get('status')}")
    if summary.get("blocked_at"):
        click.echo(f"Blocked at: {summary.get('blocked_at')}")
