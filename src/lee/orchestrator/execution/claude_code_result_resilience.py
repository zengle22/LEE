"""Stability guards for flaky Claude headless result envelopes."""

from __future__ import annotations

from typing import Any, Dict


def should_retry_empty_tool_use_result(parsed: Dict[str, Any]) -> bool:
    """Detect transient headless envelopes that should be retried once."""
    if not isinstance(parsed, dict):
        return False
    if str(parsed.get("error") or "").strip():
        return False
    if str(parsed.get("stop_reason") or "").strip().lower() != "tool_use":
        return False
    if str(parsed.get("result_text") or "").strip():
        return False
    if parsed.get("changed_files") or parsed.get("commands_run"):
        return False
    return True
