from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.runners.auto_check_gate_runner import AutoCheckGateRunner
from lee.orchestrator.execution.runners.gate_runner import HumanGateRunner
from lee.orchestrator.storage.models import GateApproval, GateStatus


def _pending_gate(*, workflow_id: str, gate_id: str, step_id: str) -> GateApproval:
    return GateApproval(
        workflow_id=workflow_id,
        gate_id=gate_id,
        step_id=step_id,
        status=GateStatus.PENDING,
    )


@pytest.mark.asyncio
async def test_human_gate_runner_reuses_existing_pending_gate_for_same_step():
    runner = HumanGateRunner()
    ctx = SimpleNamespace(
        store=SimpleNamespace(
            update_workflow_status=AsyncMock(),
            get_pending_gates=AsyncMock(
                return_value=[_pending_gate(workflow_id="wf-1", gate_id="gate_existing", step_id="epic_freeze")]
            ),
            get_gate_approval=AsyncMock(),
            create_gate_approval=AsyncMock(),
        ),
        event_log=MagicMock(),
    )
    step = SimpleNamespace(id="epic_freeze", gate_id="gate_wf-1_epic_freeze", config={"gate": {}})

    result = await runner.execute("wf-1", step, ctx)

    assert result.status == "blocked"
    assert "gate_existing" in result.message
    ctx.store.create_gate_approval.assert_not_called()
    ctx.event_log.log_gate_triggered.assert_not_called()


@pytest.mark.asyncio
async def test_auto_check_gate_runner_reuses_existing_pending_gate_for_same_step():
    runner = AutoCheckGateRunner()
    ctx = SimpleNamespace(
        store=SimpleNamespace(
            update_workflow_status=AsyncMock(),
            get_pending_gates=AsyncMock(
                return_value=[_pending_gate(workflow_id="wf-2", gate_id="gate_existing", step_id="feat_freeze")]
            ),
            get_gate_approval=AsyncMock(),
            create_gate_approval=AsyncMock(),
        ),
        event_log=MagicMock(),
    )
    step = SimpleNamespace(id="feat_freeze", gate_id="gate_wf-2_feat_freeze")

    result = await runner._block_for_human_gate(
        workflow_id="wf-2",
        step=step,
        ctx=ctx,
        gate_config={},
        output_data={"decision": "revise"},
        error_message="Review requires revision",
    )

    assert result.status == "blocked"
    assert "gate_existing" in result.message
    ctx.store.create_gate_approval.assert_not_called()
    ctx.event_log.log_gate_triggered.assert_not_called()
