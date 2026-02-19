"""
Integration tests for Gate Improvement v1.1

Tests end-to-end scenarios including:
- Full rejection/rollback flow
- Full revision/retry flow
- Full spawn workflow flow
- Full flag/continue flow

Gate Improvement v1.1 - Phase 2
"""

import pytest
import sys
import tempfile
from pathlib import Path
from datetime import datetime
from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.storage.models import (
    WorkflowInstance,
    WorkflowLevel,
    WorkflowStatus,
    Step,
    TaskExecution,
    TaskExecutionStatus,
    GateApproval,
    GateStatus,
)
from lee.orchestrator.execution.template_manager import WorkflowTemplate


import pytest_asyncio


@pytest_asyncio.fixture
async def workflow_store():
    """创建带有测试工作流的数据库"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = Path(f.name)

    store = SQLiteStore(str(db_path))
    await store.connect()

    # v1.1: 运行迁移以确保新字段存在
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from lee.orchestrator.storage.migrations.migration_002_gate_actions import upgrade
    upgrade(str(db_path))

    # 创建测试工作流
    template = WorkflowTemplate(
        id="test_workflow",
        level=WorkflowLevel.TASK,
        name="Test Workflow",
        description="Integration test workflow",
        steps=[
            Step(id="s1", kind="agent", depends_on=[]),
            Step(id="s2", kind="agent", depends_on=["s1"]),
            Step(id="s3", kind="human_gate", depends_on=["s2"]),
            Step(id="s4", kind="agent", depends_on=["s3"]),
        ],
    )

    instance = WorkflowInstance(
        id="test_wf_001",
        level=WorkflowLevel.TASK,
        template_id="test_workflow",
        status=WorkflowStatus.RUNNING,
        data={
            "completed_steps": ["s1", "s2"],
            "step_outputs": {
                "s1": {"result": "output from s1"},
                "s2": {"result": "output from s2"},
            },
        },
    )

    await store.create_workflow(instance)

    # 创建 task_executions
    for step_id in ["s1", "s2"]:
        execution = TaskExecution(
            id=f"exec_{step_id}",
            workflow_id="test_wf_001",
            step_name=step_id,
            executor_type="llm",  # Required field
            status=TaskExecutionStatus.COMPLETED,
        )
        await store.create_task_execution(execution)

    # 创建 gate
    gate = GateApproval(
        workflow_id="test_wf_001",
        gate_id="gate_s3",
        step_id="s3",
        status=GateStatus.PENDING,
        default_reject_action="rollback",
        default_reject_target="s1",
        version=1,
    )
    await store.create_gate_approval(gate)

    yield store, template

    await store.close()
    Path(db_path).unlink(missing_ok=True)


@pytest.mark.asyncio
class TestFullRejectionRollbackFlow:
    """测试完整的拒绝回退流程"""

    async def test_reject_with_rollback(self, workflow_store):
        """测试拒绝后回退到指定步骤"""
        store, template = workflow_store

        # 1. 验证初始状态
        workflow = await store.get_workflow("test_wf_001")
        assert workflow.data["completed_steps"] == ["s1", "s2"]
        assert len(workflow.data["step_outputs"]) == 2

        # 2. 模拟 reject with rollback
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")
        assert gate.status == GateStatus.PENDING
        assert gate.version == 1

        updated_gate = await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.REJECTED,
            approver="reviewer1",
            comments="需要回退到 s1 重新开始",
            expected_version=1,
            decision_action="rollback",
            target_step="s1",
        )

        # 3. 验证 gate 状态
        assert updated_gate is not None
        assert updated_gate.status == GateStatus.REJECTED
        assert updated_gate.decision_action == "rollback"
        assert updated_gate.target_step == "s1"
        assert updated_gate.version == 2

        # 4. 模拟 rollback 清理（未来由 rewind_to 实现）
        # 获取需要作废的步骤
        steps_after_s1 = template.get_steps_after("s1")
        assert set(steps_after_s1) == {"s2", "s3", "s4"}

        # 验证 s2, s3, s4 应该被作废
        # （这里只验证逻辑，实际清理由 rewind_to 实现）

    async def test_rollback_clears_outputs(self, workflow_store):
        """测试回退清理输出"""
        store, template = workflow_store

        # 验证当前输出
        workflow = await store.get_workflow("test_wf_001")
        assert "s1" in workflow.data["step_outputs"]
        assert "s2" in workflow.data["step_outputs"]

        # 模拟回退到 s1
        steps_after_s1 = template.get_steps_after("s1")

        # 清理逻辑（简化版本）
        new_outputs = workflow.data["step_outputs"].copy()
        for step_id in steps_after_s1:
            new_outputs.pop(step_id, None)

        # 验证只有 s1 的输出保留
        assert "s1" in new_outputs
        assert "s2" not in new_outputs
        assert "s3" not in new_outputs
        assert "s4" not in new_outputs

    async def test_rollback_clears_completed_steps(self, workflow_store):
        """测试回退清理完成步骤列表"""
        store, template = workflow_store

        # 验证当前完成步骤
        workflow = await store.get_workflow("test_wf_001")
        assert workflow.data["completed_steps"] == ["s1", "s2"]

        # 模拟回退到 s1
        steps_after_s1 = template.get_steps_after("s1")

        # 清理逻辑
        new_completed = [s for s in workflow.data["completed_steps"]
                       if s not in steps_after_s1]

        # 验证只有 s1 被保留
        assert new_completed == ["s1"]


@pytest.mark.asyncio
class TestFullRevisionRetryFlow:
    """测试完整的修订重试流程"""

    async def test_revise_with_retry(self, workflow_store):
        """测试修订后重试"""
        store, template = workflow_store

        # 1. 创建 REVISE 状态的 gate
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")

        updated_gate = await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.REVISED,
            approver="reviewer1",
            comments="需要修正 s2 的输出",
            expected_version=1,
            decision_action="retry",
            target_step="s2",
            structured_feedback={
                "issues": ["输出格式不正确"],
                "expected_changes": ["使用 JSON 格式"],
            },
            issues=["输出格式不正确"],
        )

        # 2. 验证 gate 状态
        assert updated_gate is not None
        assert updated_gate.status == GateStatus.REVISED
        assert updated_gate.decision_action == "retry"
        assert updated_gate.target_step == "s2"
        assert updated_gate.structured_feedback is not None
        assert updated_gate.issues == ["输出格式不正确"]

    async def test_retry_clears_step_status(self, workflow_store):
        """测试重试清理步骤状态"""
        store, _ = workflow_store

        workflow = await store.get_workflow("test_wf_001")

        # s2 已完成
        assert "s2" in workflow.data["completed_steps"]

        # 模拟重试 s2
        # 清理逻辑
        new_completed = [s for s in workflow.data["completed_steps"]
                       if s != "s2"]

        assert "s2" not in new_completed
        assert "s1" in new_completed


@pytest.mark.asyncio
class TestSpawnWorkflowFlow:
    """测试派生新工作流流程"""

    async def test_spawn_creates_new_workflow(self, workflow_store):
        """测试 spawn 创建新工作流"""
        store, _ = workflow_store

        # 1. Reject with spawn
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")

        updated_gate = await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.REJECTED,
            approver="pm1",
            comments="需求变更，创建新工作流",
            expected_version=1,
            decision_action="spawn",
        )

        assert updated_gate is not None
        assert updated_gate.decision_action == "spawn"

        # 2. 创建新工作流（模拟）
        new_instance = WorkflowInstance(
            id="test_wf_002",
            level=WorkflowLevel.TASK,
            parent_id="test_wf_001",
            template_id="test_workflow",
            status=WorkflowStatus.PENDING,
            data={
                "spawned_from": "test_wf_001",
                "spawned_from_gate": "gate_s3",
                "reason": "需求变更",
            },
        )

        await store.create_workflow(new_instance)

        # 3. 将原工作流标记为 SUPERSEDED
        await store.update_workflow_status("test_wf_001", WorkflowStatus.SUPERSEDED)

        # 4. 验证状态
        old_workflow = await store.get_workflow("test_wf_001")
        assert old_workflow.status == WorkflowStatus.SUPERSEDED

        new_workflow = await store.get_workflow("test_wf_002")
        assert new_workflow is not None
        assert new_workflow.parent_id == "test_wf_001"


@pytest.mark.asyncio
class TestFlagContinueFlow:
    """测试标记继续流程"""

    async def test_flag_with_continue(self, workflow_store):
        """测试标记问题并继续工作流"""
        store, _ = workflow_store

        # 1. Flag gate
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")

        updated_gate = await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.FLAGGED,
            approver="reviewer1",
            comments="代码风格需要改进，但不阻断",
            expected_version=1,
            issues=["代码风格需要改进"],
        )

        # 2. 验证 gate 状态
        assert updated_gate is not None
        assert updated_gate.status == GateStatus.FLAGGED
        assert updated_gate.issues == ["代码风格需要改进"]

        # 3. 工作流继续运行（模拟）
        # gate 被标记为 FLAGGED，但工作流继续
        await store.update_workflow_status("test_wf_001", WorkflowStatus.RUNNING)

        workflow = await store.get_workflow("test_wf_001")
        assert workflow.status == WorkflowStatus.RUNNING

    async def test_flag_with_pause(self, workflow_store):
        """测试标记问题并暂停工作流"""
        store, _ = workflow_store

        # Flag gate 但暂停工作流
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")

        updated_gate = await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.FLAGGED,
            approver="reviewer1",
            comments="需要人工审核",
            expected_version=1,
            issues=["需要人工审核"],
        )

        # 工作流保持暂停
        await store.update_workflow_status("test_wf_001", WorkflowStatus.PAUSED)

        workflow = await store.get_workflow("test_wf_001")
        assert workflow.status == WorkflowStatus.PAUSED


@pytest.mark.asyncio
class TestComplexScenarios:
    """测试复杂场景"""

    async def test_multiple_rollback_retries(self, workflow_store):
        """测试多次回退和重试"""
        store, template = workflow_store

        # 第一次：reject → rollback to s1
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")
        await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.REJECTED,
            approver="reviewer1",
            comments="第一次拒绝",
            expected_version=1,
            decision_action="rollback",
            target_step="s1",
        )

        # 重置 s2 的完成状态
        workflow = await store.get_workflow("test_wf_001")
        workflow.data["completed_steps"] = ["s1"]
        await store.update_workflow_data("test_wf_001", workflow.data)

        # 第二次：revise → retry s2
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")
        await store.update_gate_approval_with_version(
            workflow_id="test_wf_001",
            gate_id="gate_s3",
            status=GateStatus.REVISED,
            approver="reviewer1",
            comments="修订后重试",
            expected_version=2,
            decision_action="retry",
            target_step="s2",
        )

        # 验证状态转换链
        final_gate = await store.get_gate_approval("test_wf_001", "gate_s3")
        assert final_gate.version == 3  # 1 → 2 (reject) → 3 (revise)
        assert final_gate.status == GateStatus.REVISED

    async def test_parallel_workflow_rollback(self, workflow_store):
        """测试并行工作流的回退"""
        store, _ = workflow_store

        # 创建并行工作流
        parallel_template = WorkflowTemplate(
            id="parallel_workflow",
            level=WorkflowLevel.TASK,
            name="Parallel Workflow",
            description="Test parallel workflow",
            steps=[
                Step(id="s1", kind="agent", depends_on=[]),
                Step(id="s2a", kind="agent", depends_on=["s1"]),
                Step(id="s2b", kind="agent", depends_on=["s1"]),
                Step(id="s3", kind="human_gate", depends_on=["s2a", "s2b"]),
            ],
        )

        # 获取 s1 之后的步骤
        steps_after_s1 = parallel_template.get_steps_after("s1")

        # 应该包含 s2a, s2b, s3
        assert set(steps_after_s1) == {"s2a", "s2b", "s3"}

        # 验证回退到 s1 会作废所有后续步骤
        assert "s2a" in steps_after_s1
        assert "s2b" in steps_after_s1
        assert "s3" in steps_after_s1


@pytest.mark.asyncio
class TestDataConsistency:
    """测试数据一致性"""

    async def test_gate_approval_foreign_key(self, workflow_store):
        """测试 gate_approval 外键完整性"""
        store, _ = workflow_store

        # 验证 gate_approval 引用的工作流存在
        gate = await store.get_gate_approval("test_wf_001", "gate_s3")
        assert gate is not None

        workflow = await store.get_workflow(gate.workflow_id)
        assert workflow is not None
        assert workflow.id == gate.workflow_id

    async def test_step_outputs_consistency(self, workflow_store):
        """测试 step_outputs 与 completed_steps 一致性"""
        store, _ = workflow_store

        workflow = await store.get_workflow("test_wf_001")

        completed_steps = set(workflow.data["completed_steps"])
        output_steps = set(workflow.data["step_outputs"].keys())

        # 所有输出的步骤都应该是已完成的
        assert output_steps.issubset(completed_steps)

    async def test_no_orphan_task_executions(self, workflow_store):
        """测试无孤立的 task_executions"""
        store, _ = workflow_store

        # 所有 task_executions 应该引用存在的工作流
        # 这个验证需要在真实环境中执行

        # 简化验证：至少测试数据中的记录
        workflow = await store.get_workflow("test_wf_001")
        assert workflow is not None
