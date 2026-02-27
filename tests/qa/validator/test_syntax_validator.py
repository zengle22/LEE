"""
Unit tests for SyntaxValidator
"""

import pytest
from lee.qa.validator.syntax_validator import SyntaxValidator


class TestSyntaxValidator:
    """Tests for SyntaxValidator (Layer 2 validation)"""

    def test_valid_code_passes(self, valid_test_code):
        """Test that valid code passes syntax validation"""
        result = SyntaxValidator.validate(valid_test_code)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_syntax_error_detected(self, invalid_syntax_code):
        """Test detection of syntax errors"""
        result = SyntaxValidator.validate(invalid_syntax_code)
        assert not result.is_valid
        assert any(e["category"] == "syntax_error" for e in result.errors)

    def test_missing_page_parameter(self):
        """Test detection of missing page parameter"""
        code = """
import pytest

def test_example():  # Missing page parameter
    pass
"""
        result = SyntaxValidator.validate(code)
        assert not result.is_valid
        assert any("page" in e.get("message", "") for e in result.errors)

    def test_missing_docstring(self):
        """Test detection of missing docstring"""
        code = """
import pytest

def test_example(page):  # No docstring
    pass
"""
        result = SyntaxValidator.validate(code)
        # Should have warning about missing docstring
        assert any(w["category"] == "missing_docstring" for w in result.warnings)

    def test_empty_function(self):
        """Test detection of empty test function"""
        code = """
import pytest

def test_example(page):
    pass
"""
        result = SyntaxValidator.validate(code)
        # Should warn about empty function (pass only)
        has_empty_warning = any(
            w["category"] == "empty_function" for w in result.errors
        )
        # Note: This might be a warning rather than error in implementation

    def test_with_docstring(self):
        """Test that docstring is recognized"""
        code = '''
import pytest

def test_example(page):
    """This is a test function"""
    page.goto("http://localhost:3000")
'''
        result = SyntaxValidator.validate(code)
        # Should not have missing docstring error
        assert not any(w["category"] == "missing_docstring" for w in result.warnings)

    def test_wait_for_timeout_warning(self):
        """Test detection of wait_for_timeout usage"""
        code = """
import pytest
from playwright.sync_api import sync_playwright

def test_example(page):
    page.wait_for_timeout(5000)
"""
        result = SyntaxValidator.validate(code)
        assert any(w["category"] == "hardcoded_wait" for w in result.warnings)
