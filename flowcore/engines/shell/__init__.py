"""
Shell Engine - 执行 Shell 命令和脚本
"""

from .executor import ShellSkillExecutor, create_executor
from ..base import EngineRegistry

# 注册到 EngineRegistry
EngineRegistry.register("shell")(create_executor)

__all__ = ["ShellSkillExecutor", "create_executor"]
