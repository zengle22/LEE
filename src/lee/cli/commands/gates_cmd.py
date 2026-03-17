"""lee gates command - 统一的门禁管理入口"""

from __future__ import annotations

import click
import json
import os
import sqlite3
from pathlib import Path
from typing import Any, Dict, List

from lee.orchestrator.api import pm_workflow
from lee.orchestrator.storage.models import GatePurpose, GateDecisionMode


@click.group()
def gates():
    """门禁管理命令（统一入口）"""
    pass


def _safe_json_loads(raw: str | None, default):
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


def _load_gates_from_db(
    project_root: Path,
    workflow_id: str | None = None,
    status_filter: str | None = None,
) -> List[Dict[str, Any]]:
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        base_sql = """
            SELECT gate_id, step_id, status, approver, comments,
                   created_at, decided_at, approval_criteria, reviewers,
                   default_reject_action, default_reject_target,
                   purpose, decision_mode, legacy_gate_type
            FROM gate_approvals
        """
        params: list[Any] = []
        where_clauses = []

        if workflow_id:
            where_clauses.append("workflow_id = ?")
            params.append(workflow_id)

        if status_filter:
            where_clauses.append("status = ?")
            params.append(status_filter)

        if where_clauses:
            base_sql += " WHERE " + " AND ".join(where_clauses)

        base_sql += " ORDER BY created_at"
        cursor.execute(base_sql, params)

        rows = []
        for (
            gate_id,
            step_id,
            status,
            approver,
            comments,
            created_at,
            decided_at,
            approval_criteria,
            reviewers,
            default_reject_action,
            default_reject_target,
            purpose,
            decision_mode,
            legacy_gate_type,
        ) in cursor.fetchall():
            row_dict = {
                "gate_id": gate_id,
                "step_id": step_id,
                "status": status,
                "approver": approver,
                "comments": comments,
                "created_at": created_at,
                "decided_at": decided_at,
                "approval_criteria": _safe_json_loads(approval_criteria, []),
                "reviewers": _safe_json_loads(reviewers, []),
                "default_reject_action": default_reject_action,
                "default_reject_target": default_reject_target,
            }
            # SRC-041: 双轴字段
            if purpose:
                try:
                    row_dict["purpose"] = GatePurpose(purpose).value
                except ValueError:
                    row_dict["purpose"] = purpose
            if decision_mode:
                try:
                    row_dict["decision_mode"] = GateDecisionMode(decision_mode).value
                except ValueError:
                    row_dict["decision_mode"] = decision_mode
            if legacy_gate_type:
                row_dict["legacy_gate_type"] = legacy_gate_type
            rows.append(row_dict)
        return rows
    finally:
        conn.close()


def _print_gate_details(gate: Dict[str, Any]) -> None:
    click.echo(f"\nGate: {gate.get('gate_id')}")
    click.echo(f"Step: {gate.get('step_id')}")
    click.echo(f"状态: {gate.get('status')}")
    if gate.get("created_at"):
        click.echo(f"创建时间: {gate.get('created_at')}")
    if gate.get("reviewers"):
        click.echo("评审人:")
        for reviewer in gate["reviewers"]:
            if isinstance(reviewer, dict):
                rid = reviewer.get("id") or reviewer.get("name") or str(reviewer)
                click.echo(f"  - {rid}")
            else:
                click.echo(f"  - {reviewer}")
    if gate.get("approval_criteria"):
        click.echo("待决策条件:")
        for idx, criterion in enumerate(gate["approval_criteria"], 1):
            if isinstance(criterion, dict):
                title = criterion.get("name") or criterion.get("title") or f"条件{idx}"
                desc = criterion.get("description") or criterion.get("rule") or ""
                click.echo(f"  {idx}. {title}{f' - {desc}' if desc else ''}")
            else:
                click.echo(f"  {idx}. {criterion}")
    if gate.get("default_reject_action"):
        target = gate.get("default_reject_target")
        target_suffix = f" (target={target})" if target else ""
        click.echo(
            "默认拒绝动作: "
            f"{gate.get('default_reject_action')}"
            f"{target_suffix}"
        )


