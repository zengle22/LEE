"""
test_state_machine_executor.py — StateMachineExecutor 单元测试

覆盖范围：
  - 初始化: WorkflowIR → StateMachineExecutor
  - can_transition_to(): 合法/非法转换检查
  - transition(): 触发转换 + 历史记录
  - try_transition_to(): 直接转换
  - 终态检查: is_completed, is_failed, is_terminal
  - 回调: on_state_enter, on_state_exit, on_transition
  - save_state() / get_state_summary()
"""

import json
import pytest
import tempfile
from pathlib import Path

from lee.orchestrator.execution.state_machine_executor import (
    StateMachineExecutor,
    StateTransitionResult,
    StateTransition,
    WorkflowState,
)
from lee.orchestrator.ir.models import (
    StateMachineIR,
    StateTransitionIR,
    WorkflowIR,
)


# ============================================================================
# Fixtures — 构建 3 状态的简易工作流 IR
# ============================================================================

def _make_workflow_ir() -> WorkflowIR:
    """
    INIT → (step_done) → RUNNING → (complete) → COMPLETED
                                   → (fail)     → FAILED
    """
    sm = StateMachineIR(
        states=["INIT", "RUNNING", "COMPLETED", "FAILED"],
        initial_state="INIT",
        transitions={
            "INIT": [
                StateTransitionIR(from_state="INIT", to_state="RUNNING", trigger="step_done"),
            ],
            "RUNNING": [
                StateTransitionIR(from_state="RUNNING", to_state="COMPLETED", trigger="complete"),
                StateTransitionIR(from_state="RUNNING", to_state="FAILED", trigger="fail"),
            ],
        },
    )
    return WorkflowIR(
        id="test-workflow",
        kind="workflow",
        version="1.0",
        name="Test Workflow",
        description="A test workflow for unit tests",
        state_machine=sm,
    )


@pytest.fixture
def workflow_ir():
    return _make_workflow_ir()


@pytest.fixture
def executor(workflow_ir):
    return StateMachineExecutor(workflow_ir)


# ============================================================================
# 初始化
# ============================================================================

class TestInitialization:

    def test_initial_state(self, executor):
        assert executor.current_state == "INIT"

    def test_no_state_machine_raises(self):
        wf = WorkflowIR(
            id="no-sm", kind="workflow", version="1.0",
            name="No SM", description="", state_machine=None,
        )
        with pytest.raises(ValueError, match="does not have a state machine"):
            StateMachineExecutor(wf)

    def test_empty_history(self, executor):
        assert executor.transition_history == []


# ============================================================================
# can_transition_to
# ============================================================================

class TestCanTransitionTo:

    def test_valid_transition(self, executor):
        assert executor.can_transition_to("RUNNING") is True

    def test_invalid_transition(self, executor):
        """从 INIT 不能直接到 COMPLETED"""
        assert executor.can_transition_to("COMPLETED") is False

    def test_nonexistent_state(self, executor):
        assert executor.can_transition_to("NONEXISTENT") is False


# ============================================================================
# transition
# ============================================================================

class TestTransition:

    def test_successful_transition(self, executor):
        result = executor.transition("step_done")
        assert result == StateTransitionResult.SUCCESS
        assert executor.current_state == "RUNNING"

    def test_invalid_trigger(self, executor):
        result = executor.transition("nonexistent_trigger")
        assert result == StateTransitionResult.INVALID_TRANSITION
        assert executor.current_state == "INIT"  # 状态不变

    def test_transition_records_history(self, executor):
        executor.transition("step_done")
        assert len(executor.transition_history) == 1
        t = executor.transition_history[0]
        assert t.from_state == "INIT"
        assert t.to_state == "RUNNING"
        assert t.trigger == "step_done"
        assert t.result == StateTransitionResult.SUCCESS

    def test_multi_step_transition(self, executor):
        executor.transition("step_done")
        executor.transition("complete")
        assert executor.current_state == "COMPLETED"
        assert len(executor.transition_history) == 2

    def test_transition_with_metadata(self, executor):
        executor.transition("step_done", metadata={"reason": "test"})
        t = executor.transition_history[0]
        assert t.metadata == {"reason": "test"}


# ============================================================================
# try_transition_to
# ============================================================================

