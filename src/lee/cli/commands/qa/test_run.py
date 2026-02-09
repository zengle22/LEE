"""QA test-run commands"""

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
def test_run():
    """Test Run 管理"""
    pass


@test_run.command("start")
@click.argument("test_plan_id")
@click.option("--build", required=True, help="构建版本")
@click.option("--commit", required=True, help="构建 commit")
@click.option("--env", default="test", help="测试环境")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=50, show_default=True, help="最大执行步数")
def start(test_plan_id: str, build: str, commit: str, env: str,
          project_dir: str, max_steps: int) -> None:
    """启动 Test Run"""
    _start_test_run(test_plan_id, build, commit, env, project_dir, max_steps)


def _start_test_run(test_plan_id: str, build: str, commit: str, env: str,
                    project_dir: str, max_steps: int) -> None:
    """启动 Test Run 的实际实现"""
    registry = _load_registry()
    workflows = registry.get("workflows", {})
    workflow_key = "qa.test-plan-execution"

    if workflow_key not in workflows:
        raise click.ClickException(f"Workflow not found: {workflow_key}")

    entry = workflows[workflow_key]
    template_path = Path(entry.get("path", ""))
    if not template_path.is_absolute():
        template_path = (REGISTRY_PATH.parent.parent / template_path).resolve()
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    params: Dict[str, Any] = {
        "test_plan_id": test_plan_id,
        "build_version": build,
        "build_commit": commit,
        "environment": env,
    }

    project_root = Path(project_dir).resolve()

    # 验证 Test Plan 存在
    plan_path = project_root / "qa" / "test-plans" / f"{test_plan_id}.yaml"
    if not plan_path.exists():
        raise click.ClickException(f"Test Plan not found: {test_plan_id}")

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
    test_run_id = f"TR-{datetime.now().strftime('%Y-%m-%d')}-{commit[:7]}"

    click.echo(f"✓ 已创建 Test Run: {test_run_id}")
    click.echo(f"  Workflow ID: {workflow_id}")
    click.echo(f"  Test Plan: {test_plan_id}")
    click.echo(f"  Build: {build} ({commit[:7]})")
    click.echo(f"  Environment: {env}")

    summary = pm_workflow(
        "run_until_blocked",
        project_dir=str(project_root),
        workflow_id=workflow_id,
        max_steps=max_steps,
    )

    _print_execution_summary(summary)


@test_run.command("status")
@click.argument("run_id", required=False)
@click.option("--project-dir", default=".", help="项目目录")
def status(run_id: str | None, project_dir: str) -> None:
    """查看 Test Run 状态"""
    project_root = Path(project_dir).resolve()
    runs_dir = project_root / "qa" / "test-runs"

    if not runs_dir.exists():
        click.echo("暂无 Test Run")
        return

    if run_id:
        # 查看特定 Run
        run_path = runs_dir / run_id / "test-run.yaml"
        if not run_path.exists():
            raise click.ClickException(f"Test Run not found: {run_id}")
        with open(run_path, encoding="utf-8") as f:
            data = yaml.safe_load(f)
        click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))
    else:
        # 列出所有 Run
        run_dirs = [d for d in runs_dir.iterdir() if d.is_dir()]
        if not run_dirs:
            click.echo("暂无 Test Run")
            return

        click.echo(f"共 {len(run_dirs)} 个 Test Run:\n")
        for d in sorted(run_dirs, reverse=True):
            run_yaml = d / "test-run.yaml"
            if run_yaml.exists():
                with open(run_yaml, encoding="utf-8") as f:
                    data = yaml.safe_load(f) or {}
                run_id = data.get("test_run_id", d.name)
                status = data.get("status", "N/A")
                plan_id = data.get("test_plan_id", "N/A")
                build = data.get("build", {}).get("version", "N/A")
                click.echo(f"  {run_id}: {status}")
                click.echo(f"    Plan: {plan_id}, Build: {build}")


@test_run.command("approve")
@click.argument("gate_id")
@click.option("--project-dir", default=".", help="项目目录")
def approve(gate_id: str, project_dir: str) -> None:
    """批准门禁"""
    project_root = Path(project_dir).resolve()

    result = pm_workflow(
        "approve_gate",
        project_dir=str(project_root),
        gate_id=gate_id,
        approver="human",
    )

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(f"✓ 已批准门禁: {gate_id}")


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
            click.echo("批准命令: lee qa test-run approve <gate-id>")
