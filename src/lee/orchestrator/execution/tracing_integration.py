"""
Tracing Integration - StateMachine 与 TraceLog 的集成层

将状态机的事件自动记录为 spans。
这是"日志是基础设施"原则的实现。

使用方式:
    from orchestrator.core import StateMachine
    from orchestrator.core.tracing_integration import TracedStateMachine

    sm = TracedStateMachine(project_dir)
    # 所有 StateMachine 操作自动记录 spans
"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
from datetime import datetime

from .state_machine import StateMachine, StepState, RunState
from .trace import (
    TraceLog,
    SpanType,
    SpanStatus,
    ArtifactType,
    AgentInfo,
    GateInfo,
    Metrics,
)


class TracedStateMachine(StateMachine):
    """
    带追踪功能的状态机

    继承 StateMachine，在关键操作点自动记录 spans。
    日志记录对调用者透明，不需要 Agent 主动配合。
    """

    def __init__(self, project_dir: str):
        super().__init__(project_dir)
        self._trace_log: Optional[TraceLog] = None
        self._step_spans: Dict[str, str] = {}  # step_id -> span_id
        self._gate_spans: Dict[str, str] = {}  # gate_id -> span_id

    def _find_active_span_for_step(self, step_id: str) -> Optional[str]:
        """查找步骤对应的活跃 span ID

        从追踪日志中查找最近的、仍在运行的 span。
        这解决了跨进程/跨实例的 span 映射问题。
        """
        # 先检查内存缓存
        if step_id in self._step_spans:
            return self._step_spans[step_id]

        # 从追踪日志查找
        trace_log = self._get_trace_log()
        spans = trace_log.get_spans(status=SpanStatus.RUNNING)
        for span in reversed(spans):  # 从最新开始
            if span.name == f"step.{step_id}":
                self._step_spans[step_id] = span.span_id
                return span.span_id
        return None

    def _find_active_span_for_gate(self, gate_id: str) -> Optional[str]:
        """查找门禁对应的活跃 span ID"""
        # 先检查内存缓存
        if gate_id in self._gate_spans:
            return self._gate_spans[gate_id]

        # 从追踪日志查找
        trace_log = self._get_trace_log()
        spans = trace_log.get_spans(status=SpanStatus.RUNNING, span_type=SpanType.GATE)
        for span in reversed(spans):
            if span.name == f"gate.{gate_id}":
                self._gate_spans[gate_id] = span.span_id
                return span.span_id
        return None

    def _get_trace_log(self, run_id: str = None) -> TraceLog:
        """获取或创建 TraceLog

        如果没有传入 run_id，尝试从已加载的状态中获取。
        这确保追踪日志与现有工作流运行关联。
        """
        if self._trace_log is None:
            # 如果没有传入 run_id，尝试从状态中获取
            if run_id is None and self._state:
                run_id = self._state.get("run_id")
            self._trace_log = TraceLog(self.project_dir, run_id)
        return self._trace_log

    # ============================================
    # 重写关键方法以添加追踪
    # ============================================

    def init(self, workflow: Dict, run_id: str = None) -> str:
        """初始化工作流运行 (带追踪)"""
        # 先创建 TraceLog 以获取 run_id
        trace_log = self._get_trace_log(run_id)
        actual_run_id = trace_log.run_id

        # 记录 orchestrator span
        span = trace_log.start_span(
            span_type=SpanType.ORCHESTRATOR,
            name="orchestrator.init",
            input_data={
                "workflow_id": workflow.get("id"),
                "workflow_name": workflow.get("name"),
            }
        )

        try:
            # 调用父类方法
            result_run_id = super().init(workflow, actual_run_id)

            # 完成 span
            trace_log.complete_span(
                span.span_id,
                output_data={
                    "run_id": result_run_id,
                    "steps_count": len(self._state.get("steps", {})),
                }
            )

            return result_run_id

        except Exception as e:
            trace_log.fail_span(
                span.span_id,
                error_code="INIT_FAILED",
                error_message=str(e)
            )
            raise

    def start_step(self, step_id: str, agent_id: str = None, token: str = None) -> Tuple[bool, Optional[str]]:
        """开始执行步骤 (带追踪)"""
        trace_log = self._get_trace_log()

        # 记录 step span
        span = trace_log.start_span(
            span_type=SpanType.ORCHESTRATOR,
            name=f"step.{step_id}",
            agent=AgentInfo(agent_id=agent_id or "unknown") if agent_id else None,
            input_data={
                "step_id": step_id,
                "agent_id": agent_id,
                "token": token[:8] + "..." if token else None,  # 脱敏
            }
        )

        # 记录 step -> span 映射
        self._step_spans[step_id] = span.span_id

        # 调用父类方法
        success, reason = super().start_step(step_id, agent_id, token)

        if not success:
            trace_log.fail_span(
                span.span_id,
                error_code="START_BLOCKED",
                error_message=reason or "Unknown reason"
            )
            del self._step_spans[step_id]

        return success, reason

    def complete_step(self, step_id: str, outputs: List[str] = None) -> Tuple[bool, Optional[str]]:
        """完成步骤 (带追踪)"""
        trace_log = self._get_trace_log()

        # 调用父类方法
        success, reason = super().complete_step(step_id, outputs)

        # 记录产物 (使用查找方法支持跨进程)
        if success and outputs:
            span_id = self._find_active_span_for_step(step_id)
            if span_id:
                for output_path in outputs:
                    full_path = self.project_dir / output_path
                    if full_path.exists():
                        import hashlib
                        content_hash = hashlib.sha256(
                            full_path.read_bytes()
                        ).hexdigest()[:16]

                        trace_log.log_artifact(
                            span_id=span_id,
                            artifact_type=ArtifactType.FILE_CREATED,
                            path=output_path,
                            content_hash=content_hash,
                            size_bytes=full_path.stat().st_size
                        )

        return success, reason

    def finalize_step(self, step_id: str) -> Tuple[bool, Optional[str]]:
        """最终完成步骤 (带追踪)"""
        trace_log = self._get_trace_log()

        # 调用父类方法
        success, reason = super().finalize_step(step_id)

        # 完成 span (使用查找方法支持跨进程)
        span_id = self._find_active_span_for_step(step_id)
        if span_id:
            if success:
                trace_log.complete_span(
                    span_id,
                    output_data={
                        "step_id": step_id,
                        "final_state": "completed",
                    }
                )
            else:
                trace_log.fail_span(
                    span_id,
                    error_code="FINALIZE_FAILED",
                    error_message=reason or "Unknown reason"
                )
            del self._step_spans[step_id]

        return success, reason

    def fail_step(self, step_id: str, error: str) -> Tuple[bool, Optional[str]]:
        """标记步骤失败 (带追踪)"""
        trace_log = self._get_trace_log()

        # 调用父类方法
        success, reason = super().fail_step(step_id, error)

        # 完成 span (使用查找方法支持跨进程)
        span_id = self._find_active_span_for_step(step_id)
        if span_id:
            trace_log.fail_span(
                span_id,
                error_code="STEP_FAILED",
                error_message=error
            )
            del self._step_spans[step_id]

        return success, reason

    def set_validation_result(self, step_id: str, passed: bool, details: Dict = None) -> Tuple[bool, Optional[str]]:
        """设置验证结果 (带追踪)

        如果验证通过且没有门禁，完成步骤 span。
        如果验证失败，标记 span 失败。
        """
        trace_log = self._get_trace_log()

        # 获取步骤的门禁信息 (在调用父类方法之前)
        state = self.load()
        step = state["steps"].get(step_id, {})
        has_gate = step.get("gate_id") is not None

        # 调用父类方法
        success, reason = super().set_validation_result(step_id, passed, details)

        # 更新 span (使用查找方法支持跨进程)
        span_id = self._find_active_span_for_step(step_id)
        if span_id:
            if passed:
                if not has_gate:
                    # 没有门禁，直接完成 span
                    trace_log.complete_span(
                        span_id,
                        output_data={
                            "step_id": step_id,
                            "validation": "passed",
                            "final_state": "completed",
                        }
                    )
                    del self._step_spans[step_id]
                # 如果有门禁，span 保持运行状态，等门禁通过后再完成
            else:
                # 验证失败
                trace_log.fail_span(
                    span_id,
                    error_code="VALIDATION_FAILED",
                    error_message=str(details) if details else "Validation failed"
                )
                del self._step_spans[step_id]

        return success, reason

    def trigger_gate(self, gate_id: str, step_id: str, gate_type: str = "human", blocking: bool = True):
        """触发门禁 (带追踪)"""
        trace_log = self._get_trace_log()

        # 记录门禁 span
        parent_span_id = self._step_spans.get(step_id)
        span = trace_log.log_gate_trigger(
            gate_id=gate_id,
            gate_type=gate_type,
            parent_span_id=parent_span_id
        )

        # 记录 gate -> span 映射
        if not hasattr(self, '_gate_spans'):
            self._gate_spans = {}
        self._gate_spans[gate_id] = span.span_id

        # 调用父类方法
        super().trigger_gate(gate_id, step_id, gate_type, blocking)

    def approve_gate(self, gate_id: str, approver: str, comment: str = None) -> Tuple[bool, Optional[str]]:
        """审批门禁 (带追踪)"""
        trace_log = self._get_trace_log()

        # 调用父类方法
        success, reason = super().approve_gate(gate_id, approver, comment)

        # 完成门禁 span (使用查找方法支持跨进程)
        span_id = self._find_active_span_for_gate(gate_id)
        if span_id:
            if success:
                trace_log.complete_span(
                    span_id,
                    output_data={
                        "gate_id": gate_id,
                        "decision": "approved",
                        "approver": approver,
                        "comment": comment,
                    }
                )
            else:
                trace_log.fail_span(
                    span_id,
                    error_code="GATE_FAILED",
                    error_message=reason or "Unknown reason"
                )
            if gate_id in self._gate_spans:
                del self._gate_spans[gate_id]

        return success, reason

    def reject_gate(self, gate_id: str, approver: str, reason: str) -> Tuple[bool, Optional[str]]:
        """拒绝门禁 (带追踪)"""
        trace_log = self._get_trace_log()

        # 调用父类方法
        success, result_reason = super().reject_gate(gate_id, approver, reason)

        # 完成门禁 span (使用查找方法支持跨进程)
        span_id = self._find_active_span_for_gate(gate_id)
        if span_id:
            trace_log.complete_span(
                span_id,
                output_data={
                    "gate_id": gate_id,
                    "decision": "rejected",
                    "approver": approver,
                    "reason": reason,
                }
            )
            if gate_id in self._gate_spans:
                del self._gate_spans[gate_id]

        return success, result_reason

    # ============================================
    # 追踪特有方法
    # ============================================

    def get_trace_statistics(self) -> Dict:
        """获取追踪统计信息"""
        if self._trace_log:
            return self._trace_log.get_statistics()
        return {}

    def export_trace_report(self, format: str = "markdown") -> str:
        """导出追踪报告"""
        if self._trace_log is None:
            raise ValueError("No trace log available")

        if format == "yaml":
            return self._trace_log.export_yaml()
        else:
            return self._trace_log.export_markdown_report()
