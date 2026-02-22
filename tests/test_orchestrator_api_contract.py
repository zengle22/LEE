import asyncio
from unittest.mock import AsyncMock

import pytest

import lee.orchestrator.api as api_module
from lee.orchestrator.api.contract import (
    OrchestratorAction,
    OrchestratorAPIRequest,
    ResponseStatus,
)


def test_request_normalizes_legacy_action() -> None:
    req = OrchestratorAPIRequest(action="create")
    assert req.normalized_action() == OrchestratorAction.CREATE_WORKFLOW.value

    req = OrchestratorAPIRequest(action="pause")
    assert req.normalized_action() == OrchestratorAction.PAUSE_WORKFLOW.value


@pytest.mark.asyncio
async def test_dispatch_supports_legacy_create_alias(monkeypatch) -> None:
    mock_create = AsyncMock(return_value={"workflow_id": "wf_task_123"})
    monkeypatch.setattr(api_module, "api_create_workflow", mock_create)

    req = OrchestratorAPIRequest(
        action="create",
        project_dir=".",
        payload={"level": "task", "template_id": "workflow.demo"},
    )
    resp = await api_module.orchestrator_api_dispatch(req)

    assert resp.status == ResponseStatus.SUCCESS.value
    assert resp.action == OrchestratorAction.CREATE_WORKFLOW.value
    assert resp.data["workflow_id"] == "wf_task_123"
    mock_create.assert_awaited_once()


@pytest.mark.asyncio
async def test_dispatch_supports_list_gates(monkeypatch) -> None:
    mock_list = AsyncMock(
        return_value={
            "workflow_id": None,
            "status_filter": "pending",
            "total": 1,
            "gates": [{"gate_id": "gate_a"}],
        }
    )
    monkeypatch.setattr(api_module, "api_list_gates", mock_list)

    req = OrchestratorAPIRequest(
        action="list_gates",
        project_dir=".",
        payload={"status": "pending"},
    )
    resp = await api_module.orchestrator_api_dispatch(req)

    assert resp.status == ResponseStatus.SUCCESS.value
    assert resp.action == OrchestratorAction.LIST_GATES.value
    assert resp.data["total"] == 1
    mock_list.assert_awaited_once_with(api_module._normalize_project_dir("."), None, "pending")


@pytest.mark.asyncio
async def test_dispatch_supports_revise_and_flag_gate(monkeypatch) -> None:
    mock_revise = AsyncMock(return_value={"status": "success", "workflow_id": "wf_task_1"})
    mock_flag = AsyncMock(return_value={"status": "flagged", "workflow_id": "wf_task_1"})
    monkeypatch.setattr(api_module, "api_revise_gate", mock_revise)
    monkeypatch.setattr(api_module, "api_flag_gate", mock_flag)

    revise_resp = await api_module.orchestrator_api_dispatch(
        OrchestratorAPIRequest(
            action="revise_gate",
            workflow_id="wf_task_1",
            payload={"gate_id": "gate_1", "reviewer": "u1", "reason": "fix"},
        )
    )
    assert revise_resp.status == ResponseStatus.SUCCESS.value
    assert revise_resp.action == OrchestratorAction.REVISE_GATE.value

    flag_resp = await api_module.orchestrator_api_dispatch(
        OrchestratorAPIRequest(
            action="flag_gate",
            workflow_id="wf_task_1",
            payload={"gate_id": "gate_1", "reporter": "u1", "issues": ["issue"]},
        )
    )
    assert flag_resp.status == ResponseStatus.SUCCESS.value
    assert flag_resp.action == OrchestratorAction.FLAG_GATE.value


@pytest.mark.asyncio
async def test_dispatch_unknown_action_returns_error() -> None:
    resp = await api_module.orchestrator_api_dispatch(
        OrchestratorAPIRequest(action="unknown_action")
    )
    assert resp.status == ResponseStatus.ERROR.value
    assert "Unknown action" in (resp.error or "")


def test_pm_workflow_handler_list_ready_steps_legacy_shape(monkeypatch) -> None:
    async def fake_dispatch(_req):
        return api_module.OrchestratorAPIResponse(
            status=ResponseStatus.SUCCESS.value,
            action=OrchestratorAction.LIST_READY_STEPS.value,
            data=[{"id": "step_1"}],
            meta={},
        )

    monkeypatch.setattr(api_module, "orchestrator_api_dispatch", fake_dispatch)

    result = asyncio.run(
        api_module.pm_workflow_handler(
            action="list_ready_steps",
            workflow_id="wf_task_1",
        )
    )
    assert result == {"ready_steps": [{"id": "step_1"}]}
