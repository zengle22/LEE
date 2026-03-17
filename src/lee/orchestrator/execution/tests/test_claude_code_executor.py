"""
Claude Code executor unit tests.
"""

import json
import os

import pytest

from lee.orchestrator.execution.claude_code_result_resilience import (
    should_retry_empty_tool_use_result,
)
from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor
from lee.orchestrator.execution.output_seed import seed_declared_output_files


class TestNestedSessionDetection:
    """Tests for nested Claude Code session detection (BUG-LEE-EXECUTOR-001)."""

    @pytest.mark.asyncio
    async def test_invoke_claude_raises_when_in_nested_session(self, monkeypatch):
        """Test that _invoke_claude raises RuntimeError when CLAUDECODE env var is set."""
        monkeypatch.setenv("CLAUDECODE", "1")
        executor = ClaudeCodeExecutor()

        with pytest.raises(RuntimeError) as exc_info:
            await executor._invoke_claude(
                prompt="test",
                system_prompt="test",
                workspace="/tmp",
                allowed_commands=["cat"],
                timeout_seconds=30,
                max_iterations=1,
            )

        assert "Cannot launch nested Claude Code session" in str(exc_info.value)
        assert "already running inside a Claude Code session" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_invoke_claude_allows_execution_when_not_nested(self, monkeypatch, tmp_path):
        """Test that _invoke_claude works normally when CLAUDECODE env var is not set."""
        monkeypatch.delenv("CLAUDECODE", raising=False)
        executor = ClaudeCodeExecutor()

        # Mock subprocess to avoid actually calling claude CLI
        def mock_run_subprocess(*args, **kwargs):
            return '{"type":"result","subtype":"success","is_error":false,"num_turns":1,"result":"test"}'

        monkeypatch.setattr(executor, "_run_subprocess", mock_run_subprocess)

        # Should not raise
        result = await executor._invoke_claude(
            prompt="test",
            system_prompt="test",
            workspace=str(tmp_path),
            allowed_commands=["cat"],
            timeout_seconds=30,
            max_iterations=1,
        )

        assert result is not None


class TestClaudeCodeExecutor:
    def setup_method(self):
        self.executor = ClaudeCodeExecutor()

    def test_parse_result_object_preserves_stop_reason(self):
        parsed = self.executor._parse_result_object(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "num_turns": 2,
                "result": "",
                "stop_reason": "tool_use",
                "session_id": "test-session",
            },
            raw_output='{"type":"result"}',
        )

        assert parsed["stop_reason"] == "tool_use"
        assert parsed["result_text"] == ""

    def test_determine_status_fails_on_empty_tool_use_result(self):
        status = self.executor._determine_status(
            {
                "error": None,
                "test_results": {},
                "stop_reason": "tool_use",
                "result_text": "",
            },
            {},
        )

        assert status == "fail"

    def test_empty_tool_use_result_is_retryable(self):
        assert should_retry_empty_tool_use_result(
            {
                "error": None,
                "stop_reason": "tool_use",
                "result_text": "",
                "changed_files": [],
                "commands_run": [],
            }
        )

    def test_determine_status_keeps_success_for_completed_turn(self):
        status = self.executor._determine_status(
            {
                "error": None,
                "test_results": {"failed": 0},
                "stop_reason": "end_turn",
                "result_text": '{"done": true}',
            },
            {},
        )

        assert status == "success"

    def test_default_model_uses_supported_claude_sonnet_version(self):
        previous = os.environ.pop("CLAUDE_CODE_MODEL", None)
        try:
            executor = ClaudeCodeExecutor()
            assert executor._model == "sonnet"
        finally:
            if previous is not None:
                os.environ["CLAUDE_CODE_MODEL"] = previous

    def test_legacy_env_model_alias_normalizes_to_supported_sonnet(self):
        previous = os.environ.get("CLAUDE_CODE_MODEL")
        try:
            os.environ["CLAUDE_CODE_MODEL"] = "claude-sonnet-4-6"
            executor = ClaudeCodeExecutor()
            assert executor._model == "sonnet"
        finally:
            if previous is None:
                os.environ.pop("CLAUDE_CODE_MODEL", None)
            else:
                os.environ["CLAUDE_CODE_MODEL"] = previous

    def test_build_system_prompt_marks_read_only_mode(self):
        prompt = self.executor._build_system_prompt(
            goal="validate requirement chain",
            workspace="E:\\ai\\LEE",
            allowed_commands=["cat", "ls"],
            write_scope=[],
            read_only=True,
            forbidden_read_paths=["output/"],
            max_iterations=3,
            max_bash_calls=10,
            stop_conditions={},
            system_prompt_extra="",
        )

        assert "只读模式" in prompt
        assert "禁止使用 Write/Edit/MultiEdit" in prompt

    def test_build_allowed_tools_uses_read_only_toolset(self):
        allowed_tools = self.executor._build_allowed_tools(
            allowed_commands=["cat"],
            read_only=True,
        )

        assert allowed_tools == ["Read", "Bash"]

    def test_build_allowed_tools_keeps_write_tools_when_not_read_only(self):
        allowed_tools = self.executor._build_allowed_tools(
            allowed_commands=["cat"],
            read_only=False,
        )

        assert allowed_tools == ["Read", "Write", "Edit", "MultiEdit", "Bash"]

    def test_build_system_prompt_uses_structured_output_only_mode(self):
        prompt = self.executor._build_system_prompt(
            goal="repair structured payload",
            workspace="E:\\ai\\LEE",
            allowed_commands=[],
            write_scope=[],
            read_only=True,
            forbidden_read_paths=[],
            max_iterations=1,
            max_bash_calls=0,
            stop_conditions={},
            system_prompt_extra="",
            structured_output_only=True,
        )

        assert "只允许返回最终 machine-readable JSON 对象本体" in prompt
        assert '"status": "success 或 fail"' not in prompt

    def test_build_user_prompt_requires_read_before_writing_outputs(self):
        prompt = self.executor._build_user_prompt(
            goal="write tech package",
            context_files=["spec/feat.md"],
            output_files=["output/tech-packages/FEAT-1/design_analysis.md"],
        )

        assert "第一次写入前，必须先用 Read 读取这些文件" in prompt
        assert "output/tech-packages/FEAT-1/design_analysis.md" in prompt


