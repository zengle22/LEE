"""
flowcore - 兼容性重定向包 (已弃用)

⚠️ 警告: flowcore 包已被弃用，将在 v0.3.0 中移除
请迁移到 lee 包:

  迁移示例:
  - from flowcore.orchestrator import Orchestrator
  + from lee.orchestrator.execution import Orchestrator
  
  - from flowcore.engines import ExecutorFactory
  + from lee.orchestrator.execution import ExecutorFactory

本包提供向后兼容的重定向，会触发 DeprecationWarning
"""

import warnings
from importlib.metadata import PackageNotFoundError, version

# 版本号保持同步
try:
    __version__ = version("lee-framework")
except PackageNotFoundError:  # pragma: no cover - fallback for source-only usage
    __version__ = "0.1.0"

# 弃用警告
warnings.warn(
    "flowcore 包已被弃用，将在 v0.3.0 中移除。"
    "请使用 lee 包替代。"
    "迁移指南: https://github.com/your-org/LEE/blob/main/docs/MIGRATION-v0.1-to-v0.2.md",
    DeprecationWarning,
    stacklevel=2,
)

__all__ = ["__version__"]
