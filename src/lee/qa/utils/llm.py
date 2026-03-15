"""
QA Module - LLM Client

LLM client wrapper for code generation.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """LLM response"""
    content: str
    model: str
    tokens_used: int = 0
    finish_reason: str = None


class LLMClient:
    """
    LLM client for code generation.

    Provides a unified interface for calling LLM services.
    """

    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None):
        """
        Initialize LLM client.

        Args:
            model: Model name or identifier
            api_key: API key for the service
        """
        self.model = model or os.getenv("LLM_MODEL", "claude-sonnet-4")
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self._client = None

    def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 4000,
    ) -> str:
        """
        Complete a prompt with LLM.

        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate

        Returns:
            Generated text
        """
        if not self._client:
            self._initialize_client()

        response = self._call_llm(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        return response

    def _initialize_client(self):
        """Initialize the LLM client"""
        # Fail fast to avoid fake-success behavior in non-mock mode.
        raise RuntimeError(
            "LLMClient backend is not configured. "
            "Inject a concrete client or use MockLLMClient for tests."
        )

    def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Call the LLM service."""
        raise RuntimeError(
            "LLMClient has no configured backend implementation. "
            "Use MockLLMClient in tests or provide a real provider client."
        )

    def complete_with_feedback(
        self,
        original_prompt: str,
        feedback: str,
        temperature: float = 0.3,
    ) -> str:
        """
        Complete with feedback from previous attempt.

        Args:
            original_prompt: Original user prompt
            feedback: Feedback on previous attempt
            temperature: Sampling temperature

        Returns:
            Generated text incorporating feedback
        """
        system_prompt = f"""You are a code generation expert. The previous attempt had issues:
{feedback}

Please fix these issues and regenerate the code."""

        return self.complete(
            prompt=original_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
        )


class MockLLMClient(LLMClient):
    """
    Mock LLM client for testing.

    Returns predefined responses based on prompt patterns.
    """

    def __init__(self):
        super().__init__()
        self.responses = {}
        self.call_count = 0

    def set_response(self, pattern: str, response: str):
        """Set a response for a specific prompt pattern"""
        self.responses[pattern] = response

    def _call_llm(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Return mock response based on prompt"""
        self.call_count += 1

        # Check for matching patterns
        for pattern, response in self.responses.items():
            if pattern in prompt:
                return response

        # Default response
        return """
```python
import pytest
from playwright.sync_api import sync_playwright

def test_example(page):
    page.goto("http://localhost:3000")
    assert page.title() == "Example"
```
"""


def create_llm_client(mock: bool = False) -> LLMClient:
    """
    Factory function to create LLM client.

    Args:
        mock: If True, return MockLLMClient

    Returns:
        LLM client instance
    """
    if mock:
        return MockLLMClient()
    return LLMClient()
