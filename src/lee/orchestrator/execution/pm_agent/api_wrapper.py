"""
PM Agent Orchestrator API Wrapper

Provides a clean, unified interface between Decision Engine and
Orchestrator API layer with proper error handling and logging.
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from lee.orchestrator.api import (
    api_get_state,
    api_list_ready_steps,
    api_list_gates,
    api_run_step,
    api_next_step,
    api_create_workflow,
    api_run_until_blocked,
    api_approve_gate,
    api_reject_gate,
    api_revise_gate,
    api_flag_gate,
    api_pause_workflow,
    api_resume_workflow,
)

from .models import Decision, APIRequest, APIResponse, ExecutionContext
from .exceptions import APIExecutionError

logger = logging.getLogger(__name__)


class OrchestratorAPIWrapper:
    """
    Orchestrator API Wrapper - Unified Interface

    Maps decisions to Orchestrator API calls with:
    1. Proper error handling
    2. Response formatting
    3. Call logging and metrics
    4. Constitution rule enforcement
    """

    def __init__(self, project_dir: str):
        """
        Initialize API Wrapper

        Args:
            project_dir: Project directory for Orchestrator
        """
        self.project_dir = project_dir

        # API call metrics
        self._call_counts: Dict[str, int] = {}
        self._error_counts: Dict[str, int] = {}
        self._last_call_time: Optional[datetime] = None

    async def execute(
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
            API response with status and data

        Raises:
            APIExecutionError: If API execution fails
        """
        if not decision.allowed:
            return APIResponse(
                status="denied",
                data={},
                error=decision.denial_reason or "Permission denied",
                action=decision.action
            )

        # Map action to API call
        action_handlers = {
            "get_state": self._handle_get_state,
            "list_workflows": self._handle_list_workflows,
            "list_gates": self._handle_list_gates,
            "run_step": self._handle_run_step,
            "next_step": self._handle_next_step,
            "approve_gate": self._handle_approve_gate,
            "reject_gate": self._handle_reject_gate,
            "revise_gate": self._handle_revise_gate,
            "flag_gate": self._handle_flag_gate,
            "pause_workflow": self._handle_pause_workflow,
            "resume_workflow": self._handle_resume_workflow,
            "create_workflow": self._handle_create_workflow,
            "run_workflow": self._handle_run_workflow,
            "show_help": self._handle_show_help,
        }

        handler = action_handlers.get(decision.action)
        if not handler:
            return APIResponse(
                status="error",
                data={},
                error=f"Unknown action: {decision.action}",
                action=decision.action
            )

        # Execute API call
        try:
            response = await handler(decision, context)
            self._record_call(decision.action, success=True)
            return response

        except Exception as e:
            self._record_call(decision.action, success=False)
            logger.error(f"API execution failed for action {decision.action}: {e}")
            raise APIExecutionError(
                f"Failed to execute {decision.action}: {e}",
                action=decision.action
            ) from e

    async def _handle_get_state(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle get_state action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)

        result = await api_get_state(self.project_dir, workflow_id)

        return APIResponse(
            status="success",
            data={
                "state": result,
                "workflow_id": workflow_id,
            },
            action="get_state"
        )

    async def _handle_list_workflows(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle list_workflows action"""
        result = await api_get_state(self.project_dir, None)

        return APIResponse(
            status="success",
            data={
                "workflows": result.get("workflows", []),
                "total": result.get("total", 0),
            },
            action="list_workflows"
        )

    async def _handle_list_gates(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle list_gates action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        status_filter = decision.params.params.get("status")
        result = await api_list_gates(self.project_dir, workflow_id, status_filter)

        return APIResponse(
            status="success",
            data=result,
            action="list_gates"
        )

    async def _handle_run_step(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle run_step action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        step_id = decision.params.step_id

        if not workflow_id:
            return APIResponse(
                status="error",
                data={},
                error="No workflow specified and no current workflow in context",
                action="run_step"
            )

        if not step_id:
            # Fallback to next_step
            return await self._handle_next_step(decision, context)

        result = await api_run_step(self.project_dir, workflow_id, step_id)

        return APIResponse(
            status="success" if self._is_success_status(result.get("status"), {"success", "completed", "running"}) else "failed",
            data={
                "step_id": result.get("step_id"),
                "workflow_id": result.get("workflow_id"),
                "message": result.get("message"),
                "output": result.get("output"),
                "next_steps": result.get("next_steps", []),
            },
            error=result.get("blocked_reason") or result.get("message"),
            action="run_step"
        )

    async def _handle_next_step(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle next_step action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        execution_mode = str(decision.params.params.get("execution_mode", "") or "").lower()
        try:
            max_steps = int(decision.params.params.get("max_steps", 20))
        except (TypeError, ValueError):
            max_steps = 20

        if not workflow_id:
            return APIResponse(
                status="error",
                data={},
                error="No workflow specified and no current workflow in context",
                action="next_step"
            )

        if execution_mode == "until_blocked":
            run_result = await api_run_until_blocked(
                self.project_dir,
                workflow_id,
                max_steps=max_steps,
            )
            run_status = str(run_result.get("status", "")).lower()
            ok = run_status in {"running", "blocked", "completed"}
            message_map = {
                "completed": "Workflow execution completed",
                "blocked": "Workflow execution blocked",
                "running": "Workflow execution still running",
                "failed": "Workflow execution failed",
            }
            message = message_map.get(run_status, f"Workflow execution status: {run_status or 'unknown'}")
            return APIResponse(
                status="success" if ok else "failed",
                data={
                    "step_id": run_result.get("blocked_at"),
                    "workflow_id": workflow_id,
                    "message": message,
                    "run_result": run_result,
                },
                error=None if ok else message,
                action="next_step",
            )

        result = await api_next_step(self.project_dir, workflow_id)

        return APIResponse(
            status="success" if self._is_success_status(result.get("status"), {"success", "completed", "running"}) else "failed",
            data={
                "step_id": result.get("step_id"),
                "workflow_id": result.get("workflow_id"),
                "message": result.get("message"),
                "output": result.get("output"),
                "next_steps": result.get("next_steps", []),
            },
            error=result.get("blocked_reason") or result.get("message"),
            action="next_step"
        )

    async def _handle_approve_gate(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle approve_gate action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        gate_id = decision.params.gate_id
        comment = decision.params.approval_comment or "Approved via PM Agent"
        auto_continue = bool(decision.params.params.get("auto_continue", True))
        max_steps = int(decision.params.params.get("max_steps", 10))

        if not gate_id:
            return APIResponse(
                status="error",
                data={},
                error="gate_id is required for gate approval",
                action="approve_gate"
            )
        if not workflow_id:
            workflow_id, resolve_error = await self._resolve_workflow_id_from_gate(gate_id)
            if not workflow_id:
                return APIResponse(
                    status="error",
                    data={},
                    error=resolve_error or "workflow_id is required for gate approval",
                    action="approve_gate"
                )

        result = await api_approve_gate(
            self.project_dir,
            workflow_id,
            gate_id,
            "pm_agent",
            comment
        )

        raw_status = result.get("status")
        message_text = str(result.get("message", "") or "")
        approved = self._is_success_status(raw_status, {"success", "completed", "running", "approved"})
        if not approved and not result.get("error"):
            # 兼容非标准状态返回：只要语义上已批准，也视为成功。
            # 例如：status 字段异常，但 message 包含 "approved"。
            if "approved" in message_text.lower() or bool(result.get("step_id")):
                approved = True
        if not approved and not result.get("error"):
            # 兜底：回查 gate 持久化状态，避免 API 状态字段不标准导致误判失败。
            try:
                gates_result = await api_list_gates(self.project_dir, workflow_id, None)
                gates = gates_result.get("gates", []) if isinstance(gates_result, dict) else []
                for gate in gates:
                    if gate.get("gate_id") == gate_id and str(gate.get("status", "")).lower() == "approved":
                        approved = True
                        break
            except Exception as e:
                logger.warning("Failed to verify gate status after approval call: %s", e)

        run_result = None
        run_error = None
        if auto_continue and approved:
            try:
                run_result = await api_run_until_blocked(
                    self.project_dir,
                    workflow_id,
                    max_steps=max_steps,
                )
            except Exception as e:
                # 批准动作已经成功，不应因自动续跑异常而把审批结果标记为失败。
                run_error = str(e)
                logger.warning("Auto-continue failed after gate approval: %s", e)

        return APIResponse(
            status="success" if approved else "failed",
            data={
                "gate_id": gate_id,
                "workflow_id": workflow_id,
                "decision": "approved",
                "auto_continued": auto_continue,
                "run_result": run_result,
                "run_error": run_error,
                "message": (
                    f"Gate {gate_id} approved and workflow auto-continued"
                    if auto_continue else f"Gate {gate_id} approved"
                ),
            },
            error=result.get("error"),
            action="approve_gate"
        )

    async def _handle_reject_gate(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle reject_gate action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        gate_id = decision.params.gate_id
        comment = decision.params.approval_comment or "Rejected via PM Agent"
        action = decision.params.params.get("action")
        target_step = decision.params.params.get("target_step")

        if not gate_id:
            return APIResponse(
                status="error",
                data={},
                error="gate_id is required for gate rejection",
                action="reject_gate"
            )
        if not workflow_id:
            workflow_id, resolve_error = await self._resolve_workflow_id_from_gate(gate_id)
            if not workflow_id:
                return APIResponse(
                    status="error",
                    data={},
                    error=resolve_error or "workflow_id is required for gate rejection",
                    action="reject_gate"
                )

        result = await api_reject_gate(
            self.project_dir,
            workflow_id,
            gate_id,
            "pm_agent",
            comment,
            action=action,
            target_step=target_step,
        )

        return APIResponse(
            status="success" if self._is_success_status(result.get("status"), {"success", "completed", "running", "rejected"}) else "failed",
            data={
                "gate_id": gate_id,
                "workflow_id": workflow_id,
                "decision": "rejected",
                "message": result.get("message"),
                "action": result.get("action"),
                "target_step": result.get("target_step"),
                "new_workflow_id": result.get("new_workflow_id"),
            },
            error=result.get("error"),
            action="reject_gate"
        )

    async def _handle_revise_gate(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle revise_gate action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        gate_id = decision.params.gate_id
        reviewer = decision.params.params.get("reviewer", "pm_agent")
        reason = decision.params.approval_comment or decision.params.params.get("reason") or "Revise requested via PM Agent"
        target_step = decision.params.params.get("target_step")
        structured_feedback = decision.params.params.get("structured_feedback")

        if not gate_id:
            return APIResponse(
                status="error",
                data={},
                error="gate_id is required for gate revise",
                action="revise_gate"
            )
        if not workflow_id:
            workflow_id, resolve_error = await self._resolve_workflow_id_from_gate(gate_id)
            if not workflow_id:
                return APIResponse(
                    status="error",
                    data={},
                    error=resolve_error or "workflow_id is required for gate revise",
                    action="revise_gate"
                )

        result = await api_revise_gate(
            self.project_dir,
            workflow_id,
            gate_id,
            reviewer,
            reason,
            target_step,
            structured_feedback,
        )

        return APIResponse(
            status="success" if self._is_success_status(result.get("status"), {"success", "completed", "running", "revised"}) else "failed",
            data=result,
            error=result.get("error"),
            action="revise_gate"
        )

    async def _handle_flag_gate(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle flag_gate action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        gate_id = decision.params.gate_id
        reporter = decision.params.params.get("reporter", "pm_agent")
        issues = decision.params.params.get("issues")
        continue_workflow = decision.params.params.get("continue_workflow", True)

        if not gate_id:
            return APIResponse(
                status="error",
                data={},
                error="gate_id is required for gate flag",
                action="flag_gate"
            )
        if not workflow_id:
            workflow_id, resolve_error = await self._resolve_workflow_id_from_gate(gate_id)
            if not workflow_id:
                return APIResponse(
                    status="error",
                    data={},
                    error=resolve_error or "workflow_id is required for gate flag",
                    action="flag_gate"
                )

        if not isinstance(issues, list) or not issues:
            comment = decision.params.approval_comment or "Flagged via PM Agent"
            issues = [comment]

        result = await api_flag_gate(
            self.project_dir,
            workflow_id,
            gate_id,
            reporter,
            issues,
            continue_workflow,
        )

        return APIResponse(
            status="success" if self._is_success_status(result.get("status"), {"success", "flagged", "paused", "running", "completed"}) else "failed",
            data=result,
            error=result.get("error"),
            action="flag_gate"
        )

    async def _handle_pause_workflow(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle pause_workflow action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        if not workflow_id:
            return APIResponse(
                status="error",
                data={},
                error="workflow_id is required for pause_workflow",
                action="pause_workflow"
            )

        result = await api_pause_workflow(self.project_dir, workflow_id)
        return APIResponse(
            status="success",
            data=result,
            action="pause_workflow"
        )

    async def _handle_resume_workflow(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle resume_workflow action"""
        workflow_id = decision.params.workflow_ref or (context.workflow_id if context else None)
        if not workflow_id:
            return APIResponse(
                status="error",
                data={},
                error="workflow_id is required for resume_workflow",
                action="resume_workflow"
            )

        result = await api_resume_workflow(self.project_dir, workflow_id)
        return APIResponse(
            status="success",
            data=result,
            action="resume_workflow"
        )

    async def _handle_create_workflow(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle create_workflow action"""
        # Extract parameters
        level = decision.params.params.get("level", "task")
        template_id = decision.params.workflow_ref
        parent_id = decision.params.params.get("parent_id")
        data = decision.params.params.get("data", {})

        if not template_id:
            return APIResponse(
                status="error",
                data={},
                error="template_id is required to create workflow",
                action="create_workflow"
            )

        try:
            result = await api_create_workflow(
                project_dir=self.project_dir,
                level=level,
                template_id=template_id,
                parent_id=parent_id,
                data=data
            )

            return APIResponse(
                status="success",
                data=result,
                action="create_workflow"
            )
        except Exception as e:
            logger.error(f"Failed to create workflow: {e}")
            return APIResponse(
                status="error",
                data={},
                error=str(e),
                action="create_workflow"
            )

    async def _handle_run_workflow(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle run_workflow action - creates and runs a workflow"""
        params = decision.params.params or {}

        # Extract template_id from params
        template_id = params.get("template_id")
        if not template_id:
            # Fallback to workflow_ref
            template_id = decision.params.workflow_ref

        if not template_id:
            return APIResponse(
                status="error",
                data={},
                error="template_id is required to run workflow",
                action="run_workflow"
            )

        # Build workflow data with workspace_path
        workflow_data = {}

        # Extract workspace_path from various sources
        workspace_path = params.get("workspace_path") or params.get("directory") or params.get("target_dir")
        if workspace_path:
            workflow_data["workspace_path"] = workspace_path
            # Also store in params for template resolution
            workflow_data["params"] = {"workspace_path": workspace_path}
        else:
            # Use project_dir as default workspace_path
            workflow_data["params"] = {"workspace_path": self.project_dir}

        try:
            # Import Orchestrator API
            from lee.orchestrator.api import api_create_workflow, api_run_until_blocked

            # First create the workflow
            create_result = await api_create_workflow(
                project_dir=self.project_dir,
                level="task",
                template_id=template_id,
                parent_id=None,
                data=workflow_data
            )

            if "workflow_id" not in create_result:
                return APIResponse(
                    status="error",
                    data={},
                    error=f"Failed to create workflow: {create_result.get('error', 'Unknown error')}",
                    action="run_workflow"
                )

            workflow_id = create_result["workflow_id"]

            # Then run it until blocked
            run_result = await api_run_until_blocked(
                project_dir=self.project_dir,
                workflow_id=workflow_id,
                max_steps=10
            )

            # Determine API status based on actual run_result status
            run_status = str(run_result.get("status", "")).lower()
            ok = run_status in {"running", "blocked", "completed"}
            message_map = {
                "completed": "Workflow execution completed",
                "blocked": "Workflow execution blocked",
                "running": "Workflow execution still running",
                "failed": "Workflow execution failed",
            }
            message = message_map.get(run_status, f"Workflow execution status: {run_status or 'unknown'}")

            return APIResponse(
                status="success" if ok else "failed",
                data={
                    "workflow_id": workflow_id,
                    "template_id": template_id,
                    "template_input": params.get("template_input"),
                    "template_resolved": params.get("template_resolved", template_id),
                    "create_result": create_result,
                    "run_result": run_result,
                    "message": f"Created and started workflow {workflow_id} from template {template_id}: {message}"
                },
                error=None if ok else message,
                action="run_workflow"
            )

        except Exception as e:
            logger.error(f"Failed to run workflow: {e}")
            return APIResponse(
                status="error",
                data={},
                error=str(e),
                action="run_workflow"
            )

    async def _handle_show_help(
        self,
        decision: Decision,
        context: Optional[ExecutionContext]
    ) -> APIResponse:
        """Handle show_help action"""
        help_text = """
LEE PM Agent Help

Available Commands:
- Query status: "当前状态", "查看进度", "status"
- Execute step: "运行下一步", "执行 generate_code"
- Approve gate: "批准 gate_001", "通过审批"
- Reject gate: "拒绝 gate_001", "reject gate"
- List workflows: "有哪些工作流", "list workflows"
- Help: "帮助", "help"

Tips:
- Use natural language, no need for exact commands
- PM Agent will understand your intent
- All actions go through proper workflow execution
"""

        return APIResponse(
            status="success",
            data={
                "help": help_text.strip(),
            },
            action="show_help"
        )

    def _record_call(self, action: str, success: bool):
        """Record API call metrics"""
        self._call_counts[action] = self._call_counts.get(action, 0) + 1
        self._last_call_time = datetime.now()

        if not success:
            self._error_counts[action] = self._error_counts.get(action, 0) + 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get API call metrics"""
        total_calls = sum(self._call_counts.values())
        total_errors = sum(self._error_counts.values())

        return {
            "total_calls": total_calls,
            "total_errors": total_errors,
            "error_rate": total_errors / total_calls if total_calls > 0 else 0,
            "calls_by_action": dict(self._call_counts),
            "errors_by_action": dict(self._error_counts),
            "last_call_time": self._last_call_time.isoformat() if self._last_call_time else None,
        }

    def reset_metrics(self):
        """Reset API call metrics"""
        self._call_counts = {}
        self._error_counts = {}
        self._last_call_time = None

    @staticmethod
    def _is_success_status(status: Any, accepted: set[str]) -> bool:
        if status is None:
            return False
        return str(status).lower() in {s.lower() for s in accepted}

    async def _resolve_workflow_id_from_gate(self, gate_id: str) -> tuple[Optional[str], Optional[str]]:
        """
        Resolve workflow_id by gate_id when user only provides gate_id.

        Strategy:
        1. Search pending gates first (most common)
        2. If not found, search all gates
        3. Require unique workflow match
        """
        async def _find(status_filter: Optional[str]) -> list[str]:
            result = await api_list_gates(self.project_dir, None, status_filter)
            gates = result.get("gates", []) if isinstance(result, dict) else []
            wf_ids = {
                g.get("workflow_id")
                for g in gates
                if g.get("gate_id") == gate_id and g.get("workflow_id")
            }
            return sorted(wf_ids)

        try:
            workflow_ids = await _find("pending")
            if not workflow_ids:
                workflow_ids = await _find(None)
        except Exception as e:
            return None, f"Failed to resolve workflow_id for gate {gate_id}: {e}"

        if len(workflow_ids) == 1:
            return workflow_ids[0], None
        if len(workflow_ids) > 1:
            return None, (
                f"gate_id {gate_id} matches multiple workflows: "
                f"{', '.join(workflow_ids)}. Please specify workflow_id."
            )
        return None, f"No workflow found for gate_id: {gate_id}"