def _resolve_gate_ref(
    project_root: Path,
    workflow_id: str,
    gate_ref: str,
    *,
    pending_only: bool = True,
) -> str:
    """
    允许用户传 gate_id 或 step_id。
    - 若传 gate_id，直接返回
    - 若传 step_id，自动映射到对应 gate_id（优先 pending）
    """
    status_filter = "pending" if pending_only else None
    gates = _load_gates_from_db(project_root, workflow_id, status_filter=status_filter)
    if not gates:
        raise click.ClickException(
            f"Workflow {workflow_id} has no {'pending ' if pending_only else ''}gates."
        )

    exact_gate = [g for g in gates if g.get("gate_id") == gate_ref]
    if exact_gate:
        return gate_ref

    step_matches = [g for g in gates if g.get("step_id") == gate_ref]
    if len(step_matches) == 1:
        mapped = step_matches[0]["gate_id"]
        click.echo(f"检测到步骤 ID，自动映射: {gate_ref} -> {mapped}")
        return mapped
    if len(step_matches) > 1:
        candidates = ", ".join(g["gate_id"] for g in step_matches)
        raise click.ClickException(
            f"Step '{gate_ref}' matches multiple gates: {candidates}. "
            "Please use explicit gate_id."
        )

    pending_list = ", ".join(g.get("gate_id") for g in gates[:8])
    hint = f" Available gates: {pending_list}" if pending_list else ""
    raise click.ClickException(
        f"Gate/step '{gate_ref}' not found in workflow {workflow_id}.{hint}"
    )


