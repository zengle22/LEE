"""
LEE Orchestrator API Contract v1

定义 API 的统一动作枚举、请求/响应结构和兼容别名映射。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Optional


class OrchestratorAction(str, Enum):
    """标准动作集合（Contract v1）"""

    GET_STATE = "get_state"
    LIST_READY_STEPS = "list_ready_steps"
    LIST_GATES = "list_gates"
    RUN_STEP = "run_step"
    NEXT_STEP = "next_step"
    CREATE_WORKFLOW = "create_workflow"
    RUN_UNTIL_BLOCKED = "run_until_blocked"
    APPROVE_GATE = "approve_gate"
    REJECT_GATE = "reject_gate"
    REVISE_GATE = "revise_gate"
    FLAG_GATE = "flag_gate"
    PAUSE_WORKFLOW = "pause_workflow"
    RESUME_WORKFLOW = "resume_workflow"


# 兼容旧 action 名称（CLI/历史脚本仍在使用）
LEGACY_ACTION_ALIASES: Dict[str, str] = {
    "create": OrchestratorAction.CREATE_WORKFLOW.value,
    "pause": OrchestratorAction.PAUSE_WORKFLOW.value,
    "resume": OrchestratorAction.RESUME_WORKFLOW.value,
}


class ResponseStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class OrchestratorAPIRequest:
    """
    统一请求结构

    payload 内承载 action 的附加参数（如 gate_id/max_steps）。
    """

    action: str
    project_dir: str = "."
    workflow_id: Optional[str] = None
    step_id: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)

    def normalized_action(self) -> str:
        """将旧 action 归一化到 Contract v1 标准动作名。"""
        return LEGACY_ACTION_ALIASES.get(self.action, self.action)


@dataclass
class OrchestratorAPIResponse:
    """统一响应结构"""

    status: str
    action: str
    data: Any = None
    error: Optional[str] = None
    meta: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status,
            "action": self.action,
            "data": self.data,
            "error": self.error,
            "meta": self.meta,
        }
