#!/usr/bin/env python3
"""
测试 MCP Executor
验证 MCP Server 集成是否正常工作
"""

import os
import sys
import asyncio
import aiohttp
from pathlib import Path

# 添加项目根目录到路径
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "src"))

# 加载环境
from scripts.setup_env import load_env, setup_pythonpath
load_env()
setup_pythonpath()


async def test_mcp_server_health():
    """测试 MCP Server 健康检查"""
    print("\n" + "=" * 60)
    print("🧪 测试 1: MCP Server 健康检查")
    print("=" * 60)

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/health") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    print(f"\n✅ MCP Server 运行正常")
                    print(f"\n📋 服务器信息:")
                    print(f"  状态: {data.get('status')}")
                    print(f"  版本: {data.get('version')}")
                    print(f"  可用工具: {data.get('tools_count')} 个")
                    return True
                else:
                    print(f"\n❌ MCP Server 响应异常: {resp.status}")
                    return False

    except Exception as e:
        print(f"\n❌ 无法连接到 MCP Server: {e}")
        print(f"  提示: 请先启动 MCP Server: cd mcp-server && npm start")
        return False


async def test_mcp_list_tools():
    """测试列出所有工具"""
    print("\n" + "=" * 60)
    print("🧪 测试 2: 列出 MCP 工具")
    print("=" * 60)

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{server_url}/tools") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    tools = data.get('tools', [])

                    print(f"\n✅ 成功获取工具列表")
                    print(f"\n📋 可用工具 ({len(tools)} 个):")

                    for tool in tools:
                        print(f"\n  📦 {tool['name']}")
                        print(f"     描述: {tool['description']}")

                        params = tool.get('parameters', {})
                        if params:
                            print(f"     参数:")
                            for param_name, param_info in params.items():
                                required = "必需" if param_info.get('required') else "可选"
                                print(f"       - {param_name}: {required}")
                                if 'enum' in param_info:
                                    print(f"         选项: {param_info['enum']}")

                    return True
                else:
                    print(f"\n❌ 获取工具列表失败: {resp.status}")
                    return False

    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False


async def test_mcp_call_tool():
    """测试调用 MCP 工具"""
    print("\n" + "=" * 60)
    print("🧪 测试 3: 调用 MCP 工具")
    print("=" * 60)

    server_url = os.getenv("MCP_SERVER_URL", "http://localhost:3000")

    # 测试 run_tests 工具
    tool_name = "run_tests"
    arguments = {
        "project": "/test/project",
        "test_type": "unit"
    }

    print(f"\n📋 调用配置:")
    print(f"  工具: {tool_name}")
    print(f"  参数: {arguments}")

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{server_url}/tools/{tool_name}",
                json={"arguments": arguments}
            ) as resp:
                if resp.status == 200:
                    result = await resp.json()

                    print(f"\n✅ 工具调用成功")
                    print(f"\n📝 执行结果:")

                    for key, value in result.items():
                        if key == 'outputs':
                            print(f"  {key}: {', '.join(value)}")
                        elif isinstance(value, (int, float, str, bool)):
                            print(f"  {key}: {value}")
                        else:
                            print(f"  {key}: {value}")

                    return True
                else:
                    error_data = await resp.json()
                    print(f"\n❌ 工具调用失败: {resp.status}")
                    print(f"  错误: {error_data.get('error')}")
                    return False

    except Exception as e:
        print(f"\n❌ 异常: {e}")
        return False


async def test_mcp_executor():
    """测试 MCP Executor"""
    print("\n" + "=" * 60)
    print("🧪 测试 4: MCP Executor 集成")
    print("=" * 60)

    try:
        from flowcore.engines.mcp.executor import MCPSkillExecutor
        from flowcore.engines.protocol import StepExecutionRequest
        import tempfile

        # 创建临时目录
        project_dir = tempfile.mkdtemp()

        try:
            agent_spec = {
                "id": "test.mcp",
                "kind": "skill",
                "engine": {
                    "type": "mcp",
                    "server_url": os.getenv("MCP_SERVER_URL"),
                    "tool": "run_tests",
                    "timeout": 30,
                    "arguments": {
                        "project": "{{ project_dir }}",
                        "test_type": "unit"
                    }
                }
            }

            print(f"\n📋 配置:")
            print(f"  Server URL: {agent_spec['engine']['server_url']}")
            print(f"  Tool: {agent_spec['engine']['tool']}")

            # 创建执行器
            executor = MCPSkillExecutor(project_dir, agent_spec)

            request = StepExecutionRequest(
                project_dir=project_dir,
                step_id="test_mcp",
                run_id="test-run-001",
                agent_spec=agent_spec,
                context={}
            )

            print(f"\n⏳ 正在执行 MCP 工具...")
            result = await executor.execute(request)

            if result.status == "completed":
                print(f"\n✅ 执行成功！")
                print(f"\n📝 结果:")

                if result.raw:
                    raw_data = result.raw
                    print(f"  成功: {raw_data.get('success')}")
                    print(f"  消息: {raw_data.get('message')}")

                print(f"\n📊 统计:")
                print(f"  状态: {result.status}")
                print(f"  耗时: {result.duration_seconds:.2f} 秒")
                print(f"  输出: {len(result.outputs)} 个文件")

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
            # 清理
            import shutil
            shutil.rmtree(project_dir, ignore_errors=True)

    except ImportError as e:
        print(f"❌ MCP Executor 导入失败: {e}")
        return False


async def main():
    """主测试函数"""
    print("\n" + "🚀" * 30)
    print("  MCP Server 测试套件")
    print("🚀" * 30)

    results = {}

    # 测试 1: 健康检查
    results['health'] = await test_mcp_server_health()

    # 测试 2: 列出工具
    if results['health']:
        results['list_tools'] = await test_mcp_list_tools()
    else:
        results['list_tools'] = False
        print("\n⚠️  MCP Server 未运行，跳过后续测试")
        print("   提示: 在新终端运行 'cd mcp-server && npm start'")

        return 1

    # 测试 3: 调用工具
    if results['list_tools']:
        results['call_tool'] = await test_mcp_call_tool()

    # 测试 4: Executor 集成
    if results['call_tool']:
        results['executor'] = await test_mcp_executor()

    # 总结
    print("\n" + "=" * 60)
    print("📊 测试结果汇总")
    print("=" * 60)

    for test_name, passed in results.items():
        status = "✅ 通过" if passed else "❌ 失败"
        print(f"  {test_name}: {status}")

    passed_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    print(f"\n总计: {passed_count}/{total_count} 测试通过")

    if passed_count == total_count:
        print("\n🎉 MCP Server 集成测试全部通过！")
        return 0
    else:
        print("\n⚠️  部分测试失败，请检查配置")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
