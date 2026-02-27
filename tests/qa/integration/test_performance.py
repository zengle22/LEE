"""
Performance tests for QA module
"""

import pytest
import time


class TestPerformance:
    """Performance benchmarks for QA modules"""

    @pytest.mark.performance
    def test_code_validation_performance(self):
        """Test validation performance on large code"""
        from lee.qa.validator.syntax_validator import SyntaxValidator

        # Generate a large code file
        large_code = "\n".join([
            f"def test_function_{i}(page):\n    assert True\n"
            for i in range(1000)
        ])

        start = time.time()
        result = SyntaxValidator.validate(large_code)
        duration = time.time() - start

        # Should validate 1000 functions in under 1 second
        assert duration < 1.0
        assert result.is_valid

    @pytest.mark.performance
    def test_selector_validation_performance(self):
        """Test selector validation performance"""
        from lee.qa.validator.selector_validator import SelectorValidator

        # Code with many selectors
        code = "\n".join([
            f'page.locator("[data-testid=\'btn-{i}\']").click()'
            for i in range(100)
        ])

        start = time.time()
        summary = SelectorValidator.validate_selectors_in_code(code)
        duration = time.time() - start

        # Should validate 100 selectors quickly
        assert duration < 0.5
        assert summary["total"] == 100

    @pytest.mark.performance
    def test_error_classification_performance(self):
        """Test error classification performance"""
        from lee.qa.classifier.error_classifier import ErrorClassifier

        error_messages = [
            "SyntaxError: invalid syntax",
            "AssertionError: Expected True but got False",
            "Timeout waiting for selector",
            "NET::ERR_CONNECTION_REFUSED",
            "NameError: name 'x' is not defined",
        ] * 200  # 1000 total classifications

        start = time.time()
        for msg in error_messages:
            ErrorClassifier.classify(msg)
        duration = time.time() - start

        # Should classify 1000 errors quickly
        assert duration < 1.0

    @pytest.mark.performance
    def test_schema_validation_performance(self):
        """Test schema validation performance"""
        from lee.qa.validator.schema_validator import SchemaValidator

        # Valid test code
        code = """
import pytest
from playwright.sync_api import sync_playwright, expect

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        browser.close()

""" + "\n".join([
            f"def test_{i}(page):\n    '''Test {i}'''\n    page.goto('http://localhost:3000')"
            for i in range(100)
        ])

        start = time.time()
        result = SchemaValidator.validate(code)
        duration = time.time() - start

        # Should be fast
        assert duration < 0.5
        assert result.is_valid

    @pytest.mark.performance
    def test_timeout_validation_performance(self):
        """Test timeout validation performance"""
        from lee.qa.validator.timeout_validator import TimeoutValidator

        code = "\n".join([
            f"page.set_default_timeout({1000 + i * 1000})"
            for i in range(100)
        ])

        start = time.time()
        result = TimeoutValidator.validate(code)
        duration = time.time() - start

        # Should be fast
        assert duration < 0.5

    @pytest.mark.performance
    def test_full_validation_stack_performance(self):
        """Test full validation stack performance"""
        from lee.qa.validator.schema_validator import SchemaValidator
        from lee.qa.validator.syntax_validator import SyntaxValidator
        from lee.qa.validator.selector_validator import SelectorValidator
        from lee.qa.validator.timeout_validator import TimeoutValidator

        code = """
import pytest
from playwright.sync_api import sync_playwright, expect

@pytest.fixture(scope="module")
def browser_context():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        yield page
        browser.close()

def test_example(page):
    '''Test example'''
    page.set_default_timeout(30000)
    page.goto("http://localhost:3000")
    page.locator("[data-testid='submit']").click()
"""

        start = time.time()
        SchemaValidator.validate(code)
        SyntaxValidator.validate(code)
        SelectorValidator.validate(code)
        TimeoutValidator.validate(code)
        duration = time.time() - start

        # Full validation stack should be fast
        assert duration < 0.5

    @pytest.mark.performance
    def test_auto_fixer_performance(self):
        """Test auto-fixer performance"""
        from lee.qa.fixer.auto_fixer import AutoFixer
        from lee.qa.classifier.error_classifier import ErrorClassification

        code = "page.set_default_timeout(1000)\n" * 100

        classifications = [
            ErrorClassification(
                type="code_issue",
                category="code_timeout",
                confidence=0.8,
                is_false_fail=True,
                suggested_action="adjust_timeout",
                explanation="Timeout",
            )
        ]

        start = time.time()
        fixed, summary = AutoFixer.apply_all_fixes(code, classifications, {})
        duration = time.time() - start

        # Should be fast
        assert duration < 0.5

    @pytest.mark.performance
    def test_context_collector_performance(self):
        """Test context collector performance (with mock)"""
        from lee.qa.classifier.context_collector import ContextCollector

        # Mock page with many elements
        mock_page = Mock()
        mock_page.url = "http://localhost:3000"
        mock_page.title = Mock(return_value="Test")

        # Test selector exists check (simulated)
        start = time.time()
        for i in range(100):
            ContextCollector._selector_exists(mock_page, "[data-testid='btn']")
        duration = time.time() - start

        # Should be fast
        assert duration < 0.1


# Import Mock for tests
from unittest.mock import Mock
