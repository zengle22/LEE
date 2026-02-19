
import os
import shutil
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path

from lee.runtime.worktree_manager import WorktreeManager, WorktreeInfo
from lee.runtime.repo_registry import RepoRegistry

@pytest.fixture
def temp_workspace(tmp_path):
    root = tmp_path / "lee_root"
    root.mkdir()
    runs_root = root / "runs"
    runs_root.mkdir()
    
    # Mock registry setup
    repo_dir = root / "my-repo"
    repo_dir.mkdir()
    (repo_dir / ".git").mkdir()
    (repo_dir / "README.md").write_text("hello")
    
    registry = MagicMock(spec=RepoRegistry)
    registry.resolve_path.return_value = str(repo_dir)
    registry.get_repo_or_raise.return_value = MagicMock(default_branch="main")
    registry.validate_git_root.return_value = True
    
    return runs_root, registry, repo_dir

def test_allocate_symlink(temp_workspace):
    """Test standard symlink allocation"""
    runs_root, registry, repo_dir = temp_workspace
    mgr = WorktreeManager(str(runs_root), registry)
    
    info = mgr.allocate("run-1", "repo-1", mode="symlink")
    
    assert info.mode == "symlink"
    assert os.path.islink(info.workdir)
    # Fix: use os.readlink
    assert os.readlink(info.workdir) == str(repo_dir)
    assert mgr.validate_workdir("run-1", "repo-1")

def test_auto_upgrade_logic(temp_workspace):
    """Test the logic that orchestrator would use to upgrade mode"""
    runs_root, registry, repo_dir = temp_workspace
    mgr = WorktreeManager(str(runs_root), registry)
    
    # 1. Start first run (symlink)
    mgr.allocate("run-1", "repo-1", mode="symlink")
    
    # 2. Check active runs
    active = mgr.list_active_runs_for_repo("repo-1")
    assert "run-1" in active
    
    # 3. Simulate Orchestrator logic for second run
    # If active runs exist and current run not in them -> upgrade
    current_run = "run-2"
    mode = "worktree" if len(active) > 0 and current_run not in active else None
    
    assert mode == "worktree"
    
def test_allocate_worktree_mocked(temp_workspace):
    """Test worktree allocation with git operations mocked"""
    runs_root, registry, repo_dir = temp_workspace
    mgr = WorktreeManager(str(runs_root), registry)
    
    # Mock internal git worktree creation to avoid actual git calls in test env
    with patch.object(mgr, '_create_git_worktree') as mock_create:
        info = mgr.allocate("run-worktree", "repo-1", mode="worktree")
        
        assert info.mode == "worktree"
        mock_create.assert_called_once()
        # Verify call args instead of directory existence
        args, _ = mock_create.call_args
        assert args[1] == info.workdir

def test_get_git_status_mocked(temp_workspace):
    """Test git status retrieval"""
    runs_root, registry, repo_dir = temp_workspace
    mgr = WorktreeManager(str(runs_root), registry)
    
    # Allocate first
    mgr.allocate("run-status", "repo-1", mode="symlink")
    
    with patch("subprocess.run") as mock_run:
        mock_run.return_value.returncode = 0
        mock_run.return_value.stdout = " M modified_file.py"
        
        status = mgr.get_git_status("run-status", "repo-1")
        assert status == " M modified_file.py"
        mock_run.assert_called()

def test_validate_failure(temp_workspace):
    """Test validation fails for non-existent run"""
    runs_root, registry, repo_dir = temp_workspace
    mgr = WorktreeManager(str(runs_root), registry)
    
    assert not mgr.validate_workdir("non-existent", "repo-1")
