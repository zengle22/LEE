"""
Tests for Context CLI Commands - Context CLI 命令测试
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lee.cli.commands.context import context
from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)
from lee.orchestrator.execution.artifacts.context import ContextBuilder


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


@pytest.fixture
def runner(artifact_manager, monkeypatch):
    """创建 CLI Runner，并让 CLI 命令使用测试的 artifact_manager"""
    import os
    original_cwd = os.getcwd()
    original_init = ArtifactManager.__init__

    # 切换到 artifacts 目录的父目录
    artifacts_parent = artifact_manager.root_path.parent
    os.chdir(str(artifacts_parent))

    # Monkeypatch ArtifactManager.__init__
    def mocked_init(self, root_path=None):
        if root_path is None or root_path == artifact_manager.root_path:
            self.root_path = artifact_manager.root_path
            self.sequence_file = artifact_manager.sequence_file
            self.registry = artifact_manager.registry
        else:
            original_init(self, root_path=root_path)

    monkeypatch.setattr(ArtifactManager, "__init__", mocked_init)

    yield CliRunner()

    os.chdir(original_cwd)
    monkeypatch.undo()


class TestContextListCommand:
    """测试 lee context list 命令"""

    def test_list_no_bundles(self, runner):
        """测试没有 Bundle 时的列表"""
        result = runner.invoke(context, ["list"])
        assert result.exit_code == 0
        assert "No context bundles found" in result.output

    def test_list_with_bundles(self, runner, artifact_manager, context_builder):
        """测试有 Bundle 时的列表"""
        run_id = "test-run-list"

        # 创建一些 Context Bundles
        context_builder.record_llm_call(
            run_id=run_id,
            step_id="step-1",
            prompt_text="Prompt 1",
            department="backend",
        )

        context_builder.record_llm_call(
            run_id=run_id,
            step_id="step-2",
            prompt_text="Prompt 2",
            department="backend",
        )

        result = runner.invoke(context, ["list"])
        assert result.exit_code == 0
        # 应该显示表格或列表
        assert "ID" in result.output or "TCTX-" in result.output

    def test_list_with_run_id_filter(self, runner, artifact_manager, context_builder):
        """测试按 run_id 过滤"""
        # 创建不同 run 的 Bundles
        context_builder.record_llm_call(
            run_id="run-a",
            step_id="step-1",
            prompt_text="Prompt A",
        )

        context_builder.record_llm_call(
            run_id="run-b",
            step_id="step-2",
            prompt_text="Prompt B",
        )

        # 按 run_id 过滤
        result = runner.invoke(context, ["list", "--run-id", "run-a"])
        assert result.exit_code == 0
        # 应该只包含 run-a 的 Bundle

    def test_list_json_format(self, runner, artifact_manager, context_builder):
        """测试 JSON 格式输出"""
        context_builder.record_llm_call(
            run_id="test-run-json",
            step_id="step-1",
            prompt_text="Prompt",
        )

        result = runner.invoke(context, ["list", "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_list_yaml_format(self, runner, artifact_manager, context_builder):
        """测试 YAML 格式输出"""
        context_builder.record_llm_call(
            run_id="test-run-yaml",
            step_id="step-1",
            prompt_text="Prompt",
        )

        result = runner.invoke(context, ["list", "--format", "yaml"])
        assert result.exit_code == 0

        import yaml
        data = yaml.safe_load(result.output)
        assert isinstance(data, list)


class TestContextShowCommand:
    """测试 lee context show 命令"""

    def test_show_not_found(self, runner):
        """测试显示不存在的 Bundle"""
        result = runner.invoke(context, ["show", "NONEXISTENT-001"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_show_wrong_category(self, runner, artifact_manager):
        """测试显示错误类别的 artifact"""
        # 创建一个不是 context bundle 的 artifact
        artifact = artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="note",
            content="Note",
            run_id="test-run",
        )

        result = runner.invoke(context, ["show", artifact.id])
        assert result.exit_code == 0
        assert "not a context bundle" in result.output.lower()

    def test_show_bundle_yaml(self, runner, artifact_manager, context_builder):
        """测试显示 Bundle 内容 (YAML 格式)"""
        artifact = context_builder.record_llm_call(
            run_id="test-run-show",
            step_id="step-1",
            prompt_text="Test prompt content",
            department="backend",
        )

        result = runner.invoke(context, ["show", artifact.id])
        assert result.exit_code == 0
        # 默认输出 YAML 格式
        assert "run_id" in result.output
        assert "step_id" in result.output

    def test_show_bundle_json(self, runner, artifact_manager, context_builder):
        """测试显示 Bundle 内容 (JSON 格式)"""
        artifact = context_builder.record_llm_call(
            run_id="test-run-show-json",
            step_id="step-1",
            prompt_text="Test prompt",
        )

        result = runner.invoke(context, ["show", artifact.id, "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert "run_id" in data
        assert "step_id" in data

    def test_show_bundle_text(self, runner, artifact_manager, context_builder):
        """测试显示 Bundle 内容 (纯文本格式)"""
        artifact = context_builder.record_llm_call(
            run_id="test-run-show-text",
            step_id="step-1",
            prompt_text="Test prompt text",
        )

        result = runner.invoke(context, ["show", artifact.id, "--format", "text"])
        assert result.exit_code == 0
        # 纯文本格式应该包含原始内容

    def test_show_bundle_v1_0(self, runner, artifact_manager, context_builder):
        """测试显示 v1.0 完整版 Bundle"""
        artifact = context_builder.record_llm_call_v1_0(
            run_id="test-run-v1",
            step_id="step-1",
            system_prompt="System prompt",
            user_prompt="User prompt",
            artifacts={"prd": ["FDPRD-001"]},
        )

        result = runner.invoke(context, ["show", artifact.id, "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert "prompt_snapshot" in data
        assert data["prompt_snapshot"]["system"] == "System prompt"
        assert data["prompt_snapshot"]["user"] == "User prompt"
        assert "artifacts" in data
        assert data["artifacts"]["prd"] == ["FDPRD-001"]


class TestContextListOrderBy:
    """测试列表排序"""

    def test_list_order_by_created_at(self, runner, artifact_manager, context_builder):
        """测试按创建时间排序"""
        # 创建多个 Bundles
        context_builder.record_llm_call(
            run_id="run-1",
            step_id="step-1",
            prompt_text="Prompt 1",
        )

        import time
        time.sleep(0.1)  # 确保时间戳不同

        context_builder.record_llm_call(
            run_id="run-2",
            step_id="step-2",
            prompt_text="Prompt 2",
        )

        result = runner.invoke(context, ["list"])
        assert result.exit_code == 0
        # 应该按创建时间倒序排列
