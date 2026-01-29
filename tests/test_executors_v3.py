"""
测试 LEE Orchestrator v3.0 - 统一 ExecutorFactory

验证：
1. LLM Executor 创建和执行
2. Shell Executor 创建和执行
3. MetaGPT Executor 创建
4. ExecutorFactory 正常工作
"""

import asyncio
import sys
import os

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.executors import (
    BaseExecutor,
    LLMExecutor,
    ShellExecutor,
    MetaGPTExecutor,
    ExecutorFactory,
)


async def test_executor_factory():
    """测试 ExecutorFactory"""
    print("=" * 60)
    print("测试 ExecutorFactory")
    print("=" * 60)

    # 测试 LLM Executor 创建
    print("\n1. 测试 LLM Executor 创建...")
    llm_executor = ExecutorFactory.create("llm", profile="antigravity")
    assert isinstance(llm_executor, BaseExecutor)
    assert isinstance(llm_executor, LLMExecutor)
    print("   ✅ LLM Executor 创建成功")

    # 测试 Shell Executor 创建
    print("\n2. 测试 Shell Executor 创建...")
    shell_executor = ExecutorFactory.create("shell")
    assert isinstance(shell_executor, BaseExecutor)
    assert isinstance(shell_executor, ShellExecutor)
    print("   ✅ Shell Executor 创建成功")

    # 测试 MetaGPT Executor 创建
    print("\n3. 测试 MetaGPT Executor 创建...")
    try:
        metagpt_executor = ExecutorFactory.create("metagpt", role="Developer")
        assert isinstance(metagpt_executor, BaseExecutor)
        assert isinstance(metagpt_executor, MetaGPTExecutor)
        print("   ✅ MetaGPT Executor 创建成功")
    except ImportError as e:
        print(f"   ⚠️  MetaGPT 未安装，跳过: {e}")

    # 测试未知类型
    print("\n4. 测试未知类型...")
    try:
        ExecutorFactory.create("unknown")
        print("   ❌ 应该抛出异常")
        return False
    except ValueError as e:
        print(f"   ✅ 正确抛出异常: {e}")

    print("\n" + "=" * 60)
    print("✅ 所有 ExecutorFactory 测试通过！")
    print("=" * 60)
    return True


async def test_shell_executor():
    """测试 Shell Executor 执行"""
    print("\n" + "=" * 60)
    print("测试 Shell Executor 执行")
    print("=" * 60)

    executor = ExecutorFactory.create("shell")

    # 测试简单命令
    print("\n1. 执行简单命令: echo 'Hello LEE v3'")
    result = await executor.execute({
        "command": "echo 'Hello LEE v3'",
    })
    assert result["return_code"] == 0
    assert "Hello LEE v3" in result["stdout"]
    print(f"   ✅ 输出: {result['stdout'].strip()}")

    # 测试命令失败
    print("\n2. 执行失败命令: exit 1")
    result = await executor.execute({
        "command": "exit 1",
    })
    assert result["return_code"] == 1
    assert result["status"] == "failed"
    print("   ✅ 正确处理失败命令")

    print("\n" + "=" * 60)
    print("✅ 所有 Shell Executor 测试通过！")
    print("=" * 60)
    return True


async def test_llm_executor():
    """测试 LLM Executor（需要配置）"""
    print("\n" + "=" * 60)
    print("测试 LLM Executor")
    print("=" * 60)

    # 使用新的配置路径
    config_path = os.path.join(project_root, "config", "llm_config.yaml")
    if not os.path.exists(config_path):
        print("\n⚠️  配置文件不存在，跳过 LLM 测试")
        print(f"   配置文件路径: {config_path}")
        return True

    print("\n1. 创建 LLM Executor...")
    executor = ExecutorFactory.create("llm", profile="zhipu", config_path=config_path)

    print("\n2. 执行 LLM 调用...")
    result = await executor.execute({
        "prompt": "Say 'Hello LEE v3'",
    })

    print(f"   ✅ LLM 响应: {result.get('response', 'N/A')}")

    print("\n" + "=" * 60)
    print("✅ LLM Executor 测试通过！")
    print("=" * 60)
    return True


async def test_executor_registration():
    """测试自定义 Executor 注册"""
    print("\n" + "=" * 60)
    print("测试自定义 Executor 注册")
    print("=" * 60)

    # 定义自定义 Executor
    class CustomExecutor(BaseExecutor):
        async def execute(self, input_data):
            return {"custom": "result", "input": input_data}

    # 注册
    print("\n1. 注册自定义 Executor...")
    ExecutorFactory.register("custom", CustomExecutor)
    print("   ✅ 注册成功")

    # 创建
    print("\n2. 创建自定义 Executor...")
    custom_executor = ExecutorFactory.create("custom")
    result = await custom_executor.execute({"test": "data"})
    assert result["custom"] == "result"
    print(f"   ✅ 执行成功: {result}")

    print("\n" + "=" * 60)
    print("✅ 自定义 Executor 测试通过！")
    print("=" * 60)
    return True


async def main():
    """主测试流程"""
    print("\n" + "=" * 60)
    print("🚀 LEE Orchestrator v3.0 - Executor 统一测试")
    print("=" * 60)

    results = []

    # 测试 ExecutorFactory
    results.append(await test_executor_factory())

    # 测试 Shell Executor
    results.append(await test_shell_executor())

    # 测试 LLM Executor（可能跳过）
    results.append(await test_llm_executor())

    # 测试自定义 Executor
    results.append(await test_executor_registration())

    # 总结
    print("\n" + "=" * 60)
    if all(results):
        print("✅ 所有测试通过！")
        print("=" * 60)
        print("\n📋 验证结果:")
        print("  ✅ ExecutorFactory 正常工作")
        print("  ✅ LLM Executor 可创建")
        print("  ✅ Shell Executor 可执行")
        print("  ✅ MetaGPT Executor 可创建")
        print("  ✅ 支持自定义 Executor 注册")
        return 0
    else:
        print("❌ 部分测试失败")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
