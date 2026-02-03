"""
Test script to verify FileOutputHandler fix
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


async def test_fix():
    # 设置正确的路径
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "test_orchestrator.db"
    template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

    print(f"📂 项目根目录: {project_root}")
    print(f"📂 模板目录: {template_dir}")
    print(f"📂 模板目录存在: {template_dir.exists()}")

    # 初始化
    store = SQLiteStore(str(db_path))
    await store.connect()

    tm = TemplateManager(template_dir=str(template_dir))
    print(f"📋 加载所有模板...")
    templates = tm.load_all_templates()
    print(f"   可用模板: {list(templates.keys())}")

    orchestrator = Orchestrator(store, tm, project_root=str(project_root))

    # 创建工作流
    workflow = await orchestrator.create_workflow(
        level=WorkflowLevel.DEPARTMENT,
        template_id="workflow.devops.deployment",
        data={"name": "Test FileOutputHandler Fix"}
    )

    print(f"✅ 工作流创建成功")
    print(f"   ID: {workflow.id}")
    print(f"   项目目录: {project_root}")

    # 运行第一步
    print(f"\n🚀 运行第一步（p1_architecture）...")
    summary = await orchestrator.run_until_blocked(workflow.id, max_steps=1)

    print(f"\n✅ 执行完成:")
    print(f"   总步骤: {summary.total_steps}")
    print(f"   已完成: {summary.completed_steps}")
    print(f"   状态: {summary.status}")

    # 检查生成的文件
    print(f"\n📁 检查生成的文件:")
    devops_dir = project_root / "devops"
    for file in devops_dir.glob("*.yaml"):
        print(f"   ✓ {file.name}")

    await store.close()

    return summary


if __name__ == "__main__":
    asyncio.run(test_fix())
