"""
Governance CLI Commands - 临时治理命令
"""

from __future__ import annotations

import re
import json
from pathlib import Path
from typing import Optional, Any

import click
import yaml


def _slugify(value: str) -> str:
    text = value.strip().lower()
    text = re.sub(r"[^a-z0-9\u4e00-\u9fff]+", "-", text)
    text = re.sub(r"-{2,}", "-", text).strip("-")
    return text or "untitled"


def _build_acceptance_brief_content(
    brief_id: str,
    title: str,
    task_type: str,
    governed_module: Optional[str],
    future_ssot_type: Optional[str],
    human_gate_required: bool,
) -> str:
    front_matter = {
        "brief_id": brief_id,
        "title": title,
        "status": "active",
        "owner": "pending",
        "task_type": task_type,
        "scope_in": ["item 1"],
        "scope_out": ["item 1"],
        "formal_ssot_id": None,
        "future_ssot_type": future_ssot_type or None,
        "future_parent": None,
        "governed_module": governed_module or None,
        "human_gate_required": human_gate_required,
        "evidence_required": [
            "changed_files",
            "test_results",
            "output_artifacts",
            "review_notes",
        ],
    }
    front_matter_yaml = yaml.safe_dump(
        front_matter,
        allow_unicode=True,
        sort_keys=False,
    ).strip()

    body = f"""---
{front_matter_yaml}
---

# Acceptance Brief

## Task ID

{brief_id}

## Task

{title}

## Purpose

Why this task exists and what problem it solves.

## Scope In

- item 1
- item 2

## Scope Out

- item 1
- item 2

## Inputs

- source docs
- source modules
- related artifacts

## Expected Output

- code / docs / test / config changes
- artifact locations

## Non-Negotiable Constraints

- do not change completion standard
- do not weaken tests
- do not introduce parallel unmanaged paths
- do not create duplicate implementation without checking existing modules

## Acceptance Criteria

- criterion 1
- criterion 2
- criterion 3

## Evidence Required

- changed files
- test results
- output artifacts
- review notes

## Risks / Open Questions

- item 1
- item 2

## Human Gate Required?

{"YES" if human_gate_required else "NO"}

## Related Files

- path 1
- path 2

## Future SSOT Target

- future_ssot_type: {future_ssot_type or ""}
- future_parent:
- migration_note:

## Approved By

[name or pending]
"""
    return body


def _briefs_dir(project_dir: str) -> Path:
    return Path(project_dir).resolve() / ".project" / "governance" / "ACCEPTANCE_BRIEFS"


def _parse_front_matter(path: Path) -> dict[str, Any]:
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return {}

    if not text.startswith("---\n"):
        return {}

    end_idx = text.find("\n---", 4)
    if end_idx == -1:
        return {}

    raw = text[4:end_idx]
    try:
        data = yaml.safe_load(raw) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def _list_briefs(project_dir: str) -> list[dict[str, Any]]:
    briefs_dir = _briefs_dir(project_dir)
    if not briefs_dir.exists():
        return []

    results = []
    for path in sorted(briefs_dir.glob("*.md")):
        if path.name.startswith("_"):
            continue
        metadata = _parse_front_matter(path)
        results.append(
            {
                "path": str(path),
                "filename": path.name,
                "metadata": metadata,
            }
        )
    return results


def _validate_brief(path: Path) -> list[str]:
    errors: list[str] = []
    metadata = _parse_front_matter(path)
    if not metadata:
        return ["missing or invalid YAML front matter"]

    required_fields = [
        "brief_id",
        "title",
        "status",
        "scope_in",
        "scope_out",
        "human_gate_required",
        "evidence_required",
    ]
    for field in required_fields:
        if field not in metadata or metadata[field] in (None, "", []):
            errors.append(f"missing required field: {field}")

    if "status" in metadata and metadata.get("status") not in {"active", "draft", "retired"}:
        errors.append("status must be one of: active, draft, retired")

    if "scope_in" in metadata and not isinstance(metadata.get("scope_in"), list):
        errors.append("scope_in must be a list")
    if "scope_out" in metadata and not isinstance(metadata.get("scope_out"), list):
        errors.append("scope_out must be a list")
    if "evidence_required" in metadata and not isinstance(metadata.get("evidence_required"), list):
        errors.append("evidence_required must be a list")
    if "human_gate_required" in metadata and not isinstance(metadata.get("human_gate_required"), bool):
        errors.append("human_gate_required must be a boolean")

    return errors


@click.group()
def governance():
    """Governance 管理命令"""
    pass


