"""
Claude Code Executor 单元测试

测试用例：
1. 输入验证（缺少必填字段）
2. 超时处理
3. 输出解析
4. 迭代上限
5. Evidence bundle 写入
6. ExecutorFactory 注册
7. diff 摘要收集
8. 停止条件判定
"""

from __future__ import annotations

import asyncio
import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from lee.orchestrator.execution.claude_code_executor import (
    BashToolLimitExceeded,
    ClaudeCodeExecutor,
    register_claude_code_executor,
)
from lee.orchestrator.execution.executors import ExecutorFactory


# ========================================================================
# Fixtures
# ========================================================================

@pytest.fixture
def executor():
    """创建 ClaudeCodeExecutor 实例"""
    return ClaudeCodeExecutor()


@pytest.fixture
def workspace(tmp_path):
    """创建临时工作空间"""
    ws = tmp_path / "test_project"
    ws.mkdir()
    (ws / "main.py").write_text("print('hello')")
    return ws


@pytest.fixture
def base_input(workspace):
    """基础输入数据"""
    return {
        "goal": "实现用户登录功能",
        "workspace": str(workspace),
        "allowed_commands": ["pytest", "ruff"],
        "max_iterations": 3,
        "timeout_seconds": 60,
    }


# ========================================================================
# 1. 输入验证测试
# ========================================================================

class TestInputValidation:
    """测试输入数据验证"""

    @pytest.mark.asyncio
    async def test_missing_goal(self, executor, workspace):
        """缺少 goal 字段应返回 failed"""
        result = await executor.execute({
            "workspace": str(workspace),
        })
        assert result["status"] == "failed"
        assert "goal" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_missing_workspace(self, executor):
        """缺少 workspace 字段应返回 failed"""
        result = await executor.execute({
            "goal": "实现功能",
        })
        assert result["status"] == "failed"
        assert "workspace" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_workspace_not_exists(self, executor):
        """workspace 不存在应返回 failed"""
        result = await executor.execute({
            "goal": "实现功能",
            "workspace": "/nonexistent/path/xyz",
        })
        assert result["status"] == "failed"
        assert "not exist" in result["error"].lower() or "does not exist" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_workspace_is_file(self, executor, tmp_path):
        """workspace 是文件而非目录应返回 failed"""
        file_path = tmp_path / "not_a_dir.txt"
        file_path.write_text("hello")
        result = await executor.execute({
            "goal": "实现功能",
            "workspace": str(file_path),
        })
        assert result["status"] == "failed"
        assert "not a directory" in result["error"].lower()


# ========================================================================
# 2. 超时处理测试
# ========================================================================

