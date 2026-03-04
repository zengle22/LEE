"""
SUT (System Under Test) Configuration

简化版 SUT 配置实现，支持：
- Web 应用（URL）
- API 服务（base_url + 认证）
- 其他类型预留接口

运行时配置位置：{tests_dir}/runtime/{test_run_id}/sut.yaml
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional, Any

import yaml


class SUTType(Enum):
    """被测系统类型"""
    WEB = "web"
    API = "api"
    MOBILE = "mobile"
    DESKTOP = "desktop"
    MICROSERVICE = "microservice"
    UNKNOWN = "unknown"


@dataclass
class SUTConfig:
    """
    统一的 SUT 配置模型

    使用简化设计：所有类型共用一个配置，
    类型特定配置通过 extras 字段存储。
    """
    # 类型标识
    sut_type: SUTType = SUTType.WEB
    name: str = ""

    # 通用配置（Web/API 共享）
    base_url: str = "http://localhost:3000"
    base_path: str = ""
    protocol: str = "http"

    # 认证配置（可选）
    auth_type: Optional[str] = None  # none / bearer / basic / api_key
    auth_token: Optional[str] = None

    # 启用状态
    enabled: bool = True

    # 类型特定扩展配置（JSON 兼容）
    extras: Dict[str, Any] = field(default_factory=dict)

    # 元数据
    metadata: Dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_env(cls, env: str, **overrides) -> "SUTConfig":
        """
        从环境名创建默认配置，支持覆盖

        Args:
            env: 环境名称 (local/test/staging/prod)
            **overrides: 配置覆盖项

        Returns:
            SUTConfig 实例
        """
        defaults = {
            "local": "http://localhost:3000",
            "test": "http://localhost:3000",
            "staging": "https://app-staging.example.com",
            "prod": "https://app.example.com",
        }

        # 从 overrides 中提取 base_url，避免重复传递
        base_url = overrides.pop("base_url", defaults.get(env, defaults["local"]))

        return cls(
            base_url=base_url,
            **overrides
        )

    def to_env_vars(self) -> Dict[str, str]:
        """转换为环境变量字典"""
        env_vars = {
            "SUT_TYPE": self.sut_type.value,
            "SUT_BASE_URL": self.base_url,
            "SUT_BASE_PATH": self.base_path,
            "SUT_PROTOCOL": self.protocol,
        }

        if self.auth_type:
            env_vars["SUT_AUTH_TYPE"] = self.auth_type

        return env_vars

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 YAML 序列化）"""
        return {
            "sut_type": self.sut_type.value,
            "name": self.name,
            "base_url": self.base_url,
            "base_path": self.base_path,
            "protocol": self.protocol,
            "auth_type": self.auth_type,
            "enabled": self.enabled,
            "extras": self.extras,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SUTConfig":
        """从字典创建配置"""
        # 处理 sut_type
        sut_type_str = data.get("sut_type", "web").lower()
        try:
            sut_type = SUTType(sut_type_str)
        except ValueError:
            sut_type = SUTType.UNKNOWN

        return cls(
            sut_type=sut_type,
            name=data.get("name", ""),
            base_url=data.get("base_url", "http://localhost:3000"),
            base_path=data.get("base_path", ""),
            protocol=data.get("protocol", "http"),
            auth_type=data.get("auth_type"),
            enabled=data.get("enabled", True),
            extras=data.get("extras", {}),
            metadata=data.get("metadata", {}),
        )


# ─────────────────────────────────────────────────────────────────────
# URL 解析器
# ─────────────────────────────────────────────────────────────────────

class URLResolver:
    """
    SUT URL 解析器

    优先级：
    1. explicit_url - CLI 显式指定
    2. config_file - 运行时配置文件
    3. env_default - 环境默认值
    """

    # 环境默认值映射
    DEFAULT_URLS = {
        "local": "http://localhost:3000",
        "test": "http://localhost:3000",
        "staging": "https://app-staging.example.com",
        "prod": "https://app.example.com",
    }

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root

    def resolve(
        self,
        env: str,
        explicit_url: Optional[str] = None,
        config_file: Optional[Path] = None,
    ) -> str:
        """
        解析 SUT URL

        Args:
            env: 环境名称
            explicit_url: 显式指定的 URL
            config_file: 运行时配置文件路径

        Returns:
            解析后的 URL
        """
        # 1. 显式指定优先
        if explicit_url:
            return explicit_url

        # 2. 配置文件次之
        if config_file and config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if data and "base_url" in data:
                        return data["base_url"]
            except Exception:
                pass  # 忽略配置读取错误，使用默认值

        # 3. 使用环境默认值
        return self.DEFAULT_URLS.get(env, self.DEFAULT_URLS["local"])

    def resolve_with_config(
        self,
        env: str,
        explicit_url: Optional[str] = None,
        sut_config: Optional[SUTConfig] = None,
    ) -> str:
        """
        使用 SUTConfig 对象解析 URL

        Args:
            env: 环境名称
            explicit_url: 显式指定的 URL
            sut_config: SUTConfig 实例

        Returns:
            解析后的 URL
        """
        # 1. 显式指定优先
        if explicit_url:
            return explicit_url

        # 2. SUTConfig 次之
        if sut_config:
            base = sut_config.base_url
            path = sut_config.base_path
            if path:
                return f"{base.rstrip('/')}/{path.lstrip('/')}"
            return base

        # 3. 使用默认值
        return self.resolve(env)


# ─────────────────────────────────────────────────────────────────────
# SUT 配置加载器（简化版）
# ─────────────────────────────────────────────────────────────────────

class SUTConfigLoader:
    """
    SUT 配置加载器

    负责从运行时目录加载 SUT 配置。
    配置位置：{tests_dir}/runtime/{test_run_id}/sut.yaml
    """

    RUNTIME_DIR = "runtime"
    SUT_CONFIG_FILE = "sut.yaml"

    def __init__(self, project_root: Path):
        self.project_root = project_root

    def _get_tests_dir(self) -> Path:
        """获取 tests 目录（从项目配置）"""
        # 尝试加载项目配置
        config_file = self.project_root / ".project" / "dirs.yaml"

        if config_file.exists():
            try:
                with open(config_file, encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    tests_path = data.get("directories", {}).get("tests_dir", {}).get("path", "tests")
                    # 处理项目子目录情况：如果 project_root 不包含项目名子目录，则添加
                    project_name = data.get("project_name")
                    if project_name and not self.project_root.name == project_name:
                        return self.project_root / project_name / tests_path
                    return self.project_root / tests_path
            except Exception:
                pass

        # 默认返回 tests 目录
        return self.project_root / "tests"

    def get_runtime_dir(self, test_run_id: str) -> Path:
        """获取测试运行时的根目录"""
        tests_dir = self._get_tests_dir()
        return tests_dir / self.RUNTIME_DIR / test_run_id

    def get_config_path(self, test_run_id: str) -> Path:
        """获取 SUT 配置文件路径"""
        return self.get_runtime_dir(test_run_id) / self.SUT_CONFIG_FILE

    def load(self, test_run_id: str) -> Optional[SUTConfig]:
        """
        加载 SUT 配置

        Args:
            test_run_id: 测试运行 ID

        Returns:
            SUTConfig 实例，如果不存在则返回 None
        """
        config_path = self.get_config_path(test_run_id)

        if not config_path.exists():
            return None

        try:
            with open(config_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
                return SUTConfig.from_dict(data)
        except Exception:
            return None

    def save(self, test_run_id: str, config: SUTConfig) -> Path:
        """
        保存 SUT 配置

        Args:
            test_run_id: 测试运行 ID
            config: SUT 配置

        Returns:
            保存的文件路径
        """
        runtime_dir = self.get_runtime_dir(test_run_id)
        runtime_dir.mkdir(parents=True, exist_ok=True)

        config_path = self.get_config_path(test_run_id)

        with open(config_path, "w", encoding="utf-8") as f:
            yaml.dump(config.to_dict(), f, allow_unicode=True, default_flow_style=False)

        return config_path

    def load_or_create(
        self,
        test_run_id: str,
        env: str,
        **overrides,
    ) -> SUTConfig:
        """
        加载或创建 SUT 配置

        如果配置文件存在则加载，否则创建默认配置。

        Args:
            test_run_id: 测试运行 ID
            env: 环境名称
            **overrides: 配置覆盖项

        Returns:
            SUTConfig 实例
        """
        existing = self.load(test_run_id)
        if existing:
            return existing

        # 创建默认配置
        config = SUTConfig.from_env(env, **overrides)
        config.name = f"{test_run_id}-{env}"

        # 保存配置
        self.save(test_run_id, config)

        return config


# ─────────────────────────────────────────────────────────────────────
# 便捷函数
# ─────────────────────────────────────────────────────────────────────

def resolve_sut_url(
    env: str,
    explicit_url: Optional[str] = None,
    config_file: Optional[Path] = None,
) -> str:
    """
    便捷函数：解析 SUT URL

    这是最简化的入口函数，适用于不需要完整 SUT 配置的场景。

    Args:
        env: 环境名称
        explicit_url: 显式指定的 URL
        config_file: 配置文件路径

    Returns:
        解析后的 URL
    """
    resolver = URLResolver()
    return resolver.resolve(env, explicit_url, config_file)
