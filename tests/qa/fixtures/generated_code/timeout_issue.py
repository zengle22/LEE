"""
Code with timeout issues for testing validators.
"""

import pytest
import time
from playwright.sync_api import sync_playwright


def test_hardcoded_timeout(page):
    """Using hardcoded wait_for_timeout (forbidden)."""
    page.goto("http://localhost:3000")
    page.wait_for_timeout(5000)  # Forbidden pattern
    page.click("button")


def test_time_sleep(page):
    """Using time.sleep (forbidden)."""
    page.goto("http://localhost:3000")
    time.sleep(3)  # Forbidden pattern
    page.click("button")


def test_timeout_too_short(page):
    """Default timeout too short."""
    page.set_default_timeout(1000)  # Too short
    page.goto("http://localhost:3000")


def test_timeout_too_long(page):
    """Default timeout too long."""
    page.set_default_timeout(150000)  # Too long (> 120000)
    page.goto("http://localhost:3000")


def test_no_default_timeout(page):
    """Missing default timeout."""
    page.goto("http://localhost:3000")  # No default timeout set
    page.click("button")


def test_goto_timeout_short(page):
    """Goto timeout too short."""
    page.goto("http://localhost:3000", timeout=3000)  # Too short
