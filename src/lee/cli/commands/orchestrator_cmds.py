"""
lee wf — 工作流底层操作命令组

提供 Orchestrator 底层操作的 CLI 入口，统一通过 API 层调用：
  lee workflow create   --level <project|department|task> --template <id>
  lee workflow list     [--project-dir .]
  lee workflow pause    <workflow_id>
  lee workflow resume   <workflow_id>
  lee workflow run-step <workflow_id> [--step <step_id>] [--max-steps 10]
  lee workflow reject   <workflow_id> <gate_id> --rejecter <name> --reason <reason>
"""

from __future__ import annotations

from typing import Optional

import click

from lee.orchestrator.api import pm_workflow


@click.group()
def wf():
    """工作流底层操作（Orchestrator）"""
    pass


# ── create ──────────────────────────────────────────────────


@wf.command()
@click.option(
    "--level",
    required=True,
    type=click.Choice(["project", "department", "task"]),
    help="工作流层级",
)
@click.option("--template", required=True, help="模板 ID")
@click.option("--parent-id", default=None, help="父工作流 ID")
@click.option("--project-dir", default=".", help="项目目录")
def create(level: str, template: str, parent_id: Optional[str], project_dir: str) -> None:
    """创建工作流实例"""
    result = pm_workflow(
        "create",
        project_dir=project_dir,
        level=level,
        template_id=template,
        parent_id=parent_id,
    )

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(f"Created {level.upper()} workflow: {result.get('workflow_id')}")
    click.echo(f"Template: {result.get('template_id')}")
    click.echo(f"Status: {result.get('status')}")
    if parent_id:
        click.echo(f"Parent: {parent_id}")


# ── list ────────────────────────────────────────────────────


@wf.command("list")
@click.option("--project-dir", default=".", help="项目目录")
def list_workflows(project_dir: str) -> None:
    """列出所有工作流"""
    result = pm_workflow("get_state", project_dir=project_dir)

    if "error" in result:
        raise click.ClickException(result["error"])

    total = result.get("total", 0)
    if total == 0:
        click.echo("No workflows found.")
        return

    click.echo(f"Total: {total}\n")
    for wf_item in result.get("workflows", []):
        parent = f" (parent: {wf_item.get('parent_id')})" if wf_item.get("parent_id") else ""
        click.echo(f"{wf_item.get('id')} - {wf_item.get('level')} - {wf_item.get('status')}{parent}")


# ── pause ───────────────────────────────────────────────────


@wf.command()
@click.argument("workflow_id")
@click.option("--project-dir", default=".", help="项目目录")
def pause(workflow_id: str, project_dir: str) -> None:
    """暂停工作流"""
    result = pm_workflow("pause", project_dir=project_dir, workflow_id=workflow_id)

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(result.get("message", f"Workflow {workflow_id} paused"))


# ── resume ──────────────────────────────────────────────────


@wf.command()
@click.argument("workflow_id")
@click.option("--project-dir", default=".", help="项目目录")
def resume(workflow_id: str, project_dir: str) -> None:
    """恢复工作流"""
    result = pm_workflow("resume", project_dir=project_dir, workflow_id=workflow_id)

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(result.get("message", f"Workflow {workflow_id} resumed"))


# ── run-step ────────────────────────────────────────────────


@wf.command("run-step")
@click.argument("workflow_id")
@click.option("--step", default=None, help="指定步骤 ID（不指定则执行下一个就绪步骤）")
@click.option("--max-steps", default=10, show_default=True, help="run_until_blocked 最大步数")
@click.option("--until-blocked/--single", default=True, show_default=True, help="执行直到阻塞 / 仅执行单步")
@click.option("--project-dir", default=".", help="项目目录")
def run_step(workflow_id: str, step: Optional[str], max_steps: int, until_blocked: bool, project_dir: str) -> None:
    """执行工作流步骤"""
    if until_blocked and not step:
        result = pm_workflow(
            "run_until_blocked",
            project_dir=project_dir,
            workflow_id=workflow_id,
            max_steps=max_steps,
        )
    else:
        result = pm_workflow(
            "run_step",
            project_dir=project_dir,
            workflow_id=workflow_id,
            step_id=step,
        )

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(f"Status: {result.get('status')}")
    if result.get("blocked_at"):
        click.echo(f"Blocked at: {result.get('blocked_at')}")
    if result.get("completed_steps") is not None:
        click.echo(f"Completed: {result.get('completed_steps')}/{result.get('total_steps')}")
    if result.get("message"):
        click.echo(f"Message: {result.get('message')}")


# ── reject ──────────────────────────────────────────────────


@wf.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--rejecter", required=True, help="拒绝人")
@click.option("--reason", required=True, help="拒绝原因")
@click.option("--project-dir", default=".", help="项目目录")
def reject(workflow_id: str, gate_id: str, rejecter: str, reason: str, project_dir: str) -> None:
    """拒绝门禁"""
    result = pm_workflow(
        "reject_gate",
        project_dir=project_dir,
        workflow_id=workflow_id,
        gate_id=gate_id,
        rejecter=rejecter,
        reason=reason,
    )

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(result.get("message", "Gate rejected"))
