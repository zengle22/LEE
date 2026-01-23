"""
MCP Engine - 调用 MCP (Model Context Protocol) 服务
"""

from .executor import MCPSkillExecutor, create_executor
from ..base import EngineRegistry

# 注册到 EngineRegistry
EngineRegistry.register("mcp")(create_executor)

__all__ = ["MCPSkillExecutor", "create_executor"]
