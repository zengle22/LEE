import shutil
import tempfile
from pathlib import Path

import yaml

from lee.orchestrator.execution.artifacts import ArtifactManager, SSOTType
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService, SSOTValidator


def test_ssot_validator_reads_parent_and_refs_from_properties():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(root_path=temp_dir / ".artifacts", project_root=temp_dir)

        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="用户注册来源",
            content="# 用户注册来源\n",
            run_id="run-ssot-validator-001",
        )
        epic = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="用户注册史诗",
            content="# 用户注册史诗\n",
            run_id="run-ssot-validator-001",
            parent_id=src.id,
            source_refs=[src.id],
        )
        feat = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="用户注册",
            content="# 用户注册\n",
            run_id="run-ssot-validator-001",
            parent_id=epic.id,
            source_refs=[f"{src.id}#scope", epic.id],
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

        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="增长基础设施来源",
            content="# 增长基础设施来源\n",
            run_id="run-ssot-validator-002",
        )
        epic = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="增长基础设施",
            content="# 增长基础设施\n",
            run_id="run-ssot-validator-002",
            parent_id=src.id,
            source_refs=[src.id],
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


def test_ssot_service_formalize_returns_replacements():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        manager = ArtifactManager(root_path=temp_dir / ".artifacts", project_root=temp_dir)

        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="通知来源",
            content="# 通知来源\n",
            run_id="run-ssot-formalize-001",
        )
        legacy_epic = temp_dir / "spec/requirements/epics/EPIC-001__tongzhishishi.md"
        legacy_feat = temp_dir / "spec/requirements/features/FEAT-001__tongzhinengli.md"
        legacy_epic.parent.mkdir(parents=True, exist_ok=True)
        legacy_feat.parent.mkdir(parents=True, exist_ok=True)
        legacy_epic.write_text(
            "---\n{}\n---\n\n# 通知史诗\n".format(
                yaml.safe_dump(
                    {
                        "id": "EPIC-001",
                        "ssot_type": "epic",
                        "title": "通知史诗",
                        "status": "draft",
                        "version": "v1",
                        "parent_id": src.id,
                        "source_refs": [src.id],
                        "properties": {},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ).strip()
            ),
            encoding="utf-8",
        )
        legacy_feat.write_text(
            "---\n{}\n---\n\n# 通知能力\n".format(
                yaml.safe_dump(
                    {
                        "id": "FEAT-001",
                        "ssot_type": "feat",
                        "title": "通知能力",
                        "status": "draft",
                        "version": "v1",
                        "parent_id": "EPIC-001",
                        "source_refs": [f"{src.id}#scope", "EPIC-001"],
                        "properties": {},
                    },
                    allow_unicode=True,
                    sort_keys=False,
                ).strip()
            ),
            encoding="utf-8",
        )
        manager.rebuild_ssot_registry()

        service = SSOTService(manager)
        result = service.formalize(["EPIC-001", "FEAT-001"])

        assert result["count"] == 2
        assert result["replacements"]["EPIC-001"].startswith(f"EPIC-{src.id}-")
        assert result["replacements"]["FEAT-001"].startswith(f"FEAT-{src.id}-")
        assert "EPIC" in result["grouped_ids"]
        assert "FEAT" in result["grouped_ids"]
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
