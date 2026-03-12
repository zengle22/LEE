from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional


LIVE_EXECUTOR_TYPES = {"claude_code", "codex"}
HEARTBEAT_RE = re.compile(r"heartbeat elapsed=(?P<elapsed>\d+)s silent_for=(?P<silent>\d+)s")
LOG_LINE_RE = re.compile(r"^\[(?P<ts>[^\]]+)\]\[(?P<channel>[^\]]+)\]\s?(?P<message>.*)$")


@dataclass
class LiveExecutionState:
    step_name: str
    executor_type: str
    live_log_path: Path
    state: str
    elapsed_seconds: Optional[int] = None
    silent_for_seconds: Optional[int] = None


@dataclass
class ExecutionBoundarySummary:
    workflow_id: str
    step_name: str
    executor_type: str
    status: str
    evidence_dir: Optional[Path] = None
    live_log_path: Optional[Path] = None
    conversation_log_path: Optional[Path] = None
    debug_log_path: Optional[Path] = None
    prompt_system_path: Optional[Path] = None
    prompt_user_path: Optional[Path] = None
    display_state: Optional[str] = None
    elapsed_seconds: Optional[int] = None
    silent_for_seconds: Optional[int] = None


def _load_json_dict(raw: Optional[str]) -> Dict[str, object]:
    if not raw:
        return {}
    try:
        data = json.loads(raw)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _parse_live_log_line(line: str) -> Optional[Dict[str, str]]:
    match = LOG_LINE_RE.match(line.rstrip("\n"))
    if not match:
        return None
    return match.groupdict()


def _parse_heartbeat(message: str) -> Optional[Dict[str, int]]:
    match = HEARTBEAT_RE.search(message)
    if not match:
        return None
    return {
        "elapsed_seconds": int(match.group("elapsed")),
        "silent_for_seconds": int(match.group("silent")),
    }


def classify_live_execution_state(lines: Iterable[str]) -> Dict[str, object]:
    last_channel: Optional[str] = None
    last_message: str = ""
    elapsed_seconds: Optional[int] = None
    silent_for_seconds: Optional[int] = None

    for raw_line in lines:
        parsed = _parse_live_log_line(raw_line)
        if not parsed:
            continue
        last_channel = parsed["channel"]
        last_message = parsed["message"]
        if parsed["channel"] == "meta":
            heartbeat = _parse_heartbeat(parsed["message"])
            if heartbeat:
                elapsed_seconds = heartbeat["elapsed_seconds"]
                silent_for_seconds = heartbeat["silent_for_seconds"]

    if last_channel in {"stdout", "stderr"}:
        state = "streaming"
    elif silent_for_seconds is not None:
        if silent_for_seconds >= 30:
            state = "stalled"
        elif silent_for_seconds >= 10:
            state = "quiet"
        else:
            state = "streaming"
    elif "pid=" in last_message:
        state = "starting"
    else:
        state = "running"

    return {
        "state": state,
        "elapsed_seconds": elapsed_seconds,
        "silent_for_seconds": silent_for_seconds,
    }


def _tail_lines(path: Path, max_lines: int = 40) -> List[str]:
    try:
        lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    except OSError:
        return []
    if max_lines <= 0:
        return lines
    return lines[-max_lines:]


def _path_from_text(raw: object) -> Optional[Path]:
    value = str(raw or "").strip()
    return Path(value) if value else None


