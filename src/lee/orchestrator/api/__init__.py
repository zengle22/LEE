"""
LEE Orchestrator API 层

提供统一的 API 接口，供 PM Agent 和其他客户端调用。

主要功能：
1. get_state - 获取工作流状态
2. list_ready_steps - 列出就绪步骤
3. list_gates - 列出门禁
4. run_step - 执行指定步骤
5. next_step - 自动执行下一步
6. create_workflow - 创建工作流
7. approve_gate / reject_gate / revise_gate / flag_gate - 门禁操作
"""

import asyncio
import contextlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.api.contract import (
    OrchestratorAction,
    OrchestratorAPIRequest,
    OrchestratorAPIResponse,
    ResponseStatus,
)


# ========================================================================
# 全局状态
# ========================================================================

_orchestrators: Dict[tuple[str, int], Orchestrator] = {}


def _normalize_project_dir(project_dir: str) -> str:
    """Return canonical absolute project path."""
    return str(Path(project_dir).resolve())


def _orchestrator_cache_key(project_dir: str) -> tuple[str, int]:
    """
    Build cache key scoped by asyncio event loop.

    pm_workflow() uses asyncio.run() per invocation, which creates a new loop.
    Reusing loop-bound aiosqlite objects across loops can cause stalls/hangs.
    """
    loop = asyncio.get_running_loop()
    return (_normalize_project_dir(project_dir), id(loop))


async def _get_orchestrator(project_dir: str) -> Orchestrator:
    """
    获取或创建 Orchestrator 实例

    Args:
        project_dir: 项目目录

    Returns:
        Orchestrator 实例
    """
    normalized_project_dir = _normalize_project_dir(project_dir)
    key = _orchestrator_cache_key(project_dir)

    if key not in _orchestrators:
        # 数据库路径
        db_path = Path(normalized_project_dir) / ".workflow" / "orchestrator.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建存储层
        store = SQLiteStore(str(db_path))
        await store.connect()

        # 模板目录
        template_dir = Path(normalized_project_dir) / "lee" / "spec-global"
        if not template_dir.exists():
            # 尝试父目录
            parent_lee = Path(normalized_project_dir).parent / "lee" / "spec-global"
            if parent_lee.exists():
                template_dir = parent_lee

        # v3.5: 传递 project_root 到 TemplateManager 以加载配置
        template_manager = TemplateManager(
            template_dir=str(template_dir),
            project_root=normalized_project_dir
        )

        # 创建 Orchestrator
        orchestrator = Orchestrator(
            store=store,
            template_manager=template_manager,
            project_root=normalized_project_dir
        )

        _orchestrators[key] = orchestrator

    return _orchestrators[key]


async def _release_orchestrator(project_dir: str) -> None:
    """
    Close and drop orchestrator bound to current event loop.

    This is critical for pm_workflow() which creates transient event loops.
    """
    key = _orchestrator_cache_key(project_dir)
    orchestrator = _orchestrators.pop(key, None)
    if orchestrator is None:
        return

    with contextlib.suppress(Exception):
        await orchestrator.store.close()


def _serialize_gate(gate: Any) -> Dict[str, Any]:
    """将 GateApproval/GateInfo 统一序列化为 dict。"""
    return {
        "workflow_id": getattr(gate, "workflow_id", None),
        "gate_id": getattr(gate, "gate_id", None),
        "step_id": getattr(gate, "step_id", None),
        "status": getattr(getattr(gate, "status", None), "value", getattr(gate, "status", None)),
        "approver": getattr(gate, "approver", None),
        "comments": getattr(gate, "comments", None),
        "reviewers": getattr(gate, "reviewers", []),
        "approval_criteria": getattr(gate, "approval_criteria", []),
        "version": getattr(gate, "version", None),
        "default_reject_action": getattr(gate, "default_reject_action", None),
        "default_reject_target": getattr(gate, "default_reject_target", None),
        "default_revise_action": getattr(gate, "default_revise_action", None),
        "default_revise_target": getattr(gate, "default_revise_target", None),
        "decision_action": getattr(gate, "decision_action", None),
        "target_step": getattr(gate, "target_step", None),
        "structured_feedback": getattr(gate, "structured_feedback", None),
        "issues": getattr(gate, "issues", None),
        "created_at": (
            gate.created_at.isoformat()
            if getattr(gate, "created_at", None) else None
        ),
        "decided_at": (
            gate.decided_at.isoformat()
            if getattr(gate, "decided_at", None) else None
        ),
        "invalidated_at": (
            gate.invalidated_at.isoformat()
            if getattr(gate, "invalidated_at", None) else None
        ),
    }


