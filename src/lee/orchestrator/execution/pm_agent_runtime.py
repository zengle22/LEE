"""
PM Agent Runtime

The "Value-Add Layer" providing natural language interface and intelligent
coordination for LEE workflows.
"""

import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.core.event_bus import get_event_bus, EventType
from lee.orchestrator.execution.failure_handler import FailureGuard
from lee.orchestrator.execution.pm_agent_session import PMAgentSession, SessionState

logger = logging.getLogger(__name__)

@dataclass
class CompiledParams:
    workflow_ref: str
    params: Dict[str, Any]
    confidence: float
    reasoning: str

@dataclass
class ProgressReport:
    run_id: str
    status: str
    current_step: Optional[str]
    completed_steps: List[str]
    pending_gates: List[Dict]
    patch_summary: str

@dataclass
class CompletionSummary:
    run_id: str
    status: str
    duration: str
    files_changed: int
    receipt_status: str
    next_steps: List[str]

class PMAgentRuntime:
    def __init__(self, orchestrator: Orchestrator, llm_executor, store):
        self.orchestrator = orchestrator
        self.llm = llm_executor
        self.store = store
        self.event_bus = get_event_bus()
        self.failure_guard = FailureGuard()
        
    async def compile_prompt(self, user_prompt: str) -> CompiledParams:
        """
        Convert NL prompt to workflow parameters using LLM.
        """
        # Placeholder for LLM logic
        # In a real implementation, this would construct a prompt for the PM Agent LLM
        # to map user intent to available workflows and parameters.
        return CompiledParams(
            workflow_ref="unknown",
            params={},
            confidence=0.0,
            reasoning="Not implemented"
        )

    async def get_progress_report(self, run_id: str) -> ProgressReport:
        """
        Get progress from store (primary).
        """
        wf = await self.store.get_workflow(run_id)
        if not wf:
            return ProgressReport(
                run_id=run_id,
                status="not_found",
                current_step=None,
                completed_steps=[],
                pending_gates=[],
                patch_summary="Workflow not found"
            )
            
        return ProgressReport(
            run_id=run_id,
            status=wf.status.value,
            current_step=wf.current_step,
            completed_steps=wf.data.get("completed_steps", []),
            pending_gates=[], # TODO: Fetch from GateStateMachine
            patch_summary=f"Steps completed: {len(wf.data.get('completed_steps', []))}"
        )

    async def handle_gate_request(self, approval_request: Dict) -> str:
        """
        Present gate request to user via LLM interaction or return structured data.
        """
        return "pending"

    async def generate_completion_summary(self, run_id: str) -> CompletionSummary:
        """
        Generate summary after run completion.
        """
        wf = await self.store.get_workflow(run_id)
        if not wf:
            return CompletionSummary(
                run_id=run_id,
                status="not_found",
                duration="0s",
                files_changed=0,
                receipt_status="unknown",
                next_steps=[]
            )
            
        return CompletionSummary(
            run_id=run_id,
            status=wf.status.value,
            duration=str(wf.updated_at - wf.created_at) if wf.updated_at else "0s",
            files_changed=0, # Need to aggregate patch metrics
            receipt_status="verified", # Placeholder
            next_steps=["Review artifacts", "Deploy"]
        )

    async def amend_workflow(self, run_id: str, changes: Dict[str, Any]) -> bool:
        """
        Amend workflow params or state.
        Only allowed for 'pending', 'running' or 'paused' workflows.
        
        Args:
            run_id: Workflow run ID
            changes: Dict with keys like "params" to update
        
        Returns:
            True if successful
        """
        wf = await self.store.get_workflow(run_id)
        if not wf:
            raise ValueError(f"Workflow {run_id} not found")
            
        if wf.status.value not in ("pending", "running", "paused"):
            raise ValueError(f"Cannot amend workflow in status {wf.status.value}")
            
        # Update params in wf.data
        current_data = wf.data or {}
        
        # Merge params
        if "params" in changes:
            params = current_data.get("params", {})
            params.update(changes["params"])
            current_data["params"] = params
            
        await self.store.update_workflow_data(run_id, current_data)
        return True
