import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, patch

from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor


def test_claude_code_executor_defaults_to_sonnet_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("CLAUDE_CODE_MODEL", raising=False)
    executor = ClaudeCodeExecutor()
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)

    captured_cmd = []

    def mock_subprocess(cmd, *_args, **_kwargs):
        captured_cmd.extend(cmd)
        return '{"status":"success","changed_files":[],"commands_run":[],"test_results":{},"error":null}'

    with patch.object(executor, "_run_subprocess", side_effect=mock_subprocess):
        with patch.object(
            executor,
            "_collect_diff_summary",
            new=AsyncMock(return_value={"files_changed": 0, "lines_added": 0, "lines_deleted": 0}),
        ):
            result = asyncio.run(
                executor.execute(
                    {
                        "goal": "test",
                        "workspace": str(workspace),
                        "timeout_seconds": 5,
                        "timeout_retries": 0,
                        "evidence_base": str(tmp_path / "ev-default"),
                    }
                )
            )

    assert result["status"] == "success"
    assert "--model" in captured_cmd
    model_idx = captured_cmd.index("--model")
    assert captured_cmd[model_idx + 1] == "claude-sonnet-4-6"


def test_claude_code_executor_allows_model_override(tmp_path: Path) -> None:
    executor = ClaudeCodeExecutor()
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)

    captured_cmd = []

    def mock_subprocess(cmd, *_args, **_kwargs):
        captured_cmd.extend(cmd)
        return '{"status":"success","changed_files":[],"commands_run":[],"test_results":{},"error":null}'

    override_model = "claude-opus-4-20250514"

    with patch.object(executor, "_run_subprocess", side_effect=mock_subprocess):
        with patch.object(
            executor,
            "_collect_diff_summary",
            new=AsyncMock(return_value={"files_changed": 0, "lines_added": 0, "lines_deleted": 0}),
        ):
            result = asyncio.run(
                executor.execute(
                    {
                        "goal": "test",
                        "workspace": str(workspace),
                        "model": override_model,
                        "timeout_seconds": 5,
                        "timeout_retries": 0,
                        "evidence_base": str(tmp_path / "ev-override"),
                    }
                )
            )

    assert result["status"] == "success"
    assert "--model" in captured_cmd
    model_idx = captured_cmd.index("--model")
    assert captured_cmd[model_idx + 1] == override_model
