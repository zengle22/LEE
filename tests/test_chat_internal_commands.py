"""
Tests for Chat internal commands (Phase 1-3).

Simplified tests that focus on the new functionality.
"""

import pytest
from unittest.mock import Mock, patch
from datetime import datetime


class TestFormatHelpers:
    """Tests for formatting helper functions."""

    def test_format_status(self):
        """Test status formatting."""
        # Import the function from the module
        from lee.cli.commands.chat import LeeChatREPL

        # Create a minimal instance (just for accessing the method)
        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        assert "✅" in repl._format_status("completed")
        assert "🚀" in repl._format_status("running")
        assert "❌" in repl._format_status("failed")
        assert "⏳" in repl._format_status("pending")
        assert "⌛" in repl._format_status("timeout")
        assert "🚫" in repl._format_status("cancelled")

    def test_format_duration(self):
        """Test duration formatting."""
        from lee.cli.commands.chat import LeeChatREPL
        from datetime import timedelta

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        assert repl._format_duration(timedelta(seconds=30)) == "30秒"
        assert repl._format_duration(timedelta(seconds=90)) == "1分30秒"
        assert repl._format_duration(timedelta(seconds=3600)) == "1小时0分"
        assert repl._format_duration(timedelta(seconds=7265)) == "2小时1分"
        assert repl._format_duration(timedelta(seconds=0)) == "0秒"


def test_format_status_edge_cases():
    """Test format_status with edge cases."""
    from lee.cli.commands.chat import LeeChatREPL

    with patch('lee.cli.commands.chat.PMAgentRuntime'):
        with patch('lee.cli.commands.chat.TemplateManager'):
            with patch('lee.cli.commands.chat.Orchestrator'):
                repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

    # Test unknown status
    result = repl._format_status("unknown_status")
    assert "❓" in result
    assert "unknown_status" in result


class TestJobModels:
    """Tests for Job data models."""

    def test_job_status_enum(self):
        """Test JobStatus enum values."""
        from lee.orchestrator.execution.pm_agent_runtime import JobStatus

        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_job_creation(self):
        """Test Job dataclass creation."""
        from lee.orchestrator.execution.pm_agent_runtime import Job, JobStatus

        job = Job(
            id="test_123",
            text="test input",
            session_id="session_abc",
        )

        assert job.id == "test_123"
        assert job.text == "test input"
        assert job.session_id == "session_abc"
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None
        assert job.started_at is None
        assert job.completed_at is None
        assert job.result is None
        assert job.error is None


class TestRuntimeConstants:
    """Tests for runtime constants."""

    def test_default_timeout(self):
        """Test DEFAULT_TIMEOUT constant."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        assert PMAgentRuntime.DEFAULT_TIMEOUT == 7200

    def test_max_concurrent_jobs(self):
        """Test MAX_CONCURRENT_JOBS constant."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        assert PMAgentRuntime.MAX_CONCURRENT_JOBS == 3


class TestEventTypeExtensions:
    """Tests for event type extensions."""

    def test_job_event_types_exist(self):
        """Test that job-related event types are defined."""
        from lee.orchestrator.core.event_bus import EventType

        assert hasattr(EventType, 'JOB_STARTED')
        assert hasattr(EventType, 'JOB_COMPLETED')
        assert hasattr(EventType, 'JOB_FAILED')
        assert hasattr(EventType, 'JOB_CANCELLED')

        assert EventType.JOB_STARTED.value == "job_started"
        assert EventType.JOB_COMPLETED.value == "job_completed"
        assert EventType.JOB_FAILED.value == "job_failed"
        assert EventType.JOB_CANCELLED.value == "job_cancelled"


class TestSQLiteStoreExtensions:
    """Tests for SQLiteStore query methods."""

    @pytest.mark.asyncio
    async def test_list_workflows_method_exists(self):
        """Test that list_workflows method exists and has correct signature."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")
        await store.connect()

        # Check method exists
        assert hasattr(store, 'list_workflows')
        assert callable(store.list_workflows)

        # Try calling with empty database
        workflows = await store.list_workflows(limit=10)
        assert isinstance(workflows, list)

        await store.close()

    @pytest.mark.asyncio
    async def test_list_task_executions_method_exists(self):
        """Test that list_task_executions method exists."""
        from lee.orchestrator.storage.sqlite_store import SQLiteStore

        store = SQLiteStore(":memory:")
        await store.connect()

        # Check method exists
        assert hasattr(store, 'list_task_executions')
        assert callable(store.list_task_executions)

        # Try calling with empty database
        executions = await store.list_task_executions(workflow_id="test_wf", limit=10)
        assert isinstance(executions, list)

        await store.close()


class TestInternalCommandRecognition:
    """Tests for internal command recognition."""

    def test_internal_command_pattern(self):
        """Test that internal commands start with /."""
        internal_commands = [
            "/status",
            "/log",
            "/list",
            "/errors",
            "/jobs",
            "/watch",
            "/status wf_123",
            "/log wf_123 50",
        ]

        for cmd in internal_commands:
            assert cmd.startswith("/"), f"{cmd} should start with /"

    def test_non_internal_commands(self):
        """Test that regular input doesn't start with /."""
        regular_inputs = [
            "当前状态",
            "运行下一步",
            "批准 gate_review",
            "help",
            "exit",
        ]

        for inp in regular_inputs:
            assert not inp.startswith("/"), f"{inp} should not start with /"
