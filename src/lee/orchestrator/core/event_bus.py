"""
Event Bus - 事件总线实现
用于Testing Workflow v2.0的事件驱动架构
"""

from dataclasses import dataclass, field, asdict
from typing import Dict, List, Callable, Any, Optional
from datetime import datetime
from enum import Enum
import json


class EventType(Enum):
    """事件类型"""
    TEST_FAILURE = "test_failure"
    BUG_CREATED = "bug_created"
    BUG_TRIAGED = "bug_triaged"
    BUG_ROUTED = "bug_routed"
    BUG_FIXED = "bug_fixed"
    BUG_VERIFIED = "bug_verified"
    BUG_CLOSED = "bug_closed"
    BUG_BLOCKED_HUMAN = "bug_blocked_human"
    BUG_BLOCKED_PM = "bug_blocked_pm"
    BUG_BLOCKED_ENV = "bug_blocked_env"
    ROUND_COMPLETED = "round_completed"

    # Workflow Events
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    GATE_PENDING = "gate_pending"
    WORKFLOW_COMPLETED = "workflow_completed"

    # Background Job Events (Phase 2)
    JOB_STARTED = "job_started"
    JOB_COMPLETED = "job_completed"
    JOB_FAILED = "job_failed"
    JOB_CANCELLED = "job_cancelled"

    # P2: L2/L3 Workflow Events
    L2_PHASE_STARTED = "l2_phase_started"
    L2_PHASE_COMPLETED = "l2_phase_completed"
    L3_SPAWNED = "l3_spawned"
    PMA_SPLIT_COMPLETED = "pma_split_completed"
    L3_COMPLETED = "l3_completed"
    L3_FAILED = "l3_failed"


@dataclass
class Event:
    """事件对象"""
    type: EventType
    payload: Dict[str, Any]
    source_workflow: str
    timestamp: str
    event_id: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """转换为字典"""
        data = asdict(self)
        data["type"] = self.type.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        """从字典创建"""
        data["type"] = EventType(data["type"])
        return cls(**data)


class EventBus:
    """事件总线 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._handlers = {}
            cls._instance._event_log = []
        return cls._instance

    def subscribe(self, event_type: EventType, handler: Callable[[Event], None]):
        """订阅事件

        Args:
            event_type: 事件类型
            handler: 事件处理函数
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def unsubscribe(self, event_type: EventType, handler: Callable):
        """取消订阅"""
        if event_type in self._handlers:
            self._handlers[event_type].remove(handler)

    def publish(self, event: Event):
        """发布事件

        Args:
            event: 事件对象
        """
        # 记录到事件日志
        self._event_log.append(event)

        # 触发订阅的处理器
        if event.type in self._handlers:
            for handler in self._handlers[event.type]:
                try:
                    handler(event)
                except Exception as e:
                    print(f"Error handling event {event.type}: {e}")

    def get_events(self,
                   event_type: Optional[EventType] = None,
                   source_workflow: Optional[str] = None) -> List[Event]:
        """获取事件历史

        Args:
            event_type: 过滤事件类型
            source_workflow: 过滤源工作流

        Returns:
            事件列表
        """
        events = self._event_log

        if event_type is not None:
            events = [e for e in events if e.type == event_type]

        if source_workflow is not None:
            events = [e for e in events if e.source_workflow == source_workflow]

        return events

    def clear(self):
        """清空事件日志 (测试用)"""
        self._event_log.clear()

    def save_to_file(self, file_path: str):
        """保存事件日志到文件"""
        with open(file_path, 'w') as f:
            json.dump([e.to_dict() for e in self._event_log], f, indent=2)

    def load_from_file(self, file_path: str):
        """从文件加载事件日志"""
        with open(file_path, 'r') as f:
            data = json.load(f)
            self._event_log = [Event.from_dict(e) for e in data]


# 全局事件总线实例
_global_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """获取全局事件总线"""
    return _global_event_bus
