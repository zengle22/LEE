"""lee demo command"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Tuple

import click
import yaml

from lee.cli.commands.workflow_registry import (
    load_workflow_registry,
    resolve_workflow_template_path,
)
from lee.orchestrator.api import pm_workflow
from lee.orchestrator.core.template_engine import TemplateEngine


def _param_aliases(name: str) -> list[str]:
    if not isinstance(name, str):
        return []
    if name.endswith("_freeze"):
        return [f"{name}_ref"]
    if name.endswith("_freeze_ref"):
        return [name[:-4]]
    return []


def _has_param_with_aliases(params: Dict[str, Any], name: str) -> bool:
    for candidate in [name, *_param_aliases(name)]:
        if candidate in params:
            return True
    return False

def _load_registry() -> Dict[str, Any]:
    return load_workflow_registry()


def _render_workflow_template(template_path: Path, params: Dict[str, Any], project_root: Path) -> Path:
    with open(template_path, encoding="utf-8") as f:
        content = f.read()

    engine = TemplateEngine()
    rendered = engine.render_string(content, {"params": params})
    yaml.safe_load(rendered)

    out_dir = project_root / ".workflow" / "rendered"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d%H%M%S")
    out_path = out_dir / f"{template_path.stem}-{stamp}.yaml"
    out_path.write_text(rendered, encoding="utf-8")
    return out_path


def _ensure_demo_specs(feature_spec: Path, test_plan: Path, deploy_config: Path) -> None:
    feature_spec.parent.mkdir(parents=True, exist_ok=True)
    if not feature_spec.exists():
        feature_spec.write_text(
            "{\n"
            "  \"title\": \"Demo Feature\",\n"
            "  \"summary\": \"Add a demo flag to L3 pipeline\",\n"
            "  \"acceptance\": [\"Pipeline runs end-to-end in demo mode\"]\n"
            "}\n",
            encoding="utf-8",
        )

    test_plan.parent.mkdir(parents=True, exist_ok=True)
    if not test_plan.exists():
        test_plan.write_text(
            "{\n"
            "  \"title\": \"Demo Regression Plan\",\n"
            "  \"scopes\": [\"smoke\", \"regression\"],\n"
            "  \"environments\": [\"staging\"]\n"
            "}\n",
            encoding="utf-8",
        )

    deploy_config.parent.mkdir(parents=True, exist_ok=True)
    if not deploy_config.exists():
        deploy_config.write_text(
            "{\n"
            "  \"environment\": \"staging\",\n"
            "  \"version\": \"v0.0.0-demo\"\n"
            "}\n",
            encoding="utf-8",
        )


def _create_and_run(
    project_root: Path,
    registry: Dict[str, Any],
    workflow_key: str,
    params: Dict[str, Any],
    max_steps: int,
    approve: bool,
    approver: str,
    comments: str,
) -> Tuple[str, Dict[str, Any]]:
    workflows = registry.get("workflows", {})
    if workflow_key not in workflows:
        raise click.ClickException(f"Unknown workflow: {workflow_key}")

    entry = workflows[workflow_key]
    required = entry.get("required_params", []) or []
    missing = [p for p in required if not _has_param_with_aliases(params, p)]
    if missing:
        raise click.ClickException(f"Missing required params for {workflow_key}: {', '.join(missing)}")

    template_path = resolve_workflow_template_path(entry.get("path", ""))
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    rendered_path = _render_workflow_template(template_path, params, project_root)
    create_result = pm_workflow(
        "create",
        project_dir=str(project_root),
        level="task",
        template_id=str(rendered_path),
        data={"params": params, "workflow_key": workflow_key},
    )

    workflow_id = create_result.get("workflow_id")
    summary = pm_workflow(
        "run_until_blocked",
        project_dir=str(project_root),
        workflow_id=workflow_id,
        max_steps=max_steps,
    )

    if approve:
        state = pm_workflow("get_state", project_dir=str(project_root), workflow_id=workflow_id)
        for gate in state.get("pending_gates", []) or []:
            gate_id = gate.get("gate_id") or gate.get("id") or gate.get("gate")
            if not gate_id:
                continue
            pm_workflow(
                "approve_gate",
                project_dir=str(project_root),
                workflow_id=workflow_id,
                gate_id=gate_id,
                approver=approver,
                comments=comments,
            )

        summary = pm_workflow(
            "run_until_blocked",
            project_dir=str(project_root),
            workflow_id=workflow_id,
            max_steps=max_steps,
        )

    return workflow_id, summary


@click.command()
@click.option("--project-dir", default=".", help="项目目录")
@click.option("--branch", default="demo/l3", help="Dev 分支名")
@click.option("--env", default="staging", help="目标环境")
@click.option("--version", default="v0.0.0-demo", help="版本/commit")
@click.option("--feature-spec", "feature_spec", default="spec/feature-spec.json", help="Feature spec 路径")
@click.option("--test-plan", "test_plan", default="spec/test-plan.json", help="Test plan 路径")
@click.option("--deploy-config", "deploy_config", default="spec/deploy-config.json", help="Deploy config 路径")
@click.option("--max-steps", default=50, show_default=True, help="最大执行步数")
@click.option("--approve/--no-approve", default=True, show_default=True, help="自动审批 gate")
@click.option("--approver", default="demo-user", show_default=True, help="审批人")
@click.option("--comments", default="demo approval", show_default=True, help="审批意见")
@click.option("--init-specs/--no-init-specs", default=True, show_default=True, help="自动生成 demo spec")
def demo(
    project_dir: str,
    branch: str,
    env: str,
    version: str,
    feature_spec: str,
    test_plan: str,
    deploy_config: str,
    max_steps: int,
    approve: bool,
    approver: str,
    comments: str,
    init_specs: bool,
) -> None:
    """运行 L3 demo（Dev/QA/DevOps）并自动审批 gate"""
    os.environ.setdefault("LEE_DEMO_MODE", "1")

    project_root = Path(project_dir).resolve()
    if init_specs:
        _ensure_demo_specs(
            project_root / feature_spec,
            project_root / test_plan,
            project_root / deploy_config,
        )

    registry = _load_registry()

    click.echo("Running L3 demo workflows...")
    results = []

    dev_params = {"spec": feature_spec, "branch": branch}
    results.append(("dev.feature",) + _create_and_run(
        project_root, registry, "dev.feature", dev_params, max_steps, approve, approver, comments
    ))

    qa_params = {"spec": test_plan, "env": env, "version": version}
    results.append(("qa.regression",) + _create_and_run(
        project_root, registry, "qa.regression", qa_params, max_steps, approve, approver, comments
    ))

    devops_params = {"env": env, "version": version}
    results.append(("devops.deploy",) + _create_and_run(
        project_root, registry, "devops.deploy", devops_params, max_steps, approve, approver, comments
    ))

    for workflow_key, workflow_id, summary in results:
        click.echo(f"{workflow_key}: {workflow_id} status={summary.get('status')} blocked_at={summary.get('blocked_at')}")
