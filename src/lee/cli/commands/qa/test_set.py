"""QA test-set commands"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

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
    yaml.safe_load(rendered)

    out_dir = project_dir / ".workflow" / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = out_dir / f"{template_path.stem}-{stamp}.yaml"
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


@click.group()
def test_set():
    """Test Set 管理"""
    pass


@test_set.command("create")
@click.argument("module")
@click.option("--requirement", "-r", required=True, help="需求文档路径")
@click.option("--tech-design", "-t", help="技术设计文档路径（可选）")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=20, show_default=True, help="最大执行步数")
def create(module: str, requirement: str, tech_design: str | None,
           project_dir: str, max_steps: int) -> None:
    """生产 Test Set"""
    registry = _load_registry()
    workflows = registry.get("workflows", {})
    workflow_key = "qa.test-set-production"

    if workflow_key not in workflows:
        raise click.ClickException(f"Workflow not found: {workflow_key}")

    entry = workflows[workflow_key]
    template_path = Path(entry.get("path", ""))
    if not template_path.is_absolute():
        template_path = (REGISTRY_PATH.parent.parent / template_path).resolve()
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    params: Dict[str, Any] = {
        "module": module,
        "requirement_doc": requirement,
    }
    if tech_design:
        params["tech_design"] = tech_design

    project_root = Path(project_dir).resolve()
    rendered_path = _render_workflow_template(template_path, params, project_root)

    create_result = pm_workflow(
        "create",
        project_dir=str(project_root),
        level="task",
        template_id=str(rendered_path),
        data={"params": params, "workflow_key": workflow_key},
    )

    if "error" in create_result:
        raise click.ClickException(create_result["error"])

    workflow_id = create_result.get("workflow_id")
    click.echo(f"✓ 已创建 Test Set 生产工作流: {workflow_id}")
    click.echo(f"  Module: {module}")
    click.echo(f"  Requirement: {requirement}")
    if tech_design:
        click.echo(f"  Tech Design: {tech_design}")

    summary = pm_workflow(
        "run_until_blocked",
        project_dir=str(project_root),
        workflow_id=workflow_id,
        max_steps=max_steps,
    )

    _print_execution_summary(summary)


@test_set.command("list")
@click.option("--project-dir", default=".", help="项目目录")
def list_test_sets(project_dir: str) -> None:
    """列出所有 Test Set"""
    project_root = Path(project_dir).resolve()
    test_sets_dir = project_root / "qa" / "test-sets"

    if not test_sets_dir.exists():
        click.echo("暂无 Test Set")
        return

    test_set_files = list(test_sets_dir.glob("ts-*.yaml"))
    if not test_set_files:
        click.echo("暂无 Test Set")
        return

    click.echo(f"共 {len(test_set_files)} 个 Test Set:\n")
    for f in sorted(test_set_files):
        with open(f, encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        ts_id = data.get("test_set_id", f.stem)
        module = data.get("module", "N/A")
        status = data.get("status", "N/A")
        click.echo(f"  {ts_id}: {module} [{status}]")


@test_set.command("show")
@click.argument("test_set_id")
@click.option("--project-dir", default=".", help="项目目录")
def show_test_set(test_set_id: str, project_dir: str) -> None:
    """查看 Test Set 详情"""
    project_root = Path(project_dir).resolve()

    # 尝试多种命名格式
    possible_paths = [
        project_root / "qa" / "test-sets" / f"{test_set_id}.yaml",
        project_root / "qa" / "test-sets" / f"ts-{test_set_id}.yaml",
        project_root / "qa" / "test-sets" / f"ts-{test_set_id.lower().replace('_', '-')}.yaml",
    ]

    test_set_path = None
    for p in possible_paths:
        if p.exists():
            test_set_path = p
            break

    if not test_set_path:
        raise click.ClickException(f"Test Set not found: {test_set_id}")

    with open(test_set_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))


def _print_execution_summary(summary: Dict[str, Any]) -> None:
    """打印执行摘要"""
    if "error" in summary:
        click.echo(f"\n执行出错: {summary['error']}")
        return

    status = summary.get("status", "unknown")
    steps_executed = summary.get("steps_executed", 0)
    current_step = summary.get("current_step", "N/A")
    blocked_by = summary.get("blocked_by")

    click.echo(f"\n执行状态: {status}")
    click.echo(f"已执行步骤: {steps_executed}")
    click.echo(f"当前步骤: {current_step}")

    if blocked_by:
        click.echo(f"\n⏸ 等待: {blocked_by}")
        if "gate" in str(blocked_by).lower():
            click.echo(f"批准命令: lee approve <gate-id>")
