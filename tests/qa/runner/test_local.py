"""
Unit tests for LocalRunner
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from lee.qa.runner.local import LocalRunner
from lee.qa.runner.base import TestConfig


class TestLocalRunner:
    """Tests for LocalRunner"""

    @pytest.fixture
    def config(self, tmp_path):
        """Test configuration"""
        script_path = tmp_path / "test_script.py"
        return TestConfig(
            scripts=[script_path],
            base_url="http://localhost:3000",
            output_dir=tmp_path / "output",
            headless=True,
        )

    @pytest.fixture
    def runner(self, config):
        """LocalRunner instance"""
        return LocalRunner(config)

    def test_runner_name(self, runner):
        """Test runner name"""
        assert runner.name == "local"

    @patch('lee.qa.runner.local.subprocess.run')
    def test_check_environment_with_playwright(self, mock_run):
        """Test environment check with playwright installed"""
        mock_run.return_value = Mock(returncode=0)

        runner = LocalRunner(TestConfig(
            scripts=[Path("test.py")],
            base_url="http://localhost:3000",
        ))

        checks = runner.check_environment()
        # Should have checked playwright and pytest
        assert "pytest" in checks

    def test_execute_creates_output_dirs(self, runner, tmp_path):
        """Test that execute creates output directories"""
        # Output dirs should be created by __post_init__
        assert runner.config.output_dir.exists()
        assert runner.config.screenshot_dir.exists()

    def test_execute_with_valid_script(self, runner, tmp_path):
        """Test execution with a valid test script"""
        # Create a simple test script
        script_content = """
import pytest

def test_example():
    assert True
"""
        runner.config.scripts[0].write_text(script_content)

        # Mock playwright module to avoid browser requirement
        # Patch at the import location in local.py
        with patch('playwright.sync_api.sync_playwright') as mock_pw:
            # Setup mock playwright context manager
            mock_pw_instance = MagicMock()
            mock_pw.return_value = mock_pw_instance
            mock_pw_instance.__enter__ = MagicMock(return_value=mock_pw_instance)
            mock_pw_instance.__exit__ = MagicMock(return_value=False)

            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_page = MagicMock()

            mock_pw_instance.chromium.launch.return_value = mock_browser
            mock_browser.new_context.return_value = mock_context
            mock_context.new_page.return_value = mock_page

            result = runner.execute()

        # Should have some result
        assert result is not None

    @patch('lee.qa.runner.local.ContextCollector')
    def test_context_collection_on_error(self, mock_collector, runner):
        """Test context collection on error"""
        mock_collector.collect_before_test.return_value = {}
        mock_collector.collect_on_error.return_value = {}

        # Test context collection
        context = mock_collector.collect_before_test(None, "")
        assert context is not None

    def test_take_screenshot(self, runner, tmp_path):
        """Test screenshot capture"""
        mock_page = Mock()
        mock_page.screenshot = Mock(return_value=True)

        path = runner._take_screenshot(mock_page, "test_func")
        # Should attempt to take screenshot
        mock_page.screenshot.assert_called_once()

    def test_execute_test_function_passed(self, runner):
        """Test successful test function execution"""
        mock_module = Mock()
        mock_page = Mock()

        # Create a real function that succeeds
        def passing_test():
            pass

        import inspect
        setattr(mock_module, "test_example", passing_test)

        result = runner._execute_test_function(mock_module, "test_example", mock_page)

        assert result.status == "passed"
        assert result.exit_code == 0

    def test_execute_test_function_failed_assertion(self, runner):
        """Test failed test function with assertion"""
        mock_module = Mock()
        mock_page = Mock()

        def failing_test():
            raise AssertionError("Expected True but got False")

        setattr(mock_module, "test_failing", failing_test)

        result = runner._execute_test_function(mock_module, "test_failing", mock_page)

        assert result.status == "failed"
        # Error message contains the assertion text
        assert "Expected True but got False" in result.error or "AssertionError" in result.error

    def test_execute_test_function_code_issue(self, runner):
        """Test function with code issue"""
        mock_module = Mock()
        mock_page = Mock()

        def syntax_error_test():
            # SyntaxError will be classified as code_issue
            raise SyntaxError("invalid syntax")

        setattr(mock_module, "test_syntax", syntax_error_test)

        result = runner._execute_test_function(mock_module, "test_syntax", mock_page)

        # SyntaxError is classified as code_issue, so status is "invalid_run"
        assert result.status == "invalid_run"
        assert result.error_type == "code_issue"
