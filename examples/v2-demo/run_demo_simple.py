"""
V2 架构端到端示例脚本 - 简化版

直接测试 Shell Engine，不依赖 API key。
"""

import asyncio
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
    print("  V2 Architecture Demo (Shell Only)")
    print("=" * 40)
    print()

    # 项目目录
    project_dir = Path(__file__).parent

    # 执行 Step: run_unit_tests (Skill)
    print("Step: run_unit_tests")
    print("  Engine: shell")
    print()

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

    print(f"Status: {result.status}")
    print()

    if result.outputs:
        print("Outputs:")
        for output in result.outputs:
            print(f"  - {output.path}")
            if output.summary:
                print(f"    ({output.summary})")

    # 显示最后几条消息
    if result.messages:
        print()
        print("Messages (last 3):")
        for msg in result.messages[-3:]:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 截断过长的内容
            if len(content) > 100:
                content = content[:97] + "..."
            print(f"  [{role}]: {content}")

    print()
    print("=" * 40)
    if result.status == "completed":
        print("  ✅ Test passed!")
    else:
        print("  ⚠️  Test failed.")
        if result.error:
            print(f"  Error: {result.error}")
    print("=" * 40)


if __name__ == "__main__":
    asyncio.run(main())
