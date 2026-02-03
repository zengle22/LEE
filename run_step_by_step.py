"""
Run workflow step by step with detailed error logging
"""
import asyncio
import sys
import traceback
from pathlib import Path

# Add LEE src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))
from lee.orchestrator.storage.models import WorkflowLevel
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


async def run_step_by_step():
    project_root = Path("e:/projects/ai-marathon-coach").resolve()
    lee_root = Path("E:/ai/LEE").resolve()
    db_path = project_root / "devops" / "orchestrator_new.db"
    template_dir = lee_root / "spec-global" / "departments" / "devops" / "workflows"

    print(f"📂 项目根目录: {project_root}")
    print(f"📂 模板目录: {template_dir}")

    # 初始化
    store = SQLiteStore(str(db_path))
    await store.connect()

    tm = TemplateManager(template_dir=str(template_dir))
    templates = tm.load_all_templates()
    print(f"📋 可用模板: {list(templates.keys())}")

    if not templates:
        print("❌ 没有找到任何模板！")
        print(f"   模板目录: {template_dir}")
        print(f"   模板目录内容: {list(template_dir.rglob('*.yaml')) if template_dir.exists() else '不存在'}")
        await store.close()
        return

    orchestrator = Orchestrator(store, tm, project_root=str(project_root))

    # 创建工作流
    workflow = await orchestrator.create_workflow(
        level=WorkflowLevel.DEPARTMENT,
        template_id="workflow.devops.deployment",
        data={"name": "Step by Step Test"}
    )

    print(f"\n✅ 工作流创建成功: {workflow.id}")

    # 运行第一步：p1_architecture
    print(f"\n🚀 运行第一步: p1_architecture")
    try:
        summary = await orchestrator.run_until_blocked(workflow.id, max_steps=1)
        print(f"   完成: {summary.completed_steps}/{summary.total_steps}")
        print(f"   状态: {summary.status}")

        # 获取详细状态
        state = await orchestrator.get_state(workflow.id)
        print(f"   工作流状态: {state.status.value}")
        print(f"   当前步骤: {state.current_step}")

        # 查看任务执行记录
        if state.status.value == "failed":
            executions = await store.get_task_executions(workflow.id)
            for exe in executions:
                print(f"   任务执行: {exe.step_id} - {exe.status.value}")
                if exe.error_message:
                    print(f"      错误: {exe.error_message}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()

    # 检查生成的文件
    print(f"\n📁 检查生成的文件:")
    devops_dir = project_root / "devops"
    yaml_files = list(devops_dir.glob("*.yaml"))
    md_files = list(devops_dir.glob("*.md"))
    print(f"   YAML 文件: {[f.name for f in yaml_files]}")
    print(f"   MD 文件: {[f.name for f in md_files]}")

    # 运行第二步：p2_infra_code
    print(f"\n🚀 运行第二步: p2_infra_code")
    try:
        summary = await orchestrator.run_until_blocked(workflow.id, max_steps=1)
        print(f"   完成: {summary.completed_steps}/{summary.total_steps}")
        print(f"   状态: {summary.status}")

        state = await orchestrator.get_state(workflow.id)
        print(f"   工作流状态: {state.status.value}")

    except Exception as e:
        print(f"❌ 错误: {e}")
        traceback.print_exc()

    # 检查infra目录
    print(f"\n📁 检查infra目录:")
    infra_dir = devops_dir / "infra"
    if infra_dir.exists():
        print(f"   ✅ infra/ 目录存在")
        for item in sorted(infra_dir.rglob("*")):
            if item.is_file():
                print(f"      {item.relative_to(infra_dir)}")
    else:
        print(f"   ❌ infra/ 目录不存在")

    await store.close()


if __name__ == "__main__":
    asyncio.run(run_step_by_step())
