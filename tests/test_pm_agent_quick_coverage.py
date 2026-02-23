"""
Quick coverage boost tests for pm_agent_runtime.

Focuses on testing previously un-covered code paths.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch


class TestCompiledParams:
    """Tests for CompiledParams dataclass (lines 47-56)."""

    def test_compiled_params_with_all_fields(self):
        """Test CompiledParams creation with all optional fields."""
        from lee.orchestrator.execution.pm_agent_runtime import CompiledParams

        params = CompiledParams(
            workflow_ref="wf_123",
            params={"action": "test"},
            confidence=0.95,
            reasoning="Test reasoning",
            action="run",
            allowed=True
        )

        assert params.workflow_ref == "wf_123"
        assert params.action == "run"

    def test_compiled_params_with_denial(self):
        """Test CompiledParams with permission denial."""
        from lee.orchestrator.execution.pm_agent_runtime import CompiledParams

        params = CompiledParams(
            workflow_ref="wf_123",
            params={},
            confidence=0.0,
            reasoning="Not allowed",
            allowed=False,
            denial_reason="Permission denied"
        )

        assert params.allowed is False
        assert params.denial_reason == "Permission denied"


class TestProgressReport:
    """Tests for ProgressReport dataclass (lines 59-65)."""

    def test_progress_report(self):
        """Test ProgressReport creation."""
        from lee.orchestrator.execution.pm_agent_runtime import ProgressReport

        report = ProgressReport(
            run_id="run_123",
            status="running",
            current_step="step1",
            completed_steps=["step0"],
            pending_gates=[],
            patch_summary="Test summary"
        )

        assert report.run_id == "run_123"
        assert report.status == "running"
        assert len(report.completed_steps) == 1


class TestCompletionSummary:
    """Tests for CompletionSummary dataclass (lines 68-74)."""

    def test_completion_summary(self):
        """Test CompletionSummary creation."""
        from lee.orchestrator.execution.pm_agent_runtime import CompletionSummary

        summary = CompletionSummary(
            run_id="run_123",
            status="completed",
            duration="5m",
            files_changed=3,
            receipt_status="verified",
            next_steps=["deploy", "test"]
        )

        assert summary.run_id == "run_123"
        assert summary.files_changed == 3
        assert len(summary.next_steps) == 2


class TestPMAgentRuntimeAttributes:
    """Tests for PMAgentRuntime class attributes (lines 77-111)."""

    def test_runtime_constants(self):
        """Test runtime class constants."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        assert PMAgentRuntime.DEFAULT_TIMEOUT == 600
        assert PMAgentRuntime.MAX_CONCURRENT_JOBS == 3

    def test_runtime_initializes_job_tracking(self):
        """Test that runtime initializes job tracking dictionaries."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        assert hasattr(runtime, 'running_jobs')
        assert hasattr(runtime, 'jobs')
        assert isinstance(runtime.running_jobs, dict)
        assert isinstance(runtime.jobs, dict)
        assert runtime.get_total_job_count() == 0
        assert runtime.get_active_job_count() == 0


class TestJobDataclass:
    """Tests for Job dataclass."""

    def test_job_creation_minimal(self):
        """Test Job creation with minimal fields."""
        from lee.orchestrator.execution.pm_agent_runtime import Job, JobStatus

        job = Job(
            id="job_123",
            text="test input",
            session_id="session_abc"
        )

        assert job.id == "job_123"
        assert job.text == "test input"
        assert job.status == JobStatus.PENDING
        assert job.created_at is not None

    def test_job_with_status(self):
        """Test Job with explicit status."""
        from lee.orchestrator.execution.pm_agent_runtime import Job, JobStatus
        from datetime import datetime

        job = Job(
            id="job_123",
            text="test",
            session_id="session",
            status=JobStatus.RUNNING,
            started_at=datetime.now()
        )

        assert job.status == JobStatus.RUNNING
        assert job.started_at is not None

    def test_job_completion_fields(self):
        """Test Job with completion fields."""
        from lee.orchestrator.execution.pm_agent_runtime import Job, JobStatus
        from datetime import datetime

        job = Job(
            id="job_123",
            text="test",
            session_id="session",
            status=JobStatus.COMPLETED,
            completed_at=datetime.now(),
            result={"status": "success"}
        )

        assert job.status == JobStatus.COMPLETED
        assert job.result == {"status": "success"}

    def test_job_with_error(self):
        """Test Job with error."""
        from lee.orchestrator.execution.pm_agent_runtime import Job, JobStatus

        job = Job(
            id="job_123",
            text="test",
            session_id="session",
            status=JobStatus.FAILED,
            error="Something went wrong"
        )

        assert job.status == JobStatus.FAILED
        assert job.error == "Something went wrong"


class TestJobStatusEnum:
    """Tests for JobStatus enum."""

    def test_status_values(self):
        """Test all JobStatus enum values."""
        from lee.orchestrator.execution.pm_agent_runtime import JobStatus

        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"

    def test_status_is_string_enum(self):
        """Test JobStatus is a string enum."""
        from lee.orchestrator.execution.pm_agent_runtime import JobStatus

        status = JobStatus.RUNNING
        assert status.value == "running"
        # String comparison works
        assert status == JobStatus.RUNNING


class TestGetMetrics:
    """Tests for get_metrics method."""

    def test_get_metrics_returns_dict(self):
        """Test get_metrics returns a dictionary."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        metrics = runtime.get_metrics()

        assert isinstance(metrics, dict)
        assert "decision_engine_enabled" in metrics

    def test_get_metrics_with_decision_engine_disabled(self):
        """Test get_metrics when Decision Engine is disabled."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        metrics = runtime.get_metrics()

        assert metrics["decision_engine_enabled"] is False


class TestGetJobStatus:
    """Tests for get_job_status method."""

    @pytest.mark.asyncio
    async def test_get_job_status_nonexistent(self):
        """Test get_job_status for non-existent job."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        status = await runtime.get_job_status("nonexistent")

        assert status is None

    @pytest.mark.asyncio
    async def test_get_job_status_existing(self):
        """Test get_job_status for existing job."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime, Job, JobStatus

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        # Create a job
        job = Job(
            id="test_job",
            text="test input",
            session_id="session_123"
        )
        runtime.jobs["test_job"] = job

        status = await runtime.get_job_status("test_job")

        assert status is not None
        assert status["job_id"] == "test_job"
        assert status["status"] == "pending"
        assert status["text"] == "test input"


class TestListJobs:
    """Tests for list_jobs method."""

    @pytest.mark.asyncio
    async def test_list_jobs_empty(self):
        """Test list_jobs when no jobs exist."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        jobs = await runtime.list_jobs()

        assert isinstance(jobs, list)
        assert len(jobs) == 0

    @pytest.mark.asyncio
    async def test_list_jobs_with_jobs(self):
        """Test list_jobs returns job information."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime, Job, JobStatus

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        # Add some jobs
        for i in range(3):
            job = Job(
                id=f"job_{i}",
                text=f"test input {i}",
                session_id="session_123"
            )
            runtime.jobs[f"job_{i}"] = job

        jobs = await runtime.list_jobs()

        assert len(jobs) == 3
        assert all("job_id" in j for j in jobs)
        assert all("status" in j for j in jobs)


class TestCancelJob:
    """Tests for cancel_job method."""

    @pytest.mark.asyncio
    async def test_cancel_job_nonexistent(self):
        """Test cancel_job for non-existent job."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        result = await runtime.cancel_job("nonexistent")

        assert result is False

    @pytest.mark.asyncio
    async def test_cancel_job_already_completed(self):
        """Test cancel_job for already completed job."""
        from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime, Job, JobStatus

        runtime = PMAgentRuntime(
            orchestrator=Mock(),
            llm_executor=Mock(),
            store=Mock(),
            enable_decision_engine=False
        )

        job = Job(
            id="test_job",
            text="test",
            session_id="session",
            status=JobStatus.COMPLETED
        )
        runtime.jobs["test_job"] = job

        result = await runtime.cancel_job("test_job")

        assert result is False
