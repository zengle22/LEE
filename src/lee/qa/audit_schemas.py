"""Audit schema compatibility exports for FEAT-143."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class AuditQuery:
    """Structured query filters for audit log retrieval."""

    execution_id: Optional[str] = None
    task_ref: Optional[str] = None
    testplan_ref: Optional[str] = None
    release_ref: Optional[str] = None
    triggered_by: Optional[str] = None
    started_at: Optional[str] = None
    ended_at: Optional[str] = None
