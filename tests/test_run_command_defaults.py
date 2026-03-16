from pathlib import Path
from typing import Any, Dict, List
import json
import sqlite3
import io

from click.testing import CliRunner
import pytest
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
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
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
    assert captured_create_payload[0]["data"]["concurrency_scope"].startswith("project:")
    assert captured_create_payload[0]["data"]["concurrency_key"].startswith("office.workspace-cleanup::")


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
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
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
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
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


def test_run_loads_markdown_spec_into_raw_requirement_for_product_main(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: l2_workflow_template\nversion: '1.0'\n", encoding="utf-8")
    spec_file = tmp_path / "adr.md"
    spec_file.write_text("# ADR-011\n需求链一致性测试体系建设\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: l2_workflow_template\nid: x\nversion: '1.0'\nphases: []\n", encoding="utf-8")

    captured_create_payload: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "load_spec_as_params": True,
                    "required_params": [],
                    "optional_params": ["raw_requirement"],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
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
            return {"workflow_id": "wf_department_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(spec_file)],
    )

    assert result.exit_code == 0, result.output
    params = captured_create_payload[0]["data"]["params"]
    assert params["raw_requirement"] == "# ADR-011\n需求链一致性测试体系建设\n"
    assert "spec" not in params


def test_run_loads_formal_adr_spec_into_adr_and_raw_requirement_for_product_main(
    monkeypatch, tmp_path: Path
) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: l2_workflow_template\nversion: '1.0'\n", encoding="utf-8")
    spec_file = tmp_path / "spec" / "adr" / "ADR-019__demo.md"
    spec_file.parent.mkdir(parents=True, exist_ok=True)
    spec_file.write_text(
        "\n".join(
            [
                "---",
                "id: ADR-019",
                "ssot_type: adr",
                "title: EPIC 入口统一经 SRC",
                "status: draft",
                "version: v1",
                "---",
                "",
                "## 1. Decision",
                "",
                "- 所有正式 EPIC 都必须经由冻结后的 SRC 进入主链。",
                "",
                "## 3. Problem",
                "",
                "- 直接把 ADR 当成 EPIC source object 会打破现有边界。",
                "",
                "## 11. Follow-Up",
                "",
                "1. 为 bridge SRC 增加字段模板。",
            ]
        ),
        encoding="utf-8",
    )
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: l2_workflow_template\nid: x\nversion: '1.0'\nphases: []\n", encoding="utf-8")

    captured_create_payload: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "load_spec_as_params": True,
                    "required_params": [],
                    "optional_params": ["adr", "raw_requirement"],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
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
            return {"workflow_id": "wf_department_adr_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(spec_file)],
    )

    assert result.exit_code == 0, result.output
    params = captured_create_payload[0]["data"]["params"]
    assert params["adr"]["artifact_id"] == "ADR-019"
    assert params["adr"]["ssot_type"] == "ADR"
    assert params["adr"]["path"] == str(spec_file.resolve())
    assert "Decision:" in params["raw_requirement"]
    assert "Problem:" in params["raw_requirement"]
    assert "Follow-Up:" in params["raw_requirement"]
    assert "spec" not in params


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

    monkeypatch.setattr(run_module, "_list_conflicting_workflows", fail_existing)
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


def test_run_uses_epic_scope_for_epic_to_feat(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    spec_file = tmp_path / "input.yaml"
    spec_file.write_text("epic_freeze:\n  artifact_id: EPIC-123\n", encoding="utf-8")
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
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
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
    create_data = captured_create_payload[0]["data"]
    assert create_data["concurrency_scope"] == "epic:EPIC-123"
    assert create_data["scope_source"] == "params.epic_freeze.artifact_id"


def test_run_bootstraps_l2_template_as_department_workflow(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: l2_workflow_template\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text(
        "\n".join(
            [
                "kind: l2_workflow_template",
                "version: '1.0'",
                "id: workflow.product.product_main_pipeline",
                "phases:",
                "  - id: src_to_epic",
                "    name: SRC to EPIC",
                "    workflow: workflow.product.task.src_to_epic",
                "    level: task",
                "    depends_on: []",
                "    default_complexity: M",
                "    output_map:",
                "      source_freeze: $child_data.step_outputs.source_freeze",
            ]
        ),
        encoding="utf-8",
    )

    captured_create_payload: List[Dict[str, Any]] = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_department_demo_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)
    monkeypatch.setenv("LLM_PROFILE", "qwen")

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan"],
    )

    assert result.exit_code == 0, result.output
    assert captured_create_payload[0]["level"] == "department"
    create_data = captured_create_payload[0]["data"]
    assert create_data["kind"] == "l2_workflow_instance"
    assert create_data["llm_profile"] == "qwen"
    assert create_data["phases"] == [
        {
            "id": "src_to_epic",
            "name": "SRC to EPIC",
            "description": "",
            "complexity": "M",
            "status": "pending",
            "depends_on": [],
            "workflow": "workflow.product.task.src_to_epic",
            "level": "task",
            "output_map": {
                "source_freeze": "$child_data.step_outputs.source_freeze",
            },
            "l3_instance_ids": [],
        }
    ]
    assert create_data["executor_override"] == "claude_code"
    assert create_data["executor_selection_source"] == "default"


def test_list_conflicting_workflows_matches_scope_and_legacy_rows(tmp_path: Path) -> None:
    db_path = tmp_path / ".workflow" / "orchestrator.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            """
            CREATE TABLE workflow_instances (
                id TEXT,
                status TEXT,
                current_step TEXT,
                created_at TEXT,
                data TEXT
            )
            """
        )
        conn.execute(
            "INSERT INTO workflow_instances VALUES (?, ?, ?, ?, ?)",
            (
                "wf_same_scope",
                "running",
                "step_a",
                "2026-03-11T10:00:00",
                json.dumps({
                    "workflow_key": "product.epic-to-feat",
                    "concurrency_scope": "epic:EPIC-123",
                }),
            ),
        )
        conn.execute(
            "INSERT INTO workflow_instances VALUES (?, ?, ?, ?, ?)",
            (
                "wf_other_scope",
                "running",
                "step_b",
                "2026-03-11T10:01:00",
                json.dumps({
                    "workflow_key": "product.epic-to-feat",
                    "concurrency_scope": "epic:EPIC-999",
                }),
            ),
        )
        conn.execute(
            "INSERT INTO workflow_instances VALUES (?, ?, ?, ?, ?)",
            (
                "wf_legacy",
                "paused",
                "step_c",
                "2026-03-11T10:02:00",
                json.dumps({
                    "workflow_key": "product.epic-to-feat",
                }),
            ),
        )
        conn.commit()
    finally:
        conn.close()


def test_run_accepts_qwen_executor_override(monkeypatch, tmp_path: Path) -> None:
    from click.testing import CliRunner
    from lee.cli.commands import run as run_module

    template = tmp_path / "workflow.yaml"
    rendered = tmp_path / "rendered.yaml"
    template.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")
    rendered.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")

    captured_create_payload = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_department_demo_002"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan", "--executor", "qwen_chat"],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["executor_override"] == "qwen_chat"
    assert create_data["executor_selection_source"] == "cli_override"


def test_run_normalizes_legacy_qwen_executor_override(monkeypatch, tmp_path: Path) -> None:
    from click.testing import CliRunner
    from lee.cli.commands import run as run_module

    template = tmp_path / "workflow.yaml"
    rendered = tmp_path / "rendered.yaml"
    template.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")
    rendered.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")

    captured_create_payload = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_department_demo_alias"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan", "--executor", "qwen"],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["executor_override"] == "qwen_chat"
    assert create_data["executor_selection_source"] == "cli_override"


def test_run_accepts_kimi_executor_override(monkeypatch, tmp_path: Path) -> None:
    from click.testing import CliRunner
    from lee.cli.commands import run as run_module

    template = tmp_path / "workflow.yaml"
    rendered = tmp_path / "rendered.yaml"
    template.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")
    rendered.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")

    captured_create_payload = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_department_demo_003"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan", "--executor", "kimi"],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["executor_override"] == "kimi"
    assert create_data["executor_selection_source"] == "cli_override"


def test_run_uses_config_default_executor_when_cli_missing(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    rendered = tmp_path / "rendered.yaml"
    template.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")
    rendered.write_text("kind: l2_workflow_template\nphases: []\n", encoding="utf-8")

    config_dir = tmp_path / ".lee"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("executor: qwen_chat\n", encoding="utf-8")

    captured_create_payload = []

    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.main": {
                    "path": str(template),
                    "required_params": [],
                }
            }
        },
    )
    monkeypatch.setattr(run_module, "_render_workflow_template", lambda *_a, **_k: rendered)
    monkeypatch.setattr(run_module, "_list_conflicting_workflows", lambda *_a, **_k: [])
    monkeypatch.setattr(
        run_module,
        "_run_until_settled_with_gates",
        lambda *_a, **_k: {"status": "running", "completed_steps": 0, "blocked_at": None},
    )
    monkeypatch.setattr(run_module, "_print_summary", lambda *_a, **_k: None)

    def fake_pm_workflow(action: str, **kwargs):
        if action == "create":
            captured_create_payload.append(kwargs)
            return {"workflow_id": "wf_department_demo_004"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.main", "--project-dir", str(tmp_path), "--skip-plan"],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["executor_override"] == "qwen_chat"
    assert create_data["executor_selection_source"] == "file_config"


def test_select_existing_workflow_action_uses_noninteractive_stdin_command(monkeypatch) -> None:
    class _FakeStdin(io.StringIO):
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(run_module.click, "get_text_stream", lambda _name: _FakeStdin("restart\n"))

    action, workflow_id = run_module._select_existing_workflow_action(
        existing=[
            {
                "id": "wf_department_old",
                "status": "running",
                "current_step": None,
                "created_at": "2026-03-12T19:00:00",
                "concurrency_scope": "project:E:/ai/LEE:workflow:product.main",
            }
        ],
        scope_info=run_module.ConcurrencyScopeInfo(
            workflow_key="product.main",
            concurrency_scope="project:E:/ai/LEE:workflow:product.main",
            concurrency_key="product.main::project:E:/ai/LEE:workflow:product.main",
            scope_source="fallback:project+workflow_key",
        ),
    )

    assert action == "restart"
    assert workflow_id == "wf_department_old"


def test_select_existing_workflow_action_defaults_to_continue_in_noninteractive_mode(monkeypatch) -> None:
    class _FakeStdin(io.StringIO):
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(run_module.click, "get_text_stream", lambda _name: _FakeStdin(""))

    action, workflow_id = run_module._select_existing_workflow_action(
        existing=[
            {
                "id": "wf_department_old",
                "status": "running",
                "current_step": None,
                "created_at": "2026-03-12T19:00:00",
                "concurrency_scope": "project:E:/ai/LEE:workflow:product.main",
            }
        ],
        scope_info=run_module.ConcurrencyScopeInfo(
            workflow_key="product.main",
            concurrency_scope="project:E:/ai/LEE:workflow:product.main",
            concurrency_key="product.main::project:E:/ai/LEE:workflow:product.main",
            scope_source="fallback:project+workflow_key",
        ),
    )

    assert action == "continue"
    assert workflow_id == "wf_department_old"


def test_select_existing_workflow_action_requires_explicit_choice_for_new_run_in_noninteractive_mode(
    monkeypatch,
) -> None:
    class _FakeStdin(io.StringIO):
        def isatty(self) -> bool:
            return False

    monkeypatch.setattr(run_module.click, "get_text_stream", lambda _name: _FakeStdin(""))

    with pytest.raises(run_module.click.ClickException, match="显式新运行参数"):
        run_module._select_existing_workflow_action(
            existing=[
                {
                    "id": "wf_department_old",
                    "status": "running",
                    "current_step": None,
                    "created_at": "2026-03-12T19:00:00",
                    "concurrency_scope": "project:E:/ai/LEE:workflow:product.main",
                }
            ],
            scope_info=run_module.ConcurrencyScopeInfo(
                workflow_key="product.main",
                concurrency_scope="project:E:/ai/LEE:workflow:product.main",
                concurrency_key="product.main::project:E:/ai/LEE:workflow:product.main",
                scope_source="fallback:project+workflow_key",
            ),
            noninteractive_default_action=None,
        )
