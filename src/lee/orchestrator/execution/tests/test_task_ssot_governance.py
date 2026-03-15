import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.ssot_contract import SSOTContractMaterializer
from lee.orchestrator.execution.artifacts.ssot_service import SSOTValidator
from lee.orchestrator.execution.artifacts.types import ArtifactStatus, SSOTType
from lee.orchestrator.execution.gate_operations import GateOperationsMixin
from lee.orchestrator.storage.models import GateApproval, GateStatus, WorkflowStatus


class _GateHarness(GateOperationsMixin):
    def __init__(self):
        self.project_root = None
        self.state_machine = SimpleNamespace(
            _resolve_step_inputs_for_freeze=lambda step_id, instance: ["feat_freeze_ref"]
        )
        self.store = SimpleNamespace(
            get_workflow=AsyncMock(),
            update_workflow_data=AsyncMock(),
        )
        self.run_until_blocked = AsyncMock()


def _create_src_scoped_feat(manager: ArtifactManager, suffix: str = "001") -> tuple[str, str]:
    src = manager.create_ssot(
        ssot_type=SSOTType.SRC,
        title=f"Task Runtime Source {suffix}",
        content="# Source\n",
        run_id=f"run-src-{suffix}",
    )
    epic = manager.create_ssot(
        ssot_type=SSOTType.EPIC,
        title=f"Task Runtime Epic {suffix}",
        content="# Epic\n",
        run_id=f"run-epic-{suffix}",
        parent_id=src.id,
        source_refs=[src.id],
    )
    feat = manager.create_ssot(
        ssot_type=SSOTType.FEAT,
        title=f"Task Runtime Feat {suffix}",
        content="# Feature\n",
        run_id=f"run-feat-{suffix}",
        parent_id=epic.id,
        source_refs=[f"{src.id}#scope", epic.id],
    )
    return src.id, feat.id


def test_task_ssot_materializes_under_feat_directory():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        src_id, feat_id = _create_src_scoped_feat(manager, "001")
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Gate Runtime Refactor Task",
            content="# Task\n",
            run_id="run-task-001",
            parent_id=feat_id,
        )

        assert metadata.path.startswith(f"spec/tasks/{src_id}/{feat_id}/")
        assert (temp_dir / metadata.path).exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_task_parent_feat_passes_p0_validation():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        _, feat_id = _create_src_scoped_feat(manager, "002")
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Gate Approval Task",
            content="# Task\n",
            run_id="run-task-002",
            parent_id=feat_id,
        )

        validator = SSOTValidator(manager.registry)
        result = validator.validate_p0(metadata.id)

        assert result.is_valid, result.errors
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_task_ids_increment_within_same_feat_scope():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        _, feat_id = _create_src_scoped_feat(manager, "010")
        first = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="First Task",
            content="# Task\n",
            run_id="run-task-010",
            parent_id=feat_id,
        )
        second = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Second Task",
            content="# Task\n",
            run_id="run-task-011",
            parent_id=feat_id,
        )

        assert first.id == f"TASK-{feat_id}-001"
        assert second.id == f"TASK-{feat_id}-002"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_freeze_updates_formal_ssot_front_matter():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        _, feat_id = _create_src_scoped_feat(manager, "003")
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Freeze Me",
            content="# Task\n",
            run_id="run-task-003",
            parent_id=feat_id,
        )

        frozen = manager.freeze(metadata.id)
        frozen_text = (temp_dir / frozen.path).read_text(encoding="utf-8")

        assert frozen.status == ArtifactStatus.FROZEN
        assert "status: frozen" in frozen_text
        assert "frozen_at:" in frozen_text
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_gate_collects_ssot_ids_from_freeze_ref_payload():
    harness = _GateHarness()
    instance = SimpleNamespace(
        data={
            "params": {
                "feat_freeze_ref": {
                    "outputs": {
                        "task_1": {"id": "TASK-FEAT-051-001"},
                        "task_2": {"id": "TASK-FEAT-051-002"},
                        "ui_spec": {"id": "UI-FEAT-051-01"},
                    }
                }
            },
            "step_outputs": {},
        }
    )

    collected = harness._collect_gate_freeze_target_ids(instance, "delivery_prep_freeze")

    assert collected == [
        "TASK-FEAT-051-001",
        "TASK-FEAT-051-002",
        "UI-FEAT-051-01",
    ]


