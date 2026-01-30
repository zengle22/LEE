"""
LEE Executor - 基于 LangGraph 的执行层

提供统一的任务执行接口，支持多种任务类型。

使用方式:
    from lee.runtime.executor import run_task, ExecutorTaskSpec, ExecutionResult

    task = ExecutorTaskSpec(
        task_id="test-001",
        task_type="l3.test.unit",
        inputs={"repo_workspace": "."},
    )
    result = run_task(task)
"""

from .types import (
    TaskStatus,
    ExecutorTaskSpec,
    ExecutionResult,
    BaseState,
    ImplCodingState,
    UnitTestState,
)
from .langgraph_runner import run_task
from .registry import register_graph, get_graph_builder, list_registered_types

__all__ = [
    # 类型
    "TaskStatus",
    "ExecutorTaskSpec",
    "ExecutionResult",
    "BaseState",
    "ImplCodingState",
    "UnitTestState",
    # 入口函数
    "run_task",
    # 注册表
    "register_graph",
    "get_graph_builder",
    "list_registered_types",
]
