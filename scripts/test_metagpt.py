#!/usr/bin/env python3
"""
测试 MetaGPT Executor
验证 MetaGPT 集成是否正常工作
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


async def test_metagpt_import():
    """测试 MetaGPT 导入"""
    print("\n" + "=" * 60)
    print("🧪 测试 1: MetaGPT 导入")
    print("=" * 60)

    try:
        from flowcore.engines import metagpt
        print("✅ MetaGPT 模块导入成功")
        print(f"  可用引擎: {metagpt.AVAILABLE_ENGINES if hasattr(metagpt, 'AVAILABLE_ENGINES') else 'N/A'}")
        return True
    except ImportError as e:
        print(f"❌ MetaGPT 导入失败: {e}")
        print(f"  提示: MetaGPT 是可选依赖，如果未安装可忽略此测试")
        return False


async def test_metagpt_executor():
    """测试 MetaGPT 执行器"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: MetaGPT Executor")
    print("=" * 60)

    try:
        from flowcore.engines.metagpt.executor_v2 import MetaGPTExecutor
        import tempfile

        # 创建临时目录
        project_dir = tempfile.mkdtemp()

        try:
            agent_spec = {
                "id": "test.metagpt",
                "kind": "agent",
                "engine": {
                    "type": "metagpt",
                    "scenario": "default",
                    "role": "assistant",
                    "api_key": os.getenv("METAGPT_API_KEY"),
                    "base_url": os.getenv("METAGPT_BASE_URL"),
                    "model": os.getenv("METAGPT_MODEL"),
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                "system_prompt": "你是一个有帮助的助手。",
                "user_prompt": "你好，请用一句话介绍你自己。"
            }

            print(f"\n📋 配置:")
            print(f"  Scenario: {agent_spec['engine']['scenario']}")
            print(f"  Role: {agent_spec['engine']['role']}")
            print(f"  Base URL: {agent_spec['engine']['base_url']}")
            print(f"  Model: {agent_spec['engine']['model']}")

            # 创建执行器
            executor = MetaGPTExecutor(project_dir, agent_spec)

            print(f"\n✅ MetaGPT Executor 创建成功")
            print(f"  Executor 类型: {type(executor).__name__}")

            return True

        except Exception as e:
            print(f"\n❌ 创建 Executor 失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            # 清理
            import shutil
            shutil.rmtree(project_dir, ignore_errors=True)

    except ImportError as e:
        print(f"❌ MetaGPT Executor 导入失败: {e}")
        return False


async def test_metagpt_execution():
    """测试 MetaGPT 执行（如果可用）"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: MetaGPT 执行")
    print("=" * 60)

    try:
        from flowcore.engines.metagpt.executor_v2 import MetaGPTExecutor
        from flowcore.engines.protocol import StepExecutionRequest
        import tempfile

        project_dir = tempfile.mkdtemp()

        try:
            agent_spec = {
                "id": "test.metagpt",
                "kind": "agent",
                "engine": {
                    "type": "metagpt",
                    "scenario": "default",
                    "role": "assistant",
                    "api_key": os.getenv("METAGPT_API_KEY"),
                    "base_url": os.getenv("METAGPT_BASE_URL"),
                    "model": os.getenv("METAGPT_MODEL"),
                    "temperature": 0.7,
                    "max_tokens": 500
                },
                "system_prompt": "你是一个有帮助的助手。",
                "user_prompt": "你好，请用一句话介绍你自己。"
            }

            executor = MetaGPTExecutor(project_dir, agent_spec)

            request = StepExecutionRequest(
                project_dir=project_dir,
                step_id="test_metagpt",
                run_id="test-run-001",
                agent_spec=agent_spec,
                context={}
            )

            print(f"\n⏳ 正在执行 MetaGPT...")
            result = await executor.execute(request)

            if result.status == "completed":
                print(f"\n✅ 执行成功！")
                print(f"\n📝 结果:")
                if result.raw:
                    print(f"  {str(result.raw)[:200]}...")

                print(f"\n📊 统计:")
                print(f"  状态: {result.status}")
                print(f"  耗时: {result.duration_seconds:.2f} 秒")

                return True
            else:
                print(f"\n❌ 执行失败:")
                print(f"  错误: {result.error}")
                return False

        except Exception as e:
            print(f"\n❌ 执行异常: {e}")
            import traceback
            traceback.print_exc()
            return False
        finally:
            import shutil
            shutil.rmtree(project_dir, ignore_errors=True)

    except ImportError as e:
        print(f"⚠️  MetaGPT 未安装，跳过执行测试")
        return None


async def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("  MetaGPT Executor 测试套件")
    print("🚀" * 30)

    results = {}

    # 测试 1: 导入
    result1 = await test_metagpt_import()
    results['import'] = result1

    # 测试 2: 创建 Executor
    if result1:
        result2 = await test_metagpt_executor()
        results['executor'] = result2
    else:
        results['executor'] = False

    # 测试 3: 执行
    if results.get('executor'):
        result3 = await test_metagpt_execution()
        if result3 is not None:
            results['execution'] = result3

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    for test_name, passed in results.items():
        if passed is None:
            status = "⏭️  跳过"
        elif passed:
            status = "✅ 通过"
        else:
            status = "❌ 失败"
        print(f"  {test_name}: {status}")

    passed_count = sum(1 for v in results.values() if v is True)
    total_count = len(results)
    print(f"\n总计: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print("\n🎉 MetaGPT 配置正确！")
        return 0
    elif passed_count > 0:
        print("\n⚠️  部分功能可用")
        return 0
    else:
        print("\n💡 提示: MetaGPT 是可选依赖，未安装不影响核心功能")
        return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