def test_ssot_contract_allows_external_source_refs():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        src_id, feat_id = _create_src_scoped_feat(manager, "004")
        materializer = SSOTContractMaterializer(manager)
        contract = {
            "contract_version": "1.0",
            "run_id": "run-task-004",
            "outputs": [
                {
                    "key": "task_runtime",
                    "identity_kind": "ssot",
                    "ssot_type": "task",
                    "title": "Runtime Task",
                    "parent": feat_id,
                    "source_refs": [f"{feat_id}#delivery", f"{src_id}#scope", "FTA-20260311-001"],
                    "verifies": [feat_id],
                    "properties": {"slice_key": "implementation"},
                }
            ],
        }

        outputs = materializer.materialize(contract)

        assert "task_runtime" in outputs
        assert outputs["task_runtime"].artifact.id.startswith(f"TASK-{feat_id}-")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_gate_materialized_src_uses_problem_statement_as_title_slug():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        harness = _GateHarness()

        published = harness._materialize_src_candidate(
            {
                "src_structure": {
                    "title": "SRC",
                    "problem_statement": "QA Department SSOT Alignment and Workflow Reframe",
                },
                "governance_refs": {
                    "source_refs": ["ADR-012"],
                },
                "ssot_identity": {
                    "ssot_type": "SRC",
                },
            },
            manager,
        )

        assert published["artifact_id"].startswith("SRC-")
        assert published["path"].endswith("qa-department-ssot-alignment-and-workflow-reframe.md")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_gate_publish_epic_freeze_to_canonical_spec_directory():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        harness = _GateHarness()
        harness.project_root = temp_dir
        harness.state_machine = SimpleNamespace(
            _resolve_step_inputs_for_freeze=lambda step_id, instance: ["epic_candidate"]
        )

        instance = SimpleNamespace(
            data={
                "params": {},
                "step_outputs": {
                    "epic_candidate": {
                        "business_output": {
                            "title": "QA SSOT Alignment Epic",
                            "goal": "Make QA outputs enter the canonical SSOT chain.",
                            "scope": ["Bind TESTPLAN to RELEASE"],
                            "non_goals": ["Do not redesign the SSOT model itself"],
                            "success_metrics": ["Gate output must publish canonical EPIC"],
                            "priority": "P0",
                            "source_refs": ["SRC-001", "ADR-007"],
                            "ssot": {
                                "identity_kind": "ssot",
                                "ssot_type": "EPIC",
                                "derived_from": "SRC-001",
                            },
                        }
                    },
                    "epic_freeze": {"gate_approved": True},
                },
            }
        )
        harness.store.get_workflow.return_value = instance

        await harness._freeze_gate_targets("wf-epic-001", "epic_freeze")

        epic_files = list((temp_dir / "spec" / "requirements" / "SRC-001").glob("EPIC-*__*.md"))
        assert len(epic_files) == 1
        epic_text = epic_files[0].read_text(encoding="utf-8")
        assert "ssot_type: epic" in epic_text
        assert "status: frozen" in epic_text
        assert "QA SSOT Alignment Epic" in epic_text

        harness.store.update_workflow_data.assert_awaited_once()
        updated_data = harness.store.update_workflow_data.await_args.args[1]
        assert updated_data["params"]["epic_freeze_ref"]["artifact_id"].startswith("EPIC-SRC-001-")
        assert updated_data["params"]["epic_freeze_ref"]["path"].startswith("spec/requirements/SRC-001/")
        assert updated_data["step_outputs"]["epic_freeze"]["epic_freeze_ref"]["artifact_id"].startswith("EPIC-")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.asyncio
