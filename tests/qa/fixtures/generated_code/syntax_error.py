"""
Code with syntax errors for testing validators.
"""

import pytest
from playwright.sync_api import sync_playwright


def test(  # Syntax error: missing function name and incomplete definition
    page.goto("http://localhost:3000")


def test_missing_colon(page)
    """Test missing colon after function definition."""
    page.goto("http://localhost:3000")


def test_indentation_error(page):
    """Test with incorrect indentation."""
    page.goto("http://localhost:3000")
  page.click("button")  # Wrong indentation


def test_unclosed_string(page):
    """Test with unclosed string."""
    page.goto("http://localhost:3000")
    page.click("button)  # Unclosed quote
