"""
MCP Skill Executor - 调用 MCP (Model Context Protocol) 服务

支持通过 MCP 协议调用远程服务，用于：
- CI/CD 操作
- K8s 部署
- Figma 集成
- 其他 HTTP API 调用
"""

import asyncio
import json
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from ..base import AbstractExecutor
from ..protocol import StepExecutionRequest, StepExecutionResult, ArtifactReference


class MCPSkillExecutor(AbstractExecutor):
    """
    MCP 执行器 - 调用 MCP 服务

    配置示例（skill.yaml）：
    ```yaml
    kind: skill
    id: ci.deploy
    engine:
      type: mcp
      server_url: http://localhost:3000/mcp
      tool: deploy
      timeout: 600
      arguments:
        environment: staging
        project: {{ project_dir }}
    ```
    """

    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        """执行步骤"""
        started_at = datetime.now().isoformat()

        try:
            # 1. 验证请求
            valid, error = self.validate_request(request)
            if not valid:
                return StepExecutionResult(
                    status="failed",
                    error=f"Invalid request: {error}",
                    started_at=started_at,
                    engine_type="mcp"
                )

            # 2. 获取 MCP 服务器配置
            server_url = self.engine_config.get("server_url")
            tool_name = self.engine_config.get("tool")

            if not server_url:
                return StepExecutionResult(
                    status="failed",
                    error="MCP server_url not specified in engine configuration",
                    started_at=started_at,
                    engine_type="mcp"
                )

            if not tool_name:
                return StepExecutionResult(
                    status="failed",
                    error="MCP tool not specified in engine configuration",
                    started_at=started_at,
                    engine_type="mcp"
                )

            # 3. 构建参数
            arguments = self._get_arguments(request)

            # 4. 调用 MCP 服务
            timeout = self._get_timeout(request)

            try:
                result = await asyncio.wait_for(
                    self._call_mcp_tool(server_url, tool_name, arguments),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                completed_at = datetime.now().isoformat()
                return StepExecutionResult(
                    status="timeout",
                    error=f"MCP call timed out after {timeout} seconds",
                    messages=[
                        {"role": "mcp_call", "content": f"{tool_name}({json.dumps(arguments, indent=2)})"},
                        {"role": "error", "content": "Timeout"}
                    ],
                    started_at=started_at,
                    completed_at=completed_at,
                    engine_type="mcp"
                )

            # 5. 保存结果
            workspace = request.get_working_dir()
            result_file = workspace / "result.json"
            result_file.write_text(json.dumps(result, indent=2), encoding="utf-8")

            # 6. 构建输出
            completed_at = datetime.now().isoformat()
            duration = (
                datetime.fromisoformat(completed_at) -
                datetime.fromisoformat(started_at)
            ).total_seconds()

            outputs = [
                ArtifactReference(
                    id="result",
                    path=str(result_file.relative_to(request.project_dir)),
                    content_type="application/json",
                    summary="MCP tool result"
                )
            ]

            # 检查是否有额外的输出文件
            if "outputs" in result:
                for output_path in result.get("outputs", []):
                    full_path = Path(request.project_dir) / output_path
                    if full_path.exists():
                        outputs.append(
                            ArtifactReference(
                                id=output_path,
                                path=output_path,
                                content_type="application/octet-stream",
                                summary=f"Output file: {output_path}"
                            )
                        )

            # 判断状态
            status = "completed" if result.get("success", True) else "failed"

            messages = [
                {"role": "mcp_call", "content": f"{tool_name}({json.dumps(arguments, indent=2)})"},
                {"role": "mcp_result", "content": json.dumps(result, indent=2)}
            ]

            return StepExecutionResult(
                status=status,
                outputs=outputs,
                messages=messages,
                error=result.get("error"),
                started_at=started_at,
                completed_at=completed_at,
                duration_seconds=duration,
                raw=result,
                engine_type="mcp"
            )

        except Exception as e:
            completed_at = datetime.now().isoformat()
            return StepExecutionResult(
                status="failed",
                error=str(e),
                error_details={
                    "exception_type": type(e).__name__,
                    "exception_message": str(e)
                },
                started_at=started_at,
                completed_at=completed_at,
                engine_type="mcp"
            )

    async def _call_mcp_tool(
        self,
        server_url: str,
        tool_name: str,
        arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用 MCP 工具"""
        # 使用 aiohttp 调用 MCP 服务
        import aiohttp

        # MCP 协议：POST /tools/{tool_name}
        url = f"{server_url.rstrip('/')}/tools/{tool_name}"

        payload = {
            "arguments": arguments
        }

        headers = {
            "Content-Type": "application/json"
        }

        # 添加认证（如果配置）
        if "auth_token" in self.engine_config:
            headers["Authorization"] = f"Bearer {self.engine_config['auth_token']}"

        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                return await resp.json()

    def _get_arguments(self, request: StepExecutionRequest) -> Dict[str, Any]:
        """获取工具参数"""
        # 从 engine 配置获取基础参数
        arguments = self.engine_config.get("arguments", {}).copy()

        # 变量替换
        replacements = {
            "{{ project_dir }}": str(request.project_dir),
            "{{ step_id }}": request.step_id,
            "{{ run_id }}": request.run_id,
        }

        # 递归替换
        arguments = self._replace_variables(arguments, replacements)

        # 添加上下文参数
        if "context" in self.engine_config and self.engine_config["context"]:
            # 从 request.context 获取额外参数
            context_params = self.engine_config["context"]
            for param in context_params:
                if param in request.context:
                    arguments[param] = request.context[param]

        return arguments

    def _replace_variables(self, obj: Any, replacements: Dict[str, str]) -> Any:
        """递归替换变量"""
        if isinstance(obj, str):
            result = obj
            for key, value in replacements.items():
                result = result.replace(key, value)
            return result
        elif isinstance(obj, dict):
            return {k: self._replace_variables(v, replacements) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_variables(item, replacements) for item in obj]
        else:
            return obj

    def _get_timeout(self, request: StepExecutionRequest) -> int:
        """获取超时时间（秒）"""
        # 优先使用 engine 配置的超时
        if "timeout" in self.engine_config:
            return int(self.engine_config["timeout"])

        # 否则使用请求的超时
        if request.timeout_seconds:
            return request.timeout_seconds

        # 默认 600 秒（10 分钟）
        return 600


def create_executor(agent_spec: Dict, project_dir: str) -> MCPSkillExecutor:
    """工厂函数：创建 MCPSkillExecutor 实例"""
    return MCPSkillExecutor(project_dir, agent_spec)
