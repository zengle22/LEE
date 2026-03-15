"""
LEE Orchestrator — Auto Check Gate Runner

处理 type: auto_check 门禁 (kind: gate)

auto_check 门禁通过评估 check 表达式自动判断是否通过，无需人工审批。
"""

from __future__ import annotations

import re
import uuid
from datetime import datetime
from typing import Any, Dict
import yaml

from lee.orchestrator.storage.models import StepResult
from lee.orchestrator.execution.runners.base import StepRunnerBase, RunnerContext


class AutoCheckGateRunner(StepRunnerBase):
    """Auto Check Gate 步骤运行器"""

    def can_handle(self, step_kind: str) -> bool:
        """
        判断是否可以处理该步骤

        处理条件：
        - kind == "auto_check"
        - kind == "auto_check_gate"（兼容旧分发入口）

        注意：kind == "gate" 且 type == "auto_check" 的情况由 orchestrator
        直接路由到 _run_auto_check_gate_step 方法，不通过 registry 分发。
        """
        return step_kind in ("auto_check", "auto_check_gate")

    async def execute(
        self,
        workflow_id: str,
        step,
        ctx: RunnerContext,
    ) -> StepResult:
        """
        执行自动检查门禁

        流程：
        1. 从上下文获取已完成的步骤输出
        2. 评估 check 条件表达式
        3. 根据结果完成步骤或失败
        4. 更新 task_execution 状态（如果存在）
        """
        from lee.orchestrator.storage.models import TaskExecutionStatus
        import logging

        # 获取工作流上下文
        instance = await ctx.store.get_workflow(workflow_id)
        if not instance:
            raise ValueError(f"Workflow not found: {workflow_id}")

        step_outputs = instance.data.get("step_outputs", {})

        # 获取门禁配置
        gate_config = step.config.get("gate", {}) if step.config else {}
        check_expression = gate_config.get("check", "")

        # P0-5: 记录门禁检查开始日志
        logging.info(f"[AutoCheckGate] Starting check for step {step.id}: {check_expression}")

        # 构建评估上下文（合并所有已完成步骤的输出）
        eval_context = self._build_eval_context(step_outputs)

        # 评估 check 表达式
        check_passed = self._evaluate_check(check_expression, eval_context)

        # P0-5: 记录评估结果日志
        logging.info(f"[AutoCheckGate] Step {step.id} check result: {'PASSED' if check_passed else 'FAILED'}")

        # 构建输出数据
        output_data = {
            "auto_check_passed": check_passed,
            "check_expression": check_expression,
            "eval_context_keys": list(eval_context.keys()),
        }

        # 查找该步骤的 task_execution 记录
        executions = await ctx.store.get_task_executions(workflow_id)
        step_execution = None
        for exec_record in executions:
            if exec_record.step_name == step.id and exec_record.status == TaskExecutionStatus.RUNNING:
                step_execution = exec_record
                break

        if check_passed:
            # 通过：完成步骤
            result = await ctx.state_machine.complete_step(
                workflow_id,
                step.id,
                output_data
            )

            # P0-1: 确保 task_execution 状态更新（BUG-2026-0038）
            if step_execution:
                try:
                    await ctx.store.update_task_execution(
                        step_execution.id,
                        TaskExecutionStatus.COMPLETED,
                        output_data=output_data,
                        completed_at=datetime.now(),
                    )
                    # P0-5: 记录 task_execution 更新日志
                    logging.info(f"[AutoCheckGate] Updated task_execution {step_execution.id} to COMPLETED")
                except Exception as update_error:
                    # 记录错误但不抛出，因为步骤已经完成
                    logging.error(f"[AutoCheckGate] Failed to update task_execution {step_execution.id}: {update_error}")

            return StepResult(
                status="success",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"Auto check passed: {check_expression}",
                output=output_data,
            )
        else:
            # 失败：门禁失败
            on_fail = gate_config.get("on_fail", {})
            action = on_fail.get("action", "fail_step")

            error_message = f"Auto check failed: {check_expression}"

            # P0-5: 记录门禁失败日志
            logging.warning(f"[AutoCheckGate] Step {step.id} check failed: {error_message}")

            if action in ("human_gate", "human_review"):
                blocked_result = await self._block_for_human_gate(
                    workflow_id=workflow_id,
                    step=step,
                    ctx=ctx,
                    gate_config=gate_config,
                    output_data=output_data,
                    error_message=error_message,
                )

                if step_execution:
                    try:
                        await ctx.store.update_task_execution(
                            step_execution.id,
                            TaskExecutionStatus.FAILED,
                            error_message=error_message,
                            output_data=output_data,
                            completed_at=datetime.now(),
                        )
                        logging.info(f"[AutoCheckGate] Updated task_execution {step_execution.id} to FAILED")
                    except Exception as update_error:
                        logging.error(f"[AutoCheckGate] Failed to update task_execution {step_execution.id}: {update_error}")

                return blocked_result
            if action == "fail_step":
                await ctx.state_machine.fail_step(
                    workflow_id,
                    step.id,
                    error_message
                )

                # P0-1: 更新 task_execution 状态为 FAILED
                if step_execution:
                    try:
                        await ctx.store.update_task_execution(
                            step_execution.id,
                            TaskExecutionStatus.FAILED,
                            error_message=error_message,
                            completed_at=datetime.now(),
                        )
                        # P0-5: 记录 task_execution 更新日志
                        logging.info(f"[AutoCheckGate] Updated task_execution {step_execution.id} to FAILED")
                    except Exception as update_error:
                        logging.error(f"[AutoCheckGate] Failed to update task_execution {step_execution.id}: {update_error}")

                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=error_message,
                    output=output_data,
                )
            elif action == "fail_phase":
                # 失败整个 Phase
                await ctx.state_machine.fail_step(
                    workflow_id,
                    step.id,
                    error_message
                )

                # P0-1: 更新 task_execution 状态为 FAILED
                if step_execution:
                    try:
                        await ctx.store.update_task_execution(
                            step_execution.id,
                            TaskExecutionStatus.FAILED,
                            error_message=error_message,
                            completed_at=datetime.now(),
                        )
                        # P0-5: 记录 task_execution 更新日志
                        logging.info(f"[AutoCheckGate] Updated task_execution {step_execution.id} to FAILED")
                    except Exception as update_error:
                        logging.error(f"[AutoCheckGate] Failed to update task_execution {step_execution.id}: {update_error}")

                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=error_message,
                    output=output_data,
                )
            else:
                # 默认 fail_step
                await ctx.state_machine.fail_step(
                    workflow_id,
                    step.id,
                    error_message
                )

                # P0-1: 更新 task_execution 状态为 FAILED
                if step_execution:
                    try:
                        await ctx.store.update_task_execution(
                            step_execution.id,
                            TaskExecutionStatus.FAILED,
                            error_message=error_message,
                            completed_at=datetime.now(),
                        )
                        # P0-5: 记录 task_execution 更新日志
                        logging.info(f"[AutoCheckGate] Updated task_execution {step_execution.id} to FAILED")
                    except Exception as update_error:
                        logging.error(f"[AutoCheckGate] Failed to update task_execution {step_execution.id}: {update_error}")

                return StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=workflow_id,
                    message=error_message,
                    output=output_data,
                )

    async def _block_for_human_gate(
        self,
        *,
        workflow_id: str,
        step,
        ctx: RunnerContext,
        gate_config: Dict[str, Any],
        output_data: Dict[str, Any],
        error_message: str,
    ) -> StepResult:
        from lee.orchestrator.storage.models import GateApproval, GateStatus, WorkflowStatus

        await ctx.store.update_workflow_status(workflow_id, WorkflowStatus.PAUSED)

        on_reject = gate_config.get("on_reject", {}) or {}
        on_revise = gate_config.get("on_revise", {}) or {}

        default_reject_action = on_reject.get("action")
        default_reject_target = on_reject.get("target_step")
        default_revise_target = on_revise.get("target_step")
        reviewers = gate_config.get("reviewers", [])
        if isinstance(reviewers, str):
            try:
                reviewers = yaml.safe_load(reviewers) or []
            except Exception:
                reviewers = []
        approval_criteria = gate_config.get("approval_criteria", [])
        if isinstance(approval_criteria, str):
            try:
                approval_criteria = yaml.safe_load(approval_criteria) or []
            except Exception:
                approval_criteria = [approval_criteria]

        gate_id_base = step.gate_id or f"gate_{workflow_id}_{step.id}"
        pending_gates = await ctx.store.get_pending_gates(workflow_id)
        existing_pending_gate = next(
            (
                gate
                for gate in pending_gates
                if gate.step_id == step.id and gate.status == GateStatus.PENDING
            ),
            None,
        )
        if existing_pending_gate is not None:
            return StepResult(
                status="blocked",
                blocked_reason="human_gate",
                step_id=step.id,
                workflow_id=workflow_id,
                message=f"{error_message}; waiting for human review at gate: {existing_pending_gate.gate_id}",
                output=output_data,
            )

        gate_id_value = gate_id_base
        existing_gate = await ctx.store.get_gate_approval(workflow_id, gate_id_base)
        if existing_gate is not None:
            gate_id_value = f"{gate_id_base}_{uuid.uuid4().hex[:8]}"
        gate_approval = GateApproval(
            workflow_id=workflow_id,
            gate_id=gate_id_value,
            step_id=step.id,
            status=GateStatus.PENDING,
            approval_criteria=approval_criteria,
            reviewers=reviewers,
            version=1,
            default_reject_action=default_reject_action,
            default_reject_target=default_reject_target,
            default_revise_target=default_revise_target,
            structured_feedback=output_data,
        )
        await ctx.store.create_gate_approval(gate_approval)

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
            message=f"{error_message}; waiting for human review at gate: {gate_id_value}",
            output=output_data,
        )

    def _build_eval_context(self, step_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """
        构建评估上下文

        将所有步骤输出合并为一个扁平的字典，支持通过路径访问嵌套值。
        """
        context = {}

        for step_id, output_data in step_outputs.items():
            if isinstance(output_data, dict):
                # 直接合并顶层键
                context.update(output_data)

                # 同时以 step_id 为键保存完整输出
                context[f"_{step_id}"] = output_data

                # 扁平化嵌套字典（顶层可直接访问）
                self._flatten_dict(output_data, context)

                # 同时保留带 step_id 前缀的路径，便于定向引用
                self._flatten_dict(output_data, context, prefix=f"{step_id}")

        return context

    def _flatten_dict(
        self,
        d: Dict[str, Any],
        context: Dict[str, Any],
        prefix: str = ""
    ) -> None:
        """扁平化嵌套字典，支持点路径访问"""
        for key, value in d.items():
            new_key = f"{prefix}.{key}" if prefix else key
            if isinstance(value, dict):
                self._flatten_dict(value, context, new_key)
            else:
                context[new_key] = value

    def _evaluate_check(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> bool:
        """
        评估检查表达式

        支持的表达式格式：
        - "variable == value" - 相等比较
        - "variable != value" - 不等比较
        - "variable" - 真值检查
        - "variable > value" - 大于比较
        - "variable < value" - 小于比较
        - "variable >= value" - 大于等于比较
        - "variable <= value" - 小于等于比较
        - "variable and variable" - 与运算
        - "variable or variable" - 或运算
        - "not variable" - 非运算
        """
        if not expression or not expression.strip():
            return True

        try:
            # 清理表达式
            expression = expression.strip()

            # 替换上下文变量为实际值
            evaluated_expr = self._substitute_variables(expression, context)

            # 安全评估表达式
            return self._safe_eval(evaluated_expr)

        except Exception as e:
            # 评估失败时返回 False
            return False

    def _substitute_variables(
        self,
        expression: str,
        context: Dict[str, Any]
    ) -> str:
        """
        将表达式中的变量名替换为实际值

        例如：expression = "status == 'healthy'", context = {"status": "healthy"}
        结果："healthy' == 'healthy'" -> "'healthy' == 'healthy'"
        """
        # 先保护字符串字面量，避免替换其中的单词
        literal_pattern = re.compile(r"""('(?:[^'\\]|\\.)*'|"(?:[^"\\]|\\.)*")""")
        literals: Dict[str, str] = {}

        def stash_literal(match):
            token = f"__LITERAL_{len(literals)}__"
            literals[token] = match.group(0)
            return token

        protected = literal_pattern.sub(stash_literal, expression)

        # 匹配变量名（支持点路径，如 environment_info.status）
        var_pattern = re.compile(r'\b([a-zA-Z_][a-zA-Z0-9_.]*)\b')

        def replace_var(match):
            var_name = match.group(1)

            # 跳过保护占位符和布尔/空值关键字
            if var_name in literals or var_name in {"True", "False", "None", "and", "or", "not"}:
                return match.group(0)

            # 从上下文获取值
            value = self._get_context_value(context, var_name)

            if value is None:
                # 变量不存在，返回 None 字符串
                return "None"

            # 根据值类型返回字符串表示
            if isinstance(value, str):
                return f"'{value}'"
            elif isinstance(value, bool):
                return str(value)
            elif value is None:
                return "None"
            else:
                return str(value)

        substituted = var_pattern.sub(replace_var, protected)
        for token, literal in literals.items():
            substituted = substituted.replace(token, literal)
        return substituted

    def _get_context_value(
        self,
        context: Dict[str, Any],
        path: str
    ) -> Any:
        """
        获取嵌套的上下文值

        支持点路径：environment_info.status -> context["environment_info"]["status"]
        """
        if path in context:
            return context[path]

        keys = path.split(".")
        value = context

        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None

        return value

    def _safe_eval(self, expression: str) -> bool:
        """
        安全评估表达式

        只允许布尔运算和比较运算，不允许函数调用和属性访问。
        """
        # 安全检查：拒绝危险模式
        dangerous_patterns = [
            "__", "import", "exec", "eval", "(", ")",
            "[", "]", "{", "}", "lambda", "def", "class"
        ]

        for pattern in dangerous_patterns:
            if pattern in expression:
                return False

        try:
            # 使用 eval 评估表达式（已通过安全过滤）
            result = eval(expression)
            return bool(result)
        except Exception:
            return False
