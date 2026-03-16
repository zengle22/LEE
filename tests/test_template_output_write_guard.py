from pathlib import Path
from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner


def test_declared_output_validation_blocks_template_directory_write(tmp_path: Path) -> None:
    step = SimpleNamespace(
        outputs=[
            {
                "path": "spec-global/departments/dev/workflows/templates/decision_refs",
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
    assert "Forbidden template-directory write" in error


def test_detect_forbidden_template_write_paths_blocks_templates_dir(tmp_path: Path) -> None:
    blocked = ClaudeCodeRunner._detect_forbidden_template_write_paths(
        paths=["spec-global/departments/dev/workflows/templates/design_analysis"],
        project_root=str(tmp_path),
    )

    assert blocked is not None
    assert "spec-global" in blocked


def test_detect_forbidden_template_write_paths_allows_output_dir(tmp_path: Path) -> None:
    blocked = ClaudeCodeRunner._detect_forbidden_template_write_paths(
        paths=["output/tech-packages/FEAT-SRC-041-005/design_analysis.md"],
        project_root=str(tmp_path),
    )

    assert blocked is None
