"""
Context CLI Commands - Task Context Bundle 管理命令
"""

import json
import yaml
import click
from pathlib import Path
from typing import Optional

from lee.orchestrator.execution.artifacts import ArtifactManager, ArtifactType


@click.group()
def context():
    """Task Context Bundle 管理命令"""
    pass


@context.command("list")
@click.option("--run-id", help="按 run ID 过滤")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json", "yaml"]),
              help="输出格式")
def list_context_bundles(run_id: Optional[str], output_format: str):
    """列出 Task Context Bundles"""
    manager = ArtifactManager()

    # 获取所有 artifacts
    all_artifacts = list(manager.registry._artifacts.values())

    # 过滤 context bundles
    bundles = [
        a for a in all_artifacts
        if a.category == "task_context_bundle"
    ]

    # 按 run_id 过滤
    if run_id:
        bundles = [b for b in bundles if b.run_id == run_id]

    # 按创建时间排序
    bundles.sort(key=lambda x: x.created_at, reverse=True)

    # 输出
    if not bundles:
        click.echo("No context bundles found.")
        return

    if output_format == "json":
        data = [
            {
                "id": b.id,
                "run_id": b.run_id,
                "title": b.title,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "size_bytes": b.size_bytes,
            }
            for b in bundles
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    elif output_format == "yaml":
        data = [
            {
                "id": b.id,
                "run_id": b.run_id,
                "title": b.title,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "size_bytes": b.size_bytes,
            }
            for b in bundles
        ]
        click.echo(yaml.dump(data, allow_unicode=True))
    else:
        # 表格输出
        click.echo(f"{'ID':<16} {'Run ID':<20} {'Created At':<20} {'Size':<10} {'Title'}")
        click.echo("-" * 100)

        for b in bundles:
            title = b.title or b.id
            if len(title) > 30:
                title = title[:27] + "..."
            created_at = b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "N/A"
            size = f"{b.size_bytes or 0} B"
            click.echo(f"{b.id:<16} {b.run_id:<20} {created_at:<20} {size:<10} {title}")


@context.command("show")
@click.argument("bundle_id")
@click.option("--format", "output_format", default="yaml",
              type=click.Choice(["yaml", "json", "text"]),
              help="输出格式")
def show_context_bundle(bundle_id: str, output_format: str):
    """显示特定 Context Bundle 内容"""
    manager = ArtifactManager()

    # 获取 artifact
    bundle = manager.get(bundle_id)
    if not bundle:
        click.echo(f"Context bundle not found: {bundle_id}")
        return

    if bundle.category != "task_context_bundle":
        click.echo(f"Artifact {bundle_id} is not a context bundle (category: {bundle.category})")
        return

    # 读取内容
    content_path = manager.root_path / bundle.path
    if not content_path.exists():
        click.echo(f"Content file not found: {content_path}")
        return

    content = content_path.read_text(encoding="utf-8")

    # 输出
    if output_format == "json":
        try:
            data = yaml.safe_load(content)
            click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        except yaml.YAMLError as e:
            click.echo(json.dumps({"raw": content, "parse_error": str(e)}, indent=2))
    elif output_format == "text":
        click.echo(content)
    else:
        click.echo(content)


# 注册命令到主 CLI
def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(context)
