from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional

import click

from lee.orchestrator.api import pm_workflow


def _pick_resume_workflow(db_path: Path) -> Optional[str]:
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, status, current_step
            FROM workflow_instances
            WHERE status IN ('paused', 'blocked')
            ORDER BY created_at DESC
            """
        )
        candidates = cursor.fetchall()
    finally:
        conn.close()

    if not candidates:
        return None
    if len(candidates) == 1 or not click.get_text_stream("stdin").isatty():
        return str(candidates[0][0])

    click.echo("可恢复的工作流:")
    for idx, (workflow_id, status, current_step) in enumerate(candidates, start=1):
        click.echo(f"{idx}. {workflow_id} [{status}] current_step={current_step or '-'}")
    choice = click.prompt("请选择要恢复的工作流", type=int, default=1)
    if 1 <= choice <= len(candidates):
        return str(candidates[choice - 1][0])
    return None


@click.command()
@click.argument("workflow_id", required=False)
@click.option("--project-dir", default=".", help="项目目录")
def resume(workflow_id: Optional[str], project_dir: str) -> None:
    """恢复最近一次被中断或暂停的工作流。"""
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"

    if not workflow_id:
        if not db_path.exists():
            raise click.ClickException(f"数据库不存在: {db_path}")
        workflow_id = _pick_resume_workflow(db_path)
        if not workflow_id:
            raise click.ClickException("没有可恢复的 paused/blocked workflow")

    result = pm_workflow("resume", project_dir=str(project_root), workflow_id=workflow_id)
    if "error" in result:
        raise click.ClickException(str(result["error"]))
    click.echo(result.get("message", f"Workflow {workflow_id} resumed"))
