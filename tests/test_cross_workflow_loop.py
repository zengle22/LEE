"""
Tests for LEE CrossWorkflowLoopController — L3 跨工作流收敛循环

Tests:
1. IR Models: CrossWorkflowLoopConvergenceIR, CrossWorkflowLoopPhaseIR, CrossWorkflowLoopIR defaults
2. CrossWorkflowLoopState defaults
3. Controller: convergence on first round
4. Controller: max rounds exceeded
5. Controller: multi-phase QA→Dev→QA
6. Controller: bug count trend tracking
7. Controller: phase condition evaluation
8. Controller: disabled mode (single run)
9. Controller: context injection
10. Controller: evidence recording with mock collector
11. Controller: summary generation
12. SubworkflowMixin: phase condition evaluation
"""

import pytest
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock

from lee.orchestrator.ir.models import (
    CrossWorkflowLoopConvergenceIR,
    CrossWorkflowLoopPhaseIR,
    CrossWorkflowLoopIR,
)
from lee.orchestrator.execution.cross_workflow_loop import (
    CrossWorkflowLoopController,
    CrossWorkflowLoopState,
)
from lee.orchestrator.execution.subworkflow_ops import SubworkflowMixin


# ========================================================================
# IR Model Tests
# ========================================================================

class TestCrossWorkflowLoopConvergenceIR:
    def test_defaults(self):
        c = CrossWorkflowLoopConvergenceIR()
        assert c.check_phase == ""
        assert c.check_field == "exit_decision"
        assert c.pass_values == ["pass", "conditional_pass"]
        assert c.secondary_check is None

    def test_custom_values(self):
        c = CrossWorkflowLoopConvergenceIR(
            check_phase="qa_test",
            check_field="status",
            pass_values=["pass"],
            secondary_check="open_bug_count == 0",
        )
        assert c.check_phase == "qa_test"
        assert c.check_field == "status"
        assert c.pass_values == ["pass"]
        assert c.secondary_check == "open_bug_count == 0"


class TestCrossWorkflowLoopPhaseIR:
    def test_defaults(self):
        p = CrossWorkflowLoopPhaseIR()
        assert p.id == ""
        assert p.workflow_ref == ""
        assert p.role == ""
        assert p.condition is None
        assert p.inputs_from == []

    def test_qa_phase(self):
        p = CrossWorkflowLoopPhaseIR(
            id="qa_test",
            workflow_ref="workflow.qa.test_plan_execution_v1",
            role="tester",
        )
        assert p.id == "qa_test"
        assert p.workflow_ref == "workflow.qa.test_plan_execution_v1"
        assert p.role == "tester"


class TestCrossWorkflowLoopIR:
    def test_defaults(self):
        loop = CrossWorkflowLoopIR()
        assert loop.enabled is False
        assert loop.max_rounds == 3
        assert loop.phases == []
        assert loop.convergence is None
        assert loop.on_exceeded == "human_gate"

    def test_full_config(self):
        loop = CrossWorkflowLoopIR(
            enabled=True,
            max_rounds=5,
            phases=[
                CrossWorkflowLoopPhaseIR(id="qa_test", workflow_ref="wf.qa", role="tester"),
                CrossWorkflowLoopPhaseIR(id="dev_fix", workflow_ref="wf.dev", role="fixer"),
            ],
            convergence=CrossWorkflowLoopConvergenceIR(
                check_phase="qa_test",
                check_field="exit_decision",
            ),
        )
        assert loop.enabled is True
        assert loop.max_rounds == 5
        assert len(loop.phases) == 2
        assert loop.convergence.check_phase == "qa_test"


# ========================================================================
# State Tests
# ========================================================================

class TestCrossWorkflowLoopState:
    def test_defaults(self):
        s = CrossWorkflowLoopState()
        assert s.current_round == 0
        assert s.current_phase_idx == 0
        assert s.max_rounds == 3
        assert s.status == "running"
        assert s.round_results == []
        assert s.bug_counts == []


# ========================================================================
# Controller Tests
# ========================================================================

def _make_config(
    enabled=True,
    max_rounds=3,
    check_phase="qa_test",
    check_field="exit_decision",
    pass_values=None,
    phases=None,
):
    """Helper to build a CrossWorkflowLoopIR config"""
    if pass_values is None:
        pass_values = ["pass", "conditional_pass"]
    if phases is None:
        phases = [
            CrossWorkflowLoopPhaseIR(id="qa_test", workflow_ref="wf.qa", role="tester"),
            CrossWorkflowLoopPhaseIR(
                id="dev_fix",
                workflow_ref="wf.dev",
                role="fixer",
                condition="qa_test.exit_decision == 'fail'",
            ),
        ]
    return CrossWorkflowLoopIR(
        enabled=enabled,
        max_rounds=max_rounds,
        phases=phases,
        convergence=CrossWorkflowLoopConvergenceIR(
            check_phase=check_phase,
            check_field=check_field,
            pass_values=pass_values,
        ),
    )


