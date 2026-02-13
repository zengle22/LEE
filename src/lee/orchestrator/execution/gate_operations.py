"""
LEE Orchestrator v3.1 - 门禁操作 Mixin

提取自 orchestrator.py，包含门禁审批/拒绝/查询逻辑。
"""

from __future__ import annotations

import logging
from typing import List

from lee.orchestrator.storage.models import StepResult


logger = logging.getLogger(__name__)


class GateOperationsMixin:
    """门禁操作 Mixin — approve / reject / pending gates"""

    async def approve_gate(
        self,
        workflow_id: str,
        gate_id: str,
        approver: str,
        comments: str = ""
    ) -> StepResult:
        """
        批准人工门禁，恢复工作流执行

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            approver: 审批人
            comments: 审批意见

        Returns:
            步骤执行结果
        """
        from lee.orchestrator.storage.models import GateStatus, WorkflowStatus

        # v3.1: Gate 下游检查 - 在审批前评估门禁规则
        gate_evaluation = None
        rules_overridden = False
        try:
            # 尝试从 template 中获取 gate IR
            instance = await self.store.get_workflow(workflow_id)
            template = self.template_manager.get_template(instance.template_id)
            gate_ir = self._find_gate_ir(template, gate_id) if template else None

            if gate_ir:
                # 收集已完成步骤的 outputs 作为评估上下文
                eval_context = {}
                instance_data = instance.data or {}
                completed_steps = instance_data.get("completed_steps", [])
                step_outputs = instance_data.get("step_outputs", {})
                for step_id in completed_steps:
                    if step_id in step_outputs and isinstance(step_outputs[step_id], dict):
                        eval_context.update(step_outputs[step_id])

                gate_evaluation = self.gate_engine.evaluate_gate(gate_ir, eval_context)
                if gate_evaluation.verdict.value == "fail":
                    rules_overridden = True
                    logger.warning(
                        f"Gate {gate_id}: mandatory rules failed but overridden by human approval. "
                        f"Failed rules: {gate_evaluation.failed_rules}"
                    )
        except Exception as e:
            logger.warning(f"Gate evaluation error (non-blocking): {e}")

        # 更新门禁审批状态
        gate_approval = await self.store.update_gate_approval(
            workflow_id,
            gate_id,
            GateStatus.APPROVED,
            approver,
            comments
        )

        # 恢复工作流状态
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

        # v3.2: 记录门禁审批事件
        self.event_log.log_gate_approved(
            gate_id=gate_id,
            step_id=gate_approval.step_id,
            approver=approver,
            approval_id=f"{workflow_id}_{gate_id}",
        )

        # 构建输出（包含规则评估结果）
        gate_output = {"gate_approved": True, "approver": approver, "comments": comments}
        if gate_evaluation:
            gate_output["gate_evaluation"] = gate_evaluation.to_dict()
            gate_output["rules_overridden"] = rules_overridden

        # 完成门禁步骤
        result = await self.state_machine.complete_step(
            workflow_id,
            gate_approval.step_id,
            gate_output
        )

        # 检查工作流是否完成
        await self._check_workflow_completion(workflow_id)

        return StepResult(
            status="success",
            step_id=gate_approval.step_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} approved by {approver}",
            output=gate_output,
        )

    async def reject_gate(
        self,
        workflow_id: str,
        gate_id: str,
        rejecter: str,
        reason: str
    ) -> StepResult:
        """
        拒绝人工门禁，终止工作流

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            rejecter: 拒绝人
            reason: 拒绝原因

        Returns:
            步骤执行结果
        """
        from lee.orchestrator.storage.models import GateStatus, WorkflowStatus

        # 更新门禁审批状态
        gate_approval = await self.store.update_gate_approval(
            workflow_id,
            gate_id,
            GateStatus.REJECTED,
            rejecter,
            reason
        )

        # 将工作流标记为失败
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)

        # v3.2: 记录门禁拒绝事件
        self.event_log.log_gate_rejected(
            gate_id=gate_id,
            step_id=gate_approval.step_id,
            approver=rejecter,
            reason=reason,
        )

        return StepResult(
            status="failed",
            step_id=gate_approval.step_id,
            workflow_id=workflow_id,
            message=f"Gate {gate_id} rejected by {rejecter}: {reason}",
        )

    async def get_pending_gates(
        self,
        workflow_id: str
    ) -> List:
        """
        获取工作流的待审批门禁列表

        Args:
            workflow_id: 工作流 ID

        Returns:
            待审批门禁列表
        """
        from lee.orchestrator.storage.models import GateInfo

        gate_approvals = await self.store.get_pending_gates(workflow_id)

        return [
            GateInfo(
                gate_id=g.gate_id,
                workflow_id=g.workflow_id,
                step_id=g.step_id,
                status=g.status,
                reviewers=g.reviewers,
                approval_criteria=g.approval_criteria,
                approver=g.approver,
                comments=g.comments,
                created_at=g.created_at,
                decided_at=g.decided_at,
            )
            for g in gate_approvals
        ]

    def _find_gate_ir(self, template, gate_id: str):
        """
        从 template 中查找 Gate IR 定义

        v3.1: 支持从 spec-global IR 或 template steps 中查找 gate
        如果找不到 gate IR，返回 None（向后兼容）
        """
        # 尝试从 template 中查找带 gate 的 step
        if template and hasattr(template, 'steps'):
            for step in template.steps:
                if hasattr(step, 'gate_id') and step.gate_id == gate_id:
                    # 如果 step 有内联的 gate 定义，尝试解析
                    if hasattr(step, 'gate') and step.gate:
                        return step.gate
        # template_manager 目前不提供 GateIR 对象
        # 当 spec-global 全面迁移后，可以从 WorkflowIR.gates 中获取
        return None
