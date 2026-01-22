"""
Project Config - 项目配置管理

管理项目的仓库注册表和路径别名，实现路径的标准化解析。
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from dataclasses import dataclass, field


@dataclass
class Repository:
    """仓库定义"""
    id: str
    type: str = "git"  # git | local | remote
    path: str = ""
    description: str = ""
    branch: str = "main"

    def exists(self, base_path: Path) -> bool:
        """检查仓库是否存在"""
        resolved = (base_path / self.path).resolve()
        return resolved.exists()

    def resolve(self, base_path: Path) -> Path:
        """解析为绝对路径"""
        return (base_path / self.path).resolve()


@dataclass
class ProjectConfig:
    """项目配置"""
    id: str
    name: str
    base_path: Path
    repositories: Dict[str, Repository] = field(default_factory=dict)
    path_aliases: Dict[str, str] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)

    # 内置别名
    BUILTIN_ALIASES = {
        "@openspec": "./openspec",
        "@output": "./output",
    }

    @classmethod
    def load(cls, project_dir: str) -> Optional["ProjectConfig"]:
        """从 project.yaml 加载配置

        Args:
            project_dir: 项目目录或其子目录

        Returns:
            ProjectConfig 实例，如果没有找到配置文件则返回 None
        """
        project_yaml = cls._find_project_yaml(project_dir)
        if not project_yaml:
            return None

        with open(project_yaml, encoding='utf-8') as f:
            data = yaml.safe_load(f)

        base_path = project_yaml.parent

        # 解析仓库
        repositories = {}
        for repo_id, repo_data in data.get("repositories", {}).items():
            if isinstance(repo_data, str):
                # 简写格式: frontend: "../../git/frontend"
                repositories[repo_id] = Repository(id=repo_id, path=repo_data)
            elif isinstance(repo_data, dict):
                repositories[repo_id] = Repository(
                    id=repo_id,
                    type=repo_data.get("type", "git"),
                    path=repo_data.get("path", ""),
                    description=repo_data.get("description", ""),
                    branch=repo_data.get("branch", "main")
                )

        # 解析路径别名
        path_aliases = dict(cls.BUILTIN_ALIASES)
        for alias, target in data.get("path_aliases", {}).items():
            path_aliases[alias] = target

        return cls(
            id=data.get("id", "unknown"),
            name=data.get("name", "Unknown Project"),
            base_path=base_path,
            repositories=repositories,
            path_aliases=path_aliases,
            metadata=data.get("metadata", {})
        )

    @classmethod
    def _find_project_yaml(cls, start_dir: str) -> Optional[Path]:
        """向上查找 project.yaml"""
        current = Path(start_dir).resolve()

        # 最多向上查找 10 层
        for _ in range(10):
            project_yaml = current / "project.yaml"
            if project_yaml.exists():
                return project_yaml

            parent = current.parent
            if parent == current:
                break
            current = parent

        return None

    def resolve_path(self, path: str, context_dir: Path = None) -> str:
        """解析路径别名和变量

        Args:
            path: 原始路径 (可能包含 @alias 或 ${var})
            context_dir: 上下文目录 (用于解析 @openspec 等相对路径)

        Returns:
            解析后的绝对路径
        """
        if not path:
            return path

        resolved = path
        use_project_base = False  # 是否使用项目根目录作为基准

        # 1. 处理 @alias
        for alias, target in self.path_aliases.items():
            if resolved.startswith(alias):
                # 先解析 target 中的变量
                expanded_target = self._expand_variables(target)
                resolved = resolved.replace(alias, expanded_target, 1)

                # 仓库别名 (@frontend, @backend) 使用项目根目录
                # 内置别名 (@openspec, @output) 使用上下文目录
                if alias not in self.BUILTIN_ALIASES:
                    use_project_base = True
                break

        # 2. 处理 ${repositories.xxx} 和其他变量
        resolved = self._expand_variables(resolved)

        # 3. 确定基准目录
        # - 仓库路径: 相对于 project.yaml 所在目录 (self.base_path)
        # - 本地路径 (@openspec): 相对于 workflow 所在目录 (context_dir)
        if use_project_base:
            base = self.base_path
        else:
            base = context_dir if context_dir else self.base_path

        # 4. 转为绝对路径 (如果还不是绝对路径)
        if not Path(resolved).is_absolute():
            resolved = str((base / resolved).resolve())

        return resolved

    def _expand_variables(self, text: str) -> str:
        """展开变量引用"""
        if not text:
            return text

        # 匹配 ${xxx} 或 ${xxx.yyy}
        pattern = r'\$\{([^}]+)\}'

        def replace(match):
            var_path = match.group(1)
            parts = var_path.split('.')

            if parts[0] == "repositories" and len(parts) >= 2:
                repo_id = parts[1]
                if repo_id in self.repositories:
                    repo = self.repositories[repo_id]
                    if len(parts) == 2 or parts[2] == "path":
                        return repo.path
                    elif parts[2] == "branch":
                        return repo.branch
            elif parts[0] == "project":
                if len(parts) >= 2:
                    if parts[1] == "id":
                        return self.id
                    elif parts[1] == "name":
                        return self.name

            # 未知变量，保持原样
            return match.group(0)

        return re.sub(pattern, replace, text)

    def get_repository(self, repo_id: str) -> Optional[Repository]:
        """获取仓库配置"""
        return self.repositories.get(repo_id)

    def check_repositories(self) -> Dict[str, bool]:
        """检查所有仓库是否存在"""
        result = {}
        for repo_id, repo in self.repositories.items():
            result[repo_id] = repo.exists(self.base_path)
        return result

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "kind": "project",
            "version": "1.0",
            "id": self.id,
            "name": self.name,
            "repositories": {
                repo_id: {
                    "type": repo.type,
                    "path": repo.path,
                    "description": repo.description,
                    "branch": repo.branch
                }
                for repo_id, repo in self.repositories.items()
            },
            "path_aliases": {
                k: v for k, v in self.path_aliases.items()
                if k not in self.BUILTIN_ALIASES
            },
            "metadata": self.metadata
        }

    def save(self, path: str = None):
        """保存配置到文件"""
        save_path = Path(path) if path else self.base_path / "project.yaml"
        with open(save_path, 'w', encoding='utf-8') as f:
            yaml.dump(self.to_dict(), f, allow_unicode=True, default_flow_style=False, sort_keys=False)


def create_project_config(
    project_dir: str,
    project_id: str,
    project_name: str,
    repositories: Dict[str, str] = None
) -> ProjectConfig:
    """创建新的项目配置

    Args:
        project_dir: 项目目录
        project_id: 项目 ID
        project_name: 项目名称
        repositories: 仓库映射 {repo_id: path}

    Returns:
        新建的 ProjectConfig 实例
    """
    base_path = Path(project_dir).resolve()

    repos = {}
    if repositories:
        for repo_id, repo_path in repositories.items():
            repos[repo_id] = Repository(id=repo_id, path=repo_path)

    # 默认别名
    aliases = dict(ProjectConfig.BUILTIN_ALIASES)
    for repo_id in repos:
        aliases[f"@{repo_id}"] = f"${{repositories.{repo_id}.path}}"

    config = ProjectConfig(
        id=project_id,
        name=project_name,
        base_path=base_path,
        repositories=repos,
        path_aliases=aliases
    )

    return config
