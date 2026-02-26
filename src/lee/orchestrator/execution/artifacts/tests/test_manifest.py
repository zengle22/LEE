"""
Tests for ManifestManager
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts.manager import ArtifactManager
from lee.orchestrator.execution.artifacts.manifest import ManifestManager
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
def manifest_manager(temp_artifacts_dir):
    """创建 ManifestManager 实例"""
    original_cwd = Path.cwd()
    os.chdir(temp_artifacts_dir.parent)

    manager = ManifestManager(temp_artifacts_dir)

    yield manager

    os.chdir(original_cwd)


@pytest.fixture
def artifact_manager(temp_artifacts_dir):
    """创建 ArtifactManager 实例"""
    original_cwd = Path.cwd()
    os.chdir(temp_artifacts_dir.parent)

    manager = ArtifactManager(temp_artifacts_dir)

    yield manager

    os.chdir(original_cwd)


class TestManifestManager:
    """测试 ManifestManager"""

    def test_create_manifest(self, manifest_manager, temp_artifacts_dir):
        """测试创建 manifest"""
        manifest = manifest_manager.create(
            run_id="test-run-001",
            workflow_id="wf-123",
            department="pm",
            executor="claude",
            executor_version="4.6",
        )

        assert manifest.run_id == "test-run-001"
        assert manifest.workflow_id == "wf-123"
        assert manifest.department == "pm"
        assert manifest.status == "running"
        assert manifest.executor == "claude"

        # 验证文件已创建
        manifest_path = manifest.manifest_path
        assert manifest_path.exists()

    def test_get_manifest(self, manifest_manager):
        """测试获取 manifest"""
        # 创建
        manifest_manager.create(
            run_id="test-run-002",
            department="qa",
        )

        # 获取
        retrieved = manifest_manager.get("test-run-002", "qa")

        assert retrieved is not None
        assert retrieved.run_id == "test-run-002"
        assert retrieved.department == "qa"

    def test_get_nonexistent_manifest(self, manifest_manager):
        """测试获取不存在的 manifest 返回 None"""
        result = manifest_manager.get("nonexistent-run")
        assert result is None

    def test_add_artifact_to_manifest(self, manifest_manager, artifact_manager):
        """测试向 manifest 添加产出物"""
        # 创建 manifest
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        # 创建产出物
        artifact = artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="# Test",
            run_id="test-run",
            department="pm",
        )

        # 添加到 manifest
        manifest_manager.add_artifact("test-run", artifact, "pm")

        # 验证
        manifest = manifest_manager.get("test-run", "pm")
        assert len(manifest.artifacts) == 1
        assert manifest.artifacts[0].id == artifact.id

    def test_update_status(self, manifest_manager):
        """测试更新状态"""
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        manifest_manager.update_status("test-run", "completed", "pm")

        manifest = manifest_manager.get("test-run", "pm")
        assert manifest.status == "completed"
        assert manifest.completed_at is not None

    def test_complete_run(self, manifest_manager):
        """测试标记 run 完成"""
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        manifest_manager.complete("test-run", "pm")

        manifest = manifest_manager.get("test-run", "pm")
        assert manifest.status == "completed"

    def test_fail_run(self, manifest_manager):
        """测试标记 run 失败"""
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        manifest_manager.fail("test-run", "pm")

        manifest = manifest_manager.get("test-run", "pm")
        assert manifest.status == "failed"

    def test_cancel_run(self, manifest_manager):
        """测试标记 run 取消"""
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        manifest_manager.cancel("test-run", "pm")

        manifest = manifest_manager.get("test-run", "pm")
        assert manifest.status == "cancelled"

    def test_list_runs(self, manifest_manager):
        """测试列出 runs"""
        # 创建多个 runs
        manifest_manager.create(run_id="run-001", department="pm")
        manifest_manager.create(run_id="run-002", department="qa")
        manifest_manager.create(run_id="run-003", department="pm")

        # 全部列出
        all_runs = manifest_manager.list_runs()
        assert len(all_runs) == 3

        # 按部门筛选
        pm_runs = manifest_manager.list_runs(department="pm")
        assert len(pm_runs) == 2
        assert all(r.department == "pm" for r in pm_runs)

        # 按状态筛选
        running_runs = manifest_manager.list_runs(status="running")
        assert len(running_runs) == 3

    def test_get_statistics(self, manifest_manager, artifact_manager):
        """测试获取统计信息"""
        # 创建 manifest
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        # 创建多个产出物
        artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="doc1",
            run_id="test-run",
            department="pm",
        )
        artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="usage_guide",
            content="doc2",
            run_id="test-run",
            department="pm",
        )
        artifact_manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_report",
            content="report",
            run_id="test-run",
            department="pm",
        )

        # 手动添加到 manifest
        manifest = manifest_manager.get("test-run", "pm")
        for artifact in artifact_manager.registry.get_by_run("test-run"):
            manifest.add_artifact(artifact)
        manifest_manager.save(manifest)

        # 获取统计
        stats = manifest_manager.get_statistics("test-run", "pm")

        assert stats["run_id"] == "test-run"
        assert stats["status"] == "running"
        assert stats["total_artifacts"] == 3
        assert stats["by_type"]["DOCUMENT"] == 2
        assert stats["by_type"]["TEST"] == 1

    def test_set_handover(self, manifest_manager):
        """测试设置移交"""
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        manifest_manager.set_handover(
            run_id="test-run",
            handover_to="qa",
            artifact_ids=["ART-00001", "ART-00002"],
            department="pm",
        )

        manifest = manifest_manager.get("test-run", "pm")
        assert manifest.handover_to == "qa"
        assert "ART-00001" in manifest.handover_artifacts
        assert "ART-00002" in manifest.handover_artifacts

    def test_get_handover_artifacts(self, manifest_manager):
        """测试获取移交产出物"""
        manifest_manager.create(
            run_id="test-run",
            department="pm",
        )

        # 添加一些产出物到 manifest
        manifest = manifest_manager.get("test-run", "pm")
        artifact1 = ArtifactMetadata(
            id="ART-00001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="active/test1.md",
            run_id="test-run",
        )
        artifact2 = ArtifactMetadata(
            id="ART-00002",
            type=ArtifactType.DOCUMENT,
            category="usage_guide",
            status=ArtifactStatus.ACTIVE,
            path="active/test2.md",
            run_id="test-run",
        )
        manifest.add_artifact(artifact1)
        manifest.add_artifact(artifact2)

        manifest.handover_to = "qa"
        manifest.handover_artifacts = ["ART-00001"]
        manifest_manager.save(manifest)

        # 获取移交产出物
        handover_artifacts = manifest_manager.get_handover_artifacts("test-run", "pm")

        assert len(handover_artifacts) == 1
        assert handover_artifacts[0].id == "ART-00001"
