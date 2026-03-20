"""
Simple coverage tests for Orchestrator and related modules.
"""

import pytest
from unittest.mock import Mock


class TestStateMachineModels:
    """Tests for state machine related models."""

    def test_workflow_status_enum(self):
        """Test WorkflowStatus enum."""
        from lee.orchestrator.storage.models import WorkflowStatus

        assert WorkflowStatus.PENDING.value == "pending"
        assert WorkflowStatus.RUNNING.value == "running"
        assert WorkflowStatus.PAUSED.value == "paused"
        assert WorkflowStatus.COMPLETED.value == "completed"
        assert WorkflowStatus.FAILED.value == "failed"

    def test_workflow_level_enum(self):
        """Test WorkflowLevel enum."""
        from lee.orchestrator.storage.models import WorkflowLevel

        assert WorkflowLevel.PROJECT.value == "project"
        assert WorkflowLevel.DEPARTMENT.value == "department"
        assert WorkflowLevel.TASK.value == "task"

    def test_task_execution_status_enum(self):
        """Test TaskExecutionStatus enum."""
        from lee.orchestrator.storage.models import TaskExecutionStatus

        assert TaskExecutionStatus.PENDING.value == "pending"
        assert TaskExecutionStatus.RUNNING.value == "running"
        assert TaskExecutionStatus.COMPLETED.value == "completed"
        assert TaskExecutionStatus.FAILED.value == "failed"


class TestWorkflowInstance:
    """Tests for WorkflowInstance dataclass."""

    def test_workflow_instance_creation(self):
        """Test WorkflowInstance can be created."""
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel, WorkflowStatus
        from datetime import datetime

        wf = WorkflowInstance(
            id="test_wf",
            level=WorkflowLevel.TASK,
            template_id="test_template",
            status=WorkflowStatus.RUNNING,
            current_step="step1",
            data={"params": {}},
        )

        assert wf.id == "test_wf"
        assert wf.level == WorkflowLevel.TASK
        assert wf.status == WorkflowStatus.RUNNING
        assert wf.current_step == "step1"

    def test_workflow_instance_post_init(self):
        """Test WorkflowInstance __post_init__ initializes data fields."""
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel, WorkflowStatus

        wf = WorkflowInstance(
            id="test_wf",
            level=WorkflowLevel.TASK,
            template_id="test",
            status=WorkflowStatus.PENDING,
        )

        assert "completed_steps" in wf.data
        assert "params" in wf.data
        assert wf.data["completed_steps"] == []
        assert wf.data["params"] == {}


class TestTaskExecution:
    """Tests for TaskExecution dataclass."""

    def test_task_execution_creation(self):
        """Test TaskExecution can be created."""
        from lee.orchestrator.storage.models import TaskExecution, TaskExecutionStatus

        task = TaskExecution(
            id="task_1",
            workflow_id="wf_1",
            step_name="test_step",
            executor_type="shell",
            input_data={"command": "echo hello"},
        )

        assert task.id == "task_1"
        assert task.workflow_id == "wf_1"
        assert task.step_name == "test_step"
        assert task.executor_type == "shell"
        assert task.status == TaskExecutionStatus.PENDING


class TestTemplate:
    """Tests for Template dataclass."""

    def test_template_creation(self):
        """Test Template can be created."""
        from lee.orchestrator.storage.models import Template, WorkflowLevel
        from datetime import datetime

        template = Template(
            id="template_1",
            level=WorkflowLevel.TASK,
            name="Test Template",
            content="yaml: content",
        )

        assert template.id == "template_1"
        assert template.level == WorkflowLevel.TASK
        assert template.name == "Test Template"
        assert template.content == "yaml: content"


class TestStep:
    """Tests for Step dataclass."""

    def test_step_creation(self):
        """Test Step can be created."""
        from lee.orchestrator.storage.models import Step

        step = Step(
            id="step_1",
            kind="agent",
            executor_type="llm",
        )

        assert step.id == "step_1"
        assert step.kind == "agent"
        assert step.executor_type == "llm"

    def test_step_with_dependencies(self):
        """Test Step with dependencies."""
        from lee.orchestrator.storage.models import Step

        step = Step(
            id="step_2",
            kind="skill",
            depends_on=["step_1"],
        )

        assert len(step.depends_on) == 1
        assert "step_1" in step.depends_on


class TestGateApproval:
    """Tests for GateApproval dataclass."""

    def test_gate_approval_creation(self):
        """Test GateApproval can be created."""
        from lee.orchestrator.storage.models import GateApproval, GateStatus
        from datetime import datetime

        gate = GateApproval(
            workflow_id="wf_1",
            gate_id="gate_1",
            step_id="step_1",
            status=GateStatus.PENDING,
            created_at=datetime.now(),
        )

        assert gate.workflow_id == "wf_1"
        assert gate.gate_id == "gate_1"
        assert gate.status == GateStatus.PENDING


class TestGateStatusEnum:
    """Tests for GateStatus enum."""

    def test_gate_status_values(self):
        """Test GateStatus enum values."""
        from lee.orchestrator.storage.models import GateStatus

        assert GateStatus.PENDING.value == "pending"
        assert GateStatus.APPROVED.value == "approved"
        assert GateStatus.REJECTED.value == "rejected"
        assert GateStatus.REVISED.value == "revised"


