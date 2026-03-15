from pathlib import Path

from click.testing import CliRunner
import yaml

import lee.cli.commands.run as run_module
from lee.cli.commands import demo as demo_module
from lee.cli.commands.workflow_compat import adapt_params_for_workflow, resolve_registry_entry
from lee.orchestrator.execution import workflow_runner as workflow_runner_module
from lee.orchestrator.execution.workflow_bootstrap import (
    build_runtime_context_from_params,
    hydrate_l2_bootstrap,
)


def _load_registry() -> dict:
    with open(Path("config/workflow-registry.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_registry_exposes_dev_canonical_aliases() -> None:
    workflows = (_load_registry().get("workflows") or {})

    assert workflows["dev.feature-delivery"]["path"].endswith("feature-delivery-l2-template.yaml")
    assert workflows["dev.feature-delivery"]["kind"] == "l2_workflow_template"
    assert workflows["dev.bugfix-delivery"]["path"].endswith("bugfix-delivery-l2-template.yaml")
    assert workflows["dev.bugfix-delivery"]["kind"] == "l2_workflow_template"
    assert workflows["dev.feature"]["canonical_workflow"] == "dev.feature-delivery"
    assert workflows["dev.bugfix"]["canonical_workflow"] == "dev.bugfix-delivery"
    assert workflows["dev.tech-design-l3"]["path"].endswith("tech-design-l3-template.yaml")
    assert workflows["dev.tech_design_l3"]["canonical_workflow"] == "dev.tech-design-l3"


def test_build_runtime_context_from_params_adds_repo_bindings() -> None:
    context = build_runtime_context_from_params(
        {
            "formal_ssot_id": "FEAT-001",
            "source_refs": ["spec/feat.md"],
            "governing_adrs": ["ADR-008"],
            "repo_context": {"repo_id": "be-repo", "type": "backend", "branch": "main"},
            "repo_frontend": "fe-repo",
            "repo_backend": "be-repo",
        }
    )

    assert context["formal_ssot_id"] == "FEAT-001"
    assert context["repo_frontend"] == "fe-repo"
    assert context["repo_backend"] == "be-repo"
    assert context["repo_context"]["branch"] == "main"
    assert {"id": "fe-repo", "type": "frontend"} in context["repos"]
    assert {"id": "be-repo", "type": "backend"} in context["repos"]


def test_compat_params_are_adapted_for_dev_feature() -> None:
    adapted = adapt_params_for_workflow(
        "dev.feature",
        {
            "project": "lee",
            "module": "dev",
            "feature_point_id": "FEAT-001",
            "feature_spec": "spec/feat.md",
            "repo_frontend": "fe-repo",
            "repo_backend": "be-repo",
            "branch": "main",
        },
    )

    assert adapted["formal_ssot_id"] == "FEAT-001"
    assert adapted["source_refs"] == ["spec/feat.md"]
    assert adapted["governing_adrs"] == ["ADR-008"]
    assert adapted["repo_context"]["repo_id"] == "be-repo"
    assert adapted["repo_context"]["branch"] == "main"


def test_compat_params_are_adapted_for_dev_bugfix() -> None:
    adapted = adapt_params_for_workflow(
        "dev.bugfix",
        {
            "bug_id": "BUG-001",
            "bug_description": "submit failed",
            "repo": "be-repo",
            "reproduction_steps": "click submit -> 500",
            "severity": "medium",
        },
    )

    assert adapted["bug_ssot_id"] == "BUG-001"
    assert adapted["severity"] == "P2"
    assert adapted["reproduction_evidence"]["summary"] == "click submit -> 500"
    assert adapted["repo_context"]["repo_id"] == "be-repo"


def test_compat_params_are_adapted_for_dev_tech_design(tmp_path: Path) -> None:
    feat_path = tmp_path / "spec" / "requirements" / "SRC-041" / "FEAT-SRC-041-001__gate.md"
    feat_path.parent.mkdir(parents=True, exist_ok=True)
    feat_path.write_text("---\nid: FEAT-SRC-041-001\n---\n", encoding="utf-8")

    adr_dir = tmp_path / "spec" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    (adr_dir / "ADR-008__runtime.md").write_text("# ADR-008\n", encoding="utf-8")
    (adr_dir / "ADR-017__gate.md").write_text("# ADR-017\n", encoding="utf-8")

    adapted = adapt_params_for_workflow(
        "dev.tech_design_l3",
        {
            "formal_ssot_id": "FEAT-SRC-041-001",
            "source_refs": ["EPIC-SRC-041-016#scope"],
            "governing_adrs": ["ADR-008", "ADR-017"],
            "repo_context": {"repo_id": "lee", "branch": "codex/tech-design-batch"},
        },
        project_root=tmp_path,
    )

    assert adapted["formal_ssot_path"] == feat_path.resolve().as_posix()
    assert adapted["source_refs"][0] == feat_path.resolve().as_posix()
    assert adapted["tech_spec_path"] == "spec/tech/SRC-041/TECH-FEAT-SRC-041-001__tech-design.md"
    assert adapted["design_analysis_path"] == "spec/tech/FEAT-SRC-041-001/design_analysis.md"
    assert adapted["decision_refs_path"] == "spec/tech/FEAT-SRC-041-001/decision_refs.yaml"
    assert adapted["governing_adr_paths"] == [
        (adr_dir / "ADR-008__runtime.md").resolve().as_posix(),
        (adr_dir / "ADR-017__gate.md").resolve().as_posix(),
    ]


def test_tech_design_template_binds_authoritative_feat_inputs() -> None:
    template_path = Path("spec-global/departments/dev/workflows/templates/tech-design-l3-template.yaml")
    template = yaml.safe_load(template_path.read_text(encoding="utf-8"))

    steps = template["stages"][0]["steps"]
    analyze_feature = next(step for step in steps if step["id"] == "analyze_feature")
    draft_tech_spec = next(step for step in steps if step["id"] == "draft_tech_spec")

    assert analyze_feature["inputs"]["formal_ssot_id"] == "{{ params.formal_ssot_id }}"
    assert analyze_feature["inputs"]["context_files"][0]["path"] == "{{ params.formal_ssot_path | default('') }}"
    assert analyze_feature["outputs"][0]["path"] == "{{ params.design_analysis_path }}"
    assert draft_tech_spec["inputs"]["context_files"][0]["path"] == "{{ params.formal_ssot_path | default('') }}"
    assert draft_tech_spec["outputs"][0]["path"] == "{{ params.tech_spec_path }}"
    assert "Formal FEAT ID: {{ params.formal_ssot_id }}." in draft_tech_spec["config"]["claude_code"]["goal"]


def test_hydrate_l2_bootstrap_preserves_phase_payload_and_sets_context() -> None:
    bootstrap = {
        "kind": "l2_workflow_instance",
        "context": {},
        "phases": [{"id": "tech_design", "status": "pending"}],
    }

    hydrated = hydrate_l2_bootstrap(
        bootstrap,
        {
            "bug_ssot_id": "BUG-001",
            "severity": "P1",
            "reproduction_evidence": {"summary": "demo"},
            "repo": "be-repo",
        },
    )

    assert hydrated["phases"] == bootstrap["phases"]
    assert hydrated["context"]["bug_ssot_id"] == "BUG-001"
    assert {"id": "be-repo", "type": "backend"} in hydrated["context"]["repos"]


def test_demo_prefers_registered_canonical_workflow_key() -> None:
    registry = {
        "workflows": {
            "dev.feature-delivery": {},
            "dev.feature": {},
        }
    }

    selected = demo_module._select_workflow_key(registry, ["dev.feature-delivery", "dev.feature"])
    assert selected == "dev.feature-delivery"


def test_resolve_registry_entry_redirects_old_dev_keys() -> None:
    workflows = (_load_registry().get("workflows") or {})

    effective_key, raw_entry, effective_entry = resolve_registry_entry(workflows, "dev.feature")
    assert effective_key == "dev.feature-delivery"
    assert raw_entry["required_params"] == ["project", "module", "feature_point_id"]
    assert effective_entry["path"].endswith("feature-delivery-l2-template.yaml")

    effective_key, raw_entry, effective_entry = resolve_registry_entry(workflows, "dev.bugfix")
    assert effective_key == "dev.bugfix-delivery"
    assert raw_entry["required_params"] == ["bug_id", "bug_description", "project", "repo"]
    assert effective_entry["path"].endswith("bugfix-delivery-l2-template.yaml")


def test_demo_create_and_run_uses_department_level_for_l2(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "feature-delivery-l2-template.yaml"
    template.write_text(
        "kind: l2_workflow_template\nversion: '3.0'\nphases: []\n",
        encoding="utf-8",
    )

    captured: list[dict] = []

    monkeypatch.setattr(
        demo_module,
        "resolve_workflow_template_path",
        lambda _path: template,
    )

    def fake_pm_workflow(action: str, **kwargs):
        captured.append({"action": action, "kwargs": kwargs})
        if action == "create":
            return {"workflow_id": "wf_dept_001"}
        if action == "run_until_blocked":
            return {"status": "completed", "blocked_at": None}
        if action == "get_state":
            return {"pending_gates": []}
        raise AssertionError(f"unexpected action: {action}")

    monkeypatch.setattr(demo_module, "pm_workflow", fake_pm_workflow)

    registry = {
        "workflows": {
            "dev.feature-delivery": {
                "path": str(template),
                "required_params": [],
            }
        }
    }

    demo_module._create_and_run(
        project_root=tmp_path,
        registry=registry,
        workflow_key="dev.feature-delivery",
        params={
            "formal_ssot_id": "FEAT-001",
            "source_refs": ["spec/feat.md"],
            "governing_adrs": ["ADR-008"],
            "repo_context": {"repo_id": "be-repo", "type": "backend"},
            "repo_frontend": "fe-repo",
            "repo_backend": "be-repo",
        },
        max_steps=1,
        approve=False,
        approver="demo-user",
        comments="demo",
    )

    create_call = next(call for call in captured if call["action"] == "create")
    assert create_call["kwargs"]["level"] == "department"
    assert create_call["kwargs"]["data"]["context"]["repo_frontend"] == "fe-repo"


def test_run_old_dev_feature_key_executes_canonical_workflow(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "feature-delivery-l2-template.yaml"
    template.write_text("kind: l2_workflow_template\nversion: '3.0'\nphases: []\n", encoding="utf-8")
    captured_create_payload = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "dev.feature": {
                    "path": str(template),
                    "canonical_workflow": "dev.feature-delivery",
                    "required_params": ["project", "module", "feature_point_id"],
                },
                "dev.feature-delivery": {
                    "path": str(template),
                    "kind": "l2_workflow_template",
                    "required_params": [
                        "formal_ssot_id",
                        "source_refs",
                        "governing_adrs",
                        "repo_context",
                        "repo_frontend",
                        "repo_backend",
                    ],
                },
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: template)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "completed", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_dept_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        [
            "dev.feature",
            "--project-dir",
            str(tmp_path),
            "--skip-plan",
            "--spec",
            str(
                _write_yaml(
                    tmp_path / "feature.yaml",
                    {
                        "project": "lee",
                        "module": "dev",
                        "feature_point_id": "FEAT-001",
                        "feature_spec": "spec/feat.md",
                        "repo_frontend": "fe-repo",
                        "repo_backend": "be-repo",
                    },
                )
            ),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = captured_create_payload[0]["data"]
    assert payload["workflow_key"] == "dev.feature-delivery"
    assert payload["invoked_workflow_key"] == "dev.feature"
    assert payload["context"]["formal_ssot_id"] == "FEAT-001"


def test_run_old_dev_bugfix_key_executes_canonical_workflow(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "bugfix-delivery-l2-template.yaml"
    template.write_text("kind: l2_workflow_template\nversion: '3.0'\nphases: []\n", encoding="utf-8")
    captured_create_payload = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "dev.bugfix": {
                    "path": str(template),
                    "canonical_workflow": "dev.bugfix-delivery",
                    "required_params": ["bug_id", "bug_description", "project", "repo"],
                },
                "dev.bugfix-delivery": {
                    "path": str(template),
                    "kind": "l2_workflow_template",
                    "required_params": ["bug_ssot_id", "severity", "reproduction_evidence"],
                },
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: template)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "completed", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_dept_002"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        [
            "dev.bugfix",
            "--project-dir",
            str(tmp_path),
            "--skip-plan",
            "--spec",
            str(
                _write_yaml(
                    tmp_path / "bugfix.yaml",
                    {
                        "bug_id": "BUG-001",
                        "bug_description": "submit failed",
                        "project": "lee",
                        "repo": "be-repo",
                        "reproduction_steps": "click submit -> 500",
                        "severity": "medium",
                    },
                )
            ),
        ],
    )

    assert result.exit_code == 0, result.output
    payload = captured_create_payload[0]["data"]
    assert payload["workflow_key"] == "dev.bugfix-delivery"
    assert payload["invoked_workflow_key"] == "dev.bugfix"
    assert payload["context"]["bug_ssot_id"] == "BUG-001"


def _write_yaml(path: Path, payload: dict) -> Path:
    path.write_text(yaml.safe_dump(payload, allow_unicode=True, sort_keys=False), encoding="utf-8")
    return path


def test_run_workflow_accepts_executor_selection_source(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")

    async def fake_run(self):
        return workflow_runner_module.WorkflowRunResult(
            workflow_id="wf_task_001",
            instance_path=None,
            plan_summary=None,
            success=True,
        )

    monkeypatch.setattr(workflow_runner_module.WorkflowRunner, "run", fake_run)

    result = workflow_runner_module.asyncio.run(
        workflow_runner_module.run_workflow(
            workflow_key="office.workspace-cleanup",
            template_path=template,
            params={},
            project_root=tmp_path,
            executor_override="codex",
            executor_selection_source="cli:codex",
        )
    )

    assert result.success is True
    assert result.workflow_id == "wf_task_001"
