"""lee init command"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
import shutil

import click
import yaml


def _copy_tree(src: Path, dest: Path) -> None:
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


def _is_git_repo(path: Path) -> bool:
    """
    Check if path is a git repository root.

    Works for both regular repos and submodules.
    - Regular repo: .git is a directory
    - Submodule: .git is a file pointing to parent's .git/modules/
    """
    git_path = path / ".git"
    if not git_path.exists():
        return False

    # Use git command to verify it's a valid repo root
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(path),
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            # Verify the toplevel matches this path
            toplevel = Path(result.stdout.strip()).resolve()
            return toplevel == path.resolve()
    except Exception:
        pass

    return False


def _get_git_remote(path: Path) -> str | None:
    """Get git remote URL if available"""
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
    """Get current git branch"""
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


def _discover_repos(project_root: Path, max_depth: int = 4) -> dict:
    """
    Discover git repositories in the project directory.

    Args:
        project_root: Project root directory
        max_depth: Maximum depth to search for repos

    Returns:
        Dict of repo_id -> repo config
    """
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

    # If we found repos (submodules or root), return them
    if repos:
        return repos

    # Otherwise, search for git repos in subdirectories (for non-submodule projects)
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


def _discover_submodules(project_root: Path) -> dict:
    """
    Discover submodules from .gitmodules file.

    Returns:
        Dict of path -> url
    """
    gitmodules_path = project_root / ".gitmodules"
    if not gitmodules_path.exists():
        return {}

    submodules = {}

    try:
        with open(gitmodules_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Parse .gitmodules file (ini-like format)
        current_path = None
        current_url = None

        for line in content.split("\n"):
            line = line.strip()

            if line.startswith("[submodule"):
                # Save previous submodule
                if current_path and current_url:
                    submodules[current_path] = current_url
                current_path = None
                current_url = None

            elif line.startswith("path ="):
                current_path = line.split("=", 1)[1].strip()

            elif line.startswith("url ="):
                current_url = line.split("=", 1)[1].strip()

        # Save last submodule
        if current_path and current_url:
            submodules[current_path] = current_url

    except Exception as e:
        pass

    return submodules


def _create_repo_registry(project_root: Path, auto_discover: bool = True, max_depth: int = 4, force: bool = False) -> None:
    """Create .lee/repos.yaml if not exists"""
    lee_dir = project_root / ".lee"
    lee_dir.mkdir(parents=True, exist_ok=True)

    repos_file = lee_dir / "repos.yaml"

    if repos_file.exists() and not force:
        click.echo(f"  ✓ repos.yaml already exists (use --force to regenerate)")
        return

    repos = {}

    if auto_discover:
        click.echo(f"  🔍 Scanning for git repositories (depth={max_depth})...")
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

    # Create repo registry
    repo_registry = {
        "version": "1.0",
        "repos": repos
    }

    with open(repos_file, "w", encoding="utf-8") as f:
        yaml.dump(repo_registry, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

    repo_count = len(repos)
    click.echo(f"  ✓ Created .lee/repos.yaml ({repo_count} repo{'s' if repo_count > 1 else ''} found)")


def _create_directory_structure(project_root: Path) -> dict:
    """
    创建完整的项目目录结构

    Returns:
        创建的目录字典
    """
    directories = {
        # 工具目录（LEE 元数据）
        ".project": "LEE 项目配置，元数据（SSOT of project）",
        ".project/registry": "各类注册表索引（可选）",
        # 注意: .project/config.yaml 由 _create_config 函数创建

        ".workflow": "工作流运行态（可清理/可重建）",
        ".workflow/runs": "每次 run 的工作目录（中间物都在这里）",  # WORKFLOW_SUBDIRS["runs"]
        ".workflow/cache": "模型缓存、临时索引",  # WORKFLOW_SUBDIRS["cache"]

        ".artifacts": "产出物（需要长期保留/可追溯）",
        ".artifacts/active": "当前有效产物",  # ARTIFACTS_SUBDIRS["active"]
        ".artifacts/frozen": "冻结版本（对外/对下游的接口）",  # ARTIFACTS_SUBDIRS["frozen"]
        ".artifacts/archive": "归档历史",  # ARTIFACTS_SUBDIRS["archive"]

        # 内容目录（业务输出）
        "spec": "规格 SSOT（可 gate、可冻结）",
        "spec/requirements": "需求/范围/验收标准（Definition of Done）",  # SPEC_SUBDIRS["requirements"]
        "spec/api": "OpenAPI/Proto/AsyncAPI/DTO Schema",  # SPEC_SUBDIRS["api"]
        "spec/data": "数据库/数据模型/迁移规范",  # SPEC_SUBDIRS["data"]
        "spec/ui": "UI 规格（路由/页面/交互/文案）",  # SPEC_SUBDIRS["ui"]
        "spec/adr": "架构决策记录（为什么这么做）",  # SPEC_SUBDIRS["adr"]

        "docs": "解释性文档（生成/沉淀/知识）",
        "docs/guides": "使用指南/开发指南",
        "docs/reports": "阶段性报告/评审报告",
        "docs/archive": "历史文档归档",

        "src": "源码（前后端分离建议明确边界）",
        "src/backend": "后端代码",
        "src/frontend": "前端代码",

        "tests": "测试（镜像 src 结构）",
        "tests/unit": "单元测试",
        "tests/integration": "集成测试",
        "tests/e2e": "端到端测试",

        "tools": "项目工具（代码生成、lint、自检脚本）",
        "deploy": "部署（docker/helm/terraform）",

        # 兼容旧版（默认只读）
        "legacy": "兼容旧版（默认只读）",
        "legacy/spec": "原 spec/dev|qa|devops 等迁移过来",
        "legacy/evidence": "证据数据",
        "legacy/env": "环境配置",
    }

    created = {}
    for dir_path, description in directories.items():
        full_path = project_root / dir_path
        full_path.mkdir(parents=True, exist_ok=True)
        created[dir_path] = description

    return created


def _create_config(project_root: Path, force: bool = False) -> None:
    """Create .lee/config.yaml if not exists"""
    lee_dir = project_root / ".lee"
    lee_dir.mkdir(parents=True, exist_ok=True)

    config_file = lee_dir / "config.yaml"

    if config_file.exists() and not force:
        click.echo(f"  ✓ config.yaml already exists (use --force to regenerate)")
        return

    # Create default config
    config = {
        "version": "1.0",
        "project": {
            "name": project_root.name,
        },
        "spec_root": "spec-global",
        "executor": {
            "default_type": "claude_code",
        },
    }

    with open(config_file, "w", encoding="utf-8") as f:
        yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

    click.echo(f"  ✓ Created .lee/config.yaml")


@click.command()
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--no-discover", is_flag=True, help="禁用自动发现 git 仓库")
@click.option("--depth", default=4, help="搜索 git 仓库的最大深度 (默认: 4)")
@click.option("--force", is_flag=True, help="强制重新生成配置文件")
def init(project_dir: str, no_discover: bool, depth: int, force: bool) -> None:
    """初始化项目目录结构"""
    project_root = Path(project_dir).resolve()

    if force:
        click.echo(f"Reinitializing LEE project at: {project_root}")
    else:
        click.echo(f"Initializing LEE project at: {project_root}")
    click.echo()

    # Create complete directory structure
    dirs = _create_directory_structure(project_root)

    # 分类显示
    tool_dirs = [d for d in dirs if d.startswith(".")]
    content_dirs = [d for d in dirs if not d.startswith(".")]
    legacy_dirs = ["spec/dev", "spec/qa", "spec/devops", "evidence", "env"]

    click.echo(f"  ✓ Created tool directories: {', '.join(tool_dirs)}")
    click.echo(f"  ✓ Created content directories: {', '.join(content_dirs[:5])}...")
    click.echo(f"  ✓ Created legacy directories: {', '.join(legacy_dirs)}")

    # Create .lee directory with config files
    _create_repo_registry(project_root, auto_discover=not no_discover, max_depth=depth, force=force)
    _create_config(project_root, force=force)

    # Copy templates
    repo_root = Path(__file__).resolve().parents[4]
    templates_root = repo_root / "templates"
    if templates_root.exists():
        _copy_tree(templates_root / "spec", project_root / "spec")
        _copy_tree(templates_root / "env", project_root / "env")
        click.echo("  ✓ Copied template files")

    click.echo()
    click.echo(click.style("✅ Project initialized successfully!", fg="green", bold=True))
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. cd {project_root}")
    click.echo("  2. Edit .lee/repos.yaml to configure your repositories")
    click.echo("  3. Run 'lee chat' to start an interactive session")
