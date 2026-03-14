"""QA execution entry CLI."""

from __future__ import annotations

import asyncio
from pathlib import Path

import click

from lee.orchestrator.api import pm_workflow
from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.workflow_runner import derive_workflow_creation_metadata
from lee.qa import AuditLogger, ChainValidator, EntryRouter, EntrySource, ExecutionRequest
from lee.qa.workflow_launch import (
    build_test_plan_execution_params,
    render_test_plan_execution_template,
)


def _phase_line(index: int, total: int, label: str, status: str) -> str:
    icons = {"pass": "[ok]", "fail": "[x]", "info": "[..]"}
    return f"{icons.get(status, '[..]')} [{index}/{total}] {label}"


async def _run_execute(
    *,
    project_dir: Path,
    task_ref: str,
    triggered_by: str,
    entry_source: EntrySource,
) -> tuple:
    manager = ArtifactManager(project_root=project_dir, root_path=project_dir / ".artifacts")
    validator = ChainValidator(manager)
    audit_logger = AuditLogger(
        db_path=project_dir / "data" / "audit" / "audit_log.db",
        archive_path=project_dir / "data" / "audit" / "audit_log.ndjson",
    )
    router = EntryRouter(
        validator=validator.validate_chain,
        audit_sink=audit_logger.log_execution_request,
    )
    request = ExecutionRequest(
        task_ref=task_ref,
        triggered_by=triggered_by,
        entry_source=entry_source,
        metadata={"project_dir": str(project_dir)},
    )
    await audit_logger.start()
    response = await router.route(request)
    await audit_logger._queue.join()
    await audit_logger.stop()
    return response, validator


@click.command("execute")
@click.argument("task_ref")
@click.option("--triggered-by", default="human", show_default=True, help="操作用户/系统标识")
@click.option(
    "--entry-source",
    type=click.Choice([item.value for item in EntrySource], case_sensitive=False),
    default=EntrySource.CLI.value,
    show_default=True,
    help="入口来源",
)
@click.option("--project-dir", default=".", show_default=True, help="项目目录")
@click.option("--max-steps", default=50, show_default=True, help="最大执行步数")
def execute(task_ref: str, triggered_by: str, entry_source: str, project_dir: str, max_steps: int) -> None:
    """Validate and normalize the QA execution entry."""

    project_root = Path(project_dir).resolve()
    response, _ = asyncio.run(
        _run_execute(
            project_dir=project_root,
            task_ref=task_ref,
            triggered_by=triggered_by,
            entry_source=EntrySource(entry_source.upper()),
        )
    )

    click.echo(_phase_line(1, 7, "request parsed", "pass"))
    if response.success:
        click.echo(_phase_line(2, 7, "bypass check passed", "pass"))
        click.echo(_phase_line(3, 7, "chain validation passed", "pass"))
        click.echo(_phase_line(4, 7, f"audit logged: {response.audit_log_ref or 'N/A'}", "pass"))
        params = build_test_plan_execution_params(_, response.path.task_ref or task_ref)
        rendered_path = render_test_plan_execution_template(project_root, params)
        click.echo(_phase_line(5, 7, f"workflow template rendered: {rendered_path.name}", "pass"))

        workflow_data = {
            "params": params,
            "workflow_key": "qa.test-plan-execution",
            "execution_entry": {
                "task_ref": response.path.task_ref,
                "testplan_ref": response.path.testplan_ref,
                "release_ref": response.path.release_ref,
                "audit_log_ref": response.audit_log_ref,
            },
        }
        workflow_level, bootstrap_data = derive_workflow_creation_metadata(rendered_path)
        workflow_data.update(bootstrap_data)
        create_result = pm_workflow(
            "create",
            project_dir=str(project_root),
            level=workflow_level.value,
            template_id=str(rendered_path),
            data=workflow_data,
        )
        if "error" in create_result:
            raise click.ClickException(str(create_result["error"]))
        workflow_id = create_result.get("workflow_id")
        if not workflow_id:
            raise click.ClickException(f"Workflow creation failed: {create_result}")
        click.echo(_phase_line(6, 7, f"workflow created: {workflow_id}", "pass"))

        summary = pm_workflow(
            "run_until_blocked",
            project_dir=str(project_root),
            workflow_id=workflow_id,
            max_steps=max_steps,
        )
        if "error" in summary:
            raise click.ClickException(str(summary["error"]))
        summary_status = str(summary.get("status", "unknown")).lower()
        if summary_status == "failed":
            click.echo(_phase_line(7, 7, "execution advanced: failed", "fail"))
            click.echo(f"status=FAILED task_ref={response.path.task_ref}")
            click.echo(f"testplan_ref={response.path.testplan_ref} release_ref={response.path.release_ref}")
            click.echo(f"workflow_id={workflow_id}")
            raise click.ClickException(str(summary.get("blocked_at") or "workflow execution failed"))
        click.echo(_phase_line(7, 7, f"execution advanced: {summary.get('status', 'unknown')}", "pass"))
        click.echo(f"status={summary.get('status', 'unknown').upper()} task_ref={response.path.task_ref}")
        click.echo(f"testplan_ref={response.path.testplan_ref} release_ref={response.path.release_ref}")
        click.echo(f"workflow_id={workflow_id}")
        return

    click.echo(_phase_line(2, 7, "entry blocked", "fail"))
    click.echo(f"status=BLOCKED error_code={response.error_code.value if response.error_code else 'N/A'}")
    click.echo(response.error_message or "request blocked")
    raise click.exceptions.Exit(1)
