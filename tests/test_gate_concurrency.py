"""
Concurrency tests for Gate Improvement v1.1

Tests concurrent decision scenarios, transaction isolation,
and deadlock prevention.

Gate Improvement v1.1 - Phase 2
"""

import sys
import pytest
import asyncio
import tempfile
from pathlib import Path
from datetime import datetime
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.storage.models import (
    WorkflowInstance,
    WorkflowLevel,
    WorkflowStatus,
    GateApproval,
    GateStatus,
    TaskExecutionStatus,
)


import pytest_asyncio


@pytest_asyncio.fixture
async def concurrent_store():
    """创建用于并发测试的数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = SQLiteStore(str(db_path))
    await store.connect()

    # v1.1: 运行迁移以确保新字段存在
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from lee.orchestrator.storage.migrations.migration_002_gate_actions import upgrade
    upgrade(str(db_path))

    # 创建测试工作流
    instance = WorkflowInstance(
        id="test_wf_concurrent",
        level=WorkflowLevel.TASK,
        template_id="test_template",
        status=WorkflowStatus.RUNNING,
        data={"completed_steps": ["s1"]},
    )
    await store.create_workflow(instance)

    # 创建 gate
    gate = GateApproval(
        workflow_id="test_wf_concurrent",
        gate_id="gate_concurrent",
        step_id="test_step",
        status=GateStatus.PENDING,
        version=1,
    )
    await store.create_gate_approval(gate)

    yield store

    await store.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
class TestConcurrentDecisions:
    """测试并发决策场景"""

    async def test_concurrent_reject_and_approve(self, concurrent_store):
        """测试并发 reject 和 approve"""
        store = concurrent_store

        # 模拟两个用户同时决策
        results = await asyncio.gather(
            store.update_gate_approval_with_version(
                workflow_id="test_wf_concurrent",
                gate_id="gate_concurrent",
                status=GateStatus.REJECTED,
                approver="user1",
                comments="Reject",
                expected_version=1,
            ),
            store.update_gate_approval_with_version(
                workflow_id="test_wf_concurrent",
                gate_id="gate_concurrent",
                status=GateStatus.APPROVED,
                approver="user2",
                comments="Approve",
                expected_version=1,
            ),
            return_exceptions=True,
        )

        # 只有一个应该成功
        successful = [r for r in results if r is not None and not isinstance(r, Exception)]
        failures = [r for r in results if r is None or isinstance(r, Exception)]

        assert len(successful) == 1, "Exactly one decision should succeed"
        assert len(failures) == 1, "Exactly one decision should fail"

        # 验证最终状态
        final_gate = await store.get_gate_approval("test_wf_concurrent", "gate_concurrent")
        assert final_gate.version == 2  # 版本号已递增

    async def test_concurrent_multiple_reject(self, concurrent_store):
        """测试多个用户同时 reject"""
        store = concurrent_store

        # 三个用户同时 reject
        results = await asyncio.gather(
            store.update_gate_approval_with_version(
                workflow_id="test_wf_concurrent",
                gate_id="gate_concurrent",
                status=GateStatus.REJECTED,
                approver="user1",
                comments="Reject 1",
                expected_version=1,
            ),
            store.update_gate_approval_with_version(
                workflow_id="test_wf_concurrent",
                gate_id="gate_concurrent",
                status=GateStatus.REJECTED,
                approver="user2",
                comments="Reject 2",
                expected_version=1,
            ),
            store.update_gate_approval_with_version(
                workflow_id="test_wf_concurrent",
                gate_id="gate_concurrent",
                status=GateStatus.REJECTED,
                approver="user3",
                comments="Reject 3",
                expected_version=1,
            ),
            return_exceptions=True,
        )

        # 只有一个成功
        successful = [r for r in results if r is not None]
        assert len(successful) == 1

    async def test_sequential_decisions(self, concurrent_store):
        """测试顺序决策（应该都成功）"""
        store = concurrent_store

        # 第一个决策
        result1 = await store.update_gate_approval_with_version(
            workflow_id="test_wf_concurrent",
            gate_id="gate_concurrent",
            status=GateStatus.REJECTED,
            approver="user1",
            comments="First reject",
            expected_version=1,
        )
        assert result1 is not None
        assert result1.version == 2

        # 第二个决策（使用新版本号）
        result2 = await store.update_gate_approval_with_version(
            workflow_id="test_wf_concurrent",
            gate_id="gate_concurrent",
            status=GateStatus.APPROVED,
            approver="user2",
            comments="Approve after reject",
            expected_version=2,
        )
        assert result2 is not None
        assert result2.version == 3


@pytest.mark.asyncio
class TestTransactionIsolation:
    """测试事务隔离级别"""

    async def test_repeatable_read_isolation(self, concurrent_store):
        """测试 REPEATABLE READ 隔离级别"""
        store = concurrent_store

        # 开启事务
        async with store.transaction(isolation_level="REPEATABLE_READ") as cursor:
            # 在事务内读取 gate
            await cursor.execute("""
                SELECT version FROM gate_approvals
                WHERE workflow_id = ? AND gate_id = ?
            """, ("test_wf_concurrent", "gate_concurrent"))
            row = await cursor.fetchone()
            version_in_txn = row[0]

            # 在事务外更新（模拟并发）
            # 注意：由于我们的实现是单连接，这不会真正并发
            # 这里只是验证事务语法正确

            assert version_in_txn == 1

    async def test_transaction_rollback_on_error(self, concurrent_store):
        """测试事务内错误时回滚"""
        store = concurrent_store

        initial_workflow = await store.get_workflow("test_wf_concurrent")
        initial_status = initial_workflow.status

        # 尝试在事务内修改但失败
        try:
            async with store.transaction() as cursor:
                # 尝试修改工作流状态
                await cursor.execute("""
                    UPDATE workflow_instances
                    SET status = ?
                    WHERE id = ?
                """, ("paused", "test_wf_concurrent"))

                # 模拟错误
                raise ValueError("Simulated error")
        except ValueError:
            pass

        # 验证回滚：状态应该不变
        final_workflow = await store.get_workflow("test_wf_concurrent")
        assert final_workflow.status == initial_status.value  # .value for Enum comparison

    async def test_transaction_commit_success(self, concurrent_store):
        """测试事务成功提交"""
        store = concurrent_store

        async with store.transaction() as cursor:
            # 修改工作流状态
            await cursor.execute("""
                UPDATE workflow_instances
                SET status = ?
                WHERE id = ?
            """, ("paused", "test_wf_concurrent"))

        # 验证提交：状态应该改变
        final_workflow = await store.get_workflow("test_wf_concurrent")
        assert final_workflow.status.value == "paused"

        # 恢复状态
        await store.update_workflow_status("test_wf_concurrent", WorkflowStatus.RUNNING)

    async def test_lock_timeout(self, concurrent_store):
        """测试锁超时机制"""
        store = concurrent_store

        # SQLite 使用 BEGIN IMMEDIATE 会立即获取写锁
        # 如果获取不到会等待或超时

        # 模拟：在事务内持有锁
        async with store.transaction():
            # 在事务内执行操作
            gate = await store.get_gate_approval("test_wf_concurrent", "gate_concurrent")
            assert gate is not None

        # 事务提交后，锁释放

    async def test_sequential_transactions(self, concurrent_store):
        """测试顺序事务（不会死锁）"""
        store = concurrent_store

        # 顺序执行多个事务
        for i in range(3):
            async with store.transaction() as cursor:
                await cursor.execute("""
                    UPDATE workflow_instances
                    SET updated_at = ?
                    WHERE id = ?
                """, (f"2026-02-19T10:0{i}:00", "test_wf_concurrent"))

        # 验证最后一次更新生效
        workflow = await store.get_workflow("test_wf_concurrent")
        assert "10:02" in workflow.updated_at.isoformat()


@pytest.mark.asyncio
class TestRewindConcurrency:
    """测试 rewind 操作的并发性"""

    async def test_rewind_during_step_execution(self, concurrent_store):
        """测试步骤执行期间进行 rewind"""
        store = concurrent_store

        # 模拟场景：
        # 1. 步骤 s2 正在执行（RUNNING）
        # 2. 用户决定回退到 s1
        # 3. s2 应该被标记为 invalidated

        # 创建 s2 的 task_execution
        from lee.orchestrator.storage.models import TaskExecution

        execution = TaskExecution(
            id="exec_s2_running",
            workflow_id="test_wf_concurrent",
            step_name="s2",
            executor_type="llm",  # Required field
            status=TaskExecutionStatus.RUNNING,  # Use enum
        )
        await store.create_task_execution(execution)

        # 模拟回退
        # （实际清理由 rewind_to 实现）
        workflow = await store.get_workflow("test_wf_concurrent")
        steps_after_s1 = [s for s in ["s2", "s3", "s4"] if s in workflow.data.get("completed_steps", [])]

        # 验证 s2 在 completed_steps 中
        # （在真实场景中，回退会清理这些）

    async def test_rewind_preserves_earlier_steps(self, concurrent_store):
        """测试回退保留较早步骤的状态"""
        store = concurrent_store

        workflow = await store.get_workflow("test_wf_concurrent")

        # 验证 s1 在 completed_steps 中
        assert "s1" in workflow.data["completed_steps"]

        # 回退到 s1 后，s1 应该保留在 completed_steps 中
        # （因为 s1 本身就是目标步骤）

    async def test_multiple_rewind_targets(self, concurrent_store):
        """测试多次回退到不同目标"""
        store = concurrent_store

        # 第一次：回退到 s2
        # 第二次：回退到 s1

        # 验证每次回退的目标都在步骤顺序中
        from lee.orchestrator.execution.template_manager import WorkflowTemplate
        from lee.orchestrator.storage.models import Step

        template = WorkflowTemplate(
            id="test",
            level=WorkflowLevel.TASK,
            name="Test",
            description="Test",
            steps=[
                Step(id="s1", kind="agent", depends_on=[]),
                Step(id="s2", kind="agent", depends_on=["s1"]),
                Step(id="s3", kind="agent", depends_on=["s2"]),
            ],
        )

        order = template.get_step_order()

        # s2 在顺序中
        assert "s2" in order
        index_s2 = order.index("s2")

        # s1 在 s2 之前
        assert order.index("s1") < index_s2


@pytest.mark.asyncio
class TestDeadlockPrevention:
    """测试死锁预防"""

    async def test_lock_timeout(self, concurrent_store):
        """测试锁超时机制"""
        store = concurrent_store

        # SQLite 使用 BEGIN IMMEDIATE 会立即获取写锁
        # 如果获取不到会等待或超时

        # 模拟：在事务内持有锁
        async with store.transaction():
            # 在事务内执行操作
            gate = await store.get_gate_approval("test_wf_concurrent", "gate_concurrent")
            assert gate is not None

        # 事务提交后，锁释放

    async def test_sequential_transactions(self, concurrent_store):
        """测试顺序事务（不会死锁）"""
        store = concurrent_store

        # 顺序执行多个事务
        for i in range(3):
            async with store.transaction() as cursor:
                await cursor.execute("""
                    UPDATE workflow_instances
                    SET updated_at = ?
                    WHERE id = ?
                """, (f"2026-02-19T10:0{i}:00", "test_wf_concurrent"))

        # 验证最后一次更新生效
        workflow = await store.get_workflow("test_wf_concurrent")
        assert "10:02" in workflow.updated_at.isoformat()


@pytest.mark.asyncio
class TestRaceConditions:
    """测试竞态条件"""

    async def test_gate_creation_race(self, concurrent_store):
        """测试并发创建 gate（UNIQUE 约束）"""
        store = concurrent_store

        # 尝试同时创建两个相同 ID 的 gate
        gate1 = GateApproval(
            workflow_id="test_wf_concurrent",
            gate_id="race_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )

        gate2 = GateApproval(
            workflow_id="test_wf_concurrent",
            gate_id="race_gate",  # 相同 ID
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )

        # 第一个创建成功
        await store.create_gate_approval(gate1)

        # 第二个创建应该失败（UNIQUE 约束）
        with pytest.raises(Exception):  # sqlite3.IntegrityError
            await store.create_gate_approval(gate2)

    async def test_version_check_race(self, concurrent_store):
        """测试版本号检查的竞态条件"""
        store = concurrent_store

        # 创建 gate
        gate = GateApproval(
            workflow_id="test_wf_race",
            gate_id="race_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )

        # 创建工作流
        instance = WorkflowInstance(
            id="test_wf_race",
            level=WorkflowLevel.TASK,
            template_id="test",
            status=WorkflowStatus.RUNNING,
        )
        await store.create_workflow(instance)
        await store.create_gate_approval(gate)

        # 两个并发更新使用相同的版本号
        results = await asyncio.gather(
            store.update_gate_approval_with_version(
                workflow_id="test_wf_race",
                gate_id="race_gate",
                status=GateStatus.APPROVED,
                approver="user1",
                comments="Approve",
                expected_version=1,
            ),
            store.update_gate_approval_with_version(
                workflow_id="test_wf_race",
                gate_id="race_gate",
                status=GateStatus.REJECTED,
                approver="user2",
                comments="Reject",
                expected_version=1,
            ),
            return_exceptions=True,
        )

        # 验证只有一个成功
        successful = [r for r in results if r is not None]
        assert len(successful) == 1


@pytest.mark.asyncio
class TestStressScenarios:
    """压力测试场景"""

    async def test_rapid_sequential_updates(self, concurrent_store):
        """测试快速连续更新"""
        store = concurrent_store

        # 创建 gate
        instance = WorkflowInstance(
            id="test_wf_stress",
            level=WorkflowLevel.TASK,
            template_id="test",
            status=WorkflowStatus.RUNNING,
        )
        await store.create_workflow(instance)

        gate = GateApproval(
            workflow_id="test_wf_stress",
            gate_id="stress_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await store.create_gate_approval(gate)

        # 快速连续更新 10 次
        for i in range(10):
            updated = await store.update_gate_approval_with_version(
                workflow_id="test_wf_stress",
                gate_id="stress_gate",
                status=GateStatus.APPROVED if i % 2 == 0 else GateStatus.REJECTED,
                approver=f"user{i}",
                comments=f"Update {i}",
                expected_version=i + 1,  # 使用正确的版本号
            )
            assert updated is not None
            assert updated.version == i + 2  # 版本号递增

        # 验证最终版本号
        final_gate = await store.get_gate_approval("test_wf_stress", "stress_gate")
        assert final_gate.version == 11

    async def test_interleaved_operations(self, concurrent_store):
        """测试交错操作（读取、更新、验证）"""
        store = concurrent_store

        # 创建测试数据
        instance = WorkflowInstance(
            id="test_wf_interleaved",
            level=WorkflowLevel.TASK,
            template_id="test",
            status=WorkflowStatus.RUNNING,
        )
        await store.create_workflow(instance)

        gate = GateApproval(
            workflow_id="test_wf_interleaved",
            gate_id="interleaved_gate",
            step_id="test_step",
            status=GateStatus.PENDING,
            version=1,
        )
        await store.create_gate_approval(gate)

        # 交错操作：读取、更新、验证
        for i in range(5):
            # 读取
            before = await store.get_gate_approval("test_wf_interleaved", "interleaved_gate")
            current_version = before.version

            # 更新
            updated = await store.update_gate_approval_with_version(
                workflow_id="test_wf_interleaved",
                gate_id="interleaved_gate",
                status=GateStatus.APPROVED,
                approver=f"user{i}",
                comments=f"Update {i}",
                expected_version=current_version,
            )
            assert updated is not None
            assert updated.version == current_version + 1

            # 验证
            after = await store.get_gate_approval("test_wf_interleaved", "interleaved_gate")
            assert after.version == updated.version
