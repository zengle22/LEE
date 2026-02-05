"""
LEE Orchestrator - Human Approval Executor

人工审批流程管理器，支持门禁的人类介入和签字审批。

核心功能：
1. 审批状态管理：pending, approved, rejected, timeout
2. 审批记录：持久化审批决策
3. 升级策略：超时升级逻辑
4. 通知机制：发送审批通知
5. 审批历史：查询和追溯
"""

import json
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field


class ApprovalStatus(Enum):
    """审批状态"""

    PENDING = "pending"  # 待审批
    APPROVED = "approved"  # 已批准
    REJECTED = "rejected"  # 已拒绝
    TIMEOUT = "timeout"  # 超时
    CANCELLED = "cancelled"  # 已取消
    ESCALATED = "escalated"  # 已升级

    def __str__(self):
        return self.value


@dataclass
class ApprovalRequest:
    """审批请求"""

    request_id: str
    gate_id: str
    gate_name: str
    workflow_id: str
    workflow_run_id: str
    stage_id: str
    step_id: str

    # 审批配置
    required_approvers: List[Dict[str, Any]] = field(default_factory=list)
    optional_approvers: List[Dict[str, Any]] = field(default_factory=list)
    approval_sla: Optional[int] = None  # 小时
    min_required: int = 1  # 最少需要多少批准

    # 审批标准
    approval_criteria: Optional[Dict[str, Any]] = None
    context_data: Dict[str, Any] = field(default_factory=dict)

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    deadline: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # 状态
    status: ApprovalStatus = ApprovalStatus.PENDING

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "request_id": self.request_id,
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "workflow_id": self.workflow_id,
            "workflow_run_id": self.workflow_run_id,
            "stage_id": self.stage_id,
            "step_id": self.step_id,
            "required_approvers": self.required_approvers,
            "optional_approvers": self.optional_approvers,
            "approval_sla": self.approval_sla,
            "min_required": self.min_required,
            "approval_criteria": self.approval_criteria,
            "context_data": self.context_data,
            "created_at": self.created_at.isoformat(),
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "status": str(self.status),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalRequest":
        """从字典创建"""
        return cls(
            request_id=data["request_id"],
            gate_id=data["gate_id"],
            gate_name=data["gate_name"],
            workflow_id=data["workflow_id"],
            workflow_run_id=data["workflow_run_id"],
            stage_id=data["stage_id"],
            step_id=data["step_id"],
            required_approvers=data.get("required_approvers", []),
            optional_approvers=data.get("optional_approvers", []),
            approval_sla=data.get("approval_sla"),
            min_required=data.get("min_required", 1),
            approval_criteria=data.get("approval_criteria"),
            context_data=data.get("context_data", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
            deadline=datetime.fromisoformat(data["deadline"]) if data.get("deadline") else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None,
            status=ApprovalStatus(data.get("status", "pending")),
        )


@dataclass
class ApprovalDecision:
    """审批决策"""

    decision_id: str
    request_id: str
    approver: str
    approver_role: str
    decision: ApprovalStatus
    comments: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "approver": self.approver,
            "approver_role": self.approver_role,
            "decision": str(self.decision),
            "comments": self.comments,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ApprovalDecision":
        """从字典创建"""
        return cls(
            decision_id=data["decision_id"],
            request_id=data["request_id"],
            approver=data["approver"],
            approver_role=data["approver_role"],
            decision=ApprovalStatus(data["decision"]),
            comments=data.get("comments"),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]),
        )


