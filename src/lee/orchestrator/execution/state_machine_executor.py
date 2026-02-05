"""
LEE Orchestrator - State Machine Executor

状态机执行引擎，负责工作流状态转换的管理和执行。

核心功能：
1. 状态转换验证：检查转换是否合法
2. 状态转换执行：执行状态转换逻辑
3. 状态持久化：保存和恢复状态
4. 触发器处理：处理各种触发条件
5. 回调机制：状态转换时的回调钩子
"""

import json
import time
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable, TYPE_CHECKING

from lee.orchestrator.ir.models import (
    StateMachineIR,
    StateTransitionIR,
    WorkflowIR,
)

if TYPE_CHECKING:
    from lee.orchestrator.execution.gate_engine import GateEngine
    from lee.orchestrator.execution.human_approval import HumanApprovalExecutor


class WorkflowState(Enum):
    """工作流状态枚举"""

    # 基础状态
    INIT = "INIT"
    INPUT_VALIDATION = "INPUT_VALIDATION"
    REQUIREMENT_ALIGNMENT = "REQUIREMENT_ALIGNMENT"
    FEATURE_CALIBRATION = "FEATURE_CALIBRATION"
    BRANCH_COVERAGE_DESIGN = "BRANCH_COVERAGE_DESIGN"
    SPECIALIZED_TEST_DESIGN = "SPECIALIZED_TEST_DEVIEW"
    TEST_CASE_REVIEW = "TEST_CASE_REVIEW"
    REVIEW_REVISION = "REVIEW_REVISION"
    PLAYWRIGHT_GENERATION = "PLAYWRIGHT_GENERATION"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"

    # 元状态
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    TIMEOUT = "TIMEOUT"

    def __str__(self):
        return self.value


class StateTransitionResult(Enum):
    """状态转换结果"""

    SUCCESS = "success"
    INVALID_TRANSITION = "invalid_transition"
    TRIGGER_NOT_MET = "trigger_not_met"
    CONDITION_FAILED = "condition_failed"
    GATE_FAILED = "gate_failed"
    HUMAN_REJECTED = "human_rejected"
    TIMEOUT = "timeout"
    ERROR = "error"

    def __str__(self):
        return self.value


