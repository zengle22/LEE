"""
PM Agent Runtime

The "Value-Add Layer" providing natural language interface and intelligent
coordination for LEE workflows.

Refactored to use Decision Engine architecture with proper separation of concerns:
- Intent Classification (Intent Classifier)
- Permission Checking (Permission Checker)
- Parameter Mapping (Param Mapper)
- Decision Orchestration (Decision Engine)
"""

import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path

from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.core.event_bus import get_event_bus, EventType
from lee.orchestrator.execution.failure_handler import FailureGuard
from lee.orchestrator.execution.pm_agent_session import PMAgentSession, SessionState

# New imports for refactored architecture
from lee.orchestrator.execution.pm_agent.decision_engine import DecisionEngine
from lee.orchestrator.execution.pm_agent.intent_classifier import IntentClassifier
from lee.orchestrator.execution.pm_agent.param_mapper import ParamMapper
from lee.orchestrator.execution.pm_agent.permission_checker import PermissionChecker
from lee.orchestrator.execution.pm_agent.api_wrapper import OrchestratorAPIWrapper
from lee.orchestrator.execution.pm_agent.config import IntentClassifierConfig
from lee.orchestrator.execution.pm_agent.models import (
    CompiledParams,
    ConversationContext,
    Decision,
    Intent,
    IntentType,
    WorkflowParams,
    ExecutionContext,
    APIResponse,
)

logger = logging.getLogger(__name__)