class TestTryTransitionTo:

    def test_try_valid(self, executor):
        result = executor.try_transition_to("RUNNING")
        assert result == StateTransitionResult.SUCCESS
        assert executor.current_state == "RUNNING"

    def test_try_invalid(self, executor):
        result = executor.try_transition_to("COMPLETED")
        assert result == StateTransitionResult.INVALID_TRANSITION
        assert executor.current_state == "INIT"


# ============================================================================
# 终态检查
# ============================================================================

class TestTerminalChecks:

    def test_not_terminal_initially(self, executor):
        assert executor.is_terminal is False
        assert executor.is_completed is False
        assert executor.is_failed is False
        assert executor.is_blocked is False

    def test_completed(self, executor):
        executor.transition("step_done")
        executor.transition("complete")
        assert executor.is_completed is True
        assert executor.is_terminal is True
        assert executor.is_failed is False

    def test_failed(self, executor):
        executor.transition("step_done")
        executor.transition("fail")
        assert executor.is_failed is True
        assert executor.is_terminal is True
        assert executor.is_completed is False


# ============================================================================
# 回调
# ============================================================================

class TestCallbacks:

    def test_on_state_enter(self, executor):
        entered = []
        executor.on_state_enter(lambda s: entered.append(s))
        executor.transition("step_done")
        assert entered == ["RUNNING"]

    def test_on_state_exit(self, executor):
        exited = []
        executor.on_state_exit(lambda s: exited.append(s))
        executor.transition("step_done")
        assert exited == ["INIT"]

    def test_on_transition(self, executor):
        transitions = []
        executor.on_transition(lambda t: transitions.append(t))
        executor.transition("step_done")
        assert len(transitions) == 1
        assert isinstance(transitions[0], StateTransition)
        assert transitions[0].to_state == "RUNNING"

    def test_callback_exception_does_not_block(self, executor):
        """回调抛异常不应阻止状态转换"""
        executor.on_state_enter(lambda s: (_ for _ in ()).throw(RuntimeError("boom")))
        result = executor.transition("step_done")
        assert result == StateTransitionResult.SUCCESS
        assert executor.current_state == "RUNNING"


# ============================================================================
# 持久化
# ============================================================================

class TestPersistence:

    def test_save_and_load(self, executor, workflow_ir):
        executor.transition("step_done")
        executor.context["key"] = "value"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = str(Path(tmpdir) / "state.json")
            executor.save_state(path)

            # 验证文件存在且有效 JSON
            with open(path, "r") as f:
                data = json.load(f)
            assert data["current_state"] == "RUNNING"
            assert data["context"]["key"] == "value"

            # 加载
            loaded = StateMachineExecutor.load_state(path, workflow_ir)
            assert loaded.current_state == "RUNNING"
            assert loaded.context["key"] == "value"
            assert len(loaded.transition_history) == 1


# ============================================================================
# get_state_summary / get_transition_history
# ============================================================================

class TestSummaryAndHistory:

    def test_state_summary(self, executor):
        summary = executor.get_state_summary()
        assert summary["workflow_id"] == "test-workflow"
        assert summary["current_state"] == "INIT"
        assert summary["is_terminal"] is False
        assert summary["total_transitions"] == 0

    def test_state_summary_after_transition(self, executor):
        executor.transition("step_done")
        summary = executor.get_state_summary()
        assert summary["current_state"] == "RUNNING"
        assert summary["total_transitions"] == 1

    def test_transition_history_limit(self, executor):
        executor.transition("step_done")
        executor.transition("complete")
        history = executor.get_transition_history(limit=1)
        assert len(history) == 1
        assert history[0]["to_state"] == "COMPLETED"

    def test_transition_history_full(self, executor):
        executor.transition("step_done")
        executor.transition("complete")
        history = executor.get_transition_history()
        assert len(history) == 2


# ============================================================================
# StateTransition 序列化
# ============================================================================

class TestStateTransitionSerialization:

    def test_to_dict_roundtrip(self, executor):
        executor.transition("step_done")
        t = executor.transition_history[0]
        d = t.to_dict()
        reconstructed = StateTransition.from_dict(d)
        assert reconstructed.from_state == t.from_state
        assert reconstructed.to_state == t.to_state
        assert reconstructed.trigger == t.trigger
        assert reconstructed.result == t.result
