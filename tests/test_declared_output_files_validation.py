from pathlib import Path
from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner


def test_validate_declared_output_files_passes_when_required_paths_exist(tmp_path: Path) -> None:
    output_path = tmp_path / "spec" / "tech" / "FEAT-001" / "decision_refs.yaml"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("ok: true\n", encoding="utf-8")

    step = SimpleNamespace(
        outputs=[
            {
                "path": "spec/tech/FEAT-001/decision_refs.yaml",
                "type": "file",
                "required": True,
            }
        ]
    )

    error = ClaudeCodeRunner._validate_declared_output_files(
        step=step,
        project_root=str(tmp_path),
    )

    assert error is None


def test_validate_declared_output_files_fails_when_required_path_missing(tmp_path: Path) -> None:
    step = SimpleNamespace(
        outputs=[
            {
                "path": "spec/tech/FEAT-001/decision_refs.yaml",
                "type": "file",
                "required": True,
            }
        ]
    )

    error = ClaudeCodeRunner._validate_declared_output_files(
        step=step,
        project_root=str(tmp_path),
    )

    assert error is not None
    assert "Missing declared output file" in error
    assert "decision_refs.yaml" in error


def test_validate_declared_output_files_ignores_optional_outputs(tmp_path: Path) -> None:
    step = SimpleNamespace(
        outputs=[
            {
                "path": "spec/tech/FEAT-001/optional.md",
                "type": "file",
                "required": False,
            }
        ]
    )

    error = ClaudeCodeRunner._validate_declared_output_files(
        step=step,
        project_root=str(tmp_path),
    )

    assert error is None
