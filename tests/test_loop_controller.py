"""
Tests for LEE LoopController — Auto-Fix Convergence Loop

Tests:
1. LoopConfigIR defaults and custom values
2. StageIR with loop config
3. LoopController basic convergence
4. LoopController max iterations exceeded
5. LoopController same output stop
6. LoopController loop context injection
7. LoopController disabled loop
8. LoopController evidence recording (mock)
"""

import pytest
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from lee.orchestrator.ir.models import LoopConfigIR, StageIR, StepIR, StepKind


# ── LoopConfigIR ───────────────────────────────────────────────────

class TestLoopConfigIR:
    def test_defaults(self):
        cfg = LoopConfigIR()
        assert cfg.enabled is False
        assert cfg.max_iterations == 3
        assert cfg.stop_on_same_output is True
        assert cfg.completion_check_step is None
        assert cfg.completion_status == "passed"

    def test_custom_values(self):
        cfg = LoopConfigIR(
            enabled=True,
            max_iterations=5,
            stop_on_same_output=False,
            completion_check_step="run_tests",
            completion_status="success",
        )
        assert cfg.enabled is True
        assert cfg.max_iterations == 5
        assert cfg.stop_on_same_output is False
        assert cfg.completion_check_step == "run_tests"
        assert cfg.completion_status == "success"


class TestStageIRWithLoop:
    def test_stage_without_loop(self):
        stage = StageIR(id="s1", name="Stage 1", description="desc")
        assert stage.loop is None

    def test_stage_with_loop(self):
        loop_cfg = LoopConfigIR(enabled=True, max_iterations=3)
        stage = StageIR(
            id="fix_loop",
            name="Auto-Fix Loop",
            description="patch → test → retry",
            loop=loop_cfg,
        )
        assert stage.loop is not None
        assert stage.loop.enabled is True
        assert stage.loop.max_iterations == 3


# ── LoopController ─────────────────────────────────────────────────

from lee.orchestrator.execution.loop_controller import LoopController, LoopState


class TestLoopState:
    def test_defaults(self):
        state = LoopState()
        assert state.current_iteration == 0
        assert state.max_iterations == 3
        assert state.output_hashes == []
        assert state.iteration_results == []
        assert state.status == "running"


class TestLoopControllerConvergence:
    """测试基本收敛场景：step 返回 passed → 第 N 轮停止"""

    def test_converges_on_second_iteration(self):
        cfg = LoopConfigIR(
            enabled=True,
            max_iterations=5,
            completion_check_step="run_tests",
            completion_status="passed",
        )
        controller = LoopController(config=cfg, run_id="test-run")

        # 第一轮: should_continue=True
        assert controller.should_continue() is True

        # 第一轮: tests fail
        decision_1 = controller.record_iteration({
            "apply_patch": {"status": "completed", "output": "patch v1"},
            "run_tests": {"status": "failed", "output": "3 tests failed"},
        })
        assert decision_1 == "continue"
        assert controller.state.current_iteration == 1

        # 第二轮: should_continue=True
        assert controller.should_continue() is True

        # 第二轮: tests pass → converged
        decision_2 = controller.record_iteration({
            "apply_patch": {"status": "completed", "output": "patch v2"},
            "run_tests": {"status": "passed", "output": "all tests passed"},
        })
        assert decision_2 == "converged"
        assert controller.state.status == "converged"
        assert controller.state.current_iteration == 2

        # 第三轮: should_continue=False (已收敛)
        assert controller.should_continue() is False


class TestLoopControllerMaxIterations:
    """测试最大轮次超限"""

    def test_stops_at_max_iterations(self):
        cfg = LoopConfigIR(
            enabled=True,
            max_iterations=2,
            completion_check_step="run_tests",
            completion_status="passed",
        )
        controller = LoopController(config=cfg, run_id="test-run")

        # 第一轮失败
        assert controller.should_continue() is True
        decision_1 = controller.record_iteration({
            "run_tests": {"status": "failed", "output": "fail"},
        })
        assert decision_1 == "continue"

        # 第二轮还是失败 → max exceeded
        assert controller.should_continue() is True
        decision_2 = controller.record_iteration({
            "run_tests": {"status": "failed", "output": "still fail"},
        })
        assert decision_2 == "stop_max"
        assert controller.state.status == "max_exceeded"

        # 不再继续
        assert controller.should_continue() is False

    def test_max_iterations_check_in_should_continue(self):
        """当 should_continue 检测到超限时也停止"""
        cfg = LoopConfigIR(enabled=True, max_iterations=1)
        controller = LoopController(config=cfg, run_id="test-run")

        assert controller.should_continue() is True
        controller.record_iteration({"step": {"status": "failed"}})
        # current_iteration=1, max=1 → should_continue returns False
        assert controller.should_continue() is False


