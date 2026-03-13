from pathlib import Path

from lee.orchestrator.execution.artifacts.ssot_files import lint_ssot_workflow_provenance


def test_lint_ssot_workflow_provenance_requires_workflow_instance_id(tmp_path: Path):
    target = tmp_path / "spec" / "requirements" / "features" / "FEAT-001__demo.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\n"
        "id: FEAT-001\n"
        "ssot_type: feat\n"
        "title: Demo\n"
        "status: frozen\n"
        "version: v1\n"
        "---\n\n"
        "# Demo\n",
        encoding="utf-8",
    )

    errors = lint_ssot_workflow_provenance(tmp_path, [target])

    assert len(errors) == 1
    assert "missing workflow_instance_id" in errors[0]


def test_lint_ssot_workflow_provenance_accepts_governed_file_with_workflow_instance_id(tmp_path: Path):
    target = tmp_path / "spec" / "requirements" / "features" / "FEAT-001__demo.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(
        "---\n"
        "id: FEAT-001\n"
        "ssot_type: feat\n"
        "title: Demo\n"
        "status: frozen\n"
        "version: v1\n"
        "workflow_instance_id: wf_task_123\n"
        "---\n\n"
        "# Demo\n",
        encoding="utf-8",
    )

    errors = lint_ssot_workflow_provenance(tmp_path, [target])

    assert errors == []
