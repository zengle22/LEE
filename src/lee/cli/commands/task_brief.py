"""
Task Brief CLI Commands - Task Brief 管理命令
"""

import json
import yaml
import click
from pathlib import Path
from typing import Optional, List

from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    TaskBrief,
    TaskBriefGenerator,
)


@click.group()
def task_brief():
    """Task Brief 管理命令"""
    pass


@task_brief.command("list")
@click.option("--run-id", help="按 run ID 过滤")
@click.option("--department", help="按部门过滤")
@click.option("--format", "output_format", default="table",
              type=click.Choice(["table", "json", "yaml"]),
              help="输出格式")
def list_task_briefs(run_id: Optional[str], department: Optional[str], output_format: str):
    """列出 Task Briefs"""
    manager = ArtifactManager()

    # 获取所有 artifacts
    all_artifacts = list(manager.registry._artifacts.values())

    # 过滤 task briefs
    briefs = [
        a for a in all_artifacts
        if a.category == "task_brief"
    ]

    # 按 run_id 过滤
    if run_id:
        briefs = [b for b in briefs if b.run_id == run_id]

    # 按 department 过滤
    if department:
        briefs = [b for b in briefs if b.department == department]

    # 按创建时间排序
    briefs.sort(key=lambda x: x.created_at, reverse=True)

    # 输出
    if not briefs:
        click.echo("No task briefs found.")
        return

    if output_format == "json":
        data = [
            {
                "id": b.id,
                "run_id": b.run_id,
                "department": b.department,
                "title": b.title,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "tags": b.tags,
            }
            for b in briefs
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
    elif output_format == "yaml":
        data = [
            {
                "id": b.id,
                "run_id": b.run_id,
                "department": b.department,
                "title": b.title,
                "created_at": b.created_at.isoformat() if b.created_at else None,
                "tags": b.tags,
            }
            for b in briefs
        ]
        click.echo(yaml.dump(data, allow_unicode=True))
    else:
        # 表格输出
        click.echo(f"{'ID':<20} {'Run ID':<20} {'Dept':<12} {'Created At':<16} {'Title'}")
        click.echo("-" * 110)

        for b in briefs:
            title = b.title or b.id
            if len(title) > 30:
                title = title[:27] + "..."
            created_at = b.created_at.strftime("%Y-%m-%d %H:%M") if b.created_at else "N/A"
            dept = b.department or "N/A"
            click.echo(f"{b.id:<20} {b.run_id:<20} {dept:<12} {created_at:<16} {title}")


@task_brief.command("show")
@click.argument("brief_id")
@click.option("--format", "output_format", default="yaml",
              type=click.Choice(["yaml", "json", "text"]),
              help="输出格式")
def show_task_brief(brief_id: str, output_format: str):
    """显示特定 Task Brief 内容"""
    manager = ArtifactManager()

    # 获取 artifact
    brief = manager.get(brief_id)
    if not brief:
        click.echo(f"Task brief not found: {brief_id}")
        return

    if brief.category != "task_brief":
        click.echo(f"Artifact {brief_id} is not a task brief (category: {brief.category})")
        return

    # 读取内容
    content_path = manager.root_path / brief.path
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


@task_brief.command("create")
@click.option("--run-id", required=True, help="run ID")
@click.option("--department", required=True, help="部门")
@click.option("--title", required=True, help="任务标题")
@click.option("--description", required=True, help="任务描述")
@click.option("--type", "task_type", default="feature",
              type=click.Choice(["feature", "bugfix", "incident", "refactor"]),
              help="任务类型")
@click.option("--related-prd", help="关联的 PRD ID")
@click.option("--related-bug", help="关联的 Bug Report ID")
@click.option("--scope-include", multiple=True, help="包含范围 (可多次指定)")
@click.option("--scope-exclude", multiple=True, help="排除范围 (可多次指定)")
@click.option("--acceptance", multiple=True, help="验收标准 (可多次指定)")
@click.option("--risk", "risks", multiple=True, help="风险 (可多次指定)")
def create_task_brief(
    run_id: str,
    department: str,
    title: str,
    description: str,
    task_type: str,
    related_prd: Optional[str],
    related_bug: Optional[str],
    scope_include: List[str],
    scope_exclude: List[str],
    acceptance: List[str],
    risks: List[str],
):
    """手动创建 Task Brief"""
    manager = ArtifactManager()
    generator = TaskBriefGenerator(manager)

    # 构建 related_ssot
    related_ssot = {}
    if related_prd:
        related_ssot["prd"] = related_prd
    if related_bug:
        related_ssot["bug_report"] = related_bug

    # 创建 Task Brief
    brief = generator.create_manual(
        run_id=run_id,
        department=department,
        title=title,
        description=description,
        task_type=task_type,
        related_ssot=related_ssot,
        scope_include=list(scope_include),
        scope_exclude=list(scope_exclude),
        acceptance=list(acceptance),
        risks=list(risks),
    )

    # 保存
    artifact = generator.save_brief(brief)

    click.echo(f"✅ Task Brief created: {artifact.id}")
    click.echo(f"   Path: {manager.root_path / artifact.path}")


# 注册命令到主 CLI
def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(task_brief)
