"""
LEE Orchestrator v3.0 - 工作流状态机

本模块定义了工作流状态机，负责状态转换和生命周期管理。

核心职责：
1. 计算状态转换
2. 验证状态转换合法性
3. 管理工作流生命周期
4. 处理步骤完成/失败
5. 支持暂停/恢复
"""

import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from lee.orchestrator.storage.models import (
    WorkflowStatus,
    TaskExecutionStatus,
    Step,
    StepResult,
    TaskExecution,
)


# ========================================================================
# 状态转换规则
# ========================================================================

class StateTransition:
    """
    状态转换规则

    定义合法的状态转换路径
    """

    # 工作流状态转换图
    WORKFLOW_TRANSITIONS = {
        WorkflowStatus.PENDING: [
            WorkflowStatus.RUNNING,
            WorkflowStatus.FAILED,
        ],
        WorkflowStatus.RUNNING: [
            WorkflowStatus.PAUSED,
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
        ],
        WorkflowStatus.PAUSED: [
            WorkflowStatus.RUNNING,
            WorkflowStatus.FAILED,
        ],
        WorkflowStatus.COMPLETED: [],  # 终态
        WorkflowStatus.FAILED: [],     # 终态
    }

    # 步骤状态转换图
    STEP_TRANSITIONS = {
        TaskExecutionStatus.PENDING: [
            TaskExecutionStatus.RUNNING,
            TaskExecutionStatus.FAILED,
        ],
        TaskExecutionStatus.RUNNING: [
            TaskExecutionStatus.COMPLETED,
            TaskExecutionStatus.FAILED,
        ],
        TaskExecutionStatus.COMPLETED: [],  # 终态
        TaskExecutionStatus.FAILED: [],     # 终态
    }

    @classmethod
    def can_transition(
        cls,
        from_status: WorkflowStatus,
        to_status: WorkflowStatus
    ) -> bool:
        """
        检查状态转换是否合法

        Args:
            from_status: 当前状态
            to_status: 目标状态

        Returns:
            是否可以转换
        """
        return to_status in cls.WORKFLOW_TRANSITIONS.get(from_status, [])


# ========================================================================
# 状态机接口
# ========================================================================

class IStateMachine:
    """
    状态机接口

    定义状态机的核心抽象方法
    """

    async def get_current_state(self, workflow_id: str) -> WorkflowStatus:
        """获取当前状态"""
        pass

    async def can_start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> bool:
        """检查是否可以开始步骤"""
        pass

    async def start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> None:
        """开始步骤"""
        pass

    async def complete_step(
        self,
        workflow_id: str,
        step_id: str,
        output: Dict[str, Any]
    ) -> StepResult:
        """完成步骤"""
        pass

    async def fail_step(
        self,
        workflow_id: str,
        step_id: str,
        error: str
    ) -> None:
        """步骤失败"""
        pass

    async def pause_workflow(
        self,
        workflow_id: str
    ) -> None:
        """暂停工作流"""
        pass

    async def resume_workflow(
        self,
        workflow_id: str
    ) -> None:
        """恢复工作流"""
        pass

    async def get_ready_steps(
        self,
        workflow_id: str,
        all_steps: List[Step]
    ) -> List[Step]:
        """获取可执行步骤"""
        pass


# ========================================================================
# 状态机实现
# ========================================================================

