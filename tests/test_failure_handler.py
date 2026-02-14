"""
Tests for LEE FailureHandler — M3 on_failure strategy

Tests:
1. FailurePolicy.from_config 解析
2. 无 on_failure 策略时直接透传
3. 重试成功场景
4. 重试耗尽后 fallback=abort
5. 重试耗尽后 fallback=human_review
6. 重试耗尽后 fallback=skip
7. 异常重试
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock
from types import SimpleNamespace

from lee.orchestrator.execution.failure_handler import (
    FailureHandler,
    FailurePolicy,
)
from lee.orchestrator.storage.models import StepResult


# ── FailurePolicy ──────────────────────────────────────────────────

class TestFailurePolicy:
    def test_from_none(self):
        p = FailurePolicy.from_config(None)
        assert p.retry == 0
        assert p.fallback == "abort"

    def test_from_empty(self):
        p = FailurePolicy.from_config({})
        assert p.retry == 0
        assert p.fallback == "abort"

    def test_from_yaml_style(self):
        p = FailurePolicy.from_config({"retry": 2, "fallback": "human_review"})
        assert p.retry == 2
        assert p.fallback == "human_review"

    def test_custom_delay(self):
        p = FailurePolicy.from_config({"retry": 1, "retry_delay_seconds": 0.1})
        assert p.retry_delay_seconds == 0.1


# ── FailureHandler ─────────────────────────────────────────────────

def _make_step(on_failure=None, step_id="s1"):
    return SimpleNamespace(
        id=step_id,
        config={"on_failure": on_failure} if on_failure else {},
        on_failure=on_failure,
        workflow_id="wf-1",
    )


def _ok_result(step_id="s1"):
    return StepResult(status="completed", step_id=step_id, workflow_id="wf-1", message="ok")


def _fail_result(step_id="s1"):
    return StepResult(status="failed", step_id=step_id, workflow_id="wf-1", message="boom")


class TestFailureHandlerHasPolicy:
    def test_no_policy(self):
        assert FailureHandler.has_policy(_make_step()) is False

    def test_with_policy(self):
        assert FailureHandler.has_policy(_make_step({"retry": 1})) is True


class TestFailureHandlerExecute:
    @pytest.mark.asyncio
    async def test_success_no_retry(self):
        handler = FailureHandler()
        step = _make_step({"retry": 2, "fallback": "abort"})
        runner = AsyncMock(return_value=_ok_result())

        result = await handler.execute_with_policy(step=step, runner_fn=runner)
        assert result.status == "completed"
        runner.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_retry_then_success(self):
        handler = FailureHandler()
        step = _make_step({"retry": 2, "fallback": "abort", "retry_delay_seconds": 0})
        call_count = 0

        async def _runner():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return _fail_result()
            return _ok_result()

        result = await handler.execute_with_policy(step=step, runner_fn=_runner)
        assert result.status == "completed"
        assert call_count == 3

    @pytest.mark.asyncio
    async def test_all_retries_exhausted_abort(self):
        handler = FailureHandler()
        step = _make_step({"retry": 1, "fallback": "abort", "retry_delay_seconds": 0})
        runner = AsyncMock(return_value=_fail_result())

        result = await handler.execute_with_policy(step=step, runner_fn=runner)
        assert result.status == "failed"
        assert runner.await_count == 2  # 1 original + 1 retry

    @pytest.mark.asyncio
    async def test_fallback_human_review_with_callback(self):
        handler = FailureHandler()
        step = _make_step({"retry": 0, "fallback": "human_review", "retry_delay_seconds": 0})
        runner = AsyncMock(return_value=_fail_result())
        hr_cb = AsyncMock(return_value=StepResult(
            status="blocked",
            blocked_reason="on_failure_human_review",
            step_id="s1",
            workflow_id="wf-1",
            message="awaiting"
        ))

        result = await handler.execute_with_policy(
            step=step, runner_fn=runner, on_human_review=hr_cb
        )
        assert result.status == "blocked"
        hr_cb.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_fallback_human_review_no_callback(self):
        handler = FailureHandler()
        step = _make_step({"retry": 0, "fallback": "human_review", "retry_delay_seconds": 0})
        runner = AsyncMock(return_value=_fail_result())

        result = await handler.execute_with_policy(step=step, runner_fn=runner)
        assert result.status == "blocked"
        assert "human review" in result.message.lower()

    @pytest.mark.asyncio
    async def test_fallback_skip(self):
        handler = FailureHandler()
        step = _make_step({"retry": 0, "fallback": "skip", "retry_delay_seconds": 0})
        runner = AsyncMock(return_value=_fail_result())

        result = await handler.execute_with_policy(step=step, runner_fn=runner)
        assert result.status == "skipped"

    @pytest.mark.asyncio
    async def test_exception_retry(self):
        handler = FailureHandler()
        step = _make_step({"retry": 1, "fallback": "abort", "retry_delay_seconds": 0})
        call_count = 0

        async def _runner():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("network error")
            return _ok_result()

        result = await handler.execute_with_policy(step=step, runner_fn=_runner)
        assert result.status == "completed"
        assert call_count == 2
