"""
Tests for artifact integration module
"""

import os
import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts.integration import (
    ArtifactFileOutputHandler,
    GateArtifactHandler,
    create_artifact_handler,
)
from lee.orchestrator.execution.artifacts.types import ArtifactType, ArtifactStatus


@pytest.fixture
def temp_project_dir():
    """创建临时项目目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def artifact_handler(temp_project_dir):
    """创建产出物处理器"""
    handler = ArtifactFileOutputHandler(
        project_root=temp_project_dir,
        run_id="test-run-001",
        workflow_id="test-wf",
        department="pm",
        enabled=True,
    )

    yield handler


@pytest.fixture
def gate_handler(temp_project_dir):
    """创建门禁处理器"""
    # 先创建一些产出物和 manifest
    from lee.orchestrator.execution.artifacts import (
        ArtifactManager,
        ArtifactFileOutputHandler,
    )

    # 创建产出物 handler (会自动创建 manifest)
    artifact_handler = ArtifactFileOutputHandler(
        project_root=temp_project_dir,
        run_id="test-run-001",
        department="pm",
        enabled=True,
    )

    # 创建一个测试产出物
    test_file = temp_project_dir / "readme.md"
    test_file.write_text("# Test Document")
    artifact_handler.register_file(str(test_file))

    handler = GateArtifactHandler(temp_project_dir)

    yield handler


class TestArtifactFileOutputHandler:
    """测试 ArtifactFileOutputHandler"""

    def test_init_creates_manifest(self, artifact_handler):
        """测试初始化创建 manifest"""
        manifest = artifact_handler.manifest_manager.get("test-run-001", "pm")
        assert manifest is not None
        assert manifest.run_id == "test-run-001"
        assert manifest.department == "pm"

    def test_disabled_handler_skips_registration(self, temp_project_dir):
        """测试禁用状态下跳过注册"""
        handler = ArtifactFileOutputHandler(
            project_root=temp_project_dir,
            run_id="test-run-002",
            enabled=False,
        )

        handler = ArtifactFileOutputHandler(
            project_root=temp_project_dir,
            run_id="test-run-002",
            enabled=False,
        )

        # 创建测试文件
        test_file = temp_project_dir / "test.md"
        test_file.write_text("# Test")

        # 注册应该被跳过
        result = handler.register_file(str(test_file))
        assert result is None

    def test_register_file_creates_artifact(self, artifact_handler, temp_project_dir):
        """测试注册文件创建产出物"""
        # 创建测试文件
        test_file = temp_project_dir / "readme.md"
        test_file.write_text("# Test Document\n\nThis is a test.")

        # 注册文件
        metadata = artifact_handler.register_file(str(test_file))

        assert metadata is not None
        assert metadata.type == ArtifactType.DOCUMENT
        assert metadata.category == "readme"
        assert metadata.run_id == "test-run-001"
        assert metadata.department == "pm"

    def test_register_file_with_content(self, artifact_handler, temp_project_dir):
        """测试使用提供的内容注册文件"""
        test_file = temp_project_dir / "test.md"
        test_file.write_text("original content")

        metadata = artifact_handler.register_file(
            str(test_file),
            content="override content",
            title="Custom Title",
            description="Custom Description",
            tags=["test", "custom"],
        )

        assert metadata is not None
        assert metadata.title == "Custom Title"
        assert metadata.description == "Custom Description"
        assert "test" in metadata.tags

    def test_register_file_infers_type(self, artifact_handler, temp_project_dir):
        """测试自动推断产出物类型"""
        # 契约类文件
        contract_file = temp_project_dir / "api-contract.yaml"
        contract_file.write_text("openapi: 3.0.0")
        contract_metadata = artifact_handler.register_file(str(contract_file))
        assert contract_metadata.type == ArtifactType.CONTRACT

        # 测试类文件
        test_file = temp_project_dir / "test-report.md"
        test_file.write_text("# Test Report")
        test_metadata = artifact_handler.register_file(str(test_file))
        assert test_metadata.type == ArtifactType.TEST

        # 文档类文件
        doc_file = temp_project_dir / "readme.md"
        doc_file.write_text("# README")
        doc_metadata = artifact_handler.register_file(str(doc_file))
        assert doc_metadata.type == ArtifactType.DOCUMENT

    def test_register_file_skip_duplicate(self, artifact_handler, temp_project_dir):
        """测试跳过重复注册"""
        test_file = temp_project_dir / "test.md"
        test_file.write_text("# Test")

        # 第一次注册
        first = artifact_handler.register_file(str(test_file))
        assert first is not None

        # 第二次注册应该被跳过
        second = artifact_handler.register_file(str(test_file))
        assert second is None

    def test_register_files_from_output(self, artifact_handler, temp_project_dir):
        """测试批量注册文件"""
        # 创建多个测试文件
        files = []
        for i in range(3):
            file_path = temp_project_dir / f"file{i}.md"
            file_path.write_text(f"# File {i}")
            files.append(str(file_path))

        # 批量注册
        artifacts = artifact_handler.register_files_from_output(
            written_files=files,
            titles={"files[0]": "First File"},
        )

        # 应该注册 3 个产出物
        assert len(artifacts) == 3

    def test_complete_run_updates_status(self, artifact_handler):
        """测试完成 run 更新状态"""
        artifact_handler.complete_run("completed")

        manifest = artifact_handler.manifest_manager.get("test-run-001", "pm")
        assert manifest.status == "completed"

    def test_get_run_artifacts(self, artifact_handler, temp_project_dir):
        """测试获取 run 产出物"""
        # 创建一些产出物
        for i in range(3):
            test_file = temp_project_dir / f"test{i}.md"
            test_file.write_text(f"# Test {i}")
            artifact_handler.register_file(str(test_file))

        # 获取产出物
        artifacts = artifact_handler.get_run_artifacts()

        assert len(artifacts) == 3

    def test_without_run_id_skips_operations(self, temp_project_dir):
        """测试没有 run_id 时跳过操作"""
        handler = ArtifactFileOutputHandler(
            project_root=temp_project_dir,
            run_id=None,
            enabled=True,
        )

        handler = ArtifactFileOutputHandler(
            project_root=temp_project_dir,
            run_id=None,
            enabled=True,
        )

        # 各种操作应该安全地返回空值
        assert handler.register_file("test.md") is None
        assert handler.get_run_artifacts() == []
        handler.complete_run()  # 不应抛出异常


class TestGateArtifactHandler:
    """测试 GateArtifactHandler"""

    def test_freeze_run_artifacts(self, gate_handler, temp_project_dir):
        """测试冻结 run 产出物"""
        frozen = gate_handler.freeze_run_artifacts("test-run-001", "pm")

        assert len(frozen) == 1
        assert frozen[0].status == ArtifactStatus.FROZEN
        assert frozen[0].path.startswith("frozen/")

    def test_approve_gate_artifacts(self, gate_handler, temp_project_dir):
        """测试门禁通过处理"""
        result = gate_handler.approve_gate_artifacts(
            run_id="test-run-001",
            gate_id="gate-001",
            department="pm",
        )

        assert result["frozen_count"] == 1
        assert len(result["frozen_artifacts"]) == 1

    def test_approve_gate_updates_manifest(self, gate_handler, temp_project_dir):
        """测试门禁通过更新 manifest"""
        gate_handler.approve_gate_artifacts(
            run_id="test-run-001",
            gate_id="gate-001",
            department="pm",
        )

        manifest = gate_handler.manifest_manager.get("test-run-001", "pm")
        assert manifest is not None
        assert "approved_gates" in manifest.properties


class TestCreateArtifactHandler:
    """测试工厂函数"""

    def test_create_artifact_handler(self, temp_project_dir):
        """测试创建产出物处理器"""
        handler = create_artifact_handler(
            run_id="test-run",
            workflow_id="test-wf",
            department="qa",
            project_root=temp_project_dir,
        )

        handler = create_artifact_handler(
            run_id="test-run",
            workflow_id="test-wf",
            department="qa",
            project_root=temp_project_dir,
        )

        assert handler.run_id == "test-run"
        assert handler.workflow_id == "test-wf"
        assert handler.department == "qa"
        assert handler.enabled is True
