"""
LEE Executor - Graph Builder 注册表

管理 task_type 到 Graph Builder 的映射。
"""

from typing import Callable, Dict, Optional, Any, List
from .types import ExecutorTaskSpec

# Graph Builder 类型定义
GraphBuilder = Callable[[ExecutorTaskSpec], Any]

# 注册表存储
_GRAPH_BUILDERS: Dict[str, GraphBuilder] = {}


def register_graph(task_type: str, builder: GraphBuilder) -> None:
    """
    注册 Graph Builder

    Args:
        task_type: 任务类型（如 "l3.impl.coding"）
        builder: Graph 构建函数
    """
    _GRAPH_BUILDERS[task_type] = builder


def get_graph_builder(task_type: str) -> Optional[GraphBuilder]:
    """
    获取 Graph Builder

    Args:
        task_type: 任务类型

    Returns:
        对应的 Graph Builder，如果不存在则返回 None
    """
    return _GRAPH_BUILDERS.get(task_type)


def list_registered_types() -> List[str]:
    """列出所有已注册的 task_type"""
    return list(_GRAPH_BUILDERS.keys())


def _auto_register() -> None:
    """自动注册内置 Graph Builder"""
    try:
        from .graphs.unit_test import build_unit_test_graph
        register_graph("l3.test.unit", build_unit_test_graph)
    except ImportError:
        pass  # Graph 模块可能还未实现

    # Phase B: impl_coding
    try:
        from .graphs.impl_coding import build_impl_coding_graph
        register_graph("l3.impl.coding", build_impl_coding_graph)
    except ImportError:
        pass


# 模块加载时自动注册
_auto_register()
