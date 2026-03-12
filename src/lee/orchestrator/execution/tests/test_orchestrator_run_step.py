from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock

from lee.orchestrator.core.event_bus import EventType
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.models import Step, StepResult, WorkflowInstance, WorkflowLevel
from lee.orchestrator.storage.sqlite_store import SQLiteStore


class _FakeExecutor:
    async def execute(self, input_data):
        return {"status": "ok", "echo": input_data}


@pytest.mark.asyncio
async def test_run_step_without_repo_scope_uses_instance_run_id_for_completed_event(
    tmp_path,
    monkeypatch,
):
    store = SQLiteStore(":memory:")
    await store.connect()
    try:
        orchestrator = Orchestrator(store=store, project_root=str(tmp_path))

        workflow = WorkflowInstance(
            id="wf_task_phase_wrapper_001",
            level=WorkflowLevel.TASK,
            template_id="workflow.test.phase_wrapper",
            data={
                "run_id": "RUN-phase-wrapper-001",
                "params": {},
                "completed_steps": [],
            },
        )
        await store.create_workflow(workflow)

        step = Step(
            id="src_to_epic",
            kind="phase",
            executor_type="fake_executor",
            input={"artifact": "adr007"},
        )

        published_events = []

        monkeypatch.setattr(
            orchestrator,
            "get_ready_steps",
            AsyncMock(return_value=[step]),
        )
        monkeypatch.setattr(
            orchestrator,
            "_check_workflow_completion",
            AsyncMock(return_value=None),
        )
        monkeypatch.setattr(
            orchestrator.executor_factory,
            "create",
            lambda executor_type, **kwargs: _FakeExecutor(),
        )
        monkeypatch.setattr(
            "lee.orchestrator.execution.orchestrator.get_event_bus",
            lambda: SimpleNamespace(publish=lambda event: published_events.append(event)),
        )

        result = await orchestrator.run_step(workflow.id)

        assert result.status == "success"
        assert result.step_id == "src_to_epic"

        completed_events = [
            event for event in published_events
            if getattr(event, "type", None) == EventType.STEP_COMPLETED
        ]
        assert completed_events, "expected a STEP_COMPLETED event"
        assert completed_events[-1].payload["run_id"] == "RUN-phase-wrapper-001"

        persisted = await store.get_workflow(workflow.id)
        assert "src_to_epic" in persisted.data.get("completed_steps", [])
    finally:
        await store.close()
