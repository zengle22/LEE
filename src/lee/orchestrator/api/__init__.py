"""
LEE Orchestrator API 层

提供统一的 API 接口，供 PM Agent 和其他客户端调用。

主要功能：
1. get_state - 获取工作流状态
2. list_ready_steps - 列出就绪步骤
3. run_step - 执行指定步骤
4. next_step - 自动执行下一步
5. create_workflow - 创建工作流
6. approve_gate / reject_gate - 门禁审批
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from lee.orchestrator.storage.sqlite_store import SQLiteStore
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager


# ========================================================================
# 全局状态
# ========================================================================

_orchestrators: Dict[str, Orchestrator] = {}


async def _get_orchestrator(project_dir: str) -> Orchestrator:
    """
    获取或创建 Orchestrator 实例

    Args:
        project_dir: 项目目录

    Returns:
        Orchestrator 实例
    """
    project_dir = str(Path(project_dir).resolve())

    if project_dir not in _orchestrators:
        # 数据库路径
        db_path = Path(project_dir) / ".workflow" / "orchestrator.db"
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 创建存储层
        store = SQLiteStore(str(db_path))
        await store.connect()

        # 模板目录
        template_dir = Path(project_dir) / "lee" / "spec-global"
        if not template_dir.exists():
            # 尝试父目录
            parent_lee = Path(project_dir).parent / "lee" / "spec-global"
            if parent_lee.exists():
                template_dir = parent_lee

        # v3.5: 传递 project_root 到 TemplateManager 以加载配置
        template_manager = TemplateManager(
            template_dir=str(template_dir),
            project_root=project_dir
        )

        # 创建 Orchestrator
        orchestrator = Orchestrator(
            store=store,
            template_manager=template_manager,
            project_root=project_dir
        )

        _orchestrators[project_dir] = orchestrator

    return _orchestrators[project_dir]


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
    reason: str
) -> Dict[str, Any]:
    """
    拒绝门禁

    Args:
        project_dir: 项目目录
        workflow_id: 工作流 ID
        gate_id: 门禁 ID
        rejecter: 拒绝人
        reason: 拒绝原因

    Returns:
        拒绝结果
    """
    orchestrator = await _get_orchestrator(project_dir)
    result = await orchestrator.reject_gate(
        workflow_id,
        gate_id,
        rejecter,
        reason
    )

    return {
        "status": result.status,
        "step_id": result.step_id,
        "workflow_id": result.workflow_id,
        "message": result.message,
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
    try:
        if action == "get_state":
            return await api_get_state(project_dir, workflow_id)

        elif action == "list_ready_steps":
            if not workflow_id:
                return {"error": "workflow_id is required for list_ready_steps"}
            return {"ready_steps": await api_list_ready_steps(project_dir, workflow_id)}

        elif action == "run_step":
            if not workflow_id:
                return {"error": "workflow_id is required for run_step"}
            return await api_run_step(project_dir, workflow_id, step_id)

        elif action == "next_step":
            if not workflow_id:
                return {"error": "workflow_id is required for next_step"}
            return await api_next_step(project_dir, workflow_id)

        elif action == "create":
            level = kwargs.get("level")
            template_id = kwargs.get("template_id")
            if not level or not template_id:
                return {"error": "level and template_id are required for create"}
            return await api_create_workflow(
                project_dir,
                level,
                template_id,
                kwargs.get("parent_id"),
                kwargs.get("data"),
            )

        elif action == "run_until_blocked":
            if not workflow_id:
                return {"error": "workflow_id is required for run_until_blocked"}
            max_steps = kwargs.get("max_steps", 10)
            return await api_run_until_blocked(project_dir, workflow_id, max_steps)

        elif action == "approve_gate":
            if not workflow_id:
                return {"error": "workflow_id is required for approve_gate"}
            gate_id = kwargs.get("gate_id")
            approver = kwargs.get("approver")
            if not gate_id or not approver:
                return {"error": "gate_id and approver are required for approve_gate"}
            return await api_approve_gate(
                project_dir,
                workflow_id,
                gate_id,
                approver,
                kwargs.get("comments", ""),
            )

        elif action == "reject_gate":
            if not workflow_id:
                return {"error": "workflow_id is required for reject_gate"}
            gate_id = kwargs.get("gate_id")
            rejecter = kwargs.get("rejecter")
            reason = kwargs.get("reason")
            if not gate_id or not rejecter or not reason:
                return {"error": "gate_id, rejecter and reason are required for reject_gate"}
            return await api_reject_gate(
                project_dir,
                workflow_id,
                gate_id,
                rejecter,
                reason,
            )

        elif action == "pause":
            if not workflow_id:
                return {"error": "workflow_id is required for pause"}
            return await api_pause_workflow(project_dir, workflow_id)

        elif action == "resume":
            if not workflow_id:
                return {"error": "workflow_id is required for resume"}
            return await api_resume_workflow(project_dir, workflow_id)

        else:
            return {"error": f"Unknown action: {action}"}

    except Exception as e:
        return {
            "error": str(e),
            "action": action,
            "timestamp": datetime.now().isoformat(),
        }


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
    "api_get_state",
    "api_list_ready_steps",
    "api_run_step",
    "api_next_step",
    "api_create_workflow",
    "api_run_until_blocked",
    "api_approve_gate",
    "api_reject_gate",
    "api_pause_workflow",
    "api_resume_workflow",
    "pm_workflow_handler",
    "pm_workflow",
]
