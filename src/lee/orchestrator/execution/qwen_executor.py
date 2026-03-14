"""
Qwen Executor

将 qwen CLI 无头模式封装为 LEE 通用执行器。
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .error_hints import append_executor_hints
from .executors import BaseExecutor


class QwenExecutor(BaseExecutor):
    DEFAULT_BINARY = "qwen"
    DEFAULT_TIMEOUT_SECONDS = 300
    DEFAULT_OUTPUT_FORMAT = "json"
    DEFAULT_APPROVAL_MODE = "default"
    INVALID_REPLY_MARKERS = (
        "请告诉我您需要",
        "请告诉我你需要",
        "请问您需要我",
        "请问你需要我",
        "我可以帮助您",
        "我可以帮助你",
        "我是产品目标分析师",
        "我是 qwen code",
        "我是qwen code",
        "我是你的助手",
        "请描述您需要",
        "请描述你需要",
        "请提供",
        "有什么需要我帮助",
    )
    PLACEHOLDER_VALUE_MARKERS = (
        "待确认",
        "待补充",
        "待完善",
        "待定",
        "未提供",
        "unknown",
        "tbd",
        "to be confirmed",
        "to be determined",
    )

    def __init__(self, **kwargs):
        self._qwen_binary = self._resolve_binary(
            os.getenv("QWEN_CLI_BINARY", self.DEFAULT_BINARY)
        )
        self._model = str(kwargs.get("model") or os.getenv("QWEN_MODEL", "")).strip()

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        prompt = self._build_prompt(input_data)
        if not prompt:
            return self._build_failed_result("Missing required field: prompt")

        workspace = str(input_data.get("workspace") or os.getcwd())
        timeout_seconds = self._coerce_timeout(input_data.get("timeout_seconds"))
        output_format = str(
            input_data.get("output_format")
            or os.getenv("QWEN_OUTPUT_FORMAT", self.DEFAULT_OUTPUT_FORMAT)
        ).strip() or self.DEFAULT_OUTPUT_FORMAT
        stream = output_format == "stream-json"
        approval_mode = self._coerce_approval_mode(
            input_data.get("approval_mode") or os.getenv("QWEN_APPROVAL_MODE", "")
        )
        include_directories = self._coerce_include_directories(
            input_data.get("include_directories")
            or os.getenv("QWEN_INCLUDE_DIRECTORIES", "")
        )
        all_files = self._coerce_bool(
            input_data.get("all_files"),
            default=self._coerce_bool(os.getenv("QWEN_ALL_FILES", ""), default=False),
        )
        yolo = self._coerce_bool(
            input_data.get("yolo"),
            default=self._coerce_bool(os.getenv("QWEN_YOLO", ""), default=False),
        )
        evidence_dir = self._prepare_evidence_dir(
            str(input_data.get("evidence_base") or ""),
            workspace,
        )

        attempts = self._build_attempt_plan(output_format)
        raw_output = ""
        parsed: Dict[str, Any] = {}
        last_error: Optional[Exception] = None
        for attempt in attempts:
            try:
                raw_output = await self._invoke_qwen(
                    prompt=prompt,
                    workspace=workspace,
                    timeout_seconds=timeout_seconds,
                    output_format=attempt["output_format"],
                    stream=attempt["output_format"] == "stream-json",
                    approval_mode=approval_mode,
                    include_directories=include_directories,
                    all_files=all_files,
                    yolo=yolo,
                    prompt_transport=attempt["transport"],
                )
            except asyncio.TimeoutError as exc:
                last_error = exc
                continue
            except FileNotFoundError:
                return self._build_failed_result(
                    append_executor_hints(
                        f"Qwen CLI binary not found: {self._qwen_binary}. "
                        "Install qwen CLI or set QWEN_CLI_BINARY."
                    ),
                    evidence_dir=str(evidence_dir),
                )
            except Exception as exc:
                last_error = exc
                continue

            parsed = self._parse_output(raw_output, stream=attempt["output_format"] == "stream-json")
            if not self._should_retry_for_invalid_reply(parsed):
                break
        else:
            if isinstance(last_error, asyncio.TimeoutError):
                return self._build_failed_result(
                    f"Qwen CLI execution timed out after {timeout_seconds}s",
                    status="timeout",
                    evidence_dir=str(evidence_dir),
                )
            if last_error is not None:
                return self._build_failed_result(
                    append_executor_hints(f"Qwen CLI invocation failed: {last_error}"),
                    evidence_dir=str(evidence_dir),
                )

        conversation_log_path = self._write_evidence(evidence_dir, raw_output, parsed, input_data)
        return {
            "status": "completed" if not parsed.get("error") else "failed",
            "generated_text": parsed.get("generated_text", ""),
            "raw_output": raw_output,
            "structured_payload": parsed.get("structured_payload"),
            "events": parsed.get("events", []),
            "changed_files": parsed.get("changed_files", []),
            "commands_run": parsed.get("commands_run", []),
            "error": parsed.get("error"),
            "evidence_bundle_path": str(evidence_dir),
            "conversation_log_path": conversation_log_path,
        }

    @classmethod
    def _build_attempt_plan(cls, output_format: str) -> List[Dict[str, str]]:
        preferred = (output_format or cls.DEFAULT_OUTPUT_FORMAT).strip() or cls.DEFAULT_OUTPUT_FORMAT
        attempts: List[Dict[str, str]] = [
            {"transport": "positional", "output_format": preferred},
            {"transport": "stdin", "output_format": preferred},
        ]
        if preferred != "stream-json":
            attempts.append({"transport": "stdin", "output_format": "stream-json"})
        return attempts

    def _build_prompt(self, input_data: Dict[str, Any]) -> str:
        system_message = str(
            input_data.get("system_message")
            or input_data.get("system_prompt_extra")
            or ""
        ).strip()
        prompt = str(
            input_data.get("prompt")
            or input_data.get("goal")
            or ""
        ).strip()
        if system_message and prompt:
            return f"{system_message}\n\n{prompt}"
        return prompt or system_message

    def _build_command(
        self,
        *,
        output_format: str,
        approval_mode: str = DEFAULT_APPROVAL_MODE,
        include_directories: Optional[List[str]] = None,
        all_files: bool = False,
        yolo: bool = False,
        prompt_transport: str = "positional",
        prompt: str = "",
    ) -> List[str]:
        command = [self._qwen_binary]
        if prompt_transport == "positional":
            command.append(prompt)
        elif prompt_transport == "pflag":
            command.extend(["-p", prompt])
        command.extend(["--output-format", output_format])
        if self._model:
            command.extend(["--model", self._model])
        if yolo:
            command.append("--yolo")
        elif approval_mode and approval_mode != self.DEFAULT_APPROVAL_MODE:
            command.extend(["--approval-mode", approval_mode])
        if all_files:
            command.append("--all-files")
        normalized_include_directories = self._coerce_include_directories(include_directories)
        if normalized_include_directories:
            command.extend(["--include-directories", ",".join(normalized_include_directories)])
        return command

    async def _invoke_qwen(
        self,
        *,
        prompt: str,
        workspace: str,
        timeout_seconds: int,
        output_format: str,
        stream: bool,
        approval_mode: str,
        include_directories: Optional[List[str]],
        all_files: bool,
        yolo: bool,
        prompt_transport: str,
    ) -> str:
        command = self._build_command(
            prompt=prompt,
            output_format=output_format,
            approval_mode=approval_mode,
            include_directories=include_directories,
            all_files=all_files,
            yolo=yolo,
            prompt_transport=prompt_transport,
        )
        process = await asyncio.create_subprocess_exec(
            *command,
            cwd=workspace,
            stdin=asyncio.subprocess.PIPE if prompt_transport == "stdin" else None,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdin_data = prompt.encode("utf-8") if prompt_transport == "stdin" else None
            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=stdin_data),
                timeout=timeout_seconds,
            )
        except asyncio.TimeoutError:
            process.kill()
            await process.communicate()
            raise

        stdout_text = stdout.decode("utf-8", errors="replace")
        stderr_text = stderr.decode("utf-8", errors="replace")
        if process.returncode != 0:
            detail = stderr_text.strip() or stdout_text.strip() or f"exit={process.returncode}"
            raise RuntimeError(detail)
        if stream:
            return stdout_text
        return stdout_text.strip()

    def _parse_output(self, raw_output: str, *, stream: bool) -> Dict[str, Any]:
        if stream:
            return self._parse_stream_json(raw_output)

        text = raw_output.strip()
        if not text:
            return {"generated_text": "", "structured_payload": None, "events": []}

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {
                "generated_text": text,
                "structured_payload": None,
                "events": [],
            }

        generated_text = self._extract_text(payload)
        structured_payload = self._extract_structured_payload(payload, generated_text)
        return {
            "generated_text": generated_text,
            "structured_payload": structured_payload if isinstance(structured_payload, dict) else None,
            "events": payload if isinstance(payload, list) else [],
            "changed_files": self._extract_changed_files(payload),
            "commands_run": self._extract_commands(payload),
            "error": self._extract_error(payload),
        }

    def _parse_stream_json(self, raw_output: str) -> Dict[str, Any]:
        events: List[Dict[str, Any]] = []
        texts: List[str] = []
        changed_files: List[str] = []
        commands_run: List[Dict[str, Any]] = []
        error: Optional[str] = None

        for line in raw_output.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                texts.append(line)
                continue
            if isinstance(event, dict):
                events.append(event)
                text = self._extract_text(event)
                if text:
                    texts.append(text)
                changed_files.extend(self._extract_changed_files(event))
                commands_run.extend(self._extract_commands(event))
                error = error or self._extract_error(event)

        generated_text = "\n".join(item for item in texts if item).strip()
        structured_payload = self._extract_structured_payload(events, generated_text)
        return {
            "generated_text": generated_text,
            "structured_payload": structured_payload,
            "events": events,
            "changed_files": list(dict.fromkeys(changed_files)),
            "commands_run": commands_run,
            "error": error,
        }

    def _prepare_evidence_dir(self, evidence_base: str, workspace: str) -> Path:
        if evidence_base:
            evidence_dir = Path(evidence_base)
        else:
            evidence_dir = (
                Path(workspace) / ".workflow" / "qwen-cli" / datetime.now().strftime("%Y%m%d-%H%M%S")
            )
        evidence_dir.mkdir(parents=True, exist_ok=True)
        return evidence_dir

    def _write_evidence(
        self,
        evidence_dir: Path,
        raw_output: str,
        parsed: Dict[str, Any],
        input_data: Dict[str, Any],
    ) -> str:
        conversation_log = evidence_dir / "conversation.log"
        conversation_log.write_text(raw_output, encoding="utf-8")
        result_json = evidence_dir / "result.json"
        result_json.write_text(
            json.dumps(
                {
                    "parsed_output": parsed,
                    "timestamp": datetime.now().isoformat(),
                    "input": {
                        key: value
                        for key, value in input_data.items()
                        if key not in {"token_context"}
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        return str(conversation_log)

    def _extract_text(self, payload: Any) -> str:
        if isinstance(payload, str):
            return payload.strip()
        if isinstance(payload, list):
            for item in reversed(payload):
                if isinstance(item, dict) and item.get("type") == "result":
                    text = self._extract_text(item.get("result"))
                    if text:
                        return text
            parts = [self._extract_text(item) for item in payload]
            ordered: List[str] = []
            for part in parts:
                if part and part not in ordered:
                    ordered.append(part)
            return "\n".join(ordered).strip()
        if not isinstance(payload, dict):
            return ""
        message = payload.get("message")
        if isinstance(message, dict):
            text = self._extract_text(message.get("content"))
            if text:
                return text
        for key in ("generated_text", "text", "response", "content", "result", "message"):
            value = payload.get(key)
            text = self._extract_text(value)
            if text:
                return text
        return ""

    def _extract_structured_payload(self, payload: Any, generated_text: str) -> Optional[Dict[str, Any]]:
        candidate = self._parse_json_text(generated_text)
        if isinstance(candidate, dict):
            return candidate
        if isinstance(payload, list):
            for item in reversed(payload):
                if not isinstance(item, dict):
                    continue
                result_payload = self._parse_json_text(str(item.get("result") or ""))
                if isinstance(result_payload, dict):
                    return result_payload
        if isinstance(payload, dict):
            result_payload = self._parse_json_text(str(payload.get("result") or ""))
            if isinstance(result_payload, dict):
                return result_payload
        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _parse_json_text(text: str) -> Optional[Dict[str, Any]]:
        raw = str(text or "").strip()
        if not raw:
            return None
        if raw.startswith("```") and raw.endswith("```"):
            lines = raw.splitlines()
            if len(lines) >= 3:
                raw = "\n".join(lines[1:-1]).strip()
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def _extract_changed_files(self, payload: Any) -> List[str]:
        if isinstance(payload, dict):
            value = payload.get("changed_files")
            if isinstance(value, list):
                return [str(item) for item in value if str(item).strip()]
        return []

    def _extract_commands(self, payload: Any) -> List[Dict[str, Any]]:
        if isinstance(payload, dict):
            value = payload.get("commands_run")
            if isinstance(value, list):
                return [item for item in value if isinstance(item, dict)]
        return []

    def _extract_error(self, payload: Any) -> Optional[str]:
        if isinstance(payload, dict):
            value = payload.get("error")
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @classmethod
    def _should_retry_for_invalid_reply(cls, parsed: Dict[str, Any]) -> bool:
        if parsed.get("error"):
            return False
        structured_payload = parsed.get("structured_payload")
        if isinstance(structured_payload, dict):
            return cls._is_low_quality_structured_payload(structured_payload)
        text = str(parsed.get("generated_text") or "").strip()
        if not text:
            return True
        lowered = text.lower()
        return any(marker.lower() in lowered for marker in cls.INVALID_REPLY_MARKERS)

    @classmethod
    def _is_low_quality_structured_payload(cls, payload: Dict[str, Any]) -> bool:
        if not payload:
            return True
        strings = cls._collect_string_leaves(payload)
        if not strings:
            return False
        placeholder_hits = sum(1 for value in strings if cls._is_placeholder_value(value))
        if placeholder_hits >= 3:
            return True
        return placeholder_hits > 0 and (placeholder_hits / max(len(strings), 1)) >= 0.3

    @classmethod
    def _is_placeholder_value(cls, raw_value: str) -> bool:
        value = str(raw_value or "").strip()
        if not value:
            return True
        lowered = value.lower()
        for marker in cls.PLACEHOLDER_VALUE_MARKERS:
            normalized = marker.lower()
            if lowered == normalized:
                return True
            if lowered.startswith(normalized) and len(lowered) <= len(normalized) + 12:
                return True
        return False

    @classmethod
    def _collect_string_leaves(cls, payload: Any) -> List[str]:
        if isinstance(payload, str):
            text = payload.strip()
            return [text] if text else []
        if isinstance(payload, dict):
            collected: List[str] = []
            for value in payload.values():
                collected.extend(cls._collect_string_leaves(value))
            return collected
        if isinstance(payload, list):
            collected: List[str] = []
            for item in payload:
                collected.extend(cls._collect_string_leaves(item))
            return collected
        return []

    @staticmethod
    def _coerce_timeout(raw_value: Any) -> int:
        try:
            value = int(raw_value)
        except (TypeError, ValueError):
            value = 0
        return value if value > 0 else QwenExecutor.DEFAULT_TIMEOUT_SECONDS

    @classmethod
    def _coerce_approval_mode(cls, raw_value: Any) -> str:
        value = str(raw_value or "").strip().lower().replace("-", "_")
        return value if value in {"default", "auto_edit"} else cls.DEFAULT_APPROVAL_MODE

    @staticmethod
    def _coerce_include_directories(raw_value: Any) -> List[str]:
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if not value:
                return []
            if ";" in value:
                return [item.strip() for item in value.split(";") if item.strip()]
            if "," in value:
                return [item.strip() for item in value.split(",") if item.strip()]
            return [value]
        if isinstance(raw_value, (list, tuple)):
            return [str(item).strip() for item in raw_value if str(item).strip()]
        return []

    @staticmethod
    def _coerce_bool(raw_value: Any, *, default: bool = False) -> bool:
        if raw_value is None:
            return default
        if isinstance(raw_value, bool):
            return raw_value
        value = str(raw_value).strip().lower()
        if value in {"1", "true", "yes", "on"}:
            return True
        if value in {"0", "false", "no", "off", ""}:
            return False
        return default

    @staticmethod
    def _resolve_binary(binary_name: str) -> str:
        candidate = str(binary_name or QwenExecutor.DEFAULT_BINARY).strip() or QwenExecutor.DEFAULT_BINARY
        direct = shutil.which(candidate)
        if direct:
            return direct
        if os.name == "nt" and "." not in Path(candidate).name:
            for suffix in (".cmd", ".exe", ".bat", ".ps1"):
                resolved = shutil.which(f"{candidate}{suffix}")
                if resolved:
                    return resolved
        return candidate

    @staticmethod
    def _build_failed_result(
        error: str,
        *,
        status: str = "failed",
        evidence_dir: str = "",
    ) -> Dict[str, Any]:
        return {
            "status": status,
            "generated_text": "",
            "raw_output": "",
            "structured_payload": None,
            "events": [],
            "changed_files": [],
            "commands_run": [],
            "error": error,
            "evidence_bundle_path": evidence_dir,
            "conversation_log_path": "",
        }


def register_qwen_executor():
    """
    注册 Qwen 执行器到 ExecutorFactory

    使用方式:
        from lee.orchestrator.execution.qwen_executor import register_qwen_executor
        register_qwen_executor()
    """
    from .executors import ExecutorFactory
    ExecutorFactory.register("qwen_chat", QwenExecutor)