# ========================================================================
# 核心 API 函数
# ========================================================================

async def api_get_state(project_dir: str, workflow_id: Optional[str] = None) -> Dict[str, Any]:
    """
    获取工作流状态

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID（可选，不指定则返回所有工作流）

    Returns:
        工作流状态信息
    """
    orchestrator = await _get_orchestrator(project_dir)

    if workflow_id:
        # 获取指定工作流状态
        state = await orchestrator.get_state(workflow_id)
        ready_steps = await orchestrator.get_ready_steps(workflow_id)
        pending_gates = await orchestrator.get_pending_gates(workflow_id)

        return {
            "workflow_id": state.workflow_id,
            "level": state.level.value,
            "status": state.status.value,
            "current_step": state.current_step,
            "parent_id": state.parent_id,
            "children": state.children,
            "template_id": state.template_id,
            "data": state.data,
            "ready_steps": [
                {
                    "id": s.id,
                    "kind": s.kind,
                    "agent_id": s.agent_id,
                    "skill_id": s.skill_id,
                }
                for s in ready_steps
            ],
            "pending_gates": [
                {
                    "gate_id": g.gate_id,
                    "step_id": g.step_id,
                    "status": g.status.value if hasattr(g.status, 'value') else str(g.status),
                    "reviewers": g.reviewers,
                }
                for g in pending_gates
            ],
            "timestamp": datetime.now().isoformat(),
        }
    else:
        # 获取所有工作流
        store = orchestrator.store
        instances = await store.get_all_instances()

        return {
            "workflows": [
                {
                    "id": inst.id,
                    "level": inst.level.value,
                    "status": inst.status.value,
                    "template_id": inst.template_id,
                    "parent_id": inst.parent_id,
                }
                for inst in instances
            ],
            "total": len(instances),
            "timestamp": datetime.now().isoformat(),
        }


async def api_list_ready_steps(project_dir: str, workflow_id: str) -> List[Dict[str, Any]]:
    """
    列出可执行步骤

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID

    Returns:
        可执行步骤列表
    """
    orchestrator = await _get_orchestrator(project_dir)
    ready_steps = await orchestrator.get_ready_steps(workflow_id)

    return [
        {
            "id": s.id,
            "kind": s.kind,
            "executor_type": s.executor_type,
            "agent_id": s.agent_id,
            "skill_id": s.skill_id,
            "gate_id": s.gate_id,
            "depends_on": s.depends_on,
        }
        for s in ready_steps
    ]


async def api_list_gates(
    project_dir: str,
    workflow_id: Optional[str] = None,
    status: Optional[str] = None
) -> Dict[str, Any]:
    """
    列出门禁（可按 workflow/status 过滤）

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID（可选）
        status: 门禁状态过滤（可选）

    Returns:
        门禁列表
    """
    orchestrator = await _get_orchestrator(project_dir)
    gates = await orchestrator.store.get_gate_approvals(
        workflow_id=workflow_id,
        status=status,
    )

    return {
        "workflow_id": workflow_id,
        "status_filter": status,
        "total": len(gates),
        "gates": [_serialize_gate(g) for g in gates],
        "timestamp": datetime.now().isoformat(),
    }


