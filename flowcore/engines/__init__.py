"""
Engines 模块 - 执行引擎集合

导入所有 Engine 子模块以触发注册。
"""

# 导入核心 Engine（必需）
from . import llm
from . import shell
from . import mcp

# 尝试导入 MetaGPT（可选依赖）
try:
    from . import metagpt
    AVAILABLE_ENGINES = ["llm", "shell", "mcp", "metagpt"]
except ImportError:
    # MetaGPT 未安装
    AVAILABLE_ENGINES = ["llm", "shell", "mcp"]

# 所有可用的 Engine 类型
__all__ = AVAILABLE_ENGINES
