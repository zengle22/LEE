"""
LEE Orchestrator — Loop Controller

Stage 级别的自动修复循环控制器。

核心功能：
1. 管理循环状态（当前迭代、历史输出哈希）
2. 执行收敛判断（通过检测、重复输出检测、最大轮次检测）
3. 记录分轮 evidence
4. 提供 loop_context 给下一轮 agent（包含 previous_result）

用法:
    controller = LoopController(loop_config, evidence_collector, run_id)
    while controller.should_continue():
        results = await run_stage_steps(...)
        decision = controller.record_iteration(results)
        if decision != "continue":
            break
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from lee.orchestrator.ir.models import LoopConfigIR

logger = logging.getLogger(__name__)


# ========================================================================
# Loop State
# ========================================================================

@dataclass
class LoopState:
    """
    循环运行时状态

    记录循环执行过程中的中间状态，用于：
    - 跟踪当前迭代轮次
    - 检测重复输出（收敛判断）
    - 存储每轮结果摘要
    """
    current_iteration: int = 0
    max_iterations: int = 3
    output_hashes: List[str] = field(default_factory=list)
    iteration_results: List[Dict[str, Any]] = field(default_factory=list)
    status: str = "running"  # running | converged | max_exceeded | same_output_stop
    started_at: Optional[str] = None
    completed_at: Optional[str] = None


# ========================================================================
# Loop Controller
# ========================================================================

class LoopController:
    """
    Stage 级循环控制器

    管理 patch → test → analyze → retry 的收敛循环。

    每轮迭代：
    1. should_continue() — 判断是否应执行下一轮
    2. 执行 stage 内所有步骤
    3. record_iteration(results) — 记录结果 + 收敛判断

    收敛判断优先级：
    1. 通过条件 — completion_check_step 的结果匹配 completion_status
    2. 重复输出 — 本轮输出哈希与前轮相同 → 无法收敛
    3. 最大轮次 — 超过 max_iterations → 强制停止
    """

    def __init__(
        self,
        config: LoopConfigIR,
        evidence_collector: Any = None,
        run_id: str = "",
    ):
        """
        初始化循环控制器

        Args:
            config: 循环配置（来自 StageIR.loop）
            evidence_collector: 证据收集器（可选）
            run_id: 工作流运行 ID
        """
        self.config = config
        self.evidence_collector = evidence_collector
        self.run_id = run_id
        self.state = LoopState(
            max_iterations=config.max_iterations,
            started_at=datetime.now().isoformat(),
        )

    def should_continue(self) -> bool:
        """
        判断是否应继续下一轮

        Returns:
            True 如果循环未终止且未超过最大轮次
        """
        if not self.config.enabled:
            return self.state.current_iteration == 0

        if self.state.status != "running":
            return False

        if self.state.current_iteration >= self.state.max_iterations:
            self.state.status = "max_exceeded"
            self.state.completed_at = datetime.now().isoformat()
            return False

        return True

    def record_iteration(self, step_results: Dict[str, Any]) -> str:
        """
        记录一轮结果，执行收敛判断

        Args:
            step_results: 本轮所有步骤的结果
                格式: {step_id: {"status": "...", "message": "...", "output": ...}}

        Returns:
            判断结果:
            - "continue"          — 继续下一轮
            - "converged"         — 成功通过
            - "stop_same_output"  — 重复输出，无法收敛
            - "stop_max"          — 超过最大轮次
        """
        self.state.current_iteration += 1
        self.state.iteration_results.append({
            "iteration": self.state.current_iteration,
            "timestamp": datetime.now().isoformat(),
            "results": step_results,
        })

        # 1. 检测通过条件
        if self.config.completion_check_step:
            check_step = self.config.completion_check_step
            if check_step in step_results:
                step_status = step_results[check_step].get("status", "")
                if step_status == self.config.completion_status:
                    self.state.status = "converged"
                    self.state.completed_at = datetime.now().isoformat()
                    logger.info(
                        f"Loop converged at iteration {self.state.current_iteration}: "
                        f"step '{check_step}' returned '{step_status}'"
                    )
                    return "converged"

        # 2. 检测重复输出
        output_hash = self._compute_output_hash(step_results)
        if self.config.stop_on_same_output and output_hash in self.state.output_hashes:
            self.state.status = "same_output_stop"
            self.state.completed_at = datetime.now().isoformat()
            logger.warning(
                f"Loop stopped at iteration {self.state.current_iteration}: "
                f"same output hash detected (cannot converge)"
            )
            return "stop_same_output"
        self.state.output_hashes.append(output_hash)

        # 3. 检测最大轮次
        if self.state.current_iteration >= self.state.max_iterations:
            self.state.status = "max_exceeded"
            self.state.completed_at = datetime.now().isoformat()
            logger.warning(
                f"Loop stopped: max iterations ({self.state.max_iterations}) exceeded"
            )
            return "stop_max"

        return "continue"

    def get_loop_context(self) -> Dict[str, Any]:
        """
        返回注入下一轮 agent 的上下文

        用于 AgentContextBuilder 的 loop_context 参数。

        Returns:
            包含 iteration, previous_result, loop_status 的字典
        """
        context: Dict[str, Any] = {
            "iteration": self.state.current_iteration,
            "max_iterations": self.state.max_iterations,
            "loop_status": self.state.status,
        }

        # 注入前轮结果
        if self.state.iteration_results:
            last_result = self.state.iteration_results[-1]
            context["previous_result"] = self._summarize_result(last_result)
            context["previous_results_full"] = last_result.get("results", {})

        return context

    def get_summary(self) -> Dict[str, Any]:
        """
        获取循环执行摘要

        Returns:
            包含循环元数据的字典
        """
        return {
            "total_iterations": self.state.current_iteration,
            "max_iterations": self.state.max_iterations,
            "final_status": self.state.status,
            "started_at": self.state.started_at,
            "completed_at": self.state.completed_at,
        }

    def write_iteration_evidence(
        self,
        iteration: int,
        step_results: Dict[str, Any],
    ) -> Optional[str]:
        """
        写入分轮 evidence 文件

        Args:
            iteration: 迭代轮次
            step_results: 本轮步骤结果

        Returns:
            证据文件路径（如果写入成功）
        """
        if not self.evidence_collector:
            return None

        try:
            evidence_data = {
                "iteration": iteration,
                "timestamp": datetime.now().isoformat(),
                "run_id": self.run_id,
                "step_results": step_results,
                "loop_status": self.state.status,
            }

            # 使用 evidence_collector 写入
            evidence_path = self.evidence_collector.write_artifact(
                run_id=self.run_id,
                name=f"loop_iteration_{iteration:03d}.json",
                content=json.dumps(evidence_data, ensure_ascii=False, indent=2),
            )
            return str(evidence_path) if evidence_path else None
        except Exception as e:
            logger.warning(f"Failed to write loop evidence for iteration {iteration}: {e}")
            return None

    # ================================================================
    # 内部方法
    # ================================================================

    def _compute_output_hash(self, results: Dict[str, Any]) -> str:
        """
        计算结果哈希，用于检测重复输出

        只对 output 和 status 字段做哈希，忽略时间戳等变化字段。
        """
        # 提取用于哈希的稳定字段
        hashable = {}
        for step_id, result in sorted(results.items()):
            hashable[step_id] = {
                "status": result.get("status", ""),
                "output": result.get("output", ""),
            }

        raw = json.dumps(hashable, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def _summarize_result(self, iteration_result: Dict[str, Any]) -> str:
        """
        将前轮结果摘要为文本，用于注入 agent prompt

        Returns:
            人类可读的结果摘要
        """
        lines = [f"Iteration {iteration_result.get('iteration', '?')}:"]
        results = iteration_result.get("results", {})

        for step_id, result in results.items():
            status = result.get("status", "unknown")
            message = result.get("message", "")
            output = result.get("output", "")

            lines.append(f"  - Step '{step_id}': {status}")
            if message:
                lines.append(f"    Message: {message}")
            if output and isinstance(output, str) and len(output) < 500:
                lines.append(f"    Output: {output}")

        return "\n".join(lines)
