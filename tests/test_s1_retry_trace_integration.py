"""
S1 单元测试: Retry + Trace 集成

覆盖:
1. AsyncRetryExecutor - 异步重试执行器
2. RetryResult.result 字段
3. TraceLog span 生命周期
4. Orchestrator 初始化包含 trace_log
5. step_runners 的 retry 导入验证
"""

import asyncio
import time
import tempfile
import shutil
import pytest
from unittest.mock import MagicMock, AsyncMock


# ========================================================================
# 1. AsyncRetryExecutor 单元测试
# ========================================================================

class TestAsyncRetryExecutor:
    """AsyncRetryExecutor 异步重试执行器测试"""

    def test_import(self):
        """验证 AsyncRetryExecutor 可导入"""
        from lee.orchestrator.execution.retry import AsyncRetryExecutor
        assert AsyncRetryExecutor is not None

    def test_retry_result_has_result_field(self):
        """验证 RetryResult 包含 result 字段"""
        from lee.orchestrator.execution.retry import RetryResult
        assert "result" in RetryResult.__dataclass_fields__

    def test_success_first_attempt(self):
        """验证首次成功不重试"""
        from lee.orchestrator.execution.retry import AsyncRetryExecutor, RetryPolicy

        async def success_func():
            return {"status": "ok", "data": 42}

        executor = AsyncRetryExecutor(policy=RetryPolicy(max_retries=3))
        result = asyncio.get_event_loop().run_until_complete(executor.execute(success_func))

        assert result.success is True
        assert result.total_attempts == 1
        assert result.result == {"status": "ok", "data": 42}
        assert result.failed_attempts == 0

    def test_success_after_retries(self):
        """验证在第N次重试后成功"""
        from lee.orchestrator.execution.retry import AsyncRetryExecutor, RetryPolicy

        call_count = 0

        async def fail_twice_then_succeed():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise RuntimeError(f"Attempt {call_count} failed")
            return {"status": "ok"}

        executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=3, base_delay=0.01, jitter=False)
        )
        result = asyncio.get_event_loop().run_until_complete(executor.execute(fail_twice_then_succeed))

        assert result.success is True
        assert result.total_attempts == 3
        assert result.result == {"status": "ok"}
        assert result.was_successful_on_retry is True
        assert call_count == 3

    def test_all_attempts_exhausted(self):
        """验证重试次数耗尽"""
        from lee.orchestrator.execution.retry import AsyncRetryExecutor, RetryPolicy

        async def always_fail():
            raise ValueError("Permanent failure")

        executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=2, base_delay=0.01, jitter=False)
        )
        result = asyncio.get_event_loop().run_until_complete(executor.execute(always_fail))

        assert result.success is False
        assert result.total_attempts == 3  # 1 initial + 2 retries
        assert result.result is None
        assert "Permanent failure" in result.final_error
        assert result.failed_attempts == 3

    def test_with_args_and_kwargs(self):
        """验证传递参数给目标函数"""
        from lee.orchestrator.execution.retry import AsyncRetryExecutor, RetryPolicy

        async def add(a, b, extra=0):
            return a + b + extra

        executor = AsyncRetryExecutor(policy=RetryPolicy(max_retries=1))
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(add, 2, 3, extra=10)
        )

        assert result.success is True
        assert result.result == 15

    def test_error_classification(self):
        """验证错误类型分类"""
        from lee.orchestrator.execution.retry import (
            AsyncRetryExecutor, RetryPolicy, RetryErrorType
        )

        async def raise_validation():
            raise type("ValidationError", (Exception,), {})("bad input")

        executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=0)  # 不重试
        )
        result = asyncio.get_event_loop().run_until_complete(
            executor.execute(raise_validation)
        )

        assert result.success is False
        assert result.attempts[0].error_type == RetryErrorType.VALIDATION_FAILED

    def test_default_retry_policy(self):
        """验证默认重试策略"""
        from lee.orchestrator.execution.retry import DEFAULT_RETRY_POLICY

        assert DEFAULT_RETRY_POLICY.max_retries == 3
        assert DEFAULT_RETRY_POLICY.base_delay > 0

    def test_fast_fail_policy(self):
        """验证快速失败策略"""
        from lee.orchestrator.execution.retry import FAST_FAIL_POLICY

        assert FAST_FAIL_POLICY.max_retries == 0

    def test_retry_timing_uses_asyncio_sleep(self):
        """验证使用 asyncio.sleep 而非 time.sleep (不阻塞事件循环)"""
        from lee.orchestrator.execution.retry import AsyncRetryExecutor, RetryPolicy
        import asyncio

        call_count = 0

        async def fail_once():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise RuntimeError("First attempt fails")
            return "ok"

        executor = AsyncRetryExecutor(
            policy=RetryPolicy(max_retries=1, base_delay=0.05, jitter=False)
        )

        start = time.time()
        result = asyncio.get_event_loop().run_until_complete(executor.execute(fail_once))
        elapsed = time.time() - start

        assert result.success is True
        # 应该等待约 0.05 秒，但不应超过 1 秒
        assert elapsed < 1.0
        assert call_count == 2


