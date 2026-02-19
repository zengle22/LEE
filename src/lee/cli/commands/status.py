"""lee status command"""

from __future__ import annotations

import sqlite3
import threading
from pathlib import Path
from typing import Optional

import click

from lee.orchestrator.api import pm_workflow


@click.command()
@click.argument("workflow_id", required=False)
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--timeout", default=10, show_default=True, help="状态查询超时（秒）")
def status(workflow_id: Optional[str], project_dir: str, timeout: int) -> None:
    """查看工作流状态"""
    result_box = {"result": None, "error": None}

    def _worker() -> None:
        try:
            result_box["result"] = pm_workflow(
                "get_state",
                project_dir=project_dir,
                workflow_id=workflow_id,
            )
        except Exception as e:
            result_box["error"] = e

    worker = threading.Thread(target=_worker, daemon=True)
    worker.start()
    worker.join(timeout=max(timeout, 1))

    if worker.is_alive():
        raise click.ClickException(
            f"Status query timed out after {max(timeout, 1)}s "
            f"(workflow_id={workflow_id or 'ALL'})"
        )

    if result_box["error"] is not None:
        raise click.ClickException(str(result_box["error"]))

    result = result_box["result"] or {}

    if "error" in result:
        raise click.ClickException(result["error"])

    if workflow_id:
        click.echo(f"Workflow: {result.get('workflow_id')}")
        click.echo(f"Level: {result.get('level')}")
        click.echo(f"Status: {result.get('status')}")
        click.echo(f"Current Step: {result.get('current_step')}")

        # 显示失败原因
        if result.get('status') in ['failed', 'paused']:
            # 从数据库查询失败原因
            try:
                db_path = Path(project_dir) / ".workflow" / "orchestrator.db"
                if db_path.exists():
                    conn = sqlite3.connect(str(db_path))
                    cursor = conn.cursor()

                    # 查询失败的步骤及其错误
                    cursor.execute(
                        """SELECT step_name, error_message, status
                           FROM task_executions
                           WHERE workflow_id = ? AND status = 'failed'
                           ORDER BY started_at DESC""",
                        (workflow_id,)
                    )
                    failed_steps = cursor.fetchall()

                    if failed_steps:
                        click.echo("\n❌ 失败原因:")
                        for step_name, error, status in failed_steps:
                            click.echo(f"  - {step_name}: {error}")

                    conn.close()
            except Exception:
                pass

        if result.get("pending_gates"):
            click.echo("\nPending Gates:")
            for gate in result["pending_gates"]:
                click.echo(f"  - {gate.get('gate_id')} (step: {gate.get('step_id')})")

        if result.get("ready_steps"):
            click.echo("\nReady Steps:")
            for step in result["ready_steps"]:
                click.echo(f"  - {step.get('id')} ({step.get('kind')})")
    else:
        click.echo(f"Total: {result.get('total')}")
        for wf in result.get("workflows", []):
            click.echo(f"- {wf.get('id')} [{wf.get('level')}] {wf.get('status')}")
