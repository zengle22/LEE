#!/usr/bin/env python3
"""
端到端 Demo - 演示统一 Engine 接口的完整流程

这个脚本展示了如何使用 Orchestrator 的统一 Engine 接口
执行一个完整的工作流。

前提条件：
1. 设置 OPENAI_API_KEY 环境变量
2. 安装依赖：pip install aiohttp pyyaml

使用方式：
    cd examples/unified-engine-demo
    export OPENAI_API_KEY="sk-..."
    python run_demo.py
"""

import asyncio
import os
import sys
from pathlib import Path

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# 导入 Orchestrator 模块
from flowcore.orchestrator.state_machine import StateMachine
from flowcore.orchestrator.workflow_parser import WorkflowParser

# 导入 Engine 模块
from flowcore.engines.protocol import StepExecutionRequest, StepExecutionResult
from flowcore.engines.base import EngineRegistry


def print_header(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_success(text: str):
    print(f"✅ {text}")


def print_error(text: str):
    print(f"❌ {text}")


def print_info(text: str):
    print(f"ℹ️  {text}")


async def main():
    """主函数"""
    print_header("Orchestrator 统一 Engine 接口 - 端到端 Demo")

    # 1. 检查环境
    print_info("1. 检查环境...")
    if not os.getenv("OPENAI_API_KEY"):
        print_error("OPENAI_API_KEY 环境变量未设置")
        print_info("请设置: export OPENAI_API_KEY='sk-...'")
        return 1

    print_success("环境检查通过")

    # 2. 初始化工作流
    print_info("2. 初始化工作流...")
    project_dir = Path(__file__).parent

    # 创建输出目录
    output_dir = project_dir / "output"
    output_dir.mkdir(exist_ok=True)

    # 加载 workflow
    workflow_file = project_dir / "workflow.yaml"
    if not workflow_file.exists():
        print_error(f"workflow.yaml 不存在: {workflow_file}")
        return 1

    parser = WorkflowParser(str(workflow_file))
    workflow = parser.workflow

    # 初始化状态机
    sm = StateMachine(str(project_dir))
    run_id = sm.init(workflow)

    print_success(f"工作流初始化完成 (Run ID: {run_id})")

    # 3. 执行步骤 1：编写文档
    print_info("3. 执行步骤 1: 编写文档...")

    result1 = await execute_step(
        project_dir=str(project_dir),
        step_id="step1_write_doc",
        workflow=workflow,
        state=sm.load()
    )

    if result1.status != "completed":
        print_error(f"步骤 1 执行失败: {result1.error}")
        return 1

    print_success(f"步骤 1 完成")
    print(f"   生成的产物: {[out.path for out in result1.outputs]}")

    # 完成步骤
    sm.complete_step("step1_write_doc", result1.get_output_paths())

    # 4. 执行步骤 2：审查文档
    print_info("\n4. 执行步骤 2: 审查文档...")

    result2 = await execute_step(
        project_dir=str(project_dir),
        step_id="step2_review_doc",
        workflow=workflow,
        state=sm.load()
    )

    if result2.status != "completed":
        print_error(f"步骤 2 执行失败: {result2.error}")
        return 1

    print_success(f"步骤 2 完成")
    print(f"   生成的产物: {[out.path for out in result2.outputs]}")

    # 完成步骤
    sm.complete_step("step2_review_doc", result2.get_output_paths())

    # 5. 显示结果
    print_header("执行完成")

    print_info("生成的文件:")
    for out in result1.outputs + result2.outputs:
        if out.path:
            file_path = project_dir / out.path
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  - {out.path} ({size} bytes)")

    print_info("查看生成的文档:")
    print(f"  cat {project_dir}/output/guide.md")
    print(f"  cat {project_dir}/output/review.md")

    print_success("Demo 执行成功！")

    return 0


async def execute_step(
    project_dir: str,
    step_id: str,
    workflow: dict,
    state: dict
) -> StepExecutionResult:
    """
    使用统一 Engine 接口执行步骤

    Args:
        project_dir: 项目目录
        step_id: 步骤 ID
        workflow: 工作流定义
        state: 状态

    Returns:
        执行结果
    """
    # 1. 解析步骤定义
    step_data = None
    for step in workflow.get("steps", []):
        if step.get("id") == step_id:
            step_data = step
            break

    if not step_data:
        raise ValueError(f"Step '{step_id}' not found in workflow")

    # 2. 构建 Agent 规范
    agent_spec = {
        "id": step_data.get("run", ""),
        "name": step_data.get("name", ""),
        "engine": step_data.get("engine", {"type": "llm"}),
        "system_prompt": step_data.get("system_prompt", ""),
        "instructions": step_data.get("instructions", []),
        "outputs": step_data.get("outputs", [])
    }

    # 3. 构建执行上下文
    context = {
        "step_description": step_data.get("description", ""),
        "inputs": [],
        "contracts": {},
        "project_meta": {
            "name": workflow.get("name", ""),
            "id": workflow.get("id", "")
        }
    }

    # 4. 构建执行请求
    request = StepExecutionRequest(
        project_dir=project_dir,
        step_id=step_id,
        run_id=state["run_id"],
        agent_spec=agent_spec,
        context=context,
        timeout_seconds=300  # 5 分钟超时
    )

    # 5. 创建 Executor
    print_info(f"   Engine 类型: {agent_spec['engine']['type']}")
    executor = EngineRegistry.create(agent_spec, project_dir)

    # 6. 执行
    result = await executor.execute(request)

    return result


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(1)
    except Exception as e:
        print_error(f"Demo 执行失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
