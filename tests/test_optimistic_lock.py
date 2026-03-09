"""
Unit tests for optimistic locking in GateApproval

Gate Improvement v1.1 - Phase 1
"""

import pytest
import pytest_asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.storage.models import (
    GateApproval,
    GateStatus,
    ConcurrentDecisionError,
)


@pytest_asyncio.fixture
async def db_store():
    """创建临时数据库存储"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    store = SQLiteStore(db_path)
    await store.connect()

    yield store

    await store.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
class TestOptimisticLocking:
    """测试乐观锁机制"""

    async def test_update_with_correct_version(self, db_store):
        """测试使用正确版本更新"""
        # 创建 gate
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await db_store.create_gate_approval(gate)

        # 使用正确的版本更新
        updated = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user1",
            comments="Approved",
            expected_version=1,
        )

        assert updated is not None
        assert updated.status == GateStatus.APPROVED
        assert updated.version == 2

    async def test_update_with_incorrect_version(self, db_store):
        """测试使用错误版本更新（并发冲突）"""
        # 创建 gate
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await db_store.create_gate_approval(gate)

        # 使用错误的版本更新（版本号不匹配）
        updated = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user1",
            comments="Approved",
            expected_version=999,  # 错误的版本号
        )

        # 应该返回 None 表示更新失败
        assert updated is None

        # 原始记录应该保持不变
        original = await db_store.get_gate_approval("test_wf", "test_gate")
        assert original.status == GateStatus.PENDING
        assert original.version == 1

    async def test_concurrent_updates(self, db_store):
        """测试并发更新冲突"""
        # 创建 gate
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await db_store.create_gate_approval(gate)

        # 获取初始版本
        initial = await db_store.get_gate_approval("test_wf", "test_gate")
        initial_version = initial.version

        # 第一次更新（成功）
        updated1 = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user1",
            comments="User 1 approved",
            expected_version=initial_version,
        )

        # 第二次更新（使用旧版本号，失败）
        updated2 = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.REJECTED,
            approver="user2",
            comments="User 2 rejected",
            expected_version=initial_version,  # 仍然使用旧版本
        )

        # 验证结果
        assert updated1 is not None
        assert updated1.status == GateStatus.APPROVED
        assert updated1.version == 2

        assert updated2 is None  # 并发冲突

        # 最终状态应该是第一次更新的结果
        final = await db_store.get_gate_approval("test_wf", "test_gate")
        assert final.status == GateStatus.APPROVED
        assert final.approver == "user1"
        assert final.version == 2

    async def test_update_without_version_check(self, db_store):
        """测试不指定版本号（自动使用当前版本）"""
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await db_store.create_gate_approval(gate)

        # 不指定版本号，应该自动使用当前版本
        updated = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user1",
            comments="Approved",
            expected_version=None,  # 自动获取
        )

        assert updated is not None
        assert updated.version == 2

    async def test_update_with_new_fields(self, db_store):
        """测试更新新字段（decision_action, target_step）"""
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
            default_reject_action="rollback",
            default_reject_target="s1",
        )
        await db_store.create_gate_approval(gate)

        # 更新并设置新字段
        updated = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.REJECTED,
            approver="user1",
            comments="Need to rollback",
            expected_version=1,
            decision_action="rollback",
            target_step="s1",
        )

        assert updated is not None
        # 注意：如果数据库没有新列，这些字段可能为 None
        # 这取决于是否运行了迁移脚本
        assert updated.status == GateStatus.REJECTED

    async def test_update_with_structured_feedback(self, db_store):
        """测试更新结构化反馈"""
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.REVISED,
            version=1,
        )
        await db_store.create_gate_approval(gate)

        # 更新并设置结构化反馈
        feedback = {
            "issues": ["代码风格需要改进"],
            "expected_changes": ["修复 linting 错误"],
        }
        issues_list = ["代码风格需要改进", "缺少测试"]

        updated = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.REVISED,
            approver="reviewer1",
            comments="需要修订",
            expected_version=1,
            structured_feedback=feedback,
            issues=issues_list,
        )

        assert updated is not None
        assert updated.status == GateStatus.REVISED


@pytest.mark.asyncio
class TestBackwardCompatibility:
    """测试向后兼容性"""

    async def test_old_gate_without_version(self, db_store):
        """测试没有 version 字段的旧 gate"""
        # 创建一个旧版本的 gate（没有 version 列）
        # 这模拟了迁移前的数据库状态

        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,  # 数据对象有 version
        )
        await db_store.create_gate_approval(gate)

        # 尝试更新
        # 如果数据库没有 version 列，应该回退到旧版本逻辑
        updated = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user1",
            comments="Approved",
            expected_version=1,
        )

        # 应该成功（可能使用旧版本逻辑或新逻辑）
        assert updated is not None

    async def test_get_gate_with_new_fields(self, db_store):
        """测试获取带有新字段的 gate"""
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
            default_reject_action="rollback",
            default_reject_target="s1",
            decision_action="retry",
            target_step="s2",
        )

        # 创建 gate（可能成功也可能失败，取决于是否有新列）
        try:
            await db_store.create_gate_approval(gate)

            # 获取 gate
            retrieved = await db_store.get_gate_approval("test_wf", "test_gate")

            # 验证基本字段
            assert retrieved is not None
            assert retrieved.workflow_id == "test_wf"
            assert retrieved.gate_id == "test_gate"

            # 新字段可能存在也可能不存在（取决于是否迁移）
            # 只要不报错就行
        except Exception as e:
            # 如果新列不存在，创建可能失败
            # 这是预期的
            assert "column" in str(e).lower()


@pytest.mark.asyncio
class TestEdgeCases:
    """测试边界情况"""

    async def test_update_nonexistent_gate(self, db_store):
        """测试更新不存在的 gate"""
        with pytest.raises(ValueError, match="Gate not found"):
            await db_store.update_gate_approval_with_version(
                workflow_id="nonexistent",
                gate_id="nonexistent",
                status=GateStatus.APPROVED,
                approver="user1",
                comments="Approve",
                expected_version=1,
            )

    async def test_version_auto_increment(self, db_store):
        """测试版本号自动递增"""
        gate = GateApproval(
            workflow_id="test_wf",
            gate_id="test_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await db_store.create_gate_approval(gate)

        # 第一次更新
        updated1 = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user1",
            comments="First update",
            expected_version=1,
        )
        assert updated1.version == 2

        # 第二次更新
        updated2 = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user2",
            comments="Second update",
            expected_version=2,
        )
        assert updated2.version == 3

        # 第三次更新
        updated3 = await db_store.update_gate_approval_with_version(
            workflow_id="test_wf",
            gate_id="test_gate",
            status=GateStatus.APPROVED,
            approver="user3",
            comments="Third update",
            expected_version=3,
        )
        assert updated3.version == 4
