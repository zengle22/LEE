"""
LEE Executor - 基于 LangGraph 的执行层

⚠️ EXPERIMENTAL — 此模块为实验性路径 (ADR-002)。
生产工作流请使用 `lee.orchestrator.execution`。
评估时间线: 2026 Q2，届时决定是否迁移或归档。

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

import warnings
warnings.warn(
    "lee.runtime.executor is EXPERIMENTAL (see ADR-002). "
    "For production workflows, use lee.orchestrator.execution.",
    DeprecationWarning,
    stacklevel=2,
)

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
