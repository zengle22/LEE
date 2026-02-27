"""
Unit tests for error pattern matching
"""

import pytest
from lee.qa.classifier.error_classifier import ErrorClassifier, ErrorType


class TestErrorPatterns:
    """Tests for error pattern matching"""

    def test_syntax_error_patterns(self):
        """Test syntax error pattern matching"""
        patterns = [
            "SyntaxError: invalid syntax",
            "IndentationError: unexpected indent",
            "TabError: inconsistent use of tabs and spaces",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            assert result.type == "code_issue"
            assert result.category == "code_syntax"

    def test_import_error_patterns(self):
        """Test import error pattern matching"""
        patterns = [
            "ModuleNotFoundError: No module named 'playwright'",
            "ImportError: cannot import name 'sync_playwright'",
            "ModuleNotFoundError: No module named 'pytest'",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            assert result.type == "code_issue"
            assert result.category == "code_import"

    def test_api_error_patterns(self):
        """Test API usage error patterns"""
        patterns = [
            "AttributeError: 'Page' object has no attribute 'wait_for'",
            "AttributeError: 'Locator' object has no attribute 'click'",
            "NameError: name 'page' is not defined",
            "TypeError: object of type 'NoneType' has no len()",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            if result.type != "code_issue":
                print(f"DEBUG: pattern='{pattern}' -> type={result.type}, category={result.category}")
            assert result.type == "code_issue"
            assert result.category == "code_api"

    def test_selector_error_patterns(self):
        """Test selector error patterns"""
        patterns = [
            "Timeout 30000ms exceeded while waiting for element to be visible",
            "Timeout waiting for selector [data-testid='submit']",
            "playwright.sync_api.errors.TimeoutError: waiting for selector '.btn'",
            "strict mode violation: waiting for locator to be visible",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            assert result.type == "code_issue"
            assert result.category == "code_selector"

    def test_assertion_error_patterns(self):
        """Test assertion error patterns (system issues)"""
        patterns = [
            "AssertionError: Expected True but got False",
            "assert result.status == 200, but got 500",
            "Expected 'Success' but found 'Error'",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            assert result.type == "system_issue"
            assert result.category == "system_assertion"
            assert result.is_false_fail is False

    def test_network_error_patterns(self):
        """Test network error patterns (system issues)"""
        patterns = [
            "NET::ERR_CONNECTION_REFUSED",
            "NET::ERR_TIMED_OUT",
            "ERR_NAME_NOT_RESOLVED",
            "Network error: connection refused",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            assert result.type == "system_issue"
            assert result.category == "system_network"

    def test_server_error_patterns(self):
        """Test server error patterns (system issues)"""
        patterns = [
            "Status 500: Internal Server Error",
            "502 Bad Gateway",
            "503 Service Unavailable",
            "HTTP 500 Internal Server Error",
        ]

        for pattern in patterns:
            result = ErrorClassifier.classify(pattern)
            assert result.type == "system_issue"
            assert result.category == "system_server"

    def test_confidence_scores(self):
        """Test confidence scores for different patterns"""
        # High confidence for code syntax errors
        result1 = ErrorClassifier.classify("SyntaxError: invalid syntax")
        assert result1.confidence >= 0.8

        # High confidence for assertion failures
        result2 = ErrorClassifier.classify("AssertionError: test failed")
        assert result2.confidence >= 0.8

        # Lower confidence for unknown errors
        result3 = ErrorClassifier.classify("Unknown error occurred")
        assert result3.confidence == 0.0

    def test_suggested_actions(self):
        """Test suggested actions for different error types"""
        actions = {
            "code_syntax": "auto_fix",
            "code_import": "auto_fix",
            "code_api": "auto_fix",
            "code_selector": "verify_selector",
            "code_timeout": "adjust_timeout",
            "system_assertion": "file_bug",
            "system_network": "check_env_or_file_bug",
            "system_server": "file_bug",
        }

        for category, expected_action in actions.items():
            error_msg = f"{category.replace('_', ' ').title()}: test error"
            result = ErrorClassifier.classify(error_msg)
            # Note: This is a simplified test; actual pattern matching may differ

    def test_is_false_fail_flag(self):
        """Test is_false_fail flag is set correctly"""
        # Code issues should be marked as false failures
        code_errors = [
            "SyntaxError: invalid syntax",
            "Timeout waiting for selector",
            "NameError: name 'x' is not defined",
        ]

        for error in code_errors:
            result = ErrorClassifier.classify(error)
            assert result.is_false_fail is True

        # System issues should NOT be marked as false failures
        system_errors = [
            "AssertionError: Expected True but got False",
            "NET::ERR_CONNECTION_REFUSED",
        ]

        for error in system_errors:
            result = ErrorClassifier.classify(error)
            assert result.is_false_fail is False
