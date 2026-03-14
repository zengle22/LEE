from pathlib import Path

import pytest
import yaml

from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.models import GateApproval, GateStatus, WorkflowInstance, WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore


@pytest.fixture
def store(tmp_path):
    return SQLiteStore(db_path=str(tmp_path / "test.db"))


@pytest.fixture
def orchestrator(store, tmp_path):
    return Orchestrator(store=store, project_root=str(tmp_path))


def test_extract_l3_handoff_refs_captures_evidence_inputs(orchestrator):
    refs = orchestrator._extract_l3_handoff_refs(
        {
            "step_outputs": {
                "integration_reporting": {
                    "integration_outputs": ["INT-001"],
                    "verification_results": ["VERIFY-INT-001"],
                },
                "bugfix_verification": {
                    "verification_report_ref": "VERIFY-001",
                    "closure_summary_ref": "SUMMARY-001",
                },
            }
        }
    )

    assert refs["integration_outputs"] == ["INT-001"]
    assert refs["verification_results"] == ["VERIFY-INT-001"]
    assert refs["verification_report_ref"] == "VERIFY-001"
    assert refs["closure_summary_ref"] == "SUMMARY-001"


def test_direct_phase_outputs_preserve_gate_inputs(orchestrator):
    workflow_data = {
        "params": {
            "evidence_pack_ref": "EVI-001",
            "smoke_gate_inputs": {"smoke_result": {"flows_failed": 0}},
            "closure_summary_ref": "SUMMARY-001",
            "merge_or_reject_input": "MERGE-INPUT-001",
        }
    }

    smoke_output = orchestrator._build_direct_phase_output(workflow_data, "smoke_gate")
    merge_output = orchestrator._build_direct_phase_output(workflow_data, "merge_or_reject")

    assert smoke_output["smoke_gate_inputs"] == {"smoke_result": {"flows_failed": 0}}
    assert merge_output["merge_or_reject_input"] == "MERGE-INPUT-001"
    assert merge_output["merge_decision_ref"] == "MERGE-INPUT-001"


@pytest.mark.asyncio
async def test_execute_complexity_s_creates_l2_phase_gate(orchestrator, store):
    await store.connect()
    instance = WorkflowInstance(
        id="l2-gated",
        level=WorkflowLevel.DEPARTMENT,
        template_id="template.dev.feature_delivery_l2",
        status=WorkflowStatus.PENDING,
        data={
            "kind": "l2_workflow_instance",
            "params": {
                "evidence_pack_ref": "EVI-001",
                "smoke_gate_inputs": {"smoke_result": {"flows_failed": 0}},
            },
            "phases": [
                {"id": "evidence_pack", "status": "completed"},
                {"id": "smoke_gate", "status": "pending", "complexity": "S", "gate_id": "gate.dev.smoke_gate"},
            ],
        },
    )
    await store.create_workflow(instance)

    result = await orchestrator._execute_complexity_s("l2-gated", "smoke_gate")
    gate = await store.get_gate_approval("l2-gated", "gate.dev.smoke_gate")
    updated = await store.get_workflow("l2-gated")

    assert result.status == "blocked"
    assert result.blocked_reason == "human_gate"
    assert gate is not None
    assert gate.status == GateStatus.PENDING
    assert updated.status == WorkflowStatus.PAUSED
    assert updated.data["phase_gate_outputs"]["smoke_gate"]["evidence_pack_ref"] == "EVI-001"

    await store.close()


@pytest.mark.asyncio
async def test_approve_gate_completes_l2_phase_gate(orchestrator, store):
    await store.connect()
    instance = WorkflowInstance(
        id="l2-merge",
        level=WorkflowLevel.DEPARTMENT,
        template_id="template.dev.bugfix_delivery_l2",
        status=WorkflowStatus.PAUSED,
        data={
            "kind": "l2_workflow_instance",
            "params": {
                "evidence_pack_ref": "EVI-002",
                "closure_summary_ref": "SUMMARY-002",
                "merge_or_reject_input": "MERGE-INPUT-002",
            },
            "phase_gate_outputs": {
                "merge_or_reject": {
                    "phase_id": "merge_or_reject",
                    "merge_or_reject_input": "MERGE-INPUT-002",
                }
            },
            "phases": [
                {"id": "evidence_pack", "status": "completed"},
                {"id": "merge_or_reject", "status": "blocked", "complexity": "S", "gate_id": "gate.dev.merge_approval"},
            ],
        },
    )
    await store.create_workflow(instance)
    await store.create_gate_approval(
        GateApproval(
            workflow_id="l2-merge",
            gate_id="gate.dev.merge_approval",
            step_id="merge_or_reject",
        )
    )

    result = await orchestrator.approve_gate("l2-merge", "gate.dev.merge_approval", "reviewer", "approved")
    updated = await store.get_workflow("l2-merge")

    assert result.status == "success"
    assert result.output["merge_decision_ref"] == "MERGE-INPUT-002"
    assert updated.status == WorkflowStatus.COMPLETED
    assert updated.data["params"]["merge_decision_ref"] == "MERGE-INPUT-002"

    await store.close()


def test_bugfix_templates_align_merge_gate_and_evidence_inputs():
    l2_template = yaml.safe_load(
        Path("spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml").read_text(
            encoding="utf-8"
        )
    )
    evidence_template = yaml.safe_load(
        Path("spec-global/departments/dev/workflows/templates/bugfix-evidence-pack-l3-template.yaml").read_text(
            encoding="utf-8"
        )
    )

    merge_phase = next(phase for phase in l2_template["phases"] if phase["id"] == "merge_or_reject")
    review_step = next(step for step in evidence_template["steps"] if step["id"] == "review_evidence_pack")

    assert merge_phase["gate_id"] == "gate.dev.merge_approval"
    assert "verification_report_ref" in evidence_template["instance_schema"]["required_fields"]
    assert "merge_or_reject_input" in review_step["outputs"]
