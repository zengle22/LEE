"""lee status command"""

from __future__ import annotations

from typing import Optional

import click

from lee.orchestrator.api import pm_workflow


@click.command()
@click.argument("workflow_id", required=False)
@click.option("--project-dir", default=".", help="项目目录")
def status(workflow_id: Optional[str], project_dir: str) -> None:
    """查看工作流状态"""
    result = pm_workflow("get_state", project_dir=project_dir, workflow_id=workflow_id)

    if "error" in result:
        raise click.ClickException(result["error"])

    if workflow_id:
        click.echo(f"Workflow: {result.get('workflow_id')}")
        click.echo(f"Level: {result.get('level')}")
        click.echo(f"Status: {result.get('status')}")
        click.echo(f"Current Step: {result.get('current_step')}")
        if result.get("pending_gates"):
            click.echo("Pending Gates:")
            for gate in result["pending_gates"]:
                click.echo(f"  - {gate.get('gate_id')} (step: {gate.get('step_id')})")
        if result.get("ready_steps"):
            click.echo("Ready Steps:")
            for step in result["ready_steps"]:
                click.echo(f"  - {step.get('id')} ({step.get('kind')})")
    else:
        click.echo(f"Total: {result.get('total')}")
        for wf in result.get("workflows", []):
            click.echo(f"- {wf.get('id')} [{wf.get('level')}] {wf.get('status')}")
