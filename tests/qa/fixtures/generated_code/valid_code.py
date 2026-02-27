"""
Valid test code for testing validators.
"""

import pytest
from playwright.sync_api import sync_playwright, expect


@pytest.fixture(scope="module")
def browser_context():
    """Browser context fixture for tests."""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            base_url="http://localhost:3000",
        )
        page = context.new_page()
        yield page
        browser.close()


def test_login_success(page):
    """
    Test successful login flow.

    Steps:
    1. Navigate to login page
    2. Enter username and password
    3. Click login button

    Expected: User is logged in and redirected to home
    """
    page.goto("http://localhost:3000/login")
    expect(page).to_have_title("Login")

    page.locator("[data-testid='username']").fill("testuser")
    page.locator("[data-testid='password']").fill("password123")
    page.locator("[data-testid='submit']").click()

    expect(page).to_have_url("http://localhost:3000/home")


def test_logout(page):
    """
    Test logout functionality.

    Steps:
    1. Click logout button
    2. Confirm logout

    Expected: User is logged out
    """
    page.goto("http://localhost:3000/home")
    page.locator("[data-testid='logout']").click()

    expect(page).to_have_url("http://localhost:3000/login")
