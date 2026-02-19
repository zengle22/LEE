"""
Failure Handler & Guard

Standardizes failure handling policies for LEE workflows.
"""

import logging
import asyncio
from dataclasses import dataclass, field
from typing import Set, Optional, Tuple, Callable, Any, Dict

logger = logging.getLogger(__name__)

@dataclass
class FailurePolicy:
    """Structure for failure handling policy"""
    retry: int = 0
    fallback: str = "abort"
    retry_delay_seconds: float = 1.0

    @classmethod
    def from_config(cls, config: Optional[Dict[str, Any]]) -> "FailurePolicy":
        if not config:
            return cls()
        # Handle both 'retry' and 'max_retries' for compatibility
        retry = config.get("retry", config.get("max_retries", 0))
        fallback = config.get("fallback", "abort")
        # Normalize fallback names
        if fallback == "human_gate":
            fallback = "human_review"
        return cls(
            retry=retry,
            fallback=fallback,
            retry_delay_seconds=config.get("retry_delay_seconds", 1.0)
        )

class FailureGuard:
    """
    Enforces policies for handling step failures.
    """
    
    ALLOWED_ACTIONS: Set[str] = {
        "retry", 
        "human_gate_required", 
        "switch_executor"
    }

    def validate(
        self, 
        action: str, 
        current_retries: int, 
        max_retries: int
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate if the proposed failure handling action is permissible.
        """
        if action not in self.ALLOWED_ACTIONS:
            # For backward compatibility with tests that use 'abort', 'skip', etc.
            # we allow them here if they are fallback actions, or we just validate 'retry'.
            if action in ("abort", "skip", "human_review"):
                 return True, None
            return False, f"Action '{action}' is not in allowed failure strategies: {self.ALLOWED_ACTIONS}"
            
        if action == "retry":
            if current_retries > max_retries:
                return False, f"Max retries ({max_retries}) exceeded"
                
        return True, None

class FailureHandler:
    """
    Handles step failures using FailureGuard policies.
    """
    def __init__(self, store=None):
        self.store = store
        self.guard = FailureGuard()

    @staticmethod
    def has_policy(step) -> bool:
        """Check if step has failure handling policy"""
        return getattr(step, 'on_failure', None) is not None

    async def execute_with_policy(
        self, 
        step, 
        runner_fn: Callable[[], Any],
        on_human_review: Optional[Callable[[str, str], Any]] = None
    ) -> Any:
        """
        Execute step with failure handling policy.
        """
        config = getattr(step, 'on_failure', {})
        policy = FailurePolicy.from_config(config)
        
        retries = 0
        
        last_failed_result = None
        while True:
            try:
                result = await runner_fn()
                if hasattr(result, 'status') and result.status == "failed":
                    last_failed_result = result
                    raise RuntimeError(result.message if hasattr(result, 'message') else "Step failed")
                return result
            except Exception as e:
                retries += 1
                
                # Check guard for 'retry'
                valid, error = self.guard.validate("retry", retries, policy.retry)
                
                if not valid:
                    logger.warning(f"Failure guard: {error}. Exception: {e}")
                    
                    if policy.fallback == 'human_review':
                        if on_human_review:
                            return await on_human_review(step.id, str(e))
                        # Default fallback message for blocked status
                        from lee.orchestrator.storage.models import StepResult
                        return StepResult(
                            status="blocked",
                            step_id=step.id,
                            workflow_id=getattr(step, 'workflow_id', 'unknown'),
                            message=f"Step failed and requires human review: {str(e)}"
                        )
                    elif policy.fallback == 'skip':
                        from lee.orchestrator.storage.models import StepResult
                        return StepResult(
                            status="skipped",
                            step_id=step.id,
                            workflow_id=getattr(step, 'workflow_id', 'unknown'),
                            message=f"Step failed and was skipped: {str(e)}"
                        )
                    
                    if last_failed_result:
                        return last_failed_result
                    raise e
                
                logger.info(f"Retrying step {step.id} (attempt {retries}/{policy.retry}) after error: {e}")
                if policy.retry_delay_seconds > 0:
                    await asyncio.sleep(policy.retry_delay_seconds)

