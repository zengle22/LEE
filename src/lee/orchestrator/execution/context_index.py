"""
LEE Context Index
Provides repository-level summaries and configuration discovery for the PM Agent.
"""
import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class ContextIndex:
    """
    ContextIndex provides tools to explore and summarize repository structure and history.
    """
    def __init__(self, repo_registry):
        self.repo_registry = repo_registry
        # Minimal cache to avoid redundant shell calls in the same run
        self._cache = {}

    def build_tree_summary(self, repo_id: str, max_depth: int = 3) -> str:
        """
        Returns a string representation of the repo's file structure.
        """
        try:
            abs_path = self.repo_registry.resolve_path(repo_id)
            if not os.path.isdir(abs_path):
                return f"Error: Repository path not found or not a directory: {abs_path}"

            # Simple find-based tree
            cmd = ["find", ".", "-maxdepth", str(max_depth), "-not", "-path", '*/.*', "-not", "-path", "./node_modules*"]
            result = subprocess.run(cmd, cwd=abs_path, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return f"Error: failed to list files: {result.stderr.strip()}"
            
            lines = result.stdout.strip().split("\n")
            # Minimal formatting
            tree = f"# Repo Tree: {repo_id} (depth={max_depth})\n"
            tree += "\n".join(lines[:100]) # Limit to first 100 entries
            if len(lines) > 100:
                tree += f"\n... and {len(lines) - 100} more entries"
            return tree
        except Exception as e:
            logger.error(f"Failed to build tree summary for {repo_id}: {e}")
            return f"Error building tree summary: {str(e)}"

    def build_diff_summary(self, repo_id: str, n_commits: int = 5) -> str:
        """
        Returns a summary of the most recent commits.
        """
        try:
            abs_path = self.repo_registry.resolve_path(repo_id)
            if not os.path.isdir(abs_path):
                return f"Error: Repository path not found: {abs_path}"

            cmd = ["git", "log", "--oneline", "--stat", "-n", str(n_commits)]
            result = subprocess.run(cmd, cwd=abs_path, capture_output=True, text=True, timeout=10)
            
            if result.returncode != 0:
                return f"Error: failed to get git log: {result.stderr.strip()} (Is this a git repo?)"
            
            summary = f"# Recent Changes: {repo_id}\n{result.stdout.strip()}"
            return summary
        except Exception as e:
            logger.error(f"Failed to build diff summary for {repo_id}: {e}")
            return f"Error building diff summary: {str(e)}"

    def extract_configs(self, repo_id: str) -> Dict[str, str]:
        """
        Identifies and summarizes configuration files in the repo.
        """
        config_summary = {}
        try:
            abs_path = self.repo_registry.resolve_path(repo_id)
            extensions = {".yaml", ".yml", ".json", ".toml", ".ini", ".conf"}
            
            for root, dirs, files in os.walk(abs_path):
                # Prune hidden dirs
                dirs[:] = [d for d in dirs if not d.startswith('.')]
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in extensions:
                        rel_path = os.path.relpath(os.path.join(root, file), abs_path)
                        # Just identify existence for now, maybe read small snippets later
                        config_summary[rel_path] = "config"
                if len(config_summary) > 50: # Cap at 50 config files
                    break
        except Exception as e:
            logger.error(f"Failed to extract configs for {repo_id}: {e}")
            config_summary["error"] = str(e)
            
        return config_summary
