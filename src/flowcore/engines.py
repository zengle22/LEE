"""
兼容性重定向: flowcore.engines -> lee.orchestrator.execution

⚠️ 已弃用: 请直接从 lee.orchestrator.execution 导入
"""
import warnings

warnings.warn(
    "flowcore.engines 已弃用，"
    "请使用 from lee.orchestrator.execution import ...",
    DeprecationWarning,
    stacklevel=2,
)

from lee.orchestrator.execution import (
    ExecutorFactory,
    BaseExecutor,
    LangGraphExecutor,
    ClaudeCodeExecutor,
)

__all__ = [
    "ExecutorFactory",
    "BaseExecutor",
    "LangGraphExecutor",
    "ClaudeCodeExecutor",
]
