"""
Debug LLM output for p2_infra_code
"""
import asyncio
import sys
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


async def debug_llm_output():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "orchestrator_p2_test.db"
    template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

    store = SQLiteStore(str(db_path))
    await store.connect()

    # 获取任务执行记录
    executions = await store.get_task_executions("wf_department_106b13f5")

    print(f"📝 任务执行记录 ({len(executions)} 个):")
    for exe in executions:
        print(f"\n   步骤: {exe.step_name}")
        print(f"   状态: {exe.status.value}")

        # 打印输入数据的前500个字符
        if exe.input_data:
            system_message = exe.input_data.get("system_message", "")
            prompt = exe.input_data.get("prompt", "")
            print(f"\n   📥 System message (前500字符):")
            print(f"      {system_message[:500]}...")
            print(f"\n   📥 Prompt (前500字符):")
            print(f"      {prompt[:500]}...")

    # 检查最新的执行记录是否有输出
    if executions:
        latest_exe = executions[-1]
        # 注意：TaskExecution 可能没有 output 属性
        # 让我们检查数据库中是否有其他信息

    await store.close()


if __name__ == "__main__":
    asyncio.run(debug_llm_output())
