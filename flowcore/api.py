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

        # 检查是否已经有运行中的事件循环
        try:
            loop = asyncio.get_running_loop()
            # 如果有运行中的循环，不能使用 run_until_complete
            # 需要在调用处使用 await，这里返回一个标记
            return {
                "step_id": step_id,
                "status": "error",
                "error": "async_context_required",
                "message": "Cannot call async function from sync context with running event loop. Use await api_run_step_async() instead.",
                "project_dir": project_dir
            }
        except RuntimeError:
            # 没有运行中的事件循环，可以安全创建新的
            pass

        # 在同步环境中运行异步函数
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            result = loop.run_until_complete(
                orchestrator_run_step(project_dir, step_id)
            )
            return result
        finally:
            loop.close()

    except Exception as e:
        return {
            "step_id": step_id,
            "status": "failed",
            "error": str(e),
            "project_dir": project_dir
        }


def api_run_step_async(project_dir: str, step_id: str) -> Dict[str, Any]:
    """
    异步版本的 api_run_step

    在异步上下文中使用，避免 event loop 冲突

    Args:
        project_dir: 项目目录路径
        step_id: 步骤 ID

    Returns:
        执行结果摘要
    """
    return orchestrator_run_step(project_dir, step_id)


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

        # 同时读取 workflow 获取 kind 信息
        workflow_file = Path(project_dir) / "workflow.yaml"
        workflow_kinds = {}
        if workflow_file.exists():
            with open(workflow_file) as f:
                workflow = yaml.safe_load(f)
                for step in workflow.get("steps", []):
                    workflow_kinds[step.get("id")] = step.get("kind", "")

        # 找出所有 human_gate 类型的 pending 步骤
        pending_gates = []
        for step_id, step_state in state.get("steps", {}).items():
            # 优先从 workflow 获取 kind，否则从 state 获取
            step_kind = workflow_kinds.get(step_id, step_state.get("kind", ""))
            step_status = step_state.get("state", "")  # 使用 "state" 而不是 "status"

            # 支持 human_gate 和 human 类型
            is_human_gate = step_kind in ["human_gate", "human"]
            is_pending = step_status in ["pending", "pending_human"]

            if is_human_gate and is_pending:
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
            "step_name": gate_info.get("step_name", ""),
            "description": gate_info.get("description", ""),
            "checklist": gate_info.get("checklist", []),
            "approval_criteria": gate_info.get("approval_criteria", []),
            "rejection_criteria": gate_info.get("rejection_criteria", []),
            "depends_on": gate_info.get("depends_on", []),
            "upstream_artifacts": upstream_artifacts,
            "status": gate_info.get("status", "pending"),
            "history": gate_info.get("history", [])
        }
    except Exception as e:
        return {
            "error": str(e),
            "gate_id": gate_id
        }


def _generate_freeze_contract(
    project_dir: str,
    gate_id: str,
    gate_info: Dict[str, Any]
) -> None:
    """
    Generate freeze contract when a freeze gate is approved

    Args:
        project_dir: Project directory path
        gate_id: Gate ID (e.g., "freeze_market_signals")
        gate_info: Gate information from the gate file
    """
    from pathlib import Path
    import yaml
    from datetime import datetime

    project_path = Path(project_dir)

    # Read upstream analysis files
    depends_on = gate_info.get("depends_on", [])
    workspace_path = project_path / ".workflow" / "workspace"

    # Collect all upstream analysis content
    upstream_analyses = {}
    for dep_id in depends_on:
        dep_file = workspace_path / dep_id / "response.txt"
        if dep_file.exists():
            with open(dep_file, 'r', encoding='utf-8') as f:
                upstream_analyses[dep_id] = f.read()

    # Extract research topic from the first analysis (usually search_signals)
    research_topic = {}
    if "search_signals" in upstream_analyses:
        # Try to extract keywords/theme from the search signals
        content = upstream_analyses["search_signals"]
        # Basic extraction - could be enhanced with regex/LLM
        research_topic["source_analysis"] = "search_signals"

    # Get the workflow to extract research context
    workflow_file = project_path / "workflow.yaml"
    if workflow_file.exists():
        with open(workflow_file, 'r', encoding='utf-8') as f:
            workflow = yaml.safe_load(f)

        # Find the freeze step to get research context
        for step in workflow.get("steps", []):
            if step.get("id") == gate_id:
                # Extract research context from step description
                description = step.get("description", "")
                research_topic["step_description"] = description

                # Look for research theme in the first step (search_signals)
                for s in workflow.get("steps", []):
                    if s.get("id") == "search_signals":
                        desc = s.get("description", "")
                        research_topic["search_description"] = desc
                        break
                break

    # Create freeze contract
    freeze_contract = {
        "kind": "market_signal_freeze",
        "version": "1.0",
        "frozen_at": datetime.now().isoformat(),
        "gate_id": gate_id,
        "approved_by": gate_info.get("decided_by", "user"),
        "approved_at": gate_info.get("decided_at", datetime.now().isoformat()),
        "approval_comment": gate_info.get("comment", ""),
        "research_topic": research_topic,
        "frozen_conclusions": {
            "upstream_analyses": list(upstream_analyses.keys()),
            "summary": gate_info.get("comment", "")
        },
        "upstream_content": upstream_analyses,  # Include full content for reference
        "confidence_level": _extract_confidence_from_comment(gate_info.get("comment", "")),
        "validation_status": "approved"
    }

    # Determine contract path from gate_id
    # freeze_market_signals -> contracts/market_signal_freeze/v1/freeze.yaml
    contract_name = gate_id.replace("freeze_", "") + "_freeze"
    contract_dir = project_path / "contracts" / contract_name / "v1"
    contract_dir.mkdir(parents=True, exist_ok=True)

    contract_file = contract_dir / "freeze.yaml"

    # Write freeze contract
    with open(contract_file, 'w', encoding='utf-8') as f:
        yaml.safe_dump(freeze_contract, f, allow_unicode=True, default_flow_style=False, sort_keys=False)

    print(f"[INFO] Freeze contract generated: {contract_file.relative_to(project_path)}")