class TestLoopControllerSameOutput:
    """测试重复输出检测"""

    def test_stops_on_same_output(self):
        cfg = LoopConfigIR(
            enabled=True,
            max_iterations=5,
            stop_on_same_output=True,
        )
        controller = LoopController(config=cfg, run_id="test-run")

        # 第一轮
        same_result = {
            "apply_patch": {"status": "completed", "output": "same patch"},
            "run_tests": {"status": "failed", "output": "same error"},
        }
        assert controller.should_continue() is True
        decision_1 = controller.record_iteration(same_result)
        assert decision_1 == "continue"

        # 第二轮: 相同输出 → stop
        assert controller.should_continue() is True
        decision_2 = controller.record_iteration(same_result)
        assert decision_2 == "stop_same_output"
        assert controller.state.status == "same_output_stop"

    def test_does_not_stop_when_disabled(self):
        cfg = LoopConfigIR(
            enabled=True,
            max_iterations=5,
            stop_on_same_output=False,
        )
        controller = LoopController(config=cfg, run_id="test-run")

        same_result = {
            "step": {"status": "failed", "output": "same"},
        }
        controller.record_iteration(same_result)
        decision = controller.record_iteration(same_result)
        # stop_on_same_output=False → 不会因为相同输出停止
        assert decision == "continue"


class TestLoopControllerContext:
    """测试 loop context 注入"""

    def test_initial_context(self):
        cfg = LoopConfigIR(enabled=True, max_iterations=3)
        controller = LoopController(config=cfg, run_id="test-run")

        ctx = controller.get_loop_context()
        assert ctx["iteration"] == 0
        assert ctx["max_iterations"] == 3
        assert ctx["loop_status"] == "running"
        assert "previous_result" not in ctx

    def test_context_after_first_iteration(self):
        cfg = LoopConfigIR(enabled=True, max_iterations=3)
        controller = LoopController(config=cfg, run_id="test-run")

        controller.record_iteration({
            "run_tests": {"status": "failed", "message": "2 tests failed", "output": "error log"},
        })

        ctx = controller.get_loop_context()
        assert ctx["iteration"] == 1
        assert "previous_result" in ctx
        assert "run_tests" in ctx["previous_result"]
        assert "previous_results_full" in ctx


class TestLoopControllerDisabled:
    """测试 loop disabled 场景"""

    def test_disabled_runs_once(self):
        cfg = LoopConfigIR(enabled=False, max_iterations=5)
        controller = LoopController(config=cfg, run_id="test-run")

        # 第一次 should_continue → True（执行一轮）
        assert controller.should_continue() is True
        controller.state.current_iteration = 1  # 模拟执行了一轮

        # 第二次 should_continue → False（不循环）
        assert controller.should_continue() is False


class TestLoopControllerEvidence:
    """测试 evidence 记录"""

    def test_write_evidence_without_collector(self):
        cfg = LoopConfigIR(enabled=True, max_iterations=3)
        controller = LoopController(config=cfg, run_id="test-run")

        # 没有 evidence_collector 时不报错
        result = controller.write_iteration_evidence(1, {"step": {"status": "ok"}})
        assert result is None

    def test_write_evidence_with_collector(self):
        cfg = LoopConfigIR(enabled=True, max_iterations=3)
        mock_collector = MagicMock()
        mock_collector.write_artifact.return_value = "/tmp/evidence/loop_iteration_001.json"
        controller = LoopController(
            config=cfg,
            evidence_collector=mock_collector,
            run_id="test-run",
        )

        result = controller.write_iteration_evidence(1, {"step": {"status": "ok"}})
        assert result == "/tmp/evidence/loop_iteration_001.json"
        mock_collector.write_artifact.assert_called_once()

        # 验证调用参数
        call_args = mock_collector.write_artifact.call_args
        assert call_args.kwargs["run_id"] == "test-run"
        assert call_args.kwargs["name"] == "loop_iteration_001.json"


class TestLoopControllerSummary:
    """测试循环摘要"""

    def test_summary_after_convergence(self):
        cfg = LoopConfigIR(
            enabled=True,
            max_iterations=5,
            completion_check_step="test",
            completion_status="passed",
        )
        controller = LoopController(config=cfg, run_id="test-run")

        controller.record_iteration({"test": {"status": "failed"}})
        controller.record_iteration({"test": {"status": "passed"}})

        summary = controller.get_summary()
        assert summary["total_iterations"] == 2
        assert summary["max_iterations"] == 5
        assert summary["final_status"] == "converged"
        assert summary["started_at"] is not None
        assert summary["completed_at"] is not None
