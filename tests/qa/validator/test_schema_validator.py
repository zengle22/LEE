"""
Unit tests for SchemaValidator
"""

import pytest
from lee.qa.validator.schema_validator import SchemaValidator


class TestSchemaValidator:
    """Tests for SchemaValidator (Layer 1 validation)"""

    def test_valid_code_passes(self, valid_test_code):
        """Test that valid code passes schema validation"""
        result = SchemaValidator.validate(valid_test_code)
        assert result.is_valid
        assert len(result.errors) == 0

    def test_missing_playwright_import(self, missing_imports_code):
        """Test detection of missing playwright import"""
        result = SchemaValidator.validate(missing_imports_code)
        assert not result.is_valid
        assert any(e["category"] == "missing_import" for e in result.errors)

    def test_missing_pytest_import(self):
        """Test detection of missing pytest import"""
        code = """
from playwright.sync_api import sync_playwright

def test_example(page):
    pass
"""
        result = SchemaValidator.validate(code)
        assert not result.is_valid
        assert any(e["category"] == "missing_import" for e in result.errors)

    def test_forbidden_wait_for_timeout(self):
        """Test detection of forbidden wait_for_timeout pattern"""
        code = """
import pytest
from playwright.sync_api import sync_playwright

def test_example(page):
    page.wait_for_timeout(5000)
"""
        result = SchemaValidator.validate(code)
        assert not result.is_valid
        assert any(e["category"] == "forbidden_pattern" for e in result.errors)

    def test_forbidden_time_sleep(self):
        """Test detection of forbidden time.sleep pattern"""
        code = """
import pytest
import time

def test_example(page):
    time.sleep(5)
"""
        result = SchemaValidator.validate(code)
        assert not result.is_valid
        assert any("time.sleep" in e["message"] for e in result.errors)

    def test_no_test_functions(self):
        """Test detection when no test functions exist"""
        code = """
import pytest

def helper_function():
    pass
"""
        result = SchemaValidator.validate(code)
        assert not result.is_valid
        assert any(e["category"] == "no_test_functions" for e in result.errors)

    def test_recommended_locator_pattern(self, valid_test_code):
        """Test detection of recommended locator pattern"""
        code = valid_test_code + "\n    page.locator('#id').click()"
        result = SchemaValidator.validate(code)
        # Should have info about best practice
        assert any(i["category"] == "best_practice" for i in result.info)

    def test_recommended_expect_pattern(self, valid_test_code):
        """Test detection of recommended expect pattern"""
        result = SchemaValidator.validate(valid_test_code)
        # Should have info about expect usage
        assert any(i["category"] == "best_practice" for i in result.info)

    def test_validate_test_function(self, valid_test_code):
        """Test validation of specific test function"""
        result = SchemaValidator.validate_test_function(valid_test_code, "test_example")
        # Function should be found
        assert "function_not_found" not in [e["category"] for e in result.errors]
