"""
模板驱动工作流执行测试

测试完整的 run_step 逻辑：
1. 模板解析
2. 步骤依赖处理
3. Executor 集成
4. 自动创建子工作流
"""

import asyncio
import os
import sys
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
examples_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, src_dir)

from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.core.state_machine import SimpleStateMachine
from lee.orchestrator.core.event_bus import MemoryEventBus
from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.execution.orchestrator import Orchestrator


# 测试数据库
DB_PATH = os.path.join(examples_dir, "test_template_execution.db")


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def print_workflow_tree(orchestrator: Orchestrator, workflow_id: str, indent: int = 0):
    """打印工作流树"""
    state = await orchestrator.get_state(workflow_id)
    prefix = "  " * indent

    # 根据层级显示不同图标
    icons = {
        WorkflowLevel.PROJECT: "🎯",
        WorkflowLevel.DEPARTMENT: "🏢",
        WorkflowLevel.TASK: "📋",
    }
    icon = icons.get(state.level, "📄")

    # 状态图标
    status_icons = {
        WorkflowStatus.PENDING: "⏳",
        WorkflowStatus.RUNNING: "▶️",
        WorkflowStatus.COMPLETED: "✅",
        WorkflowStatus.FAILED: "❌",
        WorkflowStatus.PAUSED: "⏸️",
    }
    status_icon = status_icons.get(state.status, "")

    print(f"{prefix}{icon} {workflow_id} ({state.level.value}) {status_icon}")
    print(f"{prefix}   模板: {state.template_id or 'N/A'}")

    # 递归打印子工作流
    for child_id in state.children:
        await print_workflow_tree(orchestrator, child_id, indent + 1)


