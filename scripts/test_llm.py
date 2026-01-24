#!/usr/bin/env python3
"""
测试 LLM Executor
验证本地反代服务是否正常工作
"""

import os
import sys
import asyncio
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 加载环境
from scripts.setup_env import load_env, setup_pythonpath
load_env()
setup_pythonpath()

from flowcore.engines.llm.executor import LLMExecutor
from flowcore.engines.protocol import StepExecutionRequest


def create_test_request(project_dir: str, step_id: str = "test_step") -> StepExecutionRequest:
    """创建测试请求"""
    return StepExecutionRequest(
        project_dir=project_dir,
        step_id=step_id,
        run_id="test-run-001",
        agent_spec={
            "id": "test.agent",
            "kind": "agent",
            "version": "1.0",
            "engine": {
                "type": "llm",
                "provider": "custom",
                "base_url": os.getenv("OPENAI_BASE_URL"),
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL"),
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "system_prompt": "你是一个有帮助的助手。",
            "user_prompt": "请用一句话介绍你自己。"
        },
        context={}
    )


async def test_antigravity_proxy():
    """测试 antigravity 反代服务"""
    print("\n" + "=" * 60)
    print("🧪 测试 1: Antigravity 反代服务")
    print("=" * 60)

    # 创建临时目录
    import tempfile
    project_dir = tempfile.mkdtemp()

    try:
        # 创建执行器
        agent_spec = {
            "id": "test.antigravity",
            "kind": "agent",
            "engine": {
                "type": "llm",
                "provider": "custom",
                "base_url": os.getenv("OPENAI_BASE_URL"),
                "api_key": os.getenv("OPENAI_API_KEY"),
                "model": os.getenv("OPENAI_MODEL"),
                "temperature": 0.7,
                "max_tokens": 500
            },
            "system_prompt": "你是一个有帮助的助手。",
            "user_prompt": "你好，请用一句话介绍你自己。"
        }

        executor = LLMExecutor(project_dir, agent_spec)
        request = create_test_request(project_dir, "test_antigravity")

        print(f"\n📋 配置:")
        print(f"  Base URL: {os.getenv('OPENAI_BASE_URL')}")
        print(f"  Model: {os.getenv('OPENAI_MODEL')}")
        print(f"  Prompt: {agent_spec['user_prompt']}")

        # 执行
        print(f"\n⏳ 正在调用 LLM...")
        result = await executor.execute(request)

        # 检查结果
        if result.status == "completed":
            print(f"\n✅ 测试通过！")
            print(f"\n📝 响应内容:")
            print(f"  {result.raw[:200]}...")

            print(f"\n📊 执行统计:")
            print(f"  状态: {result.status}")
            print(f"  耗时: {result.duration_seconds:.2f} 秒")
            print(f"  输出文件: {len(result.outputs)} 个")

            return True
        else:
            print(f"\n❌ 测试失败:")
            print(f"  错误: {result.error}")
            if result.error_details:
                print(f"  详情: {result.error_details}")
            return False

    except Exception as e:
        print(f"\n❌ 异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # 清理临时目录
        import shutil
        shutil.rmtree(project_dir, ignore_errors=True)


async def test_zhipu_glm():
    """测试智谱 GLM"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 智谱 GLM API")
    print("=" * 60)

    import tempfile
    project_dir = tempfile.mkdtemp()

    try:
        agent_spec = {
            "id": "test.zhipu",
            "kind": "agent",
            "engine": {
                "type": "llm",
                "provider": "custom",
                "base_url": "https://open.bigmodel.cn/api/paas/v4",
                "api_key": os.getenv("ZHIPU_API_KEY"),
                "model": os.getenv("ZHIPU_MODEL", "glm-4-flash"),
                "temperature": 0.7,
                "max_tokens": 500
            },
            "system_prompt": "你是一个有帮助的助手。",
            "user_prompt": "你好，请用一句话介绍北京。"
        }

        executor = LLMExecutor(project_dir, agent_spec)
        request = create_test_request(project_dir, "test_zhipu")

        print(f"\n📋 配置:")
        print(f"  Base URL: https://open.bigmodel.cn/api/paas/v4")
        print(f"  Model: {os.getenv('ZHIPU_MODEL')}")
        print(f"  Prompt: {agent_spec['user_prompt']}")

        print(f"\n⏳ 正在调用智谱 GLM...")
        result = await executor.execute(request)

        if result.status == "completed":
            print(f"\n✅ 测试通过！")
            print(f"\n📝 响应内容:")
            print(f"  {result.raw[:200]}...")

            print(f"\n📊 执行统计:")
            print(f"  状态: {result.status}")
            print(f"  耗时: {result.duration_seconds:.2f} 秒")

            return True
        else:
            print(f"\n❌ 测试失败:")
            print(f"  错误: {result.error}")
            return False

    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False
    finally:
        import shutil
        shutil.rmtree(project_dir, ignore_errors=True)


async def test_with_openai_client():
    """使用原生 OpenAI 客户端测试"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 原生 OpenAI 客户端")
    print("=" * 60)

    try:
        from openai import OpenAI

        client = OpenAI(
            base_url=os.getenv("OPENAI_BASE_URL"),
            api_key=os.getenv("OPENAI_API_KEY")
        )

        print(f"\n📋 配置:")
        print(f"  Base URL: {os.getenv('OPENAI_BASE_URL')}")
        print(f"  Model: {os.getenv('OPENAI_MODEL')}")

        print(f"\n⏳ 正在调用...")
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL"),
            messages=[
                {"role": "user", "content": "你好，请用一句话说'测试成功'"}
            ]
        )

        content = response.choices[0].message.content
        print(f"\n✅ 测试通过！")
        print(f"\n📝 响应:")
        print(f"  {content}")

        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("  LLM Executor 测试套件")
    print("🚀" * 30)

    results = {}

    # 测试 1: Antigravity 反代
    results['antigravity'] = await test_antigravity_proxy()

    # 测试 2: 智谱 GLM
    results['zhipu'] = await test_zhipu_glm()

    # 测试 3: 原生客户端
    results['openai_client'] = await test_with_openai_client()

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")

    total = len(results)
    passed = sum(results.values())
    print(f"\n总计: {passed}/{total} 测试通过")

    if passed == total:
        print("\n🎉 所有测试通过！LLM Executor 配置正确。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查配置。")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
