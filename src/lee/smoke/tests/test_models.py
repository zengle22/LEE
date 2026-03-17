"""
Smoke Gate Models Tests
=======================
"""

import pytest
from datetime import datetime, timedelta

from src.lee.smoke.models import (
    SmokeGateStatus,
    GateResult,
    FailureSeverity,
    SmokeGateEvent,
    SmokeGateContext,
    TestExecutionRecord,
    SmokeGateReport,
    MergeGateState,
    SmokeGateConfig,
)


class TestSmokeGateStatus:
    """测试 SmokeGateStatus 枚举。"""

    def test_status_values(self):
        """测试状态枚举值。"""
        assert SmokeGateStatus.NOT_STARTED.value == "not_started"
        assert SmokeGateStatus.RUNNING.value == "running"
        assert SmokeGateStatus.PASSED.value == "passed"
        assert SmokeGateStatus.FAILED.value == "failed"
        assert SmokeGateStatus.INVALID.value == "invalid"


class TestGateResult:
    """测试 GateResult 枚举。"""

    def test_result_values(self):
        """测试结果枚举值。"""
        assert GateResult.ALLOW_MERGE.value == "allow_merge"
        assert GateResult.BLOCK_MERGE.value == "block_merge"
        assert GateResult.PENDING.value == "pending"
        assert GateResult.ERROR.value == "error"


class TestFailureSeverity:
    """测试 FailureSeverity 枚举。"""

    def test_severity_values(self):
        """测试严重程度枚举值。"""
        assert FailureSeverity.BLOCKER.value == "blocker"
        assert FailureSeverity.CRITICAL.value == "critical"
        assert FailureSeverity.FLAKY.value == "flaky"


class TestSmokeGateContext:
    """测试 SmokeGateContext 数据模型。"""

    def test_create_context(self):
        """测试创建上下文。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.NOT_STARTED
        )

        assert context.merge_request_id == "MR-123"
        assert context.status == SmokeGateStatus.NOT_STARTED
        assert context.result is None
        assert context.retry_count == 3
        assert context.timeout_minutes == 30

    def test_start_execution(self):
        """测试启动执行。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.NOT_STARTED
        )

        context.start_execution()

        assert context.status == SmokeGateStatus.RUNNING
        assert context.started_at is not None

    def test_start_execution_from_invalid_state(self):
        """测试从无效状态启动执行应抛出异常。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.PASSED
        )

        with pytest.raises(ValueError, match="Cannot start execution from status"):
            context.start_execution()

    def test_complete_execution_passed(self):
        """测试完成执行 - 通过。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.RUNNING
        )

        context.complete_execution(GateResult.ALLOW_MERGE)

        assert context.status == SmokeGateStatus.PASSED
        assert context.result == GateResult.ALLOW_MERGE
        assert context.completed_at is not None

    def test_complete_execution_failed(self):
        """测试完成执行 - 失败。"""
        context = SmokeGateContext(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            priority_filter=["P0", "P1"],
            status=SmokeGateStatus.RUNNING
        )

        context.complete_execution(GateResult.BLOCK_MERGE)

        assert context.status == SmokeGateStatus.FAILED
        assert context.result == GateResult.BLOCK_MERGE


class TestTestExecutionRecord:
    """测试 TestExecutionRecord 数据模型。"""

    def test_create_passing_record(self):
        """测试创建通过的测试记录。"""
        record = TestExecutionRecord(
            test_id="test_001",
            test_name="test_login",
            priority="P0",
            status="pass",
            duration_ms=1500
        )

        assert record.status == "pass"
        assert record.retry_attempts == 0
        assert record.is_flaky is False

    def test_create_failing_record(self):
        """测试创建失败的测试记录。"""
        record = TestExecutionRecord(
            test_id="test_002",
            test_name="test_checkout",
            priority="P1",
            status="fail",
            severity=FailureSeverity.BLOCKER,
            duration_ms=2000,
            error_message="Assertion failed",
            retry_attempts=3
        )

        assert record.status == "fail"
        assert record.severity == FailureSeverity.BLOCKER
        assert record.retry_attempts == 3