@dataclass
class CompiledParams:
    """Compiled parameters from natural language prompt"""
    workflow_ref: str
    params: Dict[str, Any]
    confidence: float
    reasoning: str
    action: str = ""
    allowed: bool = True
    denial_reason: Optional[str] = None

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
    """
    PM Agent Runtime - Session Management and Decision Execution

    Refactored to use Decision Engine architecture:
    - Manages conversation sessions
    - Orchestrates decision-making pipeline
    - Executes decisions via API wrapper
    - Maintains backward compatibility with existing code
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        llm_executor,
        store,
        project_dir: Optional[str] = None,
        enable_decision_engine: bool = True
    ):
        """
        Initialize PM Agent Runtime

        Args:
            orchestrator: Orchestrator instance
            llm_executor: LLM executor for NLP tasks
            store: Storage layer
            project_dir: Project directory path
            enable_decision_engine: Enable new Decision Engine (default: True)
        """
        self.orchestrator = orchestrator
        self.llm = llm_executor
        self.store = store
        self.project_dir = project_dir or str(Path.cwd())
        self.event_bus = get_event_bus()
        self.failure_guard = FailureGuard()

        # Initialize session manager
        self.session_manager = PMAgentSession(self.project_dir)

        # Initialize Decision Engine components
        self.enable_decision_engine = enable_decision_engine
        if enable_decision_engine and llm_executor:
            try:
                self._init_decision_engine()
            except Exception as e:
                logger.warning(f"Decision Engine initialization skipped: {e}")
                self.enable_decision_engine = False
                self.decision_engine = None
                self.api_wrapper = None
        else:
            self.decision_engine = None
            self.api_wrapper = None
            logger.warning("Decision Engine disabled, running in legacy mode")

    def _init_decision_engine(self):
        """Initialize Decision Engine with all components"""
        template_manager = getattr(self.orchestrator, "template_manager", None)
        if template_manager is None:
            raise ValueError("orchestrator.template_manager is required")

        # Load configuration
        config = IntentClassifierConfig(
            project_root=self.project_dir
        )

        # Validate configuration
        validation_errors = config.validate()
        if validation_errors:
            logger.warning(f"Configuration validation errors: {validation_errors}")

        # Initialize components
        self.intent_classifier = IntentClassifier(
            config=config,
            llm_executor=self.llm
        )

        self.param_mapper = ParamMapper(
            llm_executor=self.llm,
            template_manager=template_manager
        )

        self.permission_checker = PermissionChecker(
            config=config
        )

        self.decision_engine = DecisionEngine(
            intent_classifier=self.intent_classifier,
            param_mapper=self.param_mapper,
            permission_checker=self.permission_checker,
            enable_fallback=True
        )

        self.api_wrapper = OrchestratorAPIWrapper(
            project_dir=self.project_dir
        )

        logger.info("Decision Engine initialized successfully")

    async def compile_prompt(
        self,
        user_prompt: str,
        session_id: Optional[str] = None
    ) -> CompiledParams:
        """
        Convert natural language prompt to workflow parameters

        Args:
            user_prompt: User's natural language input
            session_id: Optional session ID for context

        Returns:
            CompiledParams with workflow reference, parameters, and confidence

        Raises:
            IntentClassificationError: If intent classification fails
            PermissionDeniedError: If permission is denied
            ParameterExtractionError: If parameter extraction fails
        """
        if not self.enable_decision_engine or not self.decision_engine:
            # Legacy mode: return dummy params
            return CompiledParams(
                workflow_ref="unknown",
                params={},
                confidence=0.0,
                reasoning="Decision Engine not enabled"
            )

        # Restore or create session context
        context = await self._get_or_create_context(session_id)

        try:
            # Make decision using Decision Engine
            decision = await self.decision_engine.decide(user_prompt, context)

            # Update context with decision
            if session_id:
                # Keep workflow instance id in session; avoid overwriting with template ids.
                if decision.params.workflow_ref and str(decision.params.workflow_ref).startswith("wf_"):
                    context.current_workflow_id = decision.params.workflow_ref
                # Convert ConversationContext to SessionState for persistence
                session_state = SessionState(
                    session_id=session_id,
                    run_id=context.current_workflow_id,
                    last_active_timestamp=time.time(),
                    history_summary=f"{len(context.history)} turns",
                    metadata={
                        **(context.metadata or {}),
                        "user_permissions": context.user_permissions,
                        "department": context.department,
                    }
                )
                self.session_manager.save(session_id, session_state)

            # Return compiled params (backward compatible format)
            return CompiledParams(
                workflow_ref=decision.params.workflow_ref or "current",
                params={
                    "action": decision.action,
                    "step_id": decision.params.step_id,
                    "gate_id": decision.params.gate_id,
                    **decision.params.params
                },
                confidence=decision.intent.confidence,
                reasoning=decision.intent.reasoning,
                action=decision.action,
                allowed=decision.allowed,
                denial_reason=decision.denial_reason
            )

        except Exception as e:
            logger.error(f"Failed to compile prompt: {e}")
            raise

    async def execute_decision(
        self,
        decision: Decision,
        context: Optional[ExecutionContext] = None
    ) -> APIResponse:
        """
        Execute a decision via Orchestrator API

        Args:
            decision: Decision to execute
            context: Optional execution context

        Returns:
            API response
        """
        if not self.api_wrapper:
            raise RuntimeError("API Wrapper not initialized")

        return await self.api_wrapper.execute(decision, context)

    async def process_input(
        self,
        user_input: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process user input end-to-end:
        1. Compile prompt
        2. Execute decision
        3. Return formatted response

        Args:
            user_input: User's natural language input
            session_id: Optional session ID

        Returns:
            Formatted response dictionary
        """
        # Compile prompt
        compiled = await self.compile_prompt(user_input, session_id)

        if not compiled.allowed:
            return {
                "status": "denied",
                "error": compiled.denial_reason,
                "reasoning": compiled.reasoning,
            }

        # Create decision and execute
        decision = Decision(
            intent=Intent(
                type=IntentType.QUERY_STATUS,  # Placeholder, actual type lost in CompiledParams
                confidence=compiled.confidence,
                reasoning=compiled.reasoning
            ),
            params=WorkflowParams(
                workflow_ref=compiled.workflow_ref if compiled.workflow_ref != "current" else None,
                step_id=compiled.params.get("step_id"),
                gate_id=compiled.params.get("gate_id"),
                params=compiled.params,
                confidence=compiled.confidence
            ),
            action=compiled.action or "get_state",
            allowed=compiled.allowed
        )

        # Build execution context
        context = ExecutionContext(
            project_dir=self.project_dir,
            session_id=session_id
        )

        # Execute decision
        response = await self.execute_decision(decision, context)

        result = {
            "status": response.status,
            "data": response.data,
            "error": response.error,
            "action": response.action,
            "confidence": compiled.confidence,
            "reasoning": compiled.reasoning,
        }

        # Persist richer session history for traceability.
        if session_id:
            await self._persist_session_after_response(
                session_id=session_id,
                user_input=user_input,
                compiled=compiled,
                response=response,
                decision=decision,
            )

        # Return formatted response
        return result

    async def _get_or_create_context(self, session_id: Optional[str]) -> ConversationContext:
        """Get existing context or create new one"""
        if session_id:
            existing_session = self.session_manager.restore(session_id)
            if existing_session:
                metadata = existing_session.metadata or {}
                interaction_history = metadata.get("interaction_history", [])
                if not isinstance(interaction_history, list):
                    interaction_history = []
                # Convert SessionState to ConversationContext
                return ConversationContext(
                    session_id=session_id,
                    department=metadata.get("department"),
                    user_permissions=metadata.get("user_permissions", []),
                    history=interaction_history,
                    current_workflow_id=existing_session.run_id,
                    metadata=metadata
                )

        # Create new context
        return ConversationContext(
            session_id=session_id or str(uuid.uuid4()),
            department=None,  # Could be detected from project config
            user_permissions=[],
            history=[],
            current_workflow_id=None,
            metadata={}
        )

    async def _persist_session_after_response(
        self,
        session_id: str,
        user_input: str,
        compiled: CompiledParams,
        response: APIResponse,
        decision: Decision,
    ) -> None:
        """Persist session with structured interaction history."""
        context = await self._get_or_create_context(session_id)
        metadata = dict(context.metadata or {})
        history = metadata.get("interaction_history", [])
        if not isinstance(history, list):
            history = []

        response_data = response.data if isinstance(response.data, dict) else {}
        template_input = response_data.get("template_input") or compiled.params.get("template_input")
        template_resolved = (
            response_data.get("template_resolved")
            or response_data.get("template_id")
            or compiled.params.get("template_resolved")
            or compiled.params.get("template_id")
        )

        history_entry: Dict[str, Any] = {
            "timestamp": time.time(),
            "user_input": user_input,
            "action": response.action or compiled.action or decision.action,
            "status": response.status,
            "confidence": compiled.confidence,
            "workflow_id": response_data.get("workflow_id") or context.current_workflow_id,
        }

        if template_input or template_resolved:
            history_entry["template_resolution"] = {
                "input": template_input,
                "resolved": template_resolved,
            }

        history.append(history_entry)
        max_history = 50
        if len(history) > max_history:
            history = history[-max_history:]

        metadata["interaction_history"] = history
        metadata["user_permissions"] = context.user_permissions
        metadata["department"] = context.department
        if history_entry.get("template_resolution"):
            metadata["last_template_resolution"] = history_entry["template_resolution"]

        run_id = response_data.get("workflow_id") or context.current_workflow_id
        session_state = SessionState(
            session_id=session_id,
            run_id=run_id,
            last_active_timestamp=time.time(),
            history_summary=f"{len(history)} turns",
            metadata=metadata,
        )
        self.session_manager.save(session_id, session_state)

    def get_metrics(self) -> Dict[str, Any]:
        """Get runtime metrics from all components"""
        metrics = {
            "decision_engine_enabled": self.enable_decision_engine,
        }

        if self.decision_engine:
            metrics["decision_engine"] = self.decision_engine.get_metrics()

        if self.api_wrapper:
            metrics["api_wrapper"] = self.api_wrapper.get_metrics()

        if hasattr(self, 'intent_classifier'):
            metrics["intent_classifier"] = self.intent_classifier.get_metrics()

        if hasattr(self, 'param_mapper'):
            metrics["param_mapper"] = self.param_mapper.get_metrics()

        if hasattr(self, 'permission_checker'):
            metrics["permission_checker"] = self.permission_checker.get_metrics()

        return metrics

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
