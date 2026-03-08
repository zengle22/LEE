"""lee init command"""

from __future__ import annotations

import os
from pathlib import Path

import click

from lee.orchestrator.core.project_config import initialize_project


@click.command()
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--no-discover", is_flag=True, help="禁用自动发现 git 仓库")
@click.option("--depth", default=4, help="搜索 git 仓库的最大深度 (默认: 4)")
@click.option("--force", is_flag=True, help="强制重新生成配置文件")
@click.option("--no-readme", is_flag=True, help="不生成 README 文件")
@click.option("--no-templates", is_flag=True, help="不复制模板文件")
def init(project_dir: str, no_discover: bool, depth: int, force: bool, no_readme: bool, no_templates: bool) -> None:
    """初始化项目目录结构"""
    project_root = Path(project_dir).resolve()

    if force:
        click.echo(f"Reinitializing LEE project at: {project_root}")
    else:
        click.echo(f"Initializing LEE project at: {project_root}")
    click.echo()

    # Call unified initialization function
    config = initialize_project(
        project_dir=project_root,
        project_name=None,  # Will use project_root.name
        auto_discover_repos=not no_discover,
        copy_templates=not no_templates,
        generate_readme=not no_readme,
        max_depth=depth,
        force=force,
    )

    # CLI-specific output formatting
    click.echo(f"  ✓ Created directory structure ({len(config.directories)} directories)")
    
    if not no_readme:
        click.echo("  ✓ Generated README files")
    
    if not no_templates:
        click.echo("  ✓ Copied template files")
    
    if not no_discover:
        repos_file = project_root / ".lee" / "repos.yaml"
        if repos_file.exists():
            click.echo("  ✓ Created .lee/repos.yaml")

    click.echo()
    click.echo(click.style("✅ Project initialized successfully!", fg="green", bold=True))
    click.echo()
    click.echo("Next steps:")
    click.echo(f"  1. cd {project_root}")
    click.echo("  2. Edit .lee/repos.yaml to configure your repositories")
    click.echo("  3. Run 'lee chat' to start an interactive session")
