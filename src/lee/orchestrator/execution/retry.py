"""
Retry and Error Handling - 错误处理和重试机制

P2-04 改进: 提供自动重试逻辑，支持指数退避策略。
"""

import time
from typing import Callable, Any, Optional, Tuple, Type, List, Dict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class RetryErrorType(Enum):
    """重试错误类型"""
    STEP_EXECUTION_FAILED = "step_execution_failed"
    VALIDATION_FAILED = "validation_failed"
    TOKEN_EXPIRED = "token_expired"
    DEPENDENCY_FAILED = "dependency_failed"
    UNKNOWN_ERROR = "unknown_error"


@dataclass
class RetryAttempt:
    """重试尝试记录"""
    attempt_number: int
    started_at: str
    completed_at: Optional[str] = None
    success: bool = False
    error: Optional[str] = None
    error_type: Optional[RetryErrorType] = None
    duration_seconds: float = 0.0


@dataclass
class RetryResult:
    """重试结果"""
    success: bool
    total_attempts: int
    attempts: List[RetryAttempt] = field(default_factory=list)
    final_error: Optional[str] = None
    final_error_type: Optional[RetryErrorType] = None
    total_duration_seconds: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def failed_attempts(self) -> int:
        """失败次数"""
        return len([a for a in self.attempts if not a.success])

    @property
    def was_successful_on_retry(self) -> bool:
        """是否在重试后成功"""
        return self.success and self.total_attempts > 1


class RetryPolicy:
    """重试策略配置"""

    def __init__(
        self,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        retry_on: Optional[List[Exception]] = None,
    ):
        """
        初始化重试策略

        Args:
            max_retries: 最大重试次数（不包括首次尝试）
            base_delay: 基础延迟时间（秒）
            max_delay: 最大延迟时间（秒）
            exponential_base: 指数退避的底数
            jitter: 是否添加随机抖动
            retry_on: 需要重试的异常类型列表，None 表示重试所有异常
        """
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_on = retry_on

    def get_delay(self, attempt: int) -> float:
        """
        计算延迟时间（指数退避）

        Args:
            attempt: 尝试次数（从 0 开始）

        Returns:
            延迟时间（秒）
        """
        delay = min(
            self.base_delay * (self.exponential_base ** attempt),
            self.max_delay
        )

        if self.jitter:
            import random
            delay = delay * (0.5 + random.random() * 0.5)

        return delay

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """
        判断是否应该重试

        Args:
            error: 发生的异常
            attempt: 当前尝试次数

        Returns:
            是否应该重试
        """
        if attempt >= self.max_retries:
            return False

        if self.retry_on is None:
            return True

        for retry_exception in self.retry_on:
            if isinstance(error, retry_exception):
                return True

        return False


class RetryExecutor:
    """重试执行器"""

    def __init__(self, policy: RetryPolicy = None):
        """
        初始化重试执行器

        Args:
            policy: 重试策略，None 则使用默认策略
        """
        self.policy = policy or RetryPolicy()

    def execute(
        self,
        func: Callable,
        *args: Any,
        **kwargs: Any
    ) -> RetryResult:
        """
        执行函数，并在失败时按策略重试

        Args:
            func: 要执行的函数
            *args: 函数位置参数
            **kwargs: 函数关键字参数

        Returns:
            RetryResult 对象
        """
        attempts: List[RetryAttempt] = []
        total_duration = 0.0

        for attempt in range(self.policy.max_retries + 1):
            attempt_record = RetryAttempt(
                attempt_number=attempt,
                started_at=datetime.now().isoformat(),
            )
            attempts.append(attempt_record)

            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                end_time = time.time()

                attempt_record.success = True
                attempt_record.completed_at = datetime.now().isoformat()
                attempt_record.duration_seconds = end_time - start_time

                return RetryResult(
                    success=True,
                    total_attempts=attempt + 1,
                    attempts=attempts,
                    total_duration_seconds=total_duration + (end_time - start_time),
                )

            except Exception as e:
                end_time = time.time()
                attempt_record.success = False
                attempt_record.completed_at = datetime.now().isoformat()
                attempt_record.error = str(e)
                attempt_record.error_type = self._classify_error(e)
                attempt_record.duration_seconds = end_time - start_time

                # 判断是否继续重试
                if not self.policy.should_retry(e, attempt):
                    break

                # 计算延迟并等待
                delay = self.policy.get_delay(attempt)
                if delay > 0:
                    time.sleep(delay)
                    total_duration += delay

        # 所有尝试都失败了
        last_attempt = attempts[-1]
        return RetryResult(
            success=False,
            total_attempts=len(attempts),
            attempts=attempts,
            final_error=last_attempt.error,
            final_error_type=last_attempt.error_type,
            total_duration_seconds=total_duration + sum(a.duration_seconds for a in attempts),
        )

    def _classify_error(self, error: Exception) -> RetryErrorType:
        """分类错误类型"""
        error_type_str = type(error).__name__.lower()

        if "validation" in error_type_str or "invalid" in error_type_str:
            return RetryErrorType.VALIDATION_FAILED
        elif "token" in error_type_str or "expired" in error_type_str:
            return RetryErrorType.TOKEN_EXPIRED
        elif "dependency" in error_type_str:
            return RetryErrorType.DEPENDENCY_FAILED
        elif "execution" in error_type_str or "runtime" in error_type_str:
            return RetryErrorType.STEP_EXECUTION_FAILED
        else:
            return RetryErrorType.UNKNOWN_ERROR


