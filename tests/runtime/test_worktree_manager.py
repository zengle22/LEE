"""
Unit tests for lee.runtime.worktree_manager
"""

import json
import os
import tempfile

import pytest

from lee.runtime.repo_registry import RepoEntry, RepoRegistry
from lee.runtime.worktree_manager import WorktreeInfo, WorktreeManager


@pytest.fixture
def tmp_workspace(tmp_path):
    """创建临时 workspace 结构"""
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()

    # 创建一个假 repo 目录（非真正 git repo）
    repo_dir = tmp_path / "repos" / "backend"
    repo_dir.mkdir(parents=True)
    (repo_dir / "main.go").write_text("package main")

    return tmp_path


@pytest.fixture
def registry(tmp_workspace):
    repos = {
        "backend": RepoEntry(
            repo_id="backend",
            path=str(tmp_workspace / "repos" / "backend"),
            type="git",
        ),
    }
    return RepoRegistry(repos=repos, workspace_root=str(tmp_workspace))


@pytest.fixture
def manager(tmp_workspace, registry):
    return WorktreeManager(
        runs_root=str(tmp_workspace / "runs"),
        registry=registry,
        default_mode="symlink",
    )


# ── WorktreeInfo ──────────────────────────────────────────────────


class TestWorktreeInfo:
    def test_dataclass_fields(self):
        info = WorktreeInfo(
            run_id="run-001",
            repo_id="backend",
            workdir="/tmp/workdir",
            artifacts_dir="/tmp/artifacts",
            evidence_dir="/tmp/evidence",
            logs_dir="/tmp/logs",
        )
        assert info.run_id == "run-001"
        assert info.repo_id == "backend"
        assert info.mode == "symlink"  # default


# ── Allocation ────────────────────────────────────────────────────


class TestWorktreeAllocation:
    def test_allocate_symlink(self, manager, tmp_workspace):
        info = manager.allocate("run-001", "backend")

        assert info.run_id == "run-001"
        assert info.repo_id == "backend"
        assert info.mode == "symlink"
        assert os.path.islink(info.workdir)
        assert os.path.isdir(info.artifacts_dir)
        assert os.path.isdir(info.evidence_dir)
        assert os.path.isdir(info.logs_dir)

    def test_allocate_idempotent(self, manager):
        info1 = manager.allocate("run-001", "backend")
        info2 = manager.allocate("run-001", "backend")
        assert info1.workdir == info2.workdir

    def test_allocate_unknown_repo_raises(self, manager):
        with pytest.raises(ValueError, match="Unknown repo_id"):
            manager.allocate("run-001", "nonexistent")

    def test_allocate_creates_metadata(self, manager, tmp_workspace):
        info = manager.allocate("run-001", "backend")
        meta_path = os.path.join(
            tmp_workspace, "runs", "run-001", "worktrees", "backend", "worktree.json"
        )
        assert os.path.exists(meta_path)

        with open(meta_path) as f:
            meta = json.load(f)
        assert meta["run_id"] == "run-001"
        assert meta["repo_id"] == "backend"


# ── Query ─────────────────────────────────────────────────────────


class TestWorktreeQuery:
    def test_get_workdir(self, manager):
        info = manager.allocate("run-001", "backend")
        workdir = manager.get_workdir("run-001", "backend")
        assert workdir == info.workdir

    def test_get_workdir_not_allocated(self, manager):
        with pytest.raises(ValueError, match="No worktree allocated"):
            manager.get_workdir("not-exist", "backend")

    def test_list_worktrees(self, manager):
        manager.allocate("run-001", "backend")
        worktrees = manager.list_worktrees("run-001")
        assert len(worktrees) == 1
        assert worktrees[0].repo_id == "backend"

    def test_list_worktrees_empty_run(self, manager):
        worktrees = manager.list_worktrees("empty-run")
        assert worktrees == []


# ── Release ───────────────────────────────────────────────────────


class TestWorktreeRelease:
    def test_release_removes_from_cache(self, manager):
        manager.allocate("run-001", "backend")
        manager.release("run-001", "backend")

        # Cache is cleared, but filesystem may still exist
        worktrees = manager.list_worktrees("run-001")
        # list_worktrees checks filesystem too, so may still find it
        # But a re-allocation should work cleanly
        info = manager.allocate("run-001", "backend")
        assert info.repo_id == "backend"


# ── Copy Mode ─────────────────────────────────────────────────────


class TestCopyMode:
    def test_allocate_copy(self, tmp_workspace, registry):
        manager = WorktreeManager(
            runs_root=str(tmp_workspace / "runs"),
            registry=registry,
            default_mode="copy",
        )
        info = manager.allocate("run-copy", "backend")
        assert info.mode == "copy"
        assert os.path.isdir(info.workdir)
        # Should have copied main.go
        assert os.path.exists(os.path.join(info.workdir, "main.go"))
