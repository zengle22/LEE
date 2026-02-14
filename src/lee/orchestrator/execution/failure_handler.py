"""
LEE Orchestrator v3.5 — Failure Handler

实现步骤级别的 on_failure 策略：
- retry: 自动重试 N 次
- fallback: 失败后的回退策略
  - human_review: 暂停工作流等待人工介入
  - skip: 跳过失败步骤继续执行
  - abort: 终止整个工作流

on_failure 配置来源：
1. 步骤本身的 step.config["on_failure"]
2. IR 模型中的 StepIR.on_failure（从 YAML 解析）

示例 YAML:
    on_failure:
      retry: 2
      fallback: human_review
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Dict, Optional

from lee.orchestrator.storage.models import StepResult

logger = logging.getLogger(__name__)


@dataclass
class FailurePolicy:
    """解析后的失败策略"""
    retry: int = 0                    # 重试次数（不含首次执行）
    fallback: str = "abort"           # 回退策略: human_review | skip | abort
    retry_delay_seconds: float = 2.0  # 重试间隔（秒）
    notify_on_failure: bool = True    # 失败时是否发送通知

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "FailurePolicy":
        """从 step.config["on_failure"] 或 YAML 解析失败策略"""
        if not config:
            return cls()  # 默认: 不重试, abort

        return cls(
            retry=config.get("retry", 0),
            fallback=config.get("fallback", "abort"),
            retry_delay_seconds=config.get("retry_delay_seconds", 2.0),
            notify_on_failure=config.get("notify_on_failure", True),
        )


class FailureHandler:
    """
    步骤失败处理器

    用法:
        handler = FailureHandler()
        result = await handler.execute_with_policy(
            step=step,
            runner_fn=lambda: runner.execute(workflow_id, step, ctx),
            on_human_review=async_pause_fn,
        )
    """

    async def execute_with_policy(
        self,
        step: Any,
        runner_fn: Callable[[], Coroutine[Any, Any, StepResult]],
        on_human_review: Optional[Callable[[str, str], Coroutine[Any, Any, StepResult]]] = None,
        on_skip: Optional[Callable[[str, str], Coroutine[Any, Any, StepResult]]] = None,
    ) -> StepResult:
        """
        使用 on_failure 策略包裹步骤执行

        Args:
            step: 步骤对象（需要有 config、id 属性）
            runner_fn: 实际执行步骤的协程工厂
            on_human_review: fallback=human_review 时的回调
            on_skip: fallback=skip 时的回调

        Returns:
            StepResult
        """
        # 解析策略
        on_failure_config = self._extract_on_failure(step)
        policy = FailurePolicy.from_config(on_failure_config)

        # 第一次执行 + N 次重试
        total_attempts = 1 + policy.retry
        last_result: Optional[StepResult] = None

        for attempt in range(total_attempts):
            try:
                result = await runner_fn()

                # 成功 → 直接返回
                if result.status not in ("failed",):
                    if attempt > 0:
                        logger.info(
                            f"Step {step.id} succeeded on attempt {attempt + 1}/{total_attempts}"
                        )
                    return result

                # 步骤返回 failed 但没抛异常
                last_result = result
                if attempt < total_attempts - 1:
                    logger.warning(
                        f"Step {step.id} failed (attempt {attempt + 1}/{total_attempts}), "
                        f"retrying in {policy.retry_delay_seconds}s..."
                    )
                    await asyncio.sleep(policy.retry_delay_seconds)

            except Exception as e:
                logger.error(
                    f"Step {step.id} raised exception (attempt {attempt + 1}/{total_attempts}): {e}"
                )
                last_result = StepResult(
                    status="failed",
                    step_id=step.id,
                    workflow_id=getattr(step, "workflow_id", ""),
                    message=f"Exception on attempt {attempt + 1}: {e}",
                )
                if attempt < total_attempts - 1:
                    await asyncio.sleep(policy.retry_delay_seconds)

        # 所有重试用尽 → 执行 fallback
        logger.warning(
            f"Step {step.id} failed after {total_attempts} attempts. "
            f"Fallback: {policy.fallback}"
        )

        return await self._execute_fallback(
            policy=policy,
            step=step,
            last_result=last_result or StepResult(
                status="failed",
                step_id=step.id,
                workflow_id="",
                message="All attempts exhausted",
            ),
            on_human_review=on_human_review,
            on_skip=on_skip,
        )

    async def _execute_fallback(
        self,
        policy: FailurePolicy,
        step: Any,
        last_result: StepResult,
        on_human_review: Optional[Callable] = None,
        on_skip: Optional[Callable] = None,
    ) -> StepResult:
        """执行 fallback 策略"""
        if policy.fallback == "human_review":
            if on_human_review:
                return await on_human_review(step.id, last_result.message)
            # 没有回调时，返回 blocked 状态让上层处理
            last_result.status = "blocked"
            last_result.blocked_reason = "on_failure_human_review"
            last_result.message = (
                f"Step {step.id} failed after retries. "
                f"Requires human review: {last_result.message}"
            )
            return last_result

        elif policy.fallback == "skip":
            if on_skip:
                return await on_skip(step.id, last_result.message)
            # 标记为 skipped
            last_result.status = "skipped"
            last_result.message = (
                f"Step {step.id} failed after retries. "
                f"Skipped per on_failure policy."
            )
            return last_result

        else:
            # abort (default) — 保持 failed 状态
            return last_result

    @staticmethod
    def _extract_on_failure(step: Any) -> Optional[Dict[str, Any]]:
        """从步骤配置中提取 on_failure"""
        # 优先从 step.config["on_failure"] 读取
        if hasattr(step, "config") and isinstance(step.config, dict):
            on_failure = step.config.get("on_failure")
            if on_failure:
                return on_failure

        # 再从 step.on_failure 读取（IR 模型）
        if hasattr(step, "on_failure") and step.on_failure:
            return step.on_failure

        return None

    @staticmethod
    def has_policy(step: Any) -> bool:
        """检查步骤是否有 on_failure 策略"""
        return FailureHandler._extract_on_failure(step) is not None