def _extract_confidence_from_comment(comment: str) -> int:
    """Extract confidence level from approval comment"""
    import re
    # Look for patterns like ">70%", "80%", "confidence: 75"
    patterns = [
        r'>(\d+)%',
        r'(\d+)%.*confidence',
        r'confidence.*?(\d+)',
    ]
    for pattern in patterns:
        match = re.search(pattern, comment, re.IGNORECASE)
        if match:
            try:
                return int(match.group(1))
            except ValueError:
                continue
    return 50  # Default confidence if not found


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
                    state["steps"][gate_id]["state"] = "completed"
                    state["steps"][gate_id]["gate_status"] = "approved"
                elif option == "reject":
                    state["steps"][gate_id]["status"] = "rejected"
                    state["steps"][gate_id]["state"] = "failed"
                else:
                    state["steps"][gate_id]["status"] = "pending_revision"
                    state["steps"][gate_id]["state"] = "pending"

            # 写回 state
            with open(state_file, "w") as f:
                yaml.safe_dump(state, f, allow_unicode=True, sort_keys=False)

        # When gate is approved, generate freeze contract if it's a freeze gate
        if option == "approve" and gate_id.startswith("freeze_"):
            _generate_freeze_contract(project_dir, gate_id, gate_info)

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


def gate_review_handler(action: str, project_dir: str = ".", **kwargs) -> Dict[str, Any]:
    """
    Gate Review tool handler for Claude Code - Enhanced gate review with analysis summary

    Provides comprehensive gate review functionality including:
    - List pending gates with summary
    - Show gate details with upstream analysis summary
    - Submit decisions
    - Generate decision reports

    Args:
        action: Action to perform (list, show, decide, report)
        project_dir: Project directory path
        **kwargs: Additional action-specific parameters (gate_id, decision, comment, etc.)

    Returns:
        Formatted review result with Markdown content
    """
    from pathlib import Path
    import yaml

    def _get_upstream_summary(project_dir: str, depends_on: List[str]) -> str:
        """获取上游步骤的输出摘要"""
        summary_lines = []
        workspace = Path(project_dir) / ".workflow" / "workspace"

        for dep_id in depends_on:
            dep_file = workspace / dep_id / "response.txt"
            if dep_file.exists() and dep_file.stat().st_size > 0:
                content = dep_file.read_text(encoding='utf-8')
                # 提取前 500 字符作为摘要
                preview = content[:500].replace('\n', ' ')
                summary_lines.append(f"\n**{dep_id}**:\n{preview}...")

        return "\n".join(summary_lines) if summary_lines else "*No upstream analysis available*"

    def _format_gate_list(gates: List[Dict[str, Any]]) -> str:
        """格式化 gate 列表"""
        if not gates:
            return "\n✅ No pending gates found."

        lines = ["\n## 🚪 Pending Gates\n"]
        for i, gate in enumerate(gates, 1):
            gate_id = gate.get('id')  # 使用 'id' 而不是 'gate_id'
            gate_info = gate.get('gate_info', {})

            lines.append(f"\n### {i}. `{gate_id}`")
            lines.append(f"**Status**: {gate.get('status', 'N/A')}")
            lines.append(f"**Description**: {gate.get('description', 'N/A')[:150]}...")

            # 从 gate_info 获取更多信息
            if gate_info:
                depends_on = gate_info.get('depends_on', [])
                if depends_on:
                    lines.append(f"**Dependencies**: {', '.join(depends_on)}")

                approval_criteria = gate_info.get('approval_criteria', [])
                if approval_criteria:
                    lines.append(f"\n📋 Approval Criteria:")
                    for criterion in approval_criteria:
                        lines.append(f"  - [{criterion.get('label', '')}] {criterion.get('criteria', '')}")

        return "\n".join(lines)

    def _format_gate_details(gate: Dict[str, Any], upstream_summary: str) -> str:
        """格式化 gate 详情"""
        lines = [
            f"\n## 🚪 Gate Details: `{gate['gate_id']}`",
            f"\n**Status**: {gate.get('status', 'unknown')}",
            f"**Step**: {gate.get('step_name', 'N/A')}",
            f"\n**Description**:\n{gate.get('description', 'N/A')}",
        ]

        # 审批标准
        if gate.get('approval_criteria'):
            lines.append("\n### ✅ Approval Criteria")
            for criterion in gate.get('approval_criteria', []):
                required = " (Required)" if criterion.get('required') else ""
                lines.append(f"- [{criterion.get('label', '')}]{required}")
                lines.append(f"  - {criterion.get('criteria', '')}")

        # 拒绝标准
        if gate.get('rejection_criteria'):
            lines.append("\n### ❌ Rejection Criteria")
            for reason in gate.get('rejection_criteria', []):
                lines.append(f"- {reason}")

        # 检查清单
        if gate.get('checklist'):
            lines.append("\n### 📋 Checklist")
            for item in gate.get('checklist', []):
                status = "✅" if item.get('ok') else "❌"
                note = f" - {item.get('note', '')}" if item.get('note') else ""
                lines.append(f"- {status} {item.get('item', '')}{note}")

        # 上游分析摘要
        if upstream_summary:
            lines.append("\n### 📊 Upstream Analysis Summary")
            lines.append(upstream_summary)

        # 历史
        if gate.get('history'):
            lines.append("\n### 📜 Decision History")
            for h in gate.get('history', []):
                lines.append(f"- **{h.get('decided_at', '')}**: {h.get('option', '')} by {h.get('decided_by', '')}")
                if h.get('comment'):
                    lines.append(f"  - {h.get('comment', '')}")

        # 推荐决策
        lines.append("\n### 💡 Recommendation")
        lines.append(_generate_recommendation(gate))

        return "\n".join(lines)

    def _generate_recommendation(gate: Dict[str, Any]) -> str:
        """基于分析结果生成决策建议"""
        # 这里可以添加更复杂的逻辑来分析上游数据并给出建议
        return (
            "Please review the gate details and upstream analysis above, "
            "then decide to:\n"
            "- `/gate-review --approve {gate_id}`\n"
            "- `/gate-review --reject {gate_id}`\n"
            "- `/gate-review --revise {gate_id}`"
        ).format(gate_id=gate.get('gate_id', ''))

    # 执行对应的动作
    if action == "list":
        # 列出所有待审批 gates
        gates = api_gate_list_pending(project_dir)
        return {
            "action": "list",
            "result": {
                "count": len(gates),
                "gates": gates
            },
            "markdown": _format_gate_list(gates)
        }

    elif action == "show":
        gate_id = kwargs.get("gate_id")
        if not gate_id:
            return {
                "error": "gate_id is required for show action",
                "action": action
            }

        gate = api_gate_show(project_dir, gate_id)

        # 获取上游分析摘要
        depends_on = gate.get('depends_on', [])
        upstream_summary = _get_upstream_summary(project_dir, depends_on)

        return {
            "action": "show",
            "result": gate,
            "markdown": _format_gate_details(gate, upstream_summary)
        }

    elif action == "decide":
        gate_id = kwargs.get("gate_id")
        decision = kwargs.get("decision")
        comment = kwargs.get("comment", "")

        if not gate_id or not decision:
            return {
                "error": "gate_id and decision are required for decide action",
                "action": action,
                "provided": {
                    "gate_id": gate_id,
                    "decision": decision
                }
            }

        result = api_gate_decide(
            project_dir=project_dir,
            gate_id=gate_id,
            option=decision,
            comment=comment,
            checklist=kwargs.get("checklist"),
            decided_by=kwargs.get("decided_by", "user")
        )

        return {
            "action": "decide",
            "result": result,
            "markdown": f"\n## ✅ Gate Decision Submitted\n\n**Gate**: `{gate_id}`\n**Decision**: {decision}\n**Comment**: {comment}"
        }

    elif action == "report":
        # 生成完整的决策报告
        gates = api_gate_list_pending(project_dir)
        report_lines = [
            "# 🚪 Gate Review Report",
            f"\n**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"**Pending Gates**: {len(gates)}",
        ]

        for gate in gates:
            gate_id = gate.get('id')  # 使用 'id' 而不是 'gate_id'
            gate_details = api_gate_show(project_dir, gate_id)
            depends_on = gate_details.get('depends_on', [])
            upstream_summary = _get_upstream_summary(project_dir, depends_on)

            report_lines.append(_format_gate_details(gate_details, upstream_summary))

        return {
            "action": "report",
            "result": {
                "total_gates": len(gates),
                "gates": gates
            },
            "markdown": "\n".join(report_lines)
        }

    else:
        return {
            "error": f"Unknown action: {action}",
            "valid_actions": ["list", "show", "decide", "report"]
        }


# ============================================
# 导出所有 API 函数
# ============================================

__all__ = [
    # PM Agent API
    "api_get_state",
    "api_list_ready_steps",
    "api_run_step",
    "api_run_step_async",
    "api_next_step",
    # Gate Assistant API
    "api_gate_list_pending",
    "api_gate_show",
    "api_gate_decide",
    # Tool Handlers
    "pm_workflow_handler",
    "gate_approval_handler",
    "gate_review_handler",
]
