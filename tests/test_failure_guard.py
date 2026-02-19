
import pytest
from unittest.mock import MagicMock, AsyncMock
from lee.orchestrator.execution.failure_handler import FailureGuard, FailureHandler

def test_failure_guard_validation():
    guard = FailureGuard()
    # Retry logic
    assert guard.validate("retry", 1, 3) == (True, None)
    assert guard.validate("retry", 4, 3) == (False, "Max retries (3) exceeded")
    
    # Allowed actions
    assert guard.validate("human_gate_required", 1, 3) == (True, None)
    assert guard.validate("invalid", 1, 3)[0] is False

@pytest.mark.asyncio
async def test_failure_handler_execution():
    handler = FailureHandler()
    
    # Mock step
    step = MagicMock()
    step.id = "step1"
    step.on_failure = {"action": "retry", "max_retries": 2} # Retry 2 times
    
    # Mock runner: fails twice, succeeds third time
    runner = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2"), "success"])
    
    # Mock human review
    review = AsyncMock()
    
    result = await handler.execute_with_policy(step, runner, review)
    assert result == "success"
    assert runner.call_count == 3

@pytest.mark.asyncio
async def test_failure_handler_fallback():
    handler = FailureHandler()
    step = MagicMock()
    step.id = "step1"
    step.on_failure = {"action": "retry", "max_retries": 1, "fallback": "human_gate"}
    
    runner = AsyncMock(side_effect=[Exception("fail1"), Exception("fail2")])
    review = AsyncMock(return_value="human_success")
    
    result = await handler.execute_with_policy(step, runner, review)
    assert result == "human_success"
    # 1 initial + 1 retry = 2 calls
    assert runner.call_count == 2
    review.assert_called_once()
