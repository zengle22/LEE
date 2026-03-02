"""
Unit tests for PlaywrightGenerator (TypeScript/@playwright/test)
"""

import pytest
import json
from unittest.mock import Mock, patch
from lee.qa.generator.playwright_gen import PlaywrightGenerator
from lee.qa.generator.base import GenerationRequest
from lee.qa.utils.llm import MockLLMClient


class TestPlaywrightGenerator:
    """Tests for PlaywrightGenerator"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client returning TypeScript code"""
        mock = MockLLMClient()
        mock.set_response("test", """
```typescript
import { test, expect } from '@playwright/test';

test.describe('Login Test', () => {
  test('should login successfully', async ({ page }) => {
    await page.goto('http://localhost:3000');
    await expect(page).toHaveTitle('Login');
  });
});
```
""")
        return mock

    @pytest.fixture
    def generator(self, mock_llm):
        """PlaywrightGenerator with mock LLM"""
        return PlaywrightGenerator(llm_client=mock_llm)

    @pytest.fixture
    def sample_request(self, sample_test_case):
        """Sample generation request"""
        return GenerationRequest(
            test_cases=[sample_test_case],
            base_url="http://localhost:3000",
        )

    def test_generator_properties(self, generator):
        """Test generator properties"""
        assert generator.name == "playwright"
        assert generator.framework == "playwright"

    def test_generate_returns_code(self, generator, sample_request):
        """Test that generate returns code"""
        result = generator.generate(sample_request)
        assert result.code is not None
        assert len(result.code) > 0

    def test_generate_includes_typescript_imports(self, generator, sample_request):
        """Test that generated code includes TypeScript imports"""
        result = generator.generate(sample_request)
        assert "from '@playwright/test'" in result.code

    def test_generate_includes_test_functions(self, generator, sample_request):
        """Test that generated code includes test functions"""
        result = generator.generate(sample_request)
        assert "test(" in result.code

    def test_generate_returns_files_with_configs(self, generator, sample_request):
        """Test that generate returns file dict with config files"""
        result = generator.generate(sample_request)
        assert isinstance(result.files, dict)
        # Should have config files
        assert "package.json" in result.files
        assert "playwright.config.ts" in result.files
        assert "tsconfig.json" in result.files
        # Should have test file
        assert "e2e/test.spec.ts" in result.files

    def test_extract_code_with_typescript_markdown(self, generator):
        """Test code extraction from TypeScript markdown"""
        response = '''
```typescript
import { test, expect } from '@playwright/test';

test('example', async ({ page }) => {
  await page.goto('http://localhost:3000');
});
```
'''
        code = generator._extract_code(response)
        assert "from '@playwright/test'" in code
        assert "```" not in code

    def test_extract_code_with_ts_markdown(self, generator):
        """Test code extraction from ts markdown"""
        response = '''
```ts
test('example', async ({ page }) => {});
```
'''
        code = generator._extract_code(response)
        assert "test(" in code

    def test_extract_code_without_markdown(self, generator):
        """Test code extraction without markdown"""
        response = "test('example', async ({ page }) => {});\n"
        code = generator._extract_code(response)
        assert code == response.strip()

    def test_build_user_prompt(self, generator, sample_request):
        """Test user prompt building"""
        prompt = generator._build_user_prompt(sample_request)
        assert "测试任务" in prompt
        assert "TypeScript" in prompt
        assert sample_request.base_url in prompt
        assert sample_request.test_cases[0]["title"] in prompt

    def test_split_into_files_with_request(self, generator, sample_request):
        """Test code splitting into files with request param"""
        code = "test('example', async ({ page }) => {});"
        files = generator._split_into_files(code, sample_request)
        assert "package.json" in files
        assert "playwright.config.ts" in files
        assert "tsconfig.json" in files
        assert "e2e/test.spec.ts" in files
        assert files["e2e/test.spec.ts"] == code

    def test_get_package_json(self, generator):
        """Test package.json generation"""
        pkg = generator._get_package_json()
        data = json.loads(pkg)
        assert data["name"] == "e2e-tests"
        assert "@playwright/test" in data["devDependencies"]
        assert "typescript" in data["devDependencies"]
        assert "test" in data["scripts"]

    def test_get_playwright_config(self, generator):
        """Test playwright.config.ts generation"""
        config = generator._get_playwright_config("http://localhost:3000")
        assert "defineConfig" in config
        assert "baseURL" in config
        assert "http://localhost:3000" in config
        assert "trace: 'on-first-retry'" in config

    def test_get_playwright_config_different_base_url(self, generator):
        """Test playwright.config.ts with different base URL"""
        config = generator._get_playwright_config("https://example.com")
        assert "https://example.com" in config

    def test_get_tsconfig(self, generator):
        """Test tsconfig.json generation"""
        tsconfig = generator._get_tsconfig()
        data = json.loads(tsconfig)
        assert data["compilerOptions"]["strict"] is True
        assert "@playwright/test" in data["compilerOptions"]["types"]
        assert "e2e/**/*" in data["include"]

    def test_system_prompt_uses_typescript(self, generator):
        """Test that system prompt specifies TypeScript"""
        prompt = generator._get_system_prompt()
        assert "TypeScript" in prompt
        assert "@playwright/test" in prompt
        assert "test.describe" in prompt
