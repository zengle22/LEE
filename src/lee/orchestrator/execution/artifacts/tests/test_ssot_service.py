import shutil
import tempfile
from pathlib import Path

from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTType
from lee.orchestrator.execution.artifacts.ssot_service import SSOTValidator


def test_ssot_validator_reads_parent_and_refs_from_properties():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(root_path=temp_dir / ".artifacts", project_root=temp_dir)

        feat = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="用户注册",
            content="# 用户注册\n",
            run_id="run-ssot-validator-001",
        )
        testset = manager.create_ssot(
            ssot_type=SSOTType.TESTSET,
            title="用户注册测试集",
            content="# 用户注册测试集\n",
            run_id="run-ssot-validator-001",
            parent_id=feat.id,
            source_refs=[f"{feat.id}#scope"],
        )

        validator = SSOTValidator(manager.registry)
        result = validator.validate_p0(testset.id)

        assert result.is_valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_ssot_validator_allows_feat_parent_epic():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(root_path=temp_dir / ".artifacts", project_root=temp_dir)

        epic = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="增长基础设施",
            content="# 增长基础设施\n",
            run_id="run-ssot-validator-002",
        )
        feat = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="用户注册",
            content="# 用户注册\n",
            run_id="run-ssot-validator-002",
            parent_id=epic.id,
            source_refs=[f"{epic.id}#scope"],
        )

        validator = SSOTValidator(manager.registry)
        result = validator.validate_p0(feat.id)

        assert result.is_valid
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
