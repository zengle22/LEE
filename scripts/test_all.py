#!/usr/bin/env python3
"""
LEE 完整测试套件
运行所有环境测试
"""

import os
import sys
import subprocess
from pathlib import Path


def run_test(script_name: str, description: str) -> bool:
    """运行单个测试脚本"""
    print("\n" + "=" * 70)
    print(f"🧪 {description}")
    print("=" * 70)

    project_root = Path(__file__).parent.parent
    script_path = project_root / script_name

    if not script_path.exists():
        print(f"❌ 测试脚本不存在: {script_path}")
        return False

    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=str(project_root),
            capture_output=False
        )

        return result.returncode == 0

    except Exception as e:
        print(f"❌ 运行测试失败: {e}")
        return False


def check_prerequisites():
    """检查前置条件"""
    print("\n" + "=" * 70)
    print("🔍 检查前置条件")
    print("=" * 70)

    checks = []

    # 检查 .env 文件
    env_file = Path(__file__).parent.parent / ".env"
    if env_file.exists():
        print("✅ .env 文件存在")
        checks.append(True)
    else:
        print("❌ .env 文件不存在")
        print("   请先运行: cp .env.example .env")
        checks.append(False)

    # 检查必需的环境变量
    from dotenv import load_dotenv
    load_dotenv(env_file)

    required_vars = [
        'OPENAI_BASE_URL',
        'OPENAI_API_KEY',
        'OPENAI_MODEL',
    ]

    all_vars_present = True
    for var in required_vars:
        value = os.getenv(var)
        if value:
            # 隐藏敏感部分
            if 'KEY' in var:
                display = f"{value[:8]}..."
            else:
                display = value
            print(f"✅ {var} = {display}")
        else:
            print(f"❌ {var} 未设置")
            all_vars_present = False

    checks.append(all_vars_present)

    # 检查 Python 依赖
    print("\n检查 Python 依赖:")
    dependencies = [
        "yaml",
        "aiohttp",
        "openai",
    ]

    all_deps_ok = True
    for dep in dependencies:
        try:
            __import__(dep)
            print(f"✅ {dep}")
        except ImportError:
            print(f"❌ {dep} 未安装")
            all_deps_ok = False

    checks.append(all_deps_ok)

    # 检查 MCP Server（可选）
    print("\n检查 MCP Server:")
    import aiohttp
    import asyncio

    async def check_mcp():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get("http://localhost:3000/health", timeout=2) as resp:
                    if resp.status == 200:
                        print("✅ MCP Server 运行中")
                        return True
        except:
            print("⚠️  MCP Server 未运行（可选）")
            print("   启动: cd mcp-server && npm start")
            return False

    mcp_ok = asyncio.run(check_mcp())
    checks.append(mcp_ok)  # MCP 是可选的，不影响整体

    return all(checks[:3])  # 前三项是必需的


def main():
    """主函数"""
    print("\n" + "🚀" * 35)
    print("  LEE 完整测试套件")
    print("🚀" * 35)

    # 检查前置条件
    if not check_prerequisites():
        print("\n❌ 前置条件检查失败，请先完成配置")
        print("\n💡 配置步骤:")
        print("  1. cp .env.example .env")
        print("  2. 编辑 .env 填入 API keys")
        print("  3. python scripts/install_requirements.py")
        return 1

    print("\n✅ 前置条件检查通过")

    # 运行测试
    tests = [
        ("scripts/test_llm.py", "LLM Executor 测试"),
        ("scripts/test_metagpt.py", "MetaGPT Executor 测试"),
        ("scripts/test_mcp.py", "MCP Server 测试"),
        ("examples/pm-gate-integration-demo/test_pm_gate_integration.py", "PM Gate 集成测试"),
    ]

    results = {}
    for script, description in tests:
        results[description] = run_test(script, description)

    # 总结
    print("\n" + "=" * 70)
    print("📊 测试结果汇总")
    print("=" * 70)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\n总计: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print("\n🎉 所有测试通过！环境配置正确。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查配置和日志")
        return 1


if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⚠️  测试被用户中断")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 测试运行异常: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
