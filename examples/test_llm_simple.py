"""
LLM Executor 简单测试

测试 LLM 执行器的基本功能
"""

import asyncio
import os
import sys
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.executors import ExecutorFactory


async def test_zhipu_llm():
    """测试智谱 LLM"""
    print("=" * 60)
    print("测试智谱 GLM-4-Flash")
    print("=" * 60)

    executor = ExecutorFactory.create("llm", profile="zhipu")

    result = await executor.execute({
        "prompt": "用一句话介绍你自己",
        "system_message": "你是智谱 AI 开发的 GLM-4 大语言模型",
    })

    print(f"\n状态: {result.get('status')}")
    print(f"模型: {result.get('model')}")
    print(f"Provider: {result.get('provider')}")

    if result.get('status') == 'completed':
        print(f"\n响应:\n{result.get('generated_text')}")
    else:
        print(f"\n错误: {result.get('error')}")


async def test_code_generation():
    """测试代码生成"""
    print("\n" + "=" * 60)
    print("测试代码生成")
    print("=" * 60)

    executor = ExecutorFactory.create("llm", profile="zhipu")

    result = await executor.execute({
        "prompt": "写一个 Python 函数计算斐波那契数列的第 n 项",
        "system_message": "你是一个专业的程序员",
        "temperature": 0.3,
        "max_tokens": 2000,
    })

    print(f"\n状态: {result.get('status')}")

    if result.get('status') == 'completed':
        print(f"\n生成的代码:\n{result.get('generated_text')}")
    else:
        print(f"\n错误: {result.get('error')}")


async def main():
    """主函数"""
    print("🚀 LEE Orchestrator - LLM Executor 测试\n")

    await test_zhipu_llm()
    await test_code_generation()

    print("\n" + "=" * 60)
    print("✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
