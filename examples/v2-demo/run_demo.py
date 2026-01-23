"""
V2 架构端到端示例脚本

展示如何使用新的 Engine 接口来执行工作流。
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from flowcore.engines.base import EngineRegistry
from flowcore.engines.protocol import StepExecutionRequest
import yaml


async def main():
    """主函数"""
    print("=" * 40)
    print("  V2 Architecture Demo")
    print("=" * 40)
    print()

    # 项目目录
    project_dir = Path(__file__).parent

    # 1. 加载工作流
    workflow_path = project_dir / "ai-spec" / "workflows" / "demo" / "workflow.yaml"
    with open(workflow_path) as f:
        workflow = yaml.safe_load(f)

    print(f"Workflow: {workflow['id']}")
    print(f"Name: {workflow['name']}")
    print()

    # 2. 执行 Step 1: generate_code (Agent)
    print("Step 1: generate_code")
    print("  Engine: llm")

    # 加载 Agent 规范
    agent_spec_path = project_dir / "ai-spec" / "agents" / "developer" / "agent.yaml"
    with open(agent_spec_path) as f:
        agent_spec = yaml.safe_load(f)

    # 创建执行请求
    request = StepExecutionRequest(
        project_dir=str(project_dir),
        step_id="generate_code",
        run_id="RUN-DEMO-001",
        agent_spec=agent_spec,
        context={
            "step_description": "生成一个简单的 Python 函数，保存到 src/demo.py。函数名为 add(a: int, b: int) -> int，返回 a + b。",
        }
    )

    # 创建并执行 Executor
    try:
        executor = EngineRegistry.create(agent_spec, str(project_dir))
        result = await executor.execute(request)

        print(f"  Status: {result.status}")
        if result.outputs:
            for output in result.outputs:
                print(f"  Output: {output.path}")

        # 如果失败，显示错误
        if result.status == "failed":
            print(f"  Error: {result.error}")
            print()
            print("⚠️  Step 1 failed. This is expected if OPENAI_API_KEY is not set.")
            print("   To fix: export OPENAI_API_KEY='sk-...'")
            return
    except Exception as e:
        print(f"  Status: failed")
        print(f"  Error: {e}")
        print()
        print("⚠️  Step 1 failed. This is expected if OPENAI_API_KEY is not set.")
        print("   To fix: export OPENAI_API_KEY='sk-...'")
        return

    print()

    # 3. 执行 Step 2: run_unit_tests (Skill)
    print("Step 2: run_unit_tests")
    print("  Engine: shell")

    # 加载 Skill 规范
    skill_spec_path = project_dir / "ai-spec" / "skills" / "ci.run_tests.yaml"
    with open(skill_spec_path) as f:
        skill_spec = yaml.safe_load(f)

    # 创建执行请求
    request = StepExecutionRequest(
        project_dir=str(project_dir),
        step_id="run_unit_tests",
        run_id="RUN-DEMO-001",
        agent_spec=skill_spec,
        context={}
    )

    # 创建并执行 Executor
    executor = EngineRegistry.create(skill_spec, str(project_dir))
    result = await executor.execute(request)

    print(f"  Status: {result.status}")
    if result.outputs:
        for output in result.outputs:
            print(f"  Output: {output.path}")
    print()

    # 4. 完成
    print("=" * 40)
    if result.status == "completed":
        print("  ✅ All steps completed!")
    else:
        print("  ⚠️  Some steps failed. Check the output above.")
    print("=" * 40)


if __name__ == "__main__":
    # 检查环境变量
    if not os.getenv("OPENAI_API_KEY"):
        print("⚠️  Warning: OPENAI_API_KEY not set")
        print("   Step 1 (LLM) will fail without it.")
        print("   Set it with: export OPENAI_API_KEY='sk-...'")
        print()
        response = input("Continue anyway? (y/n): ")
        if response.lower() != "y":
            sys.exit(0)

    asyncio.run(main())
