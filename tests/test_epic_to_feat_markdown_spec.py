from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from click.testing import CliRunner

from lee.cli.commands import run as run_module
from lee.cli.commands import workflow_entrypoints as entry_module
from lee.cli.main import _register_commands, cli


def _write_epic_spec(path: Path, *, artifact_id: str, status: str) -> None:
    path.write_text(
        "\n".join(
            [
                "---",
                f"id: {artifact_id}",
                "ssot_type: epic",
                "title: Demo EPIC",
                f"status: {status}",
                "version: v1",
                "---",
                "",
                "# Demo EPIC",
            ]
        ),
        encoding="utf-8",
    )


def _patch_run_dependencies(
    monkeypatch,
    *,
    template: Path,
    rendered: Path,
    captured_create_payload: List[Dict[str, Any]],
) -> None:
    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                "product.epic-to-feat": {
                    "path": str(template),
                    "load_spec_as_params": True,
                    "required_params": ["epic_freeze"],
                }
            }
        },
    )
    monkeypatch.setattr(
        entry_module,
        "load_workflow_registry",
        lambda: {"workflows": {"product.epic-to-feat": {}}},
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
            return {"workflow_id": "wf_epic_to_feat_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)


def test_run_accepts_frozen_epic_markdown_spec(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    epic_spec = tmp_path / "EPIC-123__demo.md"
    _write_epic_spec(epic_spec, artifact_id="EPIC-123", status="frozen")

    captured_create_payload: List[Dict[str, Any]] = []
    _patch_run_dependencies(
        monkeypatch,
        template=template,
        rendered=rendered,
        captured_create_payload=captured_create_payload,
    )

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.epic-to-feat", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(epic_spec)],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["concurrency_scope"] == "epic:EPIC-123"
    assert create_data["scope_source"] == "params.epic_freeze.artifact_id"
    assert create_data["params"]["epic_freeze"] == {
        "artifact_id": "EPIC-123",
        "path": str(epic_spec.resolve()),
    }
    assert create_data["params"]["epic_freeze_ref"] == {
        "artifact_id": "EPIC-123",
        "path": str(epic_spec.resolve()),
    }


def test_feat_new_accepts_frozen_epic_markdown_spec(monkeypatch, tmp_path: Path) -> None:
    _register_commands()
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    epic_spec = tmp_path / "EPIC-SRC-046-020__demo.md"
    _write_epic_spec(epic_spec, artifact_id="EPIC-SRC-046-020", status="frozen")

    captured_create_payload: List[Dict[str, Any]] = []
    _patch_run_dependencies(
        monkeypatch,
        template=template,
        rendered=rendered,
        captured_create_payload=captured_create_payload,
    )

    runner = CliRunner()
    result = runner.invoke(
        cli,
        ["feat", "new", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(epic_spec)],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["params"]["epic_freeze"]["artifact_id"] == "EPIC-SRC-046-020"
    assert create_data["params"]["epic_freeze"]["path"] == str(epic_spec.resolve())


def test_run_rejects_non_frozen_epic_markdown_spec(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    epic_spec = tmp_path / "EPIC-999__draft.md"
    _write_epic_spec(epic_spec, artifact_id="EPIC-999", status="draft")

    captured_create_payload: List[Dict[str, Any]] = []
    _patch_run_dependencies(
        monkeypatch,
        template=template,
        rendered=rendered,
        captured_create_payload=captured_create_payload,
    )

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.epic-to-feat", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(epic_spec)],
    )

    assert result.exit_code != 0
    assert "is not frozen" in result.output
    assert captured_create_payload == []
