"""
Unit tests for TimeoutValidator
"""

import pytest
from lee.qa.validator.timeout_validator import TimeoutValidator


class TestTimeoutValidator:
    """Tests for TimeoutValidator (Layer 3 validation)"""

    def test_valid_timeout(self):
        """Test that reasonable timeout passes"""
        code = """
def test_example(page):
    page.set_default_timeout(30000)
    page.goto("http://localhost:3000")
"""
        result = TimeoutValidator.validate(code)
        # Should be valid or only have warnings
        assert len(result.errors) == 0

    def test_timeout_too_short_warning(self):
        """Test warning for timeout too short"""
        code = """
def test_example(page):
    page.set_default_timeout(1000)
"""
        result = TimeoutValidator.validate(code)
        assert any(w["category"] == "timeout_too_short" for w in result.warnings)

    def test_timeout_too_long_error(self):
        """Test error for timeout too long"""
        code = """
def test_example(page):
    page.set_default_timeout(150000)
"""
        result = TimeoutValidator.validate(code)
        assert any(e["category"] == "timeout_too_long" for e in result.errors)

    def test_no_default_timeout_warning(self):
        """Test warning when default timeout is not set"""
        code = """
def test_example(page):
    page.goto("http://localhost:3000")
"""
        result = TimeoutValidator.validate(code)
        assert any(w["category"] == "no_default_timeout" for w in result.warnings)

    def test_goto_timeout_warning(self):
        """Test warning for goto timeout too short"""
        code = """
def test_example(page):
    page.goto("http://localhost:3000", timeout=5000)
"""
        result = TimeoutValidator.validate(code)
        assert any(w["category"] == "goto_timeout_short" for w in result.warnings)

    def test_wait_for_timeout_warning(self):
        """Test warning for hardcoded wait"""
        code = """
def test_example(page):
    page.wait_for_timeout(10000)
"""
        result = TimeoutValidator.validate(code)
        assert any(w["category"] == "long_sleep" for w in result.warnings)

    def test_time_sleep_error(self):
        """Test error for time.sleep usage"""
        code = """
import time

def test_example(page):
    time.sleep(5)
"""
        result = TimeoutValidator.validate(code)
        assert any(e["category"] == "time_sleep" for e in result.errors)

    def test_extract_timeouts(self):
        """Test timeout extraction from code"""
        code = """
page.set_default_timeout(30000)
page.goto("http://localhost:3000", timeout=60000)
page.click("button", timeout=5000)
"""
        timeouts = TimeoutValidator._extract_timeouts(code)
        assert timeouts.get("default_timeout") == 30000
        assert timeouts.get("goto_timeout") == 60000
        assert timeouts.get("click_timeout") == 5000

    def test_suggest_timeouts(self):
        """Test timeout suggestion"""
        suggestions = TimeoutValidator.suggest_timeouts("")
        assert "default_timeout" in suggestions
        assert suggestions["default_timeout"] > 0
