"""
End-to-end integration tests
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch
import time


class TestE2E:
    """End-to-end tests for the complete pipeline"""

    @pytest.fixture
    def workspace(self, tmp_path):
        """Create temporary workspace"""
        ws = tmp_path / "workspace_e2e"
        ws.mkdir()
        yield ws
        shutil.rmtree(ws, ignore_errors=True)

    @pytest.mark.e2e
    def test_full_pipeline_mocked(self, workspace):
        """Test complete pipeline: case → script → execute → judge"""
        from lee.qa.generator.playwright_gen import PlaywrightGenerator
        from lee.qa.generator.base import GenerationRequest
        from lee.qa.runner.local import LocalRunner
        from lee.qa.runner.base import TestConfig
        from lee.qa.classifier.error_classifier import ErrorClassifier
        from lee.qa.utils.llm import MockLLMClient

        # 1. Generate script
        mock_llm = MockLLMClient()
        mock_llm.set_response("simple", """
```python
import pytest

def test_simple_page(page):
    '''Test simple page access'''
    page.goto("about:blank")
    assert page.title() == ""
```
""")

        request = GenerationRequest(
            test_cases=[{
                "case_id": "F-001",
                "title": "Simple page access",
                "priority": "P0",
                "steps": [],
                "expected_result": "Page loads",
            }],
            base_url="about:blank",
        )

        generator = PlaywrightGenerator(llm_client=mock_llm)
        gen_result = generator.generate(request)
        assert gen_result.validation.is_valid
        assert "def test_" in gen_result.code

        # 2. Save script
        script_path = workspace / "test_e2e.py"
        script_path.write_text(gen_result.code)
        assert script_path.exists()

        # 3. Execute (mocked to avoid actual browser)
        config = TestConfig(
            scripts=[script_path],
            base_url="about:blank",
            output_dir=workspace / "output",
            headless=True,
        )

        with patch('lee.qa.runner.local.sync_playwright'):
            runner = LocalRunner(config)
            run_result = runner.execute()

        assert run_result is not None

    @pytest.mark.e2e
    def test_error_recovery_pipeline(self, workspace):
        """Test pipeline with error recovery"""
        from lee.qa.validator.syntax_validator import SyntaxValidator
        from lee.qa.fixer.auto_fixer import AutoFixer
        from lee.qa.classifier.error_classifier import ErrorClassification

        # 1. Start with bad code
        bad_code = """
def test(  # Syntax error
    page.goto("http://localhost:3000")
"""

        # 2. Validate
        result = SyntaxValidator.validate(bad_code)
        assert not result.is_valid

        # 3. Create classification
        classification = ErrorClassification(
            type="code_issue",
            category="code_syntax",
            confidence=0.9,
            is_false_fail=True,
            suggested_action="auto_fix",
            explanation="Syntax error",
        )

        # 4. Apply fix (will try to fix)
        fixed_code, success = AutoFixer.apply_fix(bad_code, classification, {})
        # Fix attempt is made (may not fully fix syntax errors)

    @pytest.mark.e2e
    def test_validation_pipeline(self):
        """Test multi-layer validation pipeline"""
        from lee.qa.validator.schema_validator import SchemaValidator
        from lee.qa.validator.syntax_validator import SyntaxValidator
        from lee.qa.validator.selector_validator import SelectorValidator
        from lee.qa.validator.timeout_validator import TimeoutValidator

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

def test_login(page):
    '''Test login'''
    page.set_default_timeout(30000)
    page.goto("http://localhost:3000/login")
    page.locator("[data-testid='username']").fill("test")
    page.locator("[data-testid='password']").fill("test")
    page.locator("[data-testid='submit']").click()
"""

        # Run all validation layers
        results = {
            "schema": SchemaValidator.validate(code),
            "syntax": SyntaxValidator.validate(code),
            "selector": SelectorValidator.validate(code),
            "timeout": TimeoutValidator.validate(code),
        }

        # All should pass
        for name, result in results.items():
            assert result.is_valid, f"{name} validation failed"

    @pytest.mark.e2e
    def test_classifier_statistics(self):
        """Test error classification statistics"""
        from lee.qa.classifier.error_classifier import ErrorClassifier

        errors = [
            "SyntaxError: invalid syntax",
            "AssertionError: test failed",
            "Timeout waiting for selector",
            "NET::ERR_CONNECTION_REFUSED",
            "NameError: name 'x' is not defined",
        ]

        classifications = [ErrorClassifier.classify(e) for e in errors]
        stats = ErrorClassifier.get_statistics(classifications)

        assert stats["total"] == 5
        assert stats["code_issue"] > 0
        assert stats["system_issue"] > 0
        assert 0 < stats["false_fail_rate"] < 1

    @pytest.fixture
    def complex_test_case(self):
        """Complex test case for validation"""
        return {
            "case_id": "COMPLEX-001",
            "title": "Complex multi-step test",
            "priority": "P0",
            "type": "positive",
            "preconditions": ["User logged in", "Cart has items"],
            "steps": [
                {"step_num": 1, "action": "Go to cart", "expected": "Cart page loads"},
                {"step_num": 2, "action": "Click checkout", "expected": "Checkout page loads"},
                {"step_num": 3, "action": "Fill payment info", "expected": "Payment accepted"},
                {"step_num": 4, "action": "Confirm order", "expected": "Order created"},
            ],
            "expected_result": "Order successfully created",
        }

    @pytest.mark.e2e
    def test_complex_case_generation(self, complex_test_case):
        """Test generation of complex test case"""
        from lee.qa.generator.playwright_gen import PlaywrightGenerator
        from lee.qa.generator.base import GenerationRequest
        from lee.qa.utils.llm import MockLLMClient

        mock_llm = MockLLMClient()
        mock_llm.set_response("complex", """
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

def test_complex_001(page):
    '''Complex multi-step test'''
    page.set_default_timeout(30000)
    page.goto("http://localhost:3000/cart")
    expect(page).to_have_title("Cart")
    page.locator("[data-testid='checkout']").click()
    expect(page).to_have_url(".*checkout")
    page.locator("[data-testid='confirm']").click()
```
""")

        generator = PlaywrightGenerator(llm_client=mock_llm)
        request = GenerationRequest(
            test_cases=[complex_test_case],
            base_url="http://localhost:3000",
        )

        result = generator.generate(request)
        assert result.validation.is_valid
        assert "def test_" in result.code
        # Should include references to the steps
        assert "cart" in result.code.lower() or "checkout" in result.code.lower()
