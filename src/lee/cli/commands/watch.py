"""lee watch command"""

import click
import sqlite3
import time
from pathlib import Path


@click.command()
@click.argument("workflow_id")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--interval", default=2, help="刷新间隔（秒）")
def watch(workflow_id: str, project_dir: str, interval: int) -> None:
    """实时监控工作流执行进度"""
    project_root = Path(project_dir).resolve()
    db_path = project_root / ".workflow" / "orchestrator.db"

    if not db_path.exists():
        click.echo(f"错误: 数据库不存在 {db_path}")
        return

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

                # 检查是否已完成/失败
                if status in ["completed", "failed", "paused"]:
                    click.echo(f"\n工作流已{status}")

                    # 显示失败步骤的错误信息
                    if status == "failed" or status == "paused":
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

                    break

            except Exception as e:
                click.echo(f"查询错误: {e}")

            time.sleep(interval)

    except KeyboardInterrupt:
        click.echo("\n\n监控已停止")
