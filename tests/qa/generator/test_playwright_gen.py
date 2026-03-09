"""
Unit tests for PlaywrightGenerator (TypeScript/@playwright/test)
"""

import pytest
import json
from unittest.mock import Mock
from lee.qa.generator.playwright_gen import PlaywrightGenerator
from lee.qa.generator.base import GenerationRequest, GenerationResult
from lee.qa.utils.llm import MockLLMClient


class TestPlaywrightGenerator:
    @pytest.fixture
    def mock_llm(self):
        mock = MockLLMClient()
        mock.set_response("test", "import { test, expect } from '@playwright/test';\n\ntest.describe('Login Test', () => {\n  test('should login successfully', async ({ page }) => {\n    await page.goto('http://localhost:3000');\n    await expect(page).toHaveTitle('Login');\n  });\n});")
        return mock

    @pytest.fixture
    def generator(self, mock_llm):
        return PlaywrightGenerator(llm_client=mock_llm)

    @pytest.fixture
    def sample_request(self, sample_test_case):
        return GenerationRequest(test_cases=[sample_test_case], base_url="http://localhost:3000")

    def test_generator_properties(self, generator):
        assert generator.name == "playwright"
        assert generator.framework == "playwright"

    def test_generate_delegates_to_validate_and_retry(self, generator, sample_request):
        expected = GenerationResult(
            code="import { test } from '@playwright/test';",
            files={"e2e/test.spec.ts": "import { test } from '@playwright/test';"},
            validation=None,
            retries=0,
        )
        generator._validate_and_retry = Mock(return_value=expected)
        result = generator.generate(sample_request)
        generator._validate_and_retry.assert_called_once_with(sample_request)
        assert result is expected

    def test_split_into_files_includes_typescript_imports(self, generator, sample_request):
        code = "import { test, expect } from '@playwright/test';\n\ntest('example', async ({ page }) => {});"
        files = generator._split_into_files(code, sample_request)
        assert "from '@playwright/test'" in files["e2e/test.spec.ts"]

    def test_split_into_files_includes_test_functions(self, generator, sample_request):
        code = "import { test } from '@playwright/test';\n\ntest('example', async ({ page }) => {});"
        files = generator._split_into_files(code, sample_request)
        assert "test(" in files["e2e/test.spec.ts"]

    def test_generate_returns_files_with_configs(self, generator, sample_request):
        files = generator._split_into_files("test('example', async ({ page }) => {});", sample_request)
        assert isinstance(files, dict)
        assert "package.json" in files
        assert "playwright.config.ts" in files
        assert "tsconfig.json" in files
        assert "e2e/test.spec.ts" in files

    def test_extract_code_without_markdown(self, generator):
        response = "test('example', async ({ page }) => {});\n"
        code = generator._extract_code(response)
        assert code == response.strip()

    def test_build_user_prompt(self, generator, sample_request):
        prompt = generator._build_user_prompt(sample_request)
        assert "测试任务" in prompt
        assert "TypeScript" in prompt
        assert sample_request.base_url in prompt
        assert sample_request.test_cases[0]["title"] in prompt

    def test_split_into_files_with_request(self, generator, sample_request):
        code = "test('example', async ({ page }) => {});"
        files = generator._split_into_files(code, sample_request)
        assert "package.json" in files
        assert "playwright.config.ts" in files
        assert "tsconfig.json" in files
        assert "e2e/test.spec.ts" in files
        assert files["e2e/test.spec.ts"] == code

    def test_get_package_json(self, generator):
        pkg = generator._get_package_json()
        data = json.loads(pkg)
        assert data["name"] == "e2e-tests"
        assert "@playwright/test" in data["devDependencies"]
        assert "typescript" in data["devDependencies"]
        assert "test" in data["scripts"]

    def test_get_playwright_config(self, generator):
        config = generator._get_playwright_config("http://localhost:3000")
        assert "defineConfig" in config
