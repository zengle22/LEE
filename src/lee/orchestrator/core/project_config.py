"""
Project Config - 项目配置管理

管理项目的：
1. 仓库注册表和路径别名，实现路径的标准化解析
2. 目录结构初始化和验证，防止目录飘逸
"""

import re
import yaml
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import warnings


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
        is_posix_absolute = resolved.startswith("/")
        if not is_posix_absolute and not Path(resolved).is_absolute():
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


# ============================================
# Directory Structure Configuration
# ============================================

# Standard directory structure schema (ADR-0020)
# Boundary:
# - dirs.yaml owns directory topology and placement only
# - SSOT identity layer owns governed artifact IDs, filenames, and references
DEFAULT_DIRECTORY_SCHEMA = {
    "version": "2.0",
    "description": "LEE Standard Project Directory Topology",
    "directories": {
        # Configuration
        "config_dir": {
            "path": ".project",
            "description": "LEE project configuration and metadata (SSOT of project)",
            "subdirs": ["registry"],
            "structure": "flat",
            "create_readme": True,
            "is_project_config": True,
        },

        # Workflow state
        "workflow_dir": {
            "path": ".workflow",
            "description": "Workflow execution state (cleanable/rebuildable)",
            "subdirs": ["runs", "cache", "traces", "evidence", "tokens", "compliance", "env-check", "instances", "approvals"],
            "structure": "flat",
            "cleanup": "auto",
        },

        # Artifacts
        "artifacts_dir": {
            "path": ".artifacts",
            "description": "Build artifacts (long-term retention/traceable)",
            "subdirs": ["active", "frozen", "archive"],
            "structure": "layered",
        },

        # Specifications
        "spec_dir": {
            "path": "spec",
            "description": "Specification SSOT (gate-able, freezable)",
            "subdirs": ["requirements", "api", "data", "ui", "adr", "dev", "qa"],
            "structure": "flat",
            "create_readme": True,
            "copy_templates_from": "templates/spec",
        },

        # Contracts (frozen analysis outputs)
        "contracts_dir": {
            "path": "contracts",
            "description": "Frozen analysis results and formal contracts",
            "subdirs": ["input", "output"],
            "structure": "layered",
        },

        # Documentation
        "docs_dir": {
            "path": "docs",
            "description": "Explanatory documentation (guides, reports)",
            "subdirs": ["guides", "reports", "archive"],
            "structure": "flat",
            "naming": "descriptive",
        },

        # Knowledge
        "knowledge_dir": {
            "path": "knowledge",
            "description": "Knowledge distillation (retrospectives, patterns, evolution)",
            "subdirs": ["retrospectives", "patterns", "evolution"],
            "structure": "flat",
        },

        # Source code
        "src_dir": {
            "path": "src",
            "description": "Source code (backend/frontend separation recommended)",
            "subdirs": ["backend", "frontend"],
            "structure": "module",
        },

        # Tests
        "tests_dir": {
            "path": "tests",
            "description": "Test files (mirrors src structure)",
            "subdirs": ["unit", "integration", "e2e"],
            "structure": "hierarchical",
        },

        # Tools
        "tools_dir": {
            "path": "tools",
            "description": "Project tools (code generation, lint, self-check scripts)",
            "subdirs": [],
            "structure": "flat",
        },

        # Deploy
        "deploy_dir": {
            "path": "deploy",
            "description": "Deployment configuration (docker/helm/terraform)",
            "subdirs": [],
            "structure": "flat",
        },

        # Legacy
        "legacy_dir": {
            "path": "legacy",
            "description": "Legacy compatibility (read-only by default)",
            "subdirs": ["spec", "evidence", "env"],
            "structure": "flat",
            "cleanup": None,
        },
    },
    "constraints": {
        "strict_path_validation": True,
        "forbid_creation_outside_defined_dirs": True,
        "require_initialization": True,
        "allow_overrides": False
    }
}


@dataclass
class DirectoryConfig:
    """Directory configuration - 扩展版本（ADR-0020）"""
    name: str
    path: str
    description: str
    subdirs: List[str] = field(default_factory=list)
    structure: str = "flat"           # flat, layered, module, hierarchical
    naming: str = "default"           # default, descriptive, timestamped
    cleanup: Optional[str] = None     # auto, manual, none
    format: Optional[str] = None      # markdown, yaml, json (for docs/specs)
    
    # ADR-0020: 显式字段替代 extras Dict
    create_readme: bool = True                    # 是否生成 README
    readme_template: Optional[str] = None         # README 模板名称（None 用默认）
    copy_templates_from: Optional[str] = None     # 模板源路径（如 "templates/spec"）
    is_project_config: bool = False               # 是否为项目配置目录（创建 .project/README.md）


