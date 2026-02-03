"""
Debug workflow failure
"""
import asyncio
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.storage.models import WorkflowLevel
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


async def debug_workflow():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "orchestrator.db"
    template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

    store = SQLiteStore(str(db_path))
    await store.connect()

    # 查看所有工作流
    workflows = await store.get_all_instances()
    print(f"📋 数据库中的工作流:")
    for wf in workflows:
        print(f"   {wf.id}: {wf.template_id} - {wf.status.value}")
        if wf.data:
            print(f"      数据: {wf.data}")

    # 查看最近失败的工作流的步骤执行记录
    for wf in workflows:
        if wf.status.value == "failed":
            print(f"\n❌ 失败的工作流 {wf.id}:")
            executions = await store.get_task_executions(wf.id)
            for exe in executions:
                print(f"   步骤: {exe.step_id}")
                print(f"   状态: {exe.status.value}")
                print(f"   错误: {exe.error_message or '无'}")
                if exe.output:
                    print(f"   输出: {exe.output[:200] if len(exe.output) > 200 else exe.output}")

    await store.close()


if __name__ == "__main__":
    asyncio.run(debug_workflow())
