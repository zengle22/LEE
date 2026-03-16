from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import ClaudeCodeRunner


def test_validate_declared_output_files_ignores_symbol_outputs(tmp_path):
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(type="symbol", path="raw_source_input", required=True),
            SimpleNamespace(type="file", path="output/result.json", required=False),
        ]
    )

    error = ClaudeCodeRunner._validate_declared_output_files(
        step=step,
        project_root=str(tmp_path),
    )

    assert error is None
