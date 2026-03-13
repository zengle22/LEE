from __future__ import annotations

from pathlib import Path
from typing import Optional

import click

from lee.cli.commands.run import run
from lee.cli.commands.workflow_registry import load_workflow_registry


EXECUTOR_CHOICES = ["llm", "qwen", "kimi", "shell", "claude_code", "codex", "langgraph"]

WORKFLOW_ALIASES = {
    "adr": "governance.adr-create",
    "epic": "product.src-to-epic",
    "feat": "product.epic-to-feat",
}


def _ensure_workflow_alias_available(noun: str) -> str:
    workflow_key = WORKFLOW_ALIASES[noun]
    registry = load_workflow_registry()
    workflows = registry.get("workflows", {}) or {}
    if workflow_key not in workflows:
        raise click.ClickException(
            f"`lee {noun} new` requires workflow `{workflow_key}`, but it is not registered. "
            f"Use `lee run {workflow_key} ...` after the create workflow is added."
        )
    return workflow_key


def _dispatch_workflow_alias(
    noun: str,
    *,
    spec: Optional[Path],
    project_dir: str,
    max_steps: int,
    executor: Optional[str],
    task_id: Optional[str],
    new_task: Optional[str],
    skip_plan: bool,
    dry_run: bool,
) -> None:
    workflow_key = _ensure_workflow_alias_available(noun)
    spec_value = str(spec.resolve()) if spec else None
    if dry_run:
        click.echo(f"Workflow alias: lee {noun} new -> lee run {workflow_key}")
        if spec_value:
            click.echo(f"spec: {spec_value}")
        click.echo(f"project_dir: {Path(project_dir).resolve()}")
        if executor:
            click.echo(f"executor: {executor}")
        if task_id:
            click.echo(f"task_id: {task_id}")
        if new_task:
            click.echo(f"new_task: {new_task}")
        click.echo(f"skip_plan: {skip_plan}")
        return

    run.callback(
        workflow_key=workflow_key,
        spec=spec_value,
        env=None,
        version=None,
        branch=None,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        plan_only=False,
        skip_plan=skip_plan,
        plan_mode="suggest",
        instance=None,
        task_id=task_id,
        new_task=new_task,
    )


def _new_command(noun: str):
    def decorator(fn):
        fn = click.option(
            "--dry-run",
            is_flag=True,
            help="只显示将要触发的 workflow alias，不实际执行。",
        )(fn)
        fn = click.option("--skip-plan", is_flag=True, help="跳过 Plan，直接执行 workflow。")(fn)
        fn = click.option("--new-task", help="创建新 Task 作为 SSOT Root。")(fn)
        fn = click.option("--task-id", help="关联现有 Task 作为 SSOT Root。")(fn)
        fn = click.option(
            "--executor",
            type=click.Choice(EXECUTOR_CHOICES),
            help="覆盖 workflow 中的执行器类型。",
        )(fn)
        fn = click.option("--max-steps", default=10, show_default=True, help="最大执行步数。")(fn)
        fn = click.option(
            "--project-dir",
            default=".",
            show_default=True,
            help="项目目录。",
        )(fn)
        fn = click.option(
            "--spec",
            type=click.Path(exists=True, dir_okay=False, path_type=Path),
            help="作为 workflow 输入的 spec 文件。",
        )(fn)
        return click.command(
            "new",
            help=(
                f"通过治理流程创建 {noun.upper()}。"
                " 这是 workflow-first 入口，不直接写正式 SSOT 文件。"
            ),
        )(fn)

    return decorator


@click.group(help="通过 workflow-first 治理流程创建 ADR。")
def adr() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程创建 EPIC。")
def epic() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程创建 FEAT。")
def feat() -> None:
    pass


@adr.command("new")
@click.option("--dry-run", is_flag=True, help="只显示将要触发的 workflow alias，不实际执行。")
def adr_new(dry_run: bool) -> None:
    _dispatch_workflow_alias(
        "adr",
        spec=None,
        project_dir=".",
        max_steps=10,
        executor=None,
        task_id=None,
        new_task=None,
        skip_plan=False,
        dry_run=dry_run,
    )


@_new_command("epic")
def epic_new(
    spec: Optional[Path],
    project_dir: str,
    max_steps: int,
    executor: Optional[str],
    task_id: Optional[str],
    new_task: Optional[str],
    skip_plan: bool,
    dry_run: bool,
) -> None:
    _dispatch_workflow_alias(
        "epic",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@_new_command("feat")
def feat_new(
    spec: Optional[Path],
    project_dir: str,
    max_steps: int,
    executor: Optional[str],
    task_id: Optional[str],
    new_task: Optional[str],
    skip_plan: bool,
    dry_run: bool,
) -> None:
    _dispatch_workflow_alias(
        "feat",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


adr.add_command(adr_new)
epic.add_command(epic_new)
feat.add_command(feat_new)
