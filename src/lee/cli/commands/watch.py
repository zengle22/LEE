"""lee watch command"""

import asyncio
import click
import sqlite3
import time
from pathlib import Path
from typing import Optional


@click.command()
@click.argument("workflow_id", required=False)
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--interval", default=2, help="刷新间隔（秒）")
def watch(workflow_id: Optional[str], project_dir: str, interval: int) -> None:
    """实时监控工作流执行进度"""
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"

    if not db_path.exists():
        click.echo(f"错误: 数据库不存在 {db_path}")
        return

    # 如果没有提供 workflow_id，显示列表并让用户选择
    if not workflow_id:
        workflow_id = _select_workflow_to_watch(db_path)
        if not workflow_id:
            click.echo("已取消监控")
            return

    _watch_workflow(db_path, workflow_id, interval)


def _list_workflows(db_path: Path) -> list:
    """列出所有活跃的工作流"""
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()

    cursor.execute(
        """SELECT id, status, template_id
           FROM workflow_instances
           WHERE status NOT IN ('completed', 'failed')
           ORDER BY created_at DESC"""
    )

    workflows = []
    for row in cursor.fetchall():
        workflows.append({
            "id": row[0],
            "status": row[1],
            "template_id": row[2] if len(row) > 2 else "N/A"
        })

    conn.close()
    return workflows


def _select_workflow_to_watch(db_path: Path) -> Optional[str]:
    """显示工作流列表并让用户选择"""
    workflows = _list_workflows(db_path)

    if not workflows:
        click.echo("没有活跃的工作流")
        return None

    click.echo("=" * 70)
    click.echo("可监控的工作流:")
    click.echo("=" * 70)

    for i, wf in enumerate(workflows, 1):
        status_icon = {
            "running": "🔄",
            "paused": "⏸️",
            "pending": "⏳",
            "blocked": "🚫"
        }.get(wf["status"], "❓")

        click.echo(f"{i}. {status_icon} {wf['id']}")
        click.echo(f"   模板: {wf['template_id']}")
        click.echo(f"   状态: {wf['status']}")
        click.echo()

    click.echo("0. 取消")
    click.echo()

    try:
        choice = click.prompt("请选择要监控的工作流", type=int, default=1)

        if choice == 0:
            return None

        if 1 <= choice <= len(workflows):
            return workflows[choice - 1]["id"]
        else:
            click.echo("无效的选择")
            return None

    except (KeyboardInterrupt, EOFError):
        click.echo("\n已取消")
        return None


def _watch_workflow(db_path: Path, workflow_id: str, interval: int) -> None:
    """监控指定的工作流"""
    click.echo(f"监控工作流: {workflow_id}")
    click.echo(f"数据库: {db_path}")
    click.echo("=" * 60)
    click.echo("按 Ctrl+C 停止监控\n")

    try:
        last_status = None
        last_completed = 0

        while True:
            try:
                conn = sqlite3.connect(str(db_path))
                cursor = conn.cursor()

                # 获取工作流状态
                cursor.execute(
                    "SELECT status FROM workflow_instances WHERE id = ?",
                    (workflow_id,)
                )
                result = cursor.fetchone()
                if not result:
                    click.echo("工作流不存在")
                    break

                status = result[0]

                # 获取步骤信息
                cursor.execute(
                    """SELECT step_name, status, started_at, completed_at
                       FROM task_executions
                       WHERE workflow_id = ?
                       ORDER BY started_at""",
                    (workflow_id,)
                )
                steps = cursor.fetchall()
                completed = sum(1 for s in steps if s[1] == "completed")
                running = [s for s in steps if s[1] == "running"]
                failed = [s for s in steps if s[1] == "failed"]

                # 只在有变化时更新显示
                if status != last_status or completed != last_completed:
                    timestamp = time.strftime("%H:%M:%S")

                    click.echo(f"\n[{timestamp}] 状态: {status}")
                    click.echo(f"进度: {completed}/{len(steps)} 步骤已完成")

                    if running:
                        click.echo(f"当前执行: {running[0][0]}")

                    if failed:
                        click.echo(f"失败步骤: {', '.join(f[0] for f in failed)}")

                    # 显示已完成步骤列表
                    if completed > 0:
                        click.echo("\n已完成的步骤:")
                        for step in steps:
                            if step[1] == "completed":
                                click.echo(f"  ✅ {step[0]}")

                    # 显示当前正在运行的步骤
                    if running:
                        click.echo("\n正在执行:")
                        for step in running:
                            click.echo(f"  ⚙️  {step[0]}")

                    last_status = status
                    last_completed = completed

                conn.close()

                # 检查是否已完成/失败/暂停
                if status in ["completed", "failed", "paused"]:
                    click.echo(f"\n工作流已{status}")

                    # 显示失败步骤的错误信息
                    if status in ["failed", "paused"]:
                        try:
                            cursor.execute(
                                """SELECT step_name, error_message, status
                                   FROM task_executions
                                   WHERE workflow_id = ? AND status IN ('failed', 'running')
                                   ORDER BY started_at DESC""",
                                (workflow_id,)
                            )
                            problem_steps = cursor.fetchall()

                            if problem_steps:
                                click.echo("\n问题详情:")
                                for step_name, error, step_status in problem_steps:
                                    if step_status == "failed":
                                        click.echo(f"  ❌ {step_name}: {error}")
                                    elif step_status == "running":
                                        click.echo(f"  ⚙️  {step_name}: 正在执行中...")
                        except Exception:
                            pass

                    # 关闭连接
                    try:
                        conn.close()
                    except:
                        pass

                    break

            except Exception as e:
                click.echo(f"查询错误: {e}")

            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\n\n监控已停止")