class TestTimeoutHandling:
    """测试超时处理"""

    @pytest.mark.asyncio
    async def test_timeout_returns_timeout_status(self, executor, base_input):
        """subprocess 超时应返回 status=timeout"""
        with patch.object(executor, '_invoke_claude', side_effect=asyncio.TimeoutError()):
            result = await executor.execute(base_input)
            assert result["status"] == "timeout"
            assert "timed out" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout_recovers_written_step_workspace_files(self, executor, base_input, workspace):
        """超时时若 step workspace 已有产物，应回收 changed_files 并返回 success。"""
        step_workspace = workspace / ".workflow" / "workspace" / "wf-task-1" / "tech_design"
        step_workspace.mkdir(parents=True)
        artifact = step_workspace / "tech-architecture.yaml"
        artifact.write_text("architecture: ready\n", encoding="utf-8")

        recover_input = dict(base_input)
        recover_input["step_workspace"] = str(step_workspace)

        with patch.object(executor, "_invoke_claude", side_effect=asyncio.TimeoutError("stalled")):
            with patch.object(
                executor,
                "_collect_diff_summary",
                new=AsyncMock(return_value={"files_changed": 1, "lines_added": 1, "lines_deleted": 0}),
            ):
                result = await executor.execute(recover_input)

        assert result["status"] == "success"
        assert result["recovered_from_timeout"] is True
        assert any(
            path.replace("\\", "/") == ".workflow/workspace/wf-task-1/tech_design/tech-architecture.yaml"
            for path in result["changed_files"]
        )
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_timeout_without_step_workspace_artifacts_stays_timeout(self, executor, base_input, workspace):
        """超时且 step workspace 无文件时，仍应返回 timeout。"""
        empty_step_workspace = workspace / ".workflow" / "workspace" / "wf-task-2" / "tech_design"
        empty_step_workspace.mkdir(parents=True)

        recover_input = dict(base_input)
        recover_input["step_workspace"] = str(empty_step_workspace)

        with patch.object(executor, "_invoke_claude", side_effect=asyncio.TimeoutError("stalled")):
            result = await executor.execute(recover_input)

        assert result["status"] == "timeout"

    @pytest.mark.asyncio
    async def test_cli_not_found(self, executor, base_input):
        """claude CLI 不存在应返回 failed"""
        with patch.object(executor, '_invoke_claude', side_effect=FileNotFoundError()):
            result = await executor.execute(base_input)
            assert result["status"] == "failed"
            assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_invoke_claude_retries_on_timeout(self, executor, workspace):
        """_invoke_claude 超时后应按配置重试并最终成功"""
        attempts = {"count": 0}

        def flaky_run(*args, **kwargs):
            attempts["count"] += 1
            if attempts["count"] == 1:
                raise asyncio.TimeoutError("first timeout")
            return '{"status":"success"}'

        with patch.object(executor, "_run_subprocess", side_effect=flaky_run):
            output = await executor._invoke_claude(
                prompt="test",
                system_prompt="",
                workspace=str(workspace),
                allowed_commands=[],
                timeout_seconds=1,
                max_iterations=1,
                timeout_retries=1,
                retry_backoff_seconds=0,
            )

        assert output == '{"status":"success"}'
        assert attempts["count"] == 2

    @pytest.mark.asyncio
    async def test_invoke_claude_timeout_exhausted(self, executor, workspace):
        """_invoke_claude 超时达到上限后应抛出 TimeoutError"""
        with patch.object(executor, "_run_subprocess", side_effect=asyncio.TimeoutError()):
            with pytest.raises(asyncio.TimeoutError):
                await executor._invoke_claude(
                    prompt="test",
                    system_prompt="",
                    workspace=str(workspace),
                    allowed_commands=[],
                    timeout_seconds=1,
                    max_iterations=1,
                    timeout_retries=1,
                    retry_backoff_seconds=0,
                )

    @pytest.mark.asyncio
    async def test_invoke_claude_retry_uses_resume_session(self, executor, workspace):
        """重试时应复用同一会话，并通过 --resume 续跑。"""
        seen = []
        attempts = {"count": 0}

        def flaky_run(cmd, cwd, timeout, stdin_text="", *args):
            attempts["count"] += 1
            seen.append({"cmd": list(cmd), "stdin_text": stdin_text})
            if attempts["count"] == 1:
                raise asyncio.TimeoutError("first timeout")
            return '{"status":"success"}'

        with patch.object(executor, "_run_subprocess", side_effect=flaky_run):
            output = await executor._invoke_claude(
                prompt="test retry prompt",
                system_prompt="",
                workspace=str(workspace),
                allowed_commands=[],
                timeout_seconds=1,
                max_iterations=1,
                timeout_retries=1,
                retry_backoff_seconds=0,
            )

        assert output == '{"status":"success"}'
        assert attempts["count"] == 2
        first_cmd = seen[0]["cmd"]
        second_cmd = seen[1]["cmd"]
        assert "--session-id" in first_cmd
        assert "--resume" not in first_cmd
        assert "--resume" in second_cmd
        assert "--session-id" not in second_cmd
        first_session = first_cmd[first_cmd.index("--session-id") + 1]
        resumed_session = second_cmd[second_cmd.index("--resume") + 1]
        assert first_session == resumed_session
        assert "Continue the previous session" in seen[1]["stdin_text"]

    @pytest.mark.asyncio
    async def test_bash_tool_limit_returns_failed(self, executor, base_input):
        """Bash 工具调用超过上限应 fail-fast 返回 failed。"""
        with patch.object(
            executor,
            "_invoke_claude",
            side_effect=BashToolLimitExceeded(limit=5, observed=6),
        ):
            result = await executor.execute(base_input)
        assert result["status"] == "failed"
        assert "limit exceeded" in (result.get("error") or "").lower()


# ========================================================================
# 3. 输出解析测试
# ========================================================================

