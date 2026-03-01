"""
LEE Artifact CLI Commands

产出物管理 CLI 命令实现。
"""

import json
from pathlib import Path
from typing import Optional

import click

from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    ManifestManager,
    AdoptMode,
    GovernanceKind,
)


@click.group()
def artifacts():
    """产出物管理命令"""
    pass


@artifacts.command("list")
@click.option("--type", "artifact_type", help="按类型筛选")
@click.option("--category", help="按类别筛选")
@click.option("--status", help="按状态筛选")
@click.option("--department", help="按部门筛选")
@click.option("--run-id", help="按 run ID 筛选")
@click.option("--kind", "governance_kind", help="按治理类别筛选")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "json", "yaml"]), help="输出格式")
def list_artifacts(artifact_type, category, status, department, run_id, governance_kind, output_format):
    """列出产出物"""
    manager = ArtifactManager()

    # 获取产出物列表
    if run_id:
        artifacts = manager.registry.get_by_run(run_id)
    elif artifact_type:
        artifacts = manager.registry.get_by_type(artifact_type)
    elif category:
        artifacts = manager.registry.get_by_category(category)
    elif status:
        artifacts = manager.registry.get_by_status(status)
    elif department:
        artifacts = manager.registry.get_by_department(department)
    else:
        # 默认返回最近 50 个
        artifacts = list(manager.registry._artifacts.values())[-50:]

    # 进一步筛选
    if category:
        artifacts = [a for a in artifacts if a.category == category]
    if status:
        artifacts = [a for a in artifacts if a.status.value == status]
    if governance_kind:
        artifacts = [a for a in artifacts if a.governance_kind.value == governance_kind]

    # 输出
    if output_format == "json":
        data = [a.to_dict() for a in artifacts]
        click.echo(json.dumps(data, ensure_ascii=False, indent=2))
    elif output_format == "yaml":
        import yaml
        data = [a.to_dict() for a in artifacts]
        click.echo(yaml.dump(data, allow_unicode=True))
    else:
        # 表格输出
        if not artifacts:
            click.echo("No artifacts found.")
            return

        # 表头
        click.echo(f"{'ID':<12} {'Type':<12} {'Category':<20} {'Status':<12} {'Title'}")
        click.echo("-" * 100)

        for a in artifacts:
            title = a.title or a.id
            if len(title) > 40:
                title = title[:37] + "..."
            click.echo(f"{a.id:<12} {a.type.value:<12} {a.category:<20} {a.status.value:<12} {title}")


@artifacts.command("show")
@click.argument("artifact_id")
def show_artifact(artifact_id):
    """显示产出物详情"""
    manager = ArtifactManager()
    metadata = manager.get(artifact_id)

    if not metadata:
        click.echo(f"Artifact not found: {artifact_id}", err=True)
        return

    # 显示元数据
    click.echo(f"ID:           {metadata.id}")
    click.echo(f"Type:         {metadata.type.value}")
    click.echo(f"Category:     {metadata.category}")
    click.echo(f"Status:       {metadata.status.value}")
    click.echo(f"Title:        {metadata.title}")
    click.echo(f"Description:  {metadata.description}")
    click.echo(f"Path:         {metadata.path}")
    if metadata.external_path:
        click.echo(f"External:     {metadata.external_path}")
    if metadata.adopt_mode:
        click.echo(f"Adopt Mode:   {metadata.adopt_mode.value}")
    click.echo(f"Run ID:       {metadata.run_id}")
    if metadata.department:
        click.echo(f"Department:   {metadata.department}")
    if metadata.git_sha:
        click.echo(f"Git SHA:      {metadata.git_sha}")
    if metadata.size_bytes:
        click.echo(f"Size:         {metadata.size_bytes} bytes")
    if metadata.tags:
        click.echo(f"Tags:         {', '.join(metadata.tags)}")
    click.echo(f"Created:      {metadata.created_at.isoformat()}")
    click.echo(f"Updated:      {metadata.updated_at.isoformat()}")

    # 显示关系
    if metadata.depends_on:
        click.echo(f"Depends On:   {', '.join(metadata.depends_on)}")
    if metadata.derived_from:
        click.echo(f"Derived From: {metadata.derived_from}")
    if metadata.consumed_by:
        click.echo(f"Consumed By:  {', '.join(metadata.consumed_by)}")


@artifacts.command("content")
@click.argument("artifact_id")
@click.option("--output", "-o", help="输出到文件")
def show_content(artifact_id, output):
    """显示产出物内容"""
    manager = ArtifactManager()
    content = manager.get_content(artifact_id)

    if content is None:
        click.echo(f"Artifact not found or has no content: {artifact_id}", err=True)
        return

    if output:
        Path(output).write_text(content if isinstance(content, str) else content.decode("utf-8"))
        click.echo(f"Content written to: {output}")
    else:
        if isinstance(content, bytes):
            click.echo(content.decode("utf-8", errors="replace"))
        else:
            click.echo(content)


