"""lee gates command - 统一的门禁管理入口"""

import click
import json
import sqlite3
from pathlib import Path

from lee.orchestrator.api import pm_workflow


@click.group()
def gates():
    """门禁管理命令（统一入口）"""
    pass


@gates.command()
@click.argument("workflow_id")
@click.option("--project-dir", default=".", help="项目目录")
def list(workflow_id: str, project_dir: str) -> None:
    """列出待处理的门禁"""
    # 查询数据库获取门禁信息
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"

    if not db_path.exists():
        click.echo(f"错误: 数据库不存在 {db_path}")
        return

    try:
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()

        # 获取工作流状态
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
        click.echo(f"当前步骤: {current_step or '无'}")

        # 获取待审核的门禁
        cursor.execute(
            """SELECT gate_id, status, approver, comments
               FROM gate_approvals
               WHERE workflow_id = ?""",
            (workflow_id,)
        )
        gates = cursor.fetchall()

        if gates:
            click.echo("\n门禁列表:")
            for gate_id, gate_status, approver, comments in gates:
                status_icon = "⏳" if gate_status == "pending" else "✅" if gate_status == "approved" else "❌"
                click.echo(f"  {status_icon} {gate_id}")
                click.echo(f"     状态: {gate_status}")
                if approver:
                    click.echo(f"     审批人: {approver}")
                if comments:
                    click.echo(f"     评论: {comments}")
        else:
            click.echo("\n没有门禁记录")
            # 从当前步骤推断门禁
            if current_step and "review" in current_step or "confirm" in current_step:
                click.echo(f"\n推断门禁: {current_step}")

        conn.close()

    except Exception as e:
        click.echo(f"查询失败: {e}")


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
@click.argument("gate_id")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="审批意见")
@click.option("--project-dir", default=".", help="项目目录")
def approve(workflow_id: str, gate_id: str, approver: str, comments: str, project_dir: str) -> None:
    """批准门禁"""
    # 先显示门禁详情
    click.echo(f"批准门禁: {gate_id}")
    click.echo(f"工作流: {workflow_id}")
    click.echo(f"审批人: {approver}")
    if comments:
        click.echo(f"意见: {comments}")

    # 查看产物文件
    click.echo("\n📂 查看产物文件...")
    project_root = Path(project_dir).resolve()

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
    try:
        result = pm_workflow(
            "approve_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=gate_id,
            approver=approver,
            decision="approve",
            comments=comments
        )

        click.echo(f"\n✅ 门禁已批准")
        if result.get("next_step"):
            click.echo(f"下一步: {result.get('next_step')}")

    except Exception as e:
        click.echo(f"批准失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--approver", required=True, help="审批人")
@click.option("--comments", default="", help="拒绝原因")
@click.option("--action", type=click.Choice(["rollback", "spawn"]), help="执行动作（rollback/spawn）")
@click.option("--target-step", help="目标步骤（用于 rollback）")
@click.option("--project-dir", default=".", help="项目目录")
def reject(workflow_id: str, gate_id: str, approver: str, comments: str, action: str, target_step: str, project_dir: str) -> None:
    """拒绝门禁（v1.1: 支持动作选择）"""
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
    try:
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

        click.echo(f"\n❌ 门禁已拒绝")
        if result.get("action"):
            click.echo(f"执行动作: {result.get('action')}")
        if result.get("target_step"):
            click.echo(f"目标步骤: {result.get('target_step')}")
        if result.get("new_workflow_id"):
            click.echo(f"新工作流: {result.get('new_workflow_id')}")

    except Exception as e:
        click.echo(f"拒绝失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--reviewer", required=True, help="评审人")
@click.option("--reason", required=True, help="修改意见")
@click.option("--target-step", help="重试目标步骤")
@click.option("--structured-feedback", help="结构化反馈（JSON）")
@click.option("--project-dir", default=".", help="项目目录")
def revise(workflow_id: str, gate_id: str, reviewer: str, reason: str, target_step: str, structured_feedback: str, project_dir: str) -> None:
    """修订门禁，重试步骤（v1.1 新增）"""
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
    try:
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

        click.echo(f"\n🔄 门禁已修订，工作流将重试")
        if result.get("target_step"):
            click.echo(f"重试目标: {result.get('target_step')}")

    except Exception as e:
        click.echo(f"修订失败: {e}")


@gates.command()
@click.argument("workflow_id")
@click.argument("gate_id")
@click.option("--reporter", required=True, help="报告人")
@click.option("--issues", required=True, help="问题列表（逗号分隔）")
@click.option("--continue-workflow/--pause-workflow", default=True, help="是否继续工作流（默认继续）")
@click.option("--project-dir", default=".", help="项目目录")
def flag(workflow_id: str, gate_id: str, reporter: str, issues: str, continue_workflow: bool, project_dir: str) -> None:
    """标记门禁问题（v1.1 新增）"""
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
    try:
        result = pm_workflow(
            "flag_gate",
            project_dir=project_dir,
            workflow_id=workflow_id,
            gate_id=gate_id,
            reporter=reporter,
            issues=issue_list,
            continue_workflow=continue_workflow,
        )

        status_str = "继续执行" if continue_workflow else "暂停等待审核"
        click.echo(f"\n🚩 门禁已标记，工作流{status_str}")

    except Exception as e:
        click.echo(f"标记失败: {e}")