class TestOutputParsing:
    """测试 claude CLI 输出解析"""

    def test_parse_json_block(self, executor):
        """从 markdown JSON 代码块提取结果"""
        output = """
我已完成了以下修改：

```json
{
  "status": "success",
  "changed_files": ["src/auth.py", "tests/test_auth.py"],
  "commands_run": [{"cmd": "pytest tests/", "exit_code": 0, "stdout_tail": "2 passed"}],
  "test_results": {"passed": 2, "failed": 0},
  "error": null
}
```
"""
        parsed = executor._parse_claude_output(output)
        assert parsed["changed_files"] == ["src/auth.py", "tests/test_auth.py"]
        assert len(parsed["commands_run"]) == 1
        assert parsed["commands_run"][0]["exit_code"] == 0
        assert parsed["test_results"]["passed"] == 2
        assert parsed["error"] is None

    def test_parse_no_json(self, executor):
        """没有 JSON 代码块时退化为文本结果"""
        output = "我完成了任务，但没有输出 JSON。"
        parsed = executor._parse_claude_output(output)
        assert parsed["result_text"] == output
        assert parsed["changed_files"] == []
        assert parsed["error"] is None

    def test_parse_raw_json(self, executor):
        """直接输出 JSON（无 markdown 包裹）"""
        data = {
            "status": "success",
            "changed_files": ["main.go"],
            "commands_run": [],
            "test_results": {},
            "error": None,
        }
        output = json.dumps(data)
        parsed = executor._parse_claude_output(output)
        assert parsed["changed_files"] == ["main.go"]

    def test_parse_multiple_json_blocks(self, executor):
        """多个 JSON 代码块取最后一个"""
        output = """
先看第一个输出：
```json
{"status": "fail", "changed_files": [], "error": "first attempt"}
```

修复后：
```json
{"status": "success", "changed_files": ["fixed.py"], "commands_run": [], "test_results": {}, "error": null}
```
"""
        parsed = executor._parse_claude_output(output)
        assert parsed["changed_files"] == ["fixed.py"]
        assert parsed["error"] is None

    def test_extract_last_json_block(self, executor):
        """_extract_last_json_block 方法测试"""
        text = '```json\n{"key": "value"}\n```'
        result = executor._extract_last_json_block(text)
        assert result == '{"key": "value"}'

    def test_extract_last_json_block_none(self, executor):
        """无 JSON 块返回 None"""
        result = executor._extract_last_json_block("no json here")
        assert result is None


# ========================================================================
# 4. 迭代上限测试
# ========================================================================