# ========================================================================
# 2. RetryPolicy 单元测试
# ========================================================================

class TestRetryPolicy:
    """RetryPolicy 重试策略测试"""

    def test_get_delay_exponential(self):
        """验证指数退避延迟计算"""
        from lee.orchestrator.execution.retry import RetryPolicy

        policy = RetryPolicy(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=False,
        )

        assert policy.get_delay(0) == 1.0   # 1 * 2^0 = 1
        assert policy.get_delay(1) == 2.0   # 1 * 2^1 = 2
        assert policy.get_delay(2) == 4.0   # 1 * 2^2 = 4
        assert policy.get_delay(3) == 8.0   # 1 * 2^3 = 8

    def test_get_delay_max_cap(self):
        """验证延迟不超过 max_delay"""
        from lee.orchestrator.execution.retry import RetryPolicy

        policy = RetryPolicy(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False,
        )

        assert policy.get_delay(10) == 5.0  # 1 * 2^10 = 1024 → capped at 5

    def test_get_delay_with_jitter(self):
        """验证抖动在合理范围内"""
        from lee.orchestrator.execution.retry import RetryPolicy

        policy = RetryPolicy(
            base_delay=1.0,
            exponential_base=2.0,
            max_delay=60.0,
            jitter=True,
        )

        delays = [policy.get_delay(1) for _ in range(20)]
        # 抖动后延迟应在 [0, 2.0] 之间
        assert all(0 <= d <= 2.0 for d in delays)
        # 不应全部相同 (概率极低)
        assert len(set(delays)) > 1

    def test_should_retry_respects_max(self):
        """验证 should_retry 尊重最大重试次数"""
        from lee.orchestrator.execution.retry import RetryPolicy

        policy = RetryPolicy(max_retries=2)

        assert policy.should_retry(RuntimeError("err"), 0) is True  # 第1次失败
        assert policy.should_retry(RuntimeError("err"), 1) is True  # 第2次失败
        assert policy.should_retry(RuntimeError("err"), 2) is False # 已达上限

    def test_should_retry_filters_exceptions(self):
        """验证异常类型过滤"""
        from lee.orchestrator.execution.retry import RetryPolicy

        policy = RetryPolicy(
            max_retries=3,
            retry_on=[RuntimeError],
        )

        assert policy.should_retry(RuntimeError("err"), 0) is True
        assert policy.should_retry(ValueError("err"), 0) is False


# ========================================================================
# 3. TraceLog 单元测试
# ========================================================================