@gates.command()
@click.argument("workflow_id", required=False, default=None)
@click.option("--all", "-a", is_flag=True, help="显示所有门禁（包括已处理的）")
@click.option("--pending", "-p", is_flag=True, help="只显示待处理门禁（默认）")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--show-dual-axis", is_flag=True, help="显示双轴字段 (purpose, decision_mode)")
def list(workflow_id: str | None, all: bool, pending: bool, project_dir: str, show_dual_axis: bool) -> None:
    """列出门禁

    不指定 WORKFLOW_ID 时，列出所有工作流的门禁。
    使用 --all 显示已处理的历史门禁。
    使用 --show-dual-axis 显示 SRC-041 双轴模型字段 (purpose, decision_mode)。
    """
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"

    if not db_path.exists():
        click.echo(f"错误: 数据库不存在 {db_path}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        if workflow_id:
            # 查询指定工作流
            cursor.execute(
                "SELECT status, current_step FROM workflow_instances WHERE id = ?",
                (workflow_id,)
            )
            result = cursor.fetchone()

            if not result:
                click.echo(f"工作流不存在: {workflow_id}")
                conn.close()
                return

            status, current_step = result
            click.echo(f"工作流: {workflow_id}")
            click.echo(f"状态: {status}")
            click.echo(f"当前步骤: {current_step or '无'}")

            # 获取门禁
            status_filter = None if all else "pending"
            gates = _load_gates_from_db(project_root, workflow_id, status_filter)
        else:
            # 查询所有工作流的门禁
            status_filter = None if all else "pending"
            cursor.execute("""
                SELECT id, status, current_step
                FROM workflow_instances
                ORDER BY updated_at DESC
            """)
            workflows = cursor.fetchall()

            if not workflows:
                click.echo("没有找到任何工作流")
                conn.close()
                return

            # 收集所有门禁
            all_gates = []
            for wf_id, wf_status, wf_step in workflows:
                gates = _load_gates_from_db(project_root, wf_id, status_filter)
                for gate in gates:
                    gate["workflow_id"] = wf_id
                    gate["workflow_status"] = wf_status
                    gate["workflow_current_step"] = wf_step
                    all_gates.append(gate)

            gates = all_gates

        if not gates:
            if workflow_id:
                click.echo("\n没有门禁记录")
            else:
                click.echo("没有找到门禁记录")
            conn.close()
            return

        # 显示门禁列表
        if workflow_id:
            click.echo("\n门禁列表:")
        else:
            click.echo(f"\n门禁列表 ({'所有' if all else '待处理'}):")

        for gate in gates:
            gate_id = gate.get("gate_id")
            step_id = gate.get("step_id")
            status = gate.get("status")
            approver = gate.get("approver")
            comments = gate.get("comments")
            created_at = gate.get("created_at")

            # 状态图标
            if status == "pending":
                status_icon = "⏳"
            elif status == "approved":
                status_icon = "✅"
            elif status == "rejected":
                status_icon = "❌"
            elif status == "flagged":
                status_icon = "🚩"
            else:
                status_icon = "📝"

            # 工作流信息（多工作流模式）
            if not workflow_id:
                wf_id = gate.get("workflow_id")
                wf_status = gate.get("workflow_status")
                click.echo(f"\n[{status_icon}] {gate_id} (工作流: {wf_id}, 状态: {wf_status})")
            else:
                click.echo(f"\n{status_icon} {gate_id}")

            click.echo(f"  步骤: {step_id}")
            click.echo(f"  状态: {status}")

            if approver:
                click.echo(f"  审批人: {approver}")
            if comments:
                click.echo(f"  评论: {comments}")
            if created_at and not workflow_id:
                click.echo(f"  创建时间: {created_at}")

            # 显示默认拒绝动作
            if gate.get("default_reject_action"):
                target = gate.get("default_reject_target")
                target_suffix = f" (target={target})" if target else ""
                click.echo(f"  默认拒绝动作: {gate.get('default_reject_action')}{target_suffix}")

            # SRC-041: 显示双轴字段
            if show_dual_axis:
                purpose = gate.get("purpose", "review")
                decision_mode = gate.get("decision_mode", "human_required")
                click.echo(f"  双轴模型:")
                click.echo(f"    purpose: {purpose}")
                click.echo(f"    decision_mode: {decision_mode}")
                legacy = gate.get("legacy_gate_type")
                if legacy:
                    click.echo(f"    legacy_gate_type: {legacy}")

        conn.close()

    except Exception as e:
        click.echo(f"查询失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.option("--approver", default=lambda: os.getenv("USER", "reviewer"), show_default="当前用户")
@click.option("--project-dir", default=".", help="项目目录")
def decide(workflow_id: str, approver: str, project_dir: str) -> None:
    """交互式门禁决策：选择 gate 后一键 approve/reject。"""
    project_root = Path(project_dir).resolve()
    pending_gates = _load_gates_from_db(project_root, workflow_id, status_filter="pending")

    if not pending_gates:
        click.echo(f"工作流 {workflow_id} 当前没有待决策门禁。")
        all_gates = _load_gates_from_db(project_root, workflow_id, status_filter=None)
        if all_gates:
            click.echo("已有门禁记录:")
            for gate in all_gates:
                click.echo(
                    f"  - {gate.get('gate_id')} [{gate.get('status')}]"
                    f" step={gate.get('step_id')}"
                )
        return

    click.echo(f"工作流: {workflow_id}")
    click.echo("待决策门禁:")
    for idx, gate in enumerate(pending_gates, 1):
        criteria_count = len(gate.get("approval_criteria") or [])
        click.echo(
            f"  {idx}. {gate.get('gate_id')} (step={gate.get('step_id')}, 条件数={criteria_count})"
        )

    selected_idx = 1
    if len(pending_gates) > 1:
        selected_idx = click.prompt(
            "选择 gate 编号",
            type=click.IntRange(1, len(pending_gates)),
            default=1,
        )
    selected_gate = pending_gates[selected_idx - 1]
    _print_gate_details(selected_gate)

    decision = click.prompt(
        "请选择决策",
        type=click.Choice(["approve", "reject"], case_sensitive=False),
        default="approve",
    ).lower()

    if decision == "approve":
        comments = click.prompt("审批意见（可留空）", default="", show_default=False)
        result = pm_workflow(
            "approve_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=selected_gate["gate_id"],
            approver=approver,
            comments=comments,
        )
    else:
        reason = click.prompt("拒绝原因", default="Rejected by reviewer")
        result = pm_workflow(
            "reject_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=selected_gate["gate_id"],
            rejecter=approver,
            reason=reason,
        )
        # 没有默认动作时再补充一次最小交互
        if "error" in result and "must specify action" in str(result.get("error", "")).lower():
            click.echo("该门禁需要指定拒绝动作。")
            action = click.prompt(
                "选择动作",
                type=click.Choice(["rollback", "spawn"], case_sensitive=False),
                default="rollback",
            ).lower()
            target_step = None
            if action == "rollback":
                target_step = click.prompt("目标步骤（可留空）", default="", show_default=False).strip() or None
            result = pm_workflow(
                "reject_gate",
                project_dir=project_dir,
                workflow_id=workflow_id,
                gate_id=selected_gate["gate_id"],
                rejecter=approver,
                reason=reason,
                action=action,
                target_step=target_step,
            )

    if "error" in result:
        raise click.ClickException(str(result.get("error")))

    status_label = "批准" if decision == "approve" else "拒绝"
    click.echo(f"\n✅ 已{status_label}: {selected_gate['gate_id']}")
    if result.get("message"):
        click.echo(result["message"])


@gates.command()
@click.argument("workflow_id")
@click.option("--project-dir", default=".", help="项目目录")
def show(workflow_id: str, project_dir: str) -> None:
    """显示门禁详情和产物（artifacts）"""
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"

    if not db_path.exists():
        click.echo(f"错误: 数据库不存在 {db_path}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 获取工作流信息
        cursor.execute(
            "SELECT status, current_step FROM workflow_instances WHERE id = ?",
            (workflow_id,)
        )
        result = cursor.fetchone()

        if not result:
            click.echo(f"工作流不存在: {workflow_id}")
            return

        status, current_step = result
        click.echo(f"工作流: {workflow_id}")
        click.echo(f"状态: {status}")
        click.echo(f"当前步骤: {current_step}")

        # 显示失败的步骤（如果有）
        if status in ["failed", "paused"]:
            cursor.execute(
                """SELECT step_name, error_message
                   FROM task_executions
                   WHERE workflow_id = ? AND status = 'failed'
                   ORDER BY started_at DESC LIMIT 5""",
                (workflow_id,)
            )
            failed_steps = cursor.fetchall()

            if failed_steps:
                click.echo("\n❌ 失败的步骤:")
                for step_name, error in failed_steps:
                    click.echo(f"\n  步骤: {step_name}")
                    click.echo(f"  错误: {error}")

        # 查找门禁相关的产物文件
        click.echo("\n📂 相关产物文件:")

        # 简化处理：列出可能的相关文件
        if (project_root / "workspace-cleanup").exists():
            click.echo("\nworkspace-cleanup/:")
            artifact_path = project_root / "workspace-cleanup"
            files = sorted(artifact_path.glob("*.yaml")) + sorted(artifact_path.glob("*.md"))
            for f in files[:10]:
                click.echo(f"  - {f.name}")

        if (project_root / "tech-debt").exists():
            click.echo("\ntech-debt/:")
            artifact_path = project_root / "tech-debt"
            files = sorted(artifact_path.glob("*.yaml")) + sorted(artifact_path.glob("*.md"))
            for f in files[:10]:
                click.echo(f"  - {f.name}")

        # 显示最近的执行记录
        click.echo("\n📝 最近执行的步骤:")
        cursor.execute(
            """SELECT step_name, status, datetime(started_at), datetime(completed_at)
               FROM task_executions
               WHERE workflow_id = ?
               ORDER BY started_at DESC LIMIT 5""",
            (workflow_id,)
        )
        steps = cursor.fetchall()

        for step_name, step_status, started, completed in steps:
            status_icon = "✅" if step_status == "completed" else "❌" if step_status == "failed" else "⚙️"
            click.echo(f"  {status_icon} {step_name} ({step_status})")

        conn.close()

    except Exception as e:
        click.echo(f"查询失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_ref")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="审批意见")
@click.option("--project-dir", default=".", help="项目目录")
def approve(workflow_id: str, gate_ref: str, approver: str, comments: str, project_dir: str) -> None:
    """批准门禁（支持 gate_id 或 step_id）"""
    project_root = Path(project_dir).resolve()
    gate_id = _resolve_gate_ref(project_root, workflow_id, gate_ref, pending_only=True)

    # 先显示门禁详情
    click.echo(f"批准门禁: {gate_id}")
    click.echo(f"工作流: {workflow_id}")
    click.echo(f"审批人: {approver}")
    if comments:
        click.echo(f"意见: {comments}")

    # 查看产物文件
    click.echo("\n📂 查看产物文件...")

    # 尝试显示提交计划
    commit_plan = project_root / "workspace-cleanup" / "commit-plan.yaml"
    if commit_plan.exists():
        click.echo(f"\n找到提交计划: {commit_plan}")
        click.echo("\n" + "=" * 60)
        # 显示前 50 行
        with open(commit_plan, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if i >= 50:
                    click.echo(f"\n... (省略 {sum(1 for _ in f) + 50} 行)")
                    break
                click.echo(line.rstrip())
        click.echo("=" * 60)

    # 确认批准
    if not click.confirm("\n确认批准此门禁？"):
        click.echo("已取消")
        return

    # 调用批准 API
    result = pm_workflow(
        "approve_gate",
        project_dir=project_dir,
        workflow_id=workflow_id,
        gate_id=gate_id,
        approver=approver,
        decision="approve",
        comments=comments
    )
    if "error" in result:
        raise click.ClickException(str(result.get("error")))

    click.echo(f"\n✅ 门禁已批准")
    if result.get("next_step"):
        click.echo(f"下一步: {result.get('next_step')}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_ref")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="拒绝原因")
@click.option("--action", type=click.Choice(["rollback", "spawn"]), help="执行动作（rollback/spawn）")
@click.option("--target-step", help="目标步骤（用于 rollback）")
@click.option("--project-dir", default=".", help="项目目录")
def reject(workflow_id: str, gate_ref: str, approver: str, comments: str, action: str, target_step: str, project_dir: str) -> None:
    """拒绝门禁（v1.1: 支持动作选择；支持 gate_id 或 step_id）"""
    project_root = Path(project_dir).resolve()
    gate_id = _resolve_gate_ref(project_root, workflow_id, gate_ref, pending_only=True)

    click.echo(f"拒绝门禁: {gate_id}")
    click.echo(f"工作流: {workflow_id}")
    click.echo(f"审批人: {approver}")
    if comments:
        click.echo(f"原因: {comments}")

    # v1.1: 如果没有指定 action，从数据库读取默认值
    if not action:
        click.echo("\n⚠️  未指定 --action，将使用 gate 配置的默认动作")

    # 确认拒绝
    if not click.confirm("\n确认拒绝此门禁？"):
        click.echo("已取消")
        return

    # 调用拒绝 API（v1.1: 支持 action 参数）
    result = pm_workflow(
        "reject_gate",
        project_dir=project_dir,
        workflow_id=workflow_id,
        gate_id=gate_id,
        rejecter=approver,
        reason=comments,
        action=action,
        target_step=target_step,
    )
    if "error" in result:
        raise click.ClickException(str(result.get("error")))

    click.echo(f"\n❌ 门禁已拒绝")
    if result.get("action"):
        click.echo(f"执行动作: {result.get('action')}")
    if result.get("target_step"):
        click.echo(f"目标步骤: {result.get('target_step')}")
    if result.get("new_workflow_id"):
        click.echo(f"新工作流: {result.get('new_workflow_id')}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_ref")
@click.option("--reviewer", required=True, help="评审人")
@click.option("--reason", required=True, help="修改意见")
@click.option("--target-step", help="重试目标步骤")
@click.option("--structured-feedback", help="结构化反馈（JSON）")
@click.option("--project-dir", default=".", help="项目目录")
def revise(workflow_id: str, gate_ref: str, reviewer: str, reason: str, target_step: str, structured_feedback: str, project_dir: str) -> None:
    """修订门禁，重试步骤（v1.1 新增；支持 gate_id 或 step_id）"""
    project_root = Path(project_dir).resolve()
    gate_id = _resolve_gate_ref(project_root, workflow_id, gate_ref, pending_only=True)

    click.echo(f"修订门禁: {gate_id}")
    click.echo(f"工作流: {workflow_id}")
    click.echo(f"评审人: {reviewer}")
    click.echo(f"修改意见: {reason}")

    # 解析结构化反馈
    feedback_data = None
    if structured_feedback:
        try:
            feedback_data = json.loads(structured_feedback)
            click.echo(f"结构化反馈: {json.dumps(feedback_data, ensure_ascii=False)}")
        except json.JSONDecodeError:
            click.echo(f"⚠️  结构化反馈 JSON 解析失败")

    # 确认修订
    if not click.confirm("\n确认修订此门禁并重试？"):
        click.echo("已取消")
        return

    # 调用修订 API
    result = pm_workflow(
        "revise_gate",
        project_dir=project_dir,
        workflow_id=workflow_id,
        gate_id=gate_id,
        reviewer=reviewer,
        reason=reason,
        target_step=target_step,
        structured_feedback=feedback_data,
    )
    if "error" in result:
        raise click.ClickException(str(result.get("error")))

    click.echo(f"\n🔄 门禁已修订，工作流将重试")
    if result.get("target_step"):
        click.echo(f"重试目标: {result.get('target_step')}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_ref")
@click.option("--reporter", required=True, help="报告人")
@click.option("--issues", required=True, help="问题列表（逗号分隔）")
@click.option("--continue-workflow/--pause-workflow", default=True, help="是否继续工作流（默认继续）")
@click.option("--project-dir", default=".", help="项目目录")
def flag(workflow_id: str, gate_ref: str, reporter: str, issues: str, continue_workflow: bool, project_dir: str) -> None:
    """标记门禁问题（v1.1 新增；支持 gate_id 或 step_id）"""
    project_root = Path(project_dir).resolve()
    gate_id = _resolve_gate_ref(project_root, workflow_id, gate_ref, pending_only=True)

    click.echo(f"标记门禁: {gate_id}")
    click.echo(f"工作流: {workflow_id}")
    click.echo(f"报告人: {reporter}")

    issue_list = [i.strip() for i in issues.split(",")]
    click.echo(f"问题:")
    for issue in issue_list:
        click.echo(f"  - {issue}")

    action_str = "继续工作流" if continue_workflow else "暂停工作流"
    if not click.confirm(f"\n确认标记此门禁并{action_str}？"):
        click.echo("已取消")
        return

    # 调用标记 API
    result = pm_workflow(
        "flag_gate",
        project_dir=project_dir,
        workflow_id=workflow_id,
        gate_id=gate_id,
        reporter=reporter,
        issues=issue_list,
        continue_workflow=continue_workflow,
    )
    if "error" in result:
        raise click.ClickException(str(result.get("error")))

    status_str = "继续执行" if continue_workflow else "暂停等待审核"
    click.echo(f"\n🚩 门禁已标记，工作流{status_str}")
