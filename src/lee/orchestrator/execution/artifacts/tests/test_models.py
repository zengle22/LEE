"""
Tests for artifact data models
"""

import pytest
from datetime import datetime
from pathlib import Path

from lee.orchestrator.execution.artifacts.models import ArtifactMetadata, RunManifest
from lee.orchestrator.execution.artifacts.types import (
    ArtifactType,
    ArtifactStatus,
    AdoptMode,
)


class TestArtifactMetadata:
    """测试 ArtifactMetadata 数据模型"""

    def test_create_minimal(self):
        """测试创建最小元数据"""
        metadata = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/pm/test-run/ART-00001.md",
        )

        assert metadata.id == "ART-00001"
        assert metadata.type == ArtifactType.DOCUMENT
        assert metadata.category == "readme"
        assert metadata.status == ArtifactStatus.ACTIVE
        assert metadata.path == "active/pm/test-run/ART-00001.md"
        assert metadata.path_root == ".artifacts"
        assert metadata.external_path is None
        assert metadata.adopt_mode is None
        assert metadata.run_id == ""

    def test_create_full(self):
        """测试创建完整元数据"""
        now = datetime.now()
        metadata = ArtifactMetadata(
            id="ART-00002",
            type=ArtifactType.CONTRACT,
            category="frozen_prd",
            status=ArtifactStatus.FROZEN,
            path="frozen/ART-00002.md",
            external_path="/tmp/original.md",
            adopt_mode=AdoptMode.COPY,
            run_id="test-run-123",
            workflow_id="wf-456",
            department="pm",
            depends_on=["ART-00001"],
            derived_from="ART-00000",
            consumed_by=["backend", "qa"],
            title="Test PRD",
            description="A test PRD document",
            tags=["test", "prd"],
            size_bytes=1024,
            content_hash="abc123",
            created_at=now,
            updated_at=now,
            frozen_at=now,
        )

        assert metadata.id == "ART-00002"
        assert metadata.type == ArtifactType.CONTRACT
        assert metadata.category == "frozen_prd"
        assert metadata.status == ArtifactStatus.FROZEN
        assert metadata.adopt_mode == AdoptMode.COPY
        assert metadata.run_id == "test-run-123"
        assert metadata.workflow_id == "wf-456"
        assert metadata.department == "pm"
        assert "ART-00001" in metadata.depends_on
        assert metadata.derived_from == "ART-00000"
        assert "backend" in metadata.consumed_by
        assert metadata.title == "Test PRD"
        assert metadata.size_bytes == 1024

    def test_to_dict(self):
        """测试序列化为字典"""
        metadata = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            title="Test",
        )

        data = metadata.to_dict()

        assert data["id"] == "ART-00001"
        assert data["type"] == "DOCUMENT"
        assert data["category"] == "readme"
        assert data["status"] == "ACTIVE"
        assert data["path"] == "active/test.md"
        assert data["path_root"] == ".artifacts"
        assert data["title"] == "Test"
        assert "created_at" in data
        assert "updated_at" in data

    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "id": "ART-00001",
            "type": "DOCUMENT",
            "category": "readme",
            "status": "ACTIVE",
            "path": "active/test.md",
            "title": "Test",
            "description": "Test desc",
            "tags": ["test"],
            "created_at": "2026-02-27T00:00:00",
            "updated_at": "2026-02-27T00:00:00",
        }

        metadata = ArtifactMetadata.from_dict(data)

        assert metadata.id == "ART-00001"
        assert metadata.type == ArtifactType.DOCUMENT
        assert metadata.category == "readme"
        assert metadata.status == ArtifactStatus.ACTIVE
        assert metadata.title == "Test"
        assert metadata.description == "Test desc"
        assert metadata.tags == ["test"]

    def test_roundtrip_serialization(self):
        """测试序列化往返"""
        original = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.TEST,
            category="test_report",
            status=ArtifactStatus.ACTIVE,
            path="active/qa/test/ART-00001.md",
            run_id="test-run",
            department="qa",
            title="Test Report",
            tags=["test", "report"],
        )

        # 序列化
        data = original.to_dict()
        # 反序列化
        restored = ArtifactMetadata.from_dict(data)

        assert restored.id == original.id
        assert restored.type == original.type
        assert restored.category == original.category
        assert restored.status == original.status
        assert restored.path == original.path
        assert restored.run_id == original.run_id
        assert restored.department == original.department
        assert restored.title == original.title
        assert restored.tags == original.tags
        assert restored.path_root == ".artifacts"

    def test_absolute_path_uses_project_root_for_project_scoped_file(self):
        """测试项目根作用域路径解析"""
        metadata = ArtifactMetadata(
            id="FEAT-001",
            type=ArtifactType.DOCUMENT,
            category="ssot_object",
            status=ArtifactStatus.ACTIVE,
            path="spec/requirements/features/FEAT-001__demo.md",
            path_root=".",
        )

        assert metadata.absolute_path == Path.cwd() / "spec/requirements/features/FEAT-001__demo.md"