class TestControllerConvergence:
    """测试收敛判定"""

    def test_converged_on_first_round(self):
        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-1")

        assert ctrl.should_continue()

        # QA phase: 直接 pass
        phase = ctrl.get_current_phase()
        assert phase["id"] == "qa_test"

        decision = ctrl.record_phase_result({"exit_decision": "pass", "open_bug_count": 0})
        assert decision == "converged"
        assert ctrl.state.status == "converged"
        assert not ctrl.should_continue()

    def test_converged_conditional_pass(self):
        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-2")

        decision = ctrl.record_phase_result({"exit_decision": "conditional_pass"})
        assert decision == "converged"

    def test_not_converged_fail(self):
        config = _make_config(max_rounds=5)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-3")

        decision = ctrl.record_phase_result({"exit_decision": "fail", "open_bug_count": 5})
        assert decision == "continue"
        assert ctrl.state.status == "running"


class TestControllerMaxRounds:
    """测试最大轮次超限"""

    def test_max_rounds_exceeded(self):
        config = _make_config(max_rounds=1)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-4")

        # Round 0: QA fails → 这是最后一轮
        decision = ctrl.record_phase_result({"exit_decision": "fail"})
        assert decision == "stop_max"
        assert ctrl.state.status == "max_exceeded"

    def test_should_continue_false_after_max(self):
        config = _make_config(max_rounds=2)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-5")

        # Round 0: QA fail → continue
        ctrl.record_phase_result({"exit_decision": "fail"})
        ctrl.advance_phase()  # → dev_fix
        ctrl.record_phase_result({"status": "completed"})
        ctrl.advance_phase()  # → round 1, qa_test

        # Round 1: QA fail → stop_max (round 1 >= max_rounds - 1 = 1)
        decision = ctrl.record_phase_result({"exit_decision": "fail"})
        assert decision == "stop_max"


class TestControllerMultiPhase:
    """测试多 phase 推进"""

    def test_phase_advancement(self):
        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-6")

        # Start at phase 0 (qa_test), round 0
        assert ctrl.state.current_phase_idx == 0
        assert ctrl.state.current_round == 0

        ctrl.advance_phase()
        assert ctrl.state.current_phase_idx == 1  # dev_fix
        assert ctrl.state.current_round == 0

        ctrl.advance_phase()
        assert ctrl.state.current_phase_idx == 0  # back to qa_test
        assert ctrl.state.current_round == 1      # round incremented

    def test_full_qa_dev_qa_loop(self):
        """完整 QA→Dev→QA 乒乓"""
        config = _make_config(max_rounds=3)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-7")

        # Round 0: QA fail
        assert ctrl.should_continue()
        decision = ctrl.record_phase_result({"exit_decision": "fail", "open_bug_count": 5})
        assert decision == "continue"

        # Round 0: Dev fix
        ctrl.advance_phase()
        decision = ctrl.record_phase_result({"status": "completed"})
        assert decision == "continue"  # dev_fix is not check_phase

        # Round 1: QA pass
        ctrl.advance_phase()  # → round 1, qa_test
        assert ctrl.state.current_round == 1
        decision = ctrl.record_phase_result({"exit_decision": "pass", "open_bug_count": 0})
        assert decision == "converged"

        summary = ctrl.get_summary()
        assert summary["final_status"] == "converged"
        assert summary["bug_trend"] == [5, 0]


class TestControllerBugTrend:
    """测试 bug 数量趋势跟踪"""

    def test_bug_count_extraction(self):
        assert CrossWorkflowLoopController._extract_bug_count({"open_bug_count": 5}) == 5
        assert CrossWorkflowLoopController._extract_bug_count({"bug_count": 3}) == 3
        assert CrossWorkflowLoopController._extract_bug_count({"open_bugs": 2}) == 2
        assert CrossWorkflowLoopController._extract_bug_count({}) is None

    def test_bug_count_from_outputs(self):
        result = {"outputs": {"open_bug_count": 7}}
        assert CrossWorkflowLoopController._extract_bug_count(result) == 7

    def test_trend_tracking(self):
        config = _make_config(max_rounds=5)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-8")

        ctrl.record_phase_result({"exit_decision": "fail", "open_bug_count": 10})
        ctrl.advance_phase()
        ctrl.record_phase_result({"status": "completed"})
        ctrl.advance_phase()  # round 1

        ctrl.record_phase_result({"exit_decision": "fail", "open_bug_count": 3})

        assert ctrl.state.bug_counts == [10, 3]


