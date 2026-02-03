"""
Check workflow status
"""
import asyncio
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.template_manager import TemplateManager


async def check_status():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    db_path = project_root / "devops" / "orchestrator_full.db"

    store = SQLiteStore(str(db_path))
    await store.connect()

    # 获取所有工作流
    workflows = await store.get_all_instances()
    print(f"📋 数据库中的工作流 ({len(workflows)} 个):")
    for wf in workflows:
        print(f"\n   {wf.id}:")
        print(f"      模板: {wf.template_id}")
        print(f"      状态: {wf.status.value}")
        print(f"      当前步骤: {wf.current_step}")
        print(f"      完成的步骤: {wf.data.get('completed_steps', [])}")

    # 检查最近的工作流的任务执行记录
    if workflows:
        latest_wf = workflows[-1]
        executions = await store.get_task_executions(latest_wf.id)
        print(f"\n📝 任务执行记录 ({len(executions)} 个):")
        for exe in executions:
            print(f"   {exe.step_name}: {exe.status.value}")
            if exe.error_message:
                print(f"      错误: {exe.error_message}")

    await store.close()


if __name__ == "__main__":
    asyncio.run(check_status())