class TestRunManifest:
    """测试 RunManifest 数据模型"""

    def test_create_minimal(self):
        """测试创建最小 manifest"""
        manifest = RunManifest(run_id="test-run-001")

        assert manifest.run_id == "test-run-001"
        assert manifest.status == "running"
        assert len(manifest.artifacts) == 0
        assert manifest.workflow_id is None
        assert manifest.department is None

    def test_create_full(self):
        """测试创建完整 manifest"""
        now = datetime.now()
        manifest = RunManifest(
            run_id="test-run-002",
            workflow_id="wf-123",
            department="pm",
            status="completed",
            executor="claude",
            executor_version="4.6",
            parent_run_id="parent-run",
            root_run_id="root-run",
            started_at=now,
            completed_at=now,
            input_artifacts=["ART-00001"],
            handover_to="qa",
            handover_artifacts=["ART-00002"],
        )

        assert manifest.run_id == "test-run-002"
        assert manifest.workflow_id == "wf-123"
        assert manifest.department == "pm"
        assert manifest.status == "completed"
        assert manifest.executor == "claude"
        assert manifest.executor_version == "4.6"
        assert manifest.parent_run_id == "parent-run"
        assert manifest.root_run_id == "root-run"
        assert "ART-00001" in manifest.input_artifacts
        assert manifest.handover_to == "qa"
        assert "ART-00002" in manifest.handover_artifacts

    def test_add_artifact(self):
        """测试添加产出物"""
        manifest = RunManifest(run_id="test-run")

        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
        )

        manifest.add_artifact(artifact)

        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].id == "ART-00001"

    def test_add_duplicate_artifact_raises(self):
        """测试添加重复产出物应抛出异常"""
        manifest = RunManifest(run_id="test-run")

        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
        )

        manifest.add_artifact(artifact)

        with pytest.raises(ValueError, match="already exists"):
            manifest.add_artifact(artifact)

    def test_get_artifact(self):
        """测试获取产出物"""
        manifest = RunManifest(run_id="test-run")

        artifact = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test.md",
            run_id="test-run",
        )

        manifest.add_artifact(artifact)

        retrieved = manifest.get_artifact("ART-00001")
        assert retrieved is not None
        assert retrieved.id == "ART-00001"

        not_found = manifest.get_artifact("ART-99999")
        assert not_found is None

    def test_get_artifacts_by_type(self):
        """测试按类型获取产出物"""
        manifest = RunManifest(run_id="test-run")

        manifest.add_artifact(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/doc1.md",
                run_id="test-run",
            )
        )
        manifest.add_artifact(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.DOCUMENT,
                category="usage_guide",
                status=ArtifactStatus.ACTIVE,
                path="active/doc2.md",
                run_id="test-run",
            )
        )
        manifest.add_artifact(
            ArtifactMetadata(
                id="ART-00003",
                type=ArtifactType.TEST,
                category="test_report",
                status=ArtifactStatus.ACTIVE,
                path="active/test.md",
                run_id="test-run",
            )
        )

        docs = manifest.get_artifacts_by_type(ArtifactType.DOCUMENT)
        assert len(docs) == 2
        assert all(a.type == ArtifactType.DOCUMENT for a in docs)

        tests = manifest.get_artifacts_by_type(ArtifactType.TEST)
        assert len(tests) == 1

    def test_get_artifacts_by_category(self):
        """测试按类别获取产出物"""
        manifest = RunManifest(run_id="test-run")

        manifest.add_artifact(
            ArtifactMetadata(
                id="ART-00001",
                type=ArtifactType.DOCUMENT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/readme.md",
                run_id="test-run",
            )
        )
        manifest.add_artifact(
            ArtifactMetadata(
                id="ART-00002",
                type=ArtifactType.CONTRACT,
                category="readme",
                status=ArtifactStatus.ACTIVE,
                path="active/contract.md",
                run_id="test-run",
            )
        )

        # 这里按实际类别获取，跨类型
        readmes = manifest.get_artifacts_by_category("readme")
        assert len(readmes) == 2
        assert all(a.category == "readme" for a in readmes)

    def test_to_dict(self):
        """测试序列化为字典"""
        manifest = RunManifest(
            run_id="test-run",
            department="pm",
            status="running",
        )

        data = manifest.to_dict()

        assert data["run_id"] == "test-run"
        assert data["department"] == "pm"
        assert data["status"] == "running"
        assert "artifacts" in data
        assert "started_at" in data

    def test_from_dict(self):
        """测试从字典反序列化"""
        data = {
            "run_id": "test-run",
            "workflow_id": "wf-123",
            "department": "pm",
            "status": "completed",
            "artifacts": [],
            "started_at": "2026-02-27T00:00:00",
            "completed_at": "2026-02-27T01:00:00",
        }

        manifest = RunManifest.from_dict(data)

        assert manifest.run_id == "test-run"
        assert manifest.workflow_id == "wf-123"
        assert manifest.department == "pm"
        assert manifest.status == "completed"

    def test_yaml_serialization(self):
        """测试 YAML 序列化"""
        manifest = RunManifest(
            run_id="test-run",
            department="pm",
            status="running",
        )

        yaml_str = manifest.to_yaml()
        assert "test-run" in yaml_str
        assert "pm" in yaml_str
        assert "running" in yaml_str

        # 反序列化
        restored = RunManifest.from_yaml(yaml_str)
        assert restored.run_id == "test-run"
        assert restored.department == "pm"
        assert restored.status == "running"