class HumanApprovalExecutor:
    """
    人工审批执行器

    职责：
    1. 创建审批请求
    2. 处理审批决策
    3. 检查超时和升级
    4. 管理审批历史
    5. 发送通知
    """

    def __init__(self, storage_path: Optional[str] = None):
        """
        初始化审批执行器

        Args:
            storage_path: 审批记录存储路径
        """
        self.storage_path = Path(storage_path) if storage_path else None
        self._requests: Dict[str, ApprovalRequest] = {}
        self._decisions: Dict[str, List[ApprovalDecision]] = {}

        # 加载已有记录
        if self.storage_path and self.storage_path.exists():
            self._load()

    # ========================================================================
    # 审批请求管理
    # ========================================================================

    def create_request(
        self,
        gate_id: str,
        gate_name: str,
        workflow_id: str,
        workflow_run_id: str,
        stage_id: str,
        step_id: str,
        required_approvers: List[Dict[str, Any]],
        optional_approvers: Optional[List[Dict[str, Any]]] = None,
        approval_sla: Optional[int] = None,
        approval_criteria: Optional[Dict[str, Any]] = None,
        context_data: Optional[Dict[str, Any]] = None,
    ) -> ApprovalRequest:
        """
        创建审批请求

        Args:
            gate_id: 门禁 ID
            gate_name: 门禁名称
            workflow_id: 工作流 ID
            workflow_run_id: 工作流运行 ID
            stage_id: 阶段 ID
            step_id: 步骤 ID
            required_approvers: 必需审批人列表
            optional_approvers: 可选审批人列表
            approval_sla: 审批 SLA（小时）
            approval_criteria: 审批标准
            context_data: 上下文数据

        Returns:
            ApprovalRequest
        """
        import uuid

        request_id = str(uuid.uuid4())

        # 计算截止时间
        deadline = None
        if approval_sla:
            deadline = datetime.now() + timedelta(hours=approval_sla)

        request = ApprovalRequest(
            request_id=request_id,
            gate_id=gate_id,
            gate_name=gate_name,
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            stage_id=stage_id,
            step_id=step_id,
            required_approvers=required_approvers,
            optional_approvers=optional_approvers or [],
            approval_sla=approval_sla,
            approval_criteria=approval_criteria,
            context_data=context_data or {},
            deadline=deadline,
        )

        self._requests[request_id] = request
        self._decisions[request_id] = []

        # 发送通知
        self._send_notification(request, "created")

        # 持久化
        self._save()

        return request

    def get_request(self, request_id: str) -> Optional[ApprovalRequest]:
        """获取审批请求"""
        return self._requests.get(request_id)

    def list_requests(
        self,
        workflow_id: Optional[str] = None,
        status: Optional[ApprovalStatus] = None,
    ) -> List[ApprovalRequest]:
        """列出审批请求"""
        requests = list(self._requests.values())

        if workflow_id:
            requests = [r for r in requests if r.workflow_id == workflow_id]

        if status:
            requests = [r for r in requests if r.status == status]

        return requests

    # ========================================================================
    # 审批决策处理
    # ========================================================================

    def submit_decision(
        self,
        request_id: str,
        approver: str,
        approver_role: str,
        decision: ApprovalStatus,
        comments: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ApprovalDecision:
        """
        提交审批决策

        Args:
            request_id: 审批请求 ID
            approver: 审批人
            approver_role: 审批人角色
            decision: 决策
            comments: 评论
            metadata: 元数据

        Returns:
            ApprovalDecision
        """
        import uuid

        request = self._requests.get(request_id)
        if not request:
            raise ValueError(f"Request not found: {request_id}")

        if request.status != ApprovalStatus.PENDING:
            raise ValueError(f"Request is not pending: {request.status}")

        # 创建决策记录
        decision_id = str(uuid.uuid4())
        approval_decision = ApprovalDecision(
            decision_id=decision_id,
            request_id=request_id,
            approver=approver,
            approver_role=approver_role,
            decision=decision,
            comments=comments,
            metadata=metadata or {},
        )

        self._decisions[request_id].append(approval_decision)

        # 检查是否达到批准条件
        self._check_completion(request)

        # 持久化
        self._save()

        # 发送通知
        self._send_notification(request, "decision_updated", approval_decision)

        return approval_decision

    def get_decisions(self, request_id: str) -> List[ApprovalDecision]:
        """获取审批决策列表"""
        return self._decisions.get(request_id, [])

    # ========================================================================
    # 超时和升级处理
    # ========================================================================

    def check_timeouts(self) -> List[str]:
        """
        检查超时的审批请求

        Returns:
            超时的请求 ID 列表
        """
        now = datetime.now()
        timeout_requests = []

        for request_id, request in self._requests.items():
            if request.status == ApprovalStatus.PENDING and request.deadline:
                if now > request.deadline:
                    timeout_requests.append(request_id)
                    self._handle_timeout(request)

        return timeout_requests

    def _handle_timeout(self, request: ApprovalRequest) -> None:
        """处理超时"""
        request.status = ApprovalStatus.TIMEOUT
        request.completed_at = datetime.now()

        # 发送通知
        self._send_notification(request, "timeout")

        # 持久化
        self._save()

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _check_completion(self, request: ApprovalRequest) -> None:
        """检查审批是否完成"""
        decisions = self._decisions[request.request_id]

        # 统计批准和拒绝
        approved = sum(1 for d in decisions if d.decision == ApprovalStatus.APPROVED)
        rejected = sum(1 for d in decisions if d.decision == ApprovalStatus.REJECTED)

        # 检查是否达到最少批准数
        if approved >= request.min_required:
            request.status = ApprovalStatus.APPROVED
            request.completed_at = datetime.now()
            return

        # 检查是否有拒绝
        if rejected > 0:
            request.status = ApprovalStatus.REJECTED
            request.completed_at = datetime.now()
            return

        # 检查是否所有必需审批人都已决策
        required_approvers = {a.get("id") for a in request.required_approvers}
        approvers = {d.approver for d in decisions}
        if required_approvers.issubset(approvers):
            # 所有必需审批人都已决策
            if approved >= request.min_required:
                request.status = ApprovalStatus.APPROVED
            else:
                request.status = ApprovalStatus.REJECTED
            request.completed_at = datetime.now()

    def _send_notification(
        self,
        request: ApprovalRequest,
        event: str,
        decision: Optional[ApprovalDecision] = None,
    ) -> None:
        """发送通知"""
        # TODO: 实现通知机制
        # 这里可以集成邮件、Slack、企业微信等
        pass

    # ========================================================================
    # 持久化
    # ========================================================================

    def _save(self) -> None:
        """保存到文件"""
        if not self.storage_path:
            return

        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "requests": {
                rid: r.to_dict() for rid, r in self._requests.items()
            },
            "decisions": {
                rid: [d.to_dict() for d in decisions]
                for rid, decisions in self._decisions.items()
            },
        }

        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _load(self) -> None:
        """从文件加载"""
        if not self.storage_path or not self.storage_path.exists():
            return

        with open(self.storage_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        self._requests = {
            rid: ApprovalRequest.from_dict(r)
            for rid, r in data.get("requests", {}).items()
        }
        self._decisions = {
            rid: [ApprovalDecision.from_dict(d) for d in decisions]
            for rid, decisions in data.get("decisions", {}).items()
        }

    def get_summary(self) -> Dict[str, Any]:
        """获取审批摘要"""
        total = len(self._requests)
        pending = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.PENDING)
        approved = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.APPROVED)
        rejected = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.REJECTED)
        timeout = sum(1 for r in self._requests.values() if r.status == ApprovalStatus.TIMEOUT)

        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "timeout": timeout,
        }
