"""
演示 LLM Executor 在实际工作流中的使用

演示场景：
1. 创建 LLM 驱动的项目
2. 执行代码生成步骤
3. 查看生成的结果
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
from lee.orchestrator.execution.executors import ExecutorFactory


# 测试数据库
DB_PATH = os.path.join(examples_dir, "test_llm_workflow.db")


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 70)
    print(f"  {title}")
    print("=" * 70)


async def main():
    """主测试流程"""
    print_section("🚀 LLM Executor 工作流演示")

    # 清理旧数据库
    if os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print(f"🗑️  清理旧数据库: {DB_PATH}")
        except PermissionError:
            print(f"⚠️  警告: 数据库文件正在使用中，跳过清理")

    # 初始化组件
    db = SQLiteStore(DB_PATH)
    await db.connect()

    state_machine = SimpleStateMachine(db)
    event_bus = MemoryEventBus()
    template_engine = TemplateEngine()

    # 传递模板目录路径
    orchestrator = Orchestrator(
        db=db,
        state_machine=state_machine,
        event_bus=event_bus,
        template_engine=template_engine,
        template_dir=examples_dir,  # 使用 examples 目录
    )

    print("✅ 初始化完成")

    # ========================================================================
    # 演示 1: 直接使用 LLM Executor
    # ========================================================================
    print_section("📝 演示 1: 直接使用 LLM Executor")

    llm_executor = ExecutorFactory.create("llm", profile="zhipu")

    print("\n🔧 执行代码生成任务...")
    result = await llm_executor.execute({
        "prompt": "写一个 Python 函数，实现二分查找算法",
        "system_message": "你是一个专业的程序员",
    })

    print(f"\n状态: {result.get('status')}")
    print(f"模型: {result.get('model')}")

    if result.get('status') == 'completed':
        print(f"\n生成的代码:\n{'-' * 60}")
        print(result.get('generated_text'))
        print('-' * 60)
    else:
        print(f"\n错误: {result.get('error')}")

    # ========================================================================
    # 演示 2: 在工作流中使用 LLM
    # ========================================================================
    print_section("🌳 演示 2: 创建 LLM 驱动的工作流")

    # 创建简单的 LLM 任务工作流
    task = await orchestrator.create_workflow(
        level=WorkflowLevel.TASK,
        template_id="task_llm_code_generation",
        data={
            "task_name": "LLM 代码生成演示",
            "description": "使用 LLM 生成排序算法代码",
        },
    )

    print(f"\n📋 创建任务: {task.id}")
    print(f"   模板: {task.template_id}")
    print(f"   状态: {task.status.value}")

    # 执行第一步
    print(f"\n▶️  执行第一步: 设计代码结构...")
    step_result = await orchestrator.run_step(task.id)

    print(f"   状态: {step_result.status}")
    print(f"   步骤: {step_result.step_id}")
    print(f"   消息: {step_result.message}")

    # 获取任务状态
    state = await orchestrator.get_state(task.id)
    print(f"\n📊 任务状态:")
    print(f"   当前状态: {state.status.value}")
    print(f"   当前步骤: {state.data.get('current_step')}")
    print(f"   已完成步骤: {state.data.get('completed_steps', [])}")

    # 显示最后输出
    if state.data.get('last_output'):
        output = state.data['last_output']
        print(f"\n📄 LLM 输出:")
        print(f"   步骤: {output.get('step_name')}")
        print(f"   执行器: {output.get('executor_type')}")
        if output.get('generated_text'):
            print(f"\n   生成内容预览:")
            text = output['generated_text']
            preview = text[:300] + "..." if len(text) > 300 else text
            print(f"   {preview}")

    # ========================================================================
    # 演示 3: 多步骤 LLM 工作流
    # ========================================================================
    print_section("🔄 演示 3: 执行多个 LLM 步骤")

    # 继续执行第二步
    print(f"\n▶️  执行第二步: 实现数据模型...")
    step_result = await orchestrator.run_step(task.id)

    print(f"   状态: {step_result.status}")
    print(f"   步骤: {step_result.step_id}")

    # 继续执行第三步
    print(f"\n▶️  执行第三步: 实现 API 接口...")
    step_result = await orchestrator.run_step(task.id)

    print(f"   状态: {step_result.status}")
    print(f"   步骤: {step_result.step_id}")

    # 最终状态
    state = await orchestrator.get_state(task.id)
    print(f"\n📊 最终状态:")
    print(f"   状态: {state.status.value}")
    print(f"   完成步骤数: {len(state.data.get('completed_steps', []))}")

    # ========================================================================
    # 演示 4: 比较不同配置的性能
    # ========================================================================
    print_section("⚡ 演示 4: 不同配置的性能对比")

    import time

    profiles = ["zhipu"]  # 只测试可用的配置

    for profile in profiles:
        print(f"\n🔧 测试配置: {profile}")

        executor = ExecutorFactory.create("llm", profile=profile)

        start = time.time()
        result = await executor.execute({
            "prompt": "2 + 2 = ?",
            "system_message": "你是数学助手",
        })
        elapsed = time.time() - start

        print(f"   耗时: {elapsed:.2f} 秒")
        print(f"   状态: {result.get('status')}")

        if result.get('status') == 'completed':
            print(f"   响应: {result.get('generated_text')[:50]}...")

    # ========================================================================
    # 总结
    # ========================================================================
    print_section("📈 演示总结")

    print("\n✅ LLM Executor 功能验证:")
    print("   - 直接调用 LLM API")
    print("   - 在工作流中使用 LLM")
    print("   - 多步骤 LLM 任务执行")
    print("   - 配置文件管理")
    print("   - 性能监控")

    print("\n📝 支持的操作:")
    print("   - 代码生成")
    print("   - 文档编写")
    print("   - 代码审查")
    print("   - 问题解答")

    print("\n🎯 使用场景:")
    print("   - 自动化代码生成")
    print("   - 文档自动生成")
    print("   - 代码辅助开发")
    print("   - 智能工作流")

    print("\n" + "=" * 70)
    print("  ✅ 演示完成！")
    print("=" * 70)

    # 关闭数据库
    await db.close()


if __name__ == "__main__":
    asyncio.run(main())