async def test_approve_gate_embeds_frozen_business_payload_for_downstream_handoff():
    harness = _GateHarness()
    instance = SimpleNamespace(
        template_id="workflow.product.task.raw_to_src",
        data={
            "completed_steps": ["source_normalization", "source_review"],
            "params": {},
            "step_outputs": {
                "source_normalization": {
                    "generated_text": "very large prose that should not leak downstream",
                    "debug_log_path": "/tmp/debug.log",
                    "business_output": {
                        "source_id": "SRC-013",
                        "title": "需求链一致性测试体系建设",
                        "problem_statement": "将需求链从文档审阅对象转为可测试系统",
                        "target_user": ["governance_owner", "workflow_maintainer"],
                        "business_motivation": "替代人工目检，建立稳定回归能力",
                        "constraints": ["Programmatic Rules First", "L0/L1/L2 成本控制"],
                        "ssot": {
                            "identity_kind": "ssot",
                            "ssot_type": "SRC",
                            "derived_from": "ADR-011",
                        },
                    }
                }
            },
        },
    )
    gate_approval = GateApproval(
        workflow_id="wf-src-001",
        gate_id="gate_wf_src_001_source_freeze",
        step_id="source_freeze",
        status=GateStatus.PENDING,
    )

    harness.template_manager = SimpleNamespace(get_template=lambda _template_id: None)
    harness.gate_engine = SimpleNamespace(evaluate_gate=lambda gate_ir, context: None)
    harness.event_log = SimpleNamespace(log_gate_approved=lambda **kwargs: None)
    harness.state_machine = SimpleNamespace(
        _resolve_step_inputs_for_freeze=lambda step_id, inst: ["normalized_src"],
        complete_step=AsyncMock(return_value={"status": "success"}),
    )
    harness.store = SimpleNamespace(
        get_workflow=AsyncMock(return_value=instance),
        get_gate_approval=AsyncMock(return_value=gate_approval),
        update_gate_approval=AsyncMock(
            return_value=GateApproval(
                workflow_id="wf-src-001",
                gate_id="gate_wf_src_001_source_freeze",
                step_id="source_freeze",
                status=GateStatus.APPROVED,
                approver="codex",
                comments="approve",
            )
        ),
        update_workflow_status=AsyncMock(),
    )
    harness._check_workflow_completion = AsyncMock()
    harness._freeze_gate_targets = AsyncMock()

    await harness.approve_gate(
        workflow_id="wf-src-001",
        gate_id="gate_wf_src_001_source_freeze",
        approver="codex",
        comments="approve",
    )

    gate_output = harness.state_machine.complete_step.await_args.args[2]
    assert gate_output["source_id"] == "SRC-013"
    assert gate_output["title"] == "需求链一致性测试体系建设"
    assert gate_output["freeze_meta"]["status"] == "frozen"
    assert gate_output["freeze_meta"]["frozen_by"] == "codex"
    assert gate_output["frozen_inputs"]["normalized_src"]["business_output"]["source_id"] == "SRC-013"
    assert "generated_text" not in gate_output["frozen_inputs"]["normalized_src"]
    assert "debug_log_path" not in gate_output["frozen_inputs"]["normalized_src"]


@pytest.mark.asyncio
async def test_approve_gate_emits_source_freeze_ref_and_src_root_id():
    harness = _GateHarness()
    instance = SimpleNamespace(
        template_id="workflow.product.task.raw_to_src",
        data={
            "completed_steps": ["source_normalization", "source_review"],
            "params": {},
            "step_outputs": {
                "source_normalization": {
                    "business_output": {
                        "title": "需求链一致性测试体系建设",
                        "ssot_materialized": {
                            "src": {
                                "id": "SRC-041",
                                "path": "spec/source/SRC-041__adr-017-gate-zhilimubiaoyujiazhifenxi.md",
                            }
                        },
                    }
                }
            },
        },
    )
    gate_approval = GateApproval(
        workflow_id="wf-src-002",
        gate_id="gate_wf_src_002_source_freeze",
        step_id="source_freeze",
        status=GateStatus.PENDING,
    )

    harness.template_manager = SimpleNamespace(get_template=lambda _template_id: None)
    harness.gate_engine = SimpleNamespace(evaluate_gate=lambda gate_ir, context: None)
    harness.event_log = SimpleNamespace(log_gate_approved=lambda **kwargs: None)
    harness.state_machine = SimpleNamespace(
        _resolve_step_inputs_for_freeze=lambda step_id, inst: ["normalized_src"],
        complete_step=AsyncMock(return_value={"status": "success"}),
    )
    harness.store = SimpleNamespace(
        get_workflow=AsyncMock(return_value=instance),
        get_gate_approval=AsyncMock(return_value=gate_approval),
        update_gate_approval=AsyncMock(
            return_value=GateApproval(
                workflow_id="wf-src-002",
                gate_id="gate_wf_src_002_source_freeze",
                step_id="source_freeze",
                status=GateStatus.APPROVED,
                approver="codex",
                comments="approve",
            )
        ),
        update_workflow_status=AsyncMock(),
    )
    harness._check_workflow_completion = AsyncMock()
    harness._freeze_gate_targets = AsyncMock()

    await harness.approve_gate(
        workflow_id="wf-src-002",
        gate_id="gate_wf_src_002_source_freeze",
        approver="codex",
        comments="approve",
    )

    gate_output = harness.state_machine.complete_step.await_args.args[2]
    assert gate_output["source_freeze_ref"] == {
        "artifact_id": "SRC-041",
        "path": "spec/source/SRC-041__adr-017-gate-zhilimubiaoyujiazhifenxi.md",
    }
    assert gate_output["src_root_id"] == "SRC-041"