def test_seed_declared_output_files_touches_missing_targets(tmp_path):
    seeded = seed_declared_output_files(
        workspace=str(tmp_path),
        output_files=["output/tech-packages/FEAT-1/design_analysis.md"],
    )

    assert seeded == ["output/tech-packages/FEAT-1/design_analysis.md"]
    assert (tmp_path / "output" / "tech-packages" / "FEAT-1" / "design_analysis.md").exists()


@pytest.mark.asyncio
async def test_execute_retries_empty_tool_use_result_once(monkeypatch, tmp_path):
    executor = ClaudeCodeExecutor()
    attempts = {"count": 0}

    async def fake_invoke(**_: object) -> str:
        attempts["count"] += 1
        if attempts["count"] == 1:
            return json.dumps(
                {
                    "type": "result",
                    "subtype": "success",
                    "is_error": False,
                    "num_turns": 1,
                    "result": "",
                    "stop_reason": "tool_use",
                    "session_id": "11111111-1111-1111-1111-111111111111",
                }
            )
        return json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "num_turns": 1,
                "result": "```json\n{\"status\":\"success\",\"changed_files\":[],\"commands_run\":[],\"test_results\":{\"passed\":0,\"failed\":0},\"error\":null}\n```",
                "stop_reason": "end_turn",
                "session_id": "11111111-1111-1111-1111-111111111111",
            }
        )

    async def fake_diff(_: str) -> dict:
        return {"files_changed": 0, "lines_added": 0, "lines_deleted": 0}

    monkeypatch.setattr(executor, "_invoke_claude", fake_invoke)
    monkeypatch.setattr(executor, "_collect_diff_summary", fake_diff)

    result = await executor.execute(
        {
            "goal": "Return a structured payload.",
            "workspace": str(tmp_path),
            "empty_result_retries": 1,
            "evidence_base": str(tmp_path / "evidence"),
        }
    )

    assert result["status"] == "success"
    assert result["empty_result_retries"] == 1
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_execute_fails_after_empty_tool_use_retry_exhausted(monkeypatch, tmp_path):
    executor = ClaudeCodeExecutor()
    attempts = {"count": 0}

    async def fake_invoke(**_: object) -> str:
        attempts["count"] += 1
        return json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "num_turns": 1,
                "result": "",
                "stop_reason": "tool_use",
                "session_id": "22222222-2222-2222-2222-222222222222",
            }
        )

    async def fake_diff(_: str) -> dict:
        return {"files_changed": 0, "lines_added": 0, "lines_deleted": 0}

    monkeypatch.setattr(executor, "_invoke_claude", fake_invoke)
    monkeypatch.setattr(executor, "_collect_diff_summary", fake_diff)

    result = await executor.execute(
        {
            "goal": "Return a structured payload.",
            "workspace": str(tmp_path),
            "empty_result_retries": 1,
            "evidence_base": str(tmp_path / "evidence"),
        }
    )

    assert result["status"] == "fail"
    assert result["empty_result_retries"] == 1
    assert attempts["count"] == 2


@pytest.mark.asyncio
async def test_execute_seeds_declared_output_files_into_prompt(monkeypatch, tmp_path):
    executor = ClaudeCodeExecutor()
    captured = {}

    async def fake_invoke(**kwargs: object) -> str:
        captured["prompt"] = kwargs["prompt"]
        return json.dumps(
            {
                "type": "result",
                "subtype": "success",
                "is_error": False,
                "num_turns": 1,
                "result": "```json\n{\"status\":\"success\",\"changed_files\":[],\"commands_run\":[],\"test_results\":{\"passed\":0,\"failed\":0},\"error\":null}\n```",
                "stop_reason": "end_turn",
                "session_id": "33333333-3333-3333-3333-333333333333",
            }
        )

    async def fake_diff(_: str) -> dict:
        return {"files_changed": 0, "lines_added": 0, "lines_deleted": 0}

    monkeypatch.setattr(executor, "_invoke_claude", fake_invoke)
    monkeypatch.setattr(executor, "_collect_diff_summary", fake_diff)

    result = await executor.execute(
        {
            "goal": "Write the declared outputs.",
            "workspace": str(tmp_path),
            "declared_output_files": ["output/tech-packages/FEAT-1/design_analysis.md"],
            "evidence_base": str(tmp_path / "evidence"),
        }
    )

    assert result["status"] == "success"
    assert "output/tech-packages/FEAT-1/design_analysis.md" in captured["prompt"]
    assert (tmp_path / "output" / "tech-packages" / "FEAT-1" / "design_analysis.md").exists()
