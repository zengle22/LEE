"""lee run command"""

from __future__ import annotations

import json
import os
import sqlite3
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

import click
import yaml

from lee.cli.commands.workflow_registry import load_workflow_registry, resolve_workflow_template_path
from lee.orchestrator.api import pm_workflow
from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.execution.artifacts import ArtifactManager, ManifestManager
from lee.orchestrator.execution.artifacts.types import ArtifactType, GovernanceKind

try:
    import fcntl
except ImportError:  # pragma: no cover
    fcntl = None

TERMINAL_WORKFLOW_STATUSES = {"completed", "failed", "superseded"}


def _load_registry() -> Dict[str, Any]:
    return load_workflow_registry()


def _load_spec_option_as_params(spec_path: str) -> Dict[str, Any]:
    """Load --spec file as params payload when the workflow opts into it."""
    path = Path(spec_path).resolve()
    if not path.exists():
        raise click.ClickException(f"Spec file not found: {path}")

    try:
        if path.suffix.lower() == ".json":
            return json.loads(path.read_text(encoding="utf-8"))
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception as exc:
        raise click.ClickException(f"Failed to parse spec file '{path}': {exc}") from exc


def _load_spec_option(spec_path: str) -> Dict[str, Any]:
    """
    Resolve --spec into workflow params.

    Default behavior:
    - object-like YAML/JSON -> merge as params
    - everything else -> keep as {"spec": "<absolute-path>"}
    """
    path = Path(spec_path).resolve()
    if not path.exists():
        raise click.ClickException(f"Spec file not found: {path}")

    if path.suffix.lower() not in {".json", ".yaml", ".yml"}:
        return {"spec": str(path)}

    loaded = _load_spec_option_as_params(str(path))
    if isinstance(loaded, dict):
        return loaded
    return {"spec": str(path)}


def _render_workflow_template(template_path: Path, params: Dict[str, Any], project_dir: Path) -> Path:
    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    now = datetime.now()
    engine = TemplateEngine()
    dirs_context = _load_directory_context(project_dir)
    rendered = engine.render_string(
        content,
        {
            "params": params,
            **params,
            "date": now.strftime("%Y-%m-%d"),
            "timestamp": now.strftime("%Y%m%d%H%M%S"),
            "now": now,
            **dirs_context,
        },
    )

    # Validate YAML is parseable
    yaml.safe_load(rendered)

    out_dir = project_dir / ".workflow" / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = now.strftime("%Y%m%d%H%M%S")
    out_path = out_dir / f"{template_path.stem}-{stamp}.yaml"
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


def _load_directory_context(project_dir: Path) -> Dict[str, Any]:
    dirs_yaml_path = project_dir / ".project" / "dirs.yaml"
    defaults: Dict[str, Any] = {
        "specs_dir": "spec",
        "qa_specs_dir": "spec/qa",
        "src_dir": "src",
        "docs_dir": "docs",
        "knowledge_dir": "knowledge",
        "tests_dir": "tests",
        "artifacts_dir": ".artifacts",
        "config_dir": ".project",
        "workflow_dir": ".workflow",
        "tools_dir": "tools",
        "deploy_dir": "deploy",
        "legacy_dir": "legacy",
    }
    if not dirs_yaml_path.exists():
        return defaults

    try:
        data = yaml.safe_load(dirs_yaml_path.read_text(encoding="utf-8")) or {}
    except Exception:
        return defaults

    directories = data.get("directories", {}) or {}
    context = dict(defaults)
    if "specs_dir" in directories:
        context["specs_dir"] = directories["specs_dir"].get("path", context["specs_dir"])
    elif "spec_dir" in directories:
        context["specs_dir"] = directories["spec_dir"].get("path", context["specs_dir"])

    if "qa_specs_dir" in directories:
        context["qa_specs_dir"] = directories["qa_specs_dir"].get("path", context["qa_specs_dir"])

    for key in [
        "src_dir",
        "docs_dir",
        "knowledge_dir",
        "tests_dir",
        "artifacts_dir",
        "config_dir",
        "workflow_dir",
        "tools_dir",
        "deploy_dir",
        "legacy_dir",
    ]:
        if key in directories:
            context[key] = directories[key].get("path", context[key])

    return context


