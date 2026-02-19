"""
LEE Cross-Workflow Loop Controller

L3 跨工作流收敛循环控制器，在 L2 层管理 QA-L3 ↔ Dev-L3 的乒乓循环。

核心场景：
    QA-L3 测试 → 产出 bug 包 → Dev-L3 修复 → QA-L3 验收 → … → bug 清零

收敛条件（三层）：
    1. 主收敛：check_phase 输出的 check_field ∈ pass_values
    2. 辅助收敛：secondary_check 表达式为真
    3. 最大轮次：max_rounds 超限

与 LoopController（Stage 内部循环）互补：
    - LoopController: 一个 L3 内部 patch → test → retry
    - CrossWorkflowLoopController: L2 层 QA-L3 → Dev-L3 → QA-L3
"""

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

log = logging.getLogger(__name__)


# ========================================================================
# State
# ========================================================================

@dataclass
class CrossWorkflowLoopState:
    """
    跨工作流循环的运行时状态

    Attributes:
        current_round: 当前完整轮次（QA-L3 完整执行一次 = round +1）
        current_phase_idx: 当前 phase 在 phases 列表中的索引
        max_rounds: 最大轮次限制
        status: running | converged | max_exceeded | aborted
        round_results: 每轮每个 phase 的结果历史
        bug_counts: 每轮 bug 数量趋势（用于趋势分析）
    """
    current_round: int = 0
    current_phase_idx: int = 0
    max_rounds: int = 3
    status: str = "running"
    round_results: List[Dict[str, Any]] = field(default_factory=list)
    bug_counts: List[int] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ========================================================================
# Controller
# ========================================================================

