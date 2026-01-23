"""
Flowcore API - 统一的 API 接口层

提供 PM Agent 和 Gate Assistant 需要的所有工具函数。

这是 Claude Code 工具调用的唯一入口点。
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime

# 导入现有的 PM Agent tools
from .orchestrator.pm_agent_tools import (
    orchestrator_get_state,
    orchestrator_run_step,
    orchestrator_run_step_sync,
    orchestrator_next,
    orchestrator_next_sync,
    orchestrator_list_steps,
)


# ============================================
# PM Agent API (PM 会话使用)
# ============================================

def api_get_state(project_dir: str) -> Dict[str, Any]:
    """
    获取项目 workflow 状态

    Args:
        project_dir: 项目目录路径

    Returns:
        包含 workflow 状态、步骤列表、阻塞信息的字典

    Example:
        >>> state = api_get_state(".")
        >>> print(state["summary"])
    """
    try:
        return orchestrator_get_state(project_dir)
    except Exception as e:
        return {
            "error": str(e),
            "project_dir": project_dir
        }


def api_list_ready_steps(project_dir: str) -> List[Dict[str, Any]]:
    """
    列出当前可以执行的步骤（就绪且未阻塞）

    Args:
        project_dir: 项目目录路径

    Returns:
        就绪步骤列表

    Example:
        >>> steps = api_list_ready_steps(".")
        >>> for step in steps:
        ...     print(f"{step['id']}: {step['description']}")
    """
    try:
        state = orchestrator_get_state(project_dir)

        # 筛选就绪的步骤
        ready_steps = []
        for step in state.get("steps", []):
            if step.get("is_ready") and step.get("status") == "pending":
                ready_steps.append({
                    "id": step["id"],
                    "name": step.get("name", ""),
                    "kind": step.get("kind", ""),
                    "description": step.get("description", ""),
                    "dependencies": step.get("depends_on", []),
                })

        return ready_steps
    except Exception as e:
        return [{"error": str(e)}]


def api_run_step(project_dir: str, step_id: str) -> Dict[str, Any]:
    """
    执行指定的 workflow 步骤

    Args:
        project_dir: 项目目录路径
        step_id: 步骤 ID

    Returns:
        执行结果摘要

    Example:
        >>> result = api_run_step(".", "generate_code")
        >>> print(result["status"])
        >>> print(result["outputs"])
    """
    try:
        import asyncio

        # 在同步环境中运行异步函数
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        result = loop.run_until_complete(
            orchestrator_run_step(project_dir, step_id)
        )

        return result
    except Exception as e:
        return {
            "step_id": step_id,
            "status": "failed",
            "error": str(e),
            "project_dir": project_dir
        }


def api_next_step(project_dir: str) -> Dict[str, Any]:
    """
    自动执行下一个就绪的步骤

    Args:
        project_dir: 项目目录路径

    Returns:
        执行结果摘要

    Example:
        >>> result = api_next_step(".")
        >>> print(f"Executed: {result['step_id']}")
    """
    try:
        return orchestrator_next_sync(project_dir)
    except Exception as e:
        return {
            "status": "failed",
            "error": str(e),
            "project_dir": project_dir
        }


# ============================================
# Gate Assistant API (Gate 会话使用)
# ============================================

def api_gate_list_pending(project_dir: str) -> List[Dict[str, Any]]:
    """
    列出当前所有等待审批的 gate

    Args:
        project_dir: 项目目录路径

    Returns:
        待审批的 gate 列表

    Example:
        >>> gates = api_gate_list_pending(".")
        >>> for gate in gates:
        ...     print(f"{gate['id']}: {gate['description']}")
    """
    try:
        from pathlib import Path
        import yaml

        # 读取 state
        state_file = Path(project_dir) / ".workflow" / "state.yaml"
        if not state_file.exists():
            return []

        with open(state_file) as f:
            import yaml
            state = yaml.safe_load(f)

        # 找出所有 human_gate 类型的 pending 步骤
        pending_gates = []
        for step_id, step_state in state.get("steps", {}).items():
            step_kind = step_state.get("kind", "")
            step_status = step_state.get("status", "")

            if step_kind == "human" and step_status == "pending_human":
                # 读取 gate 文件获取详情
                gate_file = Path(project_dir) / ".workflow" / "gates" / f"{step_id}.yaml"
                if gate_file.exists():
                    with open(gate_file) as f:
                        gate_info = yaml.safe_load(f)

                    pending_gates.append({
                        "id": step_id,
                        "description": gate_info.get("description", ""),
                        "status": step_status,
                        "gate_info": gate_info
                    })

        return pending_gates
    except Exception as e:
        return [{"error": str(e)}]


def api_gate_show(project_dir: str, gate_id: str) -> Dict[str, Any]:
    """
    展示 gate 的完整信息：描述、checklist、上游产物、历史决策

    Args:
        project_dir: 项目目录路径
        gate_id: Gate ID

    Returns:
        Gate 完整信息

    Example:
        >>> gate = api_gate_show(".", "acceptance_gate")
        >>> print(gate["checklist"])
        >>> print(gate["upstream_artifacts"])
    """
    try:
        from pathlib import Path
        import yaml

        # 读取 gate 文件
        gate_file = Path(project_dir) / ".workflow" / "gates" / f"{gate_id}.yaml"
        if not gate_file.exists():
            return {
                "error": f"Gate file not found: {gate_file}",
                "gate_id": gate_id
            }

        with open(gate_file) as f:
            gate_info = yaml.safe_load(f)

        # 读取上游产物
        upstream_artifacts = []
        state_file = Path(project_dir) / ".workflow" / "state.yaml"
        if state_file.exists():
            with open(state_file) as f:
                import yaml
                state = yaml.safe_load(f)

            # 获取这个 gate 的输入
            step_id = gate_id
            step_state = state.get("steps", {}).get(step_id, {})
            inputs = step_state.get("inputs", [])

            for inp in inputs:
                upstream_artifacts.append({
                    "from_step": inp.get("from_step"),
                    "artifact_path": inp.get("path"),
                    "description": inp.get("description", "")
                })

        return {
            "gate_id": gate_id,
            "description": gate_info.get("description", ""),
            "checklist": gate_info.get("checklist", []),
            "upstream_artifacts": upstream_artifacts,
            "status": gate_info.get("status", "pending"),
            "history": gate_info.get("history", [])
        }
    except Exception as e:
        return {
            "error": str(e),
            "gate_id": gate_id
        }


def api_gate_decide(
    project_dir: str,
    gate_id: str,
    option: str,  # approve | reject | revise
    comment: str,
    checklist: Optional[List[Dict[str, Any]]] = None,
    decided_by: str = "user"
) -> Dict[str, Any]:
    """
    提交 gate 决策

    Args:
        project_dir: 项目目录路径
        gate_id: Gate ID
        option: 决策选项 (approve/reject/revise)
        comment: 决策说明
        checklist: 审批清单检查结果
        decided_by: 决策人

    Returns:
        决策结果

    Example:
        >>> result = api_gate_decide(
        ...     ".",
        ...     "acceptance_gate",
        ...     "approve",
        ...     "按当前方案推进",
        ...     [{"item": "需求覆盖", "ok": True}],
        ...     "lezeng"
        ... )
        >>> print(result["status"])
    """
    try:
        from pathlib import Path
        import yaml
        from datetime import datetime

        # 读取 gate 文件
        gate_file = Path(project_dir) / ".workflow" / "gates" / f"{gate_id}.yaml"
        if not gate_file.exists():
            return {
                "error": f"Gate file not found: {gate_file}",
                "gate_id": gate_id
            }

        with open(gate_file) as f:
            gate_info = yaml.safe_load(f)

        # 更新 gate 状态
        gate_info["status"] = option
        gate_info["decided_by"] = decided_by
        gate_info["decided_at"] = datetime.now().isoformat()
        gate_info["comment"] = comment

        if checklist:
            gate_info["checklist"] = checklist

        # 添加决策历史
        if "history" not in gate_info:
            gate_info["history"] = []

        gate_info["history"].append({
            "option": option,
            "comment": comment,
            "decided_by": decided_by,
            "decided_at": datetime.now().isoformat()
        })

        # 写回文件
        with open(gate_file, "w") as f:
            yaml.safe_dump(gate_info, f, allow_unicode=True, sort_keys=False)

        # 更新 workflow state
        state_file = Path(project_dir) / ".workflow" / "state.yaml"
        if state_file.exists():
            with open(state_file) as f:
                import yaml
                state = yaml.safe_load(f)

            # 更新步骤状态
            if gate_id in state.get("steps", {}):
                if option == "approve":
                    state["steps"][gate_id]["status"] = "completed"
                elif option == "reject":
                    state["steps"][gate_id]["status"] = "rejected"
                else:
                    state["steps"][gate_id]["status"] = "pending_revision"

            # 写回 state
            with open(state_file, "w") as f:
                yaml.safe_dump(state, f, allow_unicode=True, sort_keys=False)

        return {
            "gate_id": gate_id,
            "status": option,
            "decided_by": decided_by,
            "decided_at": gate_info["decided_at"],
            "message": f"Gate '{gate_id}' has been {option}ed"
        }
    except Exception as e:
        return {
            "error": str(e),
            "gate_id": gate_id
        }


# ============================================
# Claude Code Tool Handlers
# ============================================

def pm_workflow_handler(action: str, project_dir: str = ".", **kwargs) -> Dict[str, Any]:
    """
    PM Workflow tool handler for Claude Code

    Routes workflow management actions to appropriate API functions.

    Args:
        action: Action to perform (get_state, list_ready_steps, run_step, next_step)
        project_dir: Project directory path
        **kwargs: Additional action-specific parameters (e.g., step_id)

    Returns:
        API function result
    """
    if action == "get_state":
        return api_get_state(project_dir)
    elif action == "list_ready_steps":
        return api_list_ready_steps(project_dir)
    elif action == "run_step":
        step_id = kwargs.get("step_id")
        if not step_id:
            return {
                "error": "step_id is required for run_step action",
                "action": action
            }
        return api_run_step(project_dir, step_id)
    elif action == "next_step":
        return api_next_step(project_dir)
    else:
        return {
            "error": f"Unknown action: {action}",
            "valid_actions": ["get_state", "list_ready_steps", "run_step", "next_step"]
        }


def gate_approval_handler(action: str, project_dir: str = ".", **kwargs) -> Dict[str, Any]:
    """
    Gate Approval tool handler for Claude Code

    Routes gate approval actions to appropriate API functions.

    Args:
        action: Action to perform (list_pending, show, decide)
        project_dir: Project directory path
        **kwargs: Additional action-specific parameters (gate_id, option, comment, etc.)

    Returns:
        API function result
    """
    if action == "list_pending":
        return {"gates": api_gate_list_pending(project_dir)}
    elif action == "show":
        gate_id = kwargs.get("gate_id")
        if not gate_id:
            return {
                "error": "gate_id is required for show action",
                "action": action
            }
        return api_gate_show(project_dir, gate_id)
    elif action == "decide":
        gate_id = kwargs.get("gate_id")
        option = kwargs.get("option")
        comment = kwargs.get("comment")

        if not gate_id or not option or not comment:
            return {
                "error": "gate_id, option, and comment are required for decide action",
                "action": action,
                "provided": {
                    "gate_id": gate_id,
                    "option": option,
                    "comment": comment
                }
            }

        return api_gate_decide(
            project_dir=project_dir,
            gate_id=gate_id,
            option=option,
            comment=comment,
            checklist=kwargs.get("checklist"),
            decided_by=kwargs.get("decided_by", "user")
        )
    else:
        return {
            "error": f"Unknown action: {action}",
            "valid_actions": ["list_pending", "show", "decide"]
        }


# ============================================
# 导出所有 API 函数
# ============================================

__all__ = [
    # PM Agent API
    "api_get_state",
    "api_list_ready_steps",
    "api_run_step",
    "api_next_step",
    # Gate Assistant API
    "api_gate_list_pending",
    "api_gate_show",
    "api_gate_decide",
    # Tool Handlers
    "pm_workflow_handler",
    "gate_approval_handler",
]
