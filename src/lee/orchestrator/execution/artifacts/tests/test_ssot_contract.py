import shutil
import tempfile
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTContractMaterializer


@pytest.fixture
def temp_project_root():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def materializer(temp_project_root):
    manager = ArtifactManager(
        root_path=temp_project_root / ".artifacts",
        project_root=temp_project_root,
    )
    return SSOTContractMaterializer(manager)


def test_validate_contract_requires_ssot_type(materializer):
    contract = {
        "contract_version": "1.0",
        "run_id": "run-001",
        "outputs": [
            {
                "key": "feat",
                "identity_kind": "ssot",
                "title": "用户注册",
            }
        ],
    }

    with pytest.raises(ValueError, match="ssot_type"):
        materializer.validate_contract(contract)


def test_materialize_full_chain_and_non_ssot(materializer):
    contract = {
        "contract_version": "1.0",
        "run_id": "run-002",
        "outputs": [
            {
                "key": "epic",
                "identity_kind": "ssot",
                "ssot_type": "epic",
                "title": "增长基础设施",
                "source_refs": ["SRC-001#1.2"],
            },
            {
                "key": "feat",
                "identity_kind": "ssot",
                "ssot_type": "feat",
                "title": "用户注册",
                "parent": "epic",
                "source_refs": ["epic#scope"],
            },
            {
                "key": "testset",
                "identity_kind": "ssot",
                "ssot_type": "testset",
                "title": "注册测试集",
                "parent": "feat",
                "verifies": ["feat"],
            },
            {
                "key": "tc",
                "identity_kind": "ssot",
                "ssot_type": "tc",
                "title": "重复邮箱失败",
                "parent": "testset",
                "verifies": ["feat"],
            },
            {
                "key": "note",
                "identity_kind": "non_ssot",
                "artifact_type": "DOCUMENT",
                "category": "readme",
                "governance_kind": "knowledge",
                "title": "复盘",
                "depends_on": ["tc"],
            },
        ],
    }

    outputs = materializer.materialize(contract)

    assert outputs["epic"].artifact.id == "EPIC-001"
    assert outputs["feat"].artifact.properties["parent_id"] == outputs["epic"].artifact.id
    assert outputs["feat"].artifact.properties["source_refs"] == [f"{outputs['epic'].artifact.id}#scope"]
    assert outputs["testset"].artifact.properties["parent_id"] == outputs["feat"].artifact.id
    assert outputs["tc"].artifact.properties["parent_id"] == outputs["testset"].artifact.id
    assert outputs["note"].artifact.id.startswith("ART-")
    assert outputs["note"].artifact.absolute_path.parent.name == "run-002"
    assert ".artifacts" in str(outputs["note"].artifact.absolute_path)
    assert outputs["feat"].artifact.absolute_path.exists()
    assert outputs["tc"].artifact.absolute_path.exists()
    validator = materializer.manager.registry
    assert validator.get(outputs["feat"].artifact.id).properties["parent_id"] == outputs["epic"].artifact.id


def test_materialize_task_preserves_formal_task_id(materializer):
    contract = {
        "contract_version": "1.0",
        "run_id": "run-003",
        "outputs": [
            {
                "key": "task_runtime",
                "identity_kind": "ssot",
                "ssot_type": "task",
                "title": "Feature Delivery Core Runtime",
                "parent": "FEAT-SRC-009-001",
                "properties": {
                    "task_id": "TASK-SRC-009-001-001",
                    "slice_key": "workflow_runtime",
                    "workstream": "workflow-runtime",
                },
                "source_refs": ["FEAT-SRC-009-001#delivery"],
                "verifies": ["FEAT-SRC-009-001"],
            }
        ],
    }

    outputs = materializer.materialize(contract)

    task = outputs["task_runtime"].artifact
    assert task.id == "TASK-SRC-009-001-001"
    assert task.absolute_path.name.startswith("TASK-SRC-009-001-001__")


def test_materialize_ui_and_tech_inherit_feat_lineage(materializer):
    materializer.manager.create_ssot(
        ssot_type="feat",
        formal_id="FEAT-082",
        title="Formal Object Metadata Inheritance",
        content="# FEAT-082",
        run_id="run-parent",
        parent_id="EPIC-003",
        source_refs=["EPIC-003#scope"],
        version="v3",
    )

    contract = {
        "contract_version": "1.0",
        "run_id": "run-082",
        "outputs": [
            {
                "key": "ui_prototype",
                "identity_kind": "ssot",
                "ssot_type": "ui",
                "title": "Metadata Inheritance UI",
                "parent": "FEAT-082",
            },
            {
                "key": "tech_spec",
                "identity_kind": "ssot",
                "ssot_type": "tech",
                "title": "Metadata Inheritance TECH",
                "parent": "FEAT-082",
            },
        ],
    }

    outputs = materializer.materialize(contract)

    ui_artifact = outputs["ui_prototype"].artifact
    tech_artifact = outputs["tech_spec"].artifact
    assert ui_artifact.properties["parent_id"] == "FEAT-082"
    assert ui_artifact.properties["source_refs"] == ["FEAT-082#design"]
    assert ui_artifact.properties["derived_from_ids"][0]["id"] == "FEAT-082"
    assert ui_artifact.properties["derived_from_ids"][0]["version"] == "v3"
    assert tech_artifact.properties["source_refs"] == ["FEAT-082#design"]
    assert tech_artifact.properties["derived_from_ids"][0]["id"] == "FEAT-082"


def test_materialize_feat_infers_parent_from_source_ref(materializer):
    materializer.manager.create_ssot(
        ssot_type="epic",
        formal_id="EPIC-003",
        title="Workflow First CLI",
        content="# EPIC-003",
        run_id="run-parent",
        source_refs=["SRC-001#scope"],
        version="v2",
    )

    contract = {
        "contract_version": "1.0",
        "run_id": "run-083",
        "outputs": [
            {
                "key": "feat",
                "identity_kind": "ssot",
                "ssot_type": "feat",
                "title": "Metadata Engine Core",
                "source_refs": ["EPIC-003#scope"],
                "properties": {"formal_id": "FEAT-082"},
            }
        ],
    }

    outputs = materializer.materialize(contract)
    feat_artifact = outputs["feat"].artifact
    assert feat_artifact.properties["parent_id"] == "EPIC-003"
    assert feat_artifact.properties["source_refs"] == ["EPIC-003#scope"]
    assert feat_artifact.properties["derived_from_ids"][0]["id"] == "EPIC-003"
    assert feat_artifact.properties["derived_from_ids"][0]["version"] == "v2"
