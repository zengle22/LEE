"""
PM Agent Tools - 给顶层 PM/Supervisor Agent 使用的工具集

这些工具允许 PM Agent：
1. 查询当前 workflow 状态
2. 执行特定的 workflow 步骤
3. 自动选择并执行下一个就绪步骤

PM Agent 只负责"看状态 + 做决策"，不直接执行副作用。
所有实际执行都通过 Orchestrator 和 Engine 接口完成。
"""

import asyncio
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime

from .state_machine import StateMachine
from .event_log import EventLog
from .workflow_parser import WorkflowParser
from .engine_commands import _execute_step_with_engine


def orchestrator_get_state(project_dir: str) -> Dict[str, Any]:
    """
    获取当前 workflow 状态

    Args:
        project_dir: 项目目录路径

    Returns:
        包含以下字段的字典：
        - workflow_id: workflow ID
        - workflow_name: workflow 名称
        - run_id: 当前运行 ID
        - total_steps: 总步骤数
        - completed_steps: 已完成步骤数
        - failed_steps: 失败步骤数
        - ready_steps: 当前就绪的步骤 ID 列表
        - steps: 所有步骤的状态信息
        - human_gates: 需要人工审批的步骤列表

    Example:
        >>> state = orchestrator_get_state(".")
        >>> print(f"Ready steps: {state['ready_steps']}")
    """
    try:
        # 初始化状态机
        sm = StateMachine(project_dir)
        state = sm.load()

        # 加载 workflow
        workflow_file = Path(project_dir) / "workflow.yaml"
        if not workflow_file.exists():
            return {
                "error": "workflow.yaml not found",
                "project_dir": project_dir
            }

        parser = WorkflowParser(str(workflow_file))
        workflow = parser.workflow

        # 获取步骤状态
        steps_state = state.get("steps", {})
        ready_steps = sm.get_ready_steps()

        # 计算已完成和失败的步骤
        completed_steps = []
        failed_steps = []
        for step_id, step_state in steps_state.items():
            if step_state.get("state") == "completed":
                completed_steps.append(step_id)
            elif step_state.get("state") == "failed":
                failed_steps.append(step_id)

        # 构建步骤信息
        steps_info = []
        for step in workflow.get("steps", []):
            step_id = step.get("id")
            step_state = steps_state.get(step_id, {})
            status = step_state.get("state", "pending")  # 使用 "state" 字段

            steps_info.append({
                "id": step_id,
                "name": step.get("name", ""),
                "kind": step.get("kind", "agent"),
                "status": status,
                "description": step.get("description", ""),
                "depends_on": step.get("depends_on", []),
                "outputs": step.get("outputs", []),
                "is_ready": step_id in ready_steps,
                "is_human_gate": step.get("kind") == "human",
            })

        return {
            "workflow_id": workflow.get("id", ""),
            "workflow_name": workflow.get("name", ""),
            "run_id": state.get("run_id", ""),
            "total_steps": len(workflow.get("steps", [])),
            "completed_steps": len(completed_steps),
            "failed_steps": len(failed_steps),
            "ready_steps": ready_steps,
            "steps": steps_info,
            "human_gates": [s["id"] for s in steps_info if s["is_human_gate"]],
            "project_dir": str(project_dir),
            "timestamp": datetime.now().isoformat(),
        }

    except FileNotFoundError:
        return {
            "error": "Workflow not initialized. Run 'init' first.",
            "project_dir": project_dir
        }
    except Exception as e:
        return {
            "error": str(e),
            "project_dir": project_dir
        }


