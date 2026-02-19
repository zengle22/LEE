
import pytest
import os
from unittest.mock import MagicMock
from lee.orchestrator.execution.patch_output import PatchCollector, PatchBundle
from lee.runtime.worktree_manager import WorktreeManager

@pytest.fixture
def patch_env(tmp_path):
    # Setup workdir structure: parent/repo_name
    # PatchCollector uses os.path.dirname(workdir) / "artifacts"
    runs_dir = tmp_path / "run_dir"
    runs_dir.mkdir()
    
    workdir = runs_dir / "repo"
    workdir.mkdir()
    
    return runs_dir, workdir

def test_collect_patch_success(patch_env):
    """Test successful patch collection"""
    runs_dir, workdir = patch_env
    
    mgr = MagicMock(spec=WorktreeManager)
    mgr.get_workdir.return_value = str(workdir)
    # Simulate git command outputs
    mgr.export_patch.return_value = "diff --git a/file.txt b/file.txt\n..."
    mgr.get_diff_stat.return_value = " file.txt | 2 +-\n 1 file changed, 1 insertion(+), 1 deletion(-)"
    mgr.get_git_status.return_value = " M file.txt"
    
    collector = PatchCollector(mgr)
    bundle = collector.collect("run-1", "step-1", "repo-1")
    
    # Verify bundle stats
    assert bundle.files_changed == 1
    assert bundle.insertions == 1
    assert bundle.deletions == 1
    assert not bundle.is_empty
    assert bundle.patch_hash
    
    # Verify artifacts on disk
    artifacts_dir = runs_dir / "artifacts"
    assert artifacts_dir.exists()
    assert (artifacts_dir / "step-1.patch").exists()
    assert (artifacts_dir / "step-1.stat").exists()
    assert (artifacts_dir / "step-1.status.txt").exists()
    
    # Check content
    assert (artifacts_dir / "step-1.status.txt").read_text() == " M file.txt"

def test_collect_empty_patch(patch_env):
    """Test collection when no changes exist"""
    runs_dir, workdir = patch_env
    
    mgr = MagicMock(spec=WorktreeManager)
    mgr.get_workdir.return_value = str(workdir)
    mgr.export_patch.return_value = ""
    mgr.get_diff_stat.return_value = ""
    mgr.get_git_status.return_value = ""
    
    collector = PatchCollector(mgr)
    bundle = collector.collect("run-1", "step-1", "repo-1")
    
    assert bundle.is_empty
    assert bundle.files_changed == 0
    assert bundle.patch_hash  # Hash of empty string
    
    artifacts_dir = runs_dir / "artifacts"
    # Artifacts should still be created for traceability
    assert (artifacts_dir / "step-1.patch").exists()
