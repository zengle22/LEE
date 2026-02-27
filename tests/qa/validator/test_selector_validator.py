"""
Unit tests for SelectorValidator
"""

import pytest
from lee.qa.validator.selector_validator import SelectorValidator


class TestSelectorValidator:
    """Tests for SelectorValidator (Layer 3 validation)"""

    def test_data_testid_selector(self):
        """Test that data-testid selector gets highest score"""
        result = SelectorValidator.validate_selector("[data-testid='submit']")
        assert result["score"] == 1.0
        assert len(result["issues"]) == 0

    def test_id_selector(self):
        """Test that id selector gets high score"""
        result = SelectorValidator.validate_selector("#submit")
        assert result["score"] >= 0.9

    def test_role_selector(self):
        """Test that ARIA role selector gets good score"""
        result = SelectorValidator.validate_selector("[role='button']")
        assert result["score"] >= 0.8

    def test_class_selector(self):
        """Test that class selector gets fair score"""
        result = SelectorValidator.validate_selector(".btn-primary")
        assert result["score"] >= 0.5

    def test_nth_child_penalty(self):
        """Test that nth-child selector gets penalty"""
        result = SelectorValidator.validate_selector("li:nth-child(1)")
        assert result["score"] < 0.7
        assert len(result["issues"]) > 0

    def test_dynamic_class_penalty(self):
        """Test that dynamic class gets penalty"""
        result = SelectorValidator.validate_selector(".class-abc123")
        assert result["score"] < 0.7
        assert any("动态类名" in issue for issue in result["issues"])

    def test_complex_path_penalty(self):
        """Test that complex CSS path gets penalty"""
        result = SelectorValidator.validate_selector("div > ul > li > a")
        assert result["score"] < 0.7

    def test_validate_code_with_good_selectors(self):
        """Test validation of code with good selectors"""
        code = """
def test_example(page):
    page.locator("[data-testid='submit']").click()
    page.locator("[data-testid='cancel']").click()
"""
        result = SelectorValidator.validate(code)
        assert result.is_valid or len(result.warnings) == 0

    def test_validate_code_with_poor_selectors(self):
        """Test validation of code with poor selectors"""
        code = """
def test_example(page):
    page.locator("li:nth-child(1)").click()
    page.locator(".class-xyz123").click()
"""
        result = SelectorValidator.validate(code)
        assert len(result.warnings) > 0

    def test_no_selectors_in_code(self):
        """Test code with no selectors"""
        code = """
def test_example(page):
    page.goto("http://localhost:3000")
"""
        summary = SelectorValidator.validate_selectors_in_code(code)
        assert summary["total"] == 0

    def test_selectors_in_code_summary(self):
        """Test summary of selectors in code"""
        code = """
def test_example(page):
    page.locator("[data-testid='a']").click()
    page.locator("#b").click()
    page.locator(".c").click()
    page.locator("li:nth-child(1)").click()
"""
        summary = SelectorValidator.validate_selectors_in_code(code)
        assert summary["total"] == 4
        assert summary["avg_score"] > 0
        assert summary["by_score"]["excellent"] >= 1
        assert summary["by_score"]["poor"] >= 1

    def test_low_score_selectors_list(self):
        """Test that low-score selectors are listed"""
        code = """
def test_example(page):
    page.locator("li:nth-child(1)").click()
    page.locator("div:first-child").click()
"""
        summary = SelectorValidator.validate_selectors_in_code(code)
        assert len(summary["low_score_selectors"]) > 0