def get_running_live_executions(project_root: Path, workflow_id: str) -> List[LiveExecutionState]:
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT step_name, executor_type, input_data
                FROM task_executions
                WHERE workflow_id = ? AND status = 'running'
                ORDER BY started_at ASC
                """,
                (workflow_id,),
            )
        except sqlite3.Error:
            return []

        states: List[LiveExecutionState] = []
        for step_name, executor_type, raw_input in cursor.fetchall():
            if executor_type not in LIVE_EXECUTOR_TYPES:
                continue
            input_data = _load_json_dict(raw_input)
            evidence_base = str(input_data.get("evidence_base") or "").strip()
            if not evidence_base:
                continue
            live_log_path = Path(evidence_base) / "conversation.live.log"
            if not live_log_path.exists():
                continue
            classified = classify_live_execution_state(_tail_lines(live_log_path))
            states.append(
                LiveExecutionState(
                    step_name=step_name,
                    executor_type=executor_type,
                    live_log_path=live_log_path,
                    state=str(classified["state"]),
                    elapsed_seconds=classified.get("elapsed_seconds"),
                    silent_for_seconds=classified.get("silent_for_seconds"),
                )
            )
        return states
    finally:
        conn.close()


def get_execution_boundary_summaries(project_root: Path, workflow_id: str) -> List[ExecutionBoundarySummary]:
    db_path = project_root / ".workflow" / "orchestrator.db"
    if not db_path.exists():
        return []

    conn = sqlite3.connect(str(db_path))
    try:
        cursor = conn.cursor()
        try:
            cursor.execute(
                """
                SELECT step_name, executor_type, input_data, output_data, status
                FROM task_executions
                WHERE workflow_id = ?
                ORDER BY
                    CASE status
                        WHEN 'running' THEN 0
                        WHEN 'failed' THEN 1
                        WHEN 'completed' THEN 2
                        ELSE 3
                    END,
                    started_at DESC
                """,
                (workflow_id,),
            )
        except sqlite3.Error:
            return []

        summaries: List[ExecutionBoundarySummary] = []
        for step_name, executor_type, raw_input, raw_output, status in cursor.fetchall():
            if executor_type not in LIVE_EXECUTOR_TYPES:
                continue
            input_data = _load_json_dict(raw_input)
            output_data = _load_json_dict(raw_output)
            evidence_dir = _path_from_text(input_data.get("evidence_base") or output_data.get("evidence_bundle_path"))
            live_log_path = (evidence_dir / "conversation.live.log") if evidence_dir else None
            if live_log_path and not live_log_path.exists():
                live_log_path = None
            display_state = None
            elapsed_seconds = None
            silent_for_seconds = None
            if live_log_path:
                classified = classify_live_execution_state(_tail_lines(live_log_path))
                display_state = str(classified["state"])
                elapsed_seconds = classified.get("elapsed_seconds")
                silent_for_seconds = classified.get("silent_for_seconds")
            summaries.append(
                ExecutionBoundarySummary(
                    workflow_id=workflow_id,
                    step_name=step_name,
                    executor_type=executor_type,
                    status=str(status),
                    evidence_dir=evidence_dir,
                    live_log_path=live_log_path,
                    conversation_log_path=_path_from_text(output_data.get("conversation_log_path")),
                    debug_log_path=_path_from_text(output_data.get("debug_log_path")),
                    prompt_system_path=_path_from_text(output_data.get("prompt_system_path") or (evidence_dir / "prompt.system.txt" if evidence_dir else None)),
                    prompt_user_path=_path_from_text(output_data.get("prompt_user_path") or (evidence_dir / "prompt.user.txt" if evidence_dir else None)),
                    display_state=display_state,
                    elapsed_seconds=elapsed_seconds,
                    silent_for_seconds=silent_for_seconds,
                )
            )
        return summaries
    finally:
        conn.close()


def format_live_execution_state(state: LiveExecutionState) -> str:
    suffix = []
    if state.elapsed_seconds is not None:
        suffix.append(f"elapsed={state.elapsed_seconds}s")
    if state.silent_for_seconds is not None:
        suffix.append(f"silent_for={state.silent_for_seconds}s")
    metrics = f" ({', '.join(suffix)})" if suffix else ""
    return (
        f"实时状态: step={state.step_name} "
        f"executor={state.executor_type} state={state.state}{metrics}"
    )


def format_execution_boundary_summary(summary: ExecutionBoundarySummary, project_root: Path) -> List[str]:
    lines = [
        f"执行边界: step={summary.step_name} executor={summary.executor_type} status={summary.status}"
    ]
    if summary.display_state:
        metrics = []
        if summary.elapsed_seconds is not None:
            metrics.append(f"elapsed={summary.elapsed_seconds}s")
        if summary.silent_for_seconds is not None:
            metrics.append(f"silent_for={summary.silent_for_seconds}s")
        suffix = f" ({', '.join(metrics)})" if metrics else ""
        lines.append(f"  展示层: state={summary.display_state}{suffix}")
    if summary.live_log_path:
        lines.append(f"  日志边界: live_log={summary.live_log_path}")
    if summary.conversation_log_path:
        lines.append(f"  证据边界: conversation_log={summary.conversation_log_path}")
    if summary.debug_log_path:
        lines.append(f"  证据边界: debug_log={summary.debug_log_path}")
    if summary.evidence_dir:
        lines.append(f"  证据边界: evidence_dir={summary.evidence_dir}")
    if summary.prompt_system_path or summary.prompt_user_path:
        lines.append(
            "  输入边界: "
            f"system_prompt={summary.prompt_system_path or '-'} "
            f"user_prompt={summary.prompt_user_path or '-'}"
        )
    lines.append(
        "  恢复入口: "
        f"lee resume {summary.workflow_id} --project-dir {project_root}"
    )
    return lines


class WorkflowLiveOutputFollower:
    def __init__(self, project_root: Path, workflow_id: str):
        self.project_root = Path(project_root)
        self.workflow_id = workflow_id
        self._offsets: Dict[Path, int] = {}
        self._announced_paths: set[Path] = set()
        self._last_state_signature: Dict[str, tuple[object, ...]] = {}

    def poll_messages(self) -> List[str]:
        messages: List[str] = []
        live_states = get_running_live_executions(self.project_root, self.workflow_id)
        active_paths = {item.live_log_path for item in live_states}

        for state in live_states:
            path = state.live_log_path
            if path not in self._announced_paths:
                self._announced_paths.add(path)
                self._offsets[path] = path.stat().st_size if path.exists() else 0
                messages.append(
                    f"接入实时输出: step={state.step_name} "
                    f"executor={state.executor_type} log={path}"
                )
            messages.extend(self._read_new_lines(state))

            signature = (
                state.state,
                state.elapsed_seconds,
                state.silent_for_seconds,
            )
            if self._last_state_signature.get(state.step_name) != signature:
                self._last_state_signature[state.step_name] = signature
                messages.append(format_live_execution_state(state))

        stale_paths = [path for path in self._offsets if path not in active_paths]
        for path in stale_paths:
            self._offsets.pop(path, None)

        active_steps = {state.step_name for state in live_states}
        stale_steps = [step_name for step_name in self._last_state_signature if step_name not in active_steps]
        for step_name in stale_steps:
            self._last_state_signature.pop(step_name, None)

        return messages

    def _read_new_lines(self, state: LiveExecutionState) -> List[str]:
        path = state.live_log_path
        start = self._offsets.get(path, 0)
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                handle.seek(start)
                chunk = handle.read()
                self._offsets[path] = handle.tell()
        except OSError:
            return []

        if not chunk:
            return []

        formatted: List[str] = []
        for raw_line in chunk.splitlines():
            rendered = self._format_log_line(state, raw_line)
            if rendered:
                formatted.append(rendered)
        return formatted

    def _format_log_line(self, state: LiveExecutionState, raw_line: str) -> Optional[str]:
        parsed = _parse_live_log_line(raw_line)
        if not parsed:
            return f"[{state.step_name}] {raw_line}"

        channel = parsed["channel"]
        message = parsed["message"]
        if channel == "meta":
            if message.startswith("heartbeat "):
                return None
            if message.startswith(("prompt_system_path=", "prompt_user_path=", "cmd=", "cwd=")):
                return None
            return f"[{state.step_name}][meta] {message}"
        return f"[{state.step_name}][{channel}] {message}"
