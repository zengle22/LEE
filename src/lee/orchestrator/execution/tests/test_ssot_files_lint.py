import shutil
import tempfile
from pathlib import Path

from lee.orchestrator.execution.artifacts.ssot_files import lint_ssot_front_matter


def _write_ssot(path: Path, artifact_id: str, title: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(
            [
                "---",
                f"id: {artifact_id}",
                "ssot_type: task",
                f"title: {title}",
                "status: active",
                "version: v1",
                "---",
                "",
                f"# {title}",
                "",
            ]
        ),
        encoding="utf-8",
    )


def test_lint_ssot_front_matter_detects_duplicate_ids():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        _write_ssot(
            temp_dir / "spec" / "tasks" / "FEAT-001" / "TASK-FEAT-001-001__first.md",
            "TASK-FEAT-001-001",
            "First",
        )
        _write_ssot(
            temp_dir / "spec" / "tasks" / "FEAT-001" / "TASK-FEAT-001-001__second.md",
            "TASK-FEAT-001-001",
            "Second",
        )

        errors = lint_ssot_front_matter(temp_dir)

        assert any("duplicate SSOT id TASK-FEAT-001-001" in err for err in errors), errors
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_lint_ssot_front_matter_passes_unique_ids():
    temp_dir = Path(tempfile.mkdtemp())
    try:
        _write_ssot(
            temp_dir / "spec" / "tasks" / "FEAT-001" / "TASK-FEAT-001-001__first.md",
            "TASK-FEAT-001-001",
            "First",
        )
        _write_ssot(
            temp_dir / "spec" / "tasks" / "FEAT-001" / "TASK-FEAT-001-002__second.md",
            "TASK-FEAT-001-002",
            "Second",
        )

        errors = lint_ssot_front_matter(temp_dir)

        assert errors == []
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
