"""
Claude Code executor unit tests.
"""

from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor


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
