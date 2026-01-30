"""
Graph 公共组件

提供通用的条件边函数和辅助函数。
"""

from typing import Any, Dict, Literal, List


def should_continue(state: Dict[str, Any]) -> Literal["continue", "stop"]:
    """
    通用条件边：判断是否应该继续执行

    检查条件（任一满足则停止）：
    1. errors 列表非空
    2. should_stop 标志为 True

    Args:
        state: 当前状态

    Returns:
        "continue" 继续执行下一个节点
        "stop" 跳转到 build_result 节点
    """
    # 检查是否有错误
    if state.get("errors"):
        return "stop"

    # 检查 should_stop 标志
    if state.get("should_stop", False):
        return "stop"

    return "continue"


def add_log(state: Dict[str, Any], message: str) -> List[str]:
    """
    添加日志（返回新的日志列表）

    Args:
        state: 当前状态
        message: 日志消息

    Returns:
        新的日志列表
    """
    logs = state.get("logs", []).copy()
    logs.append(message)
    return logs


def add_error(state: Dict[str, Any], error: str) -> List[str]:
    """
    添加错误（返回新的错误列表）

    Args:
        state: 当前状态
        error: 错误消息

    Returns:
        新的错误列表
    """
    errors = state.get("errors", []).copy()
    errors.append(error)
    return errors


def update_metrics(
    state: Dict[str, Any],
    updates: Dict[str, Any],
) -> Dict[str, Any]:
    """
    更新指标（返回新的指标字典）

    Args:
        state: 当前状态
        updates: 指标更新

    Returns:
        新的指标字典
    """
    metrics = state.get("metrics", {}).copy()
    metrics.update(updates)
    return metrics
