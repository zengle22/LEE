"""lee init command"""

from __future__ import annotations

from pathlib import Path
import shutil

import click


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


@click.command()
@click.option("--project-dir", default=".", help="项目目录")
def init(project_dir: str) -> None:
    """初始化项目目录结构"""
    project_root = Path(project_dir).resolve()
    (project_root / "spec" / "dev").mkdir(parents=True, exist_ok=True)
    (project_root / "spec" / "qa").mkdir(parents=True, exist_ok=True)
    (project_root / "spec" / "devops").mkdir(parents=True, exist_ok=True)
    (project_root / "evidence").mkdir(parents=True, exist_ok=True)
    (project_root / "env").mkdir(parents=True, exist_ok=True)
    (project_root / ".workflow").mkdir(parents=True, exist_ok=True)

    # Copy templates
    repo_root = Path(__file__).resolve().parents[4]
    templates_root = repo_root / "templates"
    _copy_tree(templates_root / "spec", project_root / "spec")
    _copy_tree(templates_root / "env", project_root / "env")

    click.echo(f"Initialized project at: {project_root}")
