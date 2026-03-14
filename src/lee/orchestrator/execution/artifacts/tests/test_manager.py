"""
Tests for ArtifactManager
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
import yaml

from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.models import ArtifactMetadata
from lee.orchestrator.execution.artifacts.types import (
    ArtifactType,
    ArtifactStatus,
    AdoptMode,
    SSOTType,
)


@pytest.fixture
def temp_artifacts_dir():
    """创建临时 .artifacts 目录"""
    temp_dir = Path(tempfile.mkdtemp())
    artifacts_dir = temp_dir / ".artifacts"
    yield artifacts_dir
    # 清理
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def manager(temp_artifacts_dir):
    """创建 ArtifactManager 实例"""
    # 改变工作目录到临时目录
    original_cwd = Path.cwd()
    parent_dir = temp_artifacts_dir.parent
    os.chdir(parent_dir)

    manager = ArtifactManager(temp_artifacts_dir)

    yield manager

    # 恢复工作目录
    os.chdir(original_cwd)


class TestArtifactManager:
    """测试 ArtifactManager"""

    def test_init_creates_directories(self, temp_artifacts_dir):
        """测试初始化创建目录结构"""
        ArtifactManager(temp_artifacts_dir)

        assert (temp_artifacts_dir / "active").exists()
        assert (temp_artifacts_dir / "frozen").exists()
        assert (temp_artifacts_dir / "archive").exists()
        assert (temp_artifacts_dir / "logs").exists()
        assert (temp_artifacts_dir / "cache").exists()

    def test_generate_unique_ids(self, manager):
        """测试生成唯一 ID"""
        ids = set()
        for _ in range(100):
            artifact_id = manager._generate_id()
            ids.add(artifact_id)

        assert len(ids) == 100
        assert all(id.startswith("ART-") for id in ids)

    def test_create_with_string_content(self, manager):
        """测试创建产出物 (字符串内容)"""
        metadata = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Test Document\n\nThis is test content.",
            run_id="test-run-001",
            title="Test Doc",
            description="A test document",
            department="pm",
        )

        assert metadata.id.startswith("ART-")
        assert metadata.type == ArtifactType.DOCUMENT
        assert metadata.category == "readme"
        assert metadata.status == ArtifactStatus.ACTIVE
        assert metadata.run_id == "test-run-001"
        assert metadata.department == "pm"
        assert metadata.title == "Test Doc"
        assert metadata.size_bytes > 0
        assert metadata.content_hash is not None
        assert metadata.absolute_path.exists()

        # 验证内容
        content = metadata.absolute_path.read_text()
        assert "Test Document" in content

    def test_create_with_bytes_content(self, manager):
        """测试创建产出物 (字节内容)"""
        content = b"Binary content \x00\x01\x02"
        metadata = manager.create(
            artifact_type=ArtifactType.INTERMEDIATE,
            category="temp",
            content=content,
            run_id="test-run-002",
        )

        assert metadata.absolute_path.exists()
        assert metadata.absolute_path.read_bytes() == content

    def test_create_with_file_path(self, manager):
        """测试创建产出物 (从文件路径)"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("# External File\n\nContent")
            external_path = Path(f.name)

        try:
            metadata = manager.create(
                artifact_type=ArtifactType.DOCUMENT,
                category="readme",
                content=external_path,
                run_id="test-run-003",
            )

            assert metadata.absolute_path.exists()
            content = metadata.absolute_path.read_text()
            assert "External File" in content
        finally:
            external_path.unlink()

    def test_create_invalid_category_raises(self, manager):
        """测试创建无效类别应抛出异常"""
        with pytest.raises(ValueError, match="Invalid category"):
            manager.create(
                artifact_type=ArtifactType.DOCUMENT,
                category="invalid_category",
                content="test",
                run_id="test-run",
            )

    def test_get_artifact(self, manager):
        """测试获取产出物"""
        created = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Test",
            run_id="test-run",
        )

        retrieved = manager.get(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_nonexistent_returns_none(self, manager):
        """测试获取不存在的产出物返回 None"""
        result = manager.get("ART-NONEXISTENT")
        assert result is None

    def test_get_content(self, manager):
        """测试获取产出物内容"""
        original_content = "# Test Content\n\nSome text."
        metadata = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content=original_content,
            run_id="test-run",
        )

        content = manager.get_content(metadata.id)

        assert content == original_content

    def test_adopt_copy_mode(self, manager):
        """测试 adopt copy_mode"""
        # 创建外部文件
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".md") as f:
            f.write("# External\n\nAdopt me!")
            external_path = Path(f.name)

        try:
            metadata = manager.adopt(
                external_path=external_path,
                run_id="test-run",
                artifact_type=ArtifactType.DOCUMENT,
                category="readme",
                mode=AdoptMode.COPY,
                title="Adopted File",
                department="qa",
            )

            assert metadata.id.startswith("ART-")
            assert metadata.adopt_mode == AdoptMode.COPY
            assert metadata.external_path == str(external_path)
            assert metadata.absolute_path.exists()

            # 验证内容被复制
            content = metadata.absolute_path.read_text()
            assert "Adopt me!" in content
        finally:
            external_path.unlink()

    def test_adopt_infers_mode(self, manager):
        """测试自动推断 adopt 模式"""
        # CODE_REF 默认使用 reference_mode
        with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".py") as f:
            f.write("def test(): pass")
            external_path = Path(f.name)

        try:
            # 不指定 mode，自动推断
            metadata = manager.adopt(
                external_path=external_path,
                run_id="test-run",
                artifact_type=ArtifactType.DOCUMENT,  # DOCUMENT 默认 copy_mode
                category="readme",
            )

            assert metadata.adopt_mode == AdoptMode.COPY
        finally:
            external_path.unlink()

    def test_delete_artifact(self, manager):
        """测试删除产出物"""
        metadata = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Test",
            run_id="test-run",
        )

        file_path = metadata.absolute_path
        assert file_path.exists()

        result = manager.delete(metadata.id)

        assert result is True
        assert not file_path.exists()
        assert manager.get(metadata.id) is None

    def test_freeze_artifact(self, manager):
        """测试冻结产出物"""
        metadata = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Test",
            run_id="test-run",
        )

        assert metadata.status == ArtifactStatus.ACTIVE

        frozen = manager.freeze(metadata.id)

        assert frozen.status == ArtifactStatus.FROZEN
        assert frozen.frozen_at is not None
        assert frozen.path.startswith("frozen/")

    def test_create_ssot_rerun_replaces_existing_checked_in_file(self, manager):
        """测试同一 formal_id 重跑时覆盖旧文件而不是生成重复文件"""
        first = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            formal_id="TASK-FEAT-SRC-009-001-001",
            parent_id="FEAT-SRC-009-001",
            title="旧标题",
            content="# First\n",
            run_id="test-run-001",
        )

        second = manager.create_ssot(
            ssot_type=SSOTType.TASK,
            formal_id="TASK-FEAT-SRC-009-001-001",
            parent_id="FEAT-SRC-009-001",
            title="新标题",
            content="# Second\n",
            run_id="test-run-002",
        )

        task_dir = manager.project_root / "spec" / "tasks" / "SRC-009" / "FEAT-SRC-009-001"
        matching_files = sorted(task_dir.glob("TASK-FEAT-SRC-009-001-001__*.md"))

        assert len(matching_files) == 1
        assert matching_files[0] == second.absolute_path
        assert not first.absolute_path.exists()
        assert second.absolute_path.read_text(encoding="utf-8").startswith("---\n")
        assert manager.registry.get("TASK-FEAT-SRC-009-001-001").path == (
            second.absolute_path.relative_to(manager.project_root).as_posix()
        )

    def test_freeze_already_frozen_idempotent(self, manager):
        """测试冻结已冻结的产出物是幂等的"""
        metadata = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Test",
            run_id="test-run",
        )

        first = manager.freeze(metadata.id)
        second = manager.freeze(metadata.id)

        assert second.status == ArtifactStatus.FROZEN
        assert first.path == second.path

    def test_registry_statistics(self, manager):
        """测试注册表统计"""
        # 创建不同类型的产出物
        manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="doc1",
            run_id="run1",
            department="pm",
        )
        manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="usage_guide",
            content="doc2",
            run_id="run2",
            department="qa",
        )
        manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_report",
            content="report",
            run_id="run3",
        )

        stats = manager.registry.get_statistics()

        assert stats["total_artifacts"] == 3
        assert stats["by_type"]["DOCUMENT"] == 2
        assert stats["by_type"]["TEST"] == 1
        assert stats["by_department"]["pm"] == 1
        assert stats["by_department"]["qa"] == 1

    def test_create_ssot_uses_project_placement(self, manager):
        """测试正式 SSOT 文件落在项目目录而不是 .artifacts/ssot"""
        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="用户注册来源",
            content="# Source\n",
            run_id="run-ssot-src",
        )
        epic = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="用户注册史诗",
            content="# Epic\n",
            run_id="run-ssot-epic",
            parent_id=src.id,
            source_refs=[src.id],
        )
        feat = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="用户注册",
            content="# Feature\n",
            run_id="run-ssot-feat",
            parent_id=epic.id,
            source_refs=[f"{src.id}#scope", epic.id],
        )

        testset = manager.create_ssot(
            ssot_type=SSOTType.TESTSET,
            title="用户注册测试集",
            content="# Test Set\n",
            run_id="run-ssot-testset",
            parent_id=feat.id,
        )

        assert feat.path_root == "."
        assert feat.path.startswith(f"spec/requirements/{src.id}/")
        assert feat.absolute_path.exists()
        assert ".artifacts\\ssot" not in str(feat.absolute_path)
        assert testset.path.startswith(f"spec/testing/testsets/{src.id}/")
        assert testset.properties["placement_dir"] == f"spec/testing/testsets/{src.id}"

    def test_create_ssot_writes_workflow_instance_id_front_matter(self, manager):
        metadata = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="Workflow First CLI",
            content="# FEAT\n",
            run_id="wf_task_123",
        )

        text = metadata.absolute_path.read_text(encoding="utf-8")

        assert "workflow_instance_id: wf_task_123" in text

    def test_create_ssot_merges_workflow_instance_id_into_existing_front_matter(self, manager):
        metadata = manager.create_ssot(
            ssot_type=SSOTType.TECH,
            title="Workflow First CLI Tech",
            content="---\nid: FTA-FEAT-001-001\nssot_type: frozen_technical_architecture\ntitle: Legacy\n---\n\n# Body\n",
            run_id="wf_task_456",
            parent_id="FEAT-001",
        )

        text = metadata.absolute_path.read_text(encoding="utf-8")

        assert "workflow_instance_id: wf_task_456" in text
        assert "id: TECH-FEAT-001-001" in text

    def test_create_ssot_infers_parent_and_lineage_from_source_ref(self, manager):
        manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            formal_id="EPIC-003",
            title="Workflow First CLI",
            content="# EPIC-003\n",
            run_id="wf_task_parent",
            source_refs=["SRC-001#scope"],
            version="v2",
        )

        metadata = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            formal_id="FEAT-082",
            title="Metadata Inheritance Engine",
            content="# FEAT-082\n",
            run_id="wf_task_child",
            source_refs=["EPIC-003#scope"],
        )

        assert metadata.properties["parent_id"] == "EPIC-003"
        assert metadata.properties["source_refs"] == ["EPIC-003#scope"]
        assert metadata.properties["derived_from_ids"][0]["id"] == "EPIC-003"
        assert metadata.properties["derived_from_ids"][0]["version"] == "v2"

    def test_list_ssot_by_parent_uses_parent_index(self, manager):
        """测试按父对象查询 SSOT 子对象"""
        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="支付来源",
            content="# Source\n",
            run_id="run-parent-src",
        )
        epic = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="支付史诗",
            content="# Epic\n",
            run_id="run-parent-epic",
            parent_id=src.id,
            source_refs=[src.id],
        )
        feat = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="支付能力",
            content="# Feature\n",
            run_id="run-parent-feat",
            parent_id=epic.id,
            source_refs=[f"{src.id}#scope", epic.id],
        )
        testset = manager.create_ssot(
            ssot_type=SSOTType.TESTSET,
            title="支付测试集",
            content="# Test Set\n",
            run_id="run-parent-testset",
            parent_id=feat.id,
        )

        children = manager.list_ssot_by_parent(feat.id)

        assert [child.id for child in children] == [testset.id]

    def test_freeze_ssot_keeps_project_path(self, manager):
        """测试正式 SSOT 冻结时保留项目目录主文件"""
        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="训练计划来源",
            content="# Source\n",
            run_id="run-freeze-src",
        )
        epic = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="训练计划史诗",
            content="# Epic\n",
            run_id="run-freeze-epic",
            parent_id=src.id,
            source_refs=[src.id],
        )
        feat = manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="训练计划",
            content="# Feature\n",
            run_id="run-freeze-ssot",
            parent_id=epic.id,
            source_refs=[f"{src.id}#scope", epic.id],
        )

        original_path = feat.path
        frozen = manager.freeze(feat.id)

        assert frozen.status == ArtifactStatus.FROZEN
        assert frozen.path == original_path
        assert frozen.path_root == "."
        assert frozen.absolute_path.exists()

    def test_create_ssot_with_custom_project_root(self, temp_artifacts_dir):
        """测试自定义项目根目录时 SSOT 主文件路径正确"""
        custom_root = temp_artifacts_dir.parent / "custom-project"
        custom_manager = ArtifactManager(
            root_path=custom_root / ".artifacts",
            project_root=custom_root,
        )

        src = custom_manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="自定义来源",
            content="# Source\n",
            run_id="run-custom-src",
        )
        epic = custom_manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title="自定义史诗",
            content="# Epic\n",
            run_id="run-custom-epic",
            parent_id=src.id,
            source_refs=[src.id],
        )
        feat = custom_manager.create_ssot(
            ssot_type=SSOTType.FEAT,
            title="自定义项目",
            content="# Feature\n",
            run_id="run-custom-project-root",
            parent_id=epic.id,
            source_refs=[f"{src.id}#scope", epic.id],
        )

        assert feat.path_root in {"custom-project", str(custom_root)}
        assert feat.absolute_path == custom_root / "spec/requirements" / src.id / Path(feat.path).name
        assert feat.absolute_path.exists()

    def test_formalize_ssot_ids_rewrites_paths_and_refs(self, manager):
        src = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="消息中心来源",
            content="# Source\n",
            run_id="run-formalize-src",
        )
        legacy_docs = {
            "EPIC-001": (
                manager.project_root / "spec/requirements/epics/EPIC-001__xiaoxizhongxinshishi.md",
                {
                    "id": "EPIC-001",
                    "ssot_type": "epic",
                    "title": "消息中心史诗",
                    "status": "draft",
                    "version": "v1",
                    "parent_id": src.id,
                    "source_refs": [src.id],
                    "properties": {},
                },
                "# Epic\n",
            ),
            "FEAT-001": (
                manager.project_root / "spec/requirements/features/FEAT-001__zhanneixin.md",
                {
                    "id": "FEAT-001",
                    "ssot_type": "feat",
                    "title": "站内信",
                    "status": "draft",
                    "version": "v1",
                    "parent_id": "EPIC-001",
                    "source_refs": [f"{src.id}#scope", "EPIC-001"],
                    "properties": {},
                },
                "# Feature\nSee EPIC-001\n",
            ),
            "TECH-FEAT-001": (
                manager.project_root / "spec/design/tech/TECH-FEAT-001__zhanneixinjishufangan.md",
                {
                    "id": "TECH-FEAT-001",
                    "ssot_type": "tech",
                    "title": "站内信技术方案",
                    "status": "draft",
                    "version": "v1",
                    "parent_id": "FEAT-001",
                    "source_refs": ["FEAT-001"],
                    "properties": {},
                },
                "# Tech\nDepends on FEAT-001\n",
            ),
            "TASK-FEAT-001-001": (
                manager.project_root / "spec/tasks/FEAT-001/TASK-FEAT-001-001__zhanneixinrenwu.md",
                {
                    "id": "TASK-FEAT-001-001",
                    "ssot_type": "task",
                    "title": "站内信任务",
                    "status": "draft",
                    "version": "v1",
                    "parent_id": "FEAT-001",
                    "source_refs": ["FEAT-001"],
                    "properties": {},
                },
                "# Task\nTrace to FEAT-001\n",
            ),
        }
        for path, front_matter, body in legacy_docs.values():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                "---\n{}\n---\n\n{}".format(
                    yaml.safe_dump(front_matter, allow_unicode=True, sort_keys=False).strip(),
                    body,
                ),
                encoding="utf-8",
            )

        manager.rebuild_ssot_registry()
        old_tech_path = legacy_docs["TECH-FEAT-001"][0]
        replacements = manager.formalize_ssot_ids(list(legacy_docs.keys()))

        new_epic_id = replacements["EPIC-001"]
        new_feat_id = replacements["FEAT-001"]
        new_tech_id = replacements["TECH-FEAT-001"]
        new_task_id = replacements["TASK-FEAT-001-001"]

        assert new_epic_id.startswith(f"EPIC-{src.id}-")
        assert new_feat_id.startswith(f"FEAT-{src.id}-")
        assert new_tech_id == f"TECH-{new_feat_id}"
        assert new_task_id.startswith(f"TASK-{new_feat_id}-")
        assert not old_tech_path.exists()

        rebuilt_feat = manager.get_ssot(new_feat_id)
        rebuilt_tech = manager.get_ssot(new_tech_id)
        rebuilt_task = manager.get_ssot(new_task_id)

        assert rebuilt_feat is not None
        assert rebuilt_tech is not None
        assert rebuilt_task is not None
        assert rebuilt_feat.path.startswith(f"spec/requirements/{src.id}/")
        assert rebuilt_tech.path.startswith(f"spec/tech/{src.id}/")
        assert rebuilt_task.path.startswith(f"spec/tasks/{src.id}/{new_feat_id}/")
        assert "FEAT-001" not in rebuilt_task.absolute_path.read_text(encoding="utf-8")
        assert new_feat_id in rebuilt_task.absolute_path.read_text(encoding="utf-8")


