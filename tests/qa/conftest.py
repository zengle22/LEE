"""
Pytest fixtures for QA module tests.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock


@pytest.fixture
def mock_llm_client():
    """Mock LLM client for testing generators"""
    mock = Mock()
    mock.complete.return_value = """
```python
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
    page.goto("http://localhost:3000")
    expect(page).to_have_title("Example")
```
"""
    return mock


@pytest.fixture
def sample_test_case():
    """Sample test case for testing"""
    return {
        "case_id": "F-BASE-002",
        "title": "开发测试登录",
        "priority": "P0",
        "type": "positive",
        "preconditions": ["用户未登录"],
        "steps": [
            {"step_num": 1, "action": "访问登录页", "expected": "页面加载"},
            {"step_num": 2, "action": "点击登录", "expected": "登录成功"},
        ],
        "expected_result": "用户登录成功",
    }


@pytest.fixture
def valid_test_code():
    """Valid test code for testing validators"""
    return """
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
    '''Test example function'''
    page.goto("http://localhost:3000")
    expect(page).to_have_title("Example")
"""


@pytest.fixture
def invalid_syntax_code():
    """Code with syntax errors"""
    return "def test(\n"  # Missing closing parenthesis


@pytest.fixture
def bad_selector_code():
    """Code with unstable selectors"""
    return """
def test_example(page):
    page.locator(":nth-child(1)").click()
    page.locator(".class-abc123").click()
"""


@pytest.fixture
def missing_imports_code():
    """Code missing required imports"""
    return """
def test_example(page):
    page.goto("http://localhost:3000")
"""


@pytest.fixture
def tmp_path(tmp_path):
    """Temporary path for file operations"""
    return tmp_path
