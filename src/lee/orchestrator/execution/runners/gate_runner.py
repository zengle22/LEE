"""
LEE Orchestrator — Gate Step Runners

包含:
  - HumanGateRunner: 处理人工审批门禁 (kind=human_gate)
  - ComplianceGateRunner: 处理合规门禁 (kind=compliance_gate)

从 step_runners.py 提取，保持原有逻辑不变。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import List

from lee.orchestrator.storage.models import StepResult
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext


class HumanGateRunner(StepRunnerBase):
    """Human Gate 步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "human_gate"

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        处理 Human Gate 步骤

        Human Gate 不调用 Executor，而是暂停工作流等待人工审批。
        """
        from lee.orchestrator.storage.models import WorkflowStatus, GateApproval, GateStatus

        # 暂停工作流
        await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        # 提取 gate 配置（从独立 gate 或 post_gate）
        gate_config = step.config.get("gate", {})
        if not gate_config and hasattr(step, 'gate_id'):
            gate_config = {
                "id": step.gate_id,
                "reviewers": step.config.get("reviewers", []),
                "approval_criteria": step.config.get("approval_criteria", []),
            }

        # v1.1: 提取默认动作配置 (P0-4)
        on_reject = gate_config.get("on_reject", {})
        on_revise = gate_config.get("on_revise", {})

        # 解析 reject 默认动作
        default_reject_action = None
        default_reject_target = None
        if on_reject:
            default_reject_action = on_reject.get("action")
            if default_reject_action == "rollback":
                default_reject_target = on_reject.get("target_step")

        # 解析 revise 默认动作
        default_revise_target = None
        if on_revise:
            # revise 总是执行 retry
            default_revise_target = on_revise.get("target_step")

        # 创建门禁审批记录（包含默认动作）
        # Include workflow_id in gate_id to make it unique across multiple workflows
        gate_id_value = step.gate_id or f"gate_{workflow_id}_{step.id}"
        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=gate_id_value,
            step_id=step.id,
            status=GateStatus.PENDING,
            approval_criteria=gate_config.get("approval_criteria", []),
            reviewers=gate_config.get("reviewers", []),
            version=1,  # v1.1: 初始版本号
            default_reject_action=default_reject_action,
            default_reject_target=default_reject_target,
            default_revise_target=default_revise_target,
        )
        await ctx.store.create_gate_approval(gate_approval)

        # v3.2: 记录门禁触发事件
        ctx.event_log.log_gate_triggered(
            gate_id=gate_id_value,
            step_id=step.id,
            gate_type="human",
            blocking=True,
        )

        return StepResult(
            status="blocked",
            blocked_reason="human_gate",
            step_id=step.id,
            workflow_id=workflow_id,
            message=f"Waiting for human approval at gate: {gate_id_value}",
            next_steps=[],
        )


class ComplianceGateRunner(StepRunnerBase):
    """合规门禁步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        return step_kind == "compliance_gate"

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        运行合规门禁步骤

        检查 AI 行为是否违规（mock/借口等）。
        违规 → 本轮测试无效。
        """
        from lee.orchestrator.verifiers.behavior_compliance import BehaviorComplianceVerifier

        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)

        # 获取输入数据
        inputs = step.input or []
        runner_output = {}
        confirmed_env_errors = []

        for inp in inputs:
            if isinstance(inp, dict):
                if "runner_output" in inp:
                    runner_output = inp["runner_output"]
                if "confirmed_env_errors" in inp:
                    confirmed_env_errors = inp["confirmed_env_errors"]

        # 执行合规检查
        verifier = BehaviorComplianceVerifier()
        context = {
            "runner_output": runner_output,
            "confirmed_env_errors": confirmed_env_errors,
            "config": step.config.get("config", {}) if step.config else {},
        }
        result = verifier.verify(context)

        # 保存检查结果
        run_id = instance.data.get("run_id", "RUN-UNKNOWN") if instance else "RUN-UNKNOWN"
        output_path = Path(ctx.project_root or ".") / f".workflow/compliance/{run_id}-{step.id}.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps({
            "status": result.status.value,
            "message": result.message,
            "details": result.details,
        }, indent=2, ensure_ascii=False), encoding="utf-8")

        output_data = {
            "compliant": result.status.value == "passed",
            "violations": result.details.get("violations", []) if result.details else [],
            "output_path": str(output_path),
        }

        if result.status.value == "passed":
            step_result = await ctx.state_machine.complete_step(
                workflow_id, step.id, output_data
            )
            return step_result
        else:
            await ctx.state_machine.fail_step(workflow_id, step.id, result.message)
            return StepResult(
                status="failed",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"AI behavior violation detected: {result.message}",
                output=output_data,
            )
