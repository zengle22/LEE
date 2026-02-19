
import pytest
import os
from unittest.mock import MagicMock, patch
from lee.orchestrator.execution.context_index import ContextIndex

@pytest.fixture
def mock_registry():
    registry = MagicMock()
    registry.resolve_path.return_value = "/tmp/fake-repo"
    return registry

def test_tree_summary(mock_registry):
    index = ContextIndex(mock_registry)
    
    with patch("os.path.isdir", return_value=True), \
         patch("subprocess.run") as mock_run:
        
        mock_run.return_value = MagicMock(returncode=0, stdout="./src\n./tests\n./README.md")
        
        summary = index.build_tree_summary("my-repo")
        
        assert "Tree Summary" in summary or "Repo Tree" in summary
        assert "./src" in summary
        mock_run.assert_called_once()

def test_diff_summary(mock_registry):
    index = ContextIndex(mock_registry)
    
    with patch("os.path.isdir", return_value=True), \
         patch("subprocess.run") as mock_run:
        
        mock_run.return_value = MagicMock(returncode=0, stdout="abc1234 Initial commit\ndef5678 Add feature")
        
        summary = index.build_diff_summary("my-repo")
        
        assert "Recent Changes" in summary
        assert "abc1234" in summary
        mock_run.assert_called_once()

def test_extract_configs(mock_registry):
    index = ContextIndex(mock_registry)
    
    with patch("os.path.isdir", return_value=True), \
         patch("os.walk") as mock_walk:
        
        # Mocking os.walk return values
        # (root, dirs, files)
        mock_walk.return_value = [
            ("/tmp/fake-repo", ["src", "config"], ["README.md"]),
            ("/tmp/fake-repo/config", [], ["app.yaml", "db.json"])
        ]
        
        configs = index.extract_configs("my-repo")
        
        # Paths are relative to abs_path
        # os.path.relpath("/tmp/fake-repo/config/app.yaml", "/tmp/fake-repo") -> "config/app.yaml"
        assert "config/app.yaml" in configs
        assert "config/db.json" in configs
        assert configs["config/app.yaml"] == "config"
