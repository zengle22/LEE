"""QA test-set commands"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict

import click
import yaml

from lee.cli.commands.workflow_registry import (
    get_workflow_registry_path,
    load_workflow_registry,
    resolve_workflow_template_path,
)
from lee.orchestrator.api import pm_workflow
from lee.orchestrator.core.template_engine import TemplateEngine


def _get_registry_path(project_dir: str = ".") -> Path:
    """获取 workflow registry 路径"""
    return get_workflow_registry_path()


def _load_registry(project_dir: str = ".") -> Dict[str, Any]:
    return load_workflow_registry()


def _load_dirs_config(project_dir: Path) -> Dict[str, Any]:
    """Load directory structure configuration from .project/dirs.yaml"""
    config_file = project_dir / ".project" / "dirs.yaml"
    if not config_file.exists():
        # Fallback to default
        return {
            "directories": {
                "specs_dir": {"path": "spec"},
                "spec_dir": {"path": "spec"},  # 别名支持
                "qa_specs_dir": {"path": "spec/qa"},
                "src_dir": {"path": "src"},
                "docs_dir": {"path": "docs"},
                "tests_dir": {"path": "tests"},
                "artifacts_dir": {"path": ".artifacts"},
            }
        }
    
    with open(config_file, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f) or {}


def _build_dir_context(project_dir: Path) -> Dict[str, str]:
    """Build directory context for template rendering."""
    dirs_config = _load_dirs_config(project_dir)
    directories = dirs_config.get("directories", {})
    context = {}
    
    # 直接映射目录配置到模板变量
    if "specs_dir" in directories:
        context["specs_dir"] = directories["specs_dir"].get("path", "spec")
    elif "spec_dir" in directories:
        context["specs_dir"] = directories["spec_dir"].get("path", "spec")
    else:
        context["specs_dir"] = "spec"
    
    if "qa_specs_dir" in directories:
        context["qa_specs_dir"] = directories["qa_specs_dir"].get("path", "spec/qa")
    else:
        context["qa_specs_dir"] = "spec/qa"
    
    # 其他目录直接映射
    for dir_name in ["src_dir", "docs_dir", "tests_dir", "artifacts_dir"]:
        if dir_name in directories:
            context[dir_name] = directories[dir_name].get("path", dir_name.replace("_dir", ""))
        else:
            defaults = {
                "src_dir": "src",
                "docs_dir": "docs",
                "tests_dir": "tests",
                "artifacts_dir": ".artifacts",
            }
            context[dir_name] = defaults.get(dir_name, dir_name.replace("_dir", ""))
    
    return context


def _render_workflow_template(template_path: Path, params: Dict[str, Any], project_dir: Path) -> Path:
    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    # 构建目录上下文
    dir_context = _build_dir_context(project_dir)
    
    engine = TemplateEngine()
    # 将 params 展开到 context 中，使模板中的 {{ module }} 等变量可以直接访问
    # 同时保留 params 键以兼容某些使用 {{ params.xxx }} 的模板
    context = dict(params)  # 复制 params 到顶层
    context["params"] = params  # 同时保留 params 嵌套结构
    context.update(dir_context)  # 注入目录变量
    
    rendered = engine.render_string(content, context)
    yaml.safe_load(rendered)

    out_dir = project_dir / ".workflow" / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = out_dir / f"{template_path.stem}-{stamp}.yaml"
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


@click.group()
def test_set():
    """Test Set 管理"""
    pass


@test_set.command("create")
@click.argument("module")
@click.option("--requirement", "-r", required=True, help="需求文档路径")
@click.option("--tech-design", "-t", help="技术设计文档路径（可选）")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=20, show_default=True, help="最大执行步数")
def create(module: str, requirement: str, tech_design: str | None,
           project_dir: str, max_steps: int) -> None:
    """生产 Test Set"""
    registry = _load_registry()
    workflows = registry.get("workflows", {})
    workflow_key = "qa.test-set-production"

    if workflow_key not in workflows:
        raise click.ClickException(f"Workflow not found: {workflow_key}")

    entry = workflows[workflow_key]
    template_path = resolve_workflow_template_path(entry.get("path", ""))
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    # 设置默认参数
    params: Dict[str, Any] = {
        "module": module,
        "requirement_doc": requirement,
    }
    if tech_design:
        params["tech_design"] = tech_design

    project_root = Path(project_dir).resolve()
    rendered_path = _render_workflow_template(template_path, params, project_root)

    create_result = pm_workflow(
        "create",
        project_dir=str(project_root),
        level="task",
        template_id=str(rendered_path),
        data={"params": params, "workflow_key": workflow_key},
    )

    if "error" in create_result:
        raise click.ClickException(create_result["error"])

    workflow_id = create_result.get("workflow_id")
    click.echo(f"✓ 已创建 Test Set 生产工作流: {workflow_id}")
    click.echo(f"  Module: {module}")
    click.echo(f"  Requirement: {requirement}")
    if tech_design:
        click.echo(f"  Tech Design: {tech_design}")

    summary = pm_workflow(
        "run_until_blocked",
        project_dir=str(project_root),
        workflow_id=workflow_id,
        max_steps=max_steps,
    )

    _print_execution_summary(summary)


@test_set.command("list")
@click.option("--project-dir", default=".", help="项目目录")
def list_test_sets(project_dir: str) -> None:
    """列出所有 Test Set"""
    project_root = Path(project_dir).resolve()
    test_sets_dir = project_root / "spec" / "qa" / "test-sets"

    if not test_sets_dir.exists():
        click.echo("暂无 Test Set")
        return

    test_set_files = list(test_sets_dir.glob("ts-*.yaml"))
    if not test_set_files:
        click.echo("暂无 Test Set")
        return

    click.echo(f"共 {len(test_set_files)} 个 Test Set:\n")
    for f in sorted(test_set_files):
        with open(f, encoding="utf-8") as fp:
            data = yaml.safe_load(fp) or {}
        ts_id = data.get("test_set_id", f.stem)
        module = data.get("module", "N/A")
        status = data.get("status", "N/A")
        click.echo(f"  {ts_id}: {module} [{status}]")


@test_set.command("show")
@click.argument("test_set_id")
@click.option("--project-dir", default=".", help="项目目录")
def show_test_set(test_set_id: str, project_dir: str) -> None:
    """查看 Test Set 详情"""
    project_root = Path(project_dir).resolve()

    # 尝试多种命名格式
    possible_paths = [
        project_root / "spec" / "qa" / "test-sets" / f"{test_set_id}.yaml",
        project_root / "spec" / "qa" / "test-sets" / f"ts-{test_set_id}.yaml",
        project_root / "spec" / "qa" / "test-sets" / f"ts-{test_set_id.lower().replace('_', '-')}.yaml",
    ]

    test_set_path = None
    for p in possible_paths:
        if p.exists():
            test_set_path = p
            break

    if not test_set_path:
        raise click.ClickException(f"Test Set not found: {test_set_id}")

    with open(test_set_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    click.echo(yaml.dump(data, allow_unicode=True, default_flow_style=False))


@test_set.command("run")
@click.argument("test_set_id")
@click.option("--test-run-id", default=None, help="Test Run ID (自动生成)")
@click.option("--build-version", default="dev", help="构建版本")
@click.option("--build-commit", default="", help="Git commit")
@click.option("--environment", default="test", help="测试环境")
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--max-steps", default=20, show_default=True, help="最大执行步数")
def run_test_set(test_set_id: str, test_run_id: str, build_version: str,
                 build_commit: str, environment: str, project_dir: str, max_steps: int) -> None:
    """直接运行 L3 Test Set (跳过 L2)"""
    raise click.ClickException(
        "`lee qa test-set run` 已被 FEAT-143 收紧。请先生成标准 TASK，再使用 `lee qa execute <TASK-TESTPLAN-REL-...>`。"
    )
    import random
    import string

    project_root = Path(project_dir).resolve()

    # 查找 Test Set 文件
    possible_paths = [
        project_root / "spec" / "qa" / "test-sets" / f"{test_set_id}.yaml",
        project_root / "spec" / "qa" / "test-sets" / f"ts-{test_set_id}.yaml",
        project_root / "spec" / "qa" / "test-sets" / f"ts-{test_set_id.lower().replace('_', '-')}.yaml",
    ]

    test_set_path = None
    for p in possible_paths:
        if p.exists():
            test_set_path = p
            break

    if not test_set_path:
        raise click.ClickException(f"Test Set not found: {test_set_id}")

    # 加载 Test Set 定义
    with open(test_set_path, encoding="utf-8") as f:
        test_set_definition = yaml.safe_load(f)

    # 生成 Test Run ID
    if not test_run_id:
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        test_run_id = f"TR-{datetime.now().strftime('%Y-%m-%d')}-{suffix}"

    click.echo(f"=== L3 Test Set 调试模式 ===")
    click.echo(f"Test Set: {test_set_id}")
    click.echo(f"Test Run: {test_run_id}")
    click.echo(f"Build: {build_version}")
    click.echo(f"Environment: {environment}")
    click.echo()

    # 创建 L3 工作流 - 使用完整路径
    template_path = "spec-global/departments/qa/workflows/templates/test-set-execute-l3-template.yaml"
    create_result = pm_workflow(
        "create",
        project_dir=str(project_root),
        level="task",
        template_id=template_path,
        data={
            "test_run_id": test_run_id,
            "test_set_id": test_set_id,
            "test_set_definition": test_set_definition,
            "build_version": build_version,
            "build_commit": build_commit,
            "environment": environment,
            # 这些字段在调试模式下提供空值
            "env_check_result": {
                "status": "healthy",
                "tools": [],
                "warnings": []
            },
            "dependency_results": {},
            "parent_l2_id": "DEBUG-L3",
            "parent_phase_id": "DEBUG",
        },
    )

    if "error" in create_result:
        raise click.ClickException(f"创建失败: {create_result['error']}")

    workflow_id = create_result.get("workflow_id")
    click.echo(f"✓ 已创建 L3 Workflow: {workflow_id}")
    click.echo()

    # 执行工作流
    summary = pm_workflow(
        "run_until_blocked",
        project_dir=str(project_root),
        workflow_id=workflow_id,
        max_steps=max_steps,
    )

    _print_execution_summary(summary)


def _print_execution_summary(summary: Dict[str, Any]) -> None:
    """打印执行摘要"""
    if "error" in summary:
        click.echo(f"\n执行出错: {summary['error']}")
        return

    status = summary.get("status", "unknown")
    steps_executed = summary.get("steps_executed", 0)
    current_step = summary.get("current_step", "N/A")
    blocked_by = summary.get("blocked_by")

    click.echo(f"\n执行状态: {status}")
    click.echo(f"已执行步骤: {steps_executed}")
    click.echo(f"当前步骤: {current_step}")

    if blocked_by:
        click.echo(f"\n⏸ 等待: {blocked_by}")
        if "gate" in str(blocked_by).lower():
            click.echo(f"批准命令: lee approve <gate-id>")