class TestSmokeGateReport:
    """测试 SmokeGateReport 数据模型。"""

    def test_create_from_executions_all_pass(self):
        """测试从执行记录创建报告 - 全部通过。"""
        executions = [
            TestExecutionRecord(
                test_id="test_001",
                test_name="test_login",
                priority="P0",
                status="pass",
                duration_ms=1500
            ),
            TestExecutionRecord(
                test_id="test_002",
                test_name="test_checkout",
                priority="P1",
                status="pass",
                duration_ms=2000
            )
        ]

        started_at = datetime.now()
        completed_at = datetime.now() + timedelta(seconds=10)

        report = SmokeGateReport.create_from_executions(
            smoke_run_id="run-001",
            merge_request_id="MR-123",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            executions=executions,
            started_at=started_at,
            completed_at=completed_at,
            log_path="/logs/smoke.log",
            evidence_dir="/evidence"
        )

        assert report.total_cases == 2
        assert report.passed == 2
        assert report.failed == 0
        assert report.pass_rate == 1.0
        assert report.result == GateResult.ALLOW_MERGE
        assert report.status == SmokeGateStatus.PASSED
        assert report.blocker_count == 0

    def test_create_from_executions_with_failures(self):
        """测试从执行记录创建报告 - 有失败。"""
        executions = [
            TestExecutionRecord(
                test_id="test_001",
                test_name="test_login",
                priority="P0",
                status="pass",
                duration_ms=1500
            ),
            TestExecutionRecord(
                test_id="test_002",
                test_name="test_checkout",
                priority="P1",
                status="fail",
                severity=FailureSeverity.BLOCKER,
                duration_ms=2000,
                error_message="Assertion failed"
            )
        ]

        started_at = datetime.now()
        completed_at = datetime.now() + timedelta(seconds=10)

        report = SmokeGateReport.create_from_executions(
            smoke_run_id="run-001",
            merge_request_id="MR-123",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            executions=executions,
            started_at=started_at,
            completed_at=completed_at,
            log_path="/logs/smoke.log",
            evidence_dir="/evidence"
        )

        assert report.total_cases == 2
        assert report.passed == 1
        assert report.failed == 1
        assert report.pass_rate == 0.5
        assert report.result == GateResult.BLOCK_MERGE
        assert report.status == SmokeGateStatus.FAILED
        assert report.blocker_count == 1


class TestMergeGateState:
    """测试 MergeGateState 数据模型。"""

    def test_create_state(self):
        """测试创建状态。"""
        state = MergeGateState(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.NOT_STARTED,
            is_mergeable=False,
            blocker_issues=["No smoke test executed"]
        )

        assert state.is_mergeable is False
        assert len(state.blocker_issues) == 1

    def test_update_from_report_passed(self):
        """测试从报告更新状态 - 通过。"""
        state = MergeGateState(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.NOT_STARTED,
            is_mergeable=False
        )

        # 创建模拟报告
        executions = [
            TestExecutionRecord(
                test_id="test_001",
                test_name="test_login",
                priority="P0",
                status="pass",
                duration_ms=1500
            )
        ]
        started_at = datetime.now()
        completed_at = datetime.now()

        report = SmokeGateReport.create_from_executions(
            smoke_run_id="run-001",
            merge_request_id="MR-123",
            commit_sha="abc123",
            test_set_ref="test-set-v1",
            executions=executions,
            started_at=started_at,
            completed_at=completed_at,
            log_path="/logs/smoke.log",
            evidence_dir="/evidence"
        )

        state.update_from_report(report)

        assert state.gate_status == SmokeGateStatus.PASSED
        assert state.gate_result == GateResult.ALLOW_MERGE
        assert state.is_mergeable is True
        assert len(state.blocker_issues) == 0

    def test_is_mergeable_with_blockers(self):
        """测试有 blocker 时不可合并。"""
        state = MergeGateState(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.FAILED,
            gate_result=GateResult.BLOCK_MERGE,
            is_mergeable=False,
            blocker_issues=["test_login failed", "test_checkout failed"]
        )

        assert state.is_mergeable is False
        assert len(state.blocker_issues) == 2


class TestSmokeGateConfig:
    """测试 SmokeGateConfig 数据模型。"""

    def test_default_config(self):
        """测试默认配置。"""
        config = SmokeGateConfig(test_set_ref="default")

        assert config.test_set_ref == "default"
        assert config.priority_filter == ["P0", "P1"]
        assert config.retry_count == 3
        assert config.timeout_minutes == 30
        assert config.parallel_workers == 4
        assert config.flaky_threshold == 0.8
        assert config.flaky_window == 5

    def test_custom_config(self):
        """测试自定义配置。"""
        config = SmokeGateConfig(
            test_set_ref="custom-set",
            priority_filter=["P0"],
            retry_count=5,
            timeout_minutes=60,
            parallel_workers=8
        )

        assert config.test_set_ref == "custom-set"
        assert config.priority_filter == ["P0"]
        assert config.retry_count == 5
        assert config.timeout_minutes == 60
        assert config.parallel_workers == 8