class TestControllerDisabled:
    """测试禁用模式"""

    def test_disabled_runs_once(self):
        config = _make_config(enabled=False)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-9")

        # 第一次 should_continue → True
        assert ctrl.should_continue()

        ctrl.state.current_round = 1  # simulate advance

        # 第二次 → False（disabled 只允许一轮）
        assert not ctrl.should_continue()


class TestControllerContext:
    """测试上下文注入"""

    def test_basic_context(self):
        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-10")

        ctx = ctrl.get_loop_context()
        assert ctx["round"] == 0
        assert ctx["max_rounds"] == 3
        assert ctx["loop_status"] == "running"

    def test_context_with_previous_results(self):
        config = _make_config(max_rounds=5)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-11")

        ctrl.record_phase_result({"exit_decision": "fail", "status": "completed", "open_bug_count": 5})

        ctx = ctrl.get_loop_context()
        assert "previous_results" in ctx
        assert "previous_result_summary" in ctx
        assert ctx["bug_trend"] == [5]


class TestControllerEvidence:
    """测试证据记录"""

    def test_evidence_writing(self):
        mock_collector = MagicMock()
        mock_collector.write_artifact.return_value = "/evidence/path.json"

        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, evidence_collector=mock_collector, run_id="test-run-12")

        path = ctrl.write_round_evidence(0, "qa_test", {"exit_decision": "fail"})
        assert path == "/evidence/path.json"
        mock_collector.write_artifact.assert_called_once()

    def test_evidence_no_collector(self):
        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-13")

        path = ctrl.write_round_evidence(0, "qa_test", {"exit_decision": "fail"})
        assert path is None


class TestControllerSummary:
    """测试摘要生成"""

    def test_summary_after_convergence(self):
        config = _make_config()
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-14")

        ctrl.record_phase_result({"exit_decision": "pass", "open_bug_count": 0})

        summary = ctrl.get_summary()
        assert summary["final_status"] == "converged"
        assert summary["max_rounds"] == 3
        assert summary["total_phases_executed"] == 1
        assert summary["bug_trend"] == [0]
        assert summary["started_at"] is not None
        assert summary["completed_at"] is not None

    def test_summary_after_max_exceeded(self):
        config = _make_config(max_rounds=1)
        ctrl = CrossWorkflowLoopController(config, run_id="test-run-15")

        ctrl.record_phase_result({"exit_decision": "fail"})

        summary = ctrl.get_summary()
        assert summary["final_status"] == "max_exceeded"


class TestFieldExtraction:
    """测试字段提取"""

    def test_simple_field(self):
        assert CrossWorkflowLoopController._extract_field(
            {"exit_decision": "pass"}, "exit_decision"
        ) == "pass"

    def test_dotted_path(self):
        assert CrossWorkflowLoopController._extract_field(
            {"outputs": {"exit_decision": "fail"}}, "outputs.exit_decision"
        ) == "fail"

    def test_missing_field(self):
        assert CrossWorkflowLoopController._extract_field({}, "missing") is None


# ========================================================================
# SubworkflowMixin Phase Condition Tests
# ========================================================================

class TestPhaseConditionEvaluation:
    """测试 _evaluate_phase_condition 静态方法"""

    def test_equal_true(self):
        result = SubworkflowMixin._evaluate_phase_condition(
            "qa_test.exit_decision == 'fail'",
            {"qa_test": {"exit_decision": "fail"}},
        )
        assert result is True

    def test_equal_false(self):
        result = SubworkflowMixin._evaluate_phase_condition(
            "qa_test.exit_decision == 'fail'",
            {"qa_test": {"exit_decision": "pass"}},
        )
        assert result is False

    def test_not_equal(self):
        result = SubworkflowMixin._evaluate_phase_condition(
            "qa_test.exit_decision != 'pass'",
            {"qa_test": {"exit_decision": "fail"}},
        )
        assert result is True

    def test_missing_phase_defaults_true(self):
        result = SubworkflowMixin._evaluate_phase_condition(
            "qa_test.exit_decision == 'fail'",
            {},
        )
        # None != "fail" → False
        assert result is False

    def test_unparseable_defaults_false(self):
        result = SubworkflowMixin._evaluate_phase_condition(
            "some random condition string",
            {},
        )
        assert result is False

    def test_uppercase_logic_supported(self):
        result = SubworkflowMixin._evaluate_phase_condition(
            "qa_test.exit_decision == 'fail' AND qa_test.retry_count > 1",
            {"qa_test": {"exit_decision": "fail", "retry_count": 2}},
        )
        assert result is True
