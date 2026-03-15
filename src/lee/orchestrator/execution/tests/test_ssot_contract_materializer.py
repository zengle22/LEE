from pathlib import Path

from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.ssot_contract import SSOTContractMaterializer


def test_materializer_drops_legacy_epic_formal_id_when_src_scope_exists(tmp_path: Path) -> None:
    manager = ArtifactManager(project_root=tmp_path)
    materializer = SSOTContractMaterializer(manager)

    outputs = materializer.materialize(
        {
            "contract_version": "1.0",
            "run_id": "wf-epic-scope-001",
            "outputs": [
                {
                    "key": "epic",
                    "identity_kind": "ssot",
                    "ssot_type": "epic",
                    "title": "交付轴 workflow 化治理与发布闭环建设",
                    "content": "# 交付轴 workflow 化治理与发布闭环建设\n",
                    "source_refs": ["SRC-046#scope"],
                    "derived_from": ["SRC-046"],
                    "properties": {
                        "formal_id": "EPIC-046",
                    },
                }
            ],
        }
    )

    artifact = outputs["epic"].artifact
    assert artifact.id == "EPIC-SRC-046-001"
    assert artifact.absolute_path == (
        tmp_path
        / "spec"
        / "requirements"
        / "SRC-046"
        / "EPIC-SRC-046-001__jiaofuzhou-workflow-huazhiliyufabubihuanjianshe.md"
    )


def test_materializer_preserves_scoped_epic_formal_id(tmp_path: Path) -> None:
    manager = ArtifactManager(project_root=tmp_path)
    materializer = SSOTContractMaterializer(manager)

    outputs = materializer.materialize(
        {
            "contract_version": "1.0",
            "run_id": "wf-epic-scope-002",
            "outputs": [
                {
                    "key": "epic",
                    "identity_kind": "ssot",
                    "ssot_type": "epic",
                    "title": "交付轴 workflow 化治理与发布闭环建设",
                    "content": "# 交付轴 workflow 化治理与发布闭环建设\n",
                    "source_refs": ["SRC-046#scope"],
                    "derived_from": ["SRC-046"],
                    "properties": {
                        "formal_id": "EPIC-SRC-046-009",
                    },
                }
            ],
        }
    )

    assert outputs["epic"].artifact.id == "EPIC-SRC-046-009"