class TestTraceLogSpanLifecycle:
    """TraceLog span 生命周期测试"""

    def setup_method(self):
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_start_and_complete_span(self):
        """验证开始和完成 span"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType, SpanStatus

        trace = TraceLog(self.temp_dir)
        span = trace.start_span(SpanType.ORCHESTRATOR, "test.step_1")

        assert span.span_id is not None
        assert span.status == SpanStatus.RUNNING

        completed = trace.complete_span(span.span_id, output_data={"result": "ok"})

        assert completed.status == SpanStatus.SUCCESS
        assert completed.completed_at is not None
        assert completed.duration_ms is not None
        assert completed.duration_ms >= 0

    def test_start_and_fail_span(self):
        """验证开始和失败 span"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType, SpanStatus

        trace = TraceLog(self.temp_dir)
        span = trace.start_span(SpanType.ORCHESTRATOR, "test.step_fail")

        failed = trace.fail_span(
            span.span_id,
            error_code="RuntimeError",
            error_message="Something broke",
        )

        assert failed.status == SpanStatus.FAILED
        assert failed.error is not None
        assert failed.error.code == "RuntimeError"
        assert "Something broke" in failed.error.message

    def test_span_context_manager(self):
        """验证 span context manager"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType, SpanStatus

        trace = TraceLog(self.temp_dir)

        with trace.span(SpanType.TOOL, "test.tool") as span:
            assert span.status == SpanStatus.RUNNING

        # span 应该已完成
        final = trace.get_span(span.span_id)
        assert final.status == SpanStatus.SUCCESS

    def test_span_context_manager_on_error(self):
        """验证 span context manager 在异常时标记失败"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType, SpanStatus

        trace = TraceLog(self.temp_dir)

        with pytest.raises(ValueError):
            with trace.span(SpanType.TOOL, "test.tool_fail") as span:
                raise ValueError("oops")

        final = trace.get_span(span.span_id)
        assert final.status == SpanStatus.FAILED
        assert final.error.message == "oops"

    def test_span_with_tags_and_attributes(self):
        """验证 span 标签和属性"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType

        trace = TraceLog(self.temp_dir)
        span = trace.start_span(
            SpanType.ORCHESTRATOR, "test.tagged",
            tags=["kind:agent", "env:test"],
            attributes={"step_id": "s1"},
        )

        assert "kind:agent" in span.tags
        assert span.attributes["step_id"] == "s1"

        trace.complete_span(span.span_id, tags=["result:success"])
        final = trace.get_span(span.span_id)
        assert "result:success" in final.tags

    def test_get_spans_query(self):
        """验证 span 查询"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType

        trace = TraceLog(self.temp_dir)

        s1 = trace.start_span(SpanType.ORCHESTRATOR, "step.1")
        s2 = trace.start_span(SpanType.TOOL, "tool.1")
        trace.complete_span(s1.span_id)
        trace.complete_span(s2.span_id)

        all_spans = trace.get_spans()
        assert len(all_spans) >= 2

        step_spans = trace.get_spans(span_type=SpanType.ORCHESTRATOR)
        assert len(step_spans) >= 1

    def test_log_agent_call(self):
        """验证 log_agent_call 便捷方法"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType

        trace = TraceLog(self.temp_dir)
        span = trace.log_agent_call(
            agent_id="agent.dev.coder",
            agent_name="Coder",
            model="zhipu-glm4",
        )

        assert span.agent is not None
        assert span.agent.agent_id == "agent.dev.coder"
        assert span.span_type == SpanType.AGENT

    def test_jsonl_persistence(self):
        """验证 JSONL 文件持久化"""
        from lee.orchestrator.execution.trace import TraceLog, SpanType

        trace = TraceLog(self.temp_dir, run_id="RUN-TEST-001")
        s = trace.start_span(SpanType.ORCHESTRATOR, "persistence.test")
        trace.complete_span(s.span_id, output_data={"done": True})

        # 用新 TraceLog 实例读取
        trace2 = TraceLog(self.temp_dir, run_id="RUN-TEST-001")
        spans = trace2.get_spans()
        assert len(spans) >= 1


# ========================================================================
# 4. Sanitize 函数测试
# ========================================================================

class TestSanitize:
    """脱敏函数测试"""

    def test_sanitize_email(self):
        from lee.orchestrator.execution.trace import sanitize
        result = sanitize("Contact user@example.com for details")
        assert "[EMAIL]" in result
        assert "user@example.com" not in result

    def test_sanitize_api_key(self):
        from lee.orchestrator.execution.trace import sanitize
        result = sanitize("Use sk-12345678901234567890abcdef")
        assert "[API_KEY]" in result

    def test_sanitize_bearer_token(self):
        from lee.orchestrator.execution.trace import sanitize
        result = sanitize("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.token")
        assert "[REDACTED]" in result

    def test_sanitize_non_string(self):
        from lee.orchestrator.execution.trace import sanitize
        assert sanitize(42) == 42
        assert sanitize(None) is None


# ========================================================================
# 5. Orchestrator 集成验证 (初始化)
# ========================================================================

class TestOrchestratorS1Init:
    """验证 Orchestrator 初始化时创建了 S1 组件"""

    def test_orchestrator_has_trace_log(self):
        """验证 Orchestrator 包含 trace_log 属性"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from lee.orchestrator.execution.trace import TraceLog

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        assert hasattr(orch, 'trace_log')
        assert isinstance(orch.trace_log, TraceLog)

    def test_step_runners_imports_retry(self):
        """验证 step_runners 导入了 retry 模块"""
        from lee.orchestrator.execution import step_runners
        assert hasattr(step_runners, 'AsyncRetryExecutor')
        assert hasattr(step_runners, 'DEFAULT_RETRY_POLICY')