class StateTransition:
    """状态转换记录"""

    def __init__(
        self,
        from_state: str,
        to_state: str,
        trigger: str,
        result: StateTransitionResult,
        timestamp: datetime,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.from_state = from_state
        self.to_state = to_state
        self.trigger = trigger
        self.result = result
        self.timestamp = timestamp
        self.error_message = error_message
        self.metadata = metadata or {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "from_state": self.from_state,
            "to_state": self.to_state,
            "trigger": self.trigger,
            "result": str(self.result),
            "timestamp": self.timestamp.isoformat(),
            "error_message": self.error_message,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StateTransition":
        """从字典创建"""
        return cls(
            from_state=data["from_state"],
            to_state=data["to_state"],
            trigger=data["trigger"],
            result=StateTransitionResult(data["result"]),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            error_message=data.get("error_message"),
            metadata=data.get("metadata", {}),
        )


class StateMachineExecutor:
    """
    状态机执行引擎

    职责：
    1. 管理当前状态
    2. 验证状态转换
    3. 执行状态转换
    4. 记录转换历史
    5. 持久化状态
    """

    def __init__(
        self,
        workflow_ir: WorkflowIR,
        gate_engine: Optional["GateEngine"] = None,
        human_approval: Optional["HumanApprovalExecutor"] = None,
    ):
        """
        初始化状态机执行器

        Args:
            workflow_ir: 工作流 IR
            gate_engine: 门禁引擎（可选）
            human_approval: 人工审批执行器（可选）
        """
        self.workflow_ir = workflow_ir
        self.gate_engine = gate_engine
        self.human_approval = human_approval

        # 状态机定义
        self.sm_ir = workflow_ir.state_machine
        if not self.sm_ir:
            raise ValueError("Workflow does not have a state machine definition")

        # 当前状态
        self.current_state = self.sm_ir.initial_state

        # 转换历史
        self.transition_history: List[StateTransition] = []

        # 回调函数
        self._on_state_enter: Optional[Callable[[str], None]] = None
        self._on_state_exit: Optional[Callable[[str], None]] = None
        self._on_transition: Optional[Callable[[StateTransition], None]] = None

        # 上下文数据
        self.context: Dict[str, Any] = {}

        # 状态数据（每个状态的数据）
        self.state_data: Dict[str, Dict[str, Any]] = {}

        # 开始时间
        self.start_time = datetime.now()

        # 状态统计
        self.state_times: Dict[str, float] = {}
        self._state_start_time: Dict[str, datetime] = {}

        # 记录初始状态时间
        self._state_start_time[self.current_state] = self.start_time

    # ========================================================================
    # 状态查询
    # ========================================================================

    @property
    def is_completed(self) -> bool:
        """是否完成"""
        return self.current_state == "COMPLETED"

    @property
    def is_blocked(self) -> bool:
        """是否阻塞"""
        return self.current_state == "BLOCKED"

    @property
    def is_failed(self) -> bool:
        """是否失败"""
        return self.current_state in ("FAILED", "TIMEOUT")

    @property
    def is_terminal(self) -> bool:
        """是否终态"""
        return self.current_state in ("COMPLETED", "BLOCKED", "FAILED", "CANCELLED", "TIMEOUT")

    def get_valid_transitions(self) -> List[str]:
        """获取当前状态的所有有效转换目标"""
        return self.sm_ir.transitions.get(self.current_state, [])

    def can_transition_to(self, target_state: str) -> bool:
        """检查是否可以转换到目标状态"""
        valid_transitions = self.get_valid_transitions()
        return any(t.to_state == target_state for t in valid_transitions)

    # ========================================================================
    # 状态转换
    # ========================================================================

    def transition(
        self,
        trigger: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateTransitionResult:
        """
        执行状态转换

        Args:
            trigger: 触发条件
            metadata: 转换元数据

        Returns:
            转换结果
        """
        # 记录转换开始时间
        transition_time = datetime.now()

        # 查找匹配的转换规则
        transition_rule = self._find_transition(trigger)
        if not transition_rule:
            result = StateTransitionResult.INVALID_TRANSITION
            self._record_transition(self.current_state, self.current_state, trigger, result, transition_time, "No matching transition rule", metadata)
            return result

        target_state = transition_rule.to_state

        # 执行状态退出回调
        if self._on_state_exit:
            try:
                self._on_state_exit(self.current_state)
            except Exception as e:
                # 回调失败不应阻止转换
                pass

        # 记录状态时间
        self._record_state_time(self.current_state)

        # 更新状态
        from_state = self.current_state
        self.current_state = target_state
        self._state_start_time[target_state] = transition_time

        # 初始化状态数据
        if target_state not in self.state_data:
            self.state_data[target_state] = {}

        # 执行状态进入回调
        if self._on_state_enter:
            try:
                self._on_state_enter(target_state)
            except Exception as e:
                # 回调失败不应阻止转换
                pass

        # 记录转换
        result = StateTransitionResult.SUCCESS
        self._record_transition(from_state, target_state, trigger, result, transition_time, None, metadata)

        # 执行转换回调
        if self._on_transition:
            transition = self.transition_history[-1]
            try:
                self._on_transition(transition)
            except Exception as e:
                # 回调失败不应阻止转换
                pass

        return result

    def try_transition_to(
        self,
        target_state: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> StateTransitionResult:
        """
        尝试转换到指定状态

        Args:
            target_state: 目标状态
            metadata: 转换元数据

        Returns:
            转换结果
        """
        if not self.can_transition_to(target_state):
            return StateTransitionResult.INVALID_TRANSITION

        # 找到对应的触发条件
        transition_rule = next(
            (t for t in self.get_valid_transitions() if t.to_state == target_state),
            None
        )
        if not transition_rule:
            return StateTransitionResult.INVALID_TRANSITION

        return self.transition(transition_rule.trigger, metadata)

    # ========================================================================
    # 回调设置
    # ========================================================================

    def on_state_enter(self, callback: Callable[[str], None]) -> None:
        """设置状态进入回调"""
        self._on_state_enter = callback

    def on_state_exit(self, callback: Callable[[str], None]) -> None:
        """设置状态退出回调"""
        self._on_state_exit = callback

    def on_transition(self, callback: Callable[[StateTransition], None]) -> None:
        """设置转换回调"""
        self._on_transition = callback

    # ========================================================================
    # 持久化
    # ========================================================================

    def save_state(self, file_path: str) -> None:
        """
        保存当前状态到文件

        Args:
            file_path: 文件路径
        """
        state_data = {
            "workflow_id": self.workflow_ir.id,
            "current_state": self.current_state,
            "context": self.context,
            "state_data": self.state_data,
            "state_times": self.state_times,
            "start_time": self.start_time.isoformat(),
            "transition_history": [t.to_dict() for t in self.transition_history],
            "saved_at": datetime.now().isoformat(),
        }

        file_path = Path(file_path)
        file_path.parent.mkdir(parents=True, exist_ok=True)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(state_data, f, indent=2, ensure_ascii=False)

    @classmethod
    def load_state(
        cls,
        file_path: str,
        workflow_ir: WorkflowIR,
        gate_engine: Optional["GateEngine"] = None,
        human_approval: Optional["HumanApprovalExecutor"] = None,
    ) -> "StateMachineExecutor":
        """
        从文件加载状态

        Args:
            file_path: 文件路径
            workflow_ir: 工作流 IR
            gate_engine: 门禁引擎（可选）
            human_approval: 人工审批执行器（可选）

        Returns:
            StateMachineExecutor 实例
        """
        with open(file_path, 'r', encoding='utf-8') as f:
            state_data = json.load(f)

        # 创建执行器
        executor = cls(workflow_ir, gate_engine, human_approval)

        # 恢复状态
        executor.current_state = state_data["current_state"]
        executor.context = state_data.get("context", {})
        executor.state_data = state_data.get("state_data", {})
        executor.state_times = state_data.get("state_times", {})
        executor.start_time = datetime.fromisoformat(state_data["start_time"])

        # 恢复转换历史
        executor.transition_history = [
            StateTransition.from_dict(t) for t in state_data.get("transition_history", [])
        ]

        return executor

    # ========================================================================
    # 辅助方法
    # ========================================================================

    def _find_transition(self, trigger: str) -> Optional[StateTransitionIR]:
        """查找匹配的转换规则"""
        transitions = self.sm_ir.transitions.get(self.current_state, [])
        for trans in transitions:
            if trans.trigger == trigger:
                return trans
        return None

    def _record_transition(
        self,
        from_state: str,
        to_state: str,
        trigger: str,
        result: StateTransitionResult,
        timestamp: datetime,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """记录转换"""
        transition = StateTransition(
            from_state=from_state,
            to_state=to_state,
            trigger=trigger,
            result=result,
            timestamp=timestamp,
            error_message=error_message,
            metadata=metadata,
        )
        self.transition_history.append(transition)

    def _record_state_time(self, state: str) -> None:
        """记录状态持续时间"""
        if state in self._state_start_time:
            duration = (datetime.now() - self._state_start_time[state]).total_seconds()
            if state not in self.state_times:
                self.state_times[state] = 0
            self.state_times[state] += duration

    def get_state_summary(self) -> Dict[str, Any]:
        """获取状态摘要"""
        return {
            "workflow_id": self.workflow_ir.id,
            "current_state": self.current_state,
            "is_terminal": self.is_terminal,
            "total_transitions": len(self.transition_history),
            "state_times": self.state_times,
            "elapsed_time": (datetime.now() - self.start_time).total_seconds(),
        }

    def get_transition_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取转换历史"""
        history = [t.to_dict() for t in self.transition_history]
        if limit:
            return history[-limit:]
        return history