async def api_run_step(
    project_dir: str,
    workflow_id: str,
    step_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    执行指定步骤

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID
        step_id: 步骤 ID（可选，不指定则执行第一个就绪步骤）

    Returns:
        执行结果
    """
    orchestrator = await _get_orchestrator(project_dir)
    result = await orchestrator.run_step(workflow_id, step_id)

    return {
        "status": result.status,
        "step_id": result.step_id,
        "workflow_id": result.workflow_id,
        "message": result.message,
        "output": result.output if hasattr(result, 'output') else None,
        "next_steps": result.next_steps if hasattr(result, 'next_steps') else [],
        "blocked_reason": result.blocked_reason if hasattr(result, 'blocked_reason') else None,
        "timestamp": datetime.now().isoformat(),
    }


async def api_next_step(project_dir: str, workflow_id: str) -> Dict[str, Any]:
    """
    自动执行下一个就绪步骤

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID

    Returns:
        执行结果
    """
    return await api_run_step(project_dir, workflow_id, None)


async def api_create_workflow(
    project_dir: str,
    level: str,
    template_id: str,
    parent_id: Optional[str] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    创建工作流

    Args:
        project_dir: 项目目录
        level: 工作流层级 (project/department/task)
        template_id: 模板 ID
        parent_id: 父工作流 ID
        data: 初始数据

    Returns:
        创建结果
    """
    orchestrator = await _get_orchestrator(project_dir)

    workflow_level = WorkflowLevel(level)
    instance = await orchestrator.create_workflow(
        level=workflow_level,
        template_id=template_id,
        parent_id=parent_id,
        data=data or {},
    )

    return {
        "workflow_id": instance.id,
        "level": instance.level.value,
        "status": instance.status.value,
        "template_id": instance.template_id,
        "parent_id": instance.parent_id,
        "timestamp": datetime.now().isoformat(),
    }


async def api_run_until_blocked(
    project_dir: str,
    workflow_id: str,
    max_steps: int = 10
) -> Dict[str, Any]:
    """
    执行直到阻塞

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID
        max_steps: 最大步数

    Returns:
        执行摘要
    """
    orchestrator = await _get_orchestrator(project_dir)
    summary = await orchestrator.run_until_blocked(workflow_id, max_steps)

    return {
        "workflow_id": summary.workflow_id,
        "total_steps": summary.total_steps,
        "completed_steps": summary.completed_steps,
        "blocked_at": summary.blocked_at,
        "status": summary.status,
        "duration_seconds": summary.duration_seconds,
        "timestamp": datetime.now().isoformat(),
    }


async def api_approve_gate(
    project_dir: str,
    workflow_id: str,
    gate_id: str,
    approver: str,
    comments: str = ""
) -> Dict[str, Any]:
    """
    批准门禁

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID
        gate_id: 门禁 ID
        approver: 审批人
        comments: 审批意见

    Returns:
        审批结果
    """
    orchestrator = await _get_orchestrator(project_dir)
    result = await orchestrator.approve_gate(
        workflow_id,
        gate_id,
        approver,
        comments
    )

    return {
        "status": result.status,
        "step_id": result.step_id,
        "workflow_id": result.workflow_id,
        "message": result.message,
        "timestamp": datetime.now().isoformat(),
    }


async def api_reject_gate(
    project_dir: str,
    workflow_id: str,
    gate_id: str,
    rejecter: str,
    reason: str,
    action: Optional[str] = None,
    target_step: Optional[str] = None,
) -> Dict[str, Any]:
    """
    拒绝门禁

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID
        gate_id: 门禁 ID
        rejecter: 拒绝人
        reason: 拒绝原因
        action: 拒绝动作（可选）
        target_step: 回退目标步骤（可选）

    Returns:
        拒绝结果
    """
    orchestrator = await _get_orchestrator(project_dir)
    result = await orchestrator.reject_gate(
        workflow_id,
        gate_id,
        rejecter,
        reason,
        action=action,
        target_step=target_step,
    )

    response = {
        "status": result.status,
        "step_id": result.step_id,
        "workflow_id": result.workflow_id,
        "message": result.message,
        "action": action,
        "target_step": target_step,
        "timestamp": datetime.now().isoformat(),
    }
    if isinstance(getattr(result, "output", None), dict):
        if result.output.get("new_workflow_id"):
            response["new_workflow_id"] = result.output.get("new_workflow_id")
    return response


async def api_revise_gate(
    project_dir: str,
    workflow_id: str,
    gate_id: str,
    reviewer: str,
    reason: str,
    target_step: Optional[str] = None,
    structured_feedback: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    修订门禁（要求重试）
    """
    orchestrator = await _get_orchestrator(project_dir)
    result = await orchestrator.revise_gate(
        workflow_id=workflow_id,
        gate_id=gate_id,
        reviewer=reviewer,
        reason=reason,
        target_step=target_step,
        structured_feedback=structured_feedback,
    )
    return {
        "status": result.status,
        "step_id": result.step_id,
        "workflow_id": result.workflow_id,
        "target_step": target_step,
        "message": result.message,
        "output": result.output if hasattr(result, "output") else None,
        "timestamp": datetime.now().isoformat(),
    }


async def api_flag_gate(
    project_dir: str,
    workflow_id: str,
    gate_id: str,
    reporter: str,
    issues: List[str],
    continue_workflow: bool = True,
) -> Dict[str, Any]:
    """
    标记门禁问题
    """
    orchestrator = await _get_orchestrator(project_dir)
    result = await orchestrator.flag_gate(
        workflow_id=workflow_id,
        gate_id=gate_id,
        reporter=reporter,
        issues=issues,
        continue_workflow=continue_workflow,
    )
    return {
        "status": result.status,
        "step_id": result.step_id,
        "workflow_id": result.workflow_id,
        "continue_workflow": continue_workflow,
        "issues": issues,
        "message": result.message,
        "output": result.output if hasattr(result, "output") else None,
        "timestamp": datetime.now().isoformat(),
    }


async def api_pause_workflow(
    project_dir: str,
    workflow_id: str,
) -> Dict[str, Any]:
    """
    暂停工作流

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID

    Returns:
        操作结果
    """
    orchestrator = await _get_orchestrator(project_dir)
    await orchestrator.pause(workflow_id)
    return {
        "workflow_id": workflow_id,
        "message": f"Workflow {workflow_id} paused",
        "timestamp": datetime.now().isoformat(),
    }


async def api_resume_workflow(
    project_dir: str,
    workflow_id: str,
) -> Dict[str, Any]:
    """
    恢复工作流

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID

    Returns:
        操作结果
    """
    orchestrator = await _get_orchestrator(project_dir)
    await orchestrator.resume(workflow_id)
    return {
        "workflow_id": workflow_id,
        "message": f"Workflow {workflow_id} resumed",
        "timestamp": datetime.now().isoformat(),
    }


# ========================================================================
# Contract v1 统一分发器
# ========================================================================

async def orchestrator_api_dispatch(
    request: OrchestratorAPIRequest
) -> OrchestratorAPIResponse:
    """
    Contract v1 统一分发入口
    """
    normalized_project_dir = _normalize_project_dir(request.project_dir)
    action = request.normalized_action()
    payload = request.payload or {}

    try:
        if action == OrchestratorAction.GET_STATE.value:
            data = await api_get_state(normalized_project_dir, request.workflow_id)

        elif action == OrchestratorAction.LIST_READY_STEPS.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for list_ready_steps")
            data = await api_list_ready_steps(normalized_project_dir, request.workflow_id)

        elif action == OrchestratorAction.LIST_GATES.value:
            data = await api_list_gates(
                normalized_project_dir,
                request.workflow_id,
                payload.get("status"),
            )

        elif action == OrchestratorAction.RUN_STEP.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for run_step")
            data = await api_run_step(normalized_project_dir, request.workflow_id, request.step_id)

        elif action == OrchestratorAction.NEXT_STEP.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for next_step")
            data = await api_next_step(normalized_project_dir, request.workflow_id)

        elif action == OrchestratorAction.CREATE_WORKFLOW.value:
            level = payload.get("level")
            template_id = payload.get("template_id")
            if not level or not template_id:
                raise ValueError("level and template_id are required for create_workflow")
            data = await api_create_workflow(
                normalized_project_dir,
                level,
                template_id,
                payload.get("parent_id"),
                payload.get("data"),
            )

        elif action == OrchestratorAction.RUN_UNTIL_BLOCKED.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for run_until_blocked")
            data = await api_run_until_blocked(
                normalized_project_dir,
                request.workflow_id,
                payload.get("max_steps", 10),
            )

        elif action == OrchestratorAction.APPROVE_GATE.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for approve_gate")
            gate_id = payload.get("gate_id")
            approver = payload.get("approver")
            if not gate_id or not approver:
                raise ValueError("gate_id and approver are required for approve_gate")
            data = await api_approve_gate(
                normalized_project_dir,
                request.workflow_id,
                gate_id,
                approver,
                payload.get("comments", ""),
            )

        elif action == OrchestratorAction.REJECT_GATE.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for reject_gate")
            gate_id = payload.get("gate_id")
            rejecter = payload.get("rejecter")
            reason = payload.get("reason")
            if not gate_id or not rejecter or not reason:
                raise ValueError("gate_id, rejecter and reason are required for reject_gate")
            data = await api_reject_gate(
                normalized_project_dir,
                request.workflow_id,
                gate_id,
                rejecter,
                reason,
                payload.get("action"),
                payload.get("target_step"),
            )

        elif action == OrchestratorAction.REVISE_GATE.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for revise_gate")
            gate_id = payload.get("gate_id")
            reviewer = payload.get("reviewer")
            reason = payload.get("reason")
            if not gate_id or not reviewer or not reason:
                raise ValueError("gate_id, reviewer and reason are required for revise_gate")
            data = await api_revise_gate(
                normalized_project_dir,
                request.workflow_id,
                gate_id,
                reviewer,
                reason,
                payload.get("target_step"),
                payload.get("structured_feedback"),
            )

        elif action == OrchestratorAction.FLAG_GATE.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for flag_gate")
            gate_id = payload.get("gate_id")
            reporter = payload.get("reporter")
            issues = payload.get("issues")
            if not gate_id or not reporter or not isinstance(issues, list):
                raise ValueError("gate_id, reporter and issues(list) are required for flag_gate")
            data = await api_flag_gate(
                normalized_project_dir,
                request.workflow_id,
                gate_id,
                reporter,
                issues,
                payload.get("continue_workflow", True),
            )

        elif action == OrchestratorAction.PAUSE_WORKFLOW.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for pause_workflow")
            data = await api_pause_workflow(normalized_project_dir, request.workflow_id)

        elif action == OrchestratorAction.RESUME_WORKFLOW.value:
            if not request.workflow_id:
                raise ValueError("workflow_id is required for resume_workflow")
            data = await api_resume_workflow(normalized_project_dir, request.workflow_id)

        else:
            raise ValueError(f"Unknown action: {request.action}")

        return OrchestratorAPIResponse(
            status=ResponseStatus.SUCCESS.value,
            action=action,
            data=data,
            error=None,
            meta={"timestamp": datetime.now().isoformat()},
        )

    except Exception as e:
        return OrchestratorAPIResponse(
            status=ResponseStatus.ERROR.value,
            action=action,
            data=None,
            error=str(e),
            meta={"timestamp": datetime.now().isoformat()},
        )
    finally:
        await _release_orchestrator(normalized_project_dir)


# ========================================================================
# pm_workflow_handler - 统一入口（供 MCP 工具调用）
# ========================================================================

async def pm_workflow_handler(
    action: str,
    project_dir: str = ".",
    workflow_id: Optional[str] = None,
    step_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    PM Workflow 统一处理器

    这是 pm_workflow MCP 工具的 handler 函数。

    Args:
        action: 操作类型 (get_state, list_ready_steps, run_step, next_step,
                         create, run_until_blocked, approve_gate, reject_gate)
        project_dir: 项目目录
        workflow_id: 工作流 ID（部分操作需要）
        step_id: 步骤 ID（run_step 操作需要）
        **kwargs: 其他参数

    Returns:
        操作结果
    """
    response = await orchestrator_api_dispatch(
        OrchestratorAPIRequest(
            action=action,
            project_dir=project_dir,
            workflow_id=workflow_id,
            step_id=step_id,
            payload=kwargs,
        )
    )

    if response.status == ResponseStatus.ERROR.value:
        return {
            "error": response.error,
            "action": action,
            "timestamp": response.meta.get("timestamp", datetime.now().isoformat()),
        }

    # Legacy compatibility: keep historical return shapes.
    if action == "list_ready_steps":
        return {"ready_steps": response.data or []}

    if isinstance(response.data, dict):
        return response.data

    return {"result": response.data}


# ========================================================================
# 同步包装器（便于非异步环境调用）
# ========================================================================

def pm_workflow(
    action: str,
    project_dir: str = ".",
    workflow_id: Optional[str] = None,
    step_id: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    PM Workflow 同步版本

    封装异步函数，便于在同步环境中调用。
    """
    return asyncio.run(pm_workflow_handler(
        action,
        project_dir,
        workflow_id,
        step_id,
        **kwargs
    ))


# 导出
__all__ = [
    "OrchestratorAction",
    "OrchestratorAPIRequest",
    "OrchestratorAPIResponse",
    "ResponseStatus",
    "api_get_state",
    "api_list_ready_steps",
    "api_list_gates",
    "api_run_step",
    "api_next_step",
    "api_create_workflow",
    "api_run_until_blocked",
    "api_approve_gate",
    "api_reject_gate",
    "api_revise_gate",
    "api_flag_gate",
    "api_pause_workflow",
    "api_resume_workflow",
    "orchestrator_api_dispatch",
    "pm_workflow_handler",
    "pm_workflow",
]