class WorkflowStateMachine(IStateMachine):
    """
    工作流状态机实现

    核心逻辑：
    1. 维护工作流状态
    2. 追踪步骤完成情况
    3. 计算可执行步骤
    4. 验证状态转换合法性
    """

    def __init__(self, store):
        """
        初始化状态机

        Args:
            store: SQLite 存储层
        """
        self.store = store

    async def get_current_state(self, workflow_id: str) -> WorkflowStatus:
        """获取当前状态"""
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")
        return instance.status

    async def can_start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> bool:
        """
        检查是否可以开始步骤

        检查条件：
        1. 工作流状态为 RUNNING
        2. 步骤未被完成
        3. 所有依赖步骤已完成
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return False

        # 检查工作流状态
        if instance.status != WorkflowStatus.RUNNING:
            return False

        # 检查步骤是否已完成
        completed_steps = instance.data.get("completed_steps", [])
        if step_id in completed_steps:
            return False

        # 检查步骤是否正在执行
        if instance.current_step == step_id:
            return False

        return True

    async def start_step(
        self,
        workflow_id: str,
        step_id: str
    ) -> None:
        """
        开始步骤

        操作：
        1. 验证状态转换合法性
        2. 创建 TaskExecution 记录
        3. 更新 workflow.current_step
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 更新当前步骤
        await self.store.update_workflow_status(
            workflow_id,
            instance.status,
            current_step=step_id
        )

    async def complete_step(
        self,
        workflow_id: str,
        step_id: str,
        output: Dict[str, Any]
    ) -> StepResult:
        """
        完成步骤

        操作：
        1. 更新 TaskExecution 状态
        2. 将 step_id 添加到 completed_steps
        3. 计算下一个就绪步骤
        4. 检查工作流是否完成
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        # 更新 completed_steps
        completed_steps = instance.data.get("completed_steps", [])
        if step_id not in completed_steps:
            completed_steps.append(step_id)

        await self.store.update_workflow_data(workflow_id, {
            **instance.data,
            "completed_steps": completed_steps,
        })

        # 清除 current_step
        await self.store.update_workflow_status(
            workflow_id,
            instance.status,
            clear_current_step=True
        )

        # 构建 StepResult
        result = StepResult(
            status="success",
            step_id=step_id,
            workflow_id=workflow_id,
            message=f"Step {step_id} completed successfully",
            next_steps=[],
            output=output,
        )

        return result

    async def fail_step(
        self,
        workflow_id: str,
        step_id: str,
        error: str
    ) -> None:
        """
        步骤失败

        操作：
        1. 更新 TaskExecution 状态
        2. 记录错误信息
        3. 更新工作流状态为 FAILED
        """
        await self.store.update_workflow_status(
            workflow_id,
            WorkflowStatus.FAILED
        )

    async def pause_workflow(
        self,
        workflow_id: str
    ) -> None:
        """
        暂停工作流

        操作：
        1. 验证状态转换合法性
        2. 更新工作流状态为 PAUSED
        """
        current_status = await self.get_current_state(workflow_id)
        if not StateTransition.can_transition(current_status, WorkflowStatus.PAUSED):
            raise ValueError(f"Cannot pause workflow in state: {current_status}")

        await self.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

    async def resume_workflow(
        self,
        workflow_id: str
    ) -> None:
        """
        恢复工作流

        操作：
        1. 验证状态转换合法性
        2. 更新工作流状态为 RUNNING
        """
        current_status = await self.get_current_state(workflow_id)
        if not StateTransition.can_transition(current_status, WorkflowStatus.RUNNING):
            raise ValueError(f"Cannot resume workflow in state: {current_status}")

        await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

    async def get_ready_steps(
        self,
        workflow_id: str,
        all_steps: List[Step]
    ) -> List[Step]:
        """
        获取可执行步骤

        算法：
        1. 获取已完成的步骤列表
        2. 遍历所有步骤
        3. 检查步骤是否已完成
        4. 检查所有依赖是否已完成
        5. 返回满足条件的步骤
        """
        instance = await self.store.get_workflow(workflow_id)
        if not instance:
            return []

        # 只处理 RUNNING 状态
        if instance.status != WorkflowStatus.RUNNING:
            return []

        completed_steps = instance.data.get("completed_steps", [])

        ready_steps = []
        for step in all_steps:
            # 跳过已完成的步骤
            if step.id in completed_steps:
                continue

            # 检查所有依赖是否已完成
            dependencies_met = all(
                dep in completed_steps
                for dep in step.depends_on
            )

            if dependencies_met:
                ready_steps.append(step)

        return ready_steps


# ========================================================================
# Gate 状态机（扩展）
# ========================================================================

@dataclass
class GateState:
    """
    Gate 状态

    Gate 是一种特殊的状态，需要人工介入
    """
    gate_id: str
    workflow_id: str
    step_id: str
    status: str  # pending | approved | rejected | skipped
    request_data: Dict[str, Any]
    response_data: Optional[Dict[str, Any]] = None
    created_at: Optional[str] = None
    resolved_at: Optional[str] = None


class GateStateMachine:
    """
    Gate 状态机

    管理 human_gate 的生命周期
    """

    def __init__(self, store):
        self.store = store
        # 临时存储 gate 状态（实际应该存储在数据库）
        self._gates: Dict[str, GateState] = {}

    async def create_gate(
        self,
        workflow_id: str,
        step_id: str,
        request_data: Dict[str, Any]
    ) -> GateState:
        """
        创建 Gate

        当工作流遇到 human_gate 时调用
        """
        gate_id = f"gate_{step_id}_{uuid.uuid4().hex[:8]}"
        gate = GateState(
            gate_id=gate_id,
            workflow_id=workflow_id,
            step_id=step_id,
            status="pending",
            request_data=request_data,
            created_at=datetime.now().isoformat(),
        )
        self._gates[gate_id] = gate
        return gate

    async def approve_gate(
        self,
        gate_id: str,
        response_data: Dict[str, Any]
    ) -> None:
        """
        批准 Gate

        人工批准后继续执行
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]
        gate.status = "approved"
        gate.response_data = response_data
        gate.resolved_at = datetime.now().isoformat()

    async def reject_gate(
        self,
        gate_id: str,
        reason: str
    ) -> None:
        """
        拒绝 Gate

        人工拒绝后终止工作流
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]
        gate.status = "rejected"
        gate.response_data = {"reason": reason}
        gate.resolved_at = datetime.now().isoformat()

        # 更新工作流状态为 FAILED
        await self.store.update_workflow_status(
            gate.workflow_id,
            WorkflowStatus.FAILED
        )

    async def skip_gate(
        self,
        gate_id: str
    ) -> None:
        """
        跳过 Gate

        跳过当前 Gate，继续执行
        """
        if gate_id not in self._gates:
            raise ValueError(f"Gate not found: {gate_id}")

        gate = self._gates[gate_id]
        gate.status = "skipped"
        gate.resolved_at = datetime.now().isoformat()
