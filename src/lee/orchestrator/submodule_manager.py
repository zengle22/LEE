"""
Submodule Manager

提供 submodule 检测和管理功能，用于 workspace-cleanup 工作流支持多仓库处理。
"""

from pathlib import Path
from typing import List, Dict, Optional
import subprocess
import configparser
import os


class SubmoduleInfo:
    """Submodule 信息"""
    def __init__(self, path: str, url: str, name: str = None):
        self.path = path  # 相对路径，如 dev/src/ai-marathon-coach-front
        self.url = url
        self.name = name or path.split('/')[-1]

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "url": self.url,
            "name": self.name,
            "type": "submodule"
        }


class ExecutionMode:
    """执行模式"""
    MAIN = "main"      # 主仓库运行
    SUBMODULE = "submodule"  # Submodule 运行


class SubmoduleManager:
    """Submodule 检测与管理"""

    @staticmethod
    def is_git_repo(path: str) -> bool:
        """检查路径是否是 git 仓库"""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=path,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    @staticmethod
    def is_submodule(workspace_path: str) -> bool:
        """
        检查当前路径是否是 submodule

        判断方法（多种方式）：
        1. 检查 .git 文件是否是文件（而不是目录）- 标准 submodule
        2. 检查 .git 是否是符号链接
        3. 检查路径是否在 .gitmodules 记录的某个 submodule 路径下
        """
        git_path = Path(workspace_path) / ".git"

        # 方法 1: 检查 .git 文件（标准 submodule）
        if git_path.is_file():
            with open(git_path, 'r') as f:
                content = f.read().strip()
                return content.startswith("gitdir:")

        # 方法 2: 检查 .git 是否是符号链接
        if git_path.is_symlink():
            return True

        return False

    @staticmethod
    def find_git_root(start_path: str) -> Optional[str]:
        """向上查找最近的 git 仓库根目录"""
        current = Path(start_path).resolve()

        while True:
            git_dir = current / ".git"
            if git_dir.exists():
                # 检查是否是 submodule
                if git_dir.is_file():
                    # 读取 gitdir 指向的路径
                    with open(git_dir, 'r') as f:
                        content = f.read().strip()
                        if content.startswith("gitdir:"):
                            # 提取实际 .git 目录路径
                            git_dir_path = content[8:].strip()
                            if not os.path.isabs(git_dir_path):
                                git_dir_path = str(current / git_dir_path)
                            # 向上查找主仓库
                            parent = Path(git_dir_path).parent.parent
                            if SubmoduleManager.is_git_repo(str(parent)):
                                return str(parent)
                return str(current)

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    @staticmethod
    def find_superproject_root(start_path: str) -> Optional[str]:
        """
        向上查找父项目（superproject）根目录。
        如果当前在 submodule 中，返回主仓库路径。
        """
        current = Path(start_path).resolve()

        # 检查当前路径是否在 .gitmodules 记录的某个 submodule 路径下
        while True:
            gitmodules = current / ".gitmodules"
            if gitmodules.exists():
                config = configparser.ConfigParser()
                try:
                    config.read(gitmodules)
                    # 检查当前路径是否匹配任何 submodule
                    for section in config.sections():
                        if section.startswith("submodule "):
                            sub_path = config.get(section, "path", fallback="")
                            if sub_path:
                                sub_full = current / sub_path
                                # 如果当前路径就是或包含这个 submodule 路径
                                if str(sub_full) == str(start_path) or str(start_path).startswith(str(sub_full) + os.sep):
                                    # 找到父项目
                                    return str(current)
                except Exception:
                    pass

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    @staticmethod
    def discover_submodules(root_path: str) -> List[SubmoduleInfo]:
        """
        从 .gitmodules 发现所有 submodule

        Args:
            root_path: 仓库根目录

        Returns:
            SubmoduleInfo 列表
        """
        submodules = []
        gitmodules_path = Path(root_path) / ".gitmodules"

        if not gitmodules_path.exists():
            return submodules

        # 解析 .gitmodules 文件
        config = configparser.ConfigParser()
        try:
            config.read(gitmodules_path)
        except Exception:
            return submodules

        for section in config.sections():
            if section.startswith("submodule "):
                path = config.get(section, "path", fallback="")
                url = config.get(section, "url", fallback="")
                if path and url:
                    submodules.append(SubmoduleInfo(path, url))

        return submodules

    @classmethod
    def detect_execution_mode(cls, workspace_path: str) -> Dict:
        """
        检测执行模式

        Args:
            workspace_path: 工作区路径

        Returns:
            {
                "execution_mode": "main" | "submodule",
                "root_path": 主仓库根目录,
                "current_path": 当前工作目录,
                "submodules": [SubmoduleInfo...],
                "target_repos": [
                    {"path": "dev/src/xxx", "type": "submodule"},
                    {"path": ".", "type": "main"}
                ]
            }
        """
        workspace_path = str(Path(workspace_path).resolve())

        # 检查是否是 git 仓库
        if not cls.is_git_repo(workspace_path):
            return {
                "execution_mode": "unknown",
                "root_path": None,
                "current_path": workspace_path,
                "submodules": [],
                "target_repos": [],
                "error": "Not a git repository"
            }

        # 首先尝试查找父项目（即使 .git 是目录）
        superproject_root = cls.find_superproject_root(workspace_path)

        # 检查是否是 submodule（标准方式：.git 是文件）
        is_sub = cls.is_submodule(workspace_path)

        if is_sub or superproject_root:
            # 在 submodule 中运行
            root_path = superproject_root or cls.find_git_root(workspace_path)
            if root_path:
                # 计算相对路径
                try:
                    rel_path = Path(workspace_path).relative_to(root_path)
                except ValueError:
                    rel_path = Path(workspace_path).name

                submodules = cls.discover_submodules(root_path)

                # 构建 target_repos（只有当前 submodule）
                target_repos = [
                    {"path": str(rel_path), "type": "submodule"},
                    {"path": ".", "type": "main"}
                ]

                return {
                    "execution_mode": ExecutionMode.SUBMODULE,
                    "root_path": root_path,
                    "current_path": workspace_path,
                    "submodules": [s.to_dict() for s in submodules],
                    "target_repos": target_repos
                }
            else:
                return {
                    "execution_mode": ExecutionMode.SUBMODULE,
                    "root_path": workspace_path,
                    "current_path": workspace_path,
                    "submodules": [],
                    "target_repos": [{"path": ".", "type": "main"}],
                    "error": "Cannot find git root for submodule"
                }
        else:
            # 主仓库运行（可能是主仓库本身，也可能是独立的仓库）
            root_path = cls.find_git_root(workspace_path) or workspace_path

            # 只有当存在 .gitmodules 时才查找 submodules
            gitmodules_path = Path(root_path) / ".gitmodules"
            if gitmodules_path.exists():
                submodules = cls.discover_submodules(root_path)
            else:
                submodules = []

            # 构建 target_repos（所有 submodules + main）
            target_repos = []
            for sm in submodules:
                target_repos.append({"path": sm.path, "type": "submodule"})
            target_repos.append({"path": ".", "type": "main"})

            # 判断是主仓库还是独立仓库
            has_submodules = len(submodules) > 0

            return {
                "execution_mode": ExecutionMode.MAIN if has_submodules else "standalone",
                "root_path": root_path,
                "current_path": workspace_path,
                "submodules": [s.to_dict() for s in submodules],
                "target_repos": target_repos
            }


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        workspace = sys.argv[1]
    else:
        workspace = os.getcwd()

    result = SubmoduleManager.detect_execution_mode(workspace)
    import json
    print(json.dumps(result, indent=2, ensure_ascii=False))
