"""
Coverage tests for SQLiteStore database operations.

Tests various database operations and edge cases.
"""

import pytest
from aiosqlite import Connection
from datetime import datetime
from pathlib import Path
import tempfile
import os


class TestSQLiteStoreBasic:
    """Basic tests for SQLiteStore."""

    @pytest.mark.asyncio
    async def test_store_creates_database_file(self):
        """Test that store creates a database file."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            store = SQLiteStore(db_path)

            await store.connect()

            # Database file should exist
            assert os.path.exists(db_path)

            await store.close()

    @pytest.mark.asyncio
    async def test_store_in_memory_database(self):
        """Test that store can use in-memory database."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")

        await store.connect()

        # Should be able to connect
        assert store._conn is not None

        await store.close()


class TestSQLiteStoreWorkflowOperations:
    """Tests for workflow CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_workflow_retrievable(self):
        """Test that created workflow can be retrieved."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import (
            WorkflowInstance, WorkflowLevel, WorkflowStatus
        )

        store = SQLiteStore(":memory:")
        await store.connect()

        wf = WorkflowInstance(
            id="test_wf",
            level=WorkflowLevel.TASK,
            template_id="test_template",
            status=WorkflowStatus.RUNNING,
            current_step="step1",
        )

        await store.create_workflow(wf)

        retrieved = await store.get_workflow("test_wf")

        assert retrieved is not None
        assert retrieved.id == "test_wf"
        assert retrieved.template_id == "test_template"

        await store.close()

    @pytest.mark.asyncio
    async def test_update_workflow_status(self):
        """Test that workflow status can be updated."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import (
            WorkflowInstance, WorkflowLevel, WorkflowStatus
        )

        store = SQLiteStore(":memory:")
        await store.connect()

        wf = WorkflowInstance(
            id="test_wf",
            level=WorkflowLevel.TASK,
            template_id="test",
            status=WorkflowStatus.PENDING,
        )

        await store.create_workflow(wf)

        # Update status
        await store.update_workflow_status(
            "test_wf",
            WorkflowStatus.RUNNING,
            current_step="step1"
        )

        # Verify update
        updated = await store.get_workflow("test_wf")
        assert updated.status == WorkflowStatus.RUNNING
        assert updated.current_step == "step1"

        await store.close()


class TestSQLiteStoreTaskExecution:
    """Tests for task execution operations."""

    @pytest.mark.asyncio
    async def test_create_task_execution(self):
        """Test creating task execution record."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import (
            TaskExecution, TaskExecutionStatus
        )

        store = SQLiteStore(":memory:")
        await store.connect()

        task = TaskExecution(
            id="task_1",
            workflow_id="wf_1",
            step_name="test_step",
            executor_type="shell",
            input_data={"command": "echo hello"},
        )

        result = await store.create_task_execution(task)

        assert result is not None
        assert result.id == "task_1"

        await store.close()

    @pytest.mark.asyncio
    async def test_update_task_execution_status(self):
        """Test updating task execution status."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import (
            TaskExecution, TaskExecutionStatus
        )
        from datetime import datetime

        store = SQLiteStore(":memory:")
        await store.connect()

        task = TaskExecution(
            id="task_1",
            workflow_id="wf_1",
            step_name="test_step",
            executor_type="shell",
        )

        await store.create_task_execution(task)

        # Update status
        await store.update_task_execution(
            "task_1",
            TaskExecutionStatus.COMPLETED,
            output_data={"exit_code": 0},
            completed_at=datetime.now()
        )

        # Verify update
        updated = await store.get_task_executions("wf_1")
        assert len(updated) == 1
        assert updated[0].status == TaskExecutionStatus.COMPLETED

        await store.close()


class TestSQLiteStoreGateOperations:
    """Tests for gate approval operations."""

    @pytest.mark.asyncio
    async def test_create_gate_approval(self):
        """Test creating gate approval."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import GateApproval, GateStatus

        store = SQLiteStore(":memory:")
        await store.connect()

        gate = GateApproval(
            workflow_id="wf_1",
            gate_id="gate_1",
            step_id="step_1",
            status=GateStatus.PENDING,
            approver=None,
        )

        result = await store.create_gate_approval(gate)

        assert result is not None
        assert result.gate_id == "gate_1"

        await store.close()

    @pytest.mark.asyncio
    async def test_get_pending_gates(self):
        """Test retrieving pending gates."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import GateApproval, GateStatus

        store = SQLiteStore(":memory:")
        await store.connect()

        # Create pending gate
        gate = GateApproval(
            workflow_id="wf_1",
            gate_id="gate_1",
            step_id="step_1",
            status=GateStatus.PENDING,
        )
        await store.create_gate_approval(gate)

        # Create approved gate
        gate2 = GateApproval(
            workflow_id="wf_1",
            gate_id="gate_2",
            step_id="step_2",
            status=GateStatus.APPROVED,
        )
        await store.create_gate_approval(gate2)

        # Get pending gates
        pending = await store.get_pending_gates("wf_1")

        assert len(pending) == 1
        assert pending[0].gate_id == "gate_1"

        await store.close()


class TestSQLiteStoreTemplate:
    """Tests for template operations."""

    @pytest.mark.asyncio
    async def test_create_template(self):
        """Test creating a template."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import Template, WorkflowLevel

        store = SQLiteStore(":memory:")
        await store.connect()

        template = Template(
            id="template_1",
            level=WorkflowLevel.TASK,
            name="Test Template",
            content="yaml: content",
        )

        result = await store.create_template(template)

        assert result is not None
        assert result.id == "template_1"

        await store.close()

    @pytest.mark.asyncio
    async def test_get_template(self):
        """Test retrieving a template."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import Template, WorkflowLevel

        store = SQLiteStore(":memory:")
        await store.connect()

        template = Template(
            id="template_1",
            level=WorkflowLevel.TASK,
            name="Test",
            content="content",
        )

        await store.create_template(template)

        retrieved = await store.get_template("template_1")

        assert retrieved is not None
        assert retrieved.name == "Test"

        await store.close()


class TestSQLiteStoreTransaction:
    """Tests for transaction support."""

    @pytest.mark.asyncio
    async def test_transaction_commit(self):
        """Test that transaction commits changes."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel

        store = SQLiteStore(":memory:")
        await store.connect()

        async with store.transaction() as cursor:
            await cursor.execute("""
                INSERT INTO workflow_instances
                (id, level, template_id, status, current_step, data, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ("wf_1", WorkflowLevel.TASK.value, "test", "pending", None, "{}",
                  datetime.now().isoformat(), datetime.now().isoformat()))

        # Verify commit
        wf = await store.get_workflow("wf_1")
        assert wf is not None

        await store.close()

    @pytest.mark.asyncio
    async def test_transaction_rollback(self):
        """Test that transaction rolls back on error."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import WorkflowLevel

        store = SQLiteStore(":memory:")
        await store.connect()

        try:
            async with store.transaction() as cursor:
                await cursor.execute("""
                    INSERT INTO workflow_instances
                    (id, level, template_id, status, current_step, data, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, ("wf_1", WorkflowLevel.TASK.value, "test", "pending", None, "{}",
                      datetime.now().isoformat(), datetime.now().isoformat()))

                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify rollback - workflow should not exist
        wf = await store.get_workflow("wf_1")
        assert wf is None

        await store.close()


class TestSQLiteStoreQueries:
    """Tests for query operations."""

    @pytest.mark.asyncio
    async def test_list_workflows_empty(self):
        """Test list_workflows returns empty list initially."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")
        await store.connect()

        workflows = await store.list_workflows()

        assert isinstance(workflows, list)
        assert len(workflows) == 0

        await store.close()

    @pytest.mark.asyncio
    async def test_list_workflows_with_data(self):
        """Test list_workflows returns workflows."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore
        from lee.orchestrator.storage.models import WorkflowInstance, WorkflowLevel

        store = SQLiteStore(":memory:")
        await store.connect()

        # Create workflows
        for i in range(3):
            wf = WorkflowInstance(
                id=f"wf_{i}",
                level=WorkflowLevel.TASK,
                template_id="test",
                status="running",
            )
            await store.create_workflow(wf)

        workflows = await store.list_workflows(limit=10)

        assert len(workflows) == 3

        await store.close()

    @pytest.mark.asyncio
    async def test_list_task_executions_empty(self):
        """Test list_task_executions with no executions."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")
        await store.connect()

        executions = await store.list_task_executions("wf_1", limit=10)

        assert isinstance(executions, list)
        assert len(executions) == 0

        await store.close()


class TestSQLiteStoreConnection:
    """Tests for connection management."""

    @pytest.mark.asyncio
    async def test_connect_creates_connection(self):
        """Test that connect creates a connection."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")
        await store.connect()

        assert store._conn is not None
        assert isinstance(store._conn, Connection)

        await store.close()

    @pytest.mark.asyncio
    async def test_close_clears_connection(self):
        """Test that close clears the connection."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")
        await store.connect()

        await store.close()

        assert store._conn is None
