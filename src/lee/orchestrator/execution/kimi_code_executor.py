"""
Kimi Code Executor

将 Kimi CLI 封装为 LEE 受控 code executor。

设计目标：
- 复用 ClaudeCodeExecutor 的治理约束、evidence bundle、超时与结果解析能力
- 通过本地 `kimi-cli --print` 调用执行任务
- 不走 LLM profile / Moonshot API 直连路径
"""

from __future__ import annotations

import asyncio
import os
import threading
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .claude_code_executor import BashToolLimitExceeded, ClaudeCodeExecutor
from .error_hints import append_executor_hints


class KimiCodeExecutor(ClaudeCodeExecutor):
    """Kimi CLI 执行器。"""

    DEFAULT_MODEL = ""
    DEFAULT_BINARY = "kimi-cli"

    def __init__(self, **kwargs):
        self._kimi_binary = os.getenv("KIMI_CLI_BINARY", self.DEFAULT_BINARY)
        self._model = (
            kwargs.get("model")
            or os.getenv("KIMI_MODEL", "").strip()
            or self.DEFAULT_MODEL
        )
        self._extra_env = self._load_kimi_env_settings()
        super().__init__(**kwargs)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        validation_error = self._validate_input(input_data)
        if validation_error:
            return self._build_result(
                status="failed",
                error=validation_error,
            )

        goal = input_data["goal"]
        workspace = input_data["workspace"]
        context_files = input_data.get("context_files") or []
        step_workspace = str(input_data.get("step_workspace") or "").strip()

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
        forbidden_read_paths = input_data.get("forbidden_read_paths") or []
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
        evidence_base = input_data.get("evidence_base", "")
        model = str(input_data.get("model") or self._model or "").strip()
        max_bash_calls = self._coerce_non_negative_int(
            input_data.get("max_bash_calls"),
            self.DEFAULT_MAX_BASH_CALLS,
        )
        resume_on_retry = bool(
            input_data.get("resume_on_retry", self.DEFAULT_RESUME_ON_RETRY)
        )

        evidence_dir = self._prepare_evidence_dir(evidence_base, workspace)

        read_only = bool(input_data.get("read_only", False))

        system_prompt = self._build_system_prompt(
            goal=goal,
            workspace=workspace,
            allowed_commands=allowed_commands,
            write_scope=write_scope,
            read_only=read_only,
            forbidden_read_paths=forbidden_read_paths,
            max_iterations=max_iterations,
            max_bash_calls=max_bash_calls,
            stop_conditions=stop_conditions,
            system_prompt_extra=system_prompt_extra,
        )
        user_prompt = self._build_user_prompt(
            goal=goal,
            context_files=context_files,
        )

        conversation_live_log_path = str(evidence_dir / "conversation.live.log")
        kimi_debug_log_path = str(evidence_dir / "kimi-debug.log")
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

        try:
            raw_output = await self._invoke_kimi(
                prompt=user_prompt,
                system_prompt=system_prompt,
                workspace=workspace,
                timeout_seconds=timeout_seconds,
                timeout_retries=timeout_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                silence_timeout_seconds=silence_timeout_seconds,
                silence_grace_seconds=silence_grace_seconds,
                model=model,
                live_log_path=conversation_live_log_path,
                max_bash_calls=max_bash_calls,
                resume_on_retry=resume_on_retry,
            )
        except asyncio.TimeoutError as e:
            detail = str(e).strip() or "timeout"
            recovered = await self._recover_timeout_result(
                workspace=workspace,
                step_workspace=step_workspace,
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=kimi_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
                detail=detail,
            )
            if recovered is not None:
                return recovered
            return self._build_result(
                status="timeout",
                error=(
                    f"Kimi CLI execution timed out after {timeout_seconds}s "
                    f"(retries={timeout_retries}, detail={detail})"
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=kimi_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except BashToolLimitExceeded as e:
            return self._build_result(
                status="failed",
                error=(
                    "Kimi Bash tool call limit exceeded: "
                    f"observed={e.observed}, limit={e.limit}"
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=kimi_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except FileNotFoundError:
            return self._build_result(
                status="failed",
                error=append_executor_hints(
                    f"Kimi CLI binary not found: {self._kimi_binary}. "
                    "Install or configure kimi-cli first."
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=kimi_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except Exception as e:
            return self._build_result(
                status="failed",
                error=append_executor_hints(f"Kimi CLI invocation failed: {e}"),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=kimi_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )

        parsed = self._parse_claude_output(raw_output)
        diff_summary = await self._collect_diff_summary(workspace)
        conversation_log_path = self._write_evidence(
            evidence_dir=evidence_dir,
            raw_output=raw_output,
            parsed=parsed,
            diff_summary=diff_summary,
            input_data=input_data,
        )
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
            "debug_log_path": kimi_debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": parsed.get("result_text", ""),
            "error": append_executor_hints(parsed.get("error")),
        }

    def _prepare_evidence_dir(self, evidence_base: str, workspace: str) -> Path:
        if evidence_base:
            evidence_dir = Path(evidence_base)
        else:
            evidence_dir = (
                Path(workspace) / ".workflow" / "kimi-code" / datetime.now().strftime("%Y%m%d-%H%M%S")
            )
        evidence_dir.mkdir(parents=True, exist_ok=True)
        return evidence_dir

    def _load_kimi_env_settings(self) -> Dict[str, str]:
        extra: Dict[str, str] = {}
        for var in (
            "KIMI_API_KEY",
            "KIMI_MODEL",
            "KIMI_BASE_URL",
            "MOONSHOT_API_KEY",
            "HTTP_PROXY",
            "HTTPS_PROXY",
        ):
            val = os.getenv(var)
            if val:
                extra[var] = val
        return extra

    def _setup_sandbox_home(self, project_root: str) -> Optional[str]:
        return None

    def _build_kimi_command(self, *, model: str = "") -> List[str]:
        command = [
            self._kimi_binary,
            "--print",
            "--output-format",
            "text",
            "--final-message-only",
        ]
        if model:
            command.extend(["--model", model])
        return command

    async def _invoke_kimi(
        self,
        *,
        prompt: str,
        system_prompt: str,
        workspace: str,
        timeout_seconds: int,
        timeout_retries: int,
        retry_backoff_seconds: int,
        silence_timeout_seconds: int,
        silence_grace_seconds: int,
        model: str,
        live_log_path: str,
        max_bash_calls: int,
        resume_on_retry: bool,
    ) -> str:
        base_cmd = self._build_kimi_command(model=model)
        full_prompt = f"{system_prompt}\n\n## Task\n\n{prompt}" if system_prompt else prompt
        last_timeout_error: Optional[Exception] = None
        total_attempts = max(timeout_retries, 0) + 1

        for attempt_idx in range(total_attempts):
            cancel_event = threading.Event()
            attempt_prompt = full_prompt
            if attempt_idx > 0 and resume_on_retry:
                attempt_prompt = (
                    f"{self._build_retry_prompt(attempt_idx, total_attempts)}\n"
                    f"{full_prompt}"
                )
            try:
                loop = asyncio.get_event_loop()
                result = await asyncio.wait_for(
                    loop.run_in_executor(
                        None,
                        self._run_subprocess,
                        list(base_cmd),
                        workspace,
                        timeout_seconds,
                        attempt_prompt,
                        live_log_path,
                        "",
                        cancel_event,
                        silence_timeout_seconds,
                        silence_grace_seconds,
                        max_bash_calls,
                    ),
                    timeout=timeout_seconds + 30,
                )
                return result
            except BashToolLimitExceeded:
                cancel_event.set()
                raise
            except asyncio.CancelledError:
                cancel_event.set()
                raise
            except asyncio.TimeoutError as e:
                cancel_event.set()
                last_timeout_error = e
                if attempt_idx >= total_attempts - 1:
                    break
                backoff_seconds = max(retry_backoff_seconds, 0) * (2 ** attempt_idx)
                if backoff_seconds > 0:
                    await asyncio.sleep(backoff_seconds)

        reason = str(last_timeout_error).strip() if last_timeout_error else "timeout"
        raise asyncio.TimeoutError(
            f"subprocess timed out after {timeout_seconds}s, attempts={total_attempts}, "
            f"last_error={reason}"
        ) from last_timeout_error


def register_kimi_code_executor():
    """注册 Kimi code executor 到 ExecutorFactory。"""
    from .executors import ExecutorFactory

    ExecutorFactory.register("kimi", KimiCodeExecutor)
