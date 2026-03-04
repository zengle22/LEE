"""
PathConfig - 可注入的路径配置服务

提供统一的路径获取接口，支持：
- 可注入设计（不依赖单例）
- WorkflowContext 集成
- 与 path_policy.py 策略一致

用法:
    from src.lee.orchestrator.core.path_config import PathConfig

    # 方式1: 直接创建
    config = PathConfig(project_root=".")
    artifacts_dir = config.get_path(".artifacts")

    # 方式2: 注入到 context
    from src.lee.orchestrator.core.path_config import get_path_config
    config = get_path_config(project_root=".")
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from .path_policy import (
    ALLOWED_WRITE_PREFIXES,
    FROZEN_PREFIXES,
    TOOL_DIRECTORIES,
    normalize_path,
)


@lru_cache(maxsize=8)
def get_path_config(project_root: str = ".") -> "PathConfig":
    """
    获取 PathConfig 实例（带缓存）

    注意: 相同 project_root 会返回缓存实例
    如需独立实例，请直接创建 PathConfig

    Args:
        project_root: 项目根目录

    Returns:
        PathConfig 实例
    """
    return PathConfig(project_root=project_root)


class PathConfig:
    """
    路径配置服务

    特性:
    - 可注入：不依赖单例，可自由创建多个实例
    - 轻量：核心逻辑复用 path_policy.py
    - 可缓存：支持 lru_cache 避免重复创建

    属性:
        project_root: 项目根目录（绝对路径）
        artifacts_dir: .artifacts 目录路径
        workflow_dir: .workflow 目录路径
        outputs_dir: outputs 目录路径
    """

    def __init__(self, project_root: str = "."):
        """
        初始化 PathConfig

        Args:
            project_root: 项目根目录（默认当前目录）
        """
        self._project_root = Path(project_root).resolve()

    @property
    def project_root(self) -> Path:
        """项目根目录"""
        return self._project_root

    # === 工具目录 ===
    @property
    def project_config_dir(self) -> Path:
        """获取 .project 目录（项目配置）"""
        return self._project_root / ".project"

    @property
    def workflow_dir(self) -> Path:
        """获取 .workflow 目录（工作流运行态）"""
        return self._project_root / ".workflow"

    @property
    def artifacts_dir(self) -> Path:
        """获取 .artifacts 目录（产出物）"""
        return self._project_root / ".artifacts"

    # === 内容目录 ===
    @property
    def spec_dir(self) -> Path:
        """获取 spec 目录（规格 SSOT）"""
        return self._project_root / "spec"

    @property
    def docs_dir(self) -> Path:
        """获取 docs 目录（解释性文档）"""
        return self._project_root / "docs"

    @property
    def src_dir(self) -> Path:
        """获取 src 目录（源码）"""
        return self._project_root / "src"

    @property
    def tests_dir(self) -> Path:
        """获取 tests 目录（测试）"""
        return self._project_root / "tests"

    @property
    def tools_dir(self) -> Path:
        """获取 tools 目录（项目工具）"""
        return self._project_root / "tools"

    @property
    def deploy_dir(self) -> Path:
        """获取 deploy 目录（部署配置）"""
        return self._project_root / "deploy"

    @property
    def legacy_dir(self) -> Path:
        """获取 legacy 目录（兼容旧版）"""
        return self._project_root / "legacy"

    def get_path(self, name: str) -> Optional[Path]:
        """
        获取指定名称的目录路径

        Args:
            name: 目录名称（如 ".artifacts", "spec"）

        Returns:
            目录路径，如果不存在返回 None

        Example:
            config.get_path(".artifacts")  # -> Path("/path/to/.artifacts")
            config.get_path("spec")       # -> Path("/path/to/spec")
            config.get_path("tools")       # -> Path("/path/to/tools")
        """
        # 规范化输入
        name = normalize_path(name).rstrip("/")

        # 新标准目录
        standard_dirs = {
            ".project", ".workflow", ".artifacts",
            "spec", "docs", "src", "tests", "tools", "deploy", "legacy"
        }

        if name in standard_dirs:
            return self._project_root / name

        return None

    def get_artifacts_subpath(self, *parts: str) -> Path:
        """
        获取 .artifacts 下的子路径

        Args:
            *parts: 子路径部分

        Returns:
            完整路径

        Example:
            config.get_artifacts_subpath("active", "run123")
            # -> /path/to/.artifacts/active/run123
        """
        return self.artifacts_dir.joinpath(*parts)

    def get_workflow_subpath(self, *parts: str) -> Path:
        """
        获取 .workflow 下的子路径

        Args:
            *parts: 子路径部分

        Returns:
            完整路径
        """
        return self.workflow_dir.joinpath(*parts)

    def get_outputs_subpath(self, *parts: str) -> Path:
        """
        获取 outputs 下的子路径

        Args:
            *parts: 子路径部分

        Returns:
            完整路径
        """
        return self.outputs_dir.joinpath(*parts)

    def is_allowed_write(self, path: str) -> bool:
        """
        检查路径是否允许写入

        Args:
            path: 相对路径或绝对路径

        Returns:
            是否允许写入
        """
        from .path_policy import is_allowed_write_path

        # 如果是绝对路径，转换为相对路径
        p = Path(path)
        if p.is_absolute():
            try:
                path = str(p.relative_to(self._project_root))
            except ValueError:
                return False

        return is_allowed_write_path(path)

    def is_frozen(self, path: str) -> bool:
        """
        检查路径是否在冻结目录

        Args:
            path: 相对路径或绝对路径

        Returns:
            是否冻结
        """
        from .path_policy import is_frozen_path

        # 如果是绝对路径，转换为相对路径
        p = Path(path)
        if p.is_absolute():
            try:
                path = str(p.relative_to(self._project_root))
            except ValueError:
                return False

        return is_frozen_path(path)

    def __repr__(self) -> str:
        return f"PathConfig(project_root={self._project_root})"
