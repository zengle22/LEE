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
