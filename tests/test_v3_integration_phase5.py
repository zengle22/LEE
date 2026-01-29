"""
测试 LEE Orchestrator v3.1 - Phase 5 集成测试

测试内容：
1. RetryPolicy 和 RetryExecutor
2. TokenManager 功能
3. ToolGuard 功能
"""

import sys
import os
import tempfile
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.retry import (
    RetryPolicy, RetryExecutor, RetryResult, RetryErrorType,
    DEFAULT_RETRY_POLICY, FAST_FAIL_POLICY, AGGRESSIVE_RETRY_POLICY,
    execute_with_retry,
)
from lee.orchestrator.core.token_manager import (
    TokenManager, StepToken, ToolGuard,
)


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_retry_policy():
    """测试 RetryPolicy"""
    print_section("测试 1: RetryPolicy")

    policy = RetryPolicy(
        max_retries=3,
        base_delay=1.0,
        max_delay=60.0,
        exponential_base=2.0,
        jitter=True,
    )

    # 测试延迟计算（指数退避）
    delay0 = policy.get_delay(0)
    delay1 = policy.get_delay(1)
    delay2 = policy.get_delay(2)

    print(f"   Delay attempt 0: {delay0:.2f}s")
    print(f"   Delay attempt 1: {delay1:.2f}s")
    print(f"   Delay attempt 2: {delay2:.2f}s")

    # 验证指数增长
    assert delay1 > delay0
    assert delay2 > delay1
    print("   ✅ 指数退避策略正常")

    # 测试 should_retry
    class TestError(Exception):
        pass

    assert policy.should_retry(TestError(), 0) == True
    assert policy.should_retry(TestError(), 2) == True
    assert policy.should_retry(TestError(), 3) == False  # max_retries exceeded
    print("   ✅ should_retry 逻辑正常")


def test_retry_executor():
    """测试 RetryExecutor"""
    print_section("测试 2: RetryExecutor")

    policy = RetryPolicy(max_retries=2, base_delay=0.1, jitter=False)
    executor = RetryExecutor(policy)

    # 测试成功场景
    call_count = 0

    def successful_func():
        nonlocal call_count
        call_count += 1
        return "success"

    result = executor.execute(successful_func)
    assert result.success == True
    assert result.total_attempts == 1
    assert call_count == 1
    print("   ✅ 成功场景测试通过")

    # 测试重试场景
    fail_count = 0

    def failing_func():
        nonlocal fail_count
        fail_count += 1
        if fail_count < 3:
            raise ValueError("Temporary error")
        return "success after retries"

    result = executor.execute(failing_func)
    assert result.success == True
    assert result.total_attempts == 3
    assert result.failed_attempts == 2
    assert result.was_successful_on_retry == True
    print(f"   ✅ 重试场景测试通过 (3次尝试, {result.failed_attempts}次失败)")


def test_preset_policies():
    """测试预设策略"""
    print_section("测试 3: 预设重试策略")

    # 默认策略
    assert DEFAULT_RETRY_POLICY.max_retries == 3
    assert DEFAULT_RETRY_POLICY.base_delay == 1.0
    print("   ✅ DEFAULT_RETRY_POLICY 参数正确")

    # 快速失败策略
    assert FAST_FAIL_POLICY.max_retries == 0
    assert FAST_FAIL_POLICY.base_delay == 0
    print("   ✅ FAST_FAIL_POLICY 参数正确")

    # 激进重试策略
    assert AGGRESSIVE_RETRY_POLICY.max_retries == 10
    assert AGGRESSIVE_RETRY_POLICY.base_delay == 0.5
    print("   ✅ AGGRESSIVE_RETRY_POLICY 参数正确")


def test_execute_with_retry():
    """测试便捷函数 execute_with_retry"""
    print_section("测试 4: execute_with_retry 便捷函数")

    # 测试成功场景
    result = execute_with_retry(lambda: "test", max_retries=3)
    assert result.success == True
    print("   ✅ execute_with_retry 成功场景通过")

    # 测试失败场景
    result = execute_with_retry(lambda: exec('raise ValueError("error")'), max_retries=1)
    assert result.success == False
    assert result.final_error is not None
    print("   ✅ execute_with_retry 失败场景通过")


