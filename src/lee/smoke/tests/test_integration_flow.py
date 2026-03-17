"""
Smoke Gate Integration Tests
============================
测试 Smoke Gate 模块与现有系统的集成
"""

import pytest
from datetime import datetime
import tempfile
import os

from src.lee.smoke.models import (
    SmokeGateStatus,
    GateResult,
    FailureSeverity,
    SmokeGateContext,
    TestExecutionRecord,
    SmokeGateReport,
    MergeGateState,
    SmokeGateConfig,
)
from src.lee.smoke.gate.manager import SmokeGateManager
from src.lee.smoke.integration.merge_gate import MergeGateIntegrator
from src.lee.smoke.hooks.pre_merge import PreMergeHook
from src.lee.smoke.storage.store import SmokeStore


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    # 延迟清理，忽略错误
    yield path
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception:
        pass  # 忽略清理错误


@pytest.fixture
def components(temp_db):
    """创建所有组件实例。"""
    store = SmokeStore(db_path=temp_db)
    manager = SmokeGateManager(store=store)
    integrator = MergeGateIntegrator(store=store)
    hook = PreMergeHook(store=store)
    return {
        "store": store,
        "manager": manager,
        "integrator": integrator,
        "hook": hook
    }


@pytest.mark.asyncio
class TestSmokeGateIntegration:
    """Smoke Gate 集成测试。"""

    async def test_full_smoke_flow(self, components):
        """测试完整的 Smoke Gate 流程。"""
        manager = components["manager"]
        integrator = components["integrator"]
        hook = components["hook"]

        # 1. 创建 Gate
        config = SmokeGateConfig(test_set_ref="test-set-v1")
        context = await manager.create_gate("MR-123", config)
        assert context.status == SmokeGateStatus.NOT_STARTED

        # 2. 检查 merge 资格（应该不可合并）
        state = await integrator.check_merge_eligibility("MR-123")
        assert state.is_mergeable is False

        # 3. 检查 hook（应该阻塞）
        assert hook.execute("MR-123") is False

        # 4. 模拟测试执行并创建报告
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

        # 5. 保存报告并更新 context 状态
        components["store"].create_gate_report(report)

        # 启动执行 (NOT_STARTED -> RUNNING)
        context.start_execution()
        components["store"].update_gate_context(context)

        # 完成执行 (RUNNING -> PASSED)
        context.complete_execution(GateResult.ALLOW_MERGE)
        components["store"].update_gate_context(context)

        # 6. 更新 Merge Gate 状态
        await integrator.update_from_report("MR-123", report)

        # 7. 检查 merge 资格（应该可合并）
        state = await integrator.check_merge_eligibility("MR-123")
        assert state.is_mergeable == True
        assert state.gate_status == SmokeGateStatus.PASSED

        # 8. 检查 hook（应该允许）
        assert hook.execute("MR-123") == True

    async def test_smoke_fail_blocks_merge(self, components):
        """测试 Smoke 失败阻塞 merge。"""
        manager = components["manager"]
        integrator = components["integrator"]
        hook = components["hook"]
        store = components["store"]

        # 1. 创建 Gate
        config = SmokeGateConfig(test_set_ref="test-set-v1")
        context = await manager.create_gate("MR-456", config)

        # 2. 模拟测试失败
        executions = [
            TestExecutionRecord(
                test_id="test_001",
                test_name="test_login",
                priority="P0",
                status="fail",
                severity=FailureSeverity.BLOCKER,
                duration_ms=1500,
                error_message="Assertion failed"
            )
        ]

        report = SmokeGateReport.create_from_executions(
            smoke_run_id="run-002",
            merge_request_id="MR-456",
            commit_sha="def456",
            test_set_ref="test-set-v1",
            executions=executions,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            log_path="/logs/smoke.log",
            evidence_dir="/evidence"
        )

        # 3. 保存报告并更新状态
        store.create_gate_report(report)
        await integrator.update_from_report("MR-456", report)

        # 更新 context 状态为 FAILED
        context.status = SmokeGateStatus.FAILED
        context.result = GateResult.BLOCK_MERGE
        store.update_gate_context(context)

        # 4. 检查 merge 资格（应该不可合并）
        state = await integrator.check_merge_eligibility("MR-456")
        assert state.is_mergeable == False
        assert state.gate_status == SmokeGateStatus.FAILED
        assert len(state.blocker_issues) > 0

        # 5. 检查 hook（应该阻塞）
        assert hook.execute("MR-456") == False

        # 6. 获取阻塞消息
        msg = hook.get_block_message("MR-456")
        assert "blocker" in msg.lower() or "failed" in msg.lower()

    async def test_flaky_test_does_not_block_merge(self, components):
        """测试 Flaky Test 不阻塞 merge。"""
        integrator = components["integrator"]
        store = components["store"]

        # 1. 模拟只有 Flaky 测试失败
        executions = [
            TestExecutionRecord(
                test_id="test_001",
                test_name="test_flaky",
                priority="P2",
                status="fail",
                severity=FailureSeverity.FLAKY,
                duration_ms=1500,
                error_message="Flaky test",
                is_flaky=True
            ),
            TestExecutionRecord(
                test_id="test_002",
                test_name="test_stable",
                priority="P0",
                status="pass",
                duration_ms=1000
            )
        ]

        report = SmokeGateReport.create_from_executions(
            smoke_run_id="run-003",
            merge_request_id="MR-789",
            commit_sha="ghi789",
            test_set_ref="test-set-v1",
            executions=executions,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            log_path="/logs/smoke.log",
            evidence_dir="/evidence"
        )

        # 2. 保存报告
        store.create_gate_report(report)

        # 3. P2 flaky 不阻塞 merge
        assert report.result == GateResult.ALLOW_MERGE
        assert report.blocker_count == 0
