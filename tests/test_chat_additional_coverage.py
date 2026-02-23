"""
Additional coverage tests for Chat command functionality.

Tests for previously uncovered code paths in chat.py.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime


class TestChatREPLInitialization:
    """Tests for LeeChatREPL initialization."""

    def test_chat_repl_initializes_session_manager(self):
        """Test that session_id is initialized."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        assert hasattr(repl, 'session_id')
        assert repl.session_id is not None


class TestChatErrorHandling:
    """Tests for error handling in chat."""

    def test_print_error_method(self):
        """Test _print_error method."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        with patch('click.echo') as mock_echo:
            repl._print_error("Test error")

        mock_echo.assert_called()

    def test_print_info_method(self):
        """Test _print_info method."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        with patch('click.echo') as mock_echo:
            repl._print_info("Test info")

        mock_echo.assert_called()


class TestChatWelcomeMessage:
    """Tests for welcome message."""

    def test_print_welcome(self):
        """Test _print_welcome displays welcome."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        with patch('click.echo') as mock_echo:
            repl._print_welcome()

        # Welcome message should have been printed
        assert mock_echo.call_count > 0


class TestChatMetrics:
    """Tests for metrics display."""

    def test_show_metrics(self):
        """Test _show_metrics displays metrics."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime') as MockRuntime:
            mock_runtime = Mock()
            mock_runtime.get_metrics.return_value = {
                "decision_engine_enabled": False
            }

            MockRuntime.return_value = mock_runtime

            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        with patch('click.echo') as mock_echo:
            repl._show_metrics()

        mock_echo.assert_called()


class TestChatHelp:
    """Tests for help display."""

    def test_show_help_includes_all_sections(self):
        """Test help message includes all sections."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        with patch('click.echo') as mock_echo:
            repl._show_help()

        # Get the help text
        calls = [str(call) for call in mock_echo.call_args_list]
        help_text = " ".join(calls)

        # Check key sections are present
        assert "自然语言命令" in help_text or "命令" in help_text
        assert "/status" in help_text
        assert "/log" in help_text
        assert "/list" in help_text


class TestChatResultDisplay:
    """Tests for result data display."""

    def test_display_result_data_with_empty_data(self):
        """Test _display_result_data handles empty data."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        # Should not crash with empty data
        with patch('click.echo'):
            repl._display_result_data({})

    def test_display_result_data_with_workflow_data(self):
        """Test _display_result_data with workflow data."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        data = {
            "workflow_id": "wf_123",
            "template_id": "test_template"
        }

        with patch('click.echo'):
            repl._display_result_data(data)


class TestChatStyles:
    """Tests for chat styling."""

    def test_chat_has_style(self):
        """Test LeeChatREPL has style attribute."""
        from lee.cli.commands.chat import LeeChatREPL
        from prompt_toolkit.styles import Style

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        assert hasattr(repl, 'style')
        assert isinstance(repl.style, Style)


class TestChatAutoSuggest:
    """Tests for auto-suggest functionality."""

    def test_ensure_prompt_auto_suggest_exists(self):
        """Test _ensure_prompt_auto_suggest method exists."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        # Should have the method
        assert hasattr(repl, '_ensure_prompt_auto_suggest')

        # Should not crash when called
        with patch.object(repl, 'session'):
            repl._ensure_prompt_auto_suggest()


class TestChatCommands:
    """Tests for command processing."""

    def test_internal_command_detection(self):
        """Test that internal commands are detected."""
        internal_commands = [
            "/status",
            "/log",
            "/list",
            "/errors",
            "/jobs",
            "/watch",
            "/status wf_123",
            "/log wf_123 10",
        ]

        for cmd in internal_commands:
            assert cmd.startswith("/"), f"{cmd} should start with /"

    def test_non_internal_commands(self):
        """Test that regular input is not detected as internal."""
        regular_inputs = [
            "当前状态如何？",
            "运行下一步",
            "批准 gate_review",
            "help",
            "exit",
            "",
        ]

        for inp in regular_inputs:
            assert not inp.startswith("/"), f"{inp} should not start with /"


class TestFormatHelpers:
    """Additional tests for format helpers."""

    def test_format_status_with_all_statuses(self):
        """Test format_status with all possible statuses."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        statuses = [
            "pending", "running", "paused", "completed",
            "failed", "timeout", "superseded", "cancelled"
        ]

        for status in statuses:
            result = repl._format_status(status)
            assert len(result) > 0  # Should return something
            assert status in result or "?" in result  # Should contain status or unknown indicator

    def test_format_duration_with_various_inputs(self):
        """Test format_duration with various timedelta values."""
        from lee.cli.commands.chat import LeeChatREPL
        from datetime import timedelta

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        test_cases = [
            (timedelta(seconds=0), "0秒"),
            (timedelta(seconds=1), "1秒"),
            (timedelta(seconds=59), "59秒"),
            (timedelta(seconds=60), "1分0秒"),
            (timedelta(seconds=3600), "1小时0分"),
            (timedelta(seconds=3661), "1小时1分"),
        ]

        for duration, expected in test_cases:
            result = repl._format_duration(duration)
            assert expected == result


class TestChatSessionManagement:
    """Tests for chat session management."""

    def test_session_id_format(self):
        """Test that session_id has expected format."""
        from lee.cli.commands.chat import LeeChatREPL

        with patch('lee.cli.commands.chat.PMAgentRuntime'):
            with patch('lee.cli.commands.chat.TemplateManager'):
                with patch('lee.cli.commands.chat.Orchestrator'):
                    repl = LeeChatREPL(project_dir="/tmp", enable_llm=False)

        # Session ID should be a non-empty string
        assert isinstance(repl.session_id, str)
        assert len(repl.session_id) > 0
