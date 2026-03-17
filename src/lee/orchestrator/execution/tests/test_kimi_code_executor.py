"""
Kimi code executor unit tests.
"""

import os

import pytest

from lee.orchestrator.execution.kimi_code_executor import KimiCodeExecutor


class TestKimiCodeExecutor:
    def setup_method(self):
        self.executor = KimiCodeExecutor()

    def test_initialization(self):
        assert self.executor._kimi_binary == "kimi-cli"
        assert self.executor._model == ""

    def test_initialization_calls_super_init(self):
        """Test that KimiCodeExecutor.__init__ calls super().__init__ (BUG-LEE-EXECUTOR-001)."""
        # When super().__init__ is called, it initializes parent class attributes
        executor = KimiCodeExecutor()

        # Verify parent class attributes are accessible
        assert hasattr(executor, '_claude_binary')
        assert hasattr(executor, '_model')
        assert hasattr(executor, '_extra_env')

        # Verify class constants from parent are accessible (Kimi has its own DEFAULT_MODEL)
        assert executor.DEFAULT_MAX_ITERATIONS == 5
        assert executor.DEFAULT_TIMEOUT_SECONDS == 3600
        assert executor.DEFAULT_MODEL == ""  # KimiCodeExecutor defines its own DEFAULT_MODEL

    def test_initialization_with_kwargs_passed_to_parent(self, monkeypatch):
        """Test that kwargs are properly passed to parent __init__."""
        # Set environment variable to test that parent init uses it
        monkeypatch.setenv("CLAUDE_CODE_MODEL", "haiku")

        executor = KimiCodeExecutor(model="custom-model")

        # Verify own attributes
        assert executor._kimi_binary == "kimi-cli"
        # model is set by Kimi's __init__ first, not overridden by parent's
        assert executor._model == "custom-model"

    def test_inherits_parent_methods(self):
        """Test that KimiCodeExecutor inherits methods from ClaudeCodeExecutor."""
        executor = KimiCodeExecutor()

        # Test that parent class methods are available
        assert hasattr(executor, '_build_system_prompt')
        assert hasattr(executor, '_build_user_prompt')
        assert hasattr(executor, '_validate_input')
        assert hasattr(executor, '_parse_claude_output')

    def test_build_kimi_command_without_model(self):
        assert self.executor._build_kimi_command() == [
            "kimi-cli",
            "--print",
            "--output-format",
            "text",
            "--final-message-only",
        ]

    def test_build_kimi_command_with_model(self):
        assert self.executor._build_kimi_command(model="kimi-k2") == [
            "kimi-cli",
            "--print",
            "--output-format",
            "text",
            "--final-message-only",
            "--model",
            "kimi-k2",
        ]

    def test_prepare_evidence_dir_defaults_to_kimi_code(self, tmp_path):
        evidence_dir = self.executor._prepare_evidence_dir("", str(tmp_path))

        assert evidence_dir.exists()
        assert ".workflow" in str(evidence_dir)
        assert "kimi-code" in str(evidence_dir)
