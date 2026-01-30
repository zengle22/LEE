"""
LEE Executor - LangGraph Runner

基于 LangGraph 的统一执行入口（仅同步版本）。

核心职责：
1. 接收 ExecutorTaskSpec
2. 根据 task_type 获取对应的 Graph Builder
3. 构建 LangGraph 流程
4. 执行并返回 ExecutionResult
"""

from typing import Dict, Any
from datetime import datetime
import logging

from .types import (
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
)
from .registry import get_graph_builder
from .tracing.span_builder import SpanBuilder

logger = logging.getLogger(__name__)


def run_task(task: ExecutorTaskSpec) -> ExecutionResult:
    """
    执行 Executor 任务（统一入口，同步版本）

    这是 Orchestrator 调用的唯一入口点。

    Args:
        task: 任务规格

    Returns:
        执行结果
    """
    started_at = datetime.now()

    # 创建 Span Builder（用于追踪）
    span_builder = SpanBuilder(
        task_id=task.task_id,
        task_type=task.task_type,
        trace_id=task.trace_id,
        parent_span_id=task.parent_span_id,
    )
    span_builder.add_event("task_started", {"task_type": task.task_type})

    try:
        # 获取 Graph Builder
        builder = get_graph_builder(task.task_type)
        if builder is None:
            span_builder.add_event("builder_not_found", {"task_type": task.task_type})
            result = ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED,
                message=f"Unknown task_type: {task.task_type}",
                started_at=started_at,
                completed_at=datetime.now(),
            )
            span_builder.complete(
                status=TaskStatus.FAILED.value,
                message=result.message,
            )
            return result

        span_builder.add_event("graph_building")

        # 构建 LangGraph
        graph = builder(task)

        # 准备初始状态
        initial_state: Dict[str, Any] = {
            "task": task,
            "logs": [f"Starting task: {task.task_id} (type: {task.task_type})"],
            "errors": [],
            "current_step": "start",
            "retry_count": 0,
            "started_at": started_at,
            "metrics": {},
            "tokens_used": 0,
            "should_stop": False,
        }

        span_builder.add_event("graph_invoking")

        # 执行 Graph
        final_state = graph.invoke(initial_state)

        span_builder.add_event("graph_completed", {
            "has_errors": len(final_state.get("errors", [])) > 0,
        })

        # 提取执行结果
        exec_result: ExecutionResult = final_state.get("exec_result")
        if exec_result is None:
            # Graph 没有返回 exec_result，构造一个默认的
            has_errors = len(final_state.get("errors", [])) > 0
            exec_result = ExecutionResult(
                task_id=task.task_id,
                status=TaskStatus.FAILED if has_errors else TaskStatus.SUCCESS,
                message="Task completed with errors" if has_errors else "Task completed",
                logs=final_state.get("logs", []),
                error_details="\n".join(final_state.get("errors", [])) if has_errors else None,
                metrics=final_state.get("metrics", {}),
                tokens_used=final_state.get("tokens_used", 0),
                started_at=started_at,
                completed_at=datetime.now(),
            )

        # 更新时间戳
        exec_result.started_at = started_at
        if exec_result.completed_at is None:
            exec_result.completed_at = datetime.now()

        # 计算持续时间
        exec_result.duration_seconds = (
            exec_result.completed_at - exec_result.started_at
        ).total_seconds()

        # 记录 Span
        span_builder.complete(
            status=exec_result.status.value,
            message=exec_result.message,
            metrics={
                **exec_result.metrics,
                "tokens_used": exec_result.tokens_used,
                "duration_seconds": exec_result.duration_seconds,
            },
        )

        return exec_result

    except Exception as e:
        # 记录异常
        import traceback
        error_details = f"{type(e).__name__}: {str(e)}\n{traceback.format_exc()}"

        logger.error(f"Executor exception: {e}", exc_info=True)
        span_builder.fail(e)

        return ExecutionResult(
            task_id=task.task_id,
            status=TaskStatus.FAILED,
            message=f"Executor exception: {e}",
            logs=[error_details],
            error_details=error_details,
            started_at=started_at,
            completed_at=datetime.now(),
        )
