"""
Codex Executor 单元测试
"""

import asyncio
import pytest
from pathlib import Path
from lee.orchestrator.execution.codex_executor import CodexExecutor


class TestCodexExecutor:
    """Codex 执行器测试套件"""

    def setup_method(self):
        """测试前设置"""
        self.executor = CodexExecutor()

    def test_initialization(self):
        """测试初始化"""
        assert self.executor._codex_binary == "codex"
        assert self.executor._model == "gpt-4o"
        assert self.executor.DEFAULT_SANDBOX_MODE == "workspace-write"

    def test_validate_input_missing_goal(self):
        """测试输入验证 - 缺少 goal"""
        result = self.executor._validate_input({"workspace": "/tmp"})
        assert result == "Missing required field: goal"

    def test_validate_input_missing_workspace(self):
        """测试输入验证 - 缺少 workspace"""
        result = self.executor._validate_input({"goal": "test"})
        assert result == "Missing required field: workspace"

    def test_validate_input_invalid_workspace(self):
        """测试输入验证 - 无效的 workspace"""
        result = self.executor._validate_input({
            "goal": "test",
            "workspace": "/nonexistent/path/xyz123"
        })
        assert "does not exist" in result

    def test_parse_jsonl_output(self):
        """测试 JSONL 输出解析"""
        sample_jsonl = '''
{"type":"thread.started","thread_id":"test-thread-123"}
{"type":"turn.started"}
{"type":"item.completed","item":{"type":"agent_message","text":"Hello!"}}
{"type":"item.completed","item":{"type":"tool_use","name":"shell","input":{"command":"ls"}}}
{"type":"turn.completed","usage":{"input_tokens":100,"cached_input_tokens":0,"output_tokens":50}}
'''
        parsed = self.executor._parse_codex_output(sample_jsonl)

        assert parsed["thread_id"] == "test-thread-123"
        assert parsed["result_text"] == "Hello!"
        assert len(parsed["commands_run"]) == 1
        assert parsed["commands_run"][0]["cmd"] == "ls"
        assert parsed["tokens_used"] == 150

    def test_parse_jsonl_with_file_operations(self):
        """测试解析文件操作"""
        sample_jsonl = '''
{"type":"item.completed","item":{"type":"tool_use","name":"write_file","input":{"path":"/tmp/test.py"}}}
{"type":"item.completed","item":{"type":"tool_use","name":"edit_file","input":{"path":"/tmp/test.py"}}}
'''
        parsed = self.executor._parse_codex_output(sample_jsonl)

        assert len(parsed["changed_files"]) == 2
        assert "/tmp/test.py" in parsed["changed_files"]

    def test_parse_jsonl_with_test_results(self):
        """测试解析测试结果"""
        sample_jsonl = '''
{"type":"item.completed","item":{"type":"agent_message","text":"Tests: 5 passed, 1 failed"}}
'''
        parsed = self.executor._parse_codex_output(sample_jsonl)

        assert parsed["test_results"]["passed"] == 5
        assert parsed["test_results"]["failed"] == 1

    def test_calculate_cost(self):
        """测试成本计算"""
        # gpt-4o: $0.005/1K input, $0.015/1K output
        cost = self.executor._calculate_cost("gpt-4o", 1000, 500)
        assert abs(cost - 0.0125) < 0.0001  # (1000 * 0.005 + 500 * 0.015) / 1000

        cost = self.executor._calculate_cost("gpt-4o", 0, 0)
        assert cost == 0

    def test_coerce_positive_int(self):
        """测试正整数转换"""
        assert self.executor._coerce_positive_int(None, 5) == 5
        assert self.executor._coerce_positive_int(10, 5) == 10
        assert self.executor._coerce_positive_int(-1, 5) == 5
        assert self.executor._coerce_positive_int("abc", 5) == 5

    def test_coerce_non_negative_int(self):
        """测试非负整数转换"""
        assert self.executor._coerce_non_negative_int(None, 5) == 5
        assert self.executor._coerce_non_negative_int(10, 5) == 10
        assert self.executor._coerce_non_negative_int(0, 5) == 0
        assert self.executor._coerce_non_negative_int(-1, 5) == 5

    def test_build_system_prompt(self):
        """测试系统 prompt 构建"""
        prompt = self.executor._build_system_prompt(
            goal="Write a function",
            workspace="/tmp/test",
            allowed_commands=["ls", "cat"],
            write_scope=[],
            max_iterations=3,
            max_bash_calls=10,
            stop_conditions={},
            system_prompt_extra="",
        )

        assert "Governance Constraints" in prompt
        assert "Working directory: /tmp/test" in prompt
        assert "Maximum iterations: 3" in prompt
        assert "Bash tool call limit: 10" in prompt

    def test_build_user_prompt(self):
        """测试用户 prompt 构建"""
        prompt = self.executor._build_user_prompt(
            goal="Write code",
            context_files=["file1.py", "file2.py"],
        )

        assert "Task Goal" in prompt
        assert "Write code" in prompt
        assert "file1.py" in prompt
        assert "file2.py" in prompt

    def test_build_retry_prompt(self):
        """测试重试 prompt 构建"""
        original = "Original task here"
        retry = self.executor._build_retry_prompt(1, 3, original)

        assert "Retry attempt 2/3" in retry
        assert "Continue the previous session" in retry
        assert original in retry

    def test_determine_status_success(self):
        """测试状态判定 - 成功"""
        parsed = {"error": None, "test_results": {"failed": 0}}
        status = self.executor._determine_status(parsed, {})
        assert status == "success"

    def test_determine_status_fail(self):
        """测试状态判定 - 失败"""
        parsed = {"error": "Something went wrong", "test_results": {}}
        status = self.executor._determine_status(parsed, {})
        assert status == "fail"

    def test_determine_status_test_fail(self):
        """测试状态判定 - 测试失败"""
        parsed = {"error": None, "test_results": {"failed": 5}}
        status = self.executor._determine_status(parsed, {})
        assert status == "fail"

    def test_determine_status_needs_human(self):
        """测试状态判定 - 需要人工介入"""
        parsed = {"error": "Policy violation detected", "test_results": {}}
        status = self.executor._determine_status(
            parsed, {"on_policy_violation": "stop_needs_human"}
        )
        assert status == "needs_human"

    def test_build_error_result(self):
        """测试错误结果构建"""
        result = self.executor._build_error_result("Test error")

        assert result["status"] == "failed"
        assert result["error"] == "Test error"
        assert result["iterations_used"] == 0
        assert result["changed_files"] == []

    def test_build_timeout_result(self):
        """测试超时结果构建"""
        result = self.executor._build_timeout_result("Timeout after 60s")

        assert result["status"] == "timeout"
        assert "Timeout" in result["error"]

    @pytest.mark.asyncio
    async def test_collect_diff_summary(self):
        """测试 diff 摘要收集"""
        summary = await self.executor._collect_diff_summary(
            "/private/var/folders/mc/9mqwl12d4h133r98k7prgr140000gn/T/vibe-kanban/worktrees/8952-claude-code-excu/lee"
        )

        assert "files_changed" in summary
        assert "lines_added" in summary
        assert "lines_deleted" in summary


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
