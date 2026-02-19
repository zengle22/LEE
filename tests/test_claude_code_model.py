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


def test_invoke_claude_passes_silence_timeouts(tmp_path: Path) -> None:
    executor = ClaudeCodeExecutor()
    workspace = tmp_path / "ws"
    workspace.mkdir(parents=True, exist_ok=True)

    captured = {}

    def mock_subprocess(
        cmd,
        cwd,
        timeout,
        stdin_text="",
        live_log_path="",
        debug_file_path="",
        cancel_event=None,
        silence_timeout_seconds=0,
        silence_grace_seconds=0,
        max_bash_calls=0,
    ):
        captured["cmd"] = list(cmd)
        captured["cwd"] = cwd
        captured["timeout"] = timeout
        captured["silence_timeout_seconds"] = silence_timeout_seconds
        captured["silence_grace_seconds"] = silence_grace_seconds
        captured["max_bash_calls"] = max_bash_calls
        return '{"status":"success","changed_files":[],"commands_run":[],"test_results":{},"error":null}'

    with patch.object(executor, "_run_subprocess", side_effect=mock_subprocess):
        output = asyncio.run(
            executor._invoke_claude(
                prompt="test prompt",
                system_prompt="test system",
                workspace=str(workspace),
                allowed_commands=["ls"],
                timeout_seconds=9,
                max_iterations=1,
                timeout_retries=0,
                retry_backoff_seconds=0,
                silence_timeout_seconds=17,
                silence_grace_seconds=3,
            )
        )

    assert output
    assert captured["cwd"] == str(workspace)
    assert captured["timeout"] == 9
    assert captured["silence_timeout_seconds"] == 17
    assert captured["silence_grace_seconds"] == 3
    assert captured["max_bash_calls"] == 60
