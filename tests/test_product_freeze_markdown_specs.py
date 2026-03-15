from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List

from click.testing import CliRunner

from lee.cli.commands import run as run_module


def _write_ssot_spec(path: Path, *, artifact_id: str, ssot_type: str, status: str) -> None:
    path.write_text(
        "\n".join(
            [
                "---",
                f"id: {artifact_id}",
                f"ssot_type: {ssot_type}",
                f"title: Demo {artifact_id}",
                f"status: {status}",
                "version: v1",
                "---",
                "",
                f"# {artifact_id}",
            ]
        ),
        encoding="utf-8",
    )


def _patch_run_dependencies(
    monkeypatch,
    *,
    workflow_key: str,
    required_params: list[str],
    template: Path,
    rendered: Path,
    captured_create_payload: List[Dict[str, Any]],
) -> None:
    monkeypatch.setattr(
        run_module,
        "_load_registry",
        lambda: {
            "workflows": {
                workflow_key: {
                    "path": str(template),
                    "load_spec_as_params": True,
                    "required_params": required_params,
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
            return {"workflow_id": "wf_product_input_001"}
        raise AssertionError(f"unexpected pm_workflow action: {action}")

    monkeypatch.setattr(run_module, "pm_workflow", fake_pm_workflow)


def test_run_accepts_frozen_src_markdown_spec(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    src_spec = tmp_path / "SRC-123__demo.md"
    _write_ssot_spec(src_spec, artifact_id="SRC-123", ssot_type="src", status="frozen")

    captured_create_payload: List[Dict[str, Any]] = []
    _patch_run_dependencies(
        monkeypatch,
        workflow_key="product.src-to-epic",
        required_params=["source_freeze"],
        template=template,
        rendered=rendered,
        captured_create_payload=captured_create_payload,
    )

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.src-to-epic", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(src_spec)],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["params"]["source_freeze"] == {
        "artifact_id": "SRC-123",
        "path": str(src_spec.resolve()),
    }
    assert create_data["params"]["source_freeze_ref"] == {
        "artifact_id": "SRC-123",
        "path": str(src_spec.resolve()),
    }
    assert create_data["concurrency_scope"] == "src:SRC-123"


def test_run_accepts_frozen_feat_markdown_spec(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    feat_spec = tmp_path / "FEAT-321__demo.md"
    _write_ssot_spec(feat_spec, artifact_id="FEAT-321", ssot_type="feat", status="frozen")

    captured_create_payload: List[Dict[str, Any]] = []
    _patch_run_dependencies(
        monkeypatch,
        workflow_key="product.feat-to-delivery-prep",
        required_params=["feat_freeze"],
        template=template,
        rendered=rendered,
        captured_create_payload=captured_create_payload,
    )

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.feat-to-delivery-prep", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(feat_spec)],
    )

    assert result.exit_code == 0, result.output
    create_data = captured_create_payload[0]["data"]
    assert create_data["params"]["feat_freeze"] == {
        "artifact_id": "FEAT-321",
        "path": str(feat_spec.resolve()),
    }
    assert create_data["params"]["feat_freeze_ref"] == {
        "artifact_id": "FEAT-321",
        "path": str(feat_spec.resolve()),
    }
    assert create_data["concurrency_scope"] == "feat:FEAT-321"


def test_run_rejects_non_frozen_src_markdown_spec(monkeypatch, tmp_path: Path) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")
    rendered = tmp_path / "rendered.yaml"
    rendered.write_text("kind: workflow\nid: x\nversion: '1.0'\n", encoding="utf-8")
    src_spec = tmp_path / "SRC-999__draft.md"
    _write_ssot_spec(src_spec, artifact_id="SRC-999", ssot_type="src", status="draft")

    captured_create_payload: List[Dict[str, Any]] = []
    _patch_run_dependencies(
        monkeypatch,
        workflow_key="product.src-to-epic",
        required_params=["source_freeze"],
        template=template,
        rendered=rendered,
        captured_create_payload=captured_create_payload,
    )

    runner = CliRunner()
    result = runner.invoke(
        run_module.run,
        ["product.src-to-epic", "--project-dir", str(tmp_path), "--skip-plan", "--spec", str(src_spec)],
    )

    assert result.exit_code != 0
    assert "is not frozen" in result.output
    assert captured_create_payload == []
