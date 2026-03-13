"""
Tests for SSOT CLI Commands - SSOT CLI 命令测试
"""

import shutil
import tempfile
from pathlib import Path

import pytest
import yaml
from click.testing import CliRunner

from lee.cli.commands.ssot import ssot
from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
    SSOTType,
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
def runner(artifact_manager, monkeypatch):
    """创建 CLI Runner，并让 CLI 命令使用测试的 artifact_manager"""
    import os
    # 保存原始 cwd 和原始的 ArtifactManager.__init__
    original_cwd = os.getcwd()
    original_init = ArtifactManager.__init__

    # 切换到 artifacts 目录的父目录，这样 CLI 会找到 .artifacts
    artifacts_parent = artifact_manager.root_path.parent
    os.chdir(str(artifacts_parent))

    # Monkeypatch ArtifactManager.__init__ 以使用测试的 manager
    def mocked_init(self, root_path=None):
        # 如果 root_path 相同，使用测试的 manager
        if root_path is None or root_path == artifact_manager.root_path:
            self.root_path = artifact_manager.root_path
            self.project_root = artifact_manager.project_root
            self.sequence_file = artifact_manager.sequence_file
            self._artifacts_path_root = artifact_manager._artifacts_path_root
            self.registry = artifact_manager.registry
        else:
            original_init(self, root_path=root_path)

    monkeypatch.setattr(ArtifactManager, "__init__", mocked_init)

    yield CliRunner()

    # 恢复原始 cwd 和 ArtifactManager.__init__
    os.chdir(original_cwd)
    monkeypatch.undo()


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


class TestSSOTCreateCommand:
    """测试 lee ssot create 命令"""

    def test_create_feat_with_epic_parent_passes_p0(self, runner, artifact_manager):
        src = artifact_manager.create_ssot(
            ssot_type="src",
            title="增长基础设施来源",
            content="# Source\n",
            run_id="test-run-create-feat-parent",
        )
        epic = artifact_manager.create_ssot(
            ssot_type="epic",
            title="增长基础设施",
            content="# Epic\n",
            run_id="test-run-create-feat-parent",
            parent_id=src.id,
            source_refs=[src.id],
        )

        feat_body = artifact_manager.project_root / "feat-body.md"
        feat_body.write_text("# 用户注册\n", encoding="utf-8")

        result = runner.invoke(
            ssot,
            [
                "create",
                "--type",
                "feat",
                "--title",
                "用户注册",
                "--content-file",
                str(feat_body),
                "--run-id",
                "test-run-create-feat-parent",
                "--status",
                "draft",
                "--version",
                "v1",
                "--parent-id",
                epic.id,
                "--source-ref",
                f"{src.id}#scope",
                "--source-ref",
                epic.id,
            ],
        )
        assert result.exit_code == 0
        assert "created FEAT-SRC-001-001" in result.output

        validate_result = runner.invoke(ssot, ["validate-p0", "FEAT-SRC-001-001"])
        assert validate_result.exit_code == 0
        assert "P0 validation passed for FEAT-SRC-001-001" in validate_result.output


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

        # 创建 PRD 和依赖它的 API，以便有 impact
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


class TestSSOTFormalizeCommand:
    def test_formalize_command_rewrites_ids(self, runner, artifact_manager):
        src = artifact_manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title="会员来源",
            content="# Source\n",
            run_id="run-cli-formalize-src",
        )
        legacy_epic = artifact_manager.project_root / "spec/requirements/epics/EPIC-001__huiyuanshishi.md"
        legacy_feat = artifact_manager.project_root / "spec/requirements/features/FEAT-001__huiyuannengli.md"
        legacy_epic.parent.mkdir(parents=True, exist_ok=True)
        legacy_feat.parent.mkdir(parents=True, exist_ok=True)
        legacy_epic.write_text(
            "---\n{}\n---\n\n# Epic\n".format(
                yaml.safe_dump(
                    {
                        "id": "EPIC-001",
                        "ssot_type": "epic",
                        "title": "会员史诗",
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
            "---\n{}\n---\n\n# Feature\n".format(
                yaml.safe_dump(
                    {
                        "id": "FEAT-001",
                        "ssot_type": "feat",
                        "title": "会员能力",
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
        artifact_manager.rebuild_ssot_registry()

        result = runner.invoke(ssot, ["formalize", "--id", "EPIC-001", "--id", "FEAT-001"])

        assert result.exit_code == 0
        assert "formalized 2 artifacts" in result.output
        assert f"EPIC-001 -> EPIC-{src.id}-" in result.output