def test_token_manager():
    """测试 TokenManager"""
    print_section("测试 5: TokenManager")

    with tempfile.TemporaryDirectory() as tmpdir:
        tm = TokenManager(tmpdir)

        # 签发令牌
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="p1_design",
            agent_id="llm-agent",
            permissions=["read", "write"],
            validity_hours=4
        )

        assert token.token_id.startswith("TKN-")
        assert token.run_id == "RUN-001"
        assert token.step_id == "p1_design"
        assert token.agent_id == "llm-agent"
        assert "read" in token.permissions
        assert token.signature is not None
        print(f"   ✅ 令牌签发成功: {token.token_id}")

        # 验证令牌
        valid, reason = tm.validate_token(
            token.token_id,
            step_id="p1_design",
            required_permission="read"
        )
        assert valid == True
        assert reason is None
        print("   ✅ 令牌验证通过")

        # 测试权限检查
        valid, reason = tm.validate_token(
            token.token_id,
            step_id="p1_design",
            required_permission="deploy"
        )
        assert valid == False
        assert "permission" in reason.lower()
        print("   ✅ 权限检查正常")

        # 测试步骤不匹配
        valid, reason = tm.validate_token(
            token.token_id,
            step_id="p2_requirement",
        )
        assert valid == False
        assert "p1_design" in reason
        print("   ✅ 步骤匹配检查正常")

        # 撤销令牌
        revoked = tm.revoke_token(token.token_id, reason="Test revoke")
        assert revoked == True
        valid, reason = tm.validate_token(token.token_id)
        assert valid == False
        assert "revoked" in reason.lower()
        print("   ✅ 令牌撤销正常")


def test_tool_guard():
    """测试 ToolGuard"""
    print_section("测试 6: ToolGuard")

    with tempfile.TemporaryDirectory() as tmpdir:
        tm = TokenManager(tmpdir)
        guard = ToolGuard(tm)

        # 签发有限权限的令牌
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step1",
            agent_id="agent1",
            permissions=["read"],  # 只有读权限
        )

        # 测试读权限
        allowed, reason = guard.check_tool_access(
            token.token_id,
            "Read",
            step_id="step1"
        )
        assert allowed == True
        print("   ✅ Read 工具访问允许")

        # 测试写权限（应该拒绝）
        allowed, reason = guard.check_tool_access(
            token.token_id,
            "Write",
            step_id="step1"
        )
        assert allowed == False
        print("   ✅ Write 工具访问拒绝（无权限）")

        # 测试执行权限（应该拒绝）
        allowed, reason = guard.check_tool_access(
            token.token_id,
            "Bash",
            step_id="step1"
        )
        assert allowed == False
        print("   ✅ Bash 工具访问拒绝（无权限）")

        # 签发完整权限令牌
        full_token = tm.issue_token(
            run_id="RUN-001",
            step_id="step2",
            agent_id="agent2",
            permissions=["read", "write", "execute", "deploy", "commit"],
        )

        # 测试所有权限
        allowed, _ = guard.check_tool_access(full_token.token_id, "Read", step_id="step2")
        assert allowed == True
        allowed, _ = guard.check_tool_access(full_token.token_id, "Write", step_id="step2")
        assert allowed == True
        allowed, _ = guard.check_tool_access(full_token.token_id, "Bash", step_id="step2")
        assert allowed == True
        print("   ✅ 完整权限令牌测试通过")


def test_retry_error_type():
    """测试 RetryErrorType 枚举"""
    print_section("测试 7: RetryErrorType")

    assert RetryErrorType.STEP_EXECUTION_FAILED.value == "step_execution_failed"
    assert RetryErrorType.VALIDATION_FAILED.value == "validation_failed"
    assert RetryErrorType.TOKEN_EXPIRED.value == "token_expired"
    assert RetryErrorType.DEPENDENCY_FAILED.value == "dependency_failed"
    assert RetryErrorType.UNKNOWN_ERROR.value == "unknown_error"
    print("   ✅ RetryErrorType 枚举正常")


def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 LEE Orchestrator v3.1 - Phase 5 集成测试")
    print("=" * 60)

    test_retry_policy()
    test_retry_executor()
    test_preset_policies()
    test_execute_with_retry()
    test_token_manager()
    test_tool_guard()
    test_retry_error_type()

    print("\n" + "=" * 60)
    print("✅ Phase 5 所有测试通过！")
    print("=" * 60)

    print("\n📋 验证结果:")
    print("  ✅ RetryPolicy")
    print("  ✅ RetryExecutor")
    print("  ✅ 预设策略 (DEFAULT/FAST_FAIL/AGGRESSIVE)")
    print("  ✅ execute_with_retry")
    print("  ✅ TokenManager")
    print("  ✅ ToolGuard")
    print("  ✅ RetryErrorType")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