async def orchestrator_run_step(
    project_dir: str,
    step_id: str
) -> Dict[str, Any]:
    """
    执行指定的 workflow 步骤

    Args:
        project_dir: 项目目录路径
        step_id: 要执行的步骤 ID

    Returns:
        包含执行结果的字典：
        - status: "completed" | "failed" | "skipped"
        - step_id: 步骤 ID
        - outputs: 输出文件列表（成功时）
        - error: 错误信息（失败时）
        - duration_seconds: 执行耗时

    Example:
        >>> result = await orchestrator_run_step(".", "generate_code")
        >>> if result["status"] == "completed":
        ...     print(f"Generated: {result['outputs']}")
    """
    try:
        # 初始化状态机
        sm = StateMachine(project_dir)
        try:
            state = sm.load()
        except FileNotFoundError:
            return {
                "status": "failed",
                "step_id": step_id,
                "error": "Workflow not initialized. Run 'init' first."
            }

        # 加载 workflow
        workflow_file = Path(project_dir) / "workflow.yaml"
        if not workflow_file.exists():
            return {
                "status": "failed",
                "step_id": step_id,
                "error": "workflow.yaml not found"
            }

        parser = WorkflowParser(str(workflow_file))
        workflow = parser.workflow

        # 检查步骤是否存在并获取 agent_ref
        step_data = None
        agent_ref = ""
        for step in workflow.get("steps", []):
            if step.get("id") == step_id:
                step_data = step
                # 获取 agent 引用
                agent_ref = step.get("run", "") or step.get("agent", "")
                if isinstance(agent_ref, dict):
                    agent_ref = agent_ref.get("ref", "")
                break

        if not step_data:
            return {
                "status": "failed",
                "step_id": step_id,
                "error": f"Step '{step_id}' not found in workflow"
            }

        # 开始执行步骤（设置状态为 IN_PROGRESS）
        start_success, start_error = sm.start_step(step_id, agent_ref)
        if not start_success:
            return {
                "status": "failed",
                "step_id": step_id,
                "error": f"Failed to start step: {start_error}"
            }

        # 执行步骤
        result = await _execute_step_with_engine(
            project_dir=project_dir,
            step_id=step_id,
            workflow=workflow,
            state=state
        )

        # 处理执行结果
        if result.status == "completed":
            # 完成步骤
            outputs = result.get_output_paths()
            sm.complete_step(step_id, outputs)

            # 记录事件
            event_log = EventLog(project_dir, state["run_id"])
            event_log.log_step_completed(step_id, result.engine_type or "engine", outputs, "")
            event_log.log_validation_passed(step_id, "engine_execution")

            return {
                "status": "completed",
                "step_id": step_id,
                "outputs": outputs,
                "messages": result.messages or [],
                "duration_seconds": result.duration_seconds,
                "engine_type": result.engine_type,
                "timestamp": datetime.now().isoformat(),
            }
        else:
            return {
                "status": "failed",
                "step_id": step_id,
                "error": result.error,
                "error_details": result.error_details,
                "duration_seconds": result.duration_seconds,
                "engine_type": result.engine_type,
                "timestamp": datetime.now().isoformat(),
            }

    except Exception as e:
        import traceback
        return {
            "status": "failed",
            "step_id": step_id,
            "error": str(e),
            "traceback": traceback.format_exc(),
            "timestamp": datetime.now().isoformat(),
        }


async def orchestrator_next(project_dir: str) -> Dict[str, Any]:
    """
    自动选择并执行下一个就绪的步骤

    Args:
        project_dir: 项目目录路径

    Returns:
        包含执行结果的字典：
        - status: "completed" | "failed" | "no_ready_steps"
        - step_id: 执行的步骤 ID
        - outputs: 输出文件列表（成功时）
        - error: 错误信息（失败时）

    Example:
        >>> result = await orchestrator_next(".")
        >>> if result["status"] == "completed":
        ...     print(f"Step {result['step_id']} completed")
    """
    try:
        # 初始化状态机
        sm = StateMachine(project_dir)
        try:
            state = sm.load()
        except FileNotFoundError:
            return {
                "status": "failed",
                "error": "Workflow not initialized. Run 'init' first."
            }

        # 获取就绪步骤
        ready_steps = sm.get_ready_steps()

        if not ready_steps:
            return {
                "status": "no_ready_steps",
                "ready_steps": [],
                "message": "No ready steps available"
            }

        # 执行第一个就绪步骤
        step_id = ready_steps[0]
        return await orchestrator_run_step(project_dir, step_id)

    except Exception as e:
        import traceback
        return {
            "status": "failed",
            "error": str(e),
            "traceback": traceback.format_exc(),
        }


def orchestrator_list_steps(project_dir: str, status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    列出 workflow 中的所有步骤

    Args:
        project_dir: 项目目录路径
        status_filter: 可选的状态过滤器（"pending", "completed", "failed", "ready"）

    Returns:
        步骤信息列表

    Example:
        >>> steps = orchestrator_list_steps(".", status_filter="ready")
        >>> for step in steps:
        ...     print(f"{step['id']}: {step['name']}")
    """
    state_result = orchestrator_get_state(project_dir)

    if "error" in state_result:
        return []

    steps = state_result.get("steps", [])

    if status_filter:
        if status_filter == "ready":
            return [s for s in steps if s["is_ready"]]
        else:
            return [s for s in steps if s["status"] == status_filter]

    return steps


# 便捷函数：同步版本的 orchestrator_run_step
def orchestrator_run_step_sync(project_dir: str, step_id: str) -> Dict[str, Any]:
    """
    orchestrator_run_step 的同步版本

    适用于非异步环境。
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(orchestrator_run_step(project_dir, step_id))


# 便捷函数：同步版本的 orchestrator_next
def orchestrator_next_sync(project_dir: str) -> Dict[str, Any]:
    """
    orchestrator_next 的同步版本

    适用于非异步环境。
    """
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    return loop.run_until_complete(orchestrator_next(project_dir))
