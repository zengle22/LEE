from pathlib import Path
from typing import Any, Dict, List

from click.testing import CliRunner
import yaml

import lee.cli.commands.run as run_module


def test_load_template_param_defaults(tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text(
        """
kind: workflow
params:
  workspace_path:
    type: string
    default: .
  exclude_patterns:
    type: array
    default: [".git", "node_modules"]
  no_default:
    type: string
""",
        encoding="utf-8",
    )
    defaults = run_module._load_template_param_defaults(template)
    assert defaults["workspace_path"] == "."
    assert defaults["exclude_patterns"] == [".git", "node_modules"]
    assert "no_default" not in defaults


def test_run_uses_template_default_params(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text(
        """
kind: workflow
version: "1.0"
params:
  workspace_path:
    type: string
    default: .
  author_name:
    type: string
    default: LEE Team
""",
        encoding="utf-8",
    )
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")

    captured_create_payload: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "office.workspace-cleanup": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_existing_same_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "completed", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_new_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["office.workspace-cleanup", "--project-dir", str(tmp_path), "--skip-plan"],
    )
    assert result.exit_code == 0, result.output
    assert len(captured_create_payload) == 1
    params = captured_create_payload[0]["data"]["params"]
    assert params["workspace_path"] == "."
    assert params["author_name"] == "LEE Team"


def test_render_workflow_template_injects_date_and_timestamp(tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text(
        """
kind: workflow
id: workflow.test.render_vars
version: "1.0"
contracts:
  outputs:
    - report:
        path: "reports/report-{{ date }}-{{ timestamp }}.yaml"
""",
        encoding="utf-8",
    )

    rendered_path = run_module._render_workflow_template(
        template_path=template,
        params={},
        project_dir=tmp_path,
    )

    rendered_doc = yaml.safe_load(rendered_path.read_text(encoding="utf-8"))
    output_path = rendered_doc["contracts"]["outputs"][0]["report"]["path"]
    assert "{{ date }}" not in output_path
    assert "{{ timestamp }}" not in output_path
    assert output_path.startswith("reports/report-")
    assert output_path.endswith(".yaml")


def test_run_loads_object_spec_into_params_without_registry_flag(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    spec_file = tmp_path / "input.yaml"
    spec_file.write_text("epic_freeze: spec/epic-freeze.yaml\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")

    captured_create_payload: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.epic-to-feat": {
                    "path": str(template),
                    "required_params": ["epic_freeze"],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_existing_same_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_new_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.epic-to-feat", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(spec_file)],
    )

    assert result.exit_code == 0, result.output
    params = captured_create_payload[0]["data"]["params"]
    assert params["epic_freeze"] == "spec/epic-freeze.yaml"


def test_run_falls_back_to_spec_path_for_non_object_spec(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    spec_file = tmp_path / "input.md"
    spec_file.write_text("# Demo Spec\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")

    captured_create_payload: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "office.workspace-cleanup": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_existing_same_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_new_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["office.workspace-cleanup", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(spec_file)],
    )

    assert result.exit_code == 0, result.output
    params = captured_create_payload[0]["data"]["params"]
    assert params["spec"] == str(spec_file.resolve())


def test_run_uses_instance_without_existing_workflow_selection(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    spec_file = tmp_path / "input.yaml"
    spec_file.write_text("module: demo\nfeat_freeze: FEAT-023\n", encoding="utf-8")

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "qa.test-set-production": {
                    "path": str(template),
                    "required_params": ["module", "feat_freeze"],
                }
            }
        },
    )

    def fail_existing(*_args, **_kwargs):
        raise AssertionError("existing workflow selection should be skipped when --instance is provided")

    monkeypatch.setattr(run_module, "_list_existing_same_workflows", fail_existing)
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "completed", "completed_steps": 3, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        [
            "qa.test-set-production",
            "--project-dir",
            str(tmp_path),
            "--skip-plan",
            "--instance",
            "wf_task_demo_001",
            "--spec",
            str(spec_file),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "Using existing workflow instance: wf_task_demo_001" in result.output


def test_refresh_summary_from_store_promotes_terminal_status(tmp_path: Path) -> None:
    summary = {"status": "running", "completed_steps": 3, "blocked_at": None}

    states = iter(
        [
            {"status": "running", "completed": 3, "current_step": "output_validation", "failed": 0},
            {"status": "completed", "completed": 5, "current_step": None, "failed": 0},
        ]
    )

    original = run_module._get_progress_snapshot
    run_module._get_progress_snapshot = lambda *_args, **_kwargs: next(states, None)
    try:
        refreshed = run_module._refresh_summary_from_store(
            tmp_path,
            "wf_task_demo_002",
            summary,
            poll_attempts=2,
            poll_interval_seconds=0.0,
        )
    finally:
        run_module._get_progress_snapshot = original

    assert refreshed["status"] == "completed"
    assert refreshed["completed_steps"] == 5
