from __future__ import annotations

import re
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
    "adr-update": "governance.adr-update",
    "src": "product.raw-to-src",
    "epic": "product.src-to-epic",
    "feat": "product.epic-to-feat",
    "delivery-prep": "product.feat-to-delivery-prep",
}


def _slugify_filename_fragment(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def _normalize_adr_id(value: str) -> str:
    raw = value.strip().upper()
    if not raw:
        raise click.ClickException("ADR ID cannot be empty.")
    if raw.isdigit():
        return f"ADR-{int(raw):03d}"
    if raw.startswith("ADR-") and raw[4:].isdigit():
        return f"ADR-{int(raw[4:]):03d}"
    return raw


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
        key: value.resolve().as_posix() if isinstance(value, Path) else value
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


def _adr_new_command(fn):
    fn = click.option("--dry-run", is_flag=True, help="只显示将要触发的 workflow alias，不实际执行。")(fn)
    fn = click.option("--skip-plan", is_flag=True, help="跳过 Plan，直接执行 workflow。")(fn)
    fn = click.option("--new-task", help="创建新 Task 作为 SSOT Root。")(fn)
    fn = click.option("--task-id", help="关联现有 Task 作为 SSOT Root。")(fn)
    fn = click.option(
        "--executor",
        type=click.Choice(EXECUTOR_CHOICES),
        help="覆盖 workflow 中的执行器类型。",
    )(fn)
    fn = click.option("--max-steps", default=10, show_default=True, help="最大执行步数。")(fn)
    fn = click.option("--project-dir", default=".", show_default=True, help="项目目录。")(fn)
    fn = click.option(
        "--spec",
        type=click.Path(exists=True, dir_okay=False, path_type=Path),
        help="ADR 创建请求 spec 文件。",
    )(fn)
    fn = click.option("--id", "adr_id", help="ADR ID，例如 ADR-031。")(fn)
    fn = click.option("--title", help="ADR 标题。")(fn)
    fn = click.option("--change-request", "-c", help="ADR 要解决的问题与决策请求。")(fn)
    fn = click.option(
        "--target-path",
        type=click.Path(dir_okay=False, path_type=Path),
        help="可选目标 ADR 路径；不提供时将按 spec/adr/<ADR-ID>__<slug>.md 生成。",
    )(fn)
    fn = click.option("--scope", help="治理范围，例如 core 或 department。")(fn)
    fn = click.option("--acceptance-brief-id", help="临时治理锚点 ID。")(fn)
    fn = click.option("--ssot-root-id", help="关联的正式 SSOT Root ID。")(fn)
    fn = click.option(
        "--human-gate-required/--no-human-gate-required",
        default=True,
        help="评审失败时是否默认进入人工 gate。",
    )(fn)
    return click.command(
        "new",
        help="通过治理流程创建 ADR。 这是 workflow-first 入口，不直接写正式 ADR 文件。",
    )(fn)


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


@click.group(help="通过 workflow-first 治理流程校验需求链。")
def chain() -> None:
    pass


@_adr_new_command
def adr_new(
    dry_run: bool,
    skip_plan: bool,
    new_task: Optional[str],
    task_id: Optional[str],
    executor: Optional[str],
    max_steps: int,
    project_dir: str,
    spec: Optional[Path],
    adr_id: Optional[str],
    title: Optional[str],
    change_request: Optional[str],
    target_path: Optional[Path],
    scope: Optional[str],
    acceptance_brief_id: Optional[str],
    ssot_root_id: Optional[str],
    human_gate_required: bool,
) -> None:
    params: Mapping[str, Any] | None = None
    if spec is None:
        missing = [
            name
            for name, value in {
                "id": adr_id,
                "title": title,
                "change-request": change_request,
            }.items()
            if not value
        ]
        if missing:
            raise click.ClickException(
                "Missing direct inputs for `lee adr new`: " + ", ".join(missing)
            )

        normalized_adr_id = _normalize_adr_id(adr_id or "")
        resolved_project_dir = Path(project_dir).resolve()
        resolved_target_path = (
            target_path.resolve()
            if target_path is not None
            else resolved_project_dir / "spec" / "adr" / f"{normalized_adr_id}__{_slugify_filename_fragment(title or '')}.md"
        )
        params_dict: dict[str, Any] = {
            "request_id": f"adr-create-{normalized_adr_id.lower()}",
            "spec_kind": "adr",
            "action": "create",
            "change_request": change_request,
            "target_path": resolved_target_path.as_posix(),
            "title": title,
            "adr_id": normalized_adr_id,
            "human_gate_required": human_gate_required,
        }
        if scope:
            params_dict["scope"] = scope
        if acceptance_brief_id:
            params_dict["acceptance_brief_id"] = acceptance_brief_id
        if ssot_root_id:
            params_dict["ssot_root_id"] = ssot_root_id
        params = params_dict

    _dispatch_workflow_command(
        "adr new",
        WORKFLOW_ALIASES["adr"],
        spec=spec,
        params=params,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
        dry_run=dry_run,
    )


@adr.command("update")
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
@click.option(
    "--spec",
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    required=True,
    help="现有 ADR 文件路径 (作为 update 的 target_path)。",
)
@click.option(
    "--change-request",
    "-c",
    required=True,
    help="描述需要进行的更改。",
)
@click.option(
    "--ssot-root-id",
    help="关联的正式 SSOT Root ID (如 SRC-059)。",
)
@click.option(
    "--acceptance-brief-id",
    help="临时治理锚点 ID。",
)
def adr_update(
    dry_run: bool,
    skip_plan: bool,
    new_task: Optional[str],
    task_id: Optional[str],
    executor: Optional[str],
    max_steps: int,
    project_dir: str,
    spec: Path,
    change_request: str,
    ssot_root_id: Optional[str],
    acceptance_brief_id: Optional[str],
) -> None:
    """通过治理流程更新现有 ADR。

    示例:

        lee adr update --spec spec/adr/ADR-024__fitness-function-zuowei-wanchengtiaojian-fangfuceng.md --change-request "更新决策以支持新的评估维度"
    """
    params = {
        "spec_kind": "adr",
        "action": "update",
        "change_request": change_request,
        "target_path": spec.resolve().as_posix(),
    }
    if ssot_root_id:
        params["ssot_root_id"] = ssot_root_id
    if acceptance_brief_id:
        params["acceptance_brief_id"] = acceptance_brief_id

    _dispatch_workflow_command(
        "adr update",
        WORKFLOW_ALIASES["adr-update"],
        spec=None,
        params=params,
        project_dir=project_dir,
        max_steps=max_steps,
        executor=executor,
        task_id=task_id,
        new_task=new_task,
        skip_plan=skip_plan,
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
chain.add_command(chain_validate)
