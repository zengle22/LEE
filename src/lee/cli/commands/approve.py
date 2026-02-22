"""lee approve command"""

from __future__ import annotations

import click
import sqlite3
from pathlib import Path

from lee.orchestrator.api import pm_workflow


def _resolve_gate_ref(project_dir: str, workflow_id: str, gate_ref: str) -> str:
    """兼容传入 step_id，自动映射到 pending gate_id。"""
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return gate_ref

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT gate_id
            FROM gate_approvals
            WHERE workflow_id = ? AND status = 'pending' AND gate_id = ?
            """,
            (workflow_id, gate_ref),
        )
        row = cursor.fetchone()
        if row:
            return gate_ref

        cursor.execute(
            """
            SELECT gate_id
            FROM gate_approvals
            WHERE workflow_id = ? AND status = 'pending' AND step_id = ?
            """,
            (workflow_id, gate_ref),
        )
        rows = cursor.fetchall()
        if len(rows) == 1:
            mapped = rows[0][0]
            click.echo(f"检测到步骤 ID，自动映射: {gate_ref} -> {mapped}")
            return mapped
        return gate_ref
    finally:
        conn.close()


@click.command()
@click.argument("workflow_id")
@click.argument("gate_ref")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="审批意见")
@click.option("--project-dir", default=".", help="项目目录")
def approve(workflow_id: str, gate_ref: str, approver: str, comments: str, project_dir: str) -> None:
    """审批门禁（支持 gate_id 或 step_id）"""
    gate_id = _resolve_gate_ref(project_dir, workflow_id, gate_ref)
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
