from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import List, Optional


EXECUTOR_TYPE_ALIASES = {
    "qwen": "qwen_chat",
    "kimi-cli": "kimi",
}

CODING_EXECUTOR_VALUES = {
    "claude_code",
    "codex",
    "kimi",
}


class ExecutorType(str, Enum):
    CLAUDE_CODE = "claude_code"
    QWEN_CHAT = "qwen_chat"
    KIMI = "kimi"
    CODEX = "codex"
    LANGGRAPH = "langgraph"
    SHELL = "shell"
    LLM = "llm"

    @classmethod
    def from_string(cls, value: str | None) -> Optional["ExecutorType"]:
        if not isinstance(value, str):
            return None
        normalized = value.strip().lower()
        if not normalized:
            return None
        normalized = EXECUTOR_TYPE_ALIASES.get(normalized, normalized)
        for item in cls:
            if item.value == normalized:
                return item
        return None

    @classmethod
    def allowed_values(cls) -> List[str]:
        return [item.value for item in cls]


def normalize_executor_type_name(value: str | None) -> Optional[str]:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower()
    if not normalized:
        return None
    return EXECUTOR_TYPE_ALIASES.get(normalized, normalized)


def is_coding_executor_type(value: str | None) -> bool:
    normalized = normalize_executor_type_name(value)
    return bool(normalized and normalized in CODING_EXECUTOR_VALUES)


class ConfigSource(str, Enum):
    CLI_OVERRIDE = "cli_override"
    ENV = "env"
    FILE_CONFIG = "file_config"
    DEFAULT = "default"


@dataclass
class ResolvedExecutorConfig:
    executor_type: Optional[ExecutorType]
    source: ConfigSource
    raw_cli: Optional[str] = None
    raw_env: Optional[str] = None
    raw_file: Optional[str] = None
    raw_default: Optional[str] = None
    is_valid: bool = True
    error_message: Optional[str] = None

    @property
    def value(self) -> Optional[str]:
        return self.executor_type.value if self.executor_type else None

    @property
    def source_marker(self) -> str:
        return self.source.value