async def main():
    """主测试流程"""
    print_section("🚀 LEE Orchestrator - 模板驱动执行测试")

    # 清理旧数据库
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"🗑️  清理旧数据库: {DB_PATH}")
        except PermissionError:
            print(f"⚠️  警告: 数据库文件正在使用中，跳过清理: {DB_PATH}")

    # 初始化组件
    db = SQLiteStore(DB_PATH)
    await db.connect()

    state_machine = SimpleStateMachine(db)
    event_bus = MemoryEventBus()
    template_engine = TemplateEngine()

    # 传递模板目录路径（当前目录就是 examples 目录）
    orchestrator = Orchestrator(
        db=db,
        state_machine=state_machine,
        event_bus=event_bus,
        template_engine=template_engine,
        template_dir=examples_dir,  # 使用绝对路径
    )

    print("✅ 初始化完成")

    # ========================================================================
    # 测试 1: 模板加载
    # ========================================================================
    print_section("📝 测试 1: 模板加载")

    template_manager = orchestrator.template_manager

    # 测试获取模板
    templates_to_test = [
        "project_main",
        "dept_development",
        "dept_testing",
        "task_backend_api",
        "task_frontend_ui",
        "task_integration_test",
    ]

    for template_id in templates_to_test:
        template = template_manager.get_template_content(template_id)
        if template:
            name = template.get("name", "N/A")
            print(f"  ✅ {template_id}: {name}")
        else:
            print(f"  ❌ {template_id}: 未找到")

    # ========================================================================
    # 测试 2: 创建三层工作流（从模板自动创建）
    # ========================================================================
    print_section("🌳 测试 2: 创建三层嵌套工作流")

    # 创建 L1 项目 - 应该自动创建 L2 部门和 L3 任务
    project = await orchestrator.create_workflow(
        level=WorkflowLevel.PROJECT,
        template_id="project_main",
        data={"project_name": "AI ChatBot 测试项目"},
    )

    print(f"🎯 创建 L1 项目: {project.id}")
    print(f"   模板: {project.template_id}")
    print(f"   状态: {project.status.value}")

    # 获取所有工作流
    all_workflows = await db.get_all_instances()
    print(f"\n📊 工作流统计:")
    print(f"   总数: {len(all_workflows)}")

    for level in [WorkflowLevel.PROJECT, WorkflowLevel.DEPARTMENT, WorkflowLevel.TASK]:
        count = sum(1 for w in all_workflows if w.level == level)
        print(f"   {level.value}: {count} 个")

    # ========================================================================
    # 测试 3: 显示工作流树
    # ========================================================================
    print_section("🌲 测试 3: 完整工作流树")

    await print_workflow_tree(orchestrator, project.id)

    # ========================================================================
    # 测试 4: 执行任务步骤（依赖解析）
    # ========================================================================
    print_section("⚙️ 测试 4: 执行任务步骤（依赖解析）")

    # 找到后端 API 开发任务
    all_workflows = await db.get_all_instances()
    backend_task = None
    for wf in all_workflows:
        if wf.level == WorkflowLevel.TASK and "backend" in wf.template_id:
            backend_task = wf
            break

    if backend_task:
        print(f"📋 找到任务: {backend_task.id}")
        print(f"   模板: {backend_task.template_id}")

        # 获取模板步骤
        steps = template_manager.get_steps(backend_task.template_id)
        print(f"\n   步骤列表:")
        for i, step in enumerate(steps, 1):
            name = step.get("name", "N/A")
            deps = step.get("depends_on", [])
            executor = step.get("executor", "llm")
            deps_str = f" (依赖: {deps})" if deps else ""
            print(f"   {i}. {name} [{executor}]{deps_str}")

        # 执行第一个步骤
        print(f"\n   执行第一个步骤...")
        result = await orchestrator.run_step(backend_task.id)

        print(f"   状态: {result.status}")
        print(f"   消息: {result.message}")
        print(f"   当前步骤: {result.step_id}")

        if result.next_steps:
            print(f"   可执行的下一步: {result.next_steps}")

        # 执行第二个步骤（依赖第一个）
        print(f"\n   执行第二个步骤（依赖第一个完成）...")
        result2 = await orchestrator.run_step(backend_task.id)
        print(f"   状态: {result2.status}")
        print(f"   消息: {result2.message}")

    # ========================================================================
    # 测试 5: 状态转换
    # ========================================================================
    print_section("🔄 测试 5: 状态转换")

    if backend_task:
        state = await orchestrator.get_state(backend_task.id)
        print(f"任务状态: {state.status.value}")
        print(f"完成的步骤: {state.data.get('completed_steps', [])}")

        if state.data.get("last_output"):
            print(f"\n最后输出:")
            output = state.data["last_output"]
            print(f"  步骤: {output.get('step_name')}")
            print(f"  执行器: {output.get('executor_type')}")

    # ========================================================================
    # 测试 6: 子工作流查询
    # ========================================================================
    print_section("🔍 测试 6: 子工作流查询")

    # 获取项目的所有子工作流
    project_state = await orchestrator.get_state(project.id)
    print(f"🎯 项目: {project.id}")
    print(f"   子工作流数量: {len(project_state.children)}")

    for child_id in project_state.children:
        child_state = await orchestrator.get_state(child_id)
        print(f"\n🏢 {child_id}")
        print(f"   类型: {child_state.level.value}")
        print(f"   状态: {child_state.status.value}")
        print(f"   子任务数量: {len(child_state.children)}")

        for grandchild_id in child_state.children:
            grandchild_state = await orchestrator.get_state(grandchild_id)
            print(f"     📋 {grandchild_id} - {grandchild_state.status.value}")

    # ========================================================================
    # 测试 7: 完成条件检查
    # ========================================================================
    print_section("✅ 测试 7: 完成条件检查")

    # 检查模板的完成条件
    test_templates = ["task_backend_api", "dept_development", "project_main"]

    for template_id in test_templates:
        criteria = template_manager.get_completion_criteria(template_id)
        template = template_manager.get_template_content(template_id)
        name = template.get("name", template_id) if template else template_id

        print(f"\n{name}:")
        if criteria:
            for key, value in criteria.items():
                print(f"  - {key}: {value}")
        else:
            print(f"  - 无特定完成条件")

    # ========================================================================
    # 总结
    # ========================================================================
    print_section("📈 测试总结")

    all_workflows = await db.get_all_instances()

    print(f"工作流总数: {len(all_workflows)}")

    # 按层级统计
    for level in [WorkflowLevel.PROJECT, WorkflowLevel.DEPARTMENT, WorkflowLevel.TASK]:
        workflows = [w for w in all_workflows if w.level == level]
        count = len(workflows)
        print(f"\n{level.value.upper()} ({count} 个):")

        for wf in workflows:
            completed = len(wf.data.get("completed_steps", []))
            print(f"  - {wf.id}: {wf.status.value} ({completed} 步骤完成)")

    # 按状态统计
    print(f"\n状态分布:")
    status_count = {}
    for wf in all_workflows:
        status = wf.status.value
        status_count[status] = status_count.get(status, 0) + 1

    for status, count in sorted(status_count.items()):
        print(f"  - {status}: {count} 个")

    print("\n" + "=" * 60)
    print("  ✅ 所有测试完成！")
    print("=" * 60)

    # 关闭数据库
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
