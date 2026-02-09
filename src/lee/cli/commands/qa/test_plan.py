"""QA test-plan commands"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

import click
import yaml


@click.group()
def test_plan():
    """Test Plan 管理"""
    pass


@test_plan.command("create")
@click.argument("plan_id")
@click.option("--scope", "-s", multiple=True, required=True, help="测试范围（模块）")
@click.option("--test-set", "-t", multiple=True, required=True, help="关联的 Test Set ID")
@click.option("--exit-criteria", "-e", multiple=True, help="出测条件")
@click.option("--project-dir", default=".", help="项目目录")
def create(plan_id: str, scope: tuple, test_set: tuple, exit_criteria: tuple,
           project_dir: str) -> None:
    """创建 Test Plan（人工创建）"""
    project_root = Path(project_dir).resolve()
    plans_dir = project_root / "qa" / "test-plans"
    plans_dir.mkdir(parents=True, exist_ok=True)

    # 构建 Test Plan 数据
    test_sets_list: List[Dict[str, Any]] = []
    for i, ts_id in enumerate(test_set):
        test_sets_list.append({
            "test_set_id": ts_id,
            "critical": i == 0,  # 第一个默认为 critical
            "order": i + 1,
        })

    exit_criteria_list = list(exit_criteria) if exit_criteria else [
        "所有 critical test sets 至少通过一次",
        "无 P0 bug 未关闭",
        "P1 bug ≤ 3",
    ]

    data = {
        "test_plan_id": plan_id,
        "name": f"Test Plan {plan_id}",
        "scope": list(scope),
        "test_sets": test_sets_list,
        "risk_policy": {
            "critical_test_sets_must_pass": True,
            "medium_risk_allowed_failures": 1,
            "p1_bug_threshold": 3,
            "p2_bug_threshold": 10,
        },
        "entry_criteria": [
            "核心功能已联调",
            "开发自测完成",
        ],
        "exit_criteria": exit_criteria_list,
        "status": "ready",
        "max_rounds": 5,
        "created_by": "human",
    }

    plan_path = plans_dir / f"{plan_id}.yaml"
    with open(plan_path, "w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)

    click.echo(f"✓ 已创建 Test Plan: {plan_id}")
    click.echo(f"  路径: {plan_path}")
    click.echo(f"  范围: {', '.join(scope)}")
    click.echo(f"  Test Sets: {', '.join(test_set)}")


@test_plan.command("list")
@click.option("--project-dir", default=".", help="项目目录")
def list_test_plans(project_dir: str) -> None:
    """列出所有 Test Plan"""
    project_root = Path(project_dir).resolve()
    plans_dir = project_root / "qa" / "test-plans"

    if not plans_dir.exists():
        click.echo("暂无 Test Plan")
        return

    plan_files = list(plans_dir.glob("*.yaml"))
    if not plan_files:
        click.echo("暂无 Test Plan")
        return

    click.echo(f"共 {len(plan_files)} 个 Test Plan:\n")
    for f in sorted(plan_files):
        with open(f, encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        plan_id = data.get("test_plan_id", f.stem)
        name = data.get("name", "N/A")
        status = data.get("status", "N/A")
        scope = ", ".join(data.get("scope", []))
        click.echo(f"  {plan_id}: {name}")
        click.echo(f"    Status: {status}, Scope: {scope}")


@test_plan.command("show")
@click.argument("plan_id")
@click.option("--project-dir", default=".", help="项目目录")
def show_test_plan(plan_id: str, project_dir: str) -> None:
    """查看 Test Plan 详情"""
    project_root = Path(project_dir).resolve()
    plan_path = project_root / "qa" / "test-plans" / f"{plan_id}.yaml"

    if not plan_path.exists():
        raise click.ClickException(f"Test Plan not found: {plan_id}")

    with open(plan_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))
