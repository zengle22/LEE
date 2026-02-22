"""
Event Log - 事件溯源日志实现

核心功能：
1. 自动记录所有工作流事件
2. 不依赖 Agent 主动记录
3. 支持回放和审计
4. 生成统计报告
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict


class EventType(Enum):
    """事件类型"""
    # 运行级事件
    RUN_CREATED = "run_created"
    RUN_STARTED = "run_started"
    RUN_PAUSED = "run_paused"
    RUN_RESUMED = "run_resumed"
    RUN_COMPLETED = "run_completed"
    RUN_FAILED = "run_failed"
    RUN_ABORTED = "run_aborted"

    # 步骤级事件
    STEP_READY = "step_ready"
    STEP_STARTED = "step_started"
    STEP_COMPLETED = "step_completed"
    STEP_FAILED = "step_failed"
    STEP_SKIPPED = "step_skipped"
    STEP_RETRIED = "step_retried"

    # 验证事件
    VALIDATION_STARTED = "validation_started"
    VALIDATION_PASSED = "validation_passed"
    VALIDATION_FAILED = "validation_failed"

    # 门禁事件
    GATE_TRIGGERED = "gate_triggered"
    GATE_APPROVED = "gate_approved"
    GATE_REJECTED = "gate_rejected"
    GATE_REVISED = "gate_revised"
    GATE_FLAGGED = "gate_flagged"
    GATE_TIMEOUT = "gate_timeout"

    # 产物事件
    ARTIFACT_CREATED = "artifact_created"
    ARTIFACT_VALIDATED = "artifact_validated"

    # 令牌事件
    TOKEN_ISSUED = "token_issued"
    TOKEN_VALIDATED = "token_validated"
    TOKEN_EXPIRED = "token_expired"
    TOKEN_REVOKED = "token_revoked"

    # 工具调用事件
    TOOL_CALLED = "tool_called"
    TOOL_BLOCKED = "tool_blocked"

    # 错误事件
    ERROR_OCCURRED = "error_occurred"


@dataclass
class Event:
    """事件数据结构"""
    event_id: str
    event_type: EventType
    timestamp: str
    run_id: str
    step_id: Optional[str] = None
    agent_id: Optional[str] = None
    actor: Optional[str] = None  # human / agent / system
    data: Optional[Dict] = None
    inputs_hash: Optional[str] = None
    outputs_hash: Optional[str] = None
    error: Optional[str] = None
    metadata: Optional[Dict] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d["event_type"] = self.event_type.value
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Event':
        d = d.copy()
        d["event_type"] = EventType(d["event_type"])
        return cls(**d)


class EventLog:
    """事件日志管理器"""

    LOG_FILE = ".workflow/events.jsonl"

    def __init__(self, project_dir: str, run_id: str = None):
        self.project_dir = Path(project_dir)
        self.log_path = self.project_dir / self.LOG_FILE
        self.run_id = run_id
        self._event_counter = 0

    def _generate_event_id(self) -> str:
        """生成事件 ID"""
        self._event_counter += 1
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        return f"EVT-{timestamp}-{self._event_counter:04d}"

    def _compute_hash(self, data: Any) -> str:
        """计算数据 hash"""
        return hashlib.sha256(
            json.dumps(data, sort_keys=True, default=str).encode()
        ).hexdigest()[:16]

    def log(self,
            event_type: EventType,
            step_id: str = None,
            agent_id: str = None,
            actor: str = "system",
            data: Dict = None,
            inputs_hash: str = None,
            outputs_hash: str = None,
            error: str = None,
            metadata: Dict = None) -> Event:
        """记录事件"""
        # 确保目录存在
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

        event = Event(
            event_id=self._generate_event_id(),
            event_type=event_type,
            timestamp=datetime.now().isoformat(),
            run_id=self.run_id,
            step_id=step_id,
            agent_id=agent_id,
            actor=actor,
            data=data,
            inputs_hash=inputs_hash,
            outputs_hash=outputs_hash,
            error=error,
            metadata=metadata
        )

        # 追加到日志文件
        with open(self.log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(event.to_dict(), ensure_ascii=False) + '\n')

        return event

    def log_run_created(self, workflow_id: str, workflow_name: str) -> Event:
        return self.log(
            EventType.RUN_CREATED,
            data={"workflow_id": workflow_id, "workflow_name": workflow_name}
        )

    def log_step_started(self, step_id: str, agent_id: str, token: str = None) -> Event:
        return self.log(
            EventType.STEP_STARTED,
            step_id=step_id,
            agent_id=agent_id,
            actor="agent",
            data={"token": token}
        )

    def log_step_completed(self, step_id: str, agent_id: str, outputs: List[str], outputs_hash: str) -> Event:
        return self.log(
            EventType.STEP_COMPLETED,
            step_id=step_id,
            agent_id=agent_id,
            actor="agent",
            outputs_hash=outputs_hash,
            data={"outputs": outputs}
        )

    def log_step_failed(self, step_id: str, agent_id: str, error: str) -> Event:
        return self.log(
            EventType.STEP_FAILED,
            step_id=step_id,
            agent_id=agent_id,
            actor="agent",
            error=error
        )

    def log_validation_passed(self, step_id: str, validator: str, details: Dict = None) -> Event:
        return self.log(
            EventType.VALIDATION_PASSED,
            step_id=step_id,
            actor="system",
            data={"validator": validator, "details": details}
        )

    def log_validation_failed(self, step_id: str, validator: str, errors: List[str]) -> Event:
        return self.log(
            EventType.VALIDATION_FAILED,
            step_id=step_id,
            actor="system",
            error="; ".join(errors),
            data={"validator": validator, "errors": errors}
        )

    def log_gate_triggered(self, gate_id: str, step_id: str, gate_type: str, blocking: bool) -> Event:
        return self.log(
            EventType.GATE_TRIGGERED,
            step_id=step_id,
            actor="system",
            data={"gate_id": gate_id, "gate_type": gate_type, "blocking": blocking}
        )

    def log_gate_approved(self, gate_id: str, step_id: str, approver: str, approval_id: str) -> Event:
        return self.log(
            EventType.GATE_APPROVED,
            step_id=step_id,
            actor="human",
            data={"gate_id": gate_id, "approver": approver, "approval_id": approval_id}
        )

    def log_gate_rejected(
        self,
        gate_id: str,
        step_id: str,
        approver: str,
        reason: str,
        action: Optional[str] = None,
    ) -> Event:
        return self.log(
            EventType.GATE_REJECTED,
            step_id=step_id,
            actor="human",
            error=reason,
            data={"gate_id": gate_id, "approver": approver, "action": action}
        )

    def log_gate_revised(
        self,
        gate_id: str,
        step_id: str,
        reviewer: str,
        reason: str,
    ) -> Event:
        return self.log(
            EventType.GATE_REVISED,
            step_id=step_id,
            actor="human",
            error=reason,
            data={"gate_id": gate_id, "reviewer": reviewer}
        )

    def log_gate_flagged(
        self,
        gate_id: str,
        step_id: str,
        reporter: str,
        issues: List[str],
    ) -> Event:
        return self.log(
            EventType.GATE_FLAGGED,
            step_id=step_id,
            actor="human",
            data={"gate_id": gate_id, "reporter": reporter, "issues": issues}
        )

    def log_token_issued(self, step_id: str, token_id: str, expires_at: str) -> Event:
        return self.log(
            EventType.TOKEN_ISSUED,
            step_id=step_id,
            actor="system",
            data={"token_id": token_id, "expires_at": expires_at}
        )

    def log_tool_called(self, step_id: str, tool_name: str, token: str, allowed: bool) -> Event:
        event_type = EventType.TOOL_CALLED if allowed else EventType.TOOL_BLOCKED
        return self.log(
            event_type,
            step_id=step_id,
            actor="agent",
            data={"tool_name": tool_name, "token": token, "allowed": allowed}
        )

    def get_events(self,
                   event_type: EventType = None,
                   step_id: str = None,
                   since: str = None,
                   limit: int = None) -> List[Event]:
        """查询事件"""
        if not self.log_path.exists():
            return []

        events = []
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip():
                    continue
                event = Event.from_dict(json.loads(line))

                # 过滤
                if event_type and event.event_type != event_type:
                    continue
                if step_id and event.step_id != step_id:
                    continue
                if since and event.timestamp < since:
                    continue

                events.append(event)

                if limit and len(events) >= limit:
                    break

        return events

    def get_step_timeline(self, step_id: str) -> List[Event]:
        """获取步骤的事件时间线"""
        return self.get_events(step_id=step_id)

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        events = self.get_events()

        stats = {
            "total_events": len(events),
            "event_counts": {},
            "step_durations": {},
            "gate_wait_times": {},
            "error_count": 0,
            "retry_count": 0
        }

        step_starts = {}
        gate_triggers = {}

        for event in events:
            # 事件计数
            et = event.event_type.value
            stats["event_counts"][et] = stats["event_counts"].get(et, 0) + 1

            # 错误计数
            if event.error:
                stats["error_count"] += 1

            # 步骤耗时
            if event.event_type == EventType.STEP_STARTED:
                step_starts[event.step_id] = event.timestamp
            elif event.event_type == EventType.STEP_COMPLETED and event.step_id in step_starts:
                start = datetime.fromisoformat(step_starts[event.step_id])
                end = datetime.fromisoformat(event.timestamp)
                duration = (end - start).total_seconds()
                stats["step_durations"][event.step_id] = duration

            # 门禁等待时间
            if event.event_type == EventType.GATE_TRIGGERED:
                gate_id = event.data.get("gate_id")
                gate_triggers[gate_id] = event.timestamp
            elif event.event_type in [
                EventType.GATE_APPROVED,
                EventType.GATE_REJECTED,
                EventType.GATE_REVISED,
                EventType.GATE_FLAGGED,
            ]:
                gate_id = event.data.get("gate_id")
                if gate_id in gate_triggers:
                    start = datetime.fromisoformat(gate_triggers[gate_id])
                    end = datetime.fromisoformat(event.timestamp)
                    wait_time = (end - start).total_seconds()
                    stats["gate_wait_times"][gate_id] = wait_time

            # 重试计数
            if event.event_type == EventType.STEP_RETRIED:
                stats["retry_count"] += 1

        return stats

    def export_audit_report(self, output_path: str = None) -> str:
        """导出审计报告"""
        events = self.get_events()
        stats = self.get_statistics()

        report = {
            "generated_at": datetime.now().isoformat(),
            "run_id": self.run_id,
            "statistics": stats,
            "events": [e.to_dict() for e in events]
        }

        if output_path is None:
            output_path = self.project_dir / ".workflow" / f"audit_report_{self.run_id}.json"

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(output_path)
