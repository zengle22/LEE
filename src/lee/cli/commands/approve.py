"""lee approve command"""

from __future__ import annotations

import click

from lee.orchestrator.api import pm_workflow


@click.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="审批意见")
@click.option("--project-dir", default=".", help="项目目录")
def approve(workflow_id: str, gate_id: str, approver: str, comments: str, project_dir: str) -> None:
    """审批门禁"""
    result = pm_workflow(
        "approve_gate",
        project_dir=project_dir,
        workflow_id=workflow_id,
        gate_id=gate_id,
        approver=approver,
        comments=comments,
    )

    if "error" in result:
        raise click.ClickException(result["error"])

    click.echo(result.get("message", "Gate approved"))
