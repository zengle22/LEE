#!/usr/bin/env python3
"""
Mock Demo - 演示统一 Engine 接口（不需要真实 API Key）

这个脚本使用 Mock 的 LLMExecutor，不需要真实的 API Key，
用于验证整个系统的正确性。
"""

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

# 添加父目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from flowcore.orchestrator.state_machine import StateMachine
from flowcore.orchestrator.workflow_parser import WorkflowParser
from flowcore.engines.protocol import StepExecutionRequest, StepExecutionResult, ArtifactReference


def print_header(text: str):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60 + "\n")


def print_success(text: str):
    print(f"✅ {text}")


def print_info(text: str):
    print(f"ℹ️  {text}")


async def main():
    """主函数"""
    print_header("Orchestrator 统一 Engine 接口 - Mock 测试")

    print_info("使用 Mock LLM Executor，不需要真实的 API Key")

    # 1. 初始化工作流
    print_info("1. 初始化工作流...")
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

    # 2. 执行步骤 1：编写文档（使用 Mock）
    print_info("2. 执行步骤 1: 编写文档 (Mock)...")

    result1 = await mock_execute_step(
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

    # 3. 执行步骤 2：审查文档（使用 Mock）
    print_info("\n3. 执行步骤 2: 审查文档 (Mock)...")

    result2 = await mock_execute_step(
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

    # 4. 显示结果
    print_header("执行完成")

    print_info("生成的文件:")
    for out in result1.outputs + result2.outputs:
        if out.path:
            file_path = project_dir / out.path
            if file_path.exists():
                size = file_path.stat().st_size
                print(f"  - {out.path} ({size} bytes)")

    print_success("Mock 测试成功！")
    print_info("\n💡 要使用真实的 LLM API，请设置环境变量后运行 run_demo.py")

    return 0


async def mock_execute_step(
    project_dir: str,
    step_id: str,
    workflow: dict,
    state: dict
) -> StepExecutionResult:
    """
    使用 Mock 执行步骤（模拟 LLM 调用）
    """
    from datetime import datetime

    print_info(f"   Engine 类型: llm (Mock)")

    # 模拟执行延迟
    await asyncio.sleep(0.5)

    # 创建模拟的输出文件
    output_dir = Path(project_dir) / "output"
    output_dir.mkdir(exist_ok=True)

    if step_id == "step1_write_doc":
        # 步骤 1: 生成文档
        content = """# Orchestrator 快速入门指南

## 简介

Orchestrator 是一个通用的 AI 工作流编排器。

## 核心特性

1. **强制执行规范**：让工作流规范从"建议"变成"协议"
2. **人类在环控制**：关键决策点强制人工审批
3. **完整审计追踪**：记录所有操作，可追溯、可回放
4. **跨平台支持**：Claude Code、Codex CLI、Gemini Code

## 快速开始

```bash
# 初始化工作流
python -m flowcore.orchestrator init . --workflow workflow.yaml

# 执行步骤
python -m flowcore.orchestrator run-engine . step1
```

## 架构

Orchestrator 采用分层架构：
- 编排层：管理工作流状态
- Engine 层：执行具体任务
- 存储层：文件系统
"""
        output_file = output_dir / "guide.md"
        output_file.write_text(content, encoding="utf-8")

        return StepExecutionResult(
            status="completed",
            outputs=[
                ArtifactReference(
                    id="guide",
                    path="output/guide.md",
                    content_type="text/markdown",
                    summary="生成的 Markdown 文档"
                )
            ],
            messages=[
                {"role": "user", "content": "生成文档"},
                {"role": "assistant", "content": content[:500] + "..."}
            ],
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            duration_seconds=0.5,
            engine_type="llm"
        )

    elif step_id == "step2_review_doc":
        # 步骤 2: 审查文档
        content = """# 文档审查报告

## 总体评价

文档质量：⭐⭐⭐⭐⭐

## 详细评价

### 1. 内容准确性 ⭐⭐⭐⭐⭐
- 内容完整，覆盖所有核心功能
- 提供了清晰的使用示例
- 架构说明准确

### 2. 结构完整性 ⭐⭐⭐⭐⭐
- 章节清晰，层次分明
- 逻辑连贯，易读性强

### 3. 代码质量 ⭐⭐⭐⭐⭐
- 代码示例正确
- 语法高亮正确

### 4. 语言表达 ⭐⭐⭐⭐⭐
- 简洁明了，无冗余
- 专业术语准确

## 改进建议

文档质量已经很高，建议：
1. 添加更多高级用例
2. 补充故障排除部分
3. 添加截图说明

## 结论

文档质量优秀，可以直接发布使用。
"""
        output_file = output_dir / "review.md"
        output_file.write_text(content, encoding="utf-8")

        return StepExecutionResult(
            status="completed",
            outputs=[
                ArtifactReference(
                    id="review",
                    path="output/review.md",
                    content_type="text/markdown",
                    summary="审查报告"
                )
            ],
            messages=[
                {"role": "user", "content": "审查文档"},
                {"role": "assistant", "content": content[:500] + "..."}
            ],
            started_at=datetime.now().isoformat(),
            completed_at=datetime.now().isoformat(),
            duration_seconds=0.5,
            engine_type="llm"
        )

    else:
        return StepExecutionResult(
            status="failed",
            error=f"Unknown step_id: {step_id}"
        )


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