class CrossWorkflowLoopController:
    """
    L3 跨工作流收敛循环控制器

    Usage:
        controller = CrossWorkflowLoopController(config, evidence_collector, run_id)
        while controller.should_continue():
            phase = controller.get_current_phase()
            result = await run_workflow(phase.workflow_ref, ...)
            decision = controller.record_phase_result(result)
            if decision != "continue":
                break
            controller.advance_phase()
    """

    def __init__(
        self,
        config,  # CrossWorkflowLoopIR
        evidence_collector: Any = None,
        run_id: str = "",
    ):
        self.config = config
        self.evidence_collector = evidence_collector
        self.run_id = run_id
        self.state = CrossWorkflowLoopState(
            max_rounds=config.max_rounds,
        )
        self.state.started_at = datetime.now(timezone.utc).isoformat()

    # ── 循环控制 ──────────────────────────────────────────────────

    def should_continue(self) -> bool:
        """
        判断循环是否应该继续

        Returns:
            True: 继续执行下一个 phase
            False: 循环终止
        """
        if not self.config.enabled:
            # 未启用循环：最多执行一轮
            return self.state.current_round < 1

        if self.state.status != "running":
            return False

        if self.state.current_round >= self.state.max_rounds:
            self.state.status = "max_exceeded"
            self.state.completed_at = datetime.now(timezone.utc).isoformat()
            log.warning(
                "Cross-workflow loop max rounds exceeded: %d/%d",
                self.state.current_round,
                self.state.max_rounds,
            )
            return False

        return True

    def get_current_phase(self) -> Dict[str, Any]:
        """
        获取当前应执行的 phase 信息

        Returns:
            phase 配置字典，包含 id, workflow_ref, role, condition, inputs_from
        """
        if not self.config.phases:
            return {}

        phase = self.config.phases[self.state.current_phase_idx]
        return {
            "id": phase.id,
            "workflow_ref": phase.workflow_ref,
            "role": phase.role,
            "condition": phase.condition,
            "inputs_from": phase.inputs_from,
            "round": self.state.current_round,
            "phase_idx": self.state.current_phase_idx,
        }

    def advance_phase(self):
        """
        推进到下一个 phase

        如果当前 phase 是最后一个，则推进到下一轮的第一个 phase。
        """
        if not self.config.phases:
            return

        next_idx = self.state.current_phase_idx + 1
        if next_idx >= len(self.config.phases):
            # 一轮结束，回到第一个 phase
            self.state.current_phase_idx = 0
            self.state.current_round += 1
            log.info(
                "Cross-workflow loop round %d completed, starting round %d",
                self.state.current_round - 1,
                self.state.current_round,
            )
        else:
            self.state.current_phase_idx = next_idx

    # ── 结果记录与收敛判定 ────────────────────────────────────────

    def record_phase_result(self, phase_result: Dict[str, Any]) -> str:
        """
        记录 phase 执行结果并判定是否继续

        Args:
            phase_result: 子工作流执行结果，包含 status、outputs 等

        Returns:
            "continue": 继续下一个 phase / 下一轮
            "converged": 收敛完成
            "stop_max": 最大轮次超限
        """
        current_phase = self._current_phase_config()
        phase_id = current_phase.id if current_phase else "unknown"

        # 记录结果
        result_record = {
            "round": self.state.current_round,
            "phase_id": phase_id,
            "phase_idx": self.state.current_phase_idx,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "result": phase_result,
        }
        self.state.round_results.append(result_record)

        # 提取 bug 数量（如果有）
        bug_count = self._extract_bug_count(phase_result)
        if bug_count is not None:
            self.state.bug_counts.append(bug_count)

        log.info(
            "Cross-workflow loop phase '%s' completed (round %d, bug_count=%s)",
            phase_id,
            self.state.current_round,
            bug_count,
        )

        # 收敛判定：仅在指定的 check_phase 完成后判定
        convergence = self.config.convergence
        if convergence and phase_id == convergence.check_phase:
            decision = self._check_convergence(phase_result)
            if decision != "continue":
                return decision

        return "continue"

    def _check_convergence(self, phase_result: Dict[str, Any]) -> str:
        """
        检查收敛条件

        三层判定：
        1. 主判定：check_field ∈ pass_values
        2. 辅助判定：secondary_check 表达式
        3. 下一轮的 max_rounds 检查（由 should_continue 处理）
        """
        convergence = self.config.convergence
        if not convergence:
            return "continue"

        # 1. 主收敛条件
        check_value = self._extract_field(phase_result, convergence.check_field)
        if check_value in convergence.pass_values:
            self.state.status = "converged"
            self.state.completed_at = datetime.now(timezone.utc).isoformat()
            log.info(
                "Cross-workflow loop CONVERGED: %s=%s (round %d)",
                convergence.check_field,
                check_value,
                self.state.current_round,
            )
            return "converged"

        # 2. bug count 趋势分析（非停止条件，仅告警）
        if len(self.state.bug_counts) >= 2:
            latest = self.state.bug_counts[-1]
            previous = self.state.bug_counts[-2]
            if latest >= previous:
                log.warning(
                    "Bug count NOT decreasing: %d -> %d (round %d). "
                    "Loop may be stuck.",
                    previous,
                    latest,
                    self.state.current_round,
                )

        # 3. 下一轮的 max_rounds 检查
        # 注意：当前 phase 已完成，下一轮需要 advance_phase 后
        # 由 should_continue() 检查。但如果当前轮次已经达到 max_rounds-1
        # 且下一步是 advance_phase -> 新一轮开始，则判定为 stop_max
        if self.state.current_round >= self.state.max_rounds - 1:
            # 当前轮结束后将 advance 到 current_round + 1 == max_rounds
            self.state.status = "max_exceeded"
            self.state.completed_at = datetime.now(timezone.utc).isoformat()
            log.warning(
                "Cross-workflow loop will exceed max rounds after this iteration: %d/%d",
                self.state.current_round + 1,
                self.state.max_rounds,
            )
            return "stop_max"

        return "continue"

    # ── 上下文注入 ────────────────────────────────────────────────

    def get_loop_context(self) -> Dict[str, Any]:
        """
        获取循环上下文，注入子工作流

        Returns:
            包含 round、phase、previous_results 等信息的字典
        """
        ctx: Dict[str, Any] = {
            "round": self.state.current_round,
            "max_rounds": self.state.max_rounds,
            "phase_idx": self.state.current_phase_idx,
            "loop_status": self.state.status,
        }

        if self.state.round_results:
            ctx["previous_results"] = self.state.round_results[-1]
            ctx["previous_result_summary"] = self._summarize_result(
                self.state.round_results[-1]
            )

        if self.state.bug_counts:
            ctx["bug_trend"] = self.state.bug_counts

        return ctx

    # ── 证据记录 ──────────────────────────────────────────────────

    def write_round_evidence(
        self,
        round_num: int,
        phase_id: str,
        phase_result: Dict[str, Any],
    ) -> Optional[str]:
        """
        写入轮次级别的证据

        Args:
            round_num: 轮次编号
            phase_id: phase 标识
            phase_result: phase 执行结果

        Returns:
            证据文件路径（如果写入成功）
        """
        if not self.evidence_collector:
            return None

        try:
            evidence_data = {
                "round": round_num,
                "phase_id": phase_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "result": phase_result,
                "bug_counts": self.state.bug_counts,
                "loop_status": self.state.status,
            }

            name = f"cross_loop_round_{round_num:03d}_{phase_id}.json"
            path = self.evidence_collector.write_artifact(
                run_id=self.run_id,
                name=name,
                content=json.dumps(evidence_data, ensure_ascii=False, indent=2),
            )
            return path
        except Exception as e:
            log.warning("Failed to write cross-workflow loop evidence: %s", e)
            return None

    # ── 摘要 ──────────────────────────────────────────────────────

    def get_summary(self) -> Dict[str, Any]:
        """
        获取循环执行摘要

        Returns:
            包含总轮次、最终状态、bug 趋势等信息的字典
        """
        if self.state.completed_at is None:
            self.state.completed_at = datetime.now(timezone.utc).isoformat()

        return {
            "total_rounds": self.state.current_round + (
                1 if self.state.current_phase_idx > 0 else 0
            ),
            "max_rounds": self.state.max_rounds,
            "final_status": self.state.status,
            "bug_trend": self.state.bug_counts,
            "total_phases_executed": len(self.state.round_results),
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }

    # ── 内部辅助方法 ──────────────────────────────────────────────

    def _current_phase_config(self):
        """获取当前 phase 的 IR 配置"""
        if not self.config.phases:
            return None
        idx = self.state.current_phase_idx
        if idx < len(self.config.phases):
            return self.config.phases[idx]
        return None

    @staticmethod
    def _extract_field(data: Dict[str, Any], field_path: str) -> Any:
        """
        从嵌套字典中提取字段值

        支持 dotted path: "outputs.exit_decision"
        """
        parts = field_path.split(".")
        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            else:
                return None
        return current

    @staticmethod
    def _extract_bug_count(phase_result: Dict[str, Any]) -> Optional[int]:
        """
        从 phase 结果中提取 bug 数量

        尝试多个候选路径：
        - open_bug_count
        - outputs.open_bugs
        - outputs.bug_count
        - bug_count
        """
        candidates = [
            "open_bug_count",
            "open_bugs",
            "bug_count",
        ]
        for key in candidates:
            val = phase_result.get(key)
            if val is not None:
                try:
                    return int(val)
                except (TypeError, ValueError):
                    continue

        # 尝试从 outputs 子字典提取
        outputs = phase_result.get("outputs", {})
        if isinstance(outputs, dict):
            for key in candidates:
                val = outputs.get(key)
                if val is not None:
                    try:
                        return int(val)
                    except (TypeError, ValueError):
                        continue

        return None

    @staticmethod
    def _summarize_result(result_record: Dict[str, Any]) -> str:
        """生成 phase 结果的文字摘要用于 prompt 注入"""
        phase_id = result_record.get("phase_id", "unknown")
        r = result_record.get("result", {})

        status = r.get("status", "unknown")

        bug_count_str = ""
        bug_count = CrossWorkflowLoopController._extract_bug_count(r)
        if bug_count is not None:
            bug_count_str = f", {bug_count} open bugs"

        return f"Phase '{phase_id}' completed with status='{status}'{bug_count_str}"
