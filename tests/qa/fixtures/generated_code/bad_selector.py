"""
Code with unstable selectors for testing validators.
"""

import pytest
from playwright.sync_api import sync_playwright


def test_nth_child_selector(page):
    """Using unstable nth-child selector."""
    page.goto("http://localhost:3000")
    page.locator("ul > li:nth-child(1)").click()  # Unstable
    page.locator("div:first-child").click()  # Unstable
    page.locator("li:last-child").click()  # Unstable


def test_dynamic_class_selector(page):
    """Using dynamic class selector."""
    page.goto("http://localhost:3000")
    page.locator(".class-abc123").click()  # Dynamic class
    page.locator(".btn-primary-xyz789").click()  # Dynamic class


def test_complex_css_path(page):
    """Using complex CSS path."""
    page.goto("http://localhost:3000")
    page.locator("div > ul > li > a > span").click()  # Complex path


def test_text_selector(page):
    """Using text selector (not recommended for i18n)."""
    page.goto("http://localhost:3000")
    page.locator("text=Submit").click()  # Text selector