@pytest.mark.asyncio
async def test_approve_gate_advances_parent_workflow_when_child_completes():
    harness = _GateHarness()
    child_instance = SimpleNamespace(
        id="wf-child-001",
        parent_id="wf-parent-001",
        status=WorkflowStatus.COMPLETED,
        template_id="workflow.product.task.raw_to_src",
        data={"completed_steps": [], "params": {}, "step_outputs": {}},
    )
    parent_instance = SimpleNamespace(
        id="wf-parent-001",
        parent_id=None,
        status=WorkflowStatus.RUNNING,
        template_id="workflow.product.main",
        data={"completed_steps": [], "params": {}, "step_outputs": {}},
    )
    gate_approval = GateApproval(
        workflow_id="wf-child-001",
        gate_id="gate_wf_child_001_source_freeze",
        step_id="source_freeze",
        status=GateStatus.PENDING,
    )

    harness.template_manager = SimpleNamespace(get_template=lambda _template_id: None)
    harness.gate_engine = SimpleNamespace(evaluate_gate=lambda gate_ir, context: None)
    harness.event_log = SimpleNamespace(log_gate_approved=lambda **kwargs: None)
    harness.state_machine = SimpleNamespace(
        _resolve_step_inputs_for_freeze=lambda step_id, inst: [],
        complete_step=AsyncMock(return_value={"status": "success"}),
    )

    async def _get_workflow(workflow_id: str):
        if workflow_id == "wf-child-001":
            return child_instance
        if workflow_id == "wf-parent-001":
            return parent_instance
        return None

    harness.store = SimpleNamespace(
        get_workflow=AsyncMock(side_effect=_get_workflow),
        get_gate_approval=AsyncMock(return_value=gate_approval),
        update_gate_approval=AsyncMock(
            return_value=GateApproval(
                workflow_id="wf-child-001",
                gate_id="gate_wf_child_001_source_freeze",
                step_id="source_freeze",
                status=GateStatus.APPROVED,
                approver="codex",
                comments="approve",
            )
        ),
        update_workflow_status=AsyncMock(),
    )
    harness._check_workflow_completion = AsyncMock()
    harness._freeze_gate_targets = AsyncMock()

    await harness.approve_gate(
        workflow_id="wf-child-001",
        gate_id="gate_wf_child_001_source_freeze",
        approver="codex",
        comments="approve",
    )

    harness.run_until_blocked.assert_awaited_once_with("wf-parent-001", max_steps=20)


def test_declared_output_payload_extracts_business_output_from_gate_payload(tmp_path):
    from lee.orchestrator.execution.state_machine import WorkflowStateMachine

    machine = WorkflowStateMachine(store=MagicMock(), template_manager=MagicMock())
    instance = SimpleNamespace(data={"params": {}})

    payload = machine._build_declared_output_payload(
        step_id="source_freeze",
        output={
            "gate_approved": True,
            "approver": "codex",
            "comments": "",
            "frozen_at": "2026-03-12T20:00:00",
            "step_id": "source_freeze",
            "title": "Kimi Executor 接入与配置能力",
            "source_id": "SRC-012",
            "freeze_meta": {"status": "frozen"},
        },
        instance=instance,
        step_output_map={},
    )

    assert payload["business_output"] == {
        "title": "Kimi Executor 接入与配置能力",
        "source_id": "SRC-012",
    }
    assert payload["gate_output"]["gate_approved"] is True


def test_gate_payload_coerces_business_output_from_workspace_artifacts(tmp_path):
    business_output_path = tmp_path / "business_output.yaml"
    business_output_path.write_text(
        "title: Kimi Executor 接入与配置能力\nsource_id: SRC-012\n",
        encoding="utf-8",
    )

    payload = GateOperationsMixin._coerce_gate_business_payload(
        {
            "status": "success",
            "workspace_artifacts": [str(business_output_path)],
        }
    )

    assert payload == {
        "title": "Kimi Executor 接入与配置能力",
        "source_id": "SRC-012",
    }
