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
        "_run_until_blocked_with_interrupt_guard",
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
        ["office.workspace-cleanup", "--project-dir", str(tmp_path)],
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
