"""
LLM 和 MetaGPT 执行器测试脚本

测试内容：
1. LLM Executor - 使用配置文件调用 LLM API
2. MetaGPT Executor - 测试 MetaGPT 集成
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


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


async def test_llm_executor():
    """测试 LLM 执行器"""
    print_section("📝 测试 1: LLM Executor")

    # 测试不同的配置文件
    profiles = ["antigravity", "zhipu", "agent.prd", "agent.dev"]

    for profile in profiles:
        print(f"\n🔧 测试配置: {profile}")

        try:
            # 创建执行器
            executor = ExecutorFactory.create("llm", profile=profile)

            # 执行任务
            result = await executor.execute({
                "prompt": "请用一句话介绍 Python 编程语言。",
                "system_message": "你是一个编程助手。",
            })

            # 显示结果
            print(f"  状态: {result.get('status')}")
            print(f"  模型: {result.get('model')}")
            print(f"  Provider: {result.get('provider')}")

            if result.get('status') == 'completed':
                print(f"  响应: {result.get('generated_text')[:100]}...")
            elif result.get('error'):
                print(f"  错误: {result.get('error')}")

        except Exception as e:
            print(f"  ❌ 错误: {str(e)}")


async def test_llm_with_complex_task():
    """测试 LLM 执行器 - 复杂任务"""
    print_section("🧠 测试 2: LLM 复杂任务")

    try:
        # 使用 agent.dev 配置（适合开发任务）
        executor = ExecutorFactory.create("llm", profile="agent.dev")

        # 执行代码生成任务
        result = await executor.execute({
            "prompt": "请写一个 Python 函数，实现快速排序算法。",
            "system_message": "你是一个专业的程序员，擅长编写高质量的代码。",
        })

        print(f"状态: {result.get('status')}")
        print(f"模型: {result.get('model')}")

        if result.get('status') == 'completed':
            print(f"\n生成的代码:\n{result.get('generated_text')[:500]}...")
        elif result.get('error'):
            print(f"错误: {result.get('error')}")

    except Exception as e:
        print(f"❌ 错误: {str(e)}")


async def test_metagpt_executor():
    """测试 MetaGPT 执行器"""
    print_section("🤖 测试 3: MetaGPT Executor")

    try:
        # 检查 MetaGPT 是否安装
        from lee.orchestrator.execution.metagpt_executor import METAGPT_AVAILABLE

        if not METAGPT_AVAILABLE:
            print("⚠️  MetaGPT 未安装")
            print("   安装命令: pip install metagpt")
            return

        # 创建 MetaGPT 执行器
        llm_config = {
            "api_key": "sk-2988e892730744ccafde80aac9ced361",  # antigravity
            "model": "gemini-3-flash",
            "base_url": "http://127.0.0.1:8045/v1",
            "investment": 5.0,
            "max_rounds": 3,
        }

        executor = ExecutorFactory.create(
            "metagpt",
            role="Developer",
            llm_config=llm_config
        )

        print(f"✅ MetaGPT 执行器创建成功")
        print(f"   角色: Developer")

        # 执行代码实现任务
        print(f"\n🚀 执行代码实现任务...")

        result = await executor.execute({
            "task_type": "code_implementation",
            "requirement": "创建一个简单的 Todo List 应用，使用 Python 和 Flask",
            "workspace": "./test_metagpt_workspace",
        })

        print(f"\n结果:")
        print(f"  状态: {result.get('status')}")
        print(f"  工作目录: {result.get('workspace')}")
        print(f"  轮次: {result.get('rounds')}")
        print(f"  耗时: {result.get('duration_seconds'):.2f} 秒")

        if result.get('summary_path'):
            print(f"  摘要: {result.get('summary_path')}")

        if result.get('error'):
            print(f"  错误: {result.get('error')}")

    except ImportError as e:
        print(f"⚠️  MetaGPT 未安装: {str(e)}")
    except Exception as e:
        print(f"❌ 错误: {str(e)}")


async def test_executor_info():
    """测试执行器信息获取"""
    print_section("ℹ️  测试 4: 执行器信息")

    # LLM 执行器信息
    print("\n📝 LLM Executor 信息:")
    for profile in ["antigravity", "zhipu"]:
        try:
            executor = ExecutorFactory.create("llm", profile=profile)
            if hasattr(executor, '_executor'):
                info = executor._executor.get_info()
                print(f"\n  配置: {profile}")
                print(f"    类型: {info.get('type')}")
                print(f"    Provider: {info.get('provider')}")
                print(f"    模型: {info.get('model')}")
                print(f"    Base URL: {info.get('base_url')}")
        except Exception as e:
            print(f"\n  配置: {profile} - 错误: {str(e)}")

    # MetaGPT 执行器信息
    print("\n🤖 MetaGPT Executor 信息:")
    try:
        from lee.orchestrator.execution.metagpt_executor import METAGPT_AVAILABLE

        if METAGPT_AVAILABLE:
            executor = ExecutorFactory.create("metagpt")
            if hasattr(executor, '_executor'):
                info = executor._executor.get_info()
                print(f"  类型: {info.get('type')}")
                print(f"  角色: {info.get('role')}")
                print(f"  LLM 配置: {info.get('llm_config')}")
        else:
            print("  MetaGPT 未安装")
    except Exception as e:
        print(f"  错误: {str(e)}")


async def main():
    """主测试流程"""
    print_section("🚀 LEE Orchestrator - LLM & MetaGPT 执行器测试")

    # 运行测试
    await test_executor_info()
    await test_llm_executor()
    await test_llm_with_complex_task()
    await test_metagpt_executor()

    # 总结
    print_section("📈 测试总结")

    print("\n✅ LLM Executor")
    print("   - 支持多种配置文件（antigravity, zhipu, agent.prd, agent.dev）")
    print("   - 支持环境变量替换")
    print("   - 自动重试机制")

    print("\n🤖 MetaGPT Executor")
    print("   - 支持代码实现任务")
    print("   - 支持自定义 LLM 配置")

    print("\n" + "=" * 60)
    print("  ✅ 测试完成！")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
