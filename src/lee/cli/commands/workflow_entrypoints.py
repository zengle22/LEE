from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Any, Mapping, Optional

import click
import yaml

from lee.cli.commands.run import run
from lee.cli.commands.workflow_registry import load_workflow_registry


EXECUTOR_CHOICES = ["llm", "qwen", "kimi", "shell", "claude_code", "codex", "langgraph"]

WORKFLOW_ALIASES = {
    "adr": "governance.adr-create",
    "src": "product.raw-to-src",
    "epic": "product.src-to-epic",
    "feat": "product.epic-to-feat",
    "delivery-prep": "product.feat-to-delivery-prep",
    "release": "product.feat-to-release",
    "delivery-plan": "product.feat-to-plan",
    "devplan": "dev.release-to-devplan",
    "testplan": "qa.release-to-testplan",
}


def _ensure_workflow_key_available(command_label: str, workflow_key: str) -> str:
    registry = load_workflow_registry()
    workflows = registry.get("workflows", {}) or {}
    if workflow_key not in workflows:
        raise click.ClickException(
            f"`lee {command_label}` requires workflow `{workflow_key}`, but it is not registered. "
            f"Use `lee run {workflow_key} ...` after the workflow is added."
        )
    return workflow_key


def _run_alias_callback(
    workflow_key: str,
    *,
    spec_value: str | None,
    project_dir: str,
    max_steps: int,
    executor: Optional[str],
    task_id: Optional[str],
    new_task: Optional[str],
    skip_plan: bool,
) -> None:
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


def _echo_alias_invocation(
    command_label: str,
    workflow_key: str,
    *,
    spec_value: str | None,
    params: Mapping[str, Any] | None,
    project_dir: str,
    executor: Optional[str],
    task_id: Optional[str],
    new_task: Optional[str],
    skip_plan: bool,
) -> None:
    click.echo(f"Workflow alias: lee {command_label} -> lee run {workflow_key}")
    if spec_value:
        click.echo(f"spec: {spec_value}")
    if params:
        for key, value in params.items():
            click.echo(f"{key}: {value}")
    click.echo(f"project_dir: {Path(project_dir).resolve()}")
    if executor:
        click.echo(f"executor: {executor}")
    if task_id:
        click.echo(f"task_id: {task_id}")
    if new_task:
        click.echo(f"new_task: {new_task}")
    click.echo(f"skip_plan: {skip_plan}")


def _write_temp_spec(params: Mapping[str, Any]) -> str:
    normalized = {
        key: str(value.resolve()) if isinstance(value, Path) else value
        for key, value in params.items()
    }
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".yaml", delete=False) as tmp:
        yaml.safe_dump(normalized, tmp, allow_unicode=True, sort_keys=False)
        return tmp.name


