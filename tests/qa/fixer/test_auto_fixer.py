"""
Unit tests for AutoFixer
"""

import pytest
from lee.qa.fixer.auto_fixer import AutoFixer
from lee.qa.classifier.error_classifier import ErrorClassification


class TestAutoFixer:
    """Tests for AutoFixer"""

    def test_can_fix_code_issue(self):
        """Test that code issues can be fixed"""
        classification = ErrorClassification(
            type="code_issue",
            category="code_syntax",
            confidence=0.9,
            is_false_fail=True,
            suggested_action="auto_fix",
            explanation="Test",
        )
        assert AutoFixer.can_fix(classification) is True

    def test_cannot_fix_system_issue(self):
        """Test that system issues cannot be auto-fixed"""
        classification = ErrorClassification(
            type="system_issue",
            category="system_assertion",
            confidence=0.9,
            is_false_fail=False,
            suggested_action="file_bug",
            explanation="Test",
        )
        assert AutoFixer.can_fix(classification) is False

    def test_fix_selector_replacement(self):
        """Test selector replacement fix"""
        code = 'page.locator("#old-id").click()'
        context = {"similar_selectors": ["#new-id"]}

        classification = ErrorClassification(
            type="code_issue",
            category="code_selector",
            confidence=0.8,
            is_false_fail=True,
            suggested_action="verify_selector",
            explanation="Selector not found",
            details={"error_message": "selector #old-id"},
        )

        fixed, success = AutoFixer.apply_fix(code, classification, context)
        assert success is True
        assert "#new-id" in fixed

    def test_fix_timeout_increase(self):
        """Test timeout increase fix"""
        code = "page.set_default_timeout(10000)"

        classification = ErrorClassification(
            type="code_issue",
            category="code_timeout",
            confidence=0.8,
            is_false_fail=True,
            suggested_action="adjust_timeout",
            explanation="Timeout too short",
        )

        fixed, success = AutoFixer.apply_fix(code, classification, {})
        assert success is True
        # Should be doubled
        assert "20000" in fixed or "60000" in fixed

    def test_fix_import_addition(self):
        """Test import addition fix"""
        code = """
def test(page):
    page.goto("http://localhost:3000")
"""

        classification = ErrorClassification(
            type="code_issue",
            category="code_import",
            confidence=0.9,
            is_false_fail=True,
            suggested_action="auto_fix",
            explanation="Missing import",
            details={"error_message": "no module named 'pytest'"},
        )

        fixed, success = AutoFixer.apply_fix(code, classification, {})
        assert success is True
        assert "import pytest" in fixed

    def test_fix_api_usage(self):
        """Test API usage fix"""
        code = 'page.click("#button")'

        classification = ErrorClassification(
            type="code_issue",
            category="code_api",
            confidence=0.8,
            is_false_fail=True,
            suggested_action="auto_fix",
            explanation="Use locator.click()",
        )

        fixed, success = AutoFixer.apply_fix(code, classification, {})
        assert success is True
        assert "locator" in fixed

    def test_apply_all_fixes(self):
        """Test applying multiple fixes"""
        code = """
page.set_default_timeout(1000)
page.click("#old")
"""

        classifications = [
            ErrorClassification(
                type="code_issue",
                category="code_timeout",
                confidence=0.8,
                is_false_fail=True,
                suggested_action="adjust_timeout",
                explanation="Timeout",
            ),
            ErrorClassification(
                type="code_issue",
                category="code_api",
                confidence=0.8,
                is_false_fail=True,
                suggested_action="auto_fix",
                explanation="API",
            ),
        ]

        fixed, summary = AutoFixer.apply_all_fixes(code, classifications, {})
        assert summary["applied"] >= 1