class TestIterationLimits:
    """测试迭代上限"""

    @pytest.mark.asyncio
    async def test_max_iterations_in_system_prompt(self, executor, base_input):
        """max_iterations 应注入到 system prompt 中"""
        base_input["max_iterations"] = 3

        captured_cmd = []

        def mock_subprocess(cmd, cwd, timeout, stdin_text="", *args):
            captured_cmd.extend(cmd)
            return json.dumps({
                "status": "success",
                "changed_files": [],
                "commands_run": [],
                "test_results": {},
                "error": None,
            })

        with patch.object(executor, '_run_subprocess', side_effect=mock_subprocess):
            await executor.execute(base_input)
            # max_iterations 通过 system prompt 传入
            system_prompt_idx = captured_cmd.index("--system-prompt")
            system_prompt = captured_cmd[system_prompt_idx + 1]
            assert "3" in system_prompt
            assert "迭代" in system_prompt or "iteration" in system_prompt.lower()

    @pytest.mark.asyncio
    async def test_allowed_tools_format(self, executor, base_input):
        """--allowedTools 应使用逗号分隔格式"""
        captured_cmd = []

        def mock_subprocess(cmd, cwd, timeout, stdin_text="", *args):
            captured_cmd.extend(cmd)
            return '{"status": "success"}'

        with patch.object(executor, '_run_subprocess', side_effect=mock_subprocess):
            await executor.execute(base_input)
            assert "--allowedTools" in captured_cmd
            idx = captured_cmd.index("--allowedTools")
            tools_str = captured_cmd[idx + 1]
            assert "Read" in tools_str
            assert "Write" in tools_str
            assert "Bash" in tools_str  # base_input has allowed_commands

    @pytest.mark.asyncio
    async def test_empty_allowed_commands_fallback_to_default(self, executor, base_input):
        """allowed_commands 为空时应回退到默认命令集（仍允许 Bash）。"""
        captured_cmd = []
        base_input["allowed_commands"] = []

        def mock_subprocess(cmd, cwd, timeout, stdin_text="", *args):
            captured_cmd.extend(cmd)
            return '{"status": "success"}'

        with patch.object(executor, '_run_subprocess', side_effect=mock_subprocess):
            await executor.execute(base_input)

        assert "--allowedTools" in captured_cmd
        idx = captured_cmd.index("--allowedTools")
        tools_str = captured_cmd[idx + 1]
        assert "Bash" in tools_str

        sp_idx = captured_cmd.index("--system-prompt")
        system_prompt = captured_cmd[sp_idx + 1]
        assert "cat" in system_prompt
        assert "find" in system_prompt

    @pytest.mark.asyncio
    async def test_strict_mcp_uses_minimal_config(self, executor, base_input):
        """strict MCP 模式应自动使用最小 mcp config"""
        captured_cmd = []

        def mock_subprocess(cmd, cwd, timeout, stdin_text="", *args):
            captured_cmd.extend(cmd)
            return '{"status": "success"}'

        with patch.object(executor, "_run_subprocess", side_effect=mock_subprocess):
            await executor.execute(base_input)

        assert "--strict-mcp-config" in captured_cmd
        assert "--setting-sources" not in captured_cmd
        assert "--mcp-config" in captured_cmd
        mcp_idx = captured_cmd.index("--mcp-config")
        mcp_path = captured_cmd[mcp_idx + 1]
        assert mcp_path.endswith("mcp-config.minimal.json")
        payload = json.loads(Path(mcp_path).read_text())
        assert payload == {"mcpServers": {}}

    @pytest.mark.asyncio
    async def test_setting_sources_is_optional_override(self, executor, base_input):
        """可通过 setting_sources 显式覆盖 claude settings 来源"""
        captured_cmd = []
        base_input["setting_sources"] = "project,local"

        def mock_subprocess(cmd, cwd, timeout, stdin_text="", *args):
            captured_cmd.extend(cmd)
            return '{"status": "success"}'

        with patch.object(executor, "_run_subprocess", side_effect=mock_subprocess):
            await executor.execute(base_input)

        assert "--setting-sources" in captured_cmd
        idx = captured_cmd.index("--setting-sources")
        assert captured_cmd[idx + 1] == "project,local"


# ========================================================================
# 5. Evidence Bundle 测试
# ========================================================================

class TestEvidenceBundle:
    """测试 evidence bundle 写入"""

    @pytest.mark.asyncio
    async def test_evidence_dir_created(self, executor, base_input, tmp_path):
        """evidence bundle 目录应被创建"""
        evidence_base = str(tmp_path / "evidence" / "test-run")
        base_input["evidence_base"] = evidence_base

        claude_output = """完成了
```json
{"status": "success", "changed_files": [], "commands_run": [], "test_results": {}, "error": null}
```"""

        with patch.object(executor, '_invoke_claude', return_value=claude_output):
            with patch.object(executor, '_collect_diff_summary', return_value={
                "files_changed": 0, "lines_added": 0, "lines_deleted": 0,
            }):
                result = await executor.execute(base_input)

        assert result["status"] == "success"
        evidence_dir = Path(evidence_base)
        assert evidence_dir.exists()
        assert (evidence_dir / "conversation.log").exists()
        assert (evidence_dir / "result.json").exists()
        assert (evidence_dir / "input_snapshot.json").exists()

    @pytest.mark.asyncio
    async def test_input_snapshot_no_token(self, executor, base_input, tmp_path):
        """input_snapshot 不应包含 token_context"""
        evidence_base = str(tmp_path / "evidence" / "token-test")
        base_input["evidence_base"] = evidence_base
        base_input["token_context"] = "SECRET_TOKEN_DATA"

        claude_output = '```json\n{"status": "success", "changed_files": [], "commands_run": [], "test_results": {}, "error": null}\n```'

        with patch.object(executor, '_invoke_claude', return_value=claude_output):
            with patch.object(executor, '_collect_diff_summary', return_value={
                "files_changed": 0, "lines_added": 0, "lines_deleted": 0,
            }):
                await executor.execute(base_input)

        snapshot = json.loads((Path(evidence_base) / "input_snapshot.json").read_text())
        assert "token_context" not in snapshot


