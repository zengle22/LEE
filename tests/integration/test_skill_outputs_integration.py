"""
Integration test for skill output reference resolution.

This test verifies the end-to-end flow of:
1. Step completes and stores outputs
2. Next step resolves $outputs references from previous step
"""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

import pytest
import yaml

import sys
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from lee.orchestrator.execution.runners.shell_runner import SkillRunner
from lee.orchestrator.execution.state_machine import WorkflowStateMachine
from lee.orchestrator.storage.models import (
    Step,
    OutputSpec,
    StepResult,
    TaskExecutionStatus,
)


class MockStore:
    """Mock store for testing."""

    def __init__(self):
        self.workflows = {}
        self.task_executions = {}

    async def get_workflow(self, workflow_id):
        return self.workflows.get(workflow_id)

    async def update_workflow_data(self, workflow_id, data):
        if workflow_id in self.workflows:
            self.workflows[workflow_id].data = data

    async def update_workflow_status(self, workflow_id, status, clear_current_step=False):
        if workflow_id in self.workflows:
            self.workflows[workflow_id].status = status
            if clear_current_step:
                self.workflows[workflow_id].current_step = None

    async def create_task_execution(self, execution):
        self.task_executions[execution.id] = execution

    async def update_task_execution(self, execution_id, status=None, output_data=None, error_message=None, completed_at=None):
        if execution_id in self.task_executions:
            exec = self.task_executions[execution_id]
            if status:
                exec.status = status
            if output_data:
                exec.output_data = output_data
            if error_message:
                exec.error_message = error_message
            if completed_at:
                exec.completed_at = completed_at


class MockWorkflowInstance:
    """Mock workflow instance."""

    def __init__(self, workflow_id, data=None):
        self.id = workflow_id
        self.status = "running"
        self.current_step = None
        self.data = data or {}


class TestSkillOutputsIntegration:
    """Integration tests for skill output reference resolution."""

    @pytest.mark.asyncio
    async def test_complete_step_stores_outputs(self, tmp_path):
        """Test that complete_step stores step outputs correctly."""
        # Setup
        store = MockStore()
        workflow_id = "test-workflow-001"
        store.workflows[workflow_id] = MockWorkflowInstance(workflow_id)

        sm = WorkflowStateMachine(store)

        # Create step with outputs
        step_outputs = [
            OutputSpec(type="file", path=".workflow/output.yaml", format="yaml"),
            OutputSpec(type="file", path=".workflow/output.json", format="json"),
        ]

        # Complete the step
        result = await sm.complete_step(
            workflow_id,
            "s1_analyze",
            {"status": "success"},
            step_outputs=step_outputs,
        )

        assert result.status == "success"

        # Verify outputs were stored
        workflow = store.workflows[workflow_id]
        assert "step_outputs" in workflow.data
        assert "s1_analyze" in workflow.data["step_outputs"]
        assert ".workflow/output.yaml" in workflow.data["step_outputs"]["s1_analyze"]["paths"]
        assert ".workflow/output.json" in workflow.data["step_outputs"]["s1_analyze"]["paths"]

    @pytest.mark.asyncio
    async def test_resolve_outputs_from_stored_step(self, tmp_path):
        """Test resolving outputs from a previously completed step."""
        # Setup project with output file
        project_root = tmp_path / "project"
        project_root.mkdir()
        workflow_dir = project_root / ".workflow"
        workflow_dir.mkdir()

        output_data = {
            "gitignore_recommendations": {
                "critical": [{"pattern": ".secret"}],
                "high_priority": [{"pattern": ".lee/"}],
            }
        }
        output_file = workflow_dir / "file-analysis.yaml"
        output_file.write_text(yaml.dump(output_data), encoding="utf-8")

        # Setup workflow data (simulating completed step)
        workflow_data = {
            "completed_steps": ["s1_1_analyze_files"],
            "step_outputs": {
                "s1_1_analyze_files": {
                    "paths": [".workflow/file-analysis.yaml"]
                }
            }
        }

        # Resolve the reference
        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_1_analyze_files.gitignore_recommendations",
            str(project_root),
            workflow_data,
        )

        assert result is not None
        assert "critical" in result
        assert result["critical"][0]["pattern"] == ".secret"

    @pytest.mark.asyncio
    async def test_full_flow_step_to_step_reference(self, tmp_path):
        """Test the full flow from step completion to reference resolution."""
        # Setup
        project_root = tmp_path / "project"
        project_root.mkdir()
        workflow_dir = project_root / ".workflow"
        workflow_dir.mkdir()

        store = MockStore()
        workflow_id = "test-workflow-002"
        store.workflows[workflow_id] = MockWorkflowInstance(workflow_id)

        sm = WorkflowStateMachine(store)

        # Step 1: Complete first step with output
        step1_outputs = [
            OutputSpec(type="file", path=".workflow/step1.yaml", format="yaml"),
        ]

        output_content = {"items": ["pattern1", "pattern2", "pattern3"]}
        (workflow_dir / "step1.yaml").write_text(yaml.dump(output_content), encoding="utf-8")

        await sm.complete_step(
            workflow_id,
            "s1_analyze",
            {"status": "success"},
            step_outputs=step1_outputs,
        )

        # Step 2: Resolve reference from Step 1
        workflow = store.workflows[workflow_id]
        result = SkillRunner._resolve_outputs_ref(
            "$outputs.s1_analyze.items",
            str(project_root),
            workflow.data,
        )

        assert result == ["pattern1", "pattern2", "pattern3"]

    @pytest.mark.asyncio
    async def test_retry_preserves_outputs(self, tmp_path):
        """Test that retrying a step preserves existing outputs."""
        store = MockStore()
        workflow_id = "test-workflow-003"
        store.workflows[workflow_id] = MockWorkflowInstance(workflow_id)

        sm = WorkflowStateMachine(store)

        # First completion
        step_outputs = [
            OutputSpec(type="file", path=".workflow/output1.yaml", format="yaml"),
        ]
        await sm.complete_step(workflow_id, "s1", {}, step_outputs=step_outputs)

        # Second completion (retry scenario - different output path)
        step_outputs2 = [
            OutputSpec(type="file", path=".workflow/output2.yaml", format="yaml"),
        ]
        await sm.complete_step(workflow_id, "s1", {}, step_outputs=step_outputs2)

        # Verify both paths are preserved
        workflow = store.workflows[workflow_id]
        paths = workflow.data["step_outputs"]["s1"]["paths"]
        assert ".workflow/output1.yaml" in paths
        assert ".workflow/output2.yaml" in paths


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
