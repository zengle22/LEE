"""
LLM Engine - 直接调用大模型 API
"""

from .executor import LLMExecutor, create_executor
from ..base import EngineRegistry

# 注册到 EngineRegistry
EngineRegistry.register("llm")(create_executor)

__all__ = ["LLMExecutor", "create_executor"]
