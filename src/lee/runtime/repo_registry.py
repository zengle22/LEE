"""
LEE Runtime — Repo Registry

将 repo 提升为一等公民。

Executor 不接受任意路径，只接受 repo_id。
路径只由 runtime 根据 registry 解析。

Usage:
    registry = RepoRegistry.from_yaml("path/to/repo-registry.yaml")
    repo = registry.get_repo("app-backend")
    abs_path = registry.resolve_path("app-backend")
"""

from __future__ import annotations

import fnmatch
import logging
import os
import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ── Data Models ───────────────────────────────────────────────────


@dataclass
class RepoEntry:
    """单个 repo 的注册信息"""

    repo_id: str
    path: str                                     # 原始路径（可能是相对路径）
    type: str = "git"                             # vcs 类型
    url: Optional[str] = None                     # 远程仓库地址
    default_branch: str = "main"
    description: str = ""
    path_policy: List[str] = field(default_factory=list)   # 写路径白名单
    owner: str = ""
    tags: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, repo_id: str, data: Dict[str, Any]) -> "RepoEntry":
        """从字典构建 RepoEntry"""
        return cls(
            repo_id=repo_id,
            path=data.get("path", ""),
            type=data.get("type", "git"),
            url=data.get("url"),
            default_branch=data.get("default_branch", "main"),
            description=data.get("description", ""),
            path_policy=data.get("path_policy", []),
            owner=data.get("owner", ""),
            tags=data.get("tags", []),
        )


@dataclass
class RepoStatus:
    """Repo 实时状态"""

    repo_id: str
    exists: bool                          # 路径是否存在
    abs_path: str = ""                    # 绝对路径
    is_clean: bool = False                # git status 是否干净
    current_branch: str = ""              # 当前分支
    current_commit: str = ""              # 当前 commit（短 hash）
    uncommitted_changes: int = 0          # 未提交变更数
    error: Optional[str] = None           # 错误信息


# ── Repo Registry ─────────────────────────────────────────────────


