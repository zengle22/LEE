"""
Claude Code Executor

将 Claude Code（多轮 LLM + 工具调用）封装为 LEE 受控执行器。

⚠️ 治理约束 ⚠️

本执行器严格遵循 Executor 宪法（见 executors.py）并额外施加：
1. workspace 目录边界 — 不允许操作 workspace 之外的文件
2. 命令白名单 — 仅允许声明的命令
3. 迭代上限 — 超过 max_iterations 自动停止
4. 结构化证据输出 — 所有操作可审计
5. 超时保护 — 总运行时间有上限

输入/输出契约见 implementation_plan.md
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .executors import BaseExecutor


class ClaudeCodeExecutor(BaseExecutor):
    """
    Claude Code 执行器

    通过 subprocess 调用 claude CLI，解析结构化输出。

    使用方式:
        executor = ClaudeCodeExecutor()
        result = await executor.execute({
            "goal": "实现用户登录 API",
            "workspace": "/path/to/project",
            "allowed_commands": ["go test", "go build"],
            "max_iterations": 5,
        })
    """

    # 默认配置
    DEFAULT_MAX_ITERATIONS = 5
    DEFAULT_TIMEOUT_SECONDS = 600
    DEFAULT_ALLOWED_COMMANDS = ["cat", "ls", "find", "grep"]

    def __init__(self, **kwargs):
        """
        初始化 Claude Code 执行器

        Args:
            **kwargs: 额外参数（保留扩展性）
        """
        self._claude_binary = os.getenv("CLAUDE_CODE_BINARY", "claude")

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Claude Code 任务

        Args:
            input_data: 输入数据，必须包含 goal 和 workspace

        Returns:
            结构化执行结果
        """
        # ========== 1. 输入验证 ==========
        validation_error = self._validate_input(input_data)
        if validation_error:
            return {
                "status": "failed",
                "error": validation_error,
                "iterations_used": 0,
                "changed_files": [],
                "commands_run": [],
                "test_results": {},
                "diff_summary": {},
                "evidence_bundle_path": "",
                "conversation_log_path": "",
            }

        goal = input_data["goal"]
        workspace = input_data["workspace"]
        context_files = input_data.get("context_files", [])
        allowed_commands = input_data.get(
            "allowed_commands", self.DEFAULT_ALLOWED_COMMANDS
        )
        write_scope = input_data.get("write_scope", [])
        max_iterations = input_data.get(
            "max_iterations", self.DEFAULT_MAX_ITERATIONS
        )
        timeout_seconds = input_data.get(
            "timeout_seconds", self.DEFAULT_TIMEOUT_SECONDS
        )
        stop_conditions = input_data.get("stop_conditions", {})
        system_prompt_extra = input_data.get("system_prompt_extra", "")
        evidence_base = input_data.get("evidence_base", "")

        # ========== 2. 构建 evidence bundle 目录 ==========
        evidence_dir = self._prepare_evidence_dir(evidence_base, workspace)

        # ========== 3. 构建 system prompt（治理约束注入） ==========
        system_prompt = self._build_system_prompt(
            goal=goal,
            workspace=workspace,
            allowed_commands=allowed_commands,
            write_scope=write_scope,
            max_iterations=max_iterations,
            stop_conditions=stop_conditions,
            system_prompt_extra=system_prompt_extra,
        )

        # ========== 4. 构建用户 prompt ==========
        user_prompt = self._build_user_prompt(
            goal=goal,
            context_files=context_files,
        )

        # ========== 5. 调用 claude CLI ==========
        try:
            raw_output = await self._invoke_claude(
                prompt=user_prompt,
                system_prompt=system_prompt,
                workspace=workspace,
                allowed_commands=allowed_commands,
                timeout_seconds=timeout_seconds,
                max_iterations=max_iterations,
            )
        except asyncio.TimeoutError:
            return self._build_result(
                status="timeout",
                error=f"Claude Code execution timed out after {timeout_seconds}s",
                evidence_dir=str(evidence_dir),
            )
        except FileNotFoundError:
            return self._build_result(
                status="failed",
                error=f"Claude CLI binary not found: {self._claude_binary}. "
                      "Install with: npm install -g @anthropic-ai/claude-code",
                evidence_dir=str(evidence_dir),
            )
        except Exception as e:
            return self._build_result(
                status="failed",
                error=f"Claude CLI invocation failed: {e}",
                evidence_dir=str(evidence_dir),
            )

        # ========== 6. 解析输出 ==========
        parsed = self._parse_claude_output(raw_output)

        # ========== 7. 收集 diff 摘要 ==========
        diff_summary = await self._collect_diff_summary(workspace)

        # ========== 8. 写入 evidence bundle ==========
        conversation_log_path = self._write_evidence(
            evidence_dir=evidence_dir,
            raw_output=raw_output,
            parsed=parsed,
            diff_summary=diff_summary,
            input_data=input_data,
        )

        # ========== 9. 构建返回结果 ==========
        status = self._determine_status(parsed, stop_conditions)

        return {
            "status": status,
            "iterations_used": parsed.get("iterations_used", 1),
            "changed_files": parsed.get("changed_files", []),
            "commands_run": parsed.get("commands_run", []),
            "test_results": parsed.get("test_results", {}),
            "diff_summary": diff_summary,
            "evidence_bundle_path": str(evidence_dir),
            "conversation_log_path": conversation_log_path,
            "generated_text": parsed.get("result_text", ""),
            "error": parsed.get("error"),
        }

    # ================================================================
    # 内部方法
    # ================================================================

    def _validate_input(self, input_data: Dict[str, Any]) -> Optional[str]:
        """验证输入数据"""
        if not input_data.get("goal"):
            return "Missing required field: goal"
        if not input_data.get("workspace"):
            return "Missing required field: workspace"

        workspace = Path(input_data["workspace"])
        if not workspace.exists():
            return f"Workspace directory does not exist: {workspace}"
        if not workspace.is_dir():
            return f"Workspace path is not a directory: {workspace}"

        return None

    def _prepare_evidence_dir(
        self, evidence_base: str, workspace: str
    ) -> Path:
        """准备 evidence bundle 目录"""
        if evidence_base:
            evidence_dir = Path(evidence_base)
        else:
            evidence_dir = (
                Path(workspace) / ".workflow" / "claude-code"
                / datetime.now().strftime("%Y%m%d-%H%M%S")
            )
        evidence_dir.mkdir(parents=True, exist_ok=True)
        return evidence_dir

    def _build_system_prompt(
        self,
        goal: str,
        workspace: str,
        allowed_commands: List[str],
        write_scope: List[str],
        max_iterations: int,
        stop_conditions: Dict[str, str],
        system_prompt_extra: str,
    ) -> str:
        """构建系统 prompt（注入治理约束）"""
        constraints = [
            f"你正在 LEE 工作流中作为受控执行器运行。",
            f"工作目录: {workspace}",
            f"允许使用的命令: {', '.join(allowed_commands)}",
            f"最大迭代轮数: {max_iterations}",
        ]

        if write_scope:
            constraints.append(
                f"允许写入的路径: {', '.join(write_scope)}"
            )
        else:
            constraints.append("允许写入工作目录内的任何文件")

        if stop_conditions:
            cond_desc = "; ".join(
                f"{k}: {v}" for k, v in stop_conditions.items()
            )
            constraints.append(f"停止条件: {cond_desc}")

        constraints_text = "\n".join(f"- {c}" for c in constraints)

        prompt = f"""## 治理约束

{constraints_text}

## 输出要求

完成任务后，请在最后输出一个 JSON 代码块，格式如下：
```json
{{
  "status": "success 或 fail",
  "changed_files": ["修改的文件列表"],
  "commands_run": [{{"cmd": "执行的命令", "exit_code": 0, "stdout_tail": "输出尾部"}}],
  "test_results": {{"passed": 0, "failed": 0}},
  "error": null
}}
```"""

        if system_prompt_extra:
            prompt += f"\n\n## 额外约束\n\n{system_prompt_extra}"

        return prompt

    def _build_user_prompt(
        self, goal: str, context_files: List[str]
    ) -> str:
        """构建用户 prompt"""
        prompt = f"## 任务目标\n\n{goal}"

        if context_files:
            files_list = "\n".join(f"- {f}" for f in context_files)
            prompt += f"\n\n## 上下文文件\n\n请先阅读以下文件：\n{files_list}"

        return prompt

    async def _invoke_claude(
        self,
        prompt: str,
        system_prompt: str,
        workspace: str,
        allowed_commands: List[str],
        timeout_seconds: int,
        max_iterations: int,
    ) -> str:
        """
        调用 claude CLI (v2.x)

        使用 --print 模式获取完整输出。
        工作目录通过 subprocess cwd 参数控制。
        prompt 通过 stdin 传入以避免 shell 转义问题。
        """
        cmd = [
            self._claude_binary,
            "--print",
            "--output-format", "json",
        ]

        # 注入系统 prompt
        if system_prompt:
            cmd.extend(["--system-prompt", system_prompt])

        # 构建工具白名单
        # claude CLI --allowedTools 接受空格/逗号分隔的工具名
        allowed_tools = ["Read", "Write", "Edit", "MultiEdit"]
        if allowed_commands:
            allowed_tools.append("Bash")

        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        # prompt 通过 stdin 传入（避免命令行参数过长或转义问题）

        loop = asyncio.get_event_loop()
        result = await asyncio.wait_for(
            loop.run_in_executor(
                None,
                self._run_subprocess,
                cmd,
                workspace,
                timeout_seconds,
                prompt,
            ),
            timeout=timeout_seconds + 30,  # 额外 30s buffer
        )
        return result

    def _run_subprocess(
        self, cmd: List[str], cwd: str, timeout: int, stdin_text: str = ""
    ) -> str:
        """同步执行 subprocess（在线程池中调用）"""
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=cwd,
                timeout=timeout,
                input=stdin_text or None,
                env={**os.environ, "CLAUDE_CODE_ENTRYPOINT": "lee-executor"},
            )
            # 合并 stdout + stderr，确保不丢失任何输出
            output = result.stdout or ""
            if result.stderr:
                output += f"\n--- stderr ---\n{result.stderr}"
            return output
        except subprocess.TimeoutExpired:
            raise asyncio.TimeoutError(
                f"subprocess timed out after {timeout}s"
            )

    def _parse_claude_output(self, raw_output: str) -> Dict[str, Any]:
        """
        解析 claude CLI 输出

        --output-format json 返回单个 JSON 对象：
        {
            "type": "result",
            "subtype": "success",
            "num_turns": 6,
            "result": "文本输出（可能包含 ```json ... ``` 代码块）",
            "is_error": false,
            "total_cost_usd": 0.19,
            ...
        }
        """
        parsed: Dict[str, Any] = {
            "result_text": "",
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "iterations_used": 1,
            "error": None,
        }

        # 清理 stderr 分隔符之前的内容作为主输出
        main_output = raw_output.split("\n--- stderr ---\n")[0].strip()

        # 1. 尝试解析 claude CLI JSON 格式输出
        try:
            data = json.loads(main_output)

            if isinstance(data, dict):
                # Claude CLI --output-format json 返回 {"type": "result", ...}
                if data.get("type") == "result":
                    return self._parse_result_object(data, raw_output)

                # 消息数组格式（stream-json 等）
                if isinstance(data, list):
                    return self._parse_json_messages(data, raw_output)

                # 用户自定义 JSON（直接包含 changed_files 等）
                parsed["changed_files"] = data.get("changed_files", [])
                parsed["commands_run"] = data.get("commands_run", [])
                parsed["test_results"] = data.get("test_results", {})
                parsed["error"] = data.get("error")
                parsed["result_text"] = raw_output
                if data.get("status") == "fail":
                    parsed["error"] = parsed["error"] or "Task reported failure"
                return parsed

            elif isinstance(data, list):
                return self._parse_json_messages(data, raw_output)

        except (json.JSONDecodeError, ValueError):
            pass

        # 2. 退化：从文本中提取 JSON 代码块
        parsed["result_text"] = raw_output
        json_block = self._extract_last_json_block(raw_output)
        if json_block:
            try:
                data = json.loads(json_block)
                if isinstance(data, dict):
                    parsed["changed_files"] = data.get("changed_files", [])
                    parsed["commands_run"] = data.get("commands_run", [])
                    parsed["test_results"] = data.get("test_results", {})
                    parsed["error"] = data.get("error")
                    if data.get("status") == "fail":
                        parsed["error"] = parsed["error"] or "Task reported failure"
            except json.JSONDecodeError:
                pass

        return parsed

    def _parse_result_object(
        self, data: Dict[str, Any], raw_output: str
    ) -> Dict[str, Any]:
        """
        解析 claude CLI --output-format json 的结果对象

        格式：
        {
            "type": "result",
            "subtype": "success",
            "is_error": false,
            "num_turns": 6,
            "result": "文本输出（包含 ```json ... ```）",
            "total_cost_usd": 0.19,
            "usage": {...},
            "session_id": "...",
        }
        """
        parsed: Dict[str, Any] = {
            "result_text": "",
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "iterations_used": data.get("num_turns", 1),
            "error": None,
            # 额外元数据
            "cost_usd": data.get("total_cost_usd", 0),
            "session_id": data.get("session_id", ""),
            "duration_ms": data.get("duration_ms", 0),
        }

        # 检查是否报错
        if data.get("is_error"):
            parsed["error"] = data.get("result", "") or "Claude reported error"

        # 提取 result 文本
        result_text = data.get("result", "")
        parsed["result_text"] = result_text

        # 从 result 文本中提取嵌入的 JSON 代码块
        if result_text:
            json_block = self._extract_last_json_block(result_text)
            if json_block:
                try:
                    embedded = json.loads(json_block)
                    if isinstance(embedded, dict):
                        parsed["changed_files"] = embedded.get("changed_files", [])
                        parsed["commands_run"] = embedded.get("commands_run", [])
                        parsed["test_results"] = embedded.get("test_results", {})
                        if embedded.get("error"):
                            parsed["error"] = embedded["error"]
                        if embedded.get("status") == "fail":
                            parsed["error"] = parsed["error"] or "Task reported failure"
                except json.JSONDecodeError:
                    pass

        return parsed

    def _parse_json_messages(
        self, messages: List[Dict[str, Any]], raw_output: str
    ) -> Dict[str, Any]:
        """
        解析 claude CLI JSON 消息数组

        每条消息格式：
        {
            "type": "result",
            "subtype": "success",
            "cost_usd": 0.05,
            "duration_ms": 12000,
            "duration_api_ms": 8000,
            "is_error": false,
            "num_turns": 3,
            "result": "最终文本输出..."
        }

        或 tool_use 消息：
        {
            "type": "assistant",
            "message": {
                "content": [
                    {"type": "tool_use", "name": "Bash", "input": {"command": "pytest"}},
                    {"type": "text", "text": "..."}
                ]
            }
        }
        """
        parsed: Dict[str, Any] = {
            "result_text": "",
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "iterations_used": 1,
            "error": None,
        }

        changed_files_set = set()
        commands_run = []
        result_texts = []

        for msg in messages:
            msg_type = msg.get("type", "")

            # result 类型消息（最终结果）
            if msg_type == "result":
                parsed["iterations_used"] = msg.get("num_turns", 1)
                result_text = msg.get("result", "")
                if result_text:
                    result_texts.append(result_text)
                if msg.get("is_error"):
                    parsed["error"] = result_text or "Claude reported error"
                # 从 result text 提取 JSON 代码块
                if result_text:
                    json_block = self._extract_last_json_block(result_text)
                    if json_block:
                        try:
                            data = json.loads(json_block)
                            if isinstance(data, dict):
                                parsed["changed_files"] = data.get("changed_files", list(changed_files_set))
                                parsed["test_results"] = data.get("test_results", parsed["test_results"])
                                if data.get("error"):
                                    parsed["error"] = data["error"]
                        except json.JSONDecodeError:
                            pass
                continue

            # assistant 消息（可能包含 tool_use）
            message_obj = msg.get("message", msg)
            content = message_obj.get("content", [])
            if isinstance(content, str):
                result_texts.append(content)
                continue

            for block in content:
                if not isinstance(block, dict):
                    continue

                block_type = block.get("type", "")

                if block_type == "text":
                    result_texts.append(block.get("text", ""))

                elif block_type == "tool_use":
                    tool_name = block.get("name", "")
                    tool_input = block.get("input", {})

                    if tool_name == "Bash":
                        cmd_str = tool_input.get("command", "")
                        if cmd_str:
                            commands_run.append({
                                "cmd": cmd_str,
                                "exit_code": 0,  # tool_use 不包含 exit code
                                "stdout_tail": "",
                            })
                    elif tool_name in ("Write", "Edit", "MultiEdit"):
                        file_path = tool_input.get("file_path", "") or tool_input.get("path", "")
                        if file_path:
                            changed_files_set.add(file_path)

            # tool_result 消息（Bash 执行结果）
            if msg_type == "tool_result" or "content" in msg:
                for block in (msg.get("content", []) if isinstance(msg.get("content"), list) else []):
                    if isinstance(block, dict) and block.get("type") == "tool_result":
                        # 提取 bash 命令结果
                        tool_content = block.get("content", "")
                        if isinstance(tool_content, str) and ("passed" in tool_content.lower() or "failed" in tool_content.lower()):
                            # 尝试解析测试结果
                            self._extract_test_results(tool_content, parsed)

        # 如果从消息中找到了文件但 JSON 块没有覆盖
        if not parsed["changed_files"] and changed_files_set:
            parsed["changed_files"] = list(changed_files_set)
        if not parsed["commands_run"] and commands_run:
            parsed["commands_run"] = commands_run

        parsed["result_text"] = "\n".join(result_texts) if result_texts else raw_output

        return parsed

    def _extract_test_results(self, output: str, parsed: Dict[str, Any]):
        """从测试输出中提取 passed/failed 计数"""
        import re
        # 匹配 pytest 风格: "5 passed, 1 failed"
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        if passed_match or failed_match:
            parsed["test_results"] = {
                "passed": int(passed_match.group(1)) if passed_match else 0,
                "failed": int(failed_match.group(1)) if failed_match else 0,
            }

    def _extract_last_json_block(self, text: str) -> Optional[str]:
        """从文本中提取最后一个 ```json ... ``` 代码块"""
        import re

        # 匹配 ```json ... ``` 代码块
        pattern = r"```json\s*\n(.*?)\n\s*```"
        matches = re.findall(pattern, text, re.DOTALL)
        if matches:
            return matches[-1].strip()

        # 退化：尝试找最后一个 { ... } 块
        # 从末尾向前搜索
        last_brace = text.rfind("}")
        if last_brace == -1:
            return None

        # 向前找对应的 {
        depth = 0
        for i in range(last_brace, -1, -1):
            if text[i] == "}":
                depth += 1
            elif text[i] == "{":
                depth -= 1
            if depth == 0:
                candidate = text[i : last_brace + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    return None

        return None

    async def _collect_diff_summary(
        self, workspace: str
    ) -> Dict[str, Any]:
        """执行 git diff --stat 收集变更摘要"""
        try:
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: subprocess.run(
                    ["git", "diff", "--stat", "--numstat"],
                    capture_output=True,
                    text=True,
                    cwd=workspace,
                    timeout=30,
                ),
            )

            if result.returncode != 0:
                return {"files_changed": 0, "lines_added": 0, "lines_deleted": 0}

            lines_added = 0
            lines_deleted = 0
            files_changed = 0

            for line in result.stdout.strip().split("\n"):
                parts = line.split("\t")
                if len(parts) >= 3:
                    try:
                        added = int(parts[0]) if parts[0] != "-" else 0
                        deleted = int(parts[1]) if parts[1] != "-" else 0
                        lines_added += added
                        lines_deleted += deleted
                        files_changed += 1
                    except ValueError:
                        continue

            return {
                "files_changed": files_changed,
                "lines_added": lines_added,
                "lines_deleted": lines_deleted,
            }
        except Exception:
            return {"files_changed": 0, "lines_added": 0, "lines_deleted": 0}

    def _write_evidence(
        self,
        evidence_dir: Path,
        raw_output: str,
        parsed: Dict[str, Any],
        diff_summary: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> str:
        """写入 evidence bundle"""
        # 1. 原始对话日志
        conversation_log = evidence_dir / "conversation.log"
        conversation_log.write_text(raw_output, encoding="utf-8")

        # 2. 结构化结果
        result_json = evidence_dir / "result.json"
        result_json.write_text(
            json.dumps(
                {
                    "parsed_output": parsed,
                    "diff_summary": diff_summary,
                    "timestamp": datetime.now().isoformat(),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        # 3. 输入快照（可审计）
        input_snapshot = evidence_dir / "input_snapshot.json"
        # 脱敏：移除 token_context
        safe_input = {k: v for k, v in input_data.items() if k != "token_context"}
        input_snapshot.write_text(
            json.dumps(safe_input, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        return str(conversation_log)

    def _determine_status(
        self, parsed: Dict[str, Any], stop_conditions: Dict[str, str]
    ) -> str:
        """根据解析结果和停止条件确定最终状态"""
        error = parsed.get("error")
        if error:
            # 仅当错误文本包含 policy 关键词时，才视为 policy violation
            error_lower = str(error).lower()
            is_policy = any(kw in error_lower for kw in ("policy", "violation", "forbidden", "unauthorized"))
            if is_policy and stop_conditions.get("on_policy_violation") == "stop_needs_human":
                return "needs_human"
            return "fail"

        test_results = parsed.get("test_results", {})
        if test_results.get("failed", 0) > 0:
            action = stop_conditions.get("on_test_fail", "fail")
            if action == "stop_needs_human":
                return "needs_human"
            return "fail"

        return "success"

    def _build_result(
        self,
        status: str,
        error: str,
        evidence_dir: str = "",
    ) -> Dict[str, Any]:
        """构建错误/异常结果"""
        return {
            "status": status,
            "error": error,
            "iterations_used": 0,
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "diff_summary": {"files_changed": 0, "lines_added": 0, "lines_deleted": 0},
            "evidence_bundle_path": evidence_dir,
            "conversation_log_path": "",
            "generated_text": "",
        }


def register_claude_code_executor():
    """
    注册 Claude Code 执行器到 ExecutorFactory

    使用方式:
        from lee.orchestrator.execution.claude_code_executor import register_claude_code_executor
        register_claude_code_executor()
    """
    from .executors import ExecutorFactory

    ExecutorFactory.register("claude_code", ClaudeCodeExecutor)
