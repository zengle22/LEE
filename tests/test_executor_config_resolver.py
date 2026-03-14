from pathlib import Path

from lee.orchestrator.config import (
    ConfigResolver,
    ConfigSource,
    ExecutorType,
    is_coding_executor_type,
    normalize_executor_type_name,
)
from lee.orchestrator.config_loader import LeeConfig


def test_config_resolver_prefers_cli_over_file_and_default(tmp_path: Path) -> None:
    config = LeeConfig.from_dict({"executor": {"default_type": "claude_code"}})

    resolved = ConfigResolver(project_root=tmp_path, config=config).resolve(
        cli_executor="qwen_chat",
    )

    assert resolved.is_valid is True
    assert resolved.executor_type == ExecutorType.QWEN_CHAT
    assert resolved.source == ConfigSource.CLI_OVERRIDE
    assert resolved.value == "qwen_chat"


def test_config_resolver_prefers_env_over_file(tmp_path: Path, monkeypatch) -> None:
    config = LeeConfig.from_dict({"executor": {"default_type": "claude_code"}})
    monkeypatch.setenv("LEE_EXECUTOR", "kimi")

    resolved = ConfigResolver(project_root=tmp_path, config=config).resolve()

    assert resolved.is_valid is True
    assert resolved.executor_type == ExecutorType.KIMI
    assert resolved.source == ConfigSource.ENV
    assert resolved.value == "kimi"


def test_config_resolver_uses_file_config_when_cli_and_env_missing(tmp_path: Path) -> None:
    config_dir = tmp_path / ".lee"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("executor: qwen_chat\n", encoding="utf-8")
    config = LeeConfig.from_dict({"executor": "qwen_chat"})

    resolved = ConfigResolver(project_root=tmp_path, config=config).resolve()

    assert resolved.is_valid is True
    assert resolved.executor_type == ExecutorType.QWEN_CHAT
    assert resolved.source == ConfigSource.FILE_CONFIG


def test_config_resolver_normalizes_legacy_qwen_alias(tmp_path: Path) -> None:
    resolved = ConfigResolver(project_root=tmp_path).resolve(cli_executor="qwen")

    assert resolved.is_valid is True
    assert resolved.executor_type == ExecutorType.QWEN_CHAT
    assert resolved.value == "qwen_chat"


def test_config_resolver_rejects_invalid_executor_type(tmp_path: Path) -> None:
    resolved = ConfigResolver(project_root=tmp_path).resolve(cli_executor="not-real")

    assert resolved.is_valid is False
    assert resolved.executor_type is None
    assert "非法的执行器类型 not-real" in (resolved.error_message or "")
    assert "claude_code" in (resolved.error_message or "")


def test_normalize_executor_type_name_maps_aliases() -> None:
    assert normalize_executor_type_name("qwen") == "qwen_chat"
    assert normalize_executor_type_name("kimi-cli") == "kimi"
    assert normalize_executor_type_name(" llm ") == "llm"


def test_is_coding_executor_type_distinguishes_dialogue_backends() -> None:
    assert is_coding_executor_type("claude_code") is True
    assert is_coding_executor_type("kimi") is True
    assert is_coding_executor_type("qwen") is False
    assert is_coding_executor_type("qwen_chat") is False
    assert is_coding_executor_type("llm") is False
