"""
PM Agent Demo - 演示 PM Agent 如何使用 Orchestrator 工具

这个脚本模拟了一个 PM Agent 的工作流程：
1. 查看当前状态
2. 决定执行某个步骤
3. 查看执行结果
4. 继续下一步决策

注意：这是一个演示脚本，展示 PM Agent 的工具使用方式。
实际使用时，PM Agent 应该是一个 AI 模型，通过工具调用使用这些接口。
"""

import asyncio
import json
from flowcore.orchestrator import (
    orchestrator_get_state,
    orchestrator_run_step,
    orchestrator_next,
    orchestrator_list_steps,
)


def print_section(title: str):
    """打印分节标题"""
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def print_state_summary(state: dict):
    """打印状态摘要"""
    print(f"Workflow: {state.get('workflow_name')} ({state.get('workflow_id')})")
    print(f"Run ID: {state.get('run_id')}")
    print(f"Progress: {state.get('completed_steps')}/{state.get('total_steps')} steps completed")
    print(f"Ready steps: {', '.join(state.get('ready_steps', [])) or 'None'}")


async def demo_pm_agent_workflow():
    """
    演示 PM Agent 的工作流程
    """
    project_dir = "."

    print_section("PM Agent Demo - 工作流执行演示")

    # 1. 获取初始状态
    print("\n[PM Agent] 查看当前状态...")
    state = orchestrator_get_state(project_dir)

    if "error" in state:
        print(f"Error: {state['error']}")
        return

    print_state_summary(state)

    # 2. 列出所有步骤
    print("\n[PM Agent] 列出所有步骤...")
    steps = orchestrator_list_steps(project_dir)
    for step in steps:
        status_icon = {"pending": "○", "completed": "✓", "failed": "✗"}.get(step["status"], "?")
        ready_icon = " [READY]" if step["is_ready"] else ""
        print(f"  {status_icon} {step['id']}: {step['name']}{ready_icon}")

    # 3. 模拟 PM Agent 决策：执行第一个就绪步骤
    print("\n[PM Agent] 决策：执行 'generate_code' 步骤")
    decision = {
        "action": "run_step",
        "step_id": "generate_code",
        "reason": "这是第一个就绪步骤，应该先生成代码"
    }
    print(f"  Decision: {json.dumps(decision, ensure_ascii=False)}")

    # 注意：实际执行会失败，因为需要 API key
    # 这里只是演示工具调用流程
    print("\n[PM Agent] 执行步骤...")
    result = await orchestrator_run_step(project_dir, "generate_code")

    if result.get("status") == "completed":
        print(f"  ✓ Step completed successfully")
        print(f"  Outputs: {result.get('outputs', [])}")
    elif result.get("status") == "failed":
        print(f"  ✗ Step failed: {result.get('error')}")
        print(f"  (这是预期的，因为需要设置 API key)")

    # 4. 查看最新状态
    print("\n[PM Agent] 查看最新状态...")
    state = orchestrator_get_state(project_dir)
    print_state_summary(state)

    # 5. 演示 orchestrator_next（自动选择下一步）
    print("\n[PM Agent] 使用 orchestrator_next 自动执行下一步...")
    result = await orchestrator_next(project_dir)
    print(f"  Result: {result.get('status')}")
    if result.get("step_id"):
        print(f"  Step ID: {result['step_id']}")

    print_section("演示完成")
    print("\n提示：")
    print("  1. 设置 OPENAI_API_KEY 环境变量以实际执行 LLM 步骤")
    print("  2. 查看 docs/PM_AGENT_PROTOCOL.md 了解 PM Agent 协议")
    print("  3. 查看 flowcore/orchestrator/pm_agent_tools.py 了解工具实现")


def demo_sync_api():
    """
    演示同步 API 的使用
    """
    print_section("同步 API 演示")

    from flowcore.orchestrator import (
        orchestrator_run_step_sync,
        orchestrator_next_sync,
    )

    print("\n[PM Agent] 使用同步 API...")
    state = orchestrator_get_state(".")
    print(f"Ready steps: {state.get('ready_steps', [])}")


if __name__ == "__main__":
    # 异步演示
    asyncio.run(demo_pm_agent_workflow())

    # 同步演示
    # demo_sync_api()