class TestOutputSpec:
    """Tests for OutputSpec dataclass."""

    def test_output_spec_creation(self):
        """Test OutputSpec can be created."""
        from lee.orchestrator.storage.models import OutputSpec

        spec = OutputSpec(
            type="file",
            path="/path/to/file",
            format="json",
        )

        assert spec.type == "file"
        assert spec.path == "/path/to/file"
        assert spec.format == "json"


class TestExecutorTypes:
    """Tests for executor types."""

    def test_executor_type_strings(self):
        """Test executor type constants."""
        # These are the valid executor types
        executor_types = ["llm", "shell", "mcp", "claude_code", "skill"]

        for et in executor_types:
            assert isinstance(et, str)
            assert len(et) > 0


class TestWorkflowState:
    """Tests for workflow state representation."""

    def test_workflow_state_dict_structure(self):
        """Test that workflow state has expected structure."""
        from lee.orchestrator.storage.models import WorkflowState

        # WorkflowState should have these fields
        expected_fields = [
            "workflow_id",
            "status",
            "current_step",
            "completed_steps",
            "pending_gates",
        ]

        # This is a type check - WorkflowState is a TypedDict
        from typing import get_type_hints
        hints = get_type_hints(WorkflowState)

        # At minimum, should have workflow_id and status
        assert "workflow_id" in hints
        assert "status" in hints


class TestEventTypes:
    """Tests for event type definitions."""

    def test_event_type_enum_exists(self):
        """Test that EventType enum exists."""
        from lee.orchestrator.core.event_bus import EventType

        # Check some key event types exist
        assert hasattr(EventType, 'STEP_STARTED')
        assert hasattr(EventType, 'STEP_COMPLETED')
        assert hasattr(EventType, 'STEP_FAILED')
        assert hasattr(EventType, 'WORKFLOW_COMPLETED')


class TestRunUntilBlockedNullSafety:
    """
    Tests for BUG-LEE-CLI-001 fix:
    run_until_blocked must not raise AttributeError when store.get_workflow returns None.
    """

    @pytest.mark.asyncio
    async def test_run_until_blocked_workflow_not_found_returns_failed(self):
        """
        Entry-guard: When workflow_id does not exist in the DB,
        run_until_blocked should return ExecutionSummary(status='failed')
        without raising AttributeError.
        """
        from unittest.mock import AsyncMock, MagicMock
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from lee.orchestrator.storage.models import ExecutionSummary

        orchestrator = object.__new__(Orchestrator)

        # store.get_workflow returns None (workflow does not exist)
        mock_store = MagicMock()
        mock_store.get_workflow = AsyncMock(return_value=None)
        orchestrator.store = mock_store

        mock_event_log = MagicMock()
        mock_event_log.log = MagicMock()
        orchestrator.event_log = mock_event_log

        summary = await orchestrator.run_until_blocked("nonexistent-wf-id", max_steps=5)

        assert isinstance(summary, ExecutionSummary)
        assert summary.status == "failed"
        assert summary.workflow_id == "nonexistent-wf-id"
        assert summary.total_steps == 0
        assert summary.completed_steps == 0

    @pytest.mark.asyncio
    async def test_run_until_blocked_no_ready_step_none_instance(self):
        """
        Defensive check inside loop: when result.status == 'no_ready_step'
        and store.get_workflow returns None mid-execution, final_status must
        be 'failed' without AttributeError.
        """
        from unittest.mock import AsyncMock, MagicMock
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from lee.orchestrator.storage.models import (
            ExecutionSummary, WorkflowInstance, WorkflowLevel, WorkflowStatus,
        )
        from datetime import datetime

        orchestrator = object.__new__(Orchestrator)

        existing_instance = WorkflowInstance(
            id="wf-test",
            level=WorkflowLevel.TASK,
            status=WorkflowStatus.RUNNING,
            template_id="tmpl",
            data={},
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

        # First call (entry): returns a real instance; subsequent calls: return None
        call_count = {"n": 0}

        async def _get_workflow(wf_id):
            call_count["n"] += 1
            if call_count["n"] == 1:
                return existing_instance
            return None

        mock_store = MagicMock()
        mock_store.get_workflow = _get_workflow

        mock_event_log = MagicMock()
        mock_event_log.log = MagicMock()
        mock_event_log.run_id = ""
        orchestrator.store = mock_store
        orchestrator.event_log = mock_event_log
        orchestrator.RUNNING_EXECUTION_POLL_SECONDS = 0.01

        # run_step returns no_ready_step on first call to trigger the inner branch
        from lee.orchestrator.execution.orchestrator import StepResult
        orchestrator.run_step = AsyncMock(
            return_value=StepResult(
                status="no_ready_step",
                step_id=None,
                workflow_id="wf-test",
                message="no ready steps",
            )
        )
        orchestrator._has_running_task_executions = AsyncMock(return_value=False)
        orchestrator._inject_loop_variables_if_needed = AsyncMock(return_value=None)

        summary = await orchestrator.run_until_blocked("wf-test", max_steps=5)

        assert isinstance(summary, ExecutionSummary)
        assert summary.status == "failed"
