"""
Tests for ArtifactRegistry
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts.registry import ArtifactRegistry
from lee.orchestrator.execution.artifacts.models import ArtifactMetadata, RunManifest
from lee.orchestrator.execution.artifacts.types import (
    ArtifactType,
    ArtifactStatus,
)


@pytest.fixture
def temp_artifacts_dir():
    """创建临时 .artifacts 目录"""
    temp_dir = Path(tempfile.mkdtemp())
    artifacts_dir = temp_dir / ".artifacts"
    yield artifacts_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def registry(temp_artifacts_dir):
    """创建 Registry 实例"""
    original_cwd = Path.cwd()
    parent_dir = temp_artifacts_dir.parent
    os.chdir(parent_dir)

    reg = ArtifactRegistry(temp_artifacts_dir)

    yield reg

    os.chdir(original_cwd)


class TestArtifactRegistry:
    """测试 ArtifactRegistry"""

    def test_init_creates_lock_file(self, registry, temp_artifacts_dir):
        """测试初始化"""
        # Registry 不自动创建目录，但 Manager 会
        # 这里测试 Registry 的属性设置
        assert registry.root_path == temp_artifacts_dir
        assert registry.registry_file == registry.root_path / ".registry.json"
        assert registry.lock_file == registry.root_path / ".registry.lock"

    def test_register_artifact(self, registry):
        """测试注册产出物"""
        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
            department="pm",
        )

        registry.register(artifact)

        retrieved = registry.get("ART-00001")
        assert retrieved is not None
        assert retrieved.id == "ART-00001"

    def test_get_artifact(self, registry):
        """测试获取产出物"""
        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
        )

        registry.register(artifact)

        retrieved = registry.get("ART-00001")
        assert retrieved is not None
        assert retrieved.id == "ART-00001"

        not_found = registry.get("NONEXISTENT")
        assert not_found is None

    def test_update_artifact(self, registry):
        """测试更新产出物"""
        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
            title="Original Title",
        )

        registry.register(artifact)

        # 更新
        artifact.title = "Updated Title"
        artifact.status = ArtifactStatus.FROZEN
        registry.update(artifact)

        retrieved = registry.get("ART-00001")
        assert retrieved.title == "Updated Title"
        assert retrieved.status == ArtifactStatus.FROZEN

    def test_update_nonexistent_raises(self, registry):
        """测试更新不存在的产出物应抛出异常"""
        artifact = ArtifactMetadata(
            id="ART-99999",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
        )

        with pytest.raises(KeyError, match="not found"):
            registry.update(artifact)

    def test_get_by_run(self, registry):
        """测试按 run 获取产出物"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/test1.md",
                run_id="run-001",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/test2.md",
                run_id="run-001",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.TEST,
                category="test_report",
                status=ArtifactStatus.ACTIVE,
                path="active/test3.md",
                run_id="run-002",
            )
        )

        run1_artifacts = registry.get_by_run("run-001")
        assert len(run1_artifacts) == 2
        assert all(a.run_id == "run-001" for a in run1_artifacts)

        run2_artifacts = registry.get_by_run("run-002")
        assert len(run2_artifacts) == 1

    def test_get_by_type(self, registry):
        """测试按类型获取产出物"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/doc1.md",
                run_id="run-001",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/doc2.md",
                run_id="run-002",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.TEST,
                category="test_report",
                status=ArtifactStatus.ACTIVE,
                path="active/test.md",
                run_id="run-003",
            )
        )

        docs = registry.get_by_type("DOCUMENT")
        assert len(docs) == 2
        assert all(a.type == ArtifactType.DOCUMENT for a in docs)

        tests = registry.get_by_type("TEST")
        assert len(tests) == 1

    def test_get_by_category(self, registry):
        """测试按类别获取产出物"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/readme1.md",
                run_id="run-001",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.CONTRACT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/readme2.md",
                run_id="run-002",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/guide.md",
                run_id="run-003",
            )
        )

        readmes = registry.get_by_category("readme")
        assert len(readmes) == 2
        assert all(a.category == "readme" for a in readmes)

    def test_get_by_status(self, registry):
        """测试按状态获取产出物"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/test1.md",
                run_id="run-001",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.FROZEN,
                path="frozen/test2.md",
                run_id="run-002",
            )
        )

        active = registry.get_by_status("ACTIVE")
        assert len(active) == 1
        assert active[0].status == ArtifactStatus.ACTIVE

        frozen = registry.get_by_status("FROZEN")
        assert len(frozen) == 1
        assert frozen[0].status == ArtifactStatus.FROZEN

    def test_get_by_department(self, registry):
        """测试按部门获取产出物"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/test1.md",
                run_id="run-001",
                department="pm",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/test2.md",
                run_id="run-002",
                department="qa",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.TEST,
                category="test_report",
                status=ArtifactStatus.ACTIVE,
                path="active/test3.md",
                run_id="run-003",
                department="pm",
            )
        )

        pm_artifacts = registry.get_by_department("pm")
        assert len(pm_artifacts) == 2
        assert all(a.department == "pm" for a in pm_artifacts)

        qa_artifacts = registry.get_by_department("qa")
        assert len(qa_artifacts) == 1

    def test_find_references_to(self, registry):
        """测试查找引用"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.CONTRACT,
                category="frozen_prd",
                status=ArtifactStatus.ACTIVE,
                path="active/prd.md",
                run_id="run-001",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/readme.md",
                run_id="run-002",
                depends_on=["ART-00001"],
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/guide.md",
                run_id="run-003",
                derived_from="ART-00001",
            )
        )

        references = registry.find_references_to("ART-00001")

        assert len(references) == 2
        referenced_ids = {r.id for r in references}
        assert "ART-00002" in referenced_ids
        assert "ART-00003" in referenced_ids

    def test_get_statistics(self, registry):
        """测试获取统计信息"""
        registry.register(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/test1.md",
                run_id="run-001",
                department="pm",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/test2.md",
                run_id="run-002",
                department="qa",
            )
        )
        registry.register(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.TEST,
                category="test_report",
                status=ArtifactStatus.FROZEN,
                path="frozen/test3.md",
                run_id="run-003",
                department="qa",
            )
        )

        stats = registry.get_statistics()

        assert stats["total_artifacts"] == 3
        assert stats["by_type"]["DOCUMENT"] == 2
        assert stats["by_type"]["TEST"] == 1
        assert stats["by_status"]["ACTIVE"] == 2
        assert stats["by_status"]["FROZEN"] == 1
        assert stats["by_department"]["pm"] == 1
        assert stats["by_department"]["qa"] == 2
        assert stats["total_runs"] == 3

    def test_save_and_load(self, registry, temp_artifacts_dir):
        """测试保存和加载注册表"""
        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
        )

        registry.register(artifact)
        registry._save()

        # 创建新实例并加载
        new_registry = ArtifactRegistry(temp_artifacts_dir)
        new_registry.load()

        retrieved = new_registry.get("ART-00001")
        assert retrieved is not None
        assert retrieved.id == "ART-00001"
        assert retrieved.category == "readme"

    def test_rebuild_from_manifests(self, registry, temp_artifacts_dir):
        """测试从 manifest 重建注册表"""
        # 创建一些 manifest 文件
        active_dir = temp_artifacts_dir / "active" / "pm" / "test-run"
        active_dir.mkdir(parents=True)

        manifest = RunManifest(
            run_id="test-run",
            department="pm",
            status="completed",
        )
        manifest.add_artifact(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/pm/test-run/artifact.md",
                run_id="test-run",
                department="pm",
            )
        )
        manifest.save(active_dir / "manifest.yaml")

        # 重建
        registry.rebuild()

        # 验证
        assert registry.get("ART-00001") is not None
        assert len(registry.get_by_run("test-run")) == 1