@dataclass
class DirectoryStructureConfig:
    """Directory structure configuration"""

    project_dir: Path
    version: str
    initialized_at: Optional[str] = None
    initialized_by: Optional[str] = None
    project_name: Optional[str] = None
    directories: Dict[str, DirectoryConfig] = field(default_factory=dict)
    # Legacy compatibility only. Governing filenames belongs to SSOT identity layer.
    naming_conventions: Dict[str, str] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    @property
    def project_content_dir(self) -> Path:
        """Get the project content directory (where all outputs go)"""
        if self.project_name:
            return self.project_dir / self.project_name
        return self.project_dir

    @classmethod
    def load(cls, project_dir: Path) -> 'DirectoryStructureConfig':
        """Load directory structure configuration from .project/dirs.yaml"""
        config_file = project_dir / ".project" / "dirs.yaml"

        if not config_file.exists():
            raise FileNotFoundError(
                f"Directory structure configuration not found: {config_file}\n\n"
                f"Please initialize the project first:\n"
                f"  python -m flowcore.orchestrator init {project_dir}"
            )

        with open(config_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert directories dict to DirectoryConfig objects
        directories = {}
        for name, dir_config in data.get("directories", {}).items():
            directories[name] = DirectoryConfig(name=name, **dir_config)

        return cls(
            project_dir=project_dir,
            version=data.get("version", "1.0"),
            initialized_at=data.get("initialized_at"),
            initialized_by=data.get("initialized_by"),
            project_name=data.get("project_name"),
            directories=directories,
            naming_conventions=data.get("file_naming_conventions", {}),
            constraints=data.get("constraints", {})
        )

    def save(self) -> None:
        """Save directory structure configuration to .project/dirs.yaml"""
        config_dir = self.project_dir / ".project"
        config_dir.mkdir(parents=True, exist_ok=True)

        # Convert DirectoryConfig objects back to dicts
        directories_dict = {}
        for name, dir_config in self.directories.items():
            directories_dict[name] = {
                "path": dir_config.path,
                "description": dir_config.description,
                "subdirs": dir_config.subdirs,
                "structure": dir_config.structure,
                "naming": dir_config.naming,
            }
            if dir_config.cleanup:
                directories_dict[name]["cleanup"] = dir_config.cleanup
            if dir_config.format:
                directories_dict[name]["format"] = dir_config.format
            # ADR-0020: 新字段
            if not dir_config.create_readme:
                directories_dict[name]["create_readme"] = dir_config.create_readme
            if dir_config.readme_template:
                directories_dict[name]["readme_template"] = dir_config.readme_template
            if dir_config.copy_templates_from:
                directories_dict[name]["copy_templates_from"] = dir_config.copy_templates_from
            if dir_config.is_project_config:
                directories_dict[name]["is_project_config"] = dir_config.is_project_config
            if dir_config.cleanup:
                directories_dict[name]["cleanup"] = dir_config.cleanup

        data = {
            "version": self.version,
            "description": "LEE Standard Project Directory Topology",
            "initialized_at": self.initialized_at,
            "initialized_by": self.initialized_by,
            "project_name": self.project_name,
            "directories": directories_dict,
            "constraints": self.constraints
        }

        # Backward compatibility only: keep legacy naming conventions when present.
        if self.naming_conventions:
            data["file_naming_conventions"] = self.naming_conventions

        config_file = config_dir / "dirs.yaml"
        with open(config_file, 'w', encoding='utf-8') as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    def get_directory_path(self, dir_name: str) -> Path:
        """Get full path for a directory"""
        if dir_name not in self.directories:
            raise ValueError(f"Unknown directory: {dir_name}")
        dir_config = self.directories[dir_name]
        # Config and workflow stay in project root, others in project content dir
        if dir_name in ["config_dir", "workflow_dir"]:
            return self.project_dir / dir_config.path
        return self.project_content_dir / dir_config.path

    def validate_output_path(self, output_path: str, output_type: str = "general") -> Tuple[bool, Optional[str]]:
        """
        Validate that an output path conforms to the configured structure

        Args:
            output_path: The output path (relative or absolute)
            output_type: Type of output (contract, doc, source, test, output)

        Returns:
            (is_valid, error_message)
        """
        path = Path(output_path)
        project_root = self.project_dir.resolve()
        is_posix_absolute = output_path.startswith("/")

        if is_posix_absolute and not path.is_absolute():
            return False, f"Path is outside project directory: {output_path}"
        if path.is_absolute():
            full_path = path.resolve()
            try:
                full_path.relative_to(project_root)
            except ValueError:
                return False, f"Path is outside project directory: {output_path}"
        else:
            full_path = (project_root / path).resolve()

        # Check if strict validation is enabled
        if not self.constraints.get("strict_path_validation", True):
            return True, None

        # Determine expected directory based on output type
        expected_dirs = {
            "contract": ["contracts_dir"],
            "doc": ["docs_dir"],
            "source": ["src_dir"],
            "test": ["tests_dir"],
            "output": ["outputs_dir", "workflow_dir"],
            "workflow": ["workflow_dir"],
            "general": list(self.directories.keys())
        }

        allowed_dir_names = expected_dirs.get(output_type, expected_dirs["general"])

        # Check if the path is within any allowed directory
        for dir_name in allowed_dir_names:
            dir_config = self.directories.get(dir_name)
            if dir_config:
                # Use get_directory_path to get full path (respects project_content_dir)
                dir_path = self.get_directory_path(dir_name).resolve()
                try:
                    full_path.relative_to(dir_path)
                    return True, None
                except ValueError:
                    continue

        # If creation outside defined dirs is forbidden
        if self.constraints.get("forbid_creation_outside_defined_dirs", True):
            allowed_paths = [str(self.get_directory_path(d)) for d in allowed_dir_names if d in self.directories]
            return False, (
                f"Path '{output_path}' is not within any configured directory.\n"
                f"Allowed directories: {', '.join(allowed_paths)}\n"
                f"Please update your output to use one of these directories."
            )

        return True, None

    def get_output_path(self, output_type: str, **kwargs) -> Path:
        """
        Get a derived path for runtime or legacy outputs.

        For governed SSOT artifacts, the directory comes from dirs.yaml/path config,
        while the filename must come from the SSOT identity layer.

        Args:
            output_type: Type of output (contract, doc, source, test, output)
            **kwargs: Additional parameters for path construction

        Returns:
            Full path for the output file
        """
        dir_mapping = {
            "contract": "contracts_dir",
            "doc": "docs_dir",
            "source": "src_dir",
            "test": "tests_dir",
            "output": "outputs_dir",
            "workflow": "workflow_dir"
        }

        dir_name = dir_mapping.get(output_type, "outputs_dir")
        base_path = self.get_directory_path(dir_name)

        # Apply naming convention
        if output_type == "contract":
            layer = kwargs.get("layer", "common")
            version = kwargs.get("version", "v1")
            name = kwargs.get("name", "contract")
            path = base_path / layer / version / f"{name}.yaml"

        elif output_type == "doc":
            category = kwargs.get("category", "general")
            date = kwargs.get("date", datetime.now().strftime("%Y-%m-%d"))
            title = kwargs.get("title", "document")
            safe_title = title.lower().replace(" ", "-").replace("/", "-")
            path = base_path / category / f"{date}-{safe_title}.md"

        elif output_type == "source":
            module = kwargs.get("module", "main")
            name = kwargs.get("name", "file")
            ext = kwargs.get("ext", "py")
            path = base_path / module / f"{name}.{ext}"

        elif output_type == "test":
            test_type = kwargs.get("type", "unit")
            name = kwargs.get("name", "test")
            ext = kwargs.get("ext", "py")
            path = base_path / test_type / f"{name}_test.{ext}"

        elif output_type == "output":
            step_id = kwargs.get("step_id", "general")
            name = kwargs.get("name", "output")
            ext = kwargs.get("ext", "txt")
            path = base_path / step_id / f"{name}.{ext}"

        elif output_type == "workflow":
            step_id = kwargs.get("step_id")
            name = kwargs.get("name", "response")
            ext = kwargs.get("ext", "txt")
            # workflow goes to .workflow/workspace/{step_id}/
            path = self.project_dir / ".workflow" / "workspace" / step_id / f"{name}.{ext}"

        else:
            # Default: just append to base path
            name = kwargs.get("name", "output")
            path = base_path / name

        # Create parent directories
        path.parent.mkdir(parents=True, exist_ok=True)

        return path


def init_project_structure(
    project_dir: Path,
    project_name: Optional[str] = None,
    config_schema: Optional[Dict] = None,
    force: bool = False,
    non_interactive: bool = False
) -> DirectoryStructureConfig:
    """
    Initialize a project with standard directory structure

    Args:
        project_dir: Project root directory
        project_name: Name of the project (will create subdirectory with this name)
        config_schema: Optional custom configuration schema
        force: Re-initialize even if already initialized
        non_interactive: Skip user confirmation prompts

    Returns:
        DirectoryStructureConfig object
    """
    project_dir = Path(project_dir).resolve()

    # === Project Name Resolution ===
    if not project_name:
        # Try to get from existing config
        config_file = project_dir / ".project" / "dirs.yaml"
        if config_file.exists() and not force:
            try:
                existing = DirectoryStructureConfig.load(project_dir)
                if existing.project_name:
                    project_name = existing.project_name
                    print(f"[INFO] Using existing project name: {project_name}")
            except:
                pass

        # If still no name, ask user
        if not project_name and not non_interactive:
            print("\n" + "="*60)
            print("PROJECT NAME REQUIRED")
            print("="*60)
            print("Please provide a name for your project.")
            print("This will create a subdirectory with all project outputs.")
            print()
            project_name = input("Project name (e.g., nutrition-app, calorie-tracker): ").strip()
            if not project_name:
                raise ValueError("Project name cannot be empty")

    # Validate project name
    if project_name:
        # Remove invalid characters
        import re
        project_name = re.sub(r'[^\w\-]', '-', project_name)
        # Remove leading/trailing dashes and dots
        project_name = project_name.strip('-.')

    # Create project subdirectory
    if project_name:
        project_content_dir = project_dir / project_name
        print(f"\n[INFO] Project content directory: {project_content_dir}")
        print(f"[INFO] All outputs will be organized under: {project_name}/")
    else:
        if non_interactive:
            # In non-interactive mode, use current directory
            project_content_dir = project_dir
            project_name = None
        else:
            raise ValueError("Project name is required in interactive mode")

    # Check if already initialized
    config_file = project_dir / ".project" / "dirs.yaml"
    if config_file.exists() and not force:
        try:
            config = DirectoryStructureConfig.load(project_dir)
            print(f"[INFO] Project structure already initialized at: {config.initialized_at}")
            print(f"[INFO] Use --force to re-initialize")
            return config
        except Exception as e:
            print(f"[WARN] Existing config found but invalid: {e}")
            print(f"[INFO] Re-initializing project structure...")

    # Use default or custom schema
    schema = config_schema or DEFAULT_DIRECTORY_SCHEMA

    # Create DirectoryStructureConfig
    config = DirectoryStructureConfig(
        project_dir=project_dir,
        project_name=project_name,
        version=schema["version"],
        initialized_at=datetime.now().isoformat(),
        initialized_by="lee-orchestrator",
        directories={},
        naming_conventions=schema.get("file_naming_conventions", {}),
        constraints=schema.get("constraints", {})
    )

    # Convert schema directories to DirectoryConfig objects
    for name, dir_config in schema.get("directories", {}).items():
        config.directories[name] = DirectoryConfig(name=name, **dir_config)

    # === Create all directories ===
    print(f"[INFO] Initializing project structure at: {project_dir}")
    print(f"[INFO] Creating directory structure...")

    for dir_name, dir_config in config.directories.items():
        # Determine base path
        if dir_name in ["config_dir", "workflow_dir"]:
            # Config and workflow stay in project root
            dir_path = project_dir / dir_config.path
        else:
            # All other directories go under project content directory
            dir_path = project_content_dir / dir_config.path

        dir_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        for subdir in dir_config.subdirs:
            (dir_path / subdir).mkdir(parents=True, exist_ok=True)

        # Create README in each directory
        readme_path = dir_path / "README.md"
        if not readme_path.exists() or force:
            readme_content = _generate_dir_readme(dir_name, dir_config)
            readme_path.write_text(readme_content, encoding='utf-8')

    # Save configuration
    config.save()

    # Create .projectignore file
    projectignore = project_dir / ".projectignore"
    if not projectignore.exists() or force:
        projectignore.write_text(
            "# LEE Project Ignore - Patterns that should not be considered project outputs\n"
            "# Add patterns here that should be ignored by the orchestrator\n\n"
            "# Examples:\n"
            "*.tmp\n"
            "*.bak\n"
            "*.swp\n"
            ".DS_Store\n"
            "node_modules/\n"
            "__pycache__/\n"
            "*.pyc\n"
        )

    # Create .project/README.md explaining the structure
    project_readme = project_dir / ".project" / "README.md"
    project_readme.write_text(_generate_project_readme(config), encoding='utf-8')

    print(f"[✓] Project structure initialized successfully")
    print(f"[INFO] Config file: {config_file}")
    print(f"[INFO] Total directories created: {len(config.directories)}")

    return config


def _generate_dir_readme(dir_name: str, dir_config: DirectoryConfig) -> str:
    """Generate README content for a directory"""
    readme = f"# {dir_config.description}\n\n"
    readme += f"**Config Key**: `{dir_name}`\n"
    readme += f"**Structure**: `{dir_config.structure}`\n"
    readme += f"**Naming**: `{dir_config.naming}`\n\n"

    if dir_config.subdirs:
        readme += "## Subdirectories\n\n"
        for subdir in dir_config.subdirs:
            readme += f"- `{subdir}/`\n"

    if dir_config.cleanup == "auto":
        readme += "\n**Note**: This directory is automatically cleaned up old files.\n"

    return readme


def _generate_project_readme(config: DirectoryStructureConfig) -> str:
    """Generate README for .project directory"""
    readme = """# LEE Project Configuration

This directory contains the LEE orchestrator configuration for this project.

## Files

- `dirs.yaml`: Directory structure configuration (DO NOT edit manually)
- `schema/`: Schema definitions for validation

## Directory Structure

`dirs.yaml` is the SSOT for directory topology only. Governed artifact identity, filename,
and reference rules belong to the SSOT identity layer rather than this file.

"""

    for dir_name, dir_config in config.directories.items():
        readme += f"- **{dir_config.path}**: {dir_config.description}\n"

    readme += """

## Constraints

"""

    constraints = config.constraints
    if constraints.get("strict_path_validation"):
        readme += "- ✅ Strict path validation enabled\n"

    if constraints.get("forbid_creation_outside_defined_dirs"):
        readme += "- ✅ File creation outside defined directories is forbidden\n"

    if constraints.get("require_initialization"):
        readme += "- ✅ Project initialization is required\n"

    readme += """
## Getting Output Paths

When creating outputs in your workflow, use the configured directory structure:

```python
from flowcore.orchestrator.project_config import get_project_structure

config = get_project_structure(".")
path = config.get_output_path("doc", category="reports", title="My Report")
# Returns: docs/reports/2025-01-25-my-report.md
```

For SSOT-governed artifacts:
- `dirs.yaml` decides which directory family the artifact belongs to
- the SSOT identity layer decides the artifact ID and final filename

Legacy `file_naming_conventions` may still appear in old configs for compatibility, but
new projects should not treat it as an active source of truth.

## Re-initializing

To re-initialize the project structure (e.g., after updating the schema):

```bash
python -m flowcore.orchestrator init . --force
```
"""

    return readme


def check_project_structure_initialized(project_dir: Path) -> Tuple[bool, Optional[DirectoryStructureConfig]]:
    """
    Check if project structure is initialized

    Returns:
        (is_initialized, DirectoryStructureConfig or None)
    """
    try:
        config = DirectoryStructureConfig.load(project_dir)
        return True, config
    except FileNotFoundError:
        return False, None
    except Exception as e:
        return False, None


def require_project_structure(project_dir: Path) -> DirectoryStructureConfig:
    """
    Require project structure to be initialized, raise error if not

    Args:
        project_dir: Project directory

    Returns:
        DirectoryStructureConfig

    Raises:
        RuntimeError: If project structure is not initialized
    """
    is_initialized, config = check_project_structure_initialized(project_dir)

    if not is_initialized:
        raise RuntimeError(
            f"Project structure not initialized at: {project_dir}\n\n"
            f"Please initialize the project first:\n"
            f"  python -m flowcore.orchestrator init {project_dir}\n\n"
            f"Or in your code:\n"
            f"  from flowcore.orchestrator.project_config import init_project_structure\n"
            f"  init_project_structure(Path('{project_dir}'))"
        )

    return config


def get_project_structure(project_dir: Path) -> DirectoryStructureConfig:
    """
    Get project structure configuration

    Args:
        project_dir: Project directory

    Returns:
        DirectoryStructureConfig
    """
    return require_project_structure(project_dir)


# ============================================
# Unified Project Initialization (ADR-0020)
# ============================================


def _is_git_repo(path: Path) -> bool:
    """Check if path is a git repository root."""
    git_path = path / ".git"
    if not git_path.exists():
        return False
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            toplevel = Path(result.stdout.strip()).resolve()
            return toplevel == path.resolve()
    except Exception:
        pass
    return False


def _get_git_remote(path: Path) -> Optional[str]:
    """Get git remote URL if available."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass
    return None


def _get_git_branch(path: Path) -> str:
    """Get current git branch."""
    try:
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except Exception:
        pass
    return "main"


def _discover_submodules(project_root: Path) -> Dict[str, str]:
    """Discover submodules from .gitmodules file."""
    gitmodules_path = project_root / ".gitmodules"
    if not gitmodules_path.exists():
        return {}

    submodules = {}
    try:
        with open(gitmodules_path, "r", encoding="utf-8") as f:
            content = f.read()

        current_path = None
        current_url = None

        for line in content.split("\n"):
            line = line.strip()
            if line.startswith("[submodule"):
                if current_path and current_url:
                    submodules[current_path] = current_url
                current_path = None
                current_url = None
            elif line.startswith("path ="):
                current_path = line.split("=", 1)[1].strip()
            elif line.startswith("url ="):
                current_url = line.split("=", 1)[1].strip()

        if current_path and current_url:
            submodules[current_path] = current_url

    except Exception:
        pass

    return submodules


def _discover_repos(project_root: Path, max_depth: int = 4) -> Dict[str, Dict]:
    """Discover git repositories in the project directory."""
    repos = {}
    root_is_repo = _is_git_repo(project_root)

    # First, try to discover submodules from .gitmodules
    submodules = _discover_submodules(project_root)
    for sub_path, sub_url in submodules.items():
        sub_full_path = project_root / sub_path
        if sub_full_path.exists():
            repo_name = sub_full_path.name.lower().replace("-", "_").replace(" ", "_")
            rel_path = f"./{sub_path}"
            repos[repo_name] = {
                "path": rel_path,
                "type": "git",
                "default_branch": _get_git_branch(sub_full_path),
                "url": sub_url,
                "description": f"Submodule {sub_full_path.name}",
            }

    # If root is a repo and we found submodules, add root as well
    if root_is_repo:
        repo_name = project_root.name.lower().replace("-", "_").replace(" ", "_")
        repos[repo_name] = {
            "path": "./.",
            "type": "git",
            "default_branch": _get_git_branch(project_root),
            "url": _get_git_remote(project_root),
            "description": f"Project {project_root.name}",
        }

    if repos:
        return repos

    # Otherwise, search for git repos in subdirectories
    exclude_dirs = {".git", ".lee", ".workflow", "node_modules", "venv", "__pycache__",
                    "dist", "build", ".venv", "env", "evidence"}

    def scan_dir(path: Path, depth: int = 0):
        if depth > max_depth:
            return
        try:
            for item in path.iterdir():
                if not item.is_dir():
                    continue
                if item.name.startswith(".") or item.name in exclude_dirs:
                    continue
                if _is_git_repo(item):
                    repo_name = item.name.lower().replace("-", "_").replace(" ", "_")
                    rel_path = f"./{item.relative_to(project_root)}"
                    repos[repo_name] = {
                        "path": rel_path,
                        "type": "git",
                        "default_branch": _get_git_branch(item),
                        "url": _get_git_remote(item),
                        "description": f"Repository {item.name}",
                    }
                else:
                    scan_dir(item, depth + 1)
        except PermissionError:
            pass

    scan_dir(project_root)
    return repos


def _create_repo_registry(project_root: Path, auto_discover: bool = True, max_depth: int = 4, force: bool = False) -> None:
    """Create .lee/repos.yaml if not exists."""
    lee_dir = project_root / ".lee"
    lee_dir.mkdir(parents=True, exist_ok=True)

    repos_file = lee_dir / "repos.yaml"
    if repos_file.exists() and not force:
        return

    repos = {}
    if auto_discover:
        print(f"  🔍 Scanning for git repositories (depth={max_depth})...")
        repos = _discover_repos(project_root, max_depth=max_depth)

    # If no repos found, create a default entry
    if not repos:
        project_name = project_root.name.lower().replace("-", "_").replace(" ", "_")
        repos[project_name] = {
            "path": "./.",
            "type": "git",
            "default_branch": "main",
            "description": f"Project {project_root.name}",
        }

    repo_registry = {
        "version": "1.0",
        "repos": repos
    }

    with open(repos_file, "w", encoding="utf-8") as f:
        yaml.dump(repo_registry, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    repo_count = len(repos)
    print(f"  ✓ Created .lee/repos.yaml ({repo_count} repo{'s' if repo_count > 1 else ''} found)")


def _copy_tree(src: Path, dest: Path) -> None:
    """Copy directory tree from src to dest, preserving existing files."""
    if not src.exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    for item in src.iterdir():
        target = dest / item.name
        if item.is_dir():
            _copy_tree(item, target)
        else:
            if not target.exists():
                shutil.copy2(item, target)


def _create_lee_config(project_root: Path, force: bool = False) -> None:
    """Create .lee/config.yaml if not exists."""
    lee_dir = project_root / ".lee"
    lee_dir.mkdir(parents=True, exist_ok=True)

    config_file = lee_dir / "config.yaml"
    if config_file.exists() and not force:
        return

    config = {
        "version": "1.0",
        "project": {"name": project_root.name},
        "spec_root": "spec-global",
        "executor": {"default_type": "claude_code"},
    }

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)


def _create_projectignore(project_root: Path, force: bool = False) -> None:
    """Create .projectignore file."""
    projectignore = project_root / ".projectignore"
    if projectignore.exists() and not force:
        return

    content = (
        "# LEE Project Ignore - Patterns that should not be considered project outputs\n"
        "# Add patterns here that should be ignored by the orchestrator\n\n"
        "# Examples:\n"
        "*.tmp\n"
        "*.bak\n"
        "*.swp\n"
        ".DS_Store\n"
        "node_modules/\n"
        "__pycache__/\n"
        "*.pyc\n"
    )
    projectignore.write_text(content, encoding='utf-8')


def _generate_readme(dir_config: DirectoryConfig, project_name: Optional[str] = None) -> str:
    """
    Generate README content for a directory - 简化版（ADR-0020）.
    """
    # Special handling for project config directory
    if dir_config.is_project_config:
        return f"""# LEE Project Configuration

**Project**: {project_name or "Unnamed Project"}

This directory contains the LEE orchestrator configuration for this project.

## Files

- `dirs.yaml`: Directory structure configuration (SSOT)
- `registry/`: Registry definitions

## Directory Structure

See `dirs.yaml` for the complete directory topology.
"""

    # Default README template
    content = f"""# {dir_config.description}

**Config Key**: `{dir_config.name}`  
**Structure**: `{dir_config.structure}`  
**Naming**: `{dir_config.naming}`

"""
    if dir_config.subdirs:
        content += "## Subdirectories\n\n"
        for subdir in dir_config.subdirs:
            content += f"- `{subdir}/`\n"
        content += "\n"

    if dir_config.cleanup == "auto":
        content += "**Note**: This directory is automatically cleaned up.\n"

    # Special content for spec directory
    if dir_config.name == "spec_dir":
        content += """
## Gate Workflow

Specifications in this directory must go through the gate workflow:
1. Create draft specification
2. Submit for gate review
3. Frozen specifications become read-only
"""

    return content


def initialize_project(
    project_dir: Path,
    *,
    project_name: Optional[str] = None,
    auto_discover_repos: bool = True,
    copy_templates: bool = True,
    generate_readme: bool = True,
    max_depth: int = 4,
    force: bool = False,
) -> DirectoryStructureConfig:
    """
    【新】统一项目初始化入口 (ADR-0020)
    
    整合了原 init_project_structure() 和 lee init CLI 的所有功能：
    - 目录结构创建
    - README 生成
    - Git 仓库发现
    - 模板复制
    - 配置文件创建
    
    Args:
        project_dir: Project root directory
        project_name: Name of the project
        auto_discover_repos: Whether to auto-discover git repositories
        copy_templates: Whether to copy template files
        generate_readme: Whether to generate README files
        max_depth: Max depth for git repo discovery
        force: Re-initialize even if already initialized
    
    Returns:
        DirectoryStructureConfig object
    """
    project_dir = Path(project_dir).resolve()

    # Check if already initialized
    config_file = project_dir / ".project" / "dirs.yaml"
    if config_file.exists() and not force:
        try:
            config = DirectoryStructureConfig.load(project_dir)
            print(f"[INFO] Project already initialized at: {config.initialized_at}")
            print(f"[INFO] Use --force to re-initialize")
            return config
        except Exception as e:
            print(f"[WARN] Existing config found but invalid: {e}")
            print(f"[INFO] Re-initializing project structure...")

    # Use default schema
    schema = DEFAULT_DIRECTORY_SCHEMA
    
    # Create DirectoryStructureConfig
    config = DirectoryStructureConfig(
        project_dir=project_dir,
        project_name=project_name or project_dir.name,
        version=schema["version"],
        initialized_at=datetime.now().isoformat(),
        initialized_by="lee-init",
        directories={},
        naming_conventions=schema.get("file_naming_conventions", {}),
        constraints=schema.get("constraints", {})
    )

    # Convert schema directories to DirectoryConfig objects
    for name, dir_config_data in schema.get("directories", {}).items():
        config.directories[name] = DirectoryConfig(name=name, **dir_config_data)

    # Create all directories
    print(f"[INFO] Initializing project structure at: {project_dir}")
    print(f"[INFO] Creating directory structure...")

    for dir_name, dir_config in config.directories.items():
        # Determine base path
        if dir_name in ["config_dir", "workflow_dir"]:
            dir_path = project_dir / dir_config.path
        else:
            project_content_dir = project_dir / (project_name or "")
            if project_name:
                project_content_dir.mkdir(parents=True, exist_ok=True)
                dir_path = project_content_dir / dir_config.path
            else:
                dir_path = project_dir / dir_config.path

        dir_path.mkdir(parents=True, exist_ok=True)

        # Create subdirectories
        for subdir in dir_config.subdirs:
            (dir_path / subdir).mkdir(parents=True, exist_ok=True)

        # Generate README
        if generate_readme and dir_config.create_readme:
            readme_path = dir_path / "README.md"
            if not readme_path.exists() or force:
                readme_content = _generate_readme(dir_config, config.project_name)
                readme_path.write_text(readme_content, encoding='utf-8')

        # Copy templates
        if copy_templates and dir_config.copy_templates_from:
            template_src = Path(dir_config.copy_templates_from)
            if not template_src.is_absolute():
                # Relative to project root or package root
                template_src = project_dir / template_src
            _copy_tree(template_src, dir_path)

    # Save configuration
    config.save()

    # Create .projectignore
    _create_projectignore(project_dir, force=force)

    # Create .lee/config.yaml
    _create_lee_config(project_dir, force=force)

    # Git repository discovery
    if auto_discover_repos:
        _create_repo_registry(project_dir, auto_discover=True, max_depth=max_depth, force=force)

    print(f"[✓] Project structure initialized successfully")
    print(f"[INFO] Config file: {config_file}")
    print(f"[INFO] Total directories created: {len(config.directories)}")

    return config


def init_project_structure(
    project_dir: Path,
    project_name: Optional[str] = None,
    config_schema: Optional[Dict] = None,
    force: bool = False,
    non_interactive: bool = False
) -> DirectoryStructureConfig:
    """
    【废弃】请使用 initialize_project() 替代
    
    此函数保留用于向后兼容，将在 v3.0 移除。
    
    向后兼容说明：
    - config_schema 参数不再支持，如果使用会发出 UserWarning
    - project_name 仍会被清理（移除特殊字符）
    - non_interactive 参数保留但不再使用（新实现总是非交互式）
    """
    warnings.warn(
        "init_project_structure() is deprecated, use initialize_project() instead",
        DeprecationWarning,
        stacklevel=2
    )
    
    # Backward compatibility: warn if config_schema is used
    if config_schema is not None:
        warnings.warn(
            "config_schema parameter is no longer supported in initialize_project(), using DEFAULT_DIRECTORY_SCHEMA",
            UserWarning,
            stacklevel=2
        )
    
    # Backward compatibility: sanitize project_name (legacy behavior)
    if project_name:
        # Remove invalid characters (legacy sanitization)
        project_name = re.sub(r'[^\w\-]', '-', project_name)
        # Remove leading/trailing dashes and dots
        project_name = project_name.strip('-.')
    
    # Call new unified function
    return initialize_project(
        project_dir=project_dir,
        project_name=project_name,
        auto_discover_repos=True,
        copy_templates=True,
        generate_readme=True,
        force=force,
    )
