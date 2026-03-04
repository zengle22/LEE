"""
QA Test Run SUT 集成测试

测试覆盖：
- test_run.py 中的 SUT URL 解析逻辑
- CLI 参数 --base-url 与环境配置的优先级
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner
import pytest
import yaml

from lee.cli.commands.qa.test_run import test_run


class TestTestRunSUTIntegration:
    """测试 test_run 命令的 SUT 集成"""

    def test_start_with_default_env(self, tmp_path):
        """测试使用默认环境时的 URL 解析"""
        runner = CliRunner()

        # 创建必要的目录和文件
        project_root = tmp_path / "project"
        project_root.mkdir()
        qa_dir = project_root / "qa" / "test-plans"
        qa_dir.mkdir(parents=True)

        # 创建 Test Plan 文件
        plan_file = qa_dir / "TP-TEST.yaml"
        plan_file.write_text(yaml.dump({
            "test_plan_id": "TP-TEST",
            "title": "Test Plan"
        }))

        with patch('lee.cli.commands.qa.test_run.pm_workflow') as mock_pm, \
             patch('lee.cli.commands.qa.test_run._render_workflow_template') as mock_render:
            mock_pm.return_value = {"workflow_id": "test-wf-123"}
            mock_render.return_value = Path("/tmp/test.yaml")

            # 不指定 --base-url，应该使用环境默认
            result = runner.invoke(test_run, [
                'start', 'TP-TEST',
                '--env', 'staging',
                '--project-dir', str(project_root)
            ])

            # 验证命令执行成功
            assert result.exit_code == 0
            # 验证输出包含解析的 URL
            assert "app-staging.example.com" in result.output

    def test_start_with_explicit_base_url(self, tmp_path):
        """测试显式指定 --base-url 参数"""
        runner = CliRunner()

        # 创建必要的目录和文件
        project_root = tmp_path / "project"
        project_root.mkdir()
        qa_dir = project_root / "qa" / "test-plans"
        qa_dir.mkdir(parents=True)

        plan_file = qa_dir / "TP-TEST.yaml"
        plan_file.write_text(yaml.dump({
            "test_plan_id": "TP-TEST",
            "title": "Test Plan"
        }))

        with patch('lee.cli.commands.qa.test_run.pm_workflow') as mock_pm, \
             patch('lee.cli.commands.qa.test_run._render_workflow_template') as mock_render:
            mock_pm.return_value = {"workflow_id": "test-wf-123"}
            mock_render.return_value = Path("/tmp/test.yaml")

            # 显式指定 --base-url
            result = runner.invoke(test_run, [
                'start', 'TP-TEST',
                '--env', 'staging',
                '--base-url', 'https://custom.example.com',
                '--project-dir', str(project_root)
            ])

            # 验证命令执行成功
            assert result.exit_code == 0
            # 验证输出包含显式指定的 URL
            assert "custom.example.com" in result.output

    def test_base_url_priority(self, tmp_path):
        """测试 base-url 优先级：CLI > 环境默认"""
        runner = CliRunner()

        # 创建必要的目录和文件
        project_root = tmp_path / "project"
        project_root.mkdir()
        qa_dir = project_root / "qa" / "test-plans"
        qa_dir.mkdir(parents=True)

        plan_file = qa_dir / "TP-TEST.yaml"
        plan_file.write_text(yaml.dump({
            "test_plan_id": "TP-TEST",
            "title": "Test Plan"
        }))

        with patch('lee.cli.commands.qa.test_run.pm_workflow') as mock_pm, \
             patch('lee.cli.commands.qa.test_run._render_workflow_template') as mock_render:
            mock_pm.return_value = {"workflow_id": "test-wf-123"}
            mock_render.return_value = Path("/tmp/test.yaml")

            # CLI --base-url 应该覆盖环境默认
            result = runner.invoke(test_run, [
                'start', 'TP-TEST',
                '--env', 'local',
                '--base-url', 'https://override.example.com',
                '--project-dir', str(project_root)
            ])

            # 验证显式指定的 URL 在输出中
            assert result.exit_code == 0
            assert "override.example.com" in result.output


class TestSUTURLResolution:
    """测试 SUT URL 解析逻辑（独立于 CLI）"""

    def test_resolve_sut_url_local(self):
        """测试 local 环境 URL 解析"""
        from lee.qa.runner import resolve_sut_url

        url = resolve_sut_url("local")
        assert url == "http://localhost:3000"

    def test_resolve_sut_url_staging(self):
        """测试 staging 环境 URL 解析"""
        from lee.qa.runner import resolve_sut_url

        url = resolve_sut_url("staging")
        assert url == "https://app-staging.example.com"

    def test_resolve_sut_url_with_explicit(self):
        """测试显式 URL 覆盖"""
        from lee.qa.runner import resolve_sut_url

        url = resolve_sut_url("staging", explicit_url="https://explicit.example.com")
        assert url == "https://explicit.example.com"

    def test_resolve_sut_url_unknown_env(self):
        """测试未知环境回退到默认"""
        from lee.qa.runner import resolve_sut_url

        url = resolve_sut_url("unknown-env")
        assert url == "http://localhost:3000"


class TestSUTConfigInTestConfig:
    """测试 TestConfig 中的 SUT 集成"""

    def test_test_config_with_sut_env(self):
        """TestConfig 使用 SUT 环境"""
        from lee.qa.runner import TestConfig, SUTType

        config = TestConfig(
            scripts=[],
            environment="staging"
        )
        # 应该自动解析为环境默认 URL
        assert config.base_url == "https://app-staging.example.com"

    def test_test_config_with_explicit_url(self):
        """TestConfig 显式 URL 优先于 SUT"""
        from lee.qa.runner import TestConfig

        config = TestConfig(
            scripts=[],
            environment="staging",
            base_url="https://explicit.example.com"
        )
        assert config.base_url == "https://explicit.example.com"

    def test_test_config_with_sut_config(self):
        """TestConfig 使用 SUTConfig 对象"""
        from lee.qa.runner import TestConfig, SUTConfig, SUTType

        sut = SUTConfig(
            sut_type=SUTType.WEB,
            base_url="https://from-sut.example.com"
        )
        config = TestConfig(
            scripts=[],
            sut_config=sut
        )
        assert config.base_url == "https://from-sut.example.com"


class TestSUTConfigLoader:
    """测试 SUT 配置加载"""

    def test_load_or_create_with_explicit_url(self, tmp_path):
        """测试显式 URL 时 load_or_create"""
        from lee.qa.runner import SUTConfigLoader

        loader = SUTConfigLoader(tmp_path)

        # 显式指定 URL
        config = loader.load_or_create("test-run-1", "staging",
                                        base_url="https://custom-staging.example.com")

        assert config.base_url == "https://custom-staging.example.com"
        assert config.name == "test-run-1-staging"

    def test_save_preserves_base_url(self, tmp_path):
        """测试保存后 base_url 正确"""
        from lee.qa.runner import SUTConfigLoader, SUTConfig, SUTType

        loader = SUTConfigLoader(tmp_path)

        config = SUTConfig(
            sut_type=SUTType.WEB,
            base_url="https://saved.example.com",
            name="test-config"
        )
        loader.save("test-run-1", config)

        # 重新加载
        loaded = loader.load("test-run-1")
        assert loaded is not None
        assert loaded.base_url == "https://saved.example.com"