def _load_template_param_defaults(template_path: Path) -> Dict[str, Any]:
    """读取 workflow 模板中 params.*.default。"""
    try:
        with open(template_path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except Exception:
        return {}
    defaults: Dict[str, Any] = {}
    params = data.get("params") or {}
    if not isinstance(params, dict):
        return defaults
    for key, spec in params.items():
        if isinstance(spec, dict) and "default" in spec:
            defaults[key] = spec.get("default")
    return defaults


def _list_existing_same_workflows(project_root: Path, workflow_key: str) -> List[Dict[str, Any]]:
    """
    查询同项目目录下、同 workflow_key 的旧流程（running/paused/pending）。
    """
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return []

    rows: List[Dict[str, Any]] = []
    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, status, current_step, created_at, data
            FROM workflow_instances
            WHERE status IN ('running', 'paused', 'pending')
            ORDER BY created_at DESC
            """
        )
        for workflow_id, status, current_step, created_at, raw_data in cursor.fetchall():
            try:
                data = json.loads(raw_data or "{}")
            except Exception:
                data = {}
            if data.get("workflow_key") != workflow_key:
                continue
            rows.append(
                {
                    "id": workflow_id,
                    "status": status,
                    "current_step": current_step,
                    "created_at": created_at,
                }
            )
    finally:
        conn.close()

    return rows


def _run_until_blocked_with_interrupt_guard(
    project_root: Path,
    workflow_id: str,
    max_steps: int,
) -> Dict[str, Any]:
    """
    执行工作流并在 Ctrl+C 时自动 pause，避免留下“假 running”状态。
    """
    try:
        return pm_workflow(
            "run_until_blocked",
            project_dir=str(project_root),
            workflow_id=workflow_id,
            max_steps=max_steps,
        )
    except KeyboardInterrupt:
        try:
            pm_workflow(
                "pause",
                project_dir=str(project_root),
                workflow_id=workflow_id,
            )
        except Exception:
            pass
        raise click.ClickException(
            f"Workflow interrupted and paused: {workflow_id}. "
            f"Use 'lee workflow resume {workflow_id} --project-dir {project_root}' to continue."
        )


def _print_summary(project_root: Path, workflow_id: str, summary: Dict[str, Any]) -> None:
    if not isinstance(summary, dict):
        raise click.ClickException(f"Invalid workflow summary: {summary}")

    if "error" in summary and "status" not in summary:
        click.echo("\n最终状态: failed")
        raise click.ClickException(str(summary.get("error")))

    status = summary.get("status")
    if not status:
        click.echo("\n最终状态: unknown")
        raise click.ClickException(f"Missing status in summary: {summary}")

    click.echo(f"\n最终状态: {status}")

    if summary.get("blocked_at"):
        click.echo(f"阻塞在: {summary.get('blocked_at')}")
        click.echo("\n💡 提示: 使用以下命令查看详情或审核门禁")
        click.echo(f"   lee status {workflow_id}")
        click.echo(f"   lee approve {workflow_id} <gate_id> --approver <your-name>")

    completed_count = summary.get("completed_steps", 0)
    if completed_count:
        click.echo(f"\n📊 完成: {completed_count} 个步骤")
        click.echo("\n已完成的步骤:")

        db_path = project_root / ".workflow" / "orchestrator.db"
        if db_path.exists():
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()
                cursor.execute(
                    """SELECT step_name
                       FROM task_executions
                       WHERE workflow_id = ? AND status = 'completed'
                       ORDER BY started_at""",
                    (workflow_id,),
                )
                for (step_name,) in cursor.fetchall():
                    click.echo(f"  ✅ {step_name}")
                conn.close()
            except Exception:
                pass


def _refresh_summary_from_store(
    project_root: Path,
    workflow_id: str,
    summary: Dict[str, Any],
    *,
    poll_attempts: int = 5,
    poll_interval_seconds: float = 0.2,
) -> Dict[str, Any]:
    """Refresh summary status from persisted workflow state before printing."""
    refreshed = dict(summary)
    if str(refreshed.get("status") or "").lower() != "running":
        return refreshed

    latest_snapshot = None
    for _ in range(max(poll_attempts, 1)):
        snapshot = _get_progress_snapshot(project_root, workflow_id)
        if not snapshot:
            break
        latest_snapshot = snapshot
        snapshot_status = str(snapshot.get("status") or "").lower()
        if snapshot_status in TERMINAL_WORKFLOW_STATUSES:
            refreshed["status"] = snapshot_status
            refreshed["blocked_at"] = None
            refreshed["completed_steps"] = max(
                int(refreshed.get("completed_steps") or 0),
                int(snapshot.get("completed") or 0),
            )
            return refreshed
        time.sleep(max(poll_interval_seconds, 0.05))

    if latest_snapshot:
        refreshed["completed_steps"] = max(
            int(refreshed.get("completed_steps") or 0),
            int(latest_snapshot.get("completed") or 0),
        )
    return refreshed


def _select_existing_workflow_action(existing: List[Dict[str, Any]]) -> tuple[str, str]:
    """
    让用户在“继续旧流程”与“结束旧流程后开新流程”之间做选择。
    返回 (action, selected_workflow_id)
    """
    click.echo("\n检测到同目录下存在相同 workflow_key 的旧流程:")
    for item in existing:
        click.echo(
            f"  - {item['id']} [{item['status']}] "
            f"current_step={item.get('current_step') or '-'} "
            f"created_at={item.get('created_at') or '-'}"
        )

    if click.get_text_stream("stdin").isatty():
        action = click.prompt(
            "\n请选择操作",
            type=click.Choice(["continue", "restart"], case_sensitive=False),
            default="continue",
            show_choices=True,
        ).lower()
    else:
        # 非交互场景无法提问，默认 continue 防止重复创建。
        action = "continue"
        click.echo("非交互模式：默认继续旧流程（continue）。")

    selected_workflow_id = existing[0]["id"]
    if action == "continue" and len(existing) > 1 and click.get_text_stream("stdin").isatty():
        selected_workflow_id = click.prompt(
            "选择要继续的 workflow_id",
            type=click.Choice([item["id"] for item in existing], case_sensitive=True),
            default=selected_workflow_id,
            show_choices=False,
        )
    return action, selected_workflow_id


def _get_progress_snapshot(project_root: Path, workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    从 SQLite 读取 workflow 进度快照。
    """
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, current_step FROM workflow_instances WHERE id = ?",
            (workflow_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        status, current_step = row
        cursor.execute(
            """
            SELECT status, COUNT(*)
            FROM task_executions
            WHERE workflow_id = ?
            GROUP BY status
            """,
            (workflow_id,),
        )
        grouped = {k: v for k, v in cursor.fetchall()}
        return {
            "status": status,
            "current_step": current_step,
            "completed": grouped.get("completed", 0),
            "running": grouped.get("running", 0),
            "failed": grouped.get("failed", 0),
        }
    finally:
        conn.close()


def _start_progress_monitor(
    project_root: Path,
    workflow_id: str,
    interval_seconds: float = 2.0,
) -> tuple[threading.Event, threading.Thread]:
    """
    启动后台进度监控线程，在 `lee run` 期间实时打印进度。
    """
    stop_event = threading.Event()

    def _monitor() -> None:
        last_signature: Optional[tuple[Any, ...]] = None
        last_emit_at = 0.0
        heartbeat_seconds = 15.0
        while not stop_event.wait(interval_seconds):
            snapshot = _get_progress_snapshot(project_root, workflow_id)
            if snapshot is None:
                continue
            now = time.monotonic()
            signature = (
                snapshot["status"],
                snapshot["current_step"],
                snapshot["completed"],
                snapshot["running"],
                snapshot["failed"],
            )
            should_emit = signature != last_signature
            is_heartbeat = False
            if not should_emit and snapshot["status"] == "running":
                should_emit = (now - last_emit_at) >= heartbeat_seconds
                is_heartbeat = should_emit
            if not should_emit:
                continue
            last_signature = signature
            last_emit_at = now
            suffix = " (heartbeat)" if is_heartbeat else ""
            click.echo(
                "进度: "
                f"status={snapshot['status']} "
                f"current_step={snapshot.get('current_step') or '-'} "
                f"completed={snapshot['completed']} "
                f"running={snapshot['running']} "
                f"failed={snapshot['failed']}{suffix}"
            )

    thread = threading.Thread(target=_monitor, daemon=True, name=f"lee-progress-{workflow_id}")
    thread.start()
    return stop_event, thread


def _get_gate_wait_snapshot(project_root: Path, workflow_id: str) -> Optional[Dict[str, Any]]:
    """
    读取当前 workflow 的 gate 等待快照。

    返回:
      {
        "status": "...",
        "current_step": "...",
        "pending_gates": [{"gate_id": "...", "step_id": "..."}]
      }
    """
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return None

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status, current_step FROM workflow_instances WHERE id = ?",
            (workflow_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return None

        status, current_step = row
        cursor.execute(
            """
            SELECT gate_id, step_id
            FROM gate_approvals
            WHERE workflow_id = ? AND status = 'pending'
            ORDER BY created_at
            """,
            (workflow_id,),
        )
        pending_gates = [
            {"gate_id": gate_id, "step_id": step_id}
            for gate_id, step_id in cursor.fetchall()
        ]
        return {
            "status": status,
            "current_step": current_step,
            "pending_gates": pending_gates,
        }
    finally:
        conn.close()


def _wait_for_gate_resolution(
    project_root: Path,
    workflow_id: str,
    interval_seconds: float = 2.0,
    heartbeat_seconds: float = 15.0,
) -> Dict[str, Any]:
    """
    在 workflow 被 gate 阻塞时等待人工决策（approve/reject/revise）。

    该函数不做审批动作，只等待状态变化，适配“另一个终端执行 gates approve/reject”场景。
    """
    last_signature: Optional[tuple[Any, ...]] = None
    last_emit_at = 0.0

    while True:
        snapshot = _get_gate_wait_snapshot(project_root, workflow_id) or {
            "status": "unknown",
            "current_step": None,
            "pending_gates": [],
        }

        status = str(snapshot.get("status") or "unknown").lower()
        pending = snapshot.get("pending_gates") or []
        gate_ids = tuple(g.get("gate_id") for g in pending)
        signature = (status, gate_ids)
        now = time.monotonic()

        should_emit = signature != last_signature
        is_heartbeat = False
        if not should_emit and pending:
            should_emit = (now - last_emit_at) >= heartbeat_seconds
            is_heartbeat = should_emit
        if should_emit:
            last_signature = signature
            last_emit_at = now
            suffix = " (heartbeat)" if is_heartbeat else ""
            click.echo(
                f"等待门禁决策: status={status} pending={len(pending)} "
                f"gates={', '.join(gate_ids) if gate_ids else '-'}{suffix}"
            )

        if status in TERMINAL_WORKFLOW_STATUSES:
            return snapshot
        if not pending:
            return snapshot

        time.sleep(max(interval_seconds, 0.2))


def _run_until_settled_with_gates(
    project_root: Path,
    workflow_id: str,
    max_steps: int,
) -> Dict[str, Any]:
    """
    主执行循环：
    - 正常执行 run_until_blocked
    - 如果因 human gate 阻塞，则等待外部审批/拒绝
    - 决策完成后继续执行，直到 completed/failed/superseded 或其他可返回状态
    """
    while True:
        summary = _run_until_blocked_with_interrupt_guard(project_root, workflow_id, max_steps)
        if str(summary.get("status")) != "blocked":
            return summary

        wait_snapshot = _get_gate_wait_snapshot(project_root, workflow_id)
        pending = (wait_snapshot or {}).get("pending_gates") or []
        if not pending:
            return summary

        click.echo("\n⏸️ 检测到人工门禁，等待审批/拒绝后自动继续...")
        for gate in pending:
            click.echo(f"  - {gate.get('gate_id')} (step={gate.get('step_id')})")
        click.echo(
            "可在另一个终端执行: "
            f"lee gates decide {workflow_id} --project-dir {project_root}"
        )

        resolved = _wait_for_gate_resolution(project_root, workflow_id)
        resolved_status = str(resolved.get("status") or "").lower()
        resolved_pending = resolved.get("pending_gates") or []

        if resolved_status in TERMINAL_WORKFLOW_STATUSES:
            return {
                "status": resolved_status,
                "blocked_at": None,
                "completed_steps": summary.get("completed_steps", 0),
            }
        if resolved_pending:
            return summary

        if resolved_status == "paused":
            resume_result = pm_workflow(
                "resume",
                project_dir=str(project_root),
                workflow_id=workflow_id,
            )
            if "error" in resume_result:
                click.echo(
                    f"门禁已处理，但恢复 workflow 失败: {resume_result.get('error')}"
                )
                return summary

        click.echo("✅ 门禁已决策，继续执行后续步骤...")


def _acquire_project_run_lock(project_root: Path):
    """
    单项目并发锁：同一 project_dir 只允许一个 `lee run` 进程。
    """
    lock_dir = project_root / ".workflow"
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_path = lock_dir / "run.lock"
    lock_fp = open(lock_path, "a+", encoding="utf-8")

    if fcntl is None:
        return lock_fp

    try:
        fcntl.flock(lock_fp.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock_fp.seek(0)
        owner = lock_fp.read().strip() or "unknown owner"
        lock_fp.close()
        raise click.ClickException(
            "Detected another active `lee run` in this project. "
            f"Lock info: {owner}"
        )

    lock_fp.seek(0)
    lock_fp.truncate()
    lock_fp.write(
        f"pid={os.getpid()} started_at={datetime.now().isoformat()} project={project_root}"
    )
    lock_fp.flush()
    return lock_fp


def _release_project_run_lock(lock_fp) -> None:
    if not lock_fp:
        return
    try:
        if fcntl is not None:
            fcntl.flock(lock_fp.fileno(), fcntl.LOCK_UN)
    finally:
        lock_fp.close()


@click.command()
@click.argument("workflow_key")
@click.option("--spec", help="Spec 文件路径")
@click.option("--env", help="目标环境")
@click.option("--version", help="版本/commit")
@click.option("--branch", help="目标分支")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=10, show_default=True, help="最大执行步数")
@click.option("--executor", default="claude_code", show_default=True, help="强制指定执行器类型（覆盖 spec 中的配置）", type=click.Choice([
    "llm", "shell", "claude_code", "codex", "langgraph"
]))
@click.option("--plan-only", is_flag=True, help="只生成 Plan，不执行")
@click.option("--skip-plan", is_flag=True, help="跳过 Plan，直接执行")
@click.option("--plan-mode", type=click.Choice(["simple", "suggest", "force"]), default="suggest", help="Plan 模式")
@click.option("--instance", help="从指定 Instance ID 运行")
@click.option("--task-id", help="关联现有 Task ID (SSOT Root)")
@click.option("--new-task", help="创建新 Task 作为 SSOT Root (提供任务描述)")
def run(workflow_key: str, spec: str | None, env: str | None, version: str | None,
        branch: str | None, project_dir: str, max_steps: int, executor: str | None,
        plan_only: bool, skip_plan: bool, plan_mode: str, instance: str | None,
        task_id: str | None, new_task: str | None) -> None:
    """运行指定工作流"""
    registry = _load_registry()
    workflows = registry.get("workflows", {})
    if workflow_key not in workflows:
        raise click.ClickException(f"Unknown workflow: {workflow_key}")

    entry = workflows[workflow_key]
    template_path = resolve_workflow_template_path(entry.get("path", ""))
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    params: Dict[str, Any] = {}
    if spec:
        params.update(_load_spec_option(spec))
    if env:
        params["env"] = env
    if version:
        params["version"] = version
    if branch:
        params["branch"] = branch

    # 为未显式传入的参数填充模板默认值，避免渲染为空字符串。
    default_params = _load_template_param_defaults(template_path)
    for k, v in default_params.items():
        params.setdefault(k, v)

    required = entry.get("required_params", []) or []
    missing = [p for p in required if p not in params]
    if missing:
        raise click.ClickException(f"Missing required params: {', '.join(missing)}")

    project_root = Path(project_dir).resolve()

    # SSOT Root 确认 (v1 简化版)
    ssot_root_id = task_id
    if new_task and not task_id:
        # 创建新 Task Card 作为 SSOT root
        artifacts_root = project_root / ".artifacts"
        artifact_manager = ArtifactManager(artifacts_root)
        task_card = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="task_card",
            content=f"# Task Card\n\n{new_task}",
            run_id=f"task-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
            title=new_task[:50],
            governance_kind=GovernanceKind.TRANSFER,
        )
        ssot_root_id = task_card.id
        click.echo(f"✅ Created Task Card: {ssot_root_id}")
    elif not task_id and not new_task:
        # 检查工作流是否会修改持久状态 (简化：所有 workflow 都视为会修改)
        click.echo(
            "\n⚠️  提示：此工作流会修改持久状态。\n"
            "建议使用 --task-id 或 --new-task 来指定 SSOT Root。\n"
            "例如:\n"
            f"   lee run {workflow_key} --task-id TASK-xxx\n"
            f"   lee run {workflow_key} --new-task \"任务描述\"\n"
        )

    lock_fp = _acquire_project_run_lock(project_root)
    try:
        if instance:
            workflow_id = instance
            click.echo(f"Using existing workflow instance: {workflow_id}")
            click.echo(f"\n执行中... (使用 'lee status {workflow_id}' 查看详细状态)")
            stop_event, monitor = _start_progress_monitor(project_root, workflow_id)
            try:
                summary = _run_until_settled_with_gates(project_root, workflow_id, max_steps)
            finally:
                stop_event.set()
                monitor.join(timeout=1)
            summary = _refresh_summary_from_store(project_root, workflow_id, summary)
            _print_summary(project_root, workflow_id, summary)
            return

        existing = _list_existing_same_workflows(project_root, workflow_key)
        if existing:
            action, existing_workflow_id = _select_existing_workflow_action(existing)
            if action == "continue":
                selected = next((item for item in existing if item["id"] == existing_workflow_id), existing[0])
                if selected["status"] == "paused":
                    resume_result = pm_workflow(
                        "resume",
                        project_dir=str(project_root),
                        workflow_id=selected["id"],
                    )
                    if "error" in resume_result:
                        raise click.ClickException(str(resume_result.get("error")))

                click.echo(f"\n继续旧流程: {selected['id']}")
                click.echo(f"执行中... (使用 'lee status {selected['id']}' 查看详细状态)")
                stop_event, monitor = _start_progress_monitor(project_root, selected["id"])
                try:
                    summary = _run_until_settled_with_gates(project_root, selected["id"], max_steps)
                finally:
                    stop_event.set()
                    monitor.join(timeout=1)
                summary = _refresh_summary_from_store(project_root, selected["id"], summary)
                _print_summary(project_root, selected["id"], summary)
                return

            # restart: 将同类旧流程统一暂停，然后创建新流程
            for item in existing:
                pause_result = pm_workflow(
                    "pause",
                    project_dir=str(project_root),
                    workflow_id=item["id"],
                )
                if "error" not in pause_result:
                    click.echo(f"已暂停旧流程: {item['id']}")

        # 新增: 使用 WorkflowRunner 处理 Plan -> Instance -> Execute
        if not instance and not skip_plan:
            # 使用 Plan 模式
            from lee.orchestrator.execution.workflow_runner import run_workflow
            import asyncio

            click.echo(f"[Plan Mode] 生成执行计划...")

            result = asyncio.run(run_workflow(
                workflow_key=workflow_key,
                template_path=template_path,
                params=params,
                project_root=project_root,
                plan_mode=plan_mode,
                skip_plan=False,
                instance_id=instance,
                ssot_root_id=ssot_root_id
            ))

            if not result.success:
                raise click.ClickException(f"Plan 失败: {result.error}")

            if plan_only:
                click.echo(f"\n✅ Plan 已生成")
                click.echo(f"Instance: {result.instance_path}")
                if result.plan_summary:
                    click.echo(f"\n--- Plan Summary ---\n{result.plan_summary}")
                return

            workflow_id = result.workflow_id
            click.echo(f"Created workflow: {workflow_id}")
            click.echo(f"Instance: {result.instance_path}")

            if result.plan_summary:
                click.echo(f"\n--- Plan Summary ---\n{result.plan_summary[:500]}...")

            click.echo(f"\n执行中... (使用 'lee status {workflow_id}' 查看详细状态)")

            # 执行工作流
            stop_event, monitor = _start_progress_monitor(project_root, workflow_id)
            try:
                summary = _run_until_settled_with_gates(project_root, workflow_id, max_steps)
            finally:
                stop_event.set()
                monitor.join(timeout=1)
            summary = _refresh_summary_from_store(project_root, workflow_id, summary)
            _print_summary(project_root, workflow_id, summary)
            _release_project_run_lock(lock_fp)
            return

        # 原有逻辑: 直接执行
        rendered_path = _render_workflow_template(template_path, params, project_root)

        # Create workflow instance (L3 task)
        # 如果指定了 executor override，将其加入 data 中传递给 workflow
        workflow_data: Dict[str, Any] = {"params": params, "workflow_key": workflow_key}
        if executor:
            workflow_data["executor_override"] = executor
            click.echo(f"Executor override: {executor}")

        create_result = pm_workflow(
            "create",
            project_dir=str(project_root),
            level="task",
            template_id=str(rendered_path),
            data=workflow_data,
        )

        if "error" in create_result:
            raise click.ClickException(str(create_result.get("error")))

        workflow_id = create_result.get("workflow_id")
        if not workflow_id:
            raise click.ClickException(f"Workflow creation failed: {create_result}")

        click.echo(f"Created workflow: {workflow_id}")
        click.echo(f"Template: {rendered_path}")
        click.echo(f"\n执行中... (使用 'lee status {workflow_id}' 查看详细状态)")

        # 执行工作流
        stop_event, monitor = _start_progress_monitor(project_root, workflow_id)
        try:
            summary = _run_until_settled_with_gates(project_root, workflow_id, max_steps)
        finally:
            stop_event.set()
            monitor.join(timeout=1)
        summary = _refresh_summary_from_store(project_root, workflow_id, summary)
        _print_summary(project_root, workflow_id, summary)
    finally:
        _release_project_run_lock(lock_fp)
