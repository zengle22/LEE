"""
Codex Executor

将 OpenAI Codex CLI（多轮 LLM + 工具调用）封装为 LEE 受控执行器。

⚠️ 治理约束 ⚠️

本执行器严格遵循 Executor 宪法（见 executors.py）并额外施加：
1. workspace 目录边界 — 不允许操作 workspace 之外的文件
2. 命令白名单 — 仅允许声明的命令（通过 sandbox 模式控制）
3. 迭代上限 — 超过 max_iterations 自动停止
4. 结构化证据输出 — 所有操作可审计
5. 超时保护 — 总运行时间有上限

架构说明：
- 完全复用 Claude Code Executor 的设计模式
- 底层调用 codex CLI (exec 子命令) 而非 claude CLI
- 解析 JSONL 格式输出并转换为统一结果格式
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import queue
import re
import signal
import shutil
import subprocess
import threading
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .error_hints import append_executor_hints
from .executors import BaseExecutor

logger = logging.getLogger(__name__)


class BashToolLimitExceeded(RuntimeError):
    """Raised when bash tool calls exceed configured hard limit."""

    def __init__(self, limit: int, observed: int):
        self.limit = limit
        self.observed = observed
        super().__init__(
            f"bash tool call limit exceeded: observed={observed}, limit={limit}"
        )


class CodexExecutor(BaseExecutor):
    """
    Codex 执行器

    通过 subprocess 调用 codex CLI，解析结构化输出。

    使用方式:
        executor = CodexExecutor()
        result = await executor.execute({
            "goal": "实现用户登录 API",
            "workspace": "/path/to/project",
            "allowed_commands": ["go test", "go build"],
            "max_iterations": 5,
        })
    """

    # 默认配置
    DEFAULT_MAX_ITERATIONS = 5
    DEFAULT_TIMEOUT_SECONDS = 3600  # 1 hour for long-running tasks
    DEFAULT_TIMEOUT_RETRIES = 1
    DEFAULT_RETRY_BACKOFF_SECONDS = 5
    DEFAULT_SILENCE_TIMEOUT_SECONDS = 600
    DEFAULT_SILENCE_GRACE_SECONDS = 20
    DEFAULT_ALLOWED_COMMANDS = ["cat", "ls", "find", "grep"]
    DEFAULT_HEARTBEAT_SECONDS = 5
    DEFAULT_MODEL = ""
    DEFAULT_MAX_BASH_CALLS = 60
    DEFAULT_RESUME_ON_RETRY = True
    DEFAULT_SANDBOX_MODE = "workspace-write"  # Codex sandbox: read-only, workspace-write, danger-full-access

    # Codex CLI 定价 (per 1K tokens, 2026)
    PRICING = {
        "gpt-4o": {"input": 0.005, "output": 0.015},
        "gpt-4-turbo": {"input": 0.01, "output": 0.03},
        "gpt-4": {"input": 0.03, "output": 0.06},
        "o1-mini": {"input": 0.003, "output": 0.012},
        "o1-preview": {"input": 0.015, "output": 0.06},
        "o3-mini": {"input": 0.001, "output": 0.003},
        "gpt-5.3-codex": {"input": 0.01, "output": 0.03},  # 估算
        "gpt-5.2-codex": {"input": 0.01, "output": 0.03},  # 估算
    }

    def __init__(self, **kwargs):
        """
        初始化 Codex 执行器

        Args:
            **kwargs: 额外参数（保留扩展性）
        """
        self._codex_binary = self._resolve_binary(
            os.getenv("CODEX_BINARY", "codex")
        )
        self._model = (
            kwargs.get("model")
            or os.getenv("CODEX_MODEL", "").strip()
            or self.DEFAULT_MODEL
        )
        self._prefer_local_auth = self._has_local_auth_file()
        self._extra_env = self._load_codex_env_settings()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Codex 任务

        Args:
            input_data: 输入数据，必须包含 goal 和 workspace

        Returns:
            结构化执行结果
        """
        # ========== 1. 输入验证 ==========
        validation_error = self._validate_input(input_data)
        if validation_error:
            return self._build_error_result(validation_error)

        goal = input_data["goal"]
        workspace = input_data["workspace"]
        context_files = input_data.get("context_files") or []

        # 获取配置参数
        configured_commands = input_data.get("allowed_commands")
        if isinstance(configured_commands, list):
            allowed_commands = [
                str(cmd).strip() for cmd in configured_commands if str(cmd).strip()
            ]
        else:
            allowed_commands = []
        if not allowed_commands:
            allowed_commands = list(self.DEFAULT_ALLOWED_COMMANDS)

        write_scope = input_data.get("write_scope") or []
        max_iterations = self._coerce_positive_int(
            input_data.get("max_iterations"),
            self.DEFAULT_MAX_ITERATIONS,
        )
        timeout_seconds = self._coerce_positive_int(
            input_data.get("timeout_seconds"),
            self.DEFAULT_TIMEOUT_SECONDS,
        )
        timeout_retries = self._coerce_non_negative_int(
            input_data.get("timeout_retries"),
            self.DEFAULT_TIMEOUT_RETRIES,
        )
        retry_backoff_seconds = self._coerce_non_negative_int(
            input_data.get("retry_backoff_seconds"),
            self.DEFAULT_RETRY_BACKOFF_SECONDS,
        )
        silence_timeout_seconds = self._coerce_non_negative_int(
            input_data.get("silence_timeout_seconds"),
            self.DEFAULT_SILENCE_TIMEOUT_SECONDS,
        )
        silence_grace_seconds = self._coerce_non_negative_int(
            input_data.get("silence_grace_seconds"),
            self.DEFAULT_SILENCE_GRACE_SECONDS,
        )
        stop_conditions = input_data.get("stop_conditions", {})
        system_prompt_extra = input_data.get("system_prompt_extra", "")
        structured_output_only = bool(input_data.get("structured_output_only", False))
        evidence_base = input_data.get("evidence_base", "")
        model = str(input_data.get("model") or self._model or "").strip()
        max_bash_calls = self._coerce_non_negative_int(
            input_data.get("max_bash_calls"),
            self.DEFAULT_MAX_BASH_CALLS,
        )
        resume_on_retry = bool(
            input_data.get("resume_on_retry", self.DEFAULT_RESUME_ON_RETRY)
        )
        sandbox_mode = input_data.get("sandbox_mode", self.DEFAULT_SANDBOX_MODE)

        # ========== 2. 构建 evidence bundle 目录 ==========
        evidence_dir = self._prepare_evidence_dir(evidence_base, workspace)

        # ========== 3. 构建 system prompt（治理约束注入） ==========
        system_prompt = self._build_system_prompt(
            goal=goal,
            workspace=workspace,
            allowed_commands=allowed_commands,
            write_scope=write_scope,
            max_iterations=max_iterations,
            max_bash_calls=max_bash_calls,
            stop_conditions=stop_conditions,
            system_prompt_extra=system_prompt_extra,
            structured_output_only=structured_output_only,
        )

        # ========== 4. 构建用户 prompt ==========
        user_prompt = self._build_user_prompt(
            goal=goal,
            context_files=context_files,
        )

        # 调试输出文件（即使失败也可用于排障）
        conversation_live_log_path = str(evidence_dir / "conversation.live.log")
        codex_debug_log_path = str(evidence_dir / "codex-debug.log")
        prompt_system_path = str(evidence_dir / "prompt.system.txt")
        prompt_user_path = str(evidence_dir / "prompt.user.txt")
        self._write_prompt_artifacts(
            prompt_system_path=prompt_system_path,
            prompt_user_path=prompt_user_path,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        self._append_live_log_meta(
            conversation_live_log_path,
            f"prompt_system_path={prompt_system_path}",
        )
        self._append_live_log_meta(
            conversation_live_log_path,
            f"prompt_user_path={prompt_user_path}",
        )
        self._append_live_log_meta(
            conversation_live_log_path,
            f"model={model or '(default)'}",
        )
        self._append_live_log_meta(
            conversation_live_log_path,
            f"sandbox_mode={sandbox_mode}",
        )

        # ========== 5. 调用 codex CLI ==========
        try:
            raw_output = await self._invoke_codex(
                prompt=user_prompt,
                system_prompt=system_prompt,
                workspace=workspace,
                allowed_commands=allowed_commands,
                timeout_seconds=timeout_seconds,
                max_iterations=max_iterations,
                timeout_retries=timeout_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                silence_timeout_seconds=silence_timeout_seconds,
                silence_grace_seconds=silence_grace_seconds,
                sandbox_mode=sandbox_mode,
                model=model,
                debug_file_path=codex_debug_log_path,
                live_log_path=conversation_live_log_path,
                max_bash_calls=max_bash_calls,
                resume_on_retry=resume_on_retry,
            )
        except asyncio.TimeoutError as e:
            return self._build_timeout_result(
                str(e),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=codex_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except BashToolLimitExceeded as e:
            return self._build_error_result(
                f"Codex Bash tool call limit exceeded: observed={e.observed}, limit={e.limit}",
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=codex_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except FileNotFoundError:
            return self._build_error_result(
                append_executor_hints(
                    f"Codex CLI binary not found: {self._codex_binary}. "
                    "Install with: npm install -g @openai/codex"
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=codex_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except Exception as e:
            return self._build_error_result(
                append_executor_hints(f"Codex CLI invocation failed: {e}"),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=codex_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )

        # ========== 6. 解析输出 ==========
        parsed = self._parse_codex_output(raw_output)

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
            "debug_log_path": codex_debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": parsed.get("result_text", ""),
            "error": append_executor_hints(parsed.get("error")),
            "cost_usd": parsed.get("cost_usd", 0),
            "tokens_used": parsed.get("tokens_used", 0),
            "thread_id": parsed.get("thread_id", ""),
        }

    # ================================================================
    # 内部方法 - Codex CLI 调用
    # ================================================================

    async def _invoke_codex(
        self,
        prompt: str,
        system_prompt: str,
        workspace: str,
        allowed_commands: List[str],
        timeout_seconds: int,
        max_iterations: int,
        timeout_retries: int = DEFAULT_TIMEOUT_RETRIES,
        retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
        silence_timeout_seconds: int = DEFAULT_SILENCE_TIMEOUT_SECONDS,
        silence_grace_seconds: int = DEFAULT_SILENCE_GRACE_SECONDS,
        sandbox_mode: str = DEFAULT_SANDBOX_MODE,
        model: str = "",
        debug_file_path: str = "",
        live_log_path: str = "",
        max_bash_calls: int = DEFAULT_MAX_BASH_CALLS,
        resume_on_retry: bool = DEFAULT_RESUME_ON_RETRY,
    ) -> str:
        """
        调用 codex CLI (exec 子命令)

        使用 --json 获取 JSONL 输出。
        工作目录通过 subprocess cwd 参数控制。
        prompt 通过 stdin 传入以避免 shell 转义问题。
        """
        base_cmd = [
            self._codex_binary,
            "exec",           # 非交互模式
            "--json",         # JSONL 输出
            "--color", "never",
            "--sandbox", sandbox_mode,
        ]

        # 指定模型
        if model:
            base_cmd.extend(["--model", model])

        # 构建完整 prompt（包含 system prompt）
        full_prompt = f"{system_prompt}\n\n## Task\n\n{prompt}"

        last_timeout_error: Optional[Exception] = None
        total_attempts = max(timeout_retries, 0) + 1

        for attempt_idx in range(total_attempts):
            cancel_event = threading.Event()
            attempt_cmd = list(base_cmd)

            # Codex CLI 的会话恢复机制暂不支持 exec 子命令
            # 因此我们在 prompt 中注入重试指令
            attempt_prompt = full_prompt
            if attempt_idx > 0 and resume_on_retry:
                attempt_prompt = self._build_retry_prompt(attempt_idx, total_attempts, full_prompt)

            try:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self._run_subprocess,
                        attempt_cmd,
                        workspace,
                        timeout_seconds,
                        attempt_prompt,
                        live_log_path,
                        debug_file_path,
                        cancel_event,
                        silence_timeout_seconds,
                        silence_grace_seconds,
                    ),
                    timeout=timeout_seconds + 30,  # 额外 30s buffer
                )
                return result
            except BashToolLimitExceeded:
                cancel_event.set()
                raise
            except asyncio.CancelledError:
                cancel_event.set()
                logger.warning(
                    "Codex invoke cancelled (attempt %s/%s)",
                    attempt_idx + 1,
                    total_attempts,
                )
                raise
            except asyncio.TimeoutError as e:
                cancel_event.set()
                last_timeout_error = e
                logger.warning(
                    "Codex invoke timed out (attempt %s/%s)",
                    attempt_idx + 1,
                    total_attempts,
                )
                if attempt_idx >= total_attempts - 1:
                    break
                if live_log_path and resume_on_retry:
                    self._append_live_log_meta(
                        live_log_path,
                        f"retrying (next_attempt={attempt_idx + 2}/{total_attempts})",
                    )
                backoff_seconds = max(retry_backoff_seconds, 0) * (2 ** attempt_idx)
                if backoff_seconds > 0:
                    await asyncio.sleep(backoff_seconds)

        reason = str(last_timeout_error).strip() if last_timeout_error else "timeout"
        raise asyncio.TimeoutError(
            f"subprocess timed out after {timeout_seconds}s, attempts={total_attempts}, "
            f"last_error={reason}"
        ) from last_timeout_error

    def _run_subprocess(
        self,
        cmd: List[str],
        cwd: str,
        timeout: int,
        stdin_text: str = "",
        live_log_path: str = "",
        debug_file_path: str = "",
        cancel_event: Optional[threading.Event] = None,
        silence_timeout_seconds: int = DEFAULT_SILENCE_TIMEOUT_SECONDS,
        silence_grace_seconds: int = DEFAULT_SILENCE_GRACE_SECONDS,
    ) -> str:
        """同步执行 subprocess（在线程池中调用，实时监控输出）"""
        process: Optional[subprocess.Popen] = None
        stdout_lines: List[str] = []
        stderr_lines: List[str] = []
        log_queue: "queue.Queue[tuple[str, str]]" = queue.Queue()
        reader_threads: List[threading.Thread] = []

        def _reader(
            stream: Optional[Any],
            channel: str,
            collector: List[str],
        ) -> None:
            if stream is None:
                return
            try:
                for line in iter(stream.readline, ""):
                    collector.append(line)
                    log_queue.put((channel, line.rstrip("\n")))
            finally:
                try:
                    stream.close()
                except Exception:
                    pass

        def _append_meta(message: str) -> None:
            if not live_log_path:
                return
            try:
                with open(live_log_path, "a", encoding="utf-8") as f:
                    f.write(f"[{datetime.now().isoformat()}][meta] {message}\n")
            except OSError:
                pass

        def _drain_log_queue() -> int:
            drained = 0
            while True:
                try:
                    channel, line = log_queue.get_nowait()
                except queue.Empty:
                    return drained
                drained += 1
                compact_line = line if len(line) <= 500 else f"{line[:500]}..."
                logger.info("[codex:%s] %s", channel, compact_line)
                if live_log_path:
                    try:
                        with open(live_log_path, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now().isoformat()}][{channel}] {line}\n")
                    except OSError:
                        pass

        try:
            env = self._build_subprocess_env()

            _append_meta(f"cmd={' '.join(cmd)}")
            _append_meta(f"cwd={cwd}")
            _append_meta(f"timeout={timeout}")
            _append_meta(f"silence_timeout={silence_timeout_seconds}")
            _append_meta(f"stdin_prompt_chars={len(stdin_text)}")

            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=cwd,
                env=env,
                text=True,
                bufsize=1,
                start_new_session=True,
            )
            _append_meta(f"pid={process.pid}")

            stdout_thread = threading.Thread(
                target=_reader,
                args=(process.stdout, "stdout", stdout_lines),
                daemon=True,
            )
            stderr_thread = threading.Thread(
                target=_reader,
                args=(process.stderr, "stderr", stderr_lines),
                daemon=True,
            )
            stdout_thread.start()
            stderr_thread.start()
            reader_threads.extend([stdout_thread, stderr_thread])

            if process.stdin:
                if stdin_text:
                    process.stdin.write(stdin_text)
                process.stdin.close()

            start_ts = time.monotonic()
            last_output_ts = start_ts
            last_heartbeat_ts = start_ts
            heartbeat_interval = float(self.DEFAULT_HEARTBEAT_SECONDS)

            while True:
                drained = _drain_log_queue()
                now_ts = time.monotonic()
                if drained > 0:
                    last_output_ts = now_ts

                if now_ts - last_heartbeat_ts >= heartbeat_interval:
                    last_activity_ts = last_output_ts
                    silent_for = int(now_ts - last_activity_ts)
                    elapsed = int(now_ts - start_ts)
                    _append_meta(
                        f"heartbeat elapsed={elapsed}s "
                        f"silent_for={silent_for}s "
                        f"stdout_lines={len(stdout_lines)} "
                        f"stderr_lines={len(stderr_lines)}"
                    )
                    last_heartbeat_ts = now_ts

                if process.poll() is not None:
                    break
                if cancel_event is not None and cancel_event.is_set():
                    _append_meta("cancellation requested; terminating subprocess")
                    raise asyncio.TimeoutError("subprocess cancelled by caller")
                if (
                    silence_timeout_seconds > 0
                    and now_ts - start_ts >= silence_grace_seconds
                ):
                    last_activity_ts = last_output_ts
                    silent_for = now_ts - last_activity_ts
                    if silent_for > silence_timeout_seconds:
                        _append_meta(
                            "silence timeout reached "
                            f"(silent_for={int(silent_for)}s, limit={silence_timeout_seconds}s)"
                        )
                        raise asyncio.TimeoutError(
                            f"subprocess stalled with no output "
                            f"for {int(silent_for)}s (limit={silence_timeout_seconds}s)"
                        )
                if now_ts - start_ts > timeout:
                    _append_meta(f"timeout reached ({timeout}s)")
                    raise asyncio.TimeoutError(
                        f"subprocess timed out after {timeout}s"
                    )
                time.sleep(0.2)

            process.wait(timeout=5)
            for t in reader_threads:
                t.join(timeout=1)
            _drain_log_queue()

            output = "".join(stdout_lines)
            stderr_output = "".join(stderr_lines)
            if stderr_output:
                output += f"\n--- stderr ---\n{stderr_output}"
            return output
        except subprocess.TimeoutExpired as e:
            raise asyncio.TimeoutError(
                f"subprocess timed out after {timeout}s"
            ) from e
        finally:
            if process and process.poll() is None:
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    else:
                        process.kill()
                except Exception:
                    pass
            for t in reader_threads:
                t.join(timeout=1)

    def _load_codex_env_settings(self) -> Dict[str, str]:
        """构建 subprocess 额外环境变量"""
        extra: Dict[str, str] = {}

        # 优先使用 Codex 专属环境变量，避免被仓库内 .env 的通用 OpenAI
        # 兼容层配置污染到底层 Codex CLI。
        for var in ("CODEX_API_KEY", "CODEX_HOME"):
            val = os.getenv(var)
            if val:
                extra[var] = val

        return extra

    @staticmethod
    def _has_local_auth_file() -> bool:
        codex_home = Path(
            os.getenv("CODEX_HOME") or (Path.home() / ".codex")
        )
        return (codex_home / "auth.json").exists()

    def _build_subprocess_env(self) -> Dict[str, str]:
        env = {
            **os.environ,
            **self._extra_env,
            "CODEX_ENTRYPOINT": "lee-executor",
        }
        if self._prefer_local_auth and not env.get("CODEX_API_KEY"):
            for var in (
                "OPENAI_API_KEY",
                "OPENAI_BASE_URL",
                "OPENAI_API_BASE",
                "OPENAI_MODEL",
            ):
                env.pop(var, None)
        return env

    @staticmethod
    def _resolve_binary(binary_name: str) -> str:
        """
        解析可执行文件路径。

        Windows 上优先传递解析后的 .cmd/.bat 包装器路径，避免 CreateProcess
        将裸命令解析到 WindowsApps 中不可直接启动的 App Execution Alias。
        """
        candidate = str(binary_name or "codex").strip() or "codex"
        direct = shutil.which(candidate)
        if direct:
            return direct
        if os.name == "nt" and "." not in Path(candidate).name:
            for suffix in (".cmd", ".bat", ".exe", ".ps1"):
                resolved = shutil.which(f"{candidate}{suffix}")
                if resolved:
                    return resolved
        return candidate

    # ================================================================
    # 内部方法 - 输出解析
    # ================================================================

    def _parse_codex_output(self, raw_output: str) -> Dict[str, Any]:
        """
        解析 codex CLI JSONL 输出

        JSONL 格式示例：
        {"type":"thread.started","thread_id":"..."}
        {"type":"turn.started"}
        {"type":"item.completed","item":{...}}
        {"type":"turn.completed","usage":{...}}
        """
        parsed: Dict[str, Any] = {
            "result_text": "",
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "iterations_used": 1,
            "error": None,
            "thread_id": "",
            "tokens_used": 0,
            "cost_usd": 0.0,
        }

        # 分离 stdout 和 stderr
        parts = raw_output.split("\n--- stderr ---\n")
        main_output = parts[0]

        # 解析 JSONL 事件
        items = []
        usage = {}
        fatal_error_messages: List[str] = []
        transient_error_messages: List[str] = []
        saw_turn_completed = False
        saw_turn_failed = False

        for line in main_output.strip().split("\n"):
            line = line.strip()
            if not line or not line.startswith("{"):
                continue
            try:
                event = json.loads(line)

                # 提取关键事件
                event_type = event.get("type")
                if event_type == "thread.started":
                    parsed["thread_id"] = event.get("thread_id", "")
                elif event_type == "item.completed":
                    item = event.get("item", {})
                    items.append(item)
                    if item.get("type") == "error" and item.get("message"):
                        transient_error_messages.append(str(item.get("message")))
                elif event_type == "turn.completed":
                    saw_turn_completed = True
                    usage = event.get("usage", {})
                elif event_type == "turn.failed":
                    saw_turn_failed = True
                    error = event.get("error", {})
                    if isinstance(error, dict) and error.get("message"):
                        fatal_error_messages.append(str(error.get("message")))
                elif event_type == "error" and event.get("message"):
                    transient_error_messages.append(str(event.get("message")))

            except json.JSONDecodeError:
                # 跳过无效的 JSON 行
                continue

        # 计算 token 使用和成本
        input_tokens = usage.get("input_tokens", 0)
        cached_tokens = usage.get("cached_input_tokens", 0)
        output_tokens = usage.get("output_tokens", 0)
        parsed["tokens_used"] = input_tokens + output_tokens
        parsed["cost_usd"] = self._calculate_cost(
            self._model or "gpt-4o", input_tokens - cached_tokens, output_tokens
        )

        # 从 items 中提取信息
        for item in items:
            item_type = item.get("type", "")

            if item_type == "agent_message":
                parsed["result_text"] += item.get("text", "")

            elif item_type == "tool_use":
                tool_name = item.get("name", "")
                tool_input = item.get("input", {})

                if tool_name == "shell" or tool_name == "local_shell":
                    cmd = tool_input.get("command", "")
                    if cmd:
                        parsed["commands_run"].append({
                            "cmd": cmd,
                            "exit_code": 0,  # Codex JSONL 不包含 exit code
                            "stdout_tail": "",
                        })
                elif tool_name in ("write_file", "edit_file", "apply_patch"):
                    file_path = tool_input.get("path", "") or tool_input.get("file_path", "")
                    if file_path:
                        parsed["changed_files"].append(file_path)

        # 提取测试结果（从 result_text 中）
        if parsed["result_text"]:
            self._extract_test_results(parsed["result_text"], parsed)

        # 检查错误
        if saw_turn_failed and fatal_error_messages:
            parsed["error"] = "; ".join(
                dict.fromkeys(msg for msg in fatal_error_messages if msg)
            )
        elif not saw_turn_completed:
            combined_errors = fatal_error_messages + transient_error_messages
            if combined_errors:
                parsed["error"] = "; ".join(
                    dict.fromkeys(msg for msg in combined_errors if msg)
                )

        if not parsed["error"] and raw_output and not saw_turn_completed:
            error_patterns = [
                r"^Error:",
                r"^fatal:",
                r"command not found",
            ]
            for pattern in error_patterns:
                matched_line = next(
                    (
                        line.strip()
                        for line in raw_output.splitlines()
                        if re.search(pattern, line, re.IGNORECASE)
                    ),
                    None,
                )
                if matched_line:
                    parsed["error"] = matched_line
                    break

        return parsed

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """根据 token 使用计算成本"""
        pricing = self.PRICING.get(model, self.PRICING.get("gpt-4o", {}))
        input_price = pricing.get("input", 0.01)
        output_price = pricing.get("output", 0.03)
        return (input_tokens / 1000 * input_price +
                output_tokens / 1000 * output_price)

    def _extract_test_results(self, output: str, parsed: Dict[str, Any]):
        """从测试输出中提取 passed/failed 计数"""
        # 匹配 pytest 风格: "5 passed, 1 failed"
        passed_match = re.search(r"(\d+)\s+passed", output)
        failed_match = re.search(r"(\d+)\s+failed", output)
        if passed_match or failed_match:
            parsed["test_results"] = {
                "passed": int(passed_match.group(1)) if passed_match else 0,
                "failed": int(failed_match.group(1)) if failed_match else 0,
            }

    # ================================================================
    # 内部方法 - 辅助函数（复用 Claude Code Executor 的逻辑）
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
                Path(workspace) / ".workflow" / "codex"
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
        max_bash_calls: int,
        stop_conditions: Dict[str, str],
        system_prompt_extra: str,
        structured_output_only: bool = False,
    ) -> str:
        """构建系统 prompt（注入治理约束）"""
        constraints = [
            f"You are running as a controlled executor in the LEE workflow.",
            f"Working directory: {workspace}",
            f"Maximum iterations: {max_iterations}",
        ]

        if max_bash_calls > 0:
            constraints.append(f"Bash tool call limit: {max_bash_calls}")

        if write_scope:
            constraints.append(
                f"Allowed write paths: {', '.join(write_scope)}"
            )
        else:
            constraints.append("Allowed to write any file within workspace")

        if stop_conditions:
            cond_desc = "; ".join(
                f"{k}: {v}" for k, v in stop_conditions.items()
            )
            constraints.append(f"Stop conditions: {cond_desc}")

        constraints_text = "\n".join(f"- {c}" for c in constraints)

        prompt = f"""## Governance Constraints

{constraints_text}
"""

        if structured_output_only:
            prompt += """

## Output Requirements

This run is in structured repair mode.
Return only the final machine-readable JSON object body.
Do not output executor wrapper fields such as status, changed_files, commands_run, test_results, or error.
Do not output prose, headings, code fences, or any extra wrapper."""
        else:
            prompt += """

## Output Requirements

After completing the task, output a JSON code block with the following format:
```json
{
  "status": "success or fail",
  "changed_files": ["list of modified files"],
  "commands_run": [{"cmd": "command", "exit_code": 0}],
  "test_results": {"passed": 0, "failed": 0},
  "error": null
}
```
"""

        if system_prompt_extra:
            prompt += f"\n\n## Additional Constraints\n\n{system_prompt_extra}"

        return prompt

    def _build_user_prompt(
        self, goal: str, context_files: List[str]
    ) -> str:
        """构建用户 prompt"""
        prompt = f"## Task Goal\n\n{goal}"

        if context_files:
            files_list = "\n".join(f"- {f}" for f in context_files)
            prompt += f"\n\n## Context Files\n\nPlease read the following files first:\n{files_list}"

        return prompt

    @staticmethod
    def _build_retry_prompt(
        attempt_idx: int,
        total_attempts: int,
        original_prompt: str,
    ) -> str:
        """Construct retry prompt that asks Codex to continue prior work."""
        return (
            f"Retry attempt {attempt_idx + 1}/{total_attempts}.\n"
            "Continue the previous session from existing progress.\n"
            "Do not restart full repository scan; only finish remaining work.\n"
            "Return only the final required JSON block when done.\n\n"
            f"Original task:\n{original_prompt}"
        )

    @staticmethod
    def _coerce_positive_int(value: Any, default: int) -> int:
        """将输入安全转换为正整数；非法值回退默认值。"""
        try:
            if value is None:
                return default
            ivalue = int(value)
            return ivalue if ivalue > 0 else default
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_non_negative_int(value: Any, default: int) -> int:
        """将输入安全转换为非负整数；非法值回退默认值。"""
        try:
            if value is None:
                return default
            ivalue = int(value)
            return ivalue if ivalue >= 0 else default
        except (TypeError, ValueError):
            return default

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
        # 脱敏：移除敏感数据
        safe_input = {k: v for k, v in input_data.items() if k not in ("token_context", "api_key")}
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
            # 检查是否为 policy violation
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

    # ================================================================
    # 内部方法 - 结果构建
    # ================================================================

    def _build_error_result(
        self,
        error: str,
        evidence_dir: str = "",
        conversation_log_path: str = "",
        debug_log_path: str = "",
        prompt_system_path: str = "",
        prompt_user_path: str = "",
    ) -> Dict[str, Any]:
        """构建错误结果"""
        return {
            "status": "failed",
            "error": error,
            "iterations_used": 0,
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "diff_summary": {"files_changed": 0, "lines_added": 0, "lines_deleted": 0},
            "evidence_bundle_path": evidence_dir,
            "conversation_log_path": conversation_log_path,
            "debug_log_path": debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": "",
            "cost_usd": 0,
            "tokens_used": 0,
            "thread_id": "",
        }

    def _build_timeout_result(
        self,
        error: str,
        evidence_dir: str = "",
        conversation_log_path: str = "",
        debug_log_path: str = "",
        prompt_system_path: str = "",
        prompt_user_path: str = "",
    ) -> Dict[str, Any]:
        """构建超时结果"""
        return {
            "status": "timeout",
            "error": error,
            "iterations_used": 0,
            "changed_files": [],
            "commands_run": [],
            "test_results": {},
            "diff_summary": {"files_changed": 0, "lines_added": 0, "lines_deleted": 0},
            "evidence_bundle_path": evidence_dir,
            "conversation_log_path": conversation_log_path,
            "debug_log_path": debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": "",
            "cost_usd": 0,
            "tokens_used": 0,
            "thread_id": "",
        }

    def _append_live_log_meta(self, live_log_path: str, message: str) -> None:
        """向 live log 追加一行 meta 信息。"""
        if not live_log_path:
            return
        try:
            with open(live_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().isoformat()}][meta] {message}\n")
        except OSError:
            pass

    def _write_prompt_artifacts(
        self,
        prompt_system_path: str,
        prompt_user_path: str,
        system_prompt: str,
        user_prompt: str,
    ) -> None:
        """将 system/user prompt 落盘，便于超时调试。"""
        try:
            Path(prompt_system_path).write_text(system_prompt or "", encoding="utf-8")
        except OSError:
            pass
        try:
            Path(prompt_user_path).write_text(user_prompt or "", encoding="utf-8")
        except OSError:
            pass


def register_codex_executor():
    """
    注册 Codex 执行器到 ExecutorFactory

    使用方式:
        from lee.orchestrator.execution.codex_executor import register_codex_executor
        register_codex_executor()
    """
    from .executors import ExecutorFactory

    ExecutorFactory.register("codex", CodexExecutor)
