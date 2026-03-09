"""
LEE Orchestrator v3.0 - Gate API

提供人工审批门（Human Gate）的 API 接口。

Gate 是一种特殊的步骤类型，需要人工介入才能继续执行工作流。
"""

from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from lee.orchestrator.storage.models import Step, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.execution.state_machine import GateStateMachine
from lee.orchestrator.execution.orchestrator import Orchestrator


@dataclass
class GateRequest:
    """
    Gate 请求

    当工作流遇到 human_gate 时创建
    """
    gate_id: str
    workflow_id: str
    step_id: str
    step_name: str
    description: str
    context: Dict[str, Any]  # 执行上下文
    created_at: str
    status: str = "pending"  # pending | approved | rejected | skipped


@dataclass
class GateResponse:
    """
    Gate 响应

    人工审批后返回
    """
    gate_id: str
    decision: str  # approved | rejected | skipped
    comment: Optional[str] = None
    checklist: List[Dict[str, Any]] = field(default_factory=list)
    responded_at: str = None


class GateAPI:
    """
    Gate API

    提供人工审批门的管理接口
    """

    def __init__(self, store: SQLiteStore, orchestrator: Orchestrator):
        """
        初始化 Gate API

        Args:
            store: SQLite 存储层
            orchestrator: Orchestrator 实例
        """
        self.store = store
        self.orchestrator = orchestrator
        self.gate_sm = GateStateMachine(store)

        # 临时存储 gate 请求（实际应该存储在数据库）
        self._gates: Dict[str, GateRequest] = {}

    async def create_gate(
        self,
        workflow_id: str,
        step_id: str,
        step_name: str,
        description: str,
        context: Dict[str, Any],
    ) -> GateRequest:
        """
        创建 Gate 请求

        Args:
            workflow_id: 工作流 ID
            step_id: 步骤 ID
            step_name: 步骤名称
            description: 描述
            context: 执行上下文

        Returns:
            Gate 请求对象
        """
        gate_state = await self.gate_sm.create_gate(workflow_id, step_id, {
            "step_name": step_name,
            "description": description,
            "context": context,
        })

        gate = GateRequest(
            gate_id=gate_state.gate_id,
            workflow_id=workflow_id,
            step_id=step_id,
            step_name=step_name,
            description=description,
            context=context,
            created_at=datetime.now().isoformat(),
        )

        self._gates[gate.gate_id] = gate

        # 暂停工作流
        try:
            await self.orchestrator.pause(workflow_id)
        except Exception:
            pass  # 工作流可能已经是 PAUSED 状态

        return gate

    async def approve_gate(
        self,
        gate_id: str,
        comment: Optional[str] = None,
        checklist: Optional[List[Dict[str, Any]]] = None,
    ) -> None:
        """
        批准 Gate

        Args:
            gate_id: Gate ID
            comment: 评论
            checklist: 检查清单
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]

        # 更新 Gate 状态
        await self.gate_sm.approve_gate(gate_id, {
            "comment": comment,
            "checklist": checklist or [],
        })

        # 恢复工作流
        await self.orchestrator.resume(gate.workflow_id)

        # 标记步骤完成
        from lee.orchestrator.execution.state_machine import WorkflowStateMachine
        sm = WorkflowStateMachine(
            self.store,
            template_manager=getattr(self.orchestrator, "template_manager", None),
            event_log=getattr(self.orchestrator, "event_log", None),
        )
        await sm.complete_step(gate.workflow_id, gate.step_id, {
            "approved": True,
            "comment": comment,
            "checklist": checklist,
        })

    async def reject_gate(
        self,
        gate_id: str,
        reason: str,
    ) -> None:
        """
        拒绝 Gate

        Args:
            gate_id: Gate ID
            reason: 拒绝原因
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]

        # 更新 Gate 状态
        await self.gate_sm.reject_gate(gate_id, reason)

        # 工作流状态已自动更新为 FAILED

    async def skip_gate(
        self,
        gate_id: str,
    ) -> None:
        """
        跳过 Gate

        Args:
            gate_id: Gate ID
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]

        # 更新 Gate 状态
        await self.gate_sm.skip_gate(gate_id)

        # 恢复工作流
        await self.orchestrator.resume(gate.workflow_id)

        # 标记步骤完成
        from lee.orchestrator.execution.state_machine import WorkflowStateMachine
        sm = WorkflowStateMachine(
            self.store,
            template_manager=getattr(self.orchestrator, "template_manager", None),
            event_log=getattr(self.orchestrator, "event_log", None),
        )
        await sm.complete_step(gate.workflow_id, gate.step_id, {
            "skipped": True,
        })

    async def get_gate(self, gate_id: str) -> Optional[GateRequest]:
        """
        获取 Gate 信息

        Args:
            gate_id: Gate ID

        Returns:
            Gate 请求对象
        """
        return self._gates.get(gate_id)

    async def list_pending_gates(self, workflow_id: Optional[str] = None) -> List[GateRequest]:
        """
        列出待处理的 Gate

        Args:
            workflow_id: 工作流 ID（可选，不指定则返回所有）

        Returns:
            待处理的 Gate 列表
        """
        pending = []
        for gate in self._gates.values():
            if gate.status == "pending":
                if workflow_id is None or gate.workflow_id == workflow_id:
                    pending.append(gate)
        return pending

    async def get_gate_status(
        self,
        gate_id: str
    ) -> Dict[str, Any]:
        """
        获取 Gate 状态

        Args:
            gate_id: Gate ID

        Returns:
            Gate 状态信息
        """
        gate = self._gates.get(gate_id)
        if not gate:
            return None

        # 查询工作流状态
        from lee.orchestrator.storage.models import WorkflowInstance
        instance = await self.store.get_workflow(gate.workflow_id)

        return {
            "gate_id": gate.gate_id,
            "workflow_id": gate.workflow_id,
            "step_id": gate.step_id,
            "step_name": gate.step_name,
            "description": gate.description,
            "status": gate.status,
            "workflow_status": instance.status.value if instance else None,
            "created_at": gate.created_at,
            "context": gate.context,
        }
