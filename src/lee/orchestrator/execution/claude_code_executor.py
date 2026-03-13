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
import logging
import os
import queue
import re
import signal
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
    DEFAULT_TIMEOUT_SECONDS = 3600  # 1 hour for long-running tasks
    DEFAULT_TIMEOUT_RETRIES = 1
    DEFAULT_RETRY_BACKOFF_SECONDS = 5
    DEFAULT_SILENCE_TIMEOUT_SECONDS = 600
    DEFAULT_SILENCE_GRACE_SECONDS = 20
    DEFAULT_STRICT_MCP_CONFIG = True
    DEFAULT_ALLOWED_COMMANDS = ["cat", "ls", "find", "grep"]
    DEFAULT_HEARTBEAT_SECONDS = 5
    DEFAULT_MODEL = "sonnet"
    LEGACY_MODEL_ALIASES = {
        "claude-sonnet-4-6": "sonnet",
        "claude-sonnet-4.6": "sonnet",
    }
    DEFAULT_MAX_BASH_CALLS = 60
    DEFAULT_RESUME_ON_RETRY = True
    BASH_PRE_TOOL_HOOK_PATTERN = re.compile(
        r"executePreToolHooks called for tool:\s*Bash"
    )

    def __init__(self, **kwargs):
        """
        初始化 Claude Code 执行器

        Args:
            **kwargs: 额外参数（保留扩展性）
        """
        self._claude_binary = os.getenv("CLAUDE_CODE_BINARY", "claude")
        self._model = self._normalize_model_name(
            kwargs.get("model")
            or os.getenv("CLAUDE_CODE_MODEL", "").strip()
            or self.DEFAULT_MODEL
        )
        self._extra_env = self._load_claude_env_settings()

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
        read_only = bool(input_data.get("read_only", False))
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
        strict_mcp_config = input_data.get(
            "strict_mcp_config", self.DEFAULT_STRICT_MCP_CONFIG
        )
        setting_sources = input_data.get("setting_sources", "")
        stop_conditions = input_data.get("stop_conditions", {})
        system_prompt_extra = input_data.get("system_prompt_extra", "")
        evidence_base = input_data.get("evidence_base", "")
        model = self._normalize_model_name(input_data.get("model") or self._model or "")
        max_bash_calls = self._coerce_non_negative_int(
            input_data.get("max_bash_calls"),
            self.DEFAULT_MAX_BASH_CALLS,
        )
        resume_on_retry = bool(
            input_data.get("resume_on_retry", self.DEFAULT_RESUME_ON_RETRY)
        )

        # ========== 2. 构建 evidence bundle 目录 ==========
        evidence_dir = self._prepare_evidence_dir(evidence_base, workspace)

        # ========== 3. 构建 system prompt（治理约束注入） ==========
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

        # ========== 4. 构建用户 prompt ==========
        user_prompt = self._build_user_prompt(
            goal=goal,
            context_files=context_files,
        )

        # 调试输出文件（即使失败也可用于排障）
        conversation_live_log_path = str(evidence_dir / "conversation.live.log")
        claude_debug_log_path = str(evidence_dir / "claude-debug.log")
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
        mcp_config_path = input_data.get("mcp_config_path", "")
        if strict_mcp_config and not mcp_config_path:
            mcp_config_path = self._ensure_minimal_mcp_config(evidence_dir)
        self._append_live_log_meta(
            conversation_live_log_path,
            f"mcp_config_path={mcp_config_path or '(none)'}",
        )
        self._append_live_log_meta(
            conversation_live_log_path,
            f"model={model or '(default)'}",
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
                timeout_retries=timeout_retries,
                retry_backoff_seconds=retry_backoff_seconds,
                silence_timeout_seconds=silence_timeout_seconds,
                silence_grace_seconds=silence_grace_seconds,
                strict_mcp_config=strict_mcp_config,
                setting_sources=setting_sources,
                mcp_config_path=mcp_config_path,
                model=model,
                debug_file_path=claude_debug_log_path,
                live_log_path=conversation_live_log_path,
                max_bash_calls=max_bash_calls,
                resume_on_retry=resume_on_retry,
                read_only=read_only,
            )
        except asyncio.TimeoutError as e:
            detail = str(e).strip()
            if not detail:
                detail = "timeout"
            recovered = await self._recover_timeout_result(
                workspace=workspace,
                step_workspace=step_workspace,
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=claude_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
                detail=detail,
            )
            if recovered is not None:
                return recovered
            return self._build_result(
                status="timeout",
                error=(
                    f"Claude Code execution timed out after {timeout_seconds}s "
                    f"(retries={timeout_retries}, detail={detail})"
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=claude_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except BashToolLimitExceeded as e:
            return self._build_result(
                status="failed",
                error=(
                    "Claude Bash tool call limit exceeded: "
                    f"observed={e.observed}, limit={e.limit}"
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=claude_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except FileNotFoundError:
            return self._build_result(
                status="failed",
                error=append_executor_hints(
                    f"Claude CLI binary not found: {self._claude_binary}. "
                    "Install with: npm install -g @anthropic-ai/claude-code"
                ),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=claude_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
            )
        except Exception as e:
            return self._build_result(
                status="failed",
                error=append_executor_hints(f"Claude CLI invocation failed: {e}"),
                evidence_dir=str(evidence_dir),
                conversation_log_path=conversation_live_log_path,
                debug_log_path=claude_debug_log_path,
                prompt_system_path=prompt_system_path,
                prompt_user_path=prompt_user_path,
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
            "debug_log_path": claude_debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": parsed.get("result_text", ""),
            "error": append_executor_hints(parsed.get("error")),
        }

    async def _recover_timeout_result(
        self,
        *,
        workspace: str,
        step_workspace: str,
        evidence_dir: str,
        conversation_log_path: str,
        debug_log_path: str,
        prompt_system_path: str,
        prompt_user_path: str,
        detail: str,
    ) -> Optional[Dict[str, Any]]:
        """Recover success from timeout when step workspace already contains outputs."""
        changed_files = self._collect_step_workspace_files(
            workspace=workspace,
            step_workspace=step_workspace,
        )
        if not changed_files:
            return None
        diff_summary = await self._collect_diff_summary(workspace)
        return {
            "status": "success",
            "iterations_used": 0,
            "changed_files": changed_files,
            "commands_run": [],
            "test_results": {},
            "diff_summary": diff_summary,
            "evidence_bundle_path": evidence_dir,
            "conversation_log_path": conversation_log_path,
            "debug_log_path": debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": "",
            "error": None,
            "recovered_from_timeout": True,
            "recovery_note": (
                "Recovered from timeout using files already written under step workspace "
                f"after executor stalled: {detail}"
            ),
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

    @staticmethod
    def _collect_step_workspace_files(
        *,
        workspace: str,
        step_workspace: str,
    ) -> List[str]:
        step_dir = Path(step_workspace)
        if not step_workspace or not step_dir.exists() or not step_dir.is_dir():
            return []

        workspace_path = Path(workspace).resolve()
        recovered: List[str] = []
        for file_path in sorted(step_dir.rglob("*")):
            if not file_path.is_file():
                continue
            name = file_path.name
            if name == "latest":
                continue
            if name.endswith(".tmp") or ".tmp." in name:
                continue
            resolved = file_path.resolve()
            try:
                recovered.append(str(resolved.relative_to(workspace_path)))
            except ValueError:
                recovered.append(str(resolved))
        return recovered

    def _build_system_prompt(
        self,
        goal: str,
        workspace: str,
        allowed_commands: List[str],
        write_scope: List[str],
        read_only: bool,
        forbidden_read_paths: List[str],
        max_iterations: int,
        max_bash_calls: int,
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
        if max_bash_calls > 0:
            constraints.append(f"Bash 工具调用上限: {max_bash_calls}")

        if read_only:
            constraints.append("只读模式: 禁止使用 Write/Edit/MultiEdit 修改任何文件")
        elif write_scope:
            constraints.append(
                f"允许写入的路径: {', '.join(write_scope)}"
            )
        else:
            constraints.append("允许写入工作目录内的任何文件")

        if forbidden_read_paths:
            constraints.append(
                f"禁止读取或引用的路径: {', '.join(forbidden_read_paths)}"
            )
            constraints.append(
                "这些路径中的文件不能作为需求事实源、示例源、回填源或 ID/标题参考源"
            )

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
```

重要提示 (BUG-2026-0061):
- 任务完成后立即退出：完成任务后请立即输出 JSON 结果，不要进行额外的检查或验证操作。
- 避免重复操作：不要重复执行已经成功的命令。
- 在执行过程中完成验证：如果需要验证文件存在，请在任务执行过程中完成。
- 提前退出是成功的：任务已完成时输出成功并退出是正确的行为。
- 只允许把当前 workspace 和显式提供的 context_files 当作权威输入；不要扫描仓库寻找相似的 EPIC、FEAT、SRC、ADR。
- 不要读取或引用任何历史运行目录、历史证据目录或历史输出目录中的文件来替代当前输入。"""

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
        timeout_retries: int = DEFAULT_TIMEOUT_RETRIES,
        retry_backoff_seconds: int = DEFAULT_RETRY_BACKOFF_SECONDS,
        silence_timeout_seconds: int = DEFAULT_SILENCE_TIMEOUT_SECONDS,
        silence_grace_seconds: int = DEFAULT_SILENCE_GRACE_SECONDS,
        strict_mcp_config: bool = DEFAULT_STRICT_MCP_CONFIG,
        setting_sources: str = "",
        mcp_config_path: str = "",
        model: str = "",
        debug_file_path: str = "",
        live_log_path: str = "",
        max_bash_calls: int = DEFAULT_MAX_BASH_CALLS,
        resume_on_retry: bool = DEFAULT_RESUME_ON_RETRY,
        read_only: bool = False,
    ) -> str:
        """
        调用 claude CLI (v2.x)

        使用 --print 模式获取完整输出。
        工作目录通过 subprocess cwd 参数控制。
        prompt 通过 stdin 传入以避免 shell 转义问题。
        """
        base_cmd = [
            self._claude_binary,
            "--print",
            "--output-format", "json",
        ]

        # 记录 claude CLI 原生日志，便于定位网络/鉴权/连接问题
        if debug_file_path:
            base_cmd.extend(["--debug-file", debug_file_path])

        if setting_sources:
            base_cmd.extend(["--setting-sources", setting_sources])

        # 仅使用显式 MCP 配置（默认无配置），避免本地全局 MCP 干扰执行稳定性
        if strict_mcp_config:
            base_cmd.append("--strict-mcp-config")
            if mcp_config_path:
                base_cmd.extend(["--mcp-config", mcp_config_path])

        # 指定模型（显式传入优先，未传则使用初始化默认）
        if model:
            base_cmd.extend(["--model", model])

        # 注入系统 prompt
        if system_prompt:
            base_cmd.extend(["--system-prompt", system_prompt])

        # 构建工具白名单
        # claude CLI --allowedTools 接受空格/逗号分隔的工具名
        allowed_tools = self._build_allowed_tools(
            allowed_commands=allowed_commands,
            read_only=read_only,
        )

        base_cmd.extend(["--allowedTools", ",".join(allowed_tools)])

        # prompt 通过 stdin 传入（避免命令行参数过长或转义问题）

        last_timeout_error: Optional[Exception] = None
        total_attempts = max(timeout_retries, 0) + 1
        retry_session_id = str(uuid.uuid4())

        for attempt_idx in range(total_attempts):
            cancel_event = threading.Event()
            attempt_cmd = list(base_cmd)
            attempt_prompt = prompt
            if resume_on_retry:
                if attempt_idx == 0:
                    attempt_cmd.extend(["--session-id", retry_session_id])
                else:
                    attempt_cmd.extend(["--resume", retry_session_id])
                    attempt_prompt = self._build_retry_prompt(attempt_idx, total_attempts)
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
                        max_bash_calls,
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
                    "Claude invoke cancelled (attempt %s/%s); sent cancellation signal to subprocess",
                    attempt_idx + 1,
                    total_attempts,
                )
                raise
            except asyncio.TimeoutError as e:
                cancel_event.set()
                last_timeout_error = e
                logger.warning(
                    "Claude invoke timed out (attempt %s/%s, timeout=%ss): %s",
                    attempt_idx + 1,
                    total_attempts,
                    timeout_seconds,
                    str(e) or "timeout",
                )
                if attempt_idx >= total_attempts - 1:
                    break
                if live_log_path and resume_on_retry:
                    self._append_live_log_meta(
                        live_log_path,
                        (
                            "retrying with session resume "
                            f"(session_id={retry_session_id}, next_attempt={attempt_idx + 2}/{total_attempts})"
                        ),
                    )
                backoff_seconds = max(retry_backoff_seconds, 0) * (2 ** attempt_idx)
                if backoff_seconds > 0:
                    await asyncio.sleep(backoff_seconds)

        reason = str(last_timeout_error).strip() if last_timeout_error else "timeout"
        raise asyncio.TimeoutError(
            f"subprocess timed out after {timeout_seconds}s, attempts={total_attempts}, "
            f"last_error={reason}"
        ) from last_timeout_error

    def _ensure_minimal_mcp_config(self, evidence_dir: Path) -> str:
        """
        生成最小 MCP 配置文件，确保 strict 模式下不加载额外 MCP 服务器。
        """
        config_path = evidence_dir / "mcp-config.minimal.json"
        if config_path.exists():
            return str(config_path)
        payload = {"mcpServers": {}}
        config_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return str(config_path)

    def _load_claude_env_settings(self) -> Dict[str, str]:
        """
        构建 subprocess 额外环境变量

        优先级:
        1. 显式环境变量 (ANTHROPIC_API_KEY, ANTHROPIC_BASE_URL)
        2. ~/.claude/settings.json 中的 env 配置 (HTTP_PROXY 等)
        """
        extra: Dict[str, str] = {}

        # 从 settings.json 读取 (HTTP_PROXY 等)
        settings_path = Path.home() / ".claude" / "settings.json"
        if settings_path.exists():
            try:
                data = json.loads(settings_path.read_text())
                extra.update(data.get("env", {}))
            except (json.JSONDecodeError, OSError):
                pass

        # 传递 API Key 和 Base URL（支持 GLM5 等非 Anthropic 后端）
        for var in ("ANTHROPIC_API_KEY", "ANTHROPIC_BASE_URL"):
            val = os.getenv(var)
            if val:
                extra[var] = val

        return extra

    @classmethod
    def _normalize_model_name(cls, model: Any) -> str:
        normalized = str(model or "").strip()
        if not normalized:
            return cls.DEFAULT_MODEL
        rewritten = cls.LEGACY_MODEL_ALIASES.get(normalized.lower(), normalized)
        if rewritten != normalized:
            logger.warning(
                "Normalizing unsupported Claude model alias '%s' -> '%s'",
                normalized,
                rewritten,
            )
        return rewritten

    def _setup_sandbox_home(self, project_root: str) -> Optional[str]:
        """
        检测是否需要沙箱 HOME 环境

        当 Claude CLI 在沙箱中运行时（如 Antigravity agent），
        无法写入 ~/.claude/debug/ 等目录。此方法在项目目录下
        创建一个可写的 .claude-sandbox/ 作为 HOME 替代。

        Returns:
            沙箱 HOME 目录路径，如果不需要返回 None
        """
        # 仅当设置了 API Key（绕过 OAuth）时才启用沙箱 HOME
        if not self._extra_env.get("ANTHROPIC_API_KEY"):
            return None

        claude_dir = Path.home() / ".claude"
        if not claude_dir.exists():
            return None

        # 尝试检测是否需要沙箱（无法写入 debug 目录）
        test_dir = claude_dir / "debug"
        try:
            test_dir.mkdir(exist_ok=True)
            test_file = test_dir / ".sandbox_test"
            test_file.write_text("test")
            test_file.unlink()
            return None  # 可以正常写入，不需要沙箱
        except OSError:
            pass  # EPERM — 需要沙箱

        # 创建沙箱 HOME 目录
        sandbox_home = Path(project_root) / ".claude-sandbox"
        sandbox_claude = sandbox_home / ".claude"
        sandbox_claude.mkdir(parents=True, exist_ok=True)

        # 复制必要的配置文件
        src_settings = claude_dir / "settings.json"
        if src_settings.exists():
            dst = sandbox_claude / "settings.json"
            if not dst.exists():
                try:
                    import shutil
                    shutil.copy2(src_settings, dst)
                except OSError:
                    pass

        # 复制 .claude.json（用户偏好，不含 OAuth token）
        src_config = Path.home() / ".claude.json"
        dst_config = sandbox_home / ".claude.json"
        if src_config.exists() and not dst_config.exists():
            try:
                import shutil
                shutil.copy2(src_config, dst_config)
            except OSError:
                pass

        return str(sandbox_home)

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
        max_bash_calls: int = DEFAULT_MAX_BASH_CALLS,
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
                logger.info("[claude:%s] %s", channel, compact_line)
                if live_log_path:
                    try:
                        with open(live_log_path, "a", encoding="utf-8") as f:
                            f.write(f"[{datetime.now().isoformat()}][{channel}] {line}\n")
                    except OSError:
                        pass

        try:
            # 构建 env: 当前环境 + Claude settings.json env + entrypoint
            env = {
                **os.environ,
                **self._extra_env,
                "CLAUDE_CODE_ENTRYPOINT": "lee-executor",
            }

            # 沙箱 HOME 重定向（规避 sandbox EPERM）
            sandbox_home = self._setup_sandbox_home(cwd)
            if sandbox_home:
                env["HOME"] = sandbox_home

            # Repo 管理 — 注入 repo 环境变量
            # 当通过 RepoRegistry 调用时，input_data.repo_id 会被上层设置
            # 这里通过 env 传递给 claude CLI 的 agent 感知
            if os.getenv("LEE_REPO_ID"):
                env["LEE_REPO_ID"] = os.getenv("LEE_REPO_ID")
            if os.getenv("LEE_WORKDIR"):
                env["LEE_WORKDIR"] = os.getenv("LEE_WORKDIR")
            if os.getenv("LEE_REPO_ROOT_EXPECTED"):
                env["LEE_REPO_ROOT_EXPECTED"] = os.getenv("LEE_REPO_ROOT_EXPECTED")

            _append_meta(f"cmd={' '.join(cmd)}")
            _append_meta(f"cwd={cwd}")
            _append_meta(f"timeout={timeout}")
            _append_meta(f"silence_timeout={silence_timeout_seconds}")
            _append_meta(f"silence_grace={silence_grace_seconds}")
            _append_meta(f"max_bash_calls={max_bash_calls}")
            _append_meta(
                f"silence_activity_source={'debug_log' if debug_file_path else 'stdout_stderr'}"
            )
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
            last_debug_growth_ts = start_ts
            last_heartbeat_ts = start_ts
            heartbeat_interval = float(self.DEFAULT_HEARTBEAT_SECONDS)
            last_debug_size = 0
            debug_read_offset = 0
            bash_tool_calls = 0
            if debug_file_path:
                try:
                    last_debug_size = Path(debug_file_path).stat().st_size
                    debug_read_offset = last_debug_size
                except OSError:
                    last_debug_size = 0
                    debug_read_offset = 0
            while True:
                drained = _drain_log_queue()
                now_ts = time.monotonic()
                if drained > 0:
                    last_output_ts = now_ts

                current_debug_size = last_debug_size
                if debug_file_path:
                    try:
                        current_debug_size = Path(debug_file_path).stat().st_size
                    except OSError:
                        current_debug_size = last_debug_size
                if current_debug_size > last_debug_size:
                    last_debug_growth_ts = now_ts
                    last_debug_size = current_debug_size
                if (
                    debug_file_path
                    and max_bash_calls > 0
                    and current_debug_size >= debug_read_offset
                ):
                    debug_read_offset, new_bash_calls = self._scan_bash_calls_from_debug_log(
                        debug_file_path,
                        debug_read_offset,
                    )
                    if new_bash_calls > 0:
                        bash_tool_calls += new_bash_calls
                        _append_meta(
                            f"bash_tool_calls={bash_tool_calls}/{max_bash_calls}"
                        )
                        if bash_tool_calls > max_bash_calls:
                            _append_meta(
                                "bash_tool_call_limit_reached "
                                f"(observed={bash_tool_calls}, limit={max_bash_calls})"
                            )
                            raise BashToolLimitExceeded(
                                limit=max_bash_calls,
                                observed=bash_tool_calls,
                            )

                if now_ts - last_heartbeat_ts >= heartbeat_interval:
                    if debug_file_path:
                        # Prefer Claude debug file activity as source-of-truth when available.
                        last_activity_ts = last_debug_growth_ts
                    else:
                        last_activity_ts = last_output_ts
                    silent_for = int(now_ts - last_activity_ts)
                    elapsed = int(now_ts - start_ts)
                    _append_meta(
                        f"heartbeat elapsed={elapsed}s "
                        f"silent_for={silent_for}s "
                        f"stdout_lines={len(stdout_lines)} "
                        f"stderr_lines={len(stderr_lines)} "
                        f"debug_log_bytes={last_debug_size}"
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
                    if debug_file_path:
                        last_activity_ts = last_debug_growth_ts
                    else:
                        last_activity_ts = last_output_ts
                    silent_for = now_ts - last_activity_ts
                    if silent_for > silence_timeout_seconds:
                        _append_meta(
                            "silence timeout reached "
                            f"(silent_for={int(silent_for)}s, limit={silence_timeout_seconds}s)"
                        )
                        raise asyncio.TimeoutError(
                            "subprocess stalled with no output/debug activity "
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
                        os.killpg(process.pid, signal.SIGKILL)
                    else:
                        process.kill()
                except Exception:
                    pass
            for t in reader_threads:
                t.join(timeout=1)

    @classmethod
    def _scan_bash_calls_from_debug_log(
        cls,
        debug_file_path: str,
        offset: int,
    ) -> tuple[int, int]:
        """Read appended debug log chunk and count new Bash pre-tool hook calls."""
        debug_path = Path(debug_file_path)
        if not debug_path.exists():
            return offset, 0
        try:
            with debug_path.open("r", encoding="utf-8", errors="ignore") as f:
                f.seek(max(offset, 0))
                chunk = f.read()
                new_offset = f.tell()
        except OSError:
            return offset, 0
        if not chunk:
            return new_offset, 0
        return new_offset, len(cls.BASH_PRE_TOOL_HOOK_PATTERN.findall(chunk))

    @staticmethod
    def _build_retry_prompt(
        attempt_idx: int,
        total_attempts: int,
    ) -> str:
        """Construct retry prompt that asks Claude to continue prior work."""
        return (
            f"Retry attempt {attempt_idx + 1}/{total_attempts}.\n"
            "Continue the previous session from existing progress.\n"
            "Do not restart full repository scan; only finish remaining work.\n"
            "Return only the final required JSON block when done.\n"
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

        # 3. 如果仍然没有检测到错误，检查 result_text 中的错误模式
        if not parsed["error"] and raw_output:
            error_patterns = [
                r"^Error:",  # 以 "Error:" 开头
                r"^fatal:",  # 以 "fatal:" 开头
                r"cannot be launched",  # 嵌套会话错误
                r"Nested sessions",  # 嵌套会话错误
                r"command not found",  # 命令未找到
            ]

            import re
            for pattern in error_patterns:
                if re.search(pattern, raw_output, re.MULTILINE | re.IGNORECASE):
                    # 提取第一行作为错误摘要
                    lines = raw_output.split('\n')
                    for line in lines:
                        line = line.strip()
                        if line:
                            parsed["error"] = line
                            break
                    break

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
            "stop_reason": data.get("stop_reason", ""),
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

        # 检测 result_text 中的错误信息
        # 有些情况下 Claude CLI 不会设置 is_error=True，但 result 中包含错误
        if result_text and not parsed["error"]:
            # 检查常见的错误模式
            error_patterns = [
                r"^Error:",  # 以 "Error:" 开头
                r"^fatal:",  # 以 "fatal:" 开头
                r"cannot be launched",  # 嵌套会话错误
                r"Nested sessions",  # 嵌套会话错误
                r"command not found",  # 命令未找到
            ]

            import re
            for pattern in error_patterns:
                if re.search(pattern, result_text, re.MULTILINE | re.IGNORECASE):
                    # 提取第一行作为错误摘要
                    first_line = result_text.split('\n')[0].strip()
                    parsed["error"] = first_line
                    break

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
            "stop_reason": "",
        }

        changed_files_set = set()
        commands_run = []
        result_texts = []

        for msg in messages:
            msg_type = msg.get("type", "")

            # result 类型消息（最终结果）
            if msg_type == "result":
                parsed["iterations_used"] = msg.get("num_turns", 1)
                parsed["stop_reason"] = msg.get("stop_reason", "") or parsed.get("stop_reason", "")
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

    @staticmethod
    def _build_allowed_tools(
        *, allowed_commands: List[str], read_only: bool
    ) -> List[str]:
        allowed_tools = ["Read"]
        if not read_only:
            allowed_tools.extend(["Write", "Edit", "MultiEdit"])
        if allowed_commands:
            allowed_tools.append("Bash")
        return allowed_tools

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

        stop_reason = str(parsed.get("stop_reason") or "").strip().lower()
        result_text = str(parsed.get("result_text") or "").strip()
        if stop_reason == "tool_use" and not result_text:
            return "fail"

        return "success"

    def _build_result(
        self,
        status: str,
        error: str,
        evidence_dir: str = "",
        conversation_log_path: str = "",
        debug_log_path: str = "",
        prompt_system_path: str = "",
        prompt_user_path: str = "",
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
            "conversation_log_path": conversation_log_path,
            "debug_log_path": debug_log_path,
            "prompt_system_path": prompt_system_path,
            "prompt_user_path": prompt_user_path,
            "generated_text": "",
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


def register_claude_code_executor():
    """
    注册 Claude Code 执行器到 ExecutorFactory

    使用方式:
        from lee.orchestrator.execution.claude_code_executor import register_claude_code_executor
        register_claude_code_executor()
    """
    from .executors import ExecutorFactory

    ExecutorFactory.register("claude_code", ClaudeCodeExecutor)
