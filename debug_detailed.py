"""
Detailed workflow debugging
"""
import asyncio
import sys
import traceback
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


async def debug_workflow():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "orchestrator_debug.db"
    template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

    # 删除旧数据库
    if db_path.exists():
        db_path.unlink()

    print(f"📂 项目根目录: {project_root}")
    print(f"📂 模板目录: {template_dir}")

    # 初始化
    store = SQLiteStore(str(db_path))
    await store.connect()

    tm = TemplateManager(template_dir=str(template_dir))
    templates = tm.load_all_templates()
    print(f"\n📋 加载了 {len(templates)} 个模板")

    orchestrator = Orchestrator(store, tm, project_root=str(project_root))

    # 创建工作流
    workflow = await orchestrator.create_workflow(
        level=WorkflowLevel.DEPARTMENT,
        template_id="workflow.devops.deployment",
        data={"name": "Debug Test"}
    )

    print(f"\n✅ 工作流创建成功: {workflow.id}")
    print(f"   状态: {workflow.status.value}")

    # 手动更新状态为 RUNNING（否则 get_ready_steps 不会返回任何步骤）
    await store.update_workflow_status(workflow.id, WorkflowStatus.RUNNING)

    # 获取就绪步骤
    ready_steps = await orchestrator.get_ready_steps(workflow.id)
    print(f"\n🎯 就绪步骤: {len(ready_steps)}")
    for step in ready_steps:
        print(f"   - {step.id} ({step.kind})")
        print(f"     agent_id: {step.agent_id}")
        print(f"     executor_type: {step.executor_type}")

    if not ready_steps:
        print("❌ 没有就绪步骤！工作流无法继续")
        await store.close()
        return

    # 尝试执行第一步
    print(f"\n🚀 执行第一步: {ready_steps[0].id}")
    try:
        result = await orchestrator.run_step(workflow.id, ready_steps[0].id)
        print(f"\n📊 执行结果:")
        print(f"   状态: {result.status}")
        print(f"   步骤 ID: {result.step_id}")
        print(f"   消息: {result.message}")
        if result.blocked_reason:
            print(f"   阻塞原因: {result.blocked_reason}")
        if result.next_steps:
            print(f"   下一步: {result.next_steps}")

    except Exception as e:
        print(f"\n❌ 执行异常: {e}")
        traceback.print_exc()

    # 检查工作流最终状态
    instance = await store.get_workflow(workflow.id)
    print(f"\n📋 工作流最终状态: {instance.status.value}")
    print(f"   当前步骤: {instance.current_step}")

    # 检查任务执行记录
    executions = await store.get_task_executions(workflow.id)
    print(f"\n📝 任务执行记录:")
    for exe in executions:
        print(f"   步骤: {exe.step_name}")
        print(f"   状态: {exe.status.value}")
        if exe.error_message:
            print(f"   错误: {exe.error_message}")
        if exe.input_data:
            print(f"   输入: {str(exe.input_data)[:100]}...")
        if exe.output:
            print(f"   输出: {str(exe.output)[:100]}...")

    await store.close()


if __name__ == "__main__":
    asyncio.run(debug_workflow())
