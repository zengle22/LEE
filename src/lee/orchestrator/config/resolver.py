from __future__ import annotations

import os
from pathlib import Path
from typing import List, Optional

from lee.orchestrator.config_loader import LeeConfig, load_config

from .types import ConfigSource, ExecutorType, ResolvedExecutorConfig


class ConfigResolver:
    """Resolve executor selection across CLI/env/config/default layers."""

    _EXECUTOR_ALIASES = {
        "qwen": "qwen_chat",
        "kimi-cli": "kimi",
    }

    def __init__(self, project_root: Optional[str | Path] = None, config: Optional[LeeConfig] = None):
        self.project_root = str(project_root or ".")
        self.config = config or load_config(self.project_root)

    def _has_config_file(self) -> bool:
        return (Path(self.project_root) / ".lee" / "config.yaml").exists()

    @staticmethod
    def _normalize(raw_value: object) -> Optional[str]:
        if not isinstance(raw_value, str):
            return None
        normalized = raw_value.strip().lower()
        if not normalized:
            return None
        return ConfigResolver._EXECUTOR_ALIASES.get(normalized, normalized)

    @classmethod
    def get_valid_executor_types(cls) -> List[str]:
        from lee.orchestrator.execution.executors import ExecutorFactory

        return sorted(str(name).strip().lower() for name in ExecutorFactory._executors.keys())

    @classmethod
    def validate_executor_type(cls, raw_value: Optional[str]) -> Optional[str]:
        value = cls._normalize(raw_value)
        if not value:
            return None
        if value in cls.get_valid_executor_types():
            return None
        allowed = ", ".join(cls.get_valid_executor_types())
        return f"错误：非法的执行器类型 {value}\n可选值：[{allowed}]"

    def resolve(
        self,
        *,
        cli_executor: Optional[str] = None,
        env_executor: Optional[str] = None,
        file_executor: Optional[str] = None,
        default_executor: str = "claude_code",
    ) -> ResolvedExecutorConfig:
        raw_cli = self._normalize(cli_executor)
        raw_env = self._normalize(env_executor or os.getenv("LEE_EXECUTOR") or os.getenv("LEE_EXECUTOR_TYPE"))
        resolved_file_value = file_executor
        if resolved_file_value is None and self._has_config_file():
            resolved_file_value = getattr(self.config.executor, "default_type", None)
        raw_file = self._normalize(resolved_file_value)
        raw_default = self._normalize(default_executor) or "claude_code"

        selected = raw_cli
        source = ConfigSource.CLI_OVERRIDE
        if not selected:
            selected = raw_env
            source = ConfigSource.ENV
        if not selected:
            selected = raw_file
            source = ConfigSource.FILE_CONFIG
        if not selected:
            selected = raw_default
            source = ConfigSource.DEFAULT

        error_message = self.validate_executor_type(selected)
        if error_message:
            return ResolvedExecutorConfig(
                executor_type=None,
                source=source,
                raw_cli=raw_cli,
                raw_env=raw_env,
                raw_file=raw_file,
                raw_default=raw_default,
                is_valid=False,
                error_message=error_message,
            )

        return ResolvedExecutorConfig(
            executor_type=ExecutorType.from_string(selected),
            source=source,
            raw_cli=raw_cli,
            raw_env=raw_env,
            raw_file=raw_file,
            raw_default=raw_default,
            is_valid=True,
            error_message=None,
        )
