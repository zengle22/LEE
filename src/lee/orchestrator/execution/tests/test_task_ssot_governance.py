import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.ssot_contract import SSOTContractMaterializer
from lee.orchestrator.execution.artifacts.ssot_service import SSOTValidator
from lee.orchestrator.execution.artifacts.types import ArtifactStatus, SSOTType
from lee.orchestrator.execution.gate_operations import GateOperationsMixin


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