@governance.command("create-brief")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--id", "brief_id", required=True, help="Acceptance Brief ID")
@click.option("--title", required=True, help="任务标题")
@click.option(
    "--type",
    "task_type",
    default="task",
    type=click.Choice(["task", "feature", "bugfix", "refactor", "incident"]),
    help="任务类型",
)
@click.option("--module", "governed_module", default=None, help="受影响模块")
@click.option(
    "--future-ssot-type",
    default=None,
    type=click.Choice(["epic", "feat", "testset", "tc", "bug", "report", "adr", "evi"]),
    help="未来正式 SSOT 类型",
)
@click.option("--human-gate-required/--no-human-gate-required", default=True, help="是否要求人工 gate")
@click.option("--force", is_flag=True, help="覆盖已存在的文件")
def create_brief(
    project_dir: str,
    brief_id: str,
    title: str,
    task_type: str,
    governed_module: Optional[str],
    future_ssot_type: Optional[str],
    human_gate_required: bool,
    force: bool,
):
    """创建 Acceptance Brief 初稿"""
    project_root = Path(project_dir).resolve()
    briefs_dir = project_root / ".project" / "governance" / "ACCEPTANCE_BRIEFS"
    briefs_dir.mkdir(parents=True, exist_ok=True)

    filename = f"AB-{brief_id}-{_slugify(title)}.md"
    target = briefs_dir / filename

    if target.exists() and not force:
        raise click.ClickException(f"Acceptance Brief already exists: {target}")

    content = _build_acceptance_brief_content(
        brief_id=brief_id,
        title=title,
        task_type=task_type,
        governed_module=governed_module,
        future_ssot_type=future_ssot_type,
        human_gate_required=human_gate_required,
    )
    target.write_text(content, encoding="utf-8")

    click.echo(f"✅ Acceptance Brief created: {target}")
    click.echo("   Next step: edit scope, acceptance criteria, evidence, and migration fields before implementation.")


@governance.command("list-briefs")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--format", "output_format", default="table", type=click.Choice(["table", "json"]), help="输出格式")
def list_briefs(project_dir: str, output_format: str):
    """列出 Acceptance Brief"""
    briefs = _list_briefs(project_dir)
    if not briefs:
        click.echo("No Acceptance Briefs found.")
        return

    if output_format == "json":
        data = [
            {
                "filename": item["filename"],
                "path": item["path"],
                "brief_id": item["metadata"].get("brief_id"),
                "title": item["metadata"].get("title"),
                "status": item["metadata"].get("status"),
                "task_type": item["metadata"].get("task_type"),
            }
            for item in briefs
        ]
        click.echo(json.dumps(data, indent=2, ensure_ascii=False))
        return

    click.echo(f"{'Brief ID':<24} {'Status':<10} {'Type':<12} {'Title'}")
    click.echo("-" * 80)
    for item in briefs:
        metadata = item["metadata"]
        click.echo(
            f"{str(metadata.get('brief_id', '-')):<24} "
            f"{str(metadata.get('status', '-')):<10} "
            f"{str(metadata.get('task_type', '-')):<12} "
            f"{str(metadata.get('title', item['filename']))}"
        )


@governance.command("check-brief")
@click.argument("brief_ref")
@click.option("--project-dir", default=".", help="项目目录")
def check_brief(brief_ref: str, project_dir: str):
    """校验 Acceptance Brief front matter"""
    brief_path = Path(brief_ref)
    if not brief_path.is_absolute():
        candidates = _list_briefs(project_dir)
        resolved = None
        for item in candidates:
            metadata = item["metadata"]
            if metadata.get("brief_id") == brief_ref or item["filename"] == brief_ref:
                resolved = Path(item["path"])
                break
        if resolved is None:
            brief_path = _briefs_dir(project_dir) / brief_ref
        else:
            brief_path = resolved

    if not brief_path.exists():
        raise click.ClickException(f"Acceptance Brief not found: {brief_ref}")

    errors = _validate_brief(brief_path)
    if errors:
        click.echo(f"❌ Acceptance Brief invalid: {brief_path}")
        for error in errors:
            click.echo(f"   - {error}")
        raise click.Abort()

    metadata = _parse_front_matter(brief_path)
    click.echo(f"✅ Acceptance Brief valid: {brief_path}")
    click.echo(f"   brief_id: {metadata.get('brief_id')}")
    click.echo(f"   status: {metadata.get('status')}")
    click.echo(f"   human_gate_required: {metadata.get('human_gate_required')}")


def register_commands(cli_group):
    """将命令注册到 CLI 组"""
    cli_group.add_command(governance)
