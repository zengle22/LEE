"""
Tests for Context Builder - Context Bundle 单元测试
"""

import shutil
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)
from lee.orchestrator.execution.artifacts.context import (
    TaskContextBundle,
    ContextBuilder,
    PromptSnapshot,
)


@pytest.fixture
def temp_artifacts_dir():
    """创建临时 artifacts 目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def artifact_manager(temp_artifacts_dir):
    """创建 ArtifactManager 实例"""
    manager = ArtifactManager(root_path=temp_artifacts_dir)
    yield manager


@pytest.fixture
def context_builder(artifact_manager):
    """创建 ContextBuilder 实例"""
    return ContextBuilder(artifact_manager)


class TestPromptSnapshot:
    """测试 PromptSnapshot 类"""

    def test_prompt_snapshot_creation(self):
        """测试 PromptSnapshot 创建"""
        snapshot = PromptSnapshot(
            system="You are a helpful assistant.",
            user="Hello, world!",
        )

        assert snapshot.system == "You are a helpful assistant."
        assert snapshot.user == "Hello, world!"

    def test_prompt_snapshot_to_dict(self):
        """测试 PromptSnapshot 转换为字典"""
        snapshot = PromptSnapshot(
            system="System prompt",
            user="User prompt",
        )

        result = snapshot.to_dict()

        assert result == {
            "system": "System prompt",
            "user": "User prompt",
        }

    def test_prompt_snapshot_default_values(self):
        """测试 PromptSnapshot 默认值"""
        snapshot = PromptSnapshot()

        assert snapshot.system == ""
        assert snapshot.user == ""


class TestTaskContextBundle:
    """测试 TaskContextBundle 类"""

    def test_bundle_v1_0_creation(self):
        """测试 v1.0 完整版 Bundle 创建"""
        prompt_snapshot = PromptSnapshot(system="System", user="User")
        artifacts = {"prd": ["FDPRD-001"], "api_contracts": ["API-001"]}
        config = {"max_artifacts": 50, "max_tokens": 10000}

        bundle = TaskContextBundle(
            id="TCTX-001",
            run_id="RUN-001",
            step_id="step-1",
            llm_call_id="CALL-001",
            artifacts=artifacts,
            prompt_snapshot=prompt_snapshot,
            config=config,
        )

        assert bundle.id == "TCTX-001"
        assert bundle.run_id == "RUN-001"
        assert bundle.artifacts == artifacts
        assert bundle.prompt_snapshot.system == "System"
        assert bundle.prompt_snapshot.user == "User"
        assert bundle.config == config

    def test_bundle_v0_9_compatibility(self):
        """测试 v0.9 兼容模式 (仅 prompt_text)"""
        bundle = TaskContextBundle(
            id="TCTX-002",
            run_id="RUN-001",
            step_id="step-1",
            llm_call_id="CALL-001",
            prompt_text="Combined prompt text",
        )

        # __post_init__ 应该自动创建 prompt_snapshot
        assert bundle.prompt_snapshot is not None
        assert bundle.prompt_snapshot.user == "Combined prompt text"
        assert bundle.prompt_snapshot.system == ""

    def test_bundle_to_dict_v1_0(self):
        """测试 v1.0 格式转换为字典"""
        prompt_snapshot = PromptSnapshot(system="System", user="User")
        artifacts = {"prd": ["FDPRD-001"]}

        bundle = TaskContextBundle(
            id="TCTX-003",
            run_id="RUN-001",
            step_id="step-1",
            llm_call_id="CALL-001",
            artifacts=artifacts,
            prompt_snapshot=prompt_snapshot,
        )

        result = bundle.to_dict()

        assert result["id"] == "TCTX-003"
        assert result["run_id"] == "RUN-001"
        assert result["artifacts"] == artifacts
        assert result["prompt_snapshot"] == {"system": "System", "user": "User"}
        assert "prompt_text" not in result  # v1.0 不应该有 prompt_text

    def test_bundle_to_dict_v0_9(self):
        """测试 v0.9 格式转换为字典"""
        bundle = TaskContextBundle(
            id="TCTX-004",
            run_id="RUN-001",
            step_id="step-1",
            llm_call_id="CALL-001",
            prompt_text="Combined prompt",
        )

        result = bundle.to_dict()

        assert result["id"] == "TCTX-004"
        assert result["prompt_text"] == "Combined prompt"
        assert "prompt_snapshot" in result  # 从 prompt_text 自动转换

    def test_bundle_auto_created_at(self):
        """测试 created_at 自动创建"""
        bundle = TaskContextBundle(
            id="TCTX-005",
            run_id="RUN-001",
            step_id="step-1",
            llm_call_id="CALL-001",
        )

        assert bundle.created_at is not None
        assert isinstance(bundle.created_at, datetime)


class TestContextBuilder:
    """测试 ContextBuilder 类"""

    def test_build_v1_0(self, context_builder):
        """测试构建 v1.0 完整版 Bundle"""
        bundle = context_builder.build_v1_0(
            run_id="RUN-001",
            step_id="step-1",
            system_prompt="System prompt",
            user_prompt="User prompt",
            artifacts={"prd": ["FDPRD-001"]},
            config={"max_artifacts": 50},
        )

        assert bundle.run_id == "RUN-001"
        assert bundle.step_id == "step-1"
        assert bundle.prompt_snapshot is not None
        assert bundle.prompt_snapshot.system == "System prompt"
        assert bundle.prompt_snapshot.user == "User prompt"
        assert bundle.artifacts == {"prd": ["FDPRD-001"]}
        assert bundle.config == {"max_artifacts": 50}

    def test_build_v0_9(self, context_builder):
        """测试构建 v0.9 简化版 Bundle"""
        bundle = context_builder.build_v0_9(
            run_id="RUN-002",
            step_id="step-2",
            prompt_text="Combined prompt text",
        )

        assert bundle.run_id == "RUN-002"
        assert bundle.step_id == "step-2"
        assert bundle.prompt_text == "Combined prompt text"
        # v0.9 也应该有自动生成的 prompt_snapshot
        assert bundle.prompt_snapshot is not None
        assert bundle.prompt_snapshot.user == "Combined prompt text"

    def test_build_v1_0_auto_generates_ids(self, context_builder):
        """测试 v1.0 自动生成 ID"""
        bundle = context_builder.build_v1_0(
            run_id="RUN-003",
            step_id="step-3",
            system_prompt="System",
            user_prompt="User",
        )

        assert bundle.id.startswith("TCTX-")
        assert bundle.llm_call_id.startswith("CALL-")

    def test_build_v0_9_auto_generates_ids(self, context_builder):
        """测试 v0.9 自动生成 ID"""
        bundle = context_builder.build_v0_9(
            run_id="RUN-004",
            step_id="step-4",
            prompt_text="Prompt",
        )

        assert bundle.id.startswith("TCTX-")
        assert bundle.llm_call_id.startswith("CALL-")

    def test_save_bundle_creates_artifact(self, context_builder, artifact_manager):
        """测试保存 Bundle 创建 artifact"""
        bundle = context_builder.build_v1_0(
            run_id="RUN-005",
            step_id="step-5",
            system_prompt="System",
            user_prompt="User",
            artifacts={"prd": ["FDPRD-001"]},
        )

        artifact = context_builder.save_bundle(
            bundle=bundle,
            department="test",
            workflow_id="wf-test",
        )

        assert artifact is not None
        assert artifact.category == "task_context_bundle"
        assert artifact.governance_kind == GovernanceKind.EVIDENCE
        assert artifact.run_id == "RUN-005"

        # 验证文件内容
        content_path = artifact_manager.root_path / artifact.path
        assert content_path.exists()

        content = yaml.safe_load(content_path.read_text(encoding="utf-8"))
        assert content["id"] == bundle.id
        assert content["prompt_snapshot"]["system"] == "System"
        assert content["prompt_snapshot"]["user"] == "User"
        assert content["artifacts"]["prd"] == ["FDPRD-001"]

    def test_record_llm_call_v0_9(self, context_builder, artifact_manager):
        """测试记录 LLM 调用 (v0.9 兼容模式)"""
        artifact = context_builder.record_llm_call(
            run_id="RUN-006",
            step_id="step-6",
            prompt_text="Combined prompt",
            department="test",
        )

        assert artifact is not None
        assert artifact.category == "task_context_bundle"

        # 验证内容
        content_path = artifact_manager.root_path / artifact.path
        content = yaml.safe_load(content_path.read_text(encoding="utf-8"))
        assert content["prompt_text"] == "Combined prompt"

    def test_record_llm_call_v1_0(self, context_builder, artifact_manager):
        """测试记录 LLM 调用 (v1.0 完整版)"""
        artifact = context_builder.record_llm_call_v1_0(
            run_id="RUN-007",
            step_id="step-7",
            system_prompt="System prompt",
            user_prompt="User prompt",
            artifacts={"api_contracts": ["API-001"]},
            department="test",
            config={"max_tokens": 5000},
        )

        assert artifact is not None
        assert artifact.category == "task_context_bundle"

        # 验证内容
        content_path = artifact_manager.root_path / artifact.path
        content = yaml.safe_load(content_path.read_text(encoding="utf-8"))
        assert content["prompt_snapshot"]["system"] == "System prompt"
        assert content["prompt_snapshot"]["user"] == "User prompt"
        assert content["artifacts"]["api_contracts"] == ["API-001"]
        assert content["config"]["max_tokens"] == 5000


class TestTaskContextBundleConfig:
    """测试 Config 相关功能"""

    def test_bundle_with_config(self):
        """测试带配置的 Bundle"""
        config = {
            "max_artifacts": 100,
            "max_tokens": 20000,
            "max_size_bytes": 50000,
        }

        bundle = TaskContextBundle(
            id="TCTX-010",
            run_id="RUN-010",
            step_id="step-10",
            llm_call_id="CALL-010",
            config=config,
        )

        result = bundle.to_dict()
        assert result["config"] == config

    def test_bundle_empty_config(self):
        """测试空配置的 Bundle"""
        bundle = TaskContextBundle(
            id="TCTX-011",
            run_id="RUN-011",
            step_id="step-11",
            llm_call_id="CALL-011",
        )

        result = bundle.to_dict()
        # 空配置不应该出现在输出中
        assert "config" not in result or result.get("config") == {}


class TestContextBundleEdgeCases:
    """测试边界情况"""

    def test_bundle_with_empty_artifacts(self):
        """测试空 artifacts 列表的 Bundle"""
        bundle = TaskContextBundle(
            id="TCTX-020",
            run_id="RUN-020",
            step_id="step-20",
            llm_call_id="CALL-020",
            artifacts={},
        )

        result = bundle.to_dict()
        # 空 artifacts 不应该出现在输出中
        assert "artifacts" not in result

    def test_bundle_with_nested_artifacts(self):
        """测试嵌套 artifacts 结构的 Bundle"""
        artifacts = {
            "prd": ["FDPRD-001", "FDPRD-002"],
            "api_contracts": ["API-001"],
            "code_snippets": ["ART-123", "ART-124"],
            "bug_reports": ["BUG-001"],
        }

        bundle = TaskContextBundle(
            id="TCTX-021",
            run_id="RUN-021",
            step_id="step-21",
            llm_call_id="CALL-021",
            artifacts=artifacts,
        )

        result = bundle.to_dict()
        assert result["artifacts"] == artifacts
        assert len(result["artifacts"]["prd"]) == 2
        assert len(result["artifacts"]["code_snippets"]) == 2
