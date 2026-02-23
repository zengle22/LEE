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

import asyncio
import json
import logging
import time
import uuid
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

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
from enum import Enum

logger = logging.getLogger(__name__)


class JobStatus(str, Enum):
    """后台任务状态"""
    PENDING = "pending"      # 已创建，等待执行
    RUNNING = "running"      # 执行中
    COMPLETED = "completed"  # 已完成
    FAILED = "failed"        # 失败
    CANCELLED = "cancelled"  # 已取消


@dataclass
class Job:
    """后台任务"""
    id: str
    text: str
    session_id: str
    status: JobStatus = JobStatus.PENDING
    created_at: datetime = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    workflow_id: Optional[str] = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

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

    Phase 1 Enhancements:
    - Timeout protection for all operations
    - Enhanced error handling and persistence
    - Workflow status query methods
    """

    # Default timeout for operations (in seconds)
    DEFAULT_TIMEOUT = 600

    # Maximum concurrent background jobs
    MAX_CONCURRENT_JOBS = 3

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

        # Background job management
        self.running_jobs: Dict[str, asyncio.Task] = {}
        self.jobs: Dict[str, Job] = {}  # In-memory job cache

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

    async def process_input_with_timeout(
        self,
        user_input: str,
        session_id: Optional[str] = None,
        timeout: int = None
    ) -> Dict[str, Any]:
        """
        Process user input with timeout protection.

        Args:
            user_input: User's natural language input
            session_id: Optional session ID
            timeout: Timeout in seconds (default: DEFAULT_TIMEOUT)

        Returns:
            Formatted response dictionary with status, data, error, etc.
            On timeout, returns status="timeout" with guidance.
        """
        if timeout is None:
            timeout = self.DEFAULT_TIMEOUT

        try:
            result = await asyncio.wait_for(
                self.process_input(user_input, session_id),
                timeout=timeout
            )
            return result
        except asyncio.TimeoutError:
            # Log timeout event
            logger.warning(
                f"Process input timed out after {timeout}s for session {session_id}"
            )

            # Try to extract workflow_id from context for better error message
            workflow_id = None
            if session_id:
                try:
                    context = await self._get_or_create_context(session_id)
                    workflow_id = context.current_workflow_id
                except Exception:
                    pass

            error_msg = (
                f"执行超时（{timeout}秒）"
            )
            if workflow_id:
                error_msg += f"\n工作流 ID: {workflow_id}"
                error_msg += f"\n使用 '/status {workflow_id}' 查看状态"
            else:
                error_msg += "\n使用 '/list' 查看最近的任务"

            return {
                "status": "timeout",
                "error": error_msg,
                "action": "timeout",
                "timeout_seconds": timeout,
            }
        except Exception as e:
            logger.error(f"Process input failed: {e}", exc_info=True)
            return {
                "status": "failed",
                "error": str(e),
                "action": "error",
            }

    async def get_workflow_status(
        self, workflow_id: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed status of a workflow.

        Args:
            workflow_id: Workflow instance ID

        Returns:
            Dict with workflow status info, or None if not found
        """
        wf = await self.store.get_workflow(workflow_id)
        if not wf:
            return None

        # Get pending gates
        pending_gates = []
        try:
            gates = await self.store.get_pending_gates(workflow_id)
            pending_gates = [
                {
                    "gate_id": g.gate_id,
                    "step_id": g.step_id,
                    "created_at": g.created_at.isoformat() if g.created_at else None,
                }
                for g in gates
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch gates for {workflow_id}: {e}")

        # Get recent task executions
        recent_executions = []
        try:
            executions = await self.store.list_task_executions(
                workflow_id=workflow_id,
                limit=5
            )
            recent_executions = [
                {
                    "step_name": e.step_name,
                    "executor_type": e.executor_type,
                    "status": e.status.value,
                    "started_at": e.started_at.isoformat() if e.started_at else None,
                    "completed_at": e.completed_at.isoformat() if e.completed_at else None,
                    "error_message": e.error_message,
                }
                for e in executions
            ]
        except Exception as e:
            logger.warning(f"Failed to fetch executions for {workflow_id}: {e}")

        return {
            "workflow_id": wf.id,
            "template_id": wf.template_id,
            "status": wf.status.value,
            "current_step": wf.current_step,
            "level": wf.level.value if wf.level else None,
            "parent_id": wf.parent_id,
            "created_at": wf.created_at.isoformat() if wf.created_at else None,
            "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
            "completed_at": wf.completed_at.isoformat() if wf.completed_at else None,
            "completed_steps": wf.data.get("completed_steps", []),
            "params": wf.data.get("params", {}),
            "pending_gates": pending_gates,
            "recent_executions": recent_executions,
        }

    async def list_recent_workflows(
        self, limit: int = 10, status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        List recent workflows.

        Args:
            limit: Maximum number of workflows to return
            status: Optional status filter

        Returns:
            List of workflow summary dicts
        """
        try:
            workflows = await self.store.list_workflows(
                limit=limit,
                status=status
            )
        except Exception as e:
            logger.error(f"Failed to list workflows: {e}")
            return []

        return [
            {
                "workflow_id": wf.id,
                "template_id": wf.template_id,
                "status": wf.status.value,
                "current_step": wf.current_step,
                "level": wf.level.value if wf.level else None,
                "created_at": wf.created_at.isoformat() if wf.created_at else None,
                "updated_at": wf.updated_at.isoformat() if wf.updated_at else None,
            }
            for wf in workflows
        ]

    async def get_workflow_logs(
        self, workflow_id: str, limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get recent logs for a workflow.

        Args:
            workflow_id: Workflow instance ID
            limit: Maximum number of log entries

        Returns:
            List of log entry dicts
        """
        logs = []

        # Get task execution logs
        try:
            executions = await self.store.list_task_executions(
                workflow_id=workflow_id,
                limit=limit
            )

            for exec in executions:
                logs.append({
                    "type": "task_execution",
                    "step_name": exec.step_name,
                    "executor_type": exec.executor_type,
                    "status": exec.status.value,
                    "started_at": exec.started_at.isoformat() if exec.started_at else None,
                    "error_message": exec.error_message,
                })
        except Exception as e:
            logger.warning(f"Failed to fetch executions for {workflow_id}: {e}")

        # Get event logs if available
        try:
            if hasattr(self.store, 'event_log'):
                events = self.store.event_log.get_events_for_run(workflow_id)
                for event in events[-limit:]:
                    logs.append({
                        "type": "event",
                        "event_type": event.event_type.value,
                        "timestamp": event.timestamp,
                        "step_id": event.step_id,
                        "actor": event.actor,
                        "error": event.error,
                        "data": event.data,
                    })
        except Exception as e:
            logger.warning(f"Failed to fetch event logs for {workflow_id}: {e}")

        # Sort by timestamp
        logs.sort(key=lambda x: x.get("timestamp") or x.get("started_at") or "", reverse=True)

        return logs[:limit]

    async def get_current_workflow_id(self, session_id: str) -> Optional[str]:
        """
        Get the current workflow ID for a session.

        Args:
            session_id: Session ID

        Returns:
            Current workflow ID or None
        """
        try:
            context = await self._get_or_create_context(session_id)
            return context.current_workflow_id
        except Exception:
            return None

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

    # ========================================================================
    # Background Job Management (Phase 2)
    # ========================================================================

    async def create_job(
        self,
        text: str,
        session_id: Optional[str] = None,
        timeout: int = None
    ) -> str:
        """
        Create a background job and return immediately.

        Args:
            text: User input text
            session_id: Optional session ID
            timeout: Optional timeout in seconds

        Returns:
            Job ID
        """
        # Check concurrent job limit
        running_count = sum(
            1 for job in self.jobs.values()
            if job.status == JobStatus.RUNNING
        )
        if running_count >= self.MAX_CONCURRENT_JOBS:
            # Wait for a slot or queue the job
            pass  # For now, just queue it

        # Create job
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            text=text,
            session_id=session_id or "",
            status=JobStatus.PENDING,
            created_at=datetime.now()
        )
        self.jobs[job_id] = job

        # Create background task
        task = asyncio.create_task(
            self._execute_job(job_id, text, session_id, timeout)
        )
        self.running_jobs[job_id] = task

        # Add callback to clean up when done
        task.add_done_callback(
            lambda t: self._on_job_done(job_id, t)
        )

        logger.info(f"Created background job {job_id} for input: {text[:50]}...")
        return job_id

    async def _execute_job(
        self,
        job_id: str,
        text: str,
        session_id: Optional[str],
        timeout: Optional[int]
    ):
        """
        Execute a background job.

        This runs in an asyncio task.
        """
        job = self.jobs.get(job_id)
        if not job:
            logger.error(f"Job {job_id} not found")
            return

        try:
            # Update status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now()

            # Publish job started event
            self.event_bus.publish(Event(
                type=EventType.JOB_STARTED,
                payload={
                    "job_id": job_id,
                    "text": text,
                    "session_id": session_id,
                },
                source_workflow=job_id,
                timestamp=datetime.now().isoformat(),
                event_id=uuid.uuid4().hex,
            ))

            # Execute with timeout
            if timeout is None:
                timeout = self.DEFAULT_TIMEOUT

            result = await asyncio.wait_for(
                self.process_input(text, session_id),
                timeout=timeout
            )

            # Job completed successfully
            job.status = JobStatus.COMPLETED
            job.completed_at = datetime.now()
            job.result = result

            # Extract workflow_id from result if available
            if result and isinstance(result, dict):
                data = result.get('data', {})
                if isinstance(data, dict):
                    job.workflow_id = data.get('workflow_id') or data.get('state', {}).get('workflow_id')

            # Publish job completed event
            self.event_bus.publish(Event(
                type=EventType.JOB_COMPLETED,
                payload={
                    "job_id": job_id,
                    "result": result,
                    "workflow_id": job.workflow_id,
                },
                source_workflow=job_id,
                timestamp=datetime.now().isoformat(),
                event_id=uuid.uuid4().hex,
            ))

            logger.info(f"Job {job_id} completed successfully")

        except asyncio.TimeoutError:
            # Job timed out
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.error = f"Timeout after {timeout}s"

            # Publish job failed event
            self.event_bus.publish(Event(
                type=EventType.JOB_FAILED,
                payload={
                    "job_id": job_id,
                    "error": job.error,
                },
                source_workflow=job_id,
                timestamp=datetime.now().isoformat(),
                event_id=uuid.uuid4().hex,
            ))

            logger.warning(f"Job {job_id} timed out")

        except Exception as e:
            # Job failed with error
            job.status = JobStatus.FAILED
            job.completed_at = datetime.now()
            job.error = str(e)

            # Publish job failed event
            self.event_bus.publish(Event(
                type=EventType.JOB_FAILED,
                payload={
                    "job_id": job_id,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
                source_workflow=job_id,
                timestamp=datetime.now().isoformat(),
                event_id=uuid.uuid4().hex,
            ))

            logger.error(f"Job {job_id} failed: {e}", exc_info=True)

    def _on_job_done(self, job_id: str, task: asyncio.Task):
        """Callback when job task completes."""
        # Clean up running_jobs
        self.running_jobs.pop(job_id, None)

        # Check for exceptions
        try:
            exception = task.exception()
            if exception:
                logger.error(f"Job {job_id} task raised exception: {exception}")
        except asyncio.CancelledError:
            logger.info(f"Job {job_id} was cancelled")
            if job_id in self.jobs:
                self.jobs[job_id].status = JobStatus.CANCELLED
        except Exception as e:
            # No exception or already handled
            pass

    async def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """
        Get status of a background job.

        Args:
            job_id: Job ID

        Returns:
            Job status dict or None if not found
        """
        job = self.jobs.get(job_id)
        if not job:
            return None

        return {
            "job_id": job.id,
            "text": job.text,
            "session_id": job.session_id,
            "status": job.status.value,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "workflow_id": job.workflow_id,
            "error": job.error,
            "has_result": job.result is not None,
        }

    async def list_jobs(
        self,
        limit: int = 20,
        status: Optional[JobStatus] = None
    ) -> List[Dict[str, Any]]:
        """
        List background jobs.

        Args:
            limit: Maximum number of jobs to return
            status: Optional status filter

        Returns:
            List of job dicts, ordered by created_at DESC
        """
        jobs = list(self.jobs.values())

        # Filter by status
        if status:
            jobs = [j for j in jobs if j.status == status]

        # Sort by created_at DESC
        jobs.sort(key=lambda j: j.created_at or datetime.min, reverse=True)

        # Convert to dicts
        return [
            {
                "job_id": j.id,
                "text": j.text[:60] + "..." if len(j.text) > 60 else j.text,
                "session_id": j.session_id,
                "status": j.status.value,
                "created_at": j.created_at.isoformat() if j.created_at else None,
                "started_at": j.started_at.isoformat() if j.started_at else None,
                "completed_at": j.completed_at.isoformat() if j.completed_at else None,
                "workflow_id": j.workflow_id,
                "error": j.error,
            }
            for j in jobs[:limit]
        ]

    async def cancel_job(self, job_id: str) -> bool:
        """
        Cancel a running job.

        Args:
            job_id: Job ID

        Returns:
            True if cancelled, False otherwise
        """
        job = self.jobs.get(job_id)
        if not job:
            return False

        if job.status != JobStatus.RUNNING and job.status != JobStatus.PENDING:
            return False

        task = self.running_jobs.get(job_id)
        if task and not task.done():
            task.cancel()
            job.status = JobStatus.CANCELLED
            job.completed_at = datetime.now()

            # Publish job cancelled event
            self.event_bus.publish(Event(
                type=EventType.JOB_CANCELLED,
                payload={"job_id": job_id},
                source_workflow=job_id,
                timestamp=datetime.now().isoformat(),
                event_id=uuid.uuid4().hex,
            ))

            return True

        return False

    def get_active_job_count(self) -> int:
        """Get number of active (running/pending) jobs."""
        return sum(
            1 for job in self.jobs.values()
            if job.status in (JobStatus.PENDING, JobStatus.RUNNING)
        )

    def get_total_job_count(self) -> int:
        """Get total number of jobs."""
        return len(self.jobs)