# ========================================================================
# 6. ExecutorFactory 注册测试
# ========================================================================

class TestExecutorRegistration:
    """测试 ExecutorFactory 注册"""

    def test_claude_code_registered(self):
        """claude_code 应已注册到 ExecutorFactory"""
        assert "claude_code" in ExecutorFactory._executors

    def test_create_claude_code_executor(self):
        """ExecutorFactory.create('claude_code') 应返回 ClaudeCodeExecutor 实例"""
        executor = ExecutorFactory.create("claude_code")
        assert isinstance(executor, ClaudeCodeExecutor)

    def test_register_idempotent(self):
        """重复注册不应报错"""
        register_claude_code_executor()
        assert "claude_code" in ExecutorFactory._executors


# ========================================================================
# 7. Diff 摘要测试
# ========================================================================

class TestDiffSummary:
    """测试 diff 摘要收集"""

    @pytest.mark.asyncio
    async def test_git_diff_parsing(self, executor, workspace):
        """解析 git diff --numstat 输出"""
        numstat_output = "10\t2\tsrc/auth.py\n5\t0\ttests/test_auth.py\n"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = numstat_output

        with patch("subprocess.run", return_value=mock_result):
            summary = await executor._collect_diff_summary(str(workspace))

        assert summary["files_changed"] == 2
        assert summary["lines_added"] == 15
        assert summary["lines_deleted"] == 2

    @pytest.mark.asyncio
    async def test_git_diff_failure(self, executor, workspace):
        """git diff 失败时返回空摘要"""
        mock_result = MagicMock()
        mock_result.returncode = 128
        mock_result.stdout = ""

        with patch("subprocess.run", return_value=mock_result):
            summary = await executor._collect_diff_summary(str(workspace))

        assert summary["files_changed"] == 0
        assert summary["lines_added"] == 0
        assert summary["lines_deleted"] == 0


# ========================================================================
# 8. 停止条件判定测试
# ========================================================================

class TestStopConditions:
    """测试停止条件"""

    def test_success_status(self, executor):
        """无错误时返回 success"""
        parsed = {"error": None, "test_results": {"passed": 5, "failed": 0}}
        status = executor._determine_status(parsed, {})
        assert status == "success"

    def test_fail_on_error(self, executor):
        """有错误时返回 fail"""
        parsed = {"error": "compilation failed", "test_results": {}}
        status = executor._determine_status(parsed, {})
        assert status == "fail"

    def test_needs_human_on_policy_violation(self, executor):
        """policy violation 时返回 needs_human"""
        parsed = {"error": "policy violation detected", "test_results": {}}
        stop_conditions = {"on_policy_violation": "stop_needs_human"}
        status = executor._determine_status(parsed, stop_conditions)
        assert status == "needs_human"

    def test_non_policy_error_with_policy_config(self, executor):
        """非 policy 错误即使配置了 on_policy_violation 也返回 fail"""
        parsed = {"error": "compilation failed", "test_results": {}}
        stop_conditions = {"on_policy_violation": "stop_needs_human"}
        status = executor._determine_status(parsed, stop_conditions)
        assert status == "fail"

    def test_fail_on_test_failure(self, executor):
        """测试失败时返回 fail"""
        parsed = {"error": None, "test_results": {"passed": 3, "failed": 2}}
        status = executor._determine_status(parsed, {})
        assert status == "fail"

    def test_needs_human_on_test_fail_config(self, executor):
        """stop_conditions 配置 test_fail → needs_human"""
        parsed = {"error": None, "test_results": {"passed": 3, "failed": 2}}
        stop_conditions = {"on_test_fail": "stop_needs_human"}
        status = executor._determine_status(parsed, stop_conditions)
        assert status == "needs_human"


# ========================================================================
# 9. System Prompt 构建测试
# ========================================================================

