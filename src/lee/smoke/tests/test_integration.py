"""
Smoke Gate Integration Tests
============================
"""

import pytest
from datetime import datetime
import tempfile
import os

from src.lee.smoke.models import (
    SmokeGateStatus,
    GateResult,
    FailureSeverity,
    TestExecutionRecord,
    SmokeGateReport,
)
from src.lee.smoke.integration.merge_gate import MergeGateIntegrator
from src.lee.smoke.storage.store import SmokeStore


@pytest.fixture
def temp_db():
    """创建临时数据库用于测试。"""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    if os.path.exists(path):
        try:
            os.remove(path)
        except (PermissionError, OSError):
            pass  # 忽略清理错误


@pytest.fixture
def integrator(temp_db):
    """创建集成器实例。"""
    store = SmokeStore(db_path=temp_db)
    return MergeGateIntegrator(store=store)


@pytest.mark.asyncio
class TestMergeGateIntegrator:
    """测试 MergeGateIntegrator 类。"""

    async def test_check_merge_eligibility_no_state(self, integrator):
        """测试检查 merge 资格 - 无状态记录。"""
        state = await integrator.check_merge_eligibility("MR-123")

        assert state.is_mergeable == False
        assert state.gate_status == SmokeGateStatus.NOT_STARTED
        assert len(state.blocker_issues) > 0

    async def test_block_merge(self, integrator):
        """测试阻塞 merge。"""
        await integrator.block_merge("MR-123", "Test failed")

        state = await integrator.check_merge_eligibility("MR-123")

        assert state.is_mergeable == False
        assert "Test failed" in state.blocker_issues

    async def test_block_merge_empty_reason_raises_error(self, integrator):
        """测试阻塞 merge 时空原因抛出异常。"""
        with pytest.raises(ValueError, match="reason cannot be empty"):
            await integrator.block_merge("MR-123", "")

    async def test_allow_merge(self, integrator):
        """测试允许 merge。"""
        # 先阻塞
        await integrator.block_merge("MR-123", "Test failed")

        # 然后允许
        await integrator.allow_merge("MR-123")

        state = await integrator.check_merge_eligibility("MR-123")

        assert state.is_mergeable == True
        assert state.blocker_issues == []

    async def test_is_mergeable(self, integrator):
        """测试 is_mergeable 方法。"""
        from src.lee.smoke.models import MergeGateState

        # 可合并状态
        mergeable_state = MergeGateState(
            merge_request_id="MR-123",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.PASSED,
            gate_result=GateResult.ALLOW_MERGE,
            is_mergeable=True,
            blocker_issues=[]
        )

        # 不可合并状态
        not_mergeable_state = MergeGateState(
            merge_request_id="MR-456",
            branch_name="feature/test",
            target_branch="main",
            current_commit_sha="abc123",
            gate_status=SmokeGateStatus.FAILED,
            gate_result=GateResult.BLOCK_MERGE,
            is_mergeable=False,
            blocker_issues=["Test failed"]
        )

        assert integrator.is_mergeable(mergeable_state) == True
        assert integrator.is_mergeable(not_mergeable_state) == False
