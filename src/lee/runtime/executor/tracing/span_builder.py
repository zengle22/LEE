"""
LEE Executor - Span 构建器

用于记录执行过程的追踪信息。

MVP 版本：简化实现，只记录基本信息到日志。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)


@dataclass
class SpanBuilder:
    """
    Span 构建器

    用于构建和记录执行追踪信息。
    """
    task_id: str
    task_type: str
    trace_id: Optional[str] = None
    parent_span_id: Optional[str] = None
    span_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    started_at: datetime = field(default_factory=datetime.now)

    # 内部状态
    _events: List[Dict[str, Any]] = field(default_factory=list)
    _completed: bool = False

    def add_event(
        self,
        name: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        添加事件

        Args:
            name: 事件名称
            data: 事件数据
        """
        self._events.append({
            "name": name,
            "timestamp": datetime.now().isoformat(),
            "data": data or {},
        })

    def complete(
        self,
        status: str,
        message: str,
        metrics: Optional[Dict[str, Any]] = None,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        完成 Span 记录

        Args:
            status: 最终状态
            message: 状态消息
            metrics: 执行指标
            extra: 额外数据

        Returns:
            完整的 Span 记录
        """
        if self._completed:
            logger.warning(f"Span {self.span_id} already completed")

        self._completed = True
        completed_at = datetime.now()
        duration = (completed_at - self.started_at).total_seconds()

        span_record = {
            "span_id": self.span_id,
            "trace_id": self.trace_id or self.span_id,
            "parent_span_id": self.parent_span_id,
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": status,
            "message": message,
            "started_at": self.started_at.isoformat(),
            "completed_at": completed_at.isoformat(),
            "duration_seconds": duration,
            "metrics": metrics or {},
            "events": self._events,
            "extra": extra or {},
        }

        # MVP: 只记录日志
        logger.info(
            f"Span completed: {self.task_type} [{status}] "
            f"duration={duration:.2f}s"
        )

        return span_record

    def fail(
        self,
        error: Exception,
        extra: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        记录失败

        Args:
            error: 异常对象
            extra: 额外数据

        Returns:
            完整的 Span 记录
        """
        import traceback

        error_details = {
            "error_type": type(error).__name__,
            "error_message": str(error),
            "traceback": traceback.format_exc(),
        }

        return self.complete(
            status="failed",
            message=f"{type(error).__name__}: {error}",
            extra={**(extra or {}), "error_details": error_details},
        )
