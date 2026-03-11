import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace

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


def test_task_ssot_materializes_under_feat_directory():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Gate Runtime Refactor Task",
            content="# Task\n",
            run_id="run-task-001",
            parent_id="FEAT-051",
        )

        assert metadata.path.startswith("spec/tasks/FEAT-051/")
        assert (temp_dir / metadata.path).exists()
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_task_parent_feat_passes_p0_validation():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Gate Approval Task",
            content="# Task\n",
            run_id="run-task-002",
            parent_id="FEAT-052",
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
        first = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="First Task",
            content="# Task\n",
            run_id="run-task-010",
            parent_id="FEAT-057",
        )
        second = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Second Task",
            content="# Task\n",
            run_id="run-task-011",
            parent_id="FEAT-057",
        )

        assert first.id == "TASK-FEAT-057-001"
        assert second.id == "TASK-FEAT-057-002"
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_freeze_updates_formal_ssot_front_matter():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(project_root=temp_dir)
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            title="Freeze Me",
            content="# Task\n",
            run_id="run-task-003",
            parent_id="FEAT-053",
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
                    "parent": "FEAT-056",
                    "source_refs": ["FEAT-056#delivery", "FTA-20260311-001"],
                    "verifies": ["FEAT-056"],
                    "properties": {"slice_key": "implementation"},
                }
            ],
        }

        outputs = materializer.materialize(contract)

        assert "task_runtime" in outputs
        assert outputs["task_runtime"].artifact.id.startswith("TASK-FEAT-056-")
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
