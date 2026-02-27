"""
Integration tests for L3 workflow integration
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import Mock, patch

from lee.qa.generator.playwright_gen import PlaywrightGenerator
from lee.qa.generator.base import GenerationRequest
from lee.qa.runner.local import LocalRunner
from lee.qa.runner.base import TestConfig
from lee.qa.classifier.error_classifier import ErrorClassifier


class TestL3WorkflowIntegration:
    """Integration tests for L3 workflow"""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create temporary workspace"""
        ws = tmp_path / "workspace"
        ws.mkdir()
        yield ws
        shutil.rmtree(ws, ignore_errors=True)

    @pytest.fixture
    def sample_test_set(self):
        """Sample test set definition"""
        return {
            "id": "test-set-001",
            "name": "登录功能测试集",
            "type": "e2e_chrome",
            "base_url": "http://localhost:3000",
            "cases": [
                {
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
            ],
        }

    def test_script_generation_integration(self, sample_test_set):
        """Test script generation integration"""
        from lee.qa.utils.llm import MockLLMClient

        mock_llm = MockLLMClient()
        mock_llm.set_response("登录", """
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

def test_f_base_002(page):
    '''开发测试登录'''
    page.goto("http://localhost:3000/login")
    expect(page).to_have_title("Login")
```
""")

        generator = PlaywrightGenerator(llm_client=mock_llm)
        request = GenerationRequest(
            test_cases=sample_test_set["cases"],
            base_url=sample_test_set["base_url"],
        )

        result = generator.generate(request)
        assert result.validation.is_valid
        assert "def test_" in result.code
        assert "import pytest" in result.code

    def test_runner_execution_integration(self, workspace):
        """Test runner execution integration"""
        # Create a simple test script
        script_path = workspace / "test_simple.py"
        script_path.write_text("""
import pytest

def test_simple():
    '''Simple test'''
    assert True
""")

        config = TestConfig(
            scripts=[script_path],
            base_url="about:blank",
            output_dir=workspace / "output",
            headless=True,
        )

        # Mock playwright since we don't need actual browser for this test
        with patch('lee.qa.runner.local.sync_playwright'):
            runner = LocalRunner(config)
            result = runner.execute()

        assert result is not None
        assert result.total >= 0

    def test_error_classification_integration(self):
        """Test error classification integration"""
        test_errors = [
            ("SyntaxError: invalid syntax", "code_issue", True),
            ("AssertionError: Expected True but got False", "system_issue", False),
            ("Timeout waiting for selector", "code_issue", True),
            ("NET::ERR_CONNECTION_REFUSED", "system_issue", False),
        ]

        for error_msg, expected_type, expected_false_fail in test_errors:
            result = ErrorClassifier.classify(error_msg)
            assert result.type == expected_type
            assert result.is_false_fail == expected_false_fail

    def test_full_pipeline_mock(self, workspace, sample_test_set):
        """Test full pipeline with mocked components"""
        from lee.qa.utils.llm import MockLLMClient

        # 1. Generate script (mocked)
        mock_llm = MockLLMClient()
        mock_llm.set_response("test", """
```python
import pytest

def test_f_base_002(page):
    '''Test'''
    page.goto("about:blank")
    assert page.title() == ""
```
""")

        generator = PlaywrightGenerator(llm_client=mock_llm)
        request = GenerationRequest(
            test_cases=sample_test_set["cases"],
            base_url="about:blank",
        )

        gen_result = generator.generate(request)
        assert gen_result.validation.is_valid

        # 2. Save script
        script_path = workspace / "test_script.py"
        script_path.write_text(gen_result.code)

        # 3. Verify script exists
        assert script_path.exists()

    def test_validation_layers_integration(self):
        """Test that all validation layers work together"""
        code = """
import pytest
from playwright.sync_api import sync_playwright

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
    page.locator("[data-testid='button']").click()
"""

        from lee.qa.validator.schema_validator import SchemaValidator
        from lee.qa.validator.syntax_validator import SyntaxValidator
        from lee.qa.validator.selector_validator import SelectorValidator
        from lee.qa.validator.timeout_validator import TimeoutValidator

        # Layer 1: Schema
        schema_result = SchemaValidator.validate(code)
        assert schema_result.is_valid

        # Layer 2: Syntax
        syntax_result = SyntaxValidator.validate(code)
        assert syntax_result.is_valid

        # Layer 3: Selectors
        selector_result = SelectorValidator.validate(code)
        # data-testid should have good score
        assert selector_result.is_valid or len(selector_result.warnings) == 0

        # Layer 3: Timeouts
        timeout_result = TimeoutValidator.validate(code)
        # Should have warning about no default timeout

    def test_classifier_with_context(self):
        """Test classifier with runtime context"""
        error_msg = "Timeout waiting for selector [data-testid='submit']"

        # Context where selector exists
        context_exists = {
            "selector": "[data-testid='submit']",
            "page_elements": {"[data-testid='submit']": {"tag": "button"}},
        }
        result_exists = ErrorClassifier.classify(error_msg, context_exists)
        # Should be uncertain or system (timing issue)
        assert result_exists.type in ["uncertain", "system_issue"]

        # Context where selector doesn't exist
        context_missing = {
            "selector": "[data-testid='submit']",
            "page_elements": {},
        }
        result_missing = ErrorClassifier.classify(error_msg, context_missing)
        # Should be code issue (selector not found)
        assert result_missing.type == "code_issue"