class RepoRegistry:
    """
    Repo 注册表 — 管理所有受管 repo

    核心职责：
    1. 从 YAML 加载 registry
    2. 按 repo_id 查询 → RepoEntry
    3. 解析相对路径 → 绝对路径
    4. 校验 repo 路径和 git root
    5. 校验写路径白名单
    """

    def __init__(
        self,
        repos: Optional[Dict[str, RepoEntry]] = None,
        workspace_root: Optional[str] = None,
    ):
        self._repos: Dict[str, RepoEntry] = repos or {}
        self._workspace_root = workspace_root or os.getcwd()

    # ── Factory Methods ───────────────────────────────────────────

    @classmethod
    def from_yaml(
        cls,
        config_path: str,
        workspace_root: Optional[str] = None,
    ) -> "RepoRegistry":
        """
        从 YAML 文件加载 registry

        Args:
            config_path: registry YAML 文件路径
            workspace_root: workspace 根目录（用于解析相对路径）

        Returns:
            RepoRegistry 实例
        """
        import yaml

        path = Path(config_path)
        if not path.exists():
            logger.warning(f"Repo registry not found: {config_path}")
            return cls(workspace_root=workspace_root)

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        version = data.get("version", "1.0")
        if version != "1.0":
            logger.warning(f"Unsupported registry version: {version}")

        repos_data = data.get("repos", {})
        repos = {}
        for repo_id, repo_dict in repos_data.items():
            if isinstance(repo_dict, dict):
                repos[repo_id] = RepoEntry.from_dict(repo_id, repo_dict)
            else:
                logger.warning(f"Invalid repo entry for '{repo_id}', skipping")

        logger.info(f"Loaded repo registry: {len(repos)} repos from {config_path}")
        return cls(repos=repos, workspace_root=workspace_root)

    @classmethod
    def from_dict(
        cls,
        data: Dict[str, Any],
        workspace_root: Optional[str] = None,
    ) -> "RepoRegistry":
        """从字典构建 registry"""
        repos_data = data.get("repos", {})
        repos = {}
        for repo_id, repo_dict in repos_data.items():
            if isinstance(repo_dict, dict):
                repos[repo_id] = RepoEntry.from_dict(repo_id, repo_dict)
        return cls(repos=repos, workspace_root=workspace_root)

    # ── Query Methods ─────────────────────────────────────────────

    def get_repo(self, repo_id: str) -> Optional[RepoEntry]:
        """按 repo_id 查询"""
        return self._repos.get(repo_id)

    def get_repo_or_raise(self, repo_id: str) -> RepoEntry:
        """按 repo_id 查询，不存在则抛异常"""
        repo = self._repos.get(repo_id)
        if repo is None:
            available = ", ".join(sorted(self._repos.keys())) or "(empty)"
            raise ValueError(
                f"Unknown repo_id: '{repo_id}'. "
                f"Available repos: {available}"
            )
        return repo

    def list_repos(self) -> List[RepoEntry]:
        """列出所有注册 repo"""
        return list(self._repos.values())

    def list_repo_ids(self) -> List[str]:
        """列出所有 repo_id"""
        return sorted(self._repos.keys())

    @property
    def workspace_root(self) -> str:
        return self._workspace_root

    def __len__(self) -> int:
        return len(self._repos)

    def __contains__(self, repo_id: str) -> bool:
        return repo_id in self._repos

    # ── Path Resolution ───────────────────────────────────────────

    def resolve_path(self, repo_id: str) -> str:
        """
        解析 repo 绝对路径

        相对路径相对于 workspace_root 解析。

        Args:
            repo_id: repo 标识

        Returns:
            绝对路径字符串
        """
        repo = self.get_repo_or_raise(repo_id)
        repo_path = Path(repo.path)
        if repo.path.startswith("/") and not repo_path.is_absolute():
            return repo.path

        if repo_path.is_absolute():
            return str(repo_path.resolve())

        # 相对路径 → 相对于 workspace_root
        return str((Path(self._workspace_root) / repo_path).resolve())

    # ── Validation ────────────────────────────────────────────────

    def validate(self) -> List[str]:
        """
        校验所有 repo 路径存在 + git root 正确

        Returns:
            错误消息列表（空 = 全部通过）
        """
        errors = []
        for repo_id, repo in self._repos.items():
            try:
                abs_path = self.resolve_path(repo_id)
            except Exception as e:
                errors.append(f"[{repo_id}] Path resolution failed: {e}")
                continue

            if not os.path.isdir(abs_path):
                errors.append(f"[{repo_id}] Directory not found: {abs_path}")
                continue

            if repo.type == "git":
                git_root = self._get_git_root(abs_path)
                if git_root is None:
                    errors.append(f"[{repo_id}] Not a git repository: {abs_path}")
                elif os.path.realpath(git_root) != os.path.realpath(abs_path):
                    errors.append(
                        f"[{repo_id}] Git root mismatch: "
                        f"expected {abs_path}, got {git_root}"
                    )

        return errors

    def validate_git_root(self, repo_id: str, actual_dir: str) -> bool:
        """
        硬校验：actual_dir 的 git root 是否匹配 repo 注册路径

        Args:
            repo_id: repo 标识
            actual_dir: 实际工作目录

        Returns:
            True = 匹配, False = 不匹配
        """
        expected = self.resolve_path(repo_id)
        git_root = self._get_git_root(actual_dir)
        if git_root is None:
            return False
        return os.path.realpath(git_root) == os.path.realpath(expected)

    # ── Path Policy ───────────────────────────────────────────────

    def check_path_allowed(
        self,
        repo_id: str,
        relative_path: str,
        extra_allowlist: Optional[List[str]] = None,
    ) -> bool:
        """
        检查写路径是否在白名单内

        Args:
            repo_id: repo 标识
            relative_path: 相对于 repo root 的路径
            extra_allowlist: 额外允许的路径（覆盖 repo 级 path_policy）

        Returns:
            True = 允许, False = 拒绝
        """
        repo = self.get_repo_or_raise(repo_id)

        # 如果提供了 extra_allowlist，优先使用
        policy = extra_allowlist if extra_allowlist else repo.path_policy

        # 空 policy = 不限制
        if not policy:
            return True

        # 规范化路径
        rel = relative_path.replace("\\", "/").lstrip("/")

        return any(fnmatch.fnmatch(rel, pattern) for pattern in policy)

    # ── Status Querying ───────────────────────────────────────────

    def get_status(self, repo_id: str) -> RepoStatus:
        """
        获取 repo 实时状态

        Returns:
            RepoStatus 实例
        """
        repo = self.get_repo_or_raise(repo_id)

        try:
            abs_path = self.resolve_path(repo_id)
        except Exception as e:
            return RepoStatus(
                repo_id=repo_id, exists=False, error=str(e)
            )

        if not os.path.isdir(abs_path):
            return RepoStatus(
                repo_id=repo_id, exists=False, abs_path=abs_path,
                error=f"Directory not found: {abs_path}"
            )

        if repo.type != "git":
            return RepoStatus(
                repo_id=repo_id, exists=True, abs_path=abs_path
            )

        # Git-specific status
        try:
            branch = self._run_git(abs_path, ["rev-parse", "--abbrev-ref", "HEAD"])
            commit = self._run_git(abs_path, ["rev-parse", "--short", "HEAD"])

            # Count uncommitted changes
            status_output = self._run_git(
                abs_path, ["status", "--porcelain"]
            )
            changes = len(
                [line for line in status_output.strip().split("\n") if line.strip()]
            ) if status_output.strip() else 0

            return RepoStatus(
                repo_id=repo_id,
                exists=True,
                abs_path=abs_path,
                is_clean=changes == 0,
                current_branch=branch.strip(),
                current_commit=commit.strip(),
                uncommitted_changes=changes,
            )
        except Exception as e:
            return RepoStatus(
                repo_id=repo_id, exists=True, abs_path=abs_path,
                error=f"Git query failed: {e}"
            )

    def get_all_status(self) -> List[RepoStatus]:
        """获取所有 repo 的实时状态"""
        return [self.get_status(repo_id) for repo_id in self._repos]

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _get_git_root(dir_path: str) -> Optional[str]:
        """获取 git 仓库根目录"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                cwd=dir_path,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    @staticmethod
    def _run_git(dir_path: str, args: List[str]) -> str:
        """执行 git 命令"""
        result = subprocess.run(
            ["git"] + args,
            cwd=dir_path,
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"git {' '.join(args)} failed: {result.stderr.strip()}"
            )
        return result.stdout
