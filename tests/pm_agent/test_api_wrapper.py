"""
Unit Tests for PM Agent Orchestrator API Wrapper

Tests for:
- Action routing to orchestrator API functions
- New contract-aligned actions (list_gates/revise_gate/flag_gate/pause/resume)
- Error handling for missing required parameters
"""

import pytest
from unittest.mock import AsyncMock

import lee.orchestrator.api as orchestrator_api_module
import lee.orchestrator.execution.pm_agent.api_wrapper as api_wrapper_module
from lee.orchestrator.execution.pm_agent.api_wrapper import OrchestratorAPIWrapper
from lee.orchestrator.execution.pm_agent.models import (
    Decision,
    Intent,
    IntentType,
    WorkflowParams,
    ExecutionContext,
)


def _decision(action: str, params: WorkflowParams) -> Decision:
    return Decision(
        intent=Intent(type=IntentType.QUERY_STATUS, confidence=0.9, reasoning="test"),
        params=params,
        action=action,
        allowed=True,
    )


@pytest.fixture
def wrapper(tmp_path):
    return OrchestratorAPIWrapper(project_dir=str(tmp_path))


@pytest.mark.asyncio
async def test_list_gates_action_calls_api(wrapper, monkeypatch):
    mock_list = AsyncMock(return_value={"total": 1, "gates": [{"gate_id": "gate_a"}]})
    monkeypatch.setattr(api_wrapper_module, "api_list_gates", mock_list)

    decision = _decision(
        "list_gates",
        WorkflowParams(workflow_ref="wf_task_1", params={"status": "pending"}),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.action == "list_gates"
    assert resp.data["total"] == 1
    mock_list.assert_awaited_once_with(str(wrapper.project_dir), "wf_task_1", "pending")


@pytest.mark.asyncio
async def test_pause_resume_workflow_actions(wrapper, monkeypatch):
    mock_pause = AsyncMock(return_value={"workflow_id": "wf_task_1", "message": "paused"})
    mock_resume = AsyncMock(return_value={"workflow_id": "wf_task_1", "message": "resumed"})
    monkeypatch.setattr(api_wrapper_module, "api_pause_workflow", mock_pause)
    monkeypatch.setattr(api_wrapper_module, "api_resume_workflow", mock_resume)

    # Missing workflow should return API-level error response
    pause_error = await wrapper.execute(_decision("pause_workflow", WorkflowParams()))
    assert pause_error.status == "error"
    assert "workflow_id is required" in (pause_error.error or "")

    # Use context fallback workflow_id
    ctx = ExecutionContext(project_dir=str(wrapper.project_dir), workflow_id="wf_task_1")
    pause_ok = await wrapper.execute(_decision("pause_workflow", WorkflowParams()), ctx)
    resume_ok = await wrapper.execute(_decision("resume_workflow", WorkflowParams()), ctx)
    assert pause_ok.status == "success"
    assert resume_ok.status == "success"
    mock_pause.assert_awaited_once_with(str(wrapper.project_dir), "wf_task_1")
    mock_resume.assert_awaited_once_with(str(wrapper.project_dir), "wf_task_1")


@pytest.mark.asyncio
async def test_revise_gate_action_calls_api(wrapper, monkeypatch):
    mock_revise = AsyncMock(return_value={"status": "success", "workflow_id": "wf_task_1"})
    monkeypatch.setattr(api_wrapper_module, "api_revise_gate", mock_revise)

    decision = _decision(
        "revise_gate",
        WorkflowParams(
            workflow_ref="wf_task_1",
            gate_id="gate_review",
            params={
                "reviewer": "alice",
                "reason": "needs update",
                "target_step": "step_fix",
                "structured_feedback": {"severity": "high"},
            },
            approval_comment="needs update",
        ),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.action == "revise_gate"
    mock_revise.assert_awaited_once_with(
        str(wrapper.project_dir),
        "wf_task_1",
        "gate_review",
        "alice",
        "needs update",
        "step_fix",
        {"severity": "high"},
    )


@pytest.mark.asyncio
async def test_flag_gate_uses_comment_as_default_issue(wrapper, monkeypatch):
    mock_flag = AsyncMock(return_value={"status": "flagged", "workflow_id": "wf_task_1"})
    monkeypatch.setattr(api_wrapper_module, "api_flag_gate", mock_flag)

    decision = _decision(
        "flag_gate",
        WorkflowParams(
            workflow_ref="wf_task_1",
            gate_id="gate_review",
            params={},
            approval_comment="missing evidence",
        ),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.action == "flag_gate"
    mock_flag.assert_awaited_once_with(
        str(wrapper.project_dir),
        "wf_task_1",
        "gate_review",
        "pm_agent",
        ["missing evidence"],
        True,
    )


@pytest.mark.asyncio
async def test_reject_gate_passthrough_action_and_target_step(wrapper, monkeypatch):
    mock_reject = AsyncMock(
        return_value={
            "status": "running",
            "workflow_id": "wf_task_1",
            "message": "rejected and rolled back",
            "action": "rollback",
            "target_step": "step_fix",
            "new_workflow_id": "wf_task_retry_1",
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_reject_gate", mock_reject)

    decision = _decision(
        "reject_gate",
        WorkflowParams(
            workflow_ref="wf_task_1",
            gate_id="gate_review",
            approval_comment="please revise",
            params={"action": "rollback", "target_step": "step_fix"},
        ),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.action == "reject_gate"
    assert resp.data["decision"] == "rejected"
    assert resp.data["action"] == "rollback"
    assert resp.data["target_step"] == "step_fix"
    assert resp.data["new_workflow_id"] == "wf_task_retry_1"
    mock_reject.assert_awaited_once_with(
        str(wrapper.project_dir),
        "wf_task_1",
        "gate_review",
        "pm_agent",
        "please revise",
        action="rollback",
        target_step="step_fix",
    )


@pytest.mark.asyncio
async def test_run_workflow_includes_template_resolution(wrapper, monkeypatch):
    mock_create = AsyncMock(return_value={"workflow_id": "wf_task_9"})
    mock_run = AsyncMock(return_value={"status": "running", "completed_steps": 1, "total_steps": 3})
    monkeypatch.setattr(orchestrator_api_module, "api_create_workflow", mock_create)
    monkeypatch.setattr(orchestrator_api_module, "api_run_until_blocked", mock_run)

    decision = _decision(
        "run_workflow",
        WorkflowParams(
            workflow_ref="workflow.office.workspace_cleanup",
            params={
                "template_id": "workflow.office.workspace_cleanup",
                "template_input": "workspace_cleanup",
                "template_resolved": "workflow.office.workspace_cleanup",
            },
        ),
    )

    resp = await wrapper.execute(decision)
    assert resp.status == "success"
    assert resp.action == "run_workflow"
    assert resp.data["template_id"] == "workflow.office.workspace_cleanup"
    assert resp.data["template_input"] == "workspace_cleanup"
    assert resp.data["template_resolved"] == "workflow.office.workspace_cleanup"


@pytest.mark.asyncio
async def test_approve_gate_resolves_workflow_id_from_gate_id(wrapper, monkeypatch):
    mock_list = AsyncMock(
        side_effect=[
            {
                "total": 1,
                "gates": [
                    {"gate_id": "gate_s5_2_review_commits", "workflow_id": "wf_task_42", "status": "pending"}
                ],
            }
        ]
    )
    mock_approve = AsyncMock(
        return_value={"status": "success", "step_id": "step_review", "workflow_id": "wf_task_42", "message": "ok"}
    )
    mock_run_until = AsyncMock(
        return_value={
            "workflow_id": "wf_task_42",
            "total_steps": 2,
            "completed_steps": 1,
            "blocked_at": None,
            "status": "running",
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_list_gates", mock_list)
    monkeypatch.setattr(api_wrapper_module, "api_approve_gate", mock_approve)
    monkeypatch.setattr(api_wrapper_module, "api_run_until_blocked", mock_run_until)

    decision = _decision(
        "approve_gate",
        WorkflowParams(workflow_ref=None, gate_id="gate_s5_2_review_commits", approval_comment="LGTM"),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.action == "approve_gate"
    assert resp.data["gate_id"] == "gate_s5_2_review_commits"
    assert resp.data["workflow_id"] == "wf_task_42"
    assert resp.data["auto_continued"] is True
    assert resp.data["run_result"]["status"] == "running"
    mock_list.assert_awaited_once_with(str(wrapper.project_dir), None, "pending")
    mock_approve.assert_awaited_once_with(
        str(wrapper.project_dir),
        "wf_task_42",
        "gate_s5_2_review_commits",
        "pm_agent",
        "LGTM",
    )
    mock_run_until.assert_awaited_once_with(
        str(wrapper.project_dir),
        "wf_task_42",
        max_steps=10,
    )


@pytest.mark.asyncio
async def test_next_step_treats_success_status_as_success(wrapper, monkeypatch):
    mock_next = AsyncMock(
        return_value={
            "status": "success",
            "step_id": "step_2",
            "workflow_id": "wf_task_1",
            "message": "step done",
            "output": {},
            "next_steps": [],
            "blocked_reason": None,
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_next_step", mock_next)

    decision = _decision("next_step", WorkflowParams(workflow_ref="wf_task_1"))
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.action == "next_step"


@pytest.mark.asyncio
async def test_next_step_uses_message_as_error_when_no_blocked_reason(wrapper, monkeypatch):
    mock_next = AsyncMock(
        return_value={
            "status": "no_ready_step",
            "step_id": None,
            "workflow_id": "wf_task_1",
            "message": "No ready steps available (workflow_status=failed)",
            "output": {},
            "next_steps": [],
            "blocked_reason": None,
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_next_step", mock_next)

    decision = _decision("next_step", WorkflowParams(workflow_ref="wf_task_1"))
    resp = await wrapper.execute(decision)

    assert resp.status == "failed"
    assert resp.error == "No ready steps available (workflow_status=failed)"
    assert resp.data["message"] == "No ready steps available (workflow_status=failed)"


@pytest.mark.asyncio
async def test_approve_gate_resolve_workflow_ambiguous(wrapper, monkeypatch):
    mock_list = AsyncMock(
        return_value={
            "total": 2,
            "gates": [
                {"gate_id": "gate_s5_2_review_commits", "workflow_id": "wf_task_1", "status": "pending"},
                {"gate_id": "gate_s5_2_review_commits", "workflow_id": "wf_task_2", "status": "pending"},
            ],
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_list_gates", mock_list)

    decision = _decision(
        "approve_gate",
        WorkflowParams(workflow_ref=None, gate_id="gate_s5_2_review_commits"),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "error"
    assert "matches multiple workflows" in (resp.error or "")


@pytest.mark.asyncio
async def test_approve_gate_can_disable_auto_continue(wrapper, monkeypatch):
    mock_approve = AsyncMock(
        return_value={"status": "success", "step_id": "step_review", "workflow_id": "wf_task_1", "message": "ok"}
    )
    mock_run_until = AsyncMock()
    monkeypatch.setattr(api_wrapper_module, "api_approve_gate", mock_approve)
    monkeypatch.setattr(api_wrapper_module, "api_run_until_blocked", mock_run_until)

    decision = _decision(
        "approve_gate",
        WorkflowParams(
            workflow_ref="wf_task_1",
            gate_id="gate_review",
            params={"auto_continue": False},
        ),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.data["auto_continued"] is False
    assert resp.data["run_result"] is None
    mock_run_until.assert_not_called()


@pytest.mark.asyncio
async def test_approve_gate_tolerates_nonstandard_success_status(wrapper, monkeypatch):
    # Simulate older/variant API returning nonstandard status, but approval message is explicit.
    mock_approve = AsyncMock(
        return_value={
            "status": "ok",
            "step_id": "step_review",
            "workflow_id": "wf_task_1",
            "message": "Gate gate_review approved by pm_agent",
        }
    )
    mock_run_until = AsyncMock(
        return_value={
            "workflow_id": "wf_task_1",
            "total_steps": 1,
            "completed_steps": 0,
            "blocked_at": None,
            "status": "running",
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_approve_gate", mock_approve)
    monkeypatch.setattr(api_wrapper_module, "api_run_until_blocked", mock_run_until)

    decision = _decision(
        "approve_gate",
        WorkflowParams(workflow_ref="wf_task_1", gate_id="gate_review"),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.data["decision"] == "approved"
    assert resp.data["run_result"]["status"] == "running"
    assert resp.data["run_error"] is None


@pytest.mark.asyncio
async def test_approve_gate_keeps_success_when_auto_continue_raises(wrapper, monkeypatch):
    mock_approve = AsyncMock(
        return_value={
            "status": "success",
            "step_id": "step_review",
            "workflow_id": "wf_task_1",
            "message": "ok",
        }
    )
    mock_run_until = AsyncMock(side_effect=RuntimeError("run loop timeout"))
    monkeypatch.setattr(api_wrapper_module, "api_approve_gate", mock_approve)
    monkeypatch.setattr(api_wrapper_module, "api_run_until_blocked", mock_run_until)

    decision = _decision(
        "approve_gate",
        WorkflowParams(workflow_ref="wf_task_1", gate_id="gate_review"),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.data["decision"] == "approved"
    assert resp.data["run_result"] is None
    assert "run loop timeout" in (resp.data.get("run_error") or "")


@pytest.mark.asyncio
async def test_approve_gate_fallbacks_to_persisted_gate_status(wrapper, monkeypatch):
    # Simulate approval API returning nonstandard payload with no explicit success cues.
    mock_approve = AsyncMock(
        return_value={
            "status": "unknown",
            "workflow_id": "wf_task_1",
            "message": "done",
        }
    )
    mock_list = AsyncMock(
        return_value={
            "total": 1,
            "gates": [
                {"gate_id": "gate_review", "workflow_id": "wf_task_1", "status": "approved"},
            ],
        }
    )
    mock_run_until = AsyncMock(
        return_value={
            "workflow_id": "wf_task_1",
            "status": "running",
            "completed_steps": 1,
            "total_steps": 2,
        }
    )
    monkeypatch.setattr(api_wrapper_module, "api_approve_gate", mock_approve)
    monkeypatch.setattr(api_wrapper_module, "api_list_gates", mock_list)
    monkeypatch.setattr(api_wrapper_module, "api_run_until_blocked", mock_run_until)

    decision = _decision(
        "approve_gate",
        WorkflowParams(workflow_ref="wf_task_1", gate_id="gate_review"),
    )
    resp = await wrapper.execute(decision)

    assert resp.status == "success"
    assert resp.data["decision"] == "approved"
    assert resp.data["run_result"]["status"] == "running"
