"""Canonical bugfix lifecycle state machine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class BugfixStateTransition:
    from_state: str
    event: str
    to_state: str


class BugfixStateMachine:
    """Minimal runtime state machine for bugfix delivery lifecycle."""

    INITIAL_STATE = "INIT"
    TERMINAL_STATES: Set[str] = {"COMPLETED", "FAILED"}

    TRANSITIONS: Dict[str, Dict[str, str]] = {
        "INIT": {
            "triage_completed": "TRIAGE",
            "run_failed": "FAILED",
        },
        "TRIAGE": {
            "root_cause_started": "ROOT_CAUSE",
            "split_required": "FAILED",
        },
        "ROOT_CAUSE": {
            "fix_design_started": "FIX_DESIGN",
            "run_failed": "FAILED",
        },
        "FIX_DESIGN": {
            "fix_impl_started": "FIX_IMPL",
            "rollback_to_root_cause": "ROOT_CAUSE",
            "run_failed": "FAILED",
        },
        "FIX_IMPL": {
            "verification_started": "VERIFICATION",
            "rollback_to_fix_design": "FIX_DESIGN",
            "run_failed": "FAILED",
        },
        "VERIFICATION": {
            "evidence_pack_started": "EVIDENCE_PACK",
            "rollback_to_fix_impl": "FIX_IMPL",
            "run_failed": "FAILED",
        },
        "EVIDENCE_PACK": {
            "merge_decision_started": "MERGE_DECISION",
            "rollback_to_verification": "VERIFICATION",
            "run_failed": "FAILED",
        },
        "MERGE_DECISION": {
            "merge_completed": "COMPLETED",
            "merge_rejected": "FAILED",
        },
    }

    def next_state(self, current_state: str, event: str) -> str:
        """Resolve the next bugfix state for the given event."""
        if current_state in self.TERMINAL_STATES:
            raise ValueError(f"Cannot transition from terminal state: {current_state}")

        candidates = self.TRANSITIONS.get(current_state, {})
        if event not in candidates:
            raise ValueError(f"Invalid bugfix transition: {current_state} --{event}--> ?")
        return candidates[event]
