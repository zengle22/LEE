"""QA audit log CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from lee.qa import AuditLogger, AuditQuery


@click.group()
def audit():
    """QA 审计日志查询"""
    pass


@audit.command("log")
@click.option("--task-ref", default=None, help="按 TASK 过滤")
@click.option("--release-ref", default=None, help="按 RELEASE 过滤")
@click.option("--project-dir", default=".", show_default=True, help="项目目录")
def audit_log(task_ref: str | None, release_ref: str | None, project_dir: str) -> None:
    """Query QA execution audit logs."""

    logger = AuditLogger(
        db_path=Path(project_dir).resolve() / "data" / "audit" / "audit_log.db",
        archive_path=Path(project_dir).resolve() / "data" / "audit" / "audit_log.ndjson",
    )
    rows = asyncio.run(
        logger.query(
            AuditQuery(
                task_ref=task_ref,
                release_ref=release_ref,
            )
        )
    )
    if not rows:
        click.echo("no audit entries")
        return

    for row in rows:
        click.echo(
            f"{row.timestamp} {row.action.value} {row.result} "
            f"task={row.path.task_ref or '-'} release={row.path.release_ref or '-'} "
            f"by={row.triggered_by}"
        )
