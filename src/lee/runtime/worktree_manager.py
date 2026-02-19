"""
LEE Runtime — Worktree Manager

管理 run×repo 的工作区分配。

每个 run 可以在多个 repo 上工作，
每个 repo 的 worktree 是隔离的：

    .lee/runs/<run_id>/worktrees/<repo_id>/
      repo/        # git worktree 或 symlink
      artifacts/   # 产物
      evidence/    # 证据
      logs/        # 日志

Usage:
    manager = WorktreeManager(runs_root=".lee/runs", registry=registry)
    info = manager.allocate("run-001", "app-backend")
    workdir = info.workdir
    # ... executor 使用 workdir 作为 cwd
    manager.release("run-001", "app-backend")
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from lee.runtime.repo_registry import RepoRegistry

logger = logging.getLogger(__name__)


# ── Data Models ───────────────────────────────────────────────────


@dataclass
class WorktreeInfo:
    """一个 run×repo worktree 的描述"""

    run_id: str
    repo_id: str
    workdir: str          # 实际代码工作目录
    artifacts_dir: str    # 产物目录
    evidence_dir: str     # 证据目录
    logs_dir: str         # 日志目录
    created_at: str = ""  # ISO 时间戳
    mode: str = "symlink" # "worktree" | "symlink" | "copy"


# ── Worktree Manager ─────────────────────────────────────────────


class WorktreeManager:
    """
    Worktree 分配器 — run×repo 二维管理

    支持三种工作区模式：
    - symlink: 默认，创建指向 repo 的符号链接（最快，适合开发）
    - worktree: 使用 git worktree（真正隔离，适合并行执行）
    - copy: 复制整个 repo（最安全但最慢，适合审计）

    硬规则：
    1. 分配后 executor 只能在 workdir 内操作
    2. git root 必须匹配预期 repo
    3. 工作区外写入 = 立即 fail
    """

    def __init__(
        self,
        runs_root: str,
        registry: RepoRegistry,
        default_mode: str = "symlink",
    ):
        """
        Args:
            runs_root: 运行记录根目录 (e.g. ".lee/runs")
            registry: Repo 注册表
            default_mode: 默认工作区模式
        """
        self._runs_root = os.path.abspath(runs_root)
        self._registry = registry
        self._default_mode = default_mode
        # In-memory cache of allocated worktrees: (run_id, repo_id) → WorktreeInfo
        self._allocated: Dict[str, WorktreeInfo] = {}

    # ── Allocation ────────────────────────────────────────────────

    def allocate(
        self,
        run_id: str,
        repo_id: str,
        mode: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> WorktreeInfo:
        """
        为 run×repo 分配工作区

        如果已分配则返回现有工作区（幂等）。

        Args:
            run_id: 运行 ID
            repo_id: repo 标识
            mode: 工作区模式 (symlink/worktree/copy)
            branch: 基于哪个分支创建 worktree（仅 worktree 模式）

        Returns:
            WorktreeInfo
        """
        cache_key = f"{run_id}:{repo_id}"

        # 幂等：已分配则直接返回
        if cache_key in self._allocated:
            logger.debug(f"Worktree already allocated: {cache_key}")
            return self._allocated[cache_key]

        # 验证 repo_id 存在
        repo = self._registry.get_repo_or_raise(repo_id)
        repo_abs_path = self._registry.resolve_path(repo_id)

        # 构建目录结构
        use_mode = mode or self._default_mode
        base_dir = os.path.join(self._runs_root, run_id, "worktrees", repo_id)
        workdir = os.path.join(base_dir, "repo")
        artifacts_dir = os.path.join(base_dir, "artifacts")
        evidence_dir = os.path.join(base_dir, "evidence")
        logs_dir = os.path.join(base_dir, "logs")

        # 如果目录已存在（从之前的 run 恢复），直接复用
        if os.path.exists(workdir):
            logger.info(f"Reusing existing worktree: {workdir}")
        else:
            # 创建子目录
            for d in [artifacts_dir, evidence_dir, logs_dir]:
                os.makedirs(d, exist_ok=True)

            # 创建工作区
            if use_mode == "symlink":
                self._create_symlink(repo_abs_path, workdir)
            elif use_mode == "worktree":
                self._create_git_worktree(
                    repo_abs_path, workdir,
                    branch=branch or repo.default_branch,
                )
            elif use_mode == "copy":
                self._create_copy(repo_abs_path, workdir)
            else:
                raise ValueError(f"Unknown worktree mode: {use_mode}")

        info = WorktreeInfo(
            run_id=run_id,
            repo_id=repo_id,
            workdir=workdir,
            artifacts_dir=artifacts_dir,
            evidence_dir=evidence_dir,
            logs_dir=logs_dir,
            created_at=datetime.utcnow().isoformat(),
            mode=use_mode,
        )

        # Cache
        self._allocated[cache_key] = info

        # Persist metadata
        self._write_metadata(base_dir, info)

        logger.info(
            f"Allocated worktree: run={run_id} repo={repo_id} "
            f"mode={use_mode} dir={workdir}"
        )
        return info

    # ── Query ─────────────────────────────────────────────────────

    def get_workdir(self, run_id: str, repo_id: str) -> str:
        """
        获取已分配的工作目录

        Args:
            run_id: 运行 ID
            repo_id: repo 标识

        Returns:
            工作目录路径

        Raises:
            ValueError: 如果未分配
        """
        cache_key = f"{run_id}:{repo_id}"
        info = self._allocated.get(cache_key)

        if info is not None:
            return info.workdir

        # 尝试从文件系统恢复
        base_dir = os.path.join(self._runs_root, run_id, "worktrees", repo_id)
        workdir = os.path.join(base_dir, "repo")
        if os.path.exists(workdir):
            return workdir

        raise ValueError(
            f"No worktree allocated for run={run_id}, repo={repo_id}"
        )

    def list_worktrees(self, run_id: str) -> List[WorktreeInfo]:
        """列出 run 下所有已分配的 worktree"""
        result = []

        # From cache
        for key, info in self._allocated.items():
            if info.run_id == run_id:
                result.append(info)

        # From filesystem (if not in cache)
        cached_repos = {info.repo_id for info in result}
        worktrees_dir = os.path.join(self._runs_root, run_id, "worktrees")
        if os.path.isdir(worktrees_dir):
            for repo_id in os.listdir(worktrees_dir):
                if repo_id in cached_repos:
                    continue
                meta = self._read_metadata(
                    os.path.join(worktrees_dir, repo_id)
                )
                if meta:
                    result.append(meta)

        return result

    def list_active_runs_for_repo(self, repo_id: str) -> List[str]:
        """
        列出对某个 repo 有活跃 worktree 的所有 run_id

        用于并行安全检查：如果有其他 run 正在使用同一 repo，
        则新 run 应自动升级为 worktree 模式以实现真正隔离。

        Returns:
            活跃的 run_id 列表
        """
        active_runs = []

        # From in-memory cache
        for key, info in self._allocated.items():
            if info.repo_id == repo_id:
                active_runs.append(info.run_id)

        # From filesystem (scan runs_root)
        cached_run_ids = set(active_runs)
        if os.path.isdir(self._runs_root):
            for run_id in os.listdir(self._runs_root):
                if run_id in cached_run_ids:
                    continue
                wt_dir = os.path.join(
                    self._runs_root, run_id, "worktrees", repo_id
                )
                if os.path.isdir(wt_dir):
                    meta = self._read_metadata(wt_dir)
                    if meta:
                        active_runs.append(run_id)

        return active_runs

    # ── Release ───────────────────────────────────────────────────

    def release(self, run_id: str, repo_id: str) -> None:
        """
        释放 worktree（清理 git worktree，保留目录用于审计）

        注意：symlink 和 copy 模式不需要 git 清理。
        """
        cache_key = f"{run_id}:{repo_id}"
        info = self._allocated.pop(cache_key, None)

        if info and info.mode == "worktree":
            try:
                repo_abs_path = self._registry.resolve_path(repo_id)
                subprocess.run(
                    ["git", "worktree", "remove", "--force", info.workdir],
                    cwd=repo_abs_path,
                    capture_output=True,
                    timeout=30,
                )
                logger.info(f"Released git worktree: {info.workdir}")
            except Exception as e:
                logger.warning(f"Failed to release git worktree: {e}")

        logger.info(f"Released worktree: run={run_id} repo={repo_id}")

    # ── Validation ────────────────────────────────────────────────

    def validate_workdir(self, run_id: str, repo_id: str) -> bool:
        """
        硬校验工作目录的 git root 是否匹配

        Returns:
            True = 校验通过
        """
        try:
            workdir = self.get_workdir(run_id, repo_id)
        except ValueError:
            return False

        return self._registry.validate_git_root(repo_id, workdir)

    # ── Diff / Patch ──────────────────────────────────────────────

    def get_diff_stat(self, run_id: str, repo_id: str) -> Optional[str]:
        """
        获取 worktree 中的 git diff stat

        Returns:
            diff stat 文本，或 None
        """
        try:
            workdir = self.get_workdir(run_id, repo_id)
        except ValueError:
            return None

        try:
            result = subprocess.run(
                ["git", "diff", "--stat"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout.strip()
            return None
        except Exception:
            return None

    def export_patch(self, run_id: str, repo_id: str) -> Optional[str]:
        """
        导出 worktree 的 git diff 作为 patch

        Returns:
            patch 内容，或 None
        """
        try:
            workdir = self.get_workdir(run_id, repo_id)
        except ValueError:
            return None

        try:
            result = subprocess.run(
                ["git", "diff"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.returncode == 0 and result.stdout.strip():
                return result.stdout
            return None
        except Exception:
            return None

    def get_git_status(self, run_id: str, repo_id: str) -> Optional[str]:
        """
        获取 worktree 的 git status --porcelain
        
        Returns:
            status 文本，或 None
        """
        try:
            workdir = self.get_workdir(run_id, repo_id)
        except ValueError:
            return None

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None

    def get_current_commit(self, run_id: str, repo_id: str) -> Optional[str]:
        """
        获取当前 commit hash (HEAD)
        
        Returns:
            commit sha, 或 None
        """
        try:
            workdir = self.get_workdir(run_id, repo_id)
        except ValueError:
            return None

        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=workdir,
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                return result.stdout.strip()
            return None
        except Exception:
            return None

    # ── Internal Helpers ──────────────────────────────────────────

    @staticmethod
    def _create_symlink(source: str, target: str) -> None:
        """创建符号链接"""
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        os.symlink(source, target)
        logger.debug(f"Created symlink: {target} -> {source}")

    @staticmethod
    def _create_git_worktree(
        repo_path: str, target: str, branch: str = "main"
    ) -> None:
        """创建 git worktree"""
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        result = subprocess.run(
            ["git", "worktree", "add", target, "-b",
             f"lee/worktree/{os.path.basename(target)}", branch],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if result.returncode != 0:
            # Try without creating a new branch
            result = subprocess.run(
                ["git", "worktree", "add", "--detach", target, branch],
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.returncode != 0:
                raise RuntimeError(
                    f"Failed to create git worktree: {result.stderr.strip()}"
                )
        logger.debug(f"Created git worktree: {target} from {repo_path}")

    @staticmethod
    def _create_copy(source: str, target: str) -> None:
        """复制仓库（排除 .git 大文件）"""
        import shutil
        parent = os.path.dirname(target)
        os.makedirs(parent, exist_ok=True)
        shutil.copytree(
            source, target,
            ignore=shutil.ignore_patterns(".git"),
        )
        logger.debug(f"Copied repo: {source} -> {target}")

    @staticmethod
    def _write_metadata(base_dir: str, info: WorktreeInfo) -> None:
        """持久化 worktree 元数据"""
        meta_path = os.path.join(base_dir, "worktree.json")
        os.makedirs(base_dir, exist_ok=True)
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(asdict(info), f, indent=2, ensure_ascii=False)

    @staticmethod
    def _read_metadata(base_dir: str) -> Optional[WorktreeInfo]:
        """从文件系统读取 worktree 元数据"""
        meta_path = os.path.join(base_dir, "worktree.json")
        if not os.path.exists(meta_path):
            return None
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return WorktreeInfo(**data)
        except Exception:
            return None