@artifacts.command("adopt")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--run-id", required=True, help="run ID")
@click.option("--type", "artifact_type", required=True, type=click.Choice([t.value for t in ArtifactType]), help="产出物类型")
@click.option("--category", required=True, help="产出物类别")
@click.option("--mode", type=click.Choice(["copy_mode", "reference_mode"]), help="adopt 模式")
@click.option("--title", help="标题")
@click.option("--description", help="描述")
@click.option("--department", help="所属部门")
@click.option("--tag", "tags", multiple=True, help="标签")
def adopt_file(file_path, run_id, artifact_type, category, mode, title, description, department, tags):
    """Adopt 外部文件到产出物系统"""
    manager = ArtifactManager()

    try:
        metadata = manager.adopt(
            external_path=file_path,
            run_id=run_id,
            artifact_type=ArtifactType(artifact_type),
            category=category,
            mode=AdoptMode(mode) if mode else None,
            title=title or "",
            description=description or "",
            department=department,
            tags=list(tags),
        )

        click.echo(f"Created artifact: {metadata.id}")
        click.echo(f"  Type:     {metadata.type.value}")
        click.echo(f"  Category: {metadata.category}")
        click.echo(f"  Path:     {metadata.path}")
        if metadata.adopt_mode:
            click.echo(f"  Mode:     {metadata.adopt_mode.value}")

    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@artifacts.command("freeze")
@click.argument("artifact_id")
def freeze_artifact(artifact_id):
    """冻结产出物"""
    manager = ArtifactManager()

    try:
        metadata = manager.freeze(artifact_id)
        click.echo(f"Frozen artifact: {metadata.id}")
        click.echo(f"  Status: {metadata.status.value}")
        click.echo(f"  Path:   {metadata.path}")
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@artifacts.command("delete")
@click.argument("artifact_id")
@click.option("--force", "-f", is_flag=True, help="强制删除 (跳过引用保护)")
def delete_artifact(artifact_id, force):
    """删除产出物"""
    manager = ArtifactManager()

    try:
        if manager.delete(artifact_id, force=force):
            click.echo(f"Deleted artifact: {artifact_id}")
        else:
            click.echo(f"Artifact not found: {artifact_id}", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        raise click.Abort()


@artifacts.command("registry")
@click.option("--rebuild", is_flag=True, help="从 manifest 重建注册表")
@click.option("--validate", is_flag=True, help="验证注册表完整性")
@click.option("--stats", is_flag=True, help="显示统计信息")
def registry_cmd(rebuild, validate, stats):
    """注册表操作"""
    manager = ArtifactManager()

    if rebuild:
        click.echo("Rebuilding registry from manifests...")
        manager.registry.rebuild()
        click.echo("Registry rebuilt successfully.")

    if validate:
        click.echo("Validating registry integrity...")
        if manager.registry.validate_integrity():
            click.echo("Registry is valid.")
        else:
            click.echo("Registry validation failed!", err=True)

    if stats:
        stats_data = manager.registry.get_statistics()
        click.echo(json.dumps(stats_data, indent=2, ensure_ascii=False))

    if not (rebuild or validate or stats):
        # 默认显示统计信息
        stats_data = manager.registry.get_statistics()
        click.echo(json.dumps(stats_data, indent=2, ensure_ascii=False))


@artifacts.command("runs")
@click.option("--status", help="按状态筛选")
@click.option("--department", help="按部门筛选")
@click.option("--limit", default=20, help="最大返回数量")
def list_runs(status, department, limit):
    """列出 runs"""
    manifest_manager = ManifestManager()

    runs = manifest_manager.list_runs(status=status, department=department, limit=limit)

    if not runs:
        click.echo("No runs found.")
        return

    click.echo(f"{'Run ID':<30} {'Department':<15} {'Status':<12} {'Started'}")
    click.echo("-" * 100)

    for run in runs:
        dept = run.department or "-"
        started = run.started_at.strftime("%Y-%m-%d %H:%M")
        click.echo(f"{run.run_id:<30} {dept:<15} {run.status:<12} {started}")


@artifacts.command("run")
@click.argument("run_id")
@click.option("--department", help="部门")
def show_run(run_id, department):
    """显示 run 详情"""
    manifest_manager = ManifestManager()
    manifest = manifest_manager.get(run_id, department)

    if not manifest:
        click.echo(f"Run not found: {run_id}", err=True)
        return

    click.echo(f"Run ID:       {manifest.run_id}")
    if manifest.workflow_id:
        click.echo(f"Workflow ID:  {manifest.workflow_id}")
    if manifest.department:
        click.echo(f"Department:   {manifest.department}")
    click.echo(f"Status:       {manifest.status}")
    click.echo(f"Started:      {manifest.started_at.isoformat()}")
    if manifest.completed_at:
        click.echo(f"Completed:    {manifest.completed_at.isoformat()}")
    if manifest.executor:
        click.echo(f"Executor:     {manifest.executor}")
        if manifest.executor_version:
            click.echo(f"Version:      {manifest.executor_version}")

    # 统计信息
    stats = manifest_manager.get_statistics(run_id, department)
    click.echo(f"\nArtifacts:    {stats.get('total_artifacts', 0)}")

    if stats.get("by_type"):
        click.echo("  By Type:")
        for type_name, count in stats["by_type"].items():
            click.echo(f"    {type_name}: {count}")

    if stats.get("by_status"):
        click.echo("  By Status:")
        for status_name, count in stats["by_status"].items():
            click.echo(f"    {status_name}: {count}")

    # 移交信息
    if manifest.handover_to:
        click.echo(f"\nHandover To:  {manifest.handover_to}")
        if manifest.handover_artifacts:
            click.echo(f"Artifacts:    {', '.join(manifest.handover_artifacts)}")


# 注册命令
def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(artifacts)
