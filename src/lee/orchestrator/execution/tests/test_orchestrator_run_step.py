from types import SimpleNamespace

import pytest
from unittest.mock import AsyncMock, MagicMock

from lee.orchestrator.core.event_bus import EventType
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.models import Step, StepResult, WorkflowInstance, WorkflowLevel, WorkflowStatus
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


@pytest.mark.asyncio
async def test_run_step_marks_l2_workflow_failed_when_any_phase_failed(tmp_path):
    store = SQLiteStore(":memory:")
    await store.connect()
    try:
        orchestrator = Orchestrator(store=store, project_root=str(tmp_path))

        workflow = WorkflowInstance(
            id="wf_department_failed_phase_001",
            level=WorkflowLevel.DEPARTMENT,
            template_id="workflow.product.main",
            data={
                "kind": "l2_workflow_instance",
                "phases": [
                    {"id": "raw_to_src", "status": "completed", "depends_on": []},
                    {"id": "src_to_epic", "status": "failed", "depends_on": ["raw_to_src"], "error": "Child workflow failed"},
                    {"id": "epic_to_feat", "status": "pending", "depends_on": ["src_to_epic"]},
                ],
            },
            status=WorkflowStatus.RUNNING,
        )
        await store.create_workflow(workflow)

        result = await orchestrator.run_step(workflow.id)

        assert result.status == "failed"
        assert result.step_id == "src_to_epic"
        assert "Child workflow failed" in result.message

        persisted = await store.get_workflow(workflow.id)
        assert persisted.status == WorkflowStatus.FAILED
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_run_step_recovers_failed_l2_phase_after_child_subworkflow_completes(tmp_path, monkeypatch):
    store = SQLiteStore(":memory:")
    await store.connect()
    try:
        orchestrator = Orchestrator(store=store, project_root=str(tmp_path))

        parent = WorkflowInstance(
            id="wf_department_recover_001",
            level=WorkflowLevel.DEPARTMENT,
            template_id="workflow.product.main",
            data={
                "kind": "l2_workflow_instance",
                "params": {"raw_requirement": "ADR-016"},
                "phases": [
                    {
                        "id": "raw_to_src",
                        "status": "completed",
                        "depends_on": [],
                        "workflow": "workflow.product.task.raw_to_src",
                        "level": "task",
                    },
                    {
                        "id": "src_to_epic",
                        "status": "completed",
                        "depends_on": ["raw_to_src"],
                        "workflow": "workflow.product.task.src_to_epic",
                        "level": "task",
                    },
                    {
                        "id": "epic_to_feat",
                        "status": "failed",
                        "depends_on": ["src_to_epic"],
                        "workflow": "workflow.product.task.epic_to_feat",
                        "level": "task",
                        "error": "Child workflow failed",
                    },
                ],
                "subworkflow_children": {
                    "epic_to_feat": "wf_task_epic_to_feat_001",
                },
            },
            status=WorkflowStatus.FAILED,
        )
        child = WorkflowInstance(
            id="wf_task_epic_to_feat_001",
            level=WorkflowLevel.TASK,
            parent_id=parent.id,
            template_id="workflow.product.task.epic_to_feat",
            data={"completed_steps": ["feat_review", "feat_freeze"]},
            status=WorkflowStatus.COMPLETED,
        )
        await store.create_workflow(parent)
        await store.create_workflow(child)

        monkeypatch.setattr(
            orchestrator,
            "_backfill_subworkflow_output",
            AsyncMock(return_value={"child_workflow_id": child.id, "status": "completed"}),
        )

        result = await orchestrator.run_step(parent.id)

        assert result.status == "success"
        assert result.message == "All L2 phases completed"

        persisted = await store.get_workflow(parent.id)
        assert persisted.status == WorkflowStatus.COMPLETED
        recovered_phase = next(
            phase for phase in persisted.data["phases"] if phase["id"] == "epic_to_feat"
        )
        assert recovered_phase["status"] == "completed"
        assert recovered_phase["child_workflow_id"] == child.id
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_run_until_blocked_waits_for_running_task_execution(tmp_path, monkeypatch):
    store = SQLiteStore(":memory:")
    await store.connect()
    try:
        orchestrator = Orchestrator(store=store, project_root=str(tmp_path))

        workflow = WorkflowInstance(
            id="wf_department_wait_running_001",
            level=WorkflowLevel.DEPARTMENT,
            template_id="workflow.product.main",
            data={"kind": "l2_workflow_instance", "phases": []},
            status=WorkflowStatus.RUNNING,
        )
        await store.create_workflow(workflow)

        call_count = 0

        async def fake_run_step(workflow_id: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return StepResult(
                    status="no_ready_step",
                    step_id=None,
                    workflow_id=workflow_id,
                    message="No ready steps available",
                )
            await store.update_workflow_status(
                workflow_id,
                WorkflowStatus.FAILED,
                completed_at=None,
            )
            return StepResult(
                status="failed",
                step_id="feat_to_delivery_prep",
                workflow_id=workflow_id,
                message="L2 phase feat_to_delivery_prep failed: Child workflow failed",
            )

        monkeypatch.setattr(orchestrator, "run_step", fake_run_step)
        monkeypatch.setattr(
            orchestrator,
            "_has_running_task_executions",
            AsyncMock(side_effect=[True, False]),
        )
        sleep_mock = AsyncMock()
        monkeypatch.setattr(
            "lee.orchestrator.execution.orchestrator.asyncio.sleep",
            sleep_mock,
        )

        summary = await orchestrator.run_until_blocked(workflow.id, max_steps=3)

        assert summary.status == "failed"
        assert call_count == 2
        sleep_mock.assert_awaited_once()
    finally:
        await store.close()


@pytest.mark.asyncio
async def test_create_workflow_persists_project_root_into_instance_data(tmp_path):
    store = SQLiteStore(":memory:")
    await store.connect()
    try:
        template_manager = MagicMock()
        template_manager.get_template.return_value = SimpleNamespace(owner="product", departments=[])
        orchestrator = Orchestrator(
            store=store,
            template_manager=template_manager,
            project_root=str(tmp_path),
        )

        instance = await orchestrator.create_workflow(
            WorkflowLevel.TASK,
            "workflow.product.task.feat_to_release",
            data={"params": {}},
        )

        persisted = await store.get_workflow(instance.id)
        assert persisted is not None
        assert persisted.data["project_root"] == str(tmp_path.resolve())
    finally:
        await store.close()
