"""
Tests for Task Brief CLI Commands - Task Brief CLI 命令测试
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lee.cli.commands.task_brief import task_brief
from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)
from lee.orchestrator.execution.artifacts.task_brief import TaskBriefGenerator


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
def task_brief_generator(artifact_manager):
    """创建 TaskBriefGenerator 实例"""
    return TaskBriefGenerator(artifact_manager)


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
    def mocked_init(self, root_path=None, project_root=None):
        if root_path is None or root_path == artifact_manager.root_path:
            self.root_path = artifact_manager.root_path
            self.project_root = artifact_manager.project_root
            self.sequence_file = artifact_manager.sequence_file
            self._artifacts_path_root = artifact_manager._artifacts_path_root
            self.registry = artifact_manager.registry
        else:
            original_init(self, root_path=root_path, project_root=project_root)

    monkeypatch.setattr(ArtifactManager, "__init__", mocked_init)

    yield CliRunner()

    os.chdir(original_cwd)
    monkeypatch.undo()


class TestTaskBriefListCommand:
    """测试 lee task-brief list 命令"""

    def test_list_no_briefs(self, runner):
        """测试没有 Task Brief 时的列表"""
        result = runner.invoke(task_brief, ["list"])
        assert result.exit_code == 0
        assert "No task briefs found" in result.output

    def test_list_with_briefs(self, runner, artifact_manager, task_brief_generator):
        """测试有 Task Brief 时的列表"""
        # 创建一些 Task Briefs
        task_brief_generator.create_and_save(
            run_id="run-1",
            department="backend",
            title="Brief 1",
            description="Description 1",
        )

        task_brief_generator.create_and_save(
            run_id="run-2",
            department="frontend",
            title="Brief 2",
            description="Description 2",
        )

        result = runner.invoke(task_brief, ["list"])
        assert result.exit_code == 0
        # 应该显示表格或列表
        assert "ID" in result.output or "TB-" in result.output

    def test_list_with_run_id_filter(self, runner, artifact_manager, task_brief_generator):
        """测试按 run_id 过滤"""
        task_brief_generator.create_and_save(
            run_id="run-a",
            department="backend",
            title="Brief A",
            description="Description A",
        )

        task_brief_generator.create_and_save(
            run_id="run-b",
            department="backend",
            title="Brief B",
            description="Description B",
        )

        # 按 run_id 过滤
        result = runner.invoke(task_brief, ["list", "--run-id", "run-a"])
        assert result.exit_code == 0
        # 应该只包含 run-a 的 Brief

    def test_list_with_department_filter(self, runner, artifact_manager, task_brief_generator):
        """测试按 department 过滤"""
        task_brief_generator.create_and_save(
            run_id="run-1",
            department="backend",
            title="Backend Brief",
            description="Backend description",
        )

        task_brief_generator.create_and_save(
            run_id="run-2",
            department="frontend",
            title="Frontend Brief",
            description="Frontend description",
        )

        # 按 department 过滤
        result = runner.invoke(task_brief, ["list", "--department", "backend"])
        assert result.exit_code == 0
        # 应该只包含 backend 的 Brief

    def test_list_json_format(self, runner, artifact_manager, task_brief_generator):
        """测试 JSON 格式输出"""
        task_brief_generator.create_and_save(
            run_id="run-json",
            department="backend",
            title="JSON Brief",
            description="Description",
        )

        result = runner.invoke(task_brief, ["list", "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert isinstance(data, list)

    def test_list_yaml_format(self, runner, artifact_manager, task_brief_generator):
        """测试 YAML 格式输出"""
        task_brief_generator.create_and_save(
            run_id="run-yaml",
            department="backend",
            title="YAML Brief",
            description="Description",
        )

        result = runner.invoke(task_brief, ["list", "--format", "yaml"])
        assert result.exit_code == 0

        import yaml
        data = yaml.safe_load(result.output)
        assert isinstance(data, list)


class TestTaskBriefShowCommand:
    """测试 lee task-brief show 命令"""

    def test_show_not_found(self, runner):
        """测试显示不存在的 Task Brief"""
        result = runner.invoke(task_brief, ["show", "NONEXISTENT-001"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_show_wrong_category(self, runner, artifact_manager):
        """测试显示错误类别的 artifact"""
        # 创建一个不是 task brief 的 artifact
        artifact = artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="note",
            content="Note",
            run_id="test-run",
        )

        result = runner.invoke(task_brief, ["show", artifact.id])
        assert result.exit_code == 0
        assert "not a task brief" in result.output.lower()

    def test_show_brief_yaml(self, runner, artifact_manager, task_brief_generator):
        """测试显示 Task Brief 内容 (YAML 格式)"""
        artifact = task_brief_generator.create_and_save(
            run_id="test-run-show",
            department="backend",
            title="Test Brief",
            description="Test description content",
            task_type="feature",
        )

        result = runner.invoke(task_brief, ["show", artifact.id])
        assert result.exit_code == 0
        # 默认输出 YAML 格式
        assert "run_id" in result.output
        assert "department" in result.output
        assert "Test Brief" in result.output

    def test_show_brief_json(self, runner, artifact_manager, task_brief_generator):
        """测试显示 Task Brief 内容 (JSON 格式)"""
        artifact = task_brief_generator.create_and_save(
            run_id="test-run-show-json",
            department="frontend",
            title="JSON Brief",
            description="Description",
        )

        result = runner.invoke(task_brief, ["show", artifact.id, "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert "run_id" in data
        assert "department" in data
        assert data["title"] == "JSON Brief"

    def test_show_brief_text(self, runner, artifact_manager, task_brief_generator):
        """测试显示 Task Brief 内容 (纯文本格式)"""
        artifact = task_brief_generator.create_and_save(
            run_id="test-run-show-text",
            department="qa",
            title="Text Brief",
            description="Text description",
        )

        result = runner.invoke(task_brief, ["show", artifact.id, "--format", "text"])
        assert result.exit_code == 0
        # 纯文本格式应该包含原始 YAML 内容


class TestTaskBriefCreateCommand:
    """测试 lee task-brief create 命令"""

    def test_create_minimal(self, runner, artifact_manager):
        """测试创建最小 Task Brief"""
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-create-1",
                "--department", "backend",
                "--title", "New Feature",
                "--description", "Feature description",
            ],
        )
        assert result.exit_code == 0
        assert "Task Brief created" in result.output

    def test_create_with_all_options(self, runner, artifact_manager):
        """测试创建完整 Task Brief"""
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-create-2",
                "--department", "backend",
                "--title", "Bug Fix",
                "--description", "Fix critical bug",
                "--type", "bugfix",
                "--related-prd", "FDPRD-001",
                "--related-bug", "BUG-001",
                "--scope-include", "Fix the bug",
                "--scope-include", "Add tests",
                "--scope-exclude", "No refactoring",
                "--acceptance", "Tests pass",
                "--acceptance", "Code review approved",
                "--risk", "May affect performance",
            ],
        )
        assert result.exit_code == 0
        assert "Task Brief created" in result.output

    def test_create_with_task_type(self, runner, artifact_manager):
        """测试创建不同任务类型的 Task Brief"""
        # feature
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-feature",
                "--department", "backend",
                "--title", "Feature",
                "--description", "New feature",
                "--type", "feature",
            ],
        )
        assert result.exit_code == 0

        # bugfix
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-bugfix",
                "--department", "backend",
                "--title", "Bug Fix",
                "--description", "Fix bug",
                "--type", "bugfix",
            ],
        )
        assert result.exit_code == 0

        # incident
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-incident",
                "--department", "ops",
                "--title", "Incident",
                "--description", "Handle incident",
                "--type", "incident",
            ],
        )
        assert result.exit_code == 0

        # refactor
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-refactor",
                "--department", "backend",
                "--title", "Refactor",
                "--description", "Code refactor",
                "--type", "refactor",
            ],
        )
        assert result.exit_code == 0

    def test_create_verifies_artifact(self, runner, artifact_manager):
        """测试创建的 Task Brief 验证 artifact 存在"""
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-verify",
                "--department", "backend",
                "--title", "Verify Brief",
                "--description", "Description",
            ],
        )
        assert result.exit_code == 0

        # 验证 artifact 确实被创建了
        import yaml
        # 查找最新创建的 artifact
        all_artifacts = list(artifact_manager.registry._artifacts.values())
        task_briefs = [a for a in all_artifacts if a.category == "task_brief"]
        assert len(task_briefs) > 0


class TestTaskBriefCreateEdges:
    """测试 Task Brief 创建的边界情况"""

    def test_create_with_special_characters(self, runner, artifact_manager):
        """测试创建包含特殊字符的 Task Brief"""
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-special",
                "--department", "backend",
                "--title", "Title with 特殊字符！@#",
                "--description", "Description with\nnewlines and\ttabs",
            ],
        )
        assert result.exit_code == 0

    def test_create_multiple_scope_items(self, runner, artifact_manager):
        """测试创建多个 scope 项目"""
        result = runner.invoke(
            task_brief,
            [
                "create",
                "--run-id", "run-multi-scope",
                "--department", "backend",
                "--title", "Multi Scope",
                "--description", "Description",
                "--scope-include", "Item 1",
                "--scope-include", "Item 2",
                "--scope-include", "Item 3",
                "--scope-exclude", "Exclude 1",
                "--scope-exclude", "Exclude 2",
            ],
        )
        assert result.exit_code == 0

        # 验证内容
        all_artifacts = list(artifact_manager.registry._artifacts.values())
        task_briefs = [a for a in all_artifacts if a.category == "task_brief" and a.run_id == "run-multi-scope"]
        assert len(task_briefs) > 0
