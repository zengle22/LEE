"""
LEE Orchestrator v3.1 - 门禁操作 Mixin

提取自 orchestrator.py，包含门禁审批/拒绝/查询逻辑。
"""

from __future__ import annotations

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.execution.artifacts.types import SSOTType
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

        # 检查 gate 是否存在
        gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)
        if gate_approval is None:
            logger.error(f"Gate not found: workflow_id={workflow_id}, gate_id={gate_id}")
            raise ValueError(f"Gate not found: {workflow_id}/{gate_id}")

        # 更新门禁审批状态
        gate_approval = await self.store.update_gate_approval(
            workflow_id,
            gate_id,
            GateStatus.APPROVED,
            approver,
            comments
        )

        # 检查更新是否成功
        if gate_approval is None:
            logger.error(f"Failed to update gate: workflow_id={workflow_id}, gate_id={gate_id}")
            raise RuntimeError(f"Failed to update gate approval: {workflow_id}/{gate_id}")

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

        await self._freeze_gate_targets(workflow_id, gate_approval.step_id)

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
        reason: str,
        action: Optional[str] = None,
        target_step: Optional[str] = None,
    ) -> StepResult:
        """
        拒绝人工门禁，执行指定动作（v1.1）

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            rejecter: 拒绝人
            reason: 拒绝原因
            action: 执行动作（rollback/spawn）可选，默认从配置读取
            target_step: 目标步骤（用于 rollback）

        Returns:
            步骤执行结果

        Raises:
            ValueError: 如果没有指定 action 且配置中也没有默认 action
        """
        from lee.orchestrator.storage.models import (
            GateStatus, WorkflowStatus, ConcurrentDecisionError
        )

        # 1. 获取 gate 配置（从 DB，不读 template）
        gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)

        if gate_approval is None:
            raise ValueError(f"Gate not found: {workflow_id}/{gate_id}")

        # 2. 确定执行 action
        if action is None:
            # 使用存储的默认 action
            default_action = gate_approval.default_reject_action
            if default_action:
                action = default_action
                target_step = target_step or gate_approval.default_reject_target

        if action is None:
            raise ValueError(
                f"Reject must specify action. "
                f"Configure on_reject.action or use --action parameter."
            )

        # 3. 使用版本检查更新 gate 状态
        updated_gate = await self.store.update_gate_approval_with_version(
            workflow_id,
            gate_id,
            GateStatus.REJECTED,
            rejecter,
            reason,
            expected_version=gate_approval.version,
            decision_action=action,
            target_step=target_step,
        )

        if updated_gate is None:
            raise ConcurrentDecisionError(
                f"Gate {gate_id} was modified by another user. "
                f"Please refresh and try again."
            )

        # 4. 记录拒绝事件
        self.event_log.log_gate_rejected(
            gate_id=gate_id,
            step_id=gate_approval.step_id,
            approver=rejecter,
            reason=reason,
            action=action,
        )

        # 5. 执行动作
        if action == "rollback":
            return await self._execute_rollback(
                workflow_id, gate_id, target_step, rejecter, reason
            )
        elif action == "spawn":
            return await self._execute_spawn_workflow(
                workflow_id, gate_id, rejecter, reason
            )
        else:
            # 未知 action，标记 FAILED
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.FAILED)
            return StepResult(
                status="failed",
                step_id=gate_approval.step_id,
                workflow_id=workflow_id,
                message=f"Gate {gate_id} rejected with unknown action '{action}': {reason}",
            )

    async def revise_gate(
        self,
        workflow_id: str,
        gate_id: str,
        reviewer: str,
        reason: str,
        target_step: Optional[str] = None,
        structured_feedback: Optional[dict] = None,
    ) -> StepResult:
        """
        修订门禁，重试步骤（v1.1 新增）

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            reviewer: 评审人
            reason: 修改意见
            target_step: 重试目标步骤
            structured_feedback: 结构化反馈

        Returns:
            步骤执行结果
        """
        from lee.orchestrator.storage.models import (
            GateStatus, ConcurrentDecisionError
        )

        # 1. 获取 gate 配置
        gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)

        if gate_approval is None:
            raise ValueError(f"Gate not found: {workflow_id}/{gate_id}")

        # 2. 确定重试目标
        if target_step is None:
            # 使用默认 target
            target_step = gate_approval.default_revise_target or gate_approval.step_id

        # 3. 更新 gate 状态为 REVISED
        updated_gate = await self.store.update_gate_approval_with_version(
            workflow_id,
            gate_id,
            GateStatus.REVISED,
            reviewer,
            reason,
            expected_version=gate_approval.version,
            decision_action="retry",
            target_step=target_step,
            structured_feedback=structured_feedback,
        )

        if updated_gate is None:
            raise ConcurrentDecisionError(
                f"Gate {gate_id} was modified by another user."
            )

        # 4. 记录修订事件
        self.event_log.log_gate_revised(
            gate_id=gate_id,
            step_id=gate_approval.step_id,
            reviewer=reviewer,
            reason=reason,
        )

        # 5. 使用 rewind_to 执行重试
        return await self.state_machine.rewind_to(
            workflow_id, target_step, mode="retry", reason=reason
        )

    async def flag_gate(
        self,
        workflow_id: str,
        gate_id: str,
        reporter: str,
        issues: list,
        continue_workflow: bool = True,
    ) -> StepResult:
        """
        标记门禁问题（v1.1 新增）

        Args:
            workflow_id: 工作流 ID
            gate_id: 门禁 ID
            reporter: 报告人
            issues: 问题列表
            continue_workflow: 是否继续工作流

        Returns:
            步骤执行结果
        """
        from lee.orchestrator.storage.models import (
            GateStatus, ConcurrentDecisionError
        )

        # 1. 获取 gate
        gate_approval = await self.store.get_gate_approval(workflow_id, gate_id)

        if gate_approval is None:
            raise ValueError(f"Gate not found: {workflow_id}/{gate_id}")

        # 2. 更新 gate 状态为 FLAGGED
        updated_gate = await self.store.update_gate_approval_with_version(
            workflow_id,
            gate_id,
            GateStatus.FLAGGED,
            reporter,
            "; ".join(issues),
            expected_version=gate_approval.version,
            issues=issues,
        )

        if updated_gate is None:
            raise ConcurrentDecisionError(
                f"Gate {gate_id} was modified by another user."
            )

        # 3. 记录标记事件
        self.event_log.log_gate_flagged(
            gate_id=gate_id,
            step_id=gate_approval.step_id,
            reporter=reporter,
            issues=issues,
        )

        # 4. 根据配置决定工作流状态
        if continue_workflow:
            # 恢复工作流运行
            await self.store.update_workflow_status(workflow_id, WorkflowStatus.RUNNING)

            # 完成门禁步骤
            await self.state_machine.complete_step(
                workflow_id, gate_id,
                {"flagged": True, "issues": issues}
            )

            return StepResult(
                status="flagged",
                step_id=gate_id,
                workflow_id=workflow_id,
                message=f"Gate {gate_id} flagged with {len(issues)} issue(s), workflow continues",
            )
        else:
            # 保持 PAUSED
            return StepResult(
                status="paused",
                step_id=gate_id,
                workflow_id=workflow_id,
                message=f"Gate {gate_id} flagged, workflow paused for review",
            )

    async def _execute_rollback(
        self,
        workflow_id: str,
        gate_id: str,
        target_step: str,
        rejecter: str,
        reason: str,
    ) -> StepResult:
        """执行回退动作"""
        # 使用 state_machine.rewind_to 原语
        return await self.state_machine.rewind_to(
            workflow_id, target_step, mode="rollback", reason=reason
        )

    async def _execute_spawn_workflow(
        self,
        workflow_id: str,
        gate_id: str,
        requester: str,
        reason: str,
    ) -> StepResult:
        """执行派生新工作流动作"""
        # 获取当前工作流实例
        instance = await self.store.get_workflow(workflow_id)

        # 创建新工作流实例
        new_workflow_id = await self.orchestrator.create_workflow(
            template_id=instance.template_id,
            project_dir=getattr(self.orchestrator, 'project_dir', '.'),
            parent_workflow_id=workflow_id,
            metadata={
                "spawned_from_gate": gate_id,
                "spawn_reason": reason,
            },
        )

        # 将原工作流标记为 SUPERSEDED
        await self.store.update_workflow_status(workflow_id, WorkflowStatus.SUPERSEDED)

        # 记录事件
        self.event_log.log_workflow_spawned(
            workflow_id=workflow_id,
            new_workflow_id=new_workflow_id,
            gate_id=gate_id,
            reason=reason,
        )

        return StepResult(
            status="spawned",
            step_id=gate_id,
            workflow_id=workflow_id,
            message=f"Spawned new workflow {new_workflow_id} from gate {gate_id}",
            output={"new_workflow_id": new_workflow_id},
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

    async def _freeze_gate_targets(self, workflow_id: str, gate_step_id: str) -> None:
        try:
            instance = await self.store.get_workflow(workflow_id)
        except Exception as exc:
            logger.warning(f"Freeze target resolution failed for workflow {workflow_id}: {exc}")
            return
        if instance is None:
            return

        target_ids = self._collect_gate_freeze_target_ids(instance, gate_step_id)
        if not target_ids:
            return

        from lee.orchestrator.execution.artifacts import ArtifactManager

        manager = ArtifactManager(project_root=Path(self.project_root or ".").resolve())
        for artifact_id in target_ids:
            try:
                metadata = manager.get(artifact_id)
                if metadata is None:
                    continue
                manager.freeze(artifact_id)
            except Exception as exc:
                logger.warning(f"Freeze target {artifact_id} failed: {exc}")

        await self._publish_gate_canonical_ssot(instance, workflow_id, gate_step_id, manager)

    async def _publish_gate_canonical_ssot(
        self,
        instance,
        workflow_id: str,
        gate_step_id: str,
        manager,
    ) -> None:
        """发布Gate产出的规范SSOT对象到标准目录"""
        payloads = self._collect_gate_freeze_payloads(instance, gate_step_id)
        if not payloads:
            return

        published_refs: Dict[str, Dict[str, Any]] = {}
        for payload in payloads:
            for candidate in self._collect_publishable_ssot_candidates(payload):
                published = self._materialize_canonical_ssot_candidate(candidate, manager)
                if not published:
                    continue
                alias = f"{gate_step_id}_ref"
                published_refs[alias] = published

        if not published_refs:
            return

        instance_data = dict(getattr(instance, "data", {}) or {})
        params = dict(instance_data.get("params", {}) or {})
        params.update(published_refs)
        instance_data["params"] = params

        step_outputs = dict(instance_data.get("step_outputs", {}) or {})
        gate_output = dict(step_outputs.get(gate_step_id, {}) or {})
        gate_output.update(published_refs)
        step_outputs[gate_step_id] = gate_output
        instance_data["step_outputs"] = step_outputs

        await self.store.update_workflow_data(workflow_id, instance_data)

    def _collect_gate_freeze_payloads(self, instance, gate_step_id: str) -> List[Any]:
        """收集Gate freeze所需的payloads，支持别名解析"""
        instance_data = getattr(instance, "data", {}) or {}
        step_output_map = instance_data.get("step_outputs", {}) or {}
        params = instance_data.get("params", {}) or {}

        sources: List[str] = []
        try:
            resolved = self.state_machine._resolve_step_inputs_for_freeze(gate_step_id, instance)
            if isinstance(resolved, list):
                sources.extend(resolved)
        except Exception:
            pass

        payloads: List[Any] = []
        for source in sources:
            for key in (source, *self._freeze_source_aliases(source)):
                if key in step_output_map:
                    payloads.append(step_output_map[key])
                    break
                if key in params:
                    payloads.append(params[key])
                    break

        if not payloads:
            payloads.extend(step_output_map.values())
        return payloads

    @staticmethod
    def _freeze_source_aliases(source: str) -> List[str]:
        """生成freeze源的别名列表"""
        if not isinstance(source, str):
            return []
        if source.endswith("_freeze_ref"):
            return [source[:-4]]
        if source.endswith("_freeze"):
            return [f"{source}_ref"]
        return []

    def _collect_publishable_ssot_candidates(self, payload: Any) -> List[Dict[str, Any]]:
        """从payload中收集可发布的SSOT候选对象"""
        collected: List[Dict[str, Any]] = []
        self._walk_publishable_candidates(payload, collected)
        return collected

    def _walk_publishable_candidates(self, payload: Any, collected: List[Dict[str, Any]]) -> None:
        """递归遍历payload寻找SSOT候选"""
        if isinstance(payload, dict):
            if self._candidate_ssot_type(payload):
                collected.append(payload)
            for value in payload.values():
                if isinstance(value, (dict, list)):
                    self._walk_publishable_candidates(value, collected)
        elif isinstance(payload, list):
            for item in payload:
                self._walk_publishable_candidates(item, collected)

    def _candidate_ssot_type(self, payload: Dict[str, Any]) -> Optional[str]:
        """识别payload是否为可物化的SSOT候选类型"""
        if not isinstance(payload, dict):
            return None
        ssot_identity = payload.get("ssot_identity")
        if isinstance(ssot_identity, dict) and str(ssot_identity.get("ssot_type", "")).upper() == "SRC":
            if isinstance(payload.get("src_structure"), dict):
                return "SRC"
        ssot = payload.get("ssot")
        if isinstance(ssot, dict) and str(ssot.get("ssot_type", "")).upper() == "EPIC":
            if payload.get("title") and payload.get("goal"):
                return "EPIC"
        return None

    def _materialize_canonical_ssot_candidate(self, payload: Dict[str, Any], manager) -> Optional[Dict[str, Any]]:
        """物化SSOT候选对象为规范制品"""
        candidate_type = self._candidate_ssot_type(payload)
        if candidate_type == "SRC":
            return self._materialize_src_candidate(payload, manager)
        if candidate_type == "EPIC":
            return self._materialize_epic_candidate(payload, manager)
        return None

    def _materialize_src_candidate(self, payload: Dict[str, Any], manager) -> Dict[str, Any]:
        """将SRC候选物化为规范SRC文件"""
        src_structure = payload.get("src_structure", {}) or {}
        governance_refs = payload.get("governance_refs", {}) or {}
        title = str(src_structure.get("title") or "Untitled SRC")
        derived_ref = (
            ((payload.get("ssot_identity") or {}).get("derived_from"))
            or ((governance_refs.get("source_refs") or [None])[0])
        )
        source_refs = self._dedupe_strings([
            *(governance_refs.get("source_refs") or []),
            derived_ref,
        ])

        content_lines = [f"# {title}", ""]

        problem_statement = src_structure.get("problem_statement")
        if problem_statement:
            content_lines.extend(["## 问题陈述", "", str(problem_statement), ""])

        content = "\n".join(content_lines)

        metadata = manager.create_ssot(
            ssot_type=SSOTType.SRC,
            title=title,
            content=content,
            run_id=derived_ref or "gate-materialize",
            parent_id=None,
        )
        return {"artifact_id": metadata.id, "path": metadata.path}

    def _materialize_epic_candidate(self, payload: Dict[str, Any], manager) -> Dict[str, Any]:
        """将EPIC候选物化为规范EPIC文件"""
        title = str(payload.get("title") or "Untitled Epic")
        goal = str(payload.get("goal") or "")
        scope = payload.get("scope", []) or []
        non_goals = payload.get("non_goals", []) or []
        success_metrics = payload.get("success_metrics", []) or []
        priority = str(payload.get("priority") or "P1")
        source_refs = self._dedupe_strings(payload.get("source_refs", []))
        ssot = payload.get("ssot", {}) or {}
        derived_from = ssot.get("derived_from")

        content_lines = [f"# {title}", ""]

        if goal:
            content_lines.extend(["## 目标", "", goal, ""])

        if scope:
            content_lines.extend(["## 范围", ""])
            for item in scope:
                content_lines.append(f"- {item}")
            content_lines.append("")

        if non_goals:
            content_lines.extend(["## 非目标", ""])
            for item in non_goals:
                content_lines.append(f"- {item}")
            content_lines.append("")

        if success_metrics:
            content_lines.extend(["## 成功标准", ""])
            for item in success_metrics:
                content_lines.append(f"- {item}")
            content_lines.append("")

        content = "\n".join(content_lines)

        src_root_id = None
        parent_id = None
        for ref in source_refs:
            ref_root = ref.split("#", 1)[0].strip()
            if ref_root.startswith("SRC-"):
                src_root_id = ref_root
                parent_id = ref_root
                break
        if parent_id is None and isinstance(derived_from, str) and derived_from.startswith("SRC-"):
            parent_id = derived_from
            src_root_id = derived_from
        properties = {"src_root_id": src_root_id} if src_root_id else None

        metadata = manager.create_ssot(
            ssot_type=SSOTType.EPIC,
            title=title,
            content=content,
            run_id=derived_from or "gate-materialize",
            parent_id=parent_id,
            source_refs=source_refs,
            properties=properties,
        )

        # 冻结为正式EPIC
        frozen = manager.freeze(metadata.id)
        return {"artifact_id": frozen.id, "path": frozen.path}

    def _dedupe_strings(self, items: List[Any]) -> List[str]:
        """去重字符串列表"""
        seen: set = set()
        result: List[str] = []
        for item in items:
            if isinstance(item, str) and item.strip():
                s = item.strip()
                if s not in seen:
                    seen.add(s)
                    result.append(s)
        return result

    def _collect_gate_freeze_target_ids(self, instance, gate_step_id: str) -> List[str]:
        payloads = self._collect_gate_freeze_payloads(instance, gate_step_id)
        collected: List[str] = []
        for payload in payloads:
            self._collect_artifact_ids_from_payload(payload, collected)
        deduped: List[str] = []
        for artifact_id in collected:
            if artifact_id not in deduped:
                deduped.append(artifact_id)
        return deduped

    def _collect_artifact_ids_from_payload(self, payload: Any, collected: List[str]) -> None:
        if isinstance(payload, dict):
            if self._is_ssot_like_id(payload.get("id")):
                collected.append(str(payload["id"]))
            for key in ("ssot_materialized", "frozen_inputs", "business_output", "structured_payload", "outputs"):
                value = payload.get(key)
                if value is not None:
                    self._collect_artifact_ids_from_payload(value, collected)
            for value in payload.values():
                if isinstance(value, (dict, list)):
                    self._collect_artifact_ids_from_payload(value, collected)
        elif isinstance(payload, list):
            for item in payload:
                self._collect_artifact_ids_from_payload(item, collected)
        elif isinstance(payload, str) and self._is_ssot_like_id(payload):
            collected.append(payload)

    @staticmethod
    def _is_ssot_like_id(value: Any) -> bool:
        if not isinstance(value, str):
            return False
        return re.match(r"^(SRC|ADR|EPIC|FEAT|TECH|UI|TASK|TESTSET|DEVPLAN|TESTPLAN|REL|REPORT|BUG|TC|EVI)-", value) is not None