def _dispatch_workflow_command(
    command_label: str,
    workflow_key: str,
    *,
    spec: Optional[Path],
    params: Mapping[str, Any] | None,
    project_dir: str,
    max_steps: int,
    executor: Optional[str],
    task_id: Optional[str],
    new_task: Optional[str],
    skip_plan: bool,
    dry_run: bool,
) -> None:
    _ensure_workflow_key_available(command_label, workflow_key)

    if spec is not None and params:
        raise click.ClickException(f"`lee {command_label}` cannot use --spec together with direct input options.")

    spec_value = str(spec.resolve()) if spec else None
    if dry_run:
        _echo_alias_invocation(
            command_label,
            workflow_key,
            spec_value=spec_value,
            params=params,
            project_dir=project_dir,
            executor=executor,
            task_id=task_id,
            new_task=new_task,
            skip_plan=skip_plan,
        )
        return

    temp_spec_path: str | None = None
    try:
        if spec_value is None and params:
            temp_spec_path = _write_temp_spec(params)
            spec_value = temp_spec_path
        _run_alias_callback(
            workflow_key,
            spec_value=spec_value,
            project_dir=project_dir,
            max_steps=max_steps,
            executor=executor,
            task_id=task_id,
            new_task=new_task,
            skip_plan=skip_plan,
        )
    finally:
        if temp_spec_path:
            Path(temp_spec_path).unlink(missing_ok=True)


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
    _dispatch_workflow_command(
        f"{noun} new",
        WORKFLOW_ALIASES[noun],
        spec=spec,
        params=None,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
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


@click.group(help="通过 workflow-first 治理流程创建 SRC。")
def src() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程创建 EPIC。")
def epic() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程创建 FEAT。")
def feat() -> None:
    pass


@click.group("delivery-prep", help="通过 workflow-first 治理流程生成 Delivery Prep。")
def delivery_prep() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程生成 RELEASE draft。")
def release() -> None:
    pass


@click.group("delivery-plan", help="通过 workflow-first 治理流程生成交付计划桥接产物。")
def delivery_plan() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程生成 DEVPLAN。")
def devplan() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程生成 TESTPLAN。")
def testplan() -> None:
    pass


@click.group(help="通过 workflow-first 治理流程校验需求链。")
def chain() -> None:
    pass


@adr.command("new")
@click.option("--dry-run", is_flag=True, help="只显示将要触发的 workflow alias，不实际执行。")
def adr_new(dry_run: bool) -> None:
    _dispatch_workflow_command(
        "adr new",
        WORKFLOW_ALIASES["adr"],
        spec=None,
        params=None,
        project_dir=".",
        max_steps=10,
        executor=None,
        task_id=None,
        new_task=None,
        skip_plan=False,
        dry_run=dry_run,
    )


@_new_command("src")
def src_new(
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
        "src",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
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


@_new_command("delivery-prep")
def delivery_prep_new(
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
        "delivery-prep",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@_new_command("release")
def release_new(
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
        "release",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@_new_command("delivery-plan")
def delivery_plan_new(
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
        "delivery-plan",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@_new_command("devplan")
def devplan_new(
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
        "devplan",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@_new_command("testplan")
def testplan_new(
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
        "testplan",
        spec=spec,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@chain.command("validate")
@click.option("--dry-run", is_flag=True, help="只显示将要触发的 workflow alias，不实际执行。")
@click.option("--skip-plan", is_flag=True, help="跳过 Plan，直接执行 workflow。")
@click.option("--new-task", help="创建新 Task 作为 SSOT Root。")
@click.option("--task-id", help="关联现有 Task 作为 SSOT Root。")
@click.option(
    "--executor",
    type=click.Choice(EXECUTOR_CHOICES),
    help="覆盖 workflow 中的执行器类型。",
)
@click.option("--max-steps", default=10, show_default=True, help="最大执行步数。")
@click.option("--project-dir", default=".", show_default=True, help="项目目录。")
@click.option("--spec", type=click.Path(exists=True, dir_okay=False, path_type=Path), help="现成 spec 文件。")
@click.option(
    "--source-freeze",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="冻结后的 SRC 或 SRC freeze 文件。",
)
@click.option(
    "--epic-freeze-bundle",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="冻结后的 EPIC bundle 文件。",
)
@click.option(
    "--feat-freeze-bundle",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="冻结后的 FEAT bundle 文件。",
)
@click.option(
    "--delivery-prep-bundle",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    help="冻结后的 delivery prep bundle 文件。",
)
def chain_validate(
    dry_run: bool,
    skip_plan: bool,
    new_task: Optional[str],
    task_id: Optional[str],
    executor: Optional[str],
    max_steps: int,
    project_dir: str,
    spec: Optional[Path],
    source_freeze: Optional[Path],
    epic_freeze_bundle: Optional[Path],
    feat_freeze_bundle: Optional[Path],
    delivery_prep_bundle: Optional[Path],
) -> None:
    params = {
        "source_freeze": source_freeze,
        "epic_freeze_bundle": epic_freeze_bundle,
        "feat_freeze_bundle": feat_freeze_bundle,
        "delivery_prep_bundle": delivery_prep_bundle,
    }
    direct_params = {key: value for key, value in params.items() if value is not None}
    if spec is None and len(direct_params) != 4:
        missing = [key for key, value in params.items() if value is None]
        raise click.ClickException(
            "Missing direct inputs for `lee chain validate`: " + ", ".join(missing)
        )

    _dispatch_workflow_command(
        "chain validate",
        "product.requirement-chain-validation",
        spec=spec,
        params=direct_params or None,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


adr.add_command(adr_new)
src.add_command(src_new)
epic.add_command(epic_new)
feat.add_command(feat_new)
delivery_prep.add_command(delivery_prep_new)
release.add_command(release_new)
delivery_plan.add_command(delivery_plan_new)
devplan.add_command(devplan_new)
testplan.add_command(testplan_new)
chain.add_command(chain_validate)
