"""
Tests for LEE ConfigLoader — M4 externalized configuration

Tests:
1. 默认配置（无文件）
2. 从字典构建
3. 从 YAML 文件加载
4. 环境变量覆盖
5. 部分配置合并
6. 配置文件不存在时的优雅降级
"""

import os
import tempfile
import pytest
from pathlib import Path

from lee.orchestrator.config_loader import (
    LeeConfig,
    RetryConfig,
    OnFailureConfig,
    ExecutorConfig,
    TracingConfig,
    EvidenceConfig,
    ConfigLoader,
    load_config,
)


# ── LeeConfig defaults ────────────────────────────────────────────

class TestLeeConfigDefaults:
    def test_default_values(self):
        config = LeeConfig()
        assert config.spec_root is None
        assert config.demo_mode is False
        assert config.retry.max_retries == 3
        assert config.on_failure.default_fallback == "abort"
        assert config.executor.timeout_seconds == 600
        assert config.tracing.enabled is True
        assert config.evidence.output_dir == ".workflow/evidence"

    def test_from_empty_dict(self):
        config = LeeConfig.from_dict({})
        assert config.retry.max_retries == 3
        assert config.demo_mode is False


# ── LeeConfig from_dict ───────────────────────────────────────────

class TestLeeConfigFromDict:
    def test_full_config(self):
        data = {
            "spec_root": "my-spec",
            "demo_mode": True,
            "retry": {"max_retries": 5, "retry_delay_seconds": 0.5},
            "on_failure": {"default_retry": 3, "default_fallback": "human_review"},
            "executor": {"default_type": "shell", "llm_model": "gpt-4o", "timeout_seconds": 600},
            "tracing": {"enabled": False, "output_dir": "/tmp/traces"},
            "evidence": {"output_dir": "/tmp/evidence"},
        }
        config = LeeConfig.from_dict(data)
        assert config.spec_root == "my-spec"
        assert config.demo_mode is True
        assert config.retry.max_retries == 5
        assert config.retry.retry_delay_seconds == 0.5
        assert config.on_failure.default_retry == 3
        assert config.on_failure.default_fallback == "human_review"
        assert config.executor.default_type == "shell"
        assert config.executor.llm_model == "gpt-4o"
        assert config.executor.timeout_seconds == 600
        assert config.tracing.enabled is False
        assert config.evidence.output_dir == "/tmp/evidence"

    def test_executor_scalar_config_is_supported(self):
        data = {
            "executor": "qwen",
        }
        config = LeeConfig.from_dict(data)
        assert config.executor.default_type == "qwen_chat"

    def test_partial_config(self):
        data = {"retry": {"max_retries": 10}}
        config = LeeConfig.from_dict(data)
        assert config.retry.max_retries == 10
        assert config.retry.retry_delay_seconds == 2.0  # default
        assert config.on_failure.default_fallback == "abort"  # default


# ── ConfigLoader ───────────────────────────────────────────────────

class TestConfigLoader:
    def test_no_config_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config = load_config(tmpdir)
            assert config.retry.max_retries == 3
            assert config.demo_mode is False

    def test_load_from_yaml(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".lee"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            config_file.write_text(
                "spec_root: custom-spec\n"
                "demo_mode: true\n"
                "retry:\n"
                "  max_retries: 7\n",
                encoding="utf-8"
            )

            config = load_config(tmpdir)
            assert config.spec_root == "custom-spec"
            assert config.demo_mode is True
            assert config.retry.max_retries == 7

    def test_custom_config_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "custom.yaml"
            config_file.write_text(
                "executor:\n"
                "  llm_model: claude-3\n",
                encoding="utf-8"
            )

            config = load_config(tmpdir, str(config_file))
            assert config.executor.llm_model == "claude-3"

    def test_env_override_demo_mode(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_val = os.environ.get("LEE_DEMO_MODE")
            try:
                os.environ["LEE_DEMO_MODE"] = "true"
                config = load_config(tmpdir)
                assert config.demo_mode is True
            finally:
                if old_val is None:
                    os.environ.pop("LEE_DEMO_MODE", None)
                else:
                    os.environ["LEE_DEMO_MODE"] = old_val

    def test_env_override_spec_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_val = os.environ.get("LEE_SPEC_ROOT")
            try:
                os.environ["LEE_SPEC_ROOT"] = "/custom/spec"
                config = load_config(tmpdir)
                assert config.spec_root == "/custom/spec"
            finally:
                if old_val is None:
                    os.environ.pop("LEE_SPEC_ROOT", None)
                else:
                    os.environ["LEE_SPEC_ROOT"] = old_val

    def test_malformed_yaml_falls_back_to_defaults(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            config_dir = Path(tmpdir) / ".lee"
            config_dir.mkdir()
            config_file = config_dir / "config.yaml"
            config_file.write_text("{{invalid yaml", encoding="utf-8")

            config = load_config(tmpdir)
            assert config.retry.max_retries == 3

    def test_env_override_executor_default_type(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_value = os.environ.get("LEE_EXECUTOR")
            try:
                os.environ["LEE_EXECUTOR"] = "qwen"
                config = load_config(tmpdir)
                assert config.executor.default_type == "qwen_chat"
            finally:
                if old_value is None:
                    os.environ.pop("LEE_EXECUTOR", None)
                else:
                    os.environ["LEE_EXECUTOR"] = old_value
