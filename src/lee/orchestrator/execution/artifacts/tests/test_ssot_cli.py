"""
Tests for SSOT CLI Commands - SSOT CLI 命令测试
"""

import shutil
import tempfile
from pathlib import Path

import pytest
from click.testing import CliRunner

from lee.cli.commands.ssot import ssot
from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)


@pytest.fixture
def temp_artifacts_dir():
    """创建临时 artifacts 目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def runner(temp_artifacts_dir):
    """创建 CLI Runner"""
    # 保存原始 cwd
    import os
    original_cwd = os.getcwd()
    # 切换到临时目录以便使用其 artifacts
    artifacts_parent = temp_artifacts_dir.parent
    os.chdir(str(artifacts_parent))

    yield CliRunner()

    # 恢复原始 cwd
    os.chdir(original_cwd)


@pytest.fixture
def artifact_manager(temp_artifacts_dir):
    """创建 ArtifactManager 实例"""
    manager = ArtifactManager(root_path=temp_artifacts_dir)
    yield manager


class TestSSOTValidateCommand:
    """测试 lee ssot validate 命令"""

    def test_validate_empty_artifacts(self, runner, artifact_manager):
        """测试空 artifacts 列表的校验"""
        result = runner.invoke(ssot, ["validate"])
        assert result.exit_code == 0
        assert "SSOT validation passed" in result.output

    def test_validate_with_run_id(self, runner, artifact_manager):
        """测试按 run_id 校验"""
        run_id = "test-run-cli-001"

        # 创建有效的真理链
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        result = runner.invoke(ssot, ["validate", "--run-id", run_id])
        assert result.exit_code == 0
        assert "SSOT validation passed" in result.output

    def test_validate_with_release_tag(self, runner, artifact_manager):
        """测试按 release tag 校验"""
        # 创建带 release tag 的 artifacts
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id="run-release",
            governance_kind=GovernanceKind.TRANSFER,
            tags=["release:v1.0"],
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id="run-release",
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
            tags=["release:v1.0"],
        )

        result = runner.invoke(ssot, ["validate", "--release", "release:v1.0"])
        assert result.exit_code == 0
        assert "SSOT validation passed" in result.output

    def test_validate_failure(self, runner, artifact_manager):
        """测试校验失败"""
        # 创建无效的 API (没有 derived_from)
        artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id="test-run-fail",
            governance_kind=GovernanceKind.TRANSFER,
        )

        result = runner.invoke(ssot, ["validate"])
        assert result.exit_code == 0
        assert "SSOT validation failed" in result.output
        assert "missing derived_from" in result.output

    def test_validate_with_enforce_flag(self, runner, artifact_manager):
        """测试 enforce 模式"""
        # 创建无效的 artifact
        artifact_manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code",
            run_id="test-run-enforce",
            governance_kind=GovernanceKind.DELIVERABLE,
        )

        result = runner.invoke(ssot, ["validate", "--enforce"])
        assert result.exit_code != 0  # enforce 模式应该退出码非零


class TestSSOTBuildIndexCommand:
    """测试 lee ssot build-index 命令"""

    def test_build_index_creates_file(self, runner, artifact_manager):
        """测试构建索引创建文件"""
        result = runner.invoke(ssot, ["build-index"])
        assert result.exit_code == 0
        assert "SSOT index built" in result.output

        # 验证索引文件存在
        index_path = artifact_manager.root_path / "trace" / "ssot-index.yaml"
        assert index_path.exists()

    def test_build_index_with_artifacts(self, runner, artifact_manager):
        """测试带 artifacts 的索引构建"""
        run_id = "test-run-index"

        # 创建一些 artifacts
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        result = runner.invoke(ssot, ["build-index"])
        assert result.exit_code == 0
        assert "Nodes:" in result.output
        assert "Edges:" in result.output

        # 验证索引内容
        import yaml
        index_path = artifact_manager.root_path / "trace" / "ssot-index.yaml"
        index_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

        assert "nodes" in index_data
        assert "edges" in index_data
        assert len(index_data["nodes"]) >= 2
        assert len(index_data["edges"]) >= 1  # 至少有 derived_from 边

    def test_build_index_with_release_filter(self, runner, artifact_manager):
        """测试按 release 过滤构建索引"""
        # 创建带 release tag 的 artifacts
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id="run-v1",
            governance_kind=GovernanceKind.TRANSFER,
            tags=["release:v1.0"],
        )

        # 创建不带 tag 的 artifacts
        other = artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="note",
            content="Note",
            run_id="run-other",
            governance_kind=GovernanceKind.KNOWLEDGE,
        )

        result = runner.invoke(ssot, ["build-index", "--release", "release:v1.0"])
        assert result.exit_code == 0

        # 验证索引只包含带 tag 的 artifacts
        import yaml
        index_path = artifact_manager.root_path / "trace" / "ssot-index.yaml"
        index_data = yaml.safe_load(index_path.read_text(encoding="utf-8"))

        node_ids = [n["id"] for n in index_data["nodes"]]
        assert prd.id in node_ids
        # other 不应该在索引中 (没有 release tag)

    def test_build_index_custom_output_path(self, runner, artifact_manager):
        """测试自定义输出路径"""
        import os
        custom_path = str(artifact_manager.root_path / "custom-index.yaml")

        result = runner.invoke(ssot, ["build-index", "-o", custom_path])
        assert result.exit_code == 0

        # 验证自定义路径文件存在
        assert Path(custom_path).exists()


class TestSSOTImpactCommand:
    """测试 lee ssot impact 命令"""

    def test_show_impact_with_dependents(self, runner, artifact_manager):
        """测试显示有依赖者的影响分析"""
        run_id = "test-run-impact"

        # 创建 PRD → API 链
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        result = runner.invoke(ssot, ["impact", prd.id])
        assert result.exit_code == 0
        assert "Impact analysis" in result.output
        assert api.id in result.output

    def test_show_impact_no_dependents(self, runner, artifact_manager):
        """测试显示没有依赖者的影响分析"""
        # 创建孤立的 artifact
        isolated = artifact_manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="note",
            content="Note",
            run_id="test-run-isolated",
            governance_kind=GovernanceKind.KNOWLEDGE,
        )

        result = runner.invoke(ssot, ["impact", isolated.id])
        assert result.exit_code == 0
        # 没有依赖者时输出应该显示 "No impact found" 或空列表

    def test_show_impact_json_format(self, runner, artifact_manager):
        """测试 JSON 格式输出"""
        run_id = "test-run-impact-json"

        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        result = runner.invoke(ssot, ["impact", prd.id, "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert "direct_dependents" in data
        assert "indirect_dependents" in data
        assert "verifiers" in data


class TestSSOTShowChainCommand:
    """测试 lee ssot show-chain 命令"""

    def test_show_chain_with_derived_from(self, runner, artifact_manager):
        """测试显示真理链"""
        run_id = "test-run-chain"

        # 创建 PRD → API 链
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        result = runner.invoke(ssot, ["show-chain", api.id])
        assert result.exit_code == 0
        assert "Truth chain" in result.output
        assert prd.id in result.output
        assert api.id in result.output

    def test_show_chain_not_found(self, runner, artifact_manager):
        """测试显示不存在的 chain"""
        result = runner.invoke(ssot, ["show-chain", "NONEXISTENT-001"])
        assert result.exit_code == 0
        assert "Chain not found" in result.output

    def test_show_chain_json_format(self, runner, artifact_manager):
        """测试 JSON 格式输出"""
        run_id = "test-run-chain-json"

        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        result = runner.invoke(ssot, ["show-chain", api.id, "--format", "json"])
        assert result.exit_code == 0

        import json
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 2  # PRD 和 API
