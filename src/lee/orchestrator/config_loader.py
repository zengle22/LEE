"""
LEE Orchestrator v3.5 — Externalized Configuration (M4)

从 .lee/config.yaml 加载项目级别的配置。
所有配置项都有合理的默认值，文件不存在时使用默认值。

配置文件路径优先级：
1. 构造函数传入的 config_path
2. {project_root}/.lee/config.yaml
3. 默认值

示例 .lee/config.yaml:
```yaml
spec_root: spec-global          # 相对于 project_root
demo_mode: false

retry:
  max_retries: 3
  retry_delay_seconds: 2.0

on_failure:
  default_retry: 2
  default_fallback: human_review

executor:
  default_type: llm
  llm_model: gpt-4
  timeout_seconds: 600

tracing:
  enabled: true
  output_dir: .workflow/traces

evidence:
  output_dir: .workflow/evidence
```
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional

from lee.orchestrator.core.path_policy import WORKFLOW_SUBDIRS

logger = logging.getLogger(__name__)


# ── Configuration Dataclasses ──────────────────────────────────────

@dataclass
class RetryConfig:
    """重试配置"""
    max_retries: int = 3
    retry_delay_seconds: float = 2.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RetryConfig":
        return cls(
            max_retries=data.get("max_retries", 3),
            retry_delay_seconds=data.get("retry_delay_seconds", 2.0),
        )


@dataclass
class OnFailureConfig:
    """默认失败处理配置"""
    default_retry: int = 2
    default_fallback: str = "abort"

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OnFailureConfig":
        return cls(
            default_retry=data.get("default_retry", 2),
            default_fallback=data.get("default_fallback", "abort"),
        )


@dataclass
class ExecutorConfig:
    """执行器配置"""
    default_type: str = "llm"
    coding_executor: str = "claude_code"       # 编码步骤首选执行器
    coding_fallback: str = "llm_patch"         # 编码步骤降级执行器
    llm_model: Optional[str] = None
    timeout_seconds: int = 600

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutorConfig":
        return cls(
            default_type=data.get("default_type", "llm"),
            coding_executor=data.get("coding_executor", "claude_code"),
            coding_fallback=data.get("coding_fallback", "llm_patch"),
            llm_model=data.get("llm_model"),
            timeout_seconds=data.get("timeout_seconds", 600),
        )


@dataclass
class TracingConfig:
    """追踪配置"""
    enabled: bool = True
    output_dir: str = WORKFLOW_SUBDIRS["traces"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "TracingConfig":
        return cls(
            enabled=data.get("enabled", True),
            output_dir=data.get("output_dir", WORKFLOW_SUBDIRS["traces"]),
        )


@dataclass
class EvidenceConfig:
    """证据收集配置"""
    output_dir: str = WORKFLOW_SUBDIRS["evidence"]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "EvidenceConfig":
        return cls(
            output_dir=data.get("output_dir", WORKFLOW_SUBDIRS["evidence"]),
        )


@dataclass
class RepoRegistryConfig:
    """Repo Registry 配置"""
    registry_path: Optional[str] = None    # 显式指定 registry 文件路径
    worktree_root: str = ".lee/runs"       # worktree 根目录
    default_mode: str = "symlink"          # 默认工作区模式 (symlink/worktree/copy)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RepoRegistryConfig":
        return cls(
            registry_path=data.get("registry_path"),
            worktree_root=data.get("worktree_root", ".lee/runs"),
            default_mode=data.get("default_mode", "symlink"),
        )


@dataclass
class LeeConfig:
    """
    LEE 项目配置

    所有配置项都有默认值，配置文件不存在时完全可用。
    """
    # 路径
    spec_root: Optional[str] = None  # 相对于 project_root，默认 "spec-global"
    demo_mode: bool = False

    # 子配置
    retry: RetryConfig = field(default_factory=RetryConfig)
    on_failure: OnFailureConfig = field(default_factory=OnFailureConfig)
    executor: ExecutorConfig = field(default_factory=ExecutorConfig)
    tracing: TracingConfig = field(default_factory=TracingConfig)
    evidence: EvidenceConfig = field(default_factory=EvidenceConfig)
    repos: RepoRegistryConfig = field(default_factory=RepoRegistryConfig)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "LeeConfig":
        """从字典构建配置"""
        return cls(
            spec_root=data.get("spec_root"),
            demo_mode=data.get("demo_mode", False),
            retry=RetryConfig.from_dict(data.get("retry", {})),
            on_failure=OnFailureConfig.from_dict(data.get("on_failure", {})),
            executor=ExecutorConfig.from_dict(data.get("executor", {})),
            tracing=TracingConfig.from_dict(data.get("tracing", {})),
            evidence=EvidenceConfig.from_dict(data.get("evidence", {})),
            repos=RepoRegistryConfig.from_dict(data.get("repos", {})),
        )


# ── Config Loader ──────────────────────────────────────────────────

class ConfigLoader:
    """
    配置加载器

    优先级（高 → 低）：
    1. 环境变量覆盖（LEE_DEMO_MODE 等）
    2. .lee/config.yaml 文件
    3. 内置默认值
    """

    def __init__(self, project_root: Optional[str] = None):
        self.project_root = project_root or "."

    def load(self, config_path: Optional[str] = None) -> LeeConfig:
        """
        加载配置

        Args:
            config_path: 可选的配置文件路径，不指定则使用默认路径

        Returns:
            LeeConfig 实例
        """
        # 确定配置文件路径
        if config_path:
            path = Path(config_path)
        else:
            path = Path(self.project_root) / ".lee" / "config.yaml"

        # 从文件加载
        config_data = self._load_yaml(path)

        # 构建配置
        config = LeeConfig.from_dict(config_data)

        # 环境变量覆盖
        config = self._apply_env_overrides(config)

        return config

    def _load_yaml(self, path: Path) -> Dict[str, Any]:
        """加载 YAML 文件"""
        if not path.exists():
            logger.debug(f"Config file not found: {path}, using defaults")
            return {}

        try:
            import yaml
            with open(path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f) or {}
            logger.info(f"Loaded config from {path}")
            return data
        except ImportError:
            logger.warning("PyYAML not installed, using defaults")
            return {}
        except Exception as e:
            logger.warning(f"Failed to parse config file {path}: {e}, using defaults")
            return {}

    @staticmethod
    def _apply_env_overrides(config: LeeConfig) -> LeeConfig:
        """应用环境变量覆盖"""
        # LEE_DEMO_MODE
        demo_env = os.getenv("LEE_DEMO_MODE", "").lower()
        if demo_env in ("1", "true", "yes"):
            config.demo_mode = True
        elif demo_env in ("0", "false", "no"):
            config.demo_mode = False

        # LEE_SPEC_ROOT
        spec_root_env = os.getenv("LEE_SPEC_ROOT")
        if spec_root_env:
            config.spec_root = spec_root_env

        # LEE_REPO_REGISTRY
        repo_registry_env = os.getenv("LEE_REPO_REGISTRY")
        if repo_registry_env:
            config.repos.registry_path = repo_registry_env

        return config


# ── Convenience ────────────────────────────────────────────────────

def load_config(project_root: Optional[str] = None,
                config_path: Optional[str] = None) -> LeeConfig:
    """便捷函数：加载项目配置"""
    return ConfigLoader(project_root).load(config_path)


# ── Resolver Integration ───────────────────────────────────────────────

def resolve_spec_root(
    project_root: str,
    cli_spec_root: Optional[str] = None
) -> "SpecResolveResult":
    """
    使用 Resolver 解析 spec_root

    整合了 CLI 参数、环境变量、配置文件和 dev 模式。

    Args:
        project_root: 项目根目录
        cli_spec_root: CLI 参数 --spec-root

    Returns:
        SpecResolveResult: 解析结果
    """
    from lee.data_path import (
        resolve_spec,
        SpecResolveInput,
        load_lee_lock,
        discover_workspace_root,
        Path,
    )

    workspace_root = Path(project_root)
    lock = load_lee_lock(workspace_root)

    input = SpecResolveInput(
        workspace_root=workspace_root,
        cli_spec_root=cli_spec_root,
        env_spec_root=os.getenv("LEE_SPEC_ROOT"),
        lock_mode=lock.mode if lock else None,
        lock_lee_src=lock.lee_src if lock else None,
    )

    # 还需要从配置文件读取 spec_root
    config = load_config(project_root)
    input.config_spec_root = config.spec_root

    return resolve_spec(input)
