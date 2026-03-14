from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.models import StepResult, WorkflowInstance, WorkflowLevel, WorkflowStatus


@pytest.mark.asyncio
async def test_l2_subworkflow_propagates_executor_context(tmp_path: Path, monkeypatch) -> None:
    lee_dir = tmp_path / ".lee"
    lee_dir.mkdir()
    (lee_dir / "repos.yaml").write_text("version: '1.0'\nrepos: {}\n", encoding="utf-8")

    parent = WorkflowInstance(
        id="wf_parent_001",
        level=WorkflowLevel.DEPARTMENT,
        template_id="workflow.product.main",
        status=WorkflowStatus.RUNNING,
        data={
            "params": {"raw_requirement": "demo"},
            "executor_override": "qwen",
            "executor_selection_source": "file_config",
            "llm_profile": "qwen",
        },
    )

    store = SimpleNamespace()
    store.get_workflow = AsyncMock(return_value=parent)
    store.update_workflow_data = AsyncMock()

    orchestrator = Orchestrator(store=store, project_root=str(tmp_path))
    monkeypatch.setattr(orchestrator, "_update_l2_phase", AsyncMock())
    monkeypatch.setattr(orchestrator, "_backfill_subworkflow_output", AsyncMock(return_value={"ok": True}))

    captured = {}

    async def fake_spawn_workflow(**kwargs):
        captured["data"] = kwargs["data"]
        return WorkflowInstance(
            id="wf_child_001",
            level=WorkflowLevel.TASK,
            template_id=kwargs["template_id"],
            status=WorkflowStatus.COMPLETED,
            data=kwargs["data"],
        )

    monkeypatch.setattr(orchestrator, "spawn_workflow", fake_spawn_workflow)

    result = await orchestrator._run_l2_phase_subworkflow(
        workflow_id="wf_parent_001",
        phase_id="src_to_epic",
        phase_info={"workflow": "workflow.product.task.src_to_epic", "level": "task"},
    )

    assert isinstance(result, StepResult)
    assert result.status == "success"
    assert captured["data"]["executor_override"] == "qwen"
    assert captured["data"]["executor_selection_source"] == "file_config"
    assert captured["data"]["llm_profile"] == "qwen"


@pytest.mark.asyncio
async def test_agent_step_routes_to_llm_runner_when_qwen_chat_override(tmp_path: Path, monkeypatch) -> None:
    lee_dir = tmp_path / ".lee"
    lee_dir.mkdir()
    (lee_dir / "repos.yaml").write_text("version: '1.0'\nrepos: {}\n", encoding="utf-8")

    instance = WorkflowInstance(
        id="wf_task_qwen_chat_001",
        level=WorkflowLevel.TASK,
        template_id="workflow.product.task.raw_to_src",
        status=WorkflowStatus.RUNNING,
        data={
            "executor_override": "qwen_chat",
            "executor_selection_source": "cli_override",
            "run_id": "RUN-qwen-chat-001",
        },
    )

    step = SimpleNamespace(
        id="raw_input_intake",
        kind="agent",
        executor_type="claude_code",
        agent_id="agent.analysis.product_goal",
        config={},
        outputs=[],
    )

    store = SimpleNamespace()
    store.get_workflow = AsyncMock(return_value=instance)

    orchestrator = Orchestrator(store=store, project_root=str(tmp_path))
    monkeypatch.setattr(orchestrator, "get_ready_steps", AsyncMock(return_value=[step]))
    monkeypatch.setattr(orchestrator.state_machine, "start_step", AsyncMock())
    monkeypatch.setattr(orchestrator, "_run_agent_step", AsyncMock(return_value=StepResult(
        status="success",
        step_id="raw_input_intake",
        workflow_id=instance.id,
        message="ok",
    )))
    monkeypatch.setattr(orchestrator, "_run_claude_code_step", AsyncMock(return_value=StepResult(
        status="failed",
        step_id="raw_input_intake",
        workflow_id=instance.id,
        message="should not use claude path",
    )))
    monkeypatch.setattr(orchestrator, "_check_workflow_completion", AsyncMock())

    result = await orchestrator.run_step(instance.id)

    assert result.status == "success"
    orchestrator._run_agent_step.assert_awaited_once()
    orchestrator._run_claude_code_step.assert_not_awaited()


@pytest.mark.asyncio
async def test_agent_step_routes_to_llm_runner_for_non_coding_override(tmp_path: Path, monkeypatch) -> None:
    lee_dir = tmp_path / ".lee"
    lee_dir.mkdir()
    (lee_dir / "repos.yaml").write_text("version: '1.0'\nrepos: {}\n", encoding="utf-8")

    instance = WorkflowInstance(
        id="wf_task_dialogue_001",
        level=WorkflowLevel.TASK,
        template_id="workflow.product.task.raw_to_src",
        status=WorkflowStatus.RUNNING,
        data={
            "executor_override": "llm",
            "executor_selection_source": "cli_override",
            "run_id": "RUN-dialogue-001",
        },
    )

    step = SimpleNamespace(
        id="raw_input_intake",
        kind="agent",
        executor_type="claude_code",
        agent_id="agent.analysis.product_goal",
        config={},
        outputs=[],
    )

    store = SimpleNamespace()
    store.get_workflow = AsyncMock(return_value=instance)

    orchestrator = Orchestrator(store=store, project_root=str(tmp_path))
    monkeypatch.setattr(orchestrator, "get_ready_steps", AsyncMock(return_value=[step]))
    monkeypatch.setattr(orchestrator.state_machine, "start_step", AsyncMock())
    monkeypatch.setattr(orchestrator, "_run_agent_step", AsyncMock(return_value=StepResult(
        status="success",
        step_id="raw_input_intake",
        workflow_id=instance.id,
        message="ok",
    )))
    monkeypatch.setattr(orchestrator, "_run_claude_code_step", AsyncMock(return_value=StepResult(
        status="failed",
        step_id="raw_input_intake",
        workflow_id=instance.id,
        message="should not use claude path",
    )))
    monkeypatch.setattr(orchestrator, "_check_workflow_completion", AsyncMock())

    result = await orchestrator.run_step(instance.id)

    assert result.status == "success"
    orchestrator._run_agent_step.assert_awaited_once()
    orchestrator._run_claude_code_step.assert_not_awaited()
