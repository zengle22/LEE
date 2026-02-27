"""
Unit tests for ErrorClassifier
"""

import pytest
from lee.qa.classifier.error_classifier import ErrorClassifier, ErrorType


class TestErrorClassifier:
    """Tests for ErrorClassifier"""

    @pytest.mark.parametrize("error_message,expected_type", [
        ("SyntaxError: invalid syntax", ErrorType.CODE_SYNTAX),
        ("IndentationError: unexpected indent", ErrorType.CODE_SYNTAX),
        ("ModuleNotFoundError: No module named 'playwright'", ErrorType.CODE_IMPORT),
        ("NameError: name 'page' is not defined", ErrorType.CODE_API),
        ("Timeout waiting for selector", ErrorType.CODE_SELECTOR),
        ("Timeout waiting for selector [data-testid='x']", ErrorType.CODE_SELECTOR),
        ("AssertionError: Expected true but got false", ErrorType.SYSTEM_ASSERTION),
        ("assert result == expected, but got False", ErrorType.SYSTEM_ASSERTION),
        ("NET::ERR_CONNECTION_REFUSED", ErrorType.SYSTEM_NETWORK),
        ("Status 500 Internal Server Error", ErrorType.SYSTEM_SERVER),
    ])
    def test_classification_patterns(self, error_message, expected_type):
        """Test error classification patterns"""
        result = ErrorClassifier.classify(error_message)
        assert result.category == expected_type.value

    def test_code_issue_is_false_fail(self):
        """Test that code issues are marked as false failures"""
        result = ErrorClassifier.classify("SyntaxError: invalid syntax")
        assert result.is_false_fail is True
        assert result.type == "code_issue"

    def test_system_issue_is_true_fail(self):
        """Test that system issues are marked as true failures"""
        result = ErrorClassifier.classify("AssertionError: Expected X but got Y")
        assert result.is_false_fail is False
        assert result.type == "system_issue"

    def test_uncertain_classification(self):
        """Test classification of uncertain errors"""
        result = ErrorClassifier.classify("Unknown error occurred")
        assert result.type == "uncertain"
        assert result.suggested_action == "manual_review"

    def test_timeout_without_context(self):
        """Test timeout classification without context"""
        result = ErrorClassifier.classify("Timeout after 30000ms")
        assert result.type == "uncertain"
        assert result.category == "timeout"

    def test_timeout_with_selector_exists(self):
        """Test timeout classification when selector exists"""
        context = {
            "selector": "[data-testid='button']",
            "page_elements": {"[data-testid='button']": {"tag": "button"}},
        }
        result = ErrorClassifier.classify("Timeout waiting for selector", context)
        # Should be uncertain or system (timing issue)
        assert result.type in ["uncertain", "system_issue"]

    def test_timeout_with_selector_missing(self):
        """Test timeout classification when selector is missing"""
        context = {
            "selector": "[data-testid='missing']",
            "page_elements": {},
        }
        result = ErrorClassifier.classify("Timeout waiting for selector", context)
        # Should be code issue (selector doesn't exist)
        assert result.type == "code_issue"
        assert result.category == "selector_not_found"

    def test_code_syntax_suggested_action(self):
        """Test suggested action for syntax errors"""
        result = ErrorClassifier.classify("SyntaxError: invalid syntax")
        assert result.suggested_action == "auto_fix"

    def test_system_assertion_suggested_action(self):
        """Test suggested action for assertion failures"""
        result = ErrorClassifier.classify("AssertionError: Expected X but got Y")
        assert result.suggested_action == "file_bug"

    def test_get_statistics(self):
        """Test statistics calculation"""
        classifications = [
            ErrorClassifier.classify("SyntaxError: invalid syntax"),
            ErrorClassifier.classify("AssertionError: failed"),
            ErrorClassifier.classify("Timeout error"),
        ]

        stats = ErrorClassifier.get_statistics(classifications)

        assert stats["total"] == 3
        assert stats["code_issue"] == 1
        assert stats["system_issue"] == 1
        assert stats["uncertain"] == 1
        assert 0 < stats["false_fail_rate"] < 1