class TestArtifactManagerReferences:
    """测试引用保护机制"""

    def test_delete_referenced_artifact_raises(self, manager):
        """测试删除被引用的产出物应抛出异常"""
        # 创建第一个产出物
        artifact1 = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="frozen_prd",
            content="# PRD",
            run_id="run1",
        )

        # 创建依赖它的产出物
        artifact2 = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Readme",
            run_id="run2",
            depends_on=[artifact1.id],
        )

        # 尝试删除被依赖的产出物
        with pytest.raises(RuntimeError, match="still referenced"):
            manager.delete(artifact1.id)

    def test_delete_referenced_with_force(self, manager):
        """测试强制删除被引用的产出物"""
        artifact1 = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="frozen_prd",
            content="# PRD",
            run_id="run1",
        )

        manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Readme",
            run_id="run2",
            depends_on=[artifact1.id],
        )

        # 强制删除
        result = manager.delete(artifact1.id, force=True)

        assert result is True

    def test_find_references_to(self, manager):
        """测试查找引用"""
        artifact1 = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="frozen_prd",
            content="# PRD",
            run_id="run1",
        )

        artifact2 = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Readme",
            run_id="run2",
            depends_on=[artifact1.id],
        )

        artifact3 = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="usage_guide",
            content="# Guide",
            run_id="run3",
            derived_from=artifact1.id,
        )

        references = manager.registry.find_references_to(artifact1.id)

        assert len(references) == 2
        referenced_ids = {r.id for r in references}
        assert artifact2.id in referenced_ids
        assert artifact3.id in referenced_ids