# 默认重试策略
DEFAULT_RETRY_POLICY = RetryPolicy(
    max_retries=3,
    base_delay=1.0,
    max_delay=30.0,
    exponential_base=2.0,
    jitter=True,
)

# 快速失败策略（用于开发/调试）
FAST_FAIL_POLICY = RetryPolicy(
    max_retries=0,
    base_delay=0,
)

# 激进重试策略（用于不稳定环境）
AGGRESSIVE_RETRY_POLICY = RetryPolicy(
    max_retries=10,
    base_delay=0.5,
    max_delay=60.0,
    exponential_base=1.5,
    jitter=True,
)


def execute_with_retry(
    func: Callable,
    *args: Any,
    max_retries: int = 3,
    policy: RetryPolicy = None,
    **kwargs: Any
) -> RetryResult:
    """
    便捷函数：执行函数并自动重试

    Args:
        func: 要执行的函数
        *args: 函数位置参数
        max_retries: 最大重试次数（如果指定了 policy 则忽略此参数）
        policy: 自定义重试策略
        **kwargs: 函数关键字参数

    Returns:
        RetryResult 对象

    Example:
        result = execute_with_retry(
            some_function,
            arg1, arg2,
            max_retries=5
        )
        if result.success:
            print(f"Success after {result.total_attempts} attempts")
        else:
            print(f"Failed: {result.final_error}")
    """
    if policy is None:
        policy = RetryPolicy(max_retries=max_retries)

    executor = RetryExecutor(policy)
    return executor.execute(func, *args, **kwargs)


def execute_step_with_retry(
    step_func: Callable,
    step_id: str,
    max_retries: int = 3,
    on_retry: Optional[Callable[[int, Exception], None]] = None,
) -> Tuple[bool, Any, Optional[str]]:
    """
    执行步骤并在失败时重试（针对 StateMachine 的专用函数）

    P2-04 改进: 此函数集成到 StateMachine 中使用。

    Args:
        step_func: 步骤执行函数
        step_id: 步骤 ID
        max_retries: 最大重试次数
        on_retry: 每次重试前的回调函数

    Returns:
        (success, result, error) 元组

    Example:
        def execute_step():
            # 执行步骤逻辑
            pass

        success, result, error = execute_step_with_retry(
            execute_step,
            step_id="p1_design",
            max_retries=3
        )
    """
    policy = RetryPolicy(max_retries=max_retries)
    executor = RetryExecutor(policy)

    def wrapped_func():
        return step_func()

    result = executor.execute(wrapped_func)

    # 调用重试回调
    if not result.success and on_retry:
        for i, attempt in enumerate(result.attempts[:-1]):  # 排除最后一次
            if not attempt.success and attempt.error:
                try:
                    error = Exception(attempt.error)
                    on_retry(i, error)
                except Exception:
                    pass

    if result.success:
        return True, None, None
    else:
        return False, None, result.final_error


# ============================================
# 与 StateMachine 集成的辅助函数
# ============================================

def can_retry_step(state_machine, step_id: str, current_attempt: int) -> Tuple[bool, Optional[str]]:
    """
    检查步骤是否可以重试

    Args:
        state_machine: StateMachine 实例
        step_id: 步骤 ID
        current_attempt: 当前尝试次数

    Returns:
        (can_retry, reason) 元组
    """
    # 加载状态
    state = state_machine.load()

    # 检查步骤是否存在
    if step_id not in state["steps"]:
        return False, f"Step not found: {step_id}"

    step = state["steps"][step_id]

    # 检查步骤状态
    if step["state"] != "failed":
        return False, f"Step is not in failed state (current: {step['state']})"

    # 检查是否已达到最大重试次数
    max_retries = step.get("max_retries", 3)
    attempt_count = step.get("retry_count", 0)

    if attempt_count >= max_retries:
        return False, f"Max retries ({max_retries}) exceeded"

    return True, None


def prepare_step_retry(state_machine, step_id: str) -> Tuple[bool, Optional[str]]:
    """
    准备步骤重试

    Args:
        state_machine: StateMachine 实例
        step_id: 步骤 ID

    Returns:
        (success, error) 元组
    """
    # 检查是否可以重试
    can_retry, reason = can_retry_step(state_machine, step_id, 0)
    if not can_retry:
        return False, reason

    # 重置步骤状态
    success, error = state_machine.reset_step(
        step_id,
        reason=f"Preparing retry attempt"
    )

    if not success:
        return False, error

    # 增加重试计数
    state = state_machine.load()
    state["steps"][step_id]["retry_count"] = state["steps"][step_id].get("retry_count", 0) + 1
    state_machine._save_state()

    return True, None
