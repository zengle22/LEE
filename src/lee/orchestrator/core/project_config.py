"""
Project Config - 项目配置管理

管理项目的：
1. 仓库注册表和路径别名，实现路径的标准化解析
2. 目录结构初始化和验证，防止目录飘逸
"""

import re
import yaml
from pathlib import Path
from typing import Dict, Optional, Any, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import json


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


# ============================================
# Directory Structure Configuration
# ============================================

# Standard directory structure schema
DEFAULT_DIRECTORY_SCHEMA = {
    "version": "1.0",
    "description": "LEE Standard Project Directory Structure",
    "directories": {
        # Configuration
        "config_dir": {
            "path": ".project",
            "description": "Project configuration and metadata",
            "subdirs": ["schema"]
        },

        # Workflow state (existing)
        "workflow_dir": {
            "path": ".workflow",
            "description": "Workflow execution state and temporary files",
            "subdirs": ["workspace", "gates", "events", "cache"]
        },

        # Contracts (frozen analysis outputs)
        "contracts_dir": {
            "path": "contracts",
            "description": "Frozen analysis results and formal contracts",
            "subdirs": ["input", "output"],
            "structure": "layered"  # layered: {layer_name}/{version}/{file}.yaml
        },

        # Documentation outputs
        "docs_dir": {
            "path": "docs",
            "description": "Generated documentation and reports",
            "subdirs": ["spec", "reports", "guides", "archive"],
            "naming": "descriptive"  # descriptive: {YYYY-MM-DD}-{title}.md
        },

        # Source code outputs
        "src_dir": {
            "path": "src",
            "description": "Generated source code",
            "subdirs": ["components", "services", "utils", "types"],
            "structure": "module"  # module: {module_name}/{file}.ext
        },

        # Intermediate outputs
        "outputs_dir": {
            "path": "outputs",
            "description": "Intermediate outputs and artifacts",
            "subdirs": ["build", "test", "analysis", "temp"],
            "cleanup": "auto"  # auto: automatically clean old files
        },

        # Test outputs
        "tests_dir": {
            "path": "tests",
            "description": "Generated test files",
            "subdirs": ["unit", "integration", "e2e"],
            "structure": "hierarchical"
        },

        # Specifications
        "specs_dir": {
            "path": "specs",
            "description": "Generated specification documents",
            "subdirs": ["requirements", "api", "database", "ui"],
            "format": "markdown"
        }
    },
    "file_naming_conventions": {
        "contracts": "{layer}/{version}/{contract_name}.yaml",
        "docs": "{category}/{YYYY-MM-DD}-{title}.md",
        "source": "{module}/{file_name}.{ext}",
        "tests": "{type}/{test_name}_test.{ext}",
        "outputs": "{step_id}/{artifact_name}.{ext}"
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
    """Directory configuration"""
    name: str
    path: str
    description: str
    subdirs: List[str] = field(default_factory=list)
    structure: str = "flat"  # flat, layered, module, hierarchical
    naming: str = "default"  # default, descriptive, timestamped
    cleanup: Optional[str] = None  # auto, manual, none
    format: Optional[str] = None  # markdown, yaml, json (for docs/specs)


@dataclass
class DirectoryStructureConfig:
    """Directory structure configuration"""

    project_dir: Path
    version: str
    initialized_at: Optional[str] = None
    initialized_by: Optional[str] = None
    project_name: Optional[str] = None
    directories: Dict[str, DirectoryConfig] = field(default_factory=dict)
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

        data = {
            "version": self.version,
            "description": "LEE Standard Project Directory Structure",
            "initialized_at": self.initialized_at,
            "initialized_by": self.initialized_by,
            "project_name": self.project_name,
            "directories": directories_dict,
            "file_naming_conventions": self.naming_conventions,
            "constraints": self.constraints
        }

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

        # If absolute path, make it relative to project dir
        if path.is_absolute():
            try:
                path = path.relative_to(self.project_dir)
            except ValueError:
                return False, f"Path is outside project directory: {output_path}"

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
                dir_path = self.get_directory_path(dir_name)
                try:
                    path.relative_to(dir_path)
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
        Get the correct output path based on type and naming convention

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

            while not project_name:
                print("[ERROR] Project name cannot be empty")
                project_name = input("Project name: ").strip()

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