class TestSystemPrompt:
    """测试 system prompt 构建"""

    def test_includes_workspace(self, executor):
        """system prompt 包含工作目录"""
        prompt = executor._build_system_prompt(
            goal="test",
            workspace="/my/project",
            allowed_commands=["pytest"],
            write_scope=["src/**"],
            forbidden_read_paths=[],
            max_iterations=5,
            max_bash_calls=12,
            stop_conditions={},
            system_prompt_extra="",
        )
        assert "/my/project" in prompt
        assert "pytest" in prompt
        assert "src/**" in prompt
        assert "12" in prompt

    def test_includes_extra(self, executor):
        """system prompt 包含额外约束"""
        prompt = executor._build_system_prompt(
            goal="test",
            workspace="/my/project",
            allowed_commands=[],
            write_scope=[],
            forbidden_read_paths=[],
            max_iterations=5,
            max_bash_calls=0,
            stop_conditions={},
            system_prompt_extra="不允许修改 go.mod",
        )
        assert "不允许修改 go.mod" in prompt

    def test_includes_forbidden_read_paths(self, executor):
        """system prompt 应显式禁止读取历史产物目录"""
        prompt = executor._build_system_prompt(
            goal="test",
            workspace="/my/project",
            allowed_commands=["cat"],
            write_scope=["spec/**"],
            forbidden_read_paths=["output/", "evidence/", ".workflow/claude-code/", "pytest-temp/", ".codex-worktrees/"],
            max_iterations=5,
            max_bash_calls=0,
            stop_conditions={},
            system_prompt_extra="",
        )
        assert "禁止读取或引用的路径" in prompt
        assert "output/" in prompt
        assert "evidence/" in prompt
        assert ".workflow/claude-code/" in prompt
        assert "pytest-temp/" in prompt
        assert ".codex-worktrees/" in prompt
        assert "不要扫描仓库寻找相似的 EPIC、FEAT、SRC、ADR" in prompt

    def test_scan_bash_calls_from_debug_log(self, tmp_path):
        """debug 日志增量扫描应能统计 Bash 调用次数。"""
        debug_file = tmp_path / "claude-debug.log"
        debug_file.write_text(
            "a\nexecutePreToolHooks called for tool: Bash\n"
            "x\nexecutePreToolHooks called for tool: Bash\n",
            encoding="utf-8",
        )
        offset, count = ClaudeCodeExecutor._scan_bash_calls_from_debug_log(
            str(debug_file),
            0,
        )
        assert count == 2
        assert offset == debug_file.stat().st_size


# ========================================================================
# 10. 端到端（mock）测试
# ========================================================================

class TestEndToEnd:
    """端到端集成测试（mock claude CLI）"""

    @pytest.mark.asyncio
    async def test_successful_execution(self, executor, base_input, tmp_path):
        """正常执行流程"""
        evidence_base = str(tmp_path / "evidence" / "e2e")
        base_input["evidence_base"] = evidence_base

        claude_output = """我已完成任务。

```json
{
  "status": "success",
  "changed_files": ["src/auth.py"],
  "commands_run": [{"cmd": "pytest tests/", "exit_code": 0, "stdout_tail": "1 passed"}],
  "test_results": {"passed": 1, "failed": 0},
  "error": null
}
```"""

        with patch.object(executor, '_invoke_claude', return_value=claude_output):
            with patch.object(executor, '_collect_diff_summary', return_value={
                "files_changed": 1, "lines_added": 20, "lines_deleted": 5,
            }):
                result = await executor.execute(base_input)

        assert result["status"] == "success"
        assert result["changed_files"] == ["src/auth.py"]
        assert result["diff_summary"]["files_changed"] == 1
        assert result["diff_summary"]["lines_added"] == 20
        assert result["evidence_bundle_path"] == evidence_base
        assert result["generated_text"]  # 非空
        assert result["error"] is None

    @pytest.mark.asyncio
    async def test_failed_execution(self, executor, base_input, tmp_path):
        """执行失败流程"""
        evidence_base = str(tmp_path / "evidence" / "fail")
        base_input["evidence_base"] = evidence_base

        claude_output = """编译失败。

```json
{
  "status": "fail",
  "changed_files": ["src/broken.py"],
  "commands_run": [{"cmd": "pytest", "exit_code": 1, "stdout_tail": "FAILED"}],
  "test_results": {"passed": 0, "failed": 1},
  "error": "Tests failed"
}
```"""

        with patch.object(executor, '_invoke_claude', return_value=claude_output):
            with patch.object(executor, '_collect_diff_summary', return_value={
                "files_changed": 1, "lines_added": 10, "lines_deleted": 0,
            }):
                result = await executor.execute(base_input)

        assert result["status"] == "fail"
        assert result["error"] is not None
