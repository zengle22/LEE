#!/usr/bin/env python3
"""
简单的 Mock MCP Server
用于测试 MCP Executor
"""

import asyncio
from aiohttp import web
import json


class MockMCPServer:
    """Mock MCP Server"""

    def __init__(self, port=3000):
        self.port = port
        self.app = web.Application()
        self.setup_routes()

    def setup_routes(self):
        """设置路由"""
        self.app.router.add_get('/health', self.health_check)
        self.app.router.add_get('/tools', self.list_tools)
        self.app.router.add_post('/tools/{tool_name}', self.call_tool)

    async def health_check(self, request):
        """健康检查"""
        return web.json_response({
            'status': 'ok',
            'server': 'LEE Mock MCP Server',
            'version': '1.0.0',
            'tools_count': 3
        })

    async def list_tools(self, request):
        """列出所有工具"""
        tools = [
            {
                'name': 'deploy',
                'description': '部署应用到指定环境',
                'parameters': {
                    'environment': {'type': 'string', 'required': True},
                    'project': {'type': 'string', 'required': True}
                }
            },
            {
                'name': 'run_tests',
                'description': '运行项目测试',
                'parameters': {
                    'project': {'type': 'string', 'required': True},
                    'test_type': {'type': 'string', 'required': False}
                }
            },
            {
                'name': 'generate_code',
                'description': '生成代码文件',
                'parameters': {
                    'prompt': {'type': 'string', 'required': True},
                    'language': {'type': 'string', 'required': False}
                }
            }
        ]

        return web.json_response({'tools': tools, 'count': len(tools)})

    async def call_tool(self, request):
        """调用工具"""
        tool_name = request.match_info['tool_name']

        try:
            data = await request.json()
            arguments = data.get('arguments', {})

            # 模拟工具执行
            await asyncio.sleep(0.5)  # 模拟延迟

            if tool_name == 'deploy':
                result = {
                    'success': True,
                    'deployment_id': f'deploy-{asyncio.get_event_loop().time()}',
                    'environment': arguments.get('environment'),
                    'project': arguments.get('project'),
                    'status': 'deployed',
                    'url': f'https://{arguments.get("environment")}.example.com',
                    'outputs': ['deployment-report.json'],
                    'message': f"部署完成: {arguments.get('project')}"
                }
            elif tool_name == 'run_tests':
                result = {
                    'success': True,
                    'test_type': arguments.get('test_type', 'unit'),
                    'total_tests': 42,
                    'passed': 40,
                    'failed': 2,
                    'coverage': '87.5%',
                    'outputs': ['test-report.xml'],
                    'message': '测试完成: 40/42 通过'
                }
            elif tool_name == 'generate_code':
                result = {
                    'success': True,
                    'code': f"// Generated code for: {arguments.get('prompt')}\nconsole.log('Hello!');",
                    'language': arguments.get('language', 'javascript'),
                    'outputs': ['generated_code.js'],
                    'message': '代码生成完成'
                }
            else:
                return web.json_response({
                    'error': f'Tool not found: {tool_name}'
                }, status=404)

            return web.json_response(result)

        except Exception as e:
            return web.json_response({
                'error': str(e),
                'success': False
            }, status=500)

    async def start(self):
        """启动服务器"""
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, 'localhost', self.port)
        await site.start()

        print(f"\n{'='*60}")
        print("🚀 LEE Mock MCP Server")
        print(f"{'='*60}")
        print(f"✅ Server running at http://localhost:{self.port}")
        print(f"📋 Available tools: 3")
        print("")
        print("Available endpoints:")
        print(f"  - GET  /health           - 健康检查")
        print(f"  - GET  /tools            - 列出所有工具")
        print(f"  - POST /tools/:tool_name - 调用工具")
        print("")
        print("Available tools:")
        print(f"  - deploy: 部署应用")
        print(f"  - run_tests: 运行测试")
        print(f"  - generate_code: 生成代码")
        print(f"{'='*60}\n")

        return runner


async def main():
    """主函数"""
    server = MockMCPServer(port=3000)
    runner = await server.start()

    try:
        # 保持运行
        print("Server is running. Press Ctrl+C to stop.")
        await asyncio.Event().wait()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down MCP server...")
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
