from pathlib import Path

from lee.orchestrator.execution.file_output_handler import FileOutputHandler


def test_resolve_path_treats_leading_slash_as_project_relative(tmp_path):
    handler = FileOutputHandler(project_root=str(tmp_path))

    resolved = handler._resolve_path("/reports/governance/demo.md", {})

    assert resolved == str((tmp_path / "reports" / "governance" / "demo.md").resolve())
