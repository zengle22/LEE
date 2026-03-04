"""
兼容性重定向: flowcore.utils -> lee.orchestrator.utils

⚠️ 已弃用: 请直接从 lee.orchestrator.utils 导入
"""
import warnings

warnings.warn(
    "flowcore.utils 已弃用，"
    "请使用 from lee.orchestrator.utils import ...",
    DeprecationWarning,
    stacklevel=2,
)

# 从 lee 包重导出
from lee.orchestrator.utils import (
    sanitization,
)

__all__ = ["sanitization"]
