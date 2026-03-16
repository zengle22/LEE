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
from lee.cli.commands.workflow_compat import adapt_params_for_workflow, resolve_registry_entry
from lee.orchestrator.api import pm_workflow
from lee.orchestrator.core.template_engine import TemplateEngine
from lee.orchestrator.execution.workflow_bootstrap import hydrate_l2_bootstrap
from lee.orchestrator.execution.workflow_runner import derive_workflow_creation_metadata
from lee.orchestrator.storage.models import WorkflowLevel


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


def _workflow_exists(registry: Dict[str, Any], workflow_key: str) -> bool:
    workflows = registry.get("workflows", {}) or {}
    return workflow_key in workflows


def _select_workflow_key(registry: Dict[str, Any], candidates: list[str]) -> str | None:
    for workflow_key in candidates:
        if _workflow_exists(registry, workflow_key):
            return workflow_key
    return None


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
    dry_run: bool = False,
) -> Tuple[str, Dict[str, Any]]:
    workflows = registry.get("workflows", {})
    if workflow_key not in workflows:
        raise click.ClickException(f"Unknown workflow: {workflow_key}")

    effective_workflow_key, entry, effective_entry = resolve_registry_entry(workflows, workflow_key)
    params = adapt_params_for_workflow(workflow_key, params, project_root=project_root)
    required = entry.get("required_params", []) or []
    missing = [p for p in required if not _has_param_with_aliases(params, p)]
    if missing:
        raise click.ClickException(f"Missing required params for {workflow_key}: {', '.join(missing)}")
    effective_required = effective_entry.get("required_params", []) or []
    effective_missing = [p for p in effective_required if not _has_param_with_aliases(params, p)]
    if effective_missing:
        raise click.ClickException(
            f"Missing canonical params after adapting '{workflow_key}' -> '{effective_workflow_key}': "
            f"{', '.join(effective_missing)}"
        )

    template_path = resolve_workflow_template_path(effective_entry.get("path", ""))
    if not template_path.exists():
        raise click.ClickException(f"Workflow template not found: {template_path}")

    rendered_path = _render_workflow_template(template_path, params, project_root)
    workflow_level, workflow_bootstrap = derive_workflow_creation_metadata(rendered_path)
    if workflow_level == WorkflowLevel.DEPARTMENT:
        workflow_bootstrap = hydrate_l2_bootstrap(workflow_bootstrap, params)

    if dry_run:
        click.echo(
            f"[dry-run] {workflow_key} -> {effective_workflow_key} "
            f"level={workflow_level.value} template={template_path}"
        )
        return (
            "dry-run",
            {
                "status": "dry-run",
                "blocked_at": None,
                "template": str(template_path),
                "effective_workflow_key": effective_workflow_key,
            },
        )

    create_result = pm_workflow(
        "create",
        project_dir=str(project_root),
        level=workflow_level.value,
        template_id=str(rendered_path),
        data={
            "params": params,
            "workflow_key": effective_workflow_key,
            "invoked_workflow_key": workflow_key,
            **workflow_bootstrap,
        },
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
@click.option("--dry-run", is_flag=True, help="只解析和渲染 demo workflows，不创建/执行实例")
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
    dry_run: bool,
) -> None:
    """运行 demo workflows（Dev/QA/DevOps）并自动审批 gate"""
    os.environ.setdefault("LEE_DEMO_MODE", "1")

    project_root = Path(project_dir).resolve()
    if init_specs:
        _ensure_demo_specs(
            project_root / feature_spec,
            project_root / test_plan,
            project_root / deploy_config,
        )

    registry = _load_registry()

    click.echo("Running demo workflows...")
    results = []

    dev_workflow = _select_workflow_key(registry, ["dev.feature-delivery", "dev.feature"])
    if dev_workflow == "dev.feature-delivery":
        dev_params = {
            "formal_ssot_id": "FEAT-DEMO-001",
            "source_refs": [str(project_root / feature_spec)],
            "governing_adrs": ["ADR-008"],
            "repo_context": {"repo_id": "lee-backend", "type": "backend", "branch": branch},
            "repo_frontend": "lee-frontend",
            "repo_backend": "lee-backend",
        }
    elif dev_workflow == "dev.feature":
        dev_params = {
            "project": "lee",
            "module": "dev",
            "feature_point_id": "FEAT-DEMO-001",
            "feature_spec": str(project_root / feature_spec),
            "repo_frontend": "lee-frontend",
            "repo_backend": "lee-backend",
            "branch": branch,
        }
    else:
        dev_params = None

    if dev_workflow and dev_params:
        results.append(
            (dev_workflow,)
            + _create_and_run(
                project_root, registry, dev_workflow, dev_params, max_steps, approve, approver, comments, dry_run
            )
        )
    else:
        click.echo("Skipping Dev demo: no registered dev demo workflow found.")

    qa_workflow = _select_workflow_key(registry, ["qa.test-plan-execution", "qa.regression"])
    if qa_workflow == "qa.test-plan-execution":
        qa_params = {
            "test_plan_id": "TESTPLAN-DEMO-001",
            "build_version": version,
            "build_commit": version,
            "environment": env,
        }
    elif qa_workflow == "qa.regression":
        qa_params = {"spec": str(project_root / test_plan), "env": env, "version": version}
    else:
        qa_params = None

    if qa_workflow and qa_params:
        results.append(
            (qa_workflow,)
            + _create_and_run(
                project_root, registry, qa_workflow, qa_params, max_steps, approve, approver, comments, dry_run
            )
        )
    else:
        click.echo("Skipping QA demo: no registered QA demo workflow found.")

    if _workflow_exists(registry, "devops.deploy"):
        devops_params = {"env": env, "version": version}
        results.append(
            ("devops.deploy",)
            + _create_and_run(
                project_root, registry, "devops.deploy", devops_params, max_steps, approve, approver, comments, dry_run
            )
        )
    else:
        click.echo("Skipping DevOps demo: workflow `devops.deploy` is not registered.")

    for workflow_key, workflow_id, summary in results:
        status = summary.get("status")
        blocked_at = summary.get("blocked_at")
        if workflow_id == "dry-run":
            click.echo(
                f"{workflow_key}: dry-run status={status} "
                f"template={summary.get('template')}"
            )
            continue
        click.echo(f"{workflow_key}: {workflow_id} status={status} blocked_at={blocked_at}")
