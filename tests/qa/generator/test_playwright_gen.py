"""
Unit tests for PlaywrightGenerator
"""

import pytest
from unittest.mock import Mock, patch
from lee.qa.generator.playwright_gen import PlaywrightGenerator
from lee.qa.generator.base import GenerationRequest
from lee.qa.utils.llm import MockLLMClient


class TestPlaywrightGenerator:
    """Tests for PlaywrightGenerator"""

    @pytest.fixture
    def mock_llm(self):
        """Mock LLM client"""
        mock = MockLLMClient()
        mock.set_response("test", """
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

    def test_generate_includes_imports(self, generator, sample_request):
        """Test that generated code includes required imports"""
        result = generator.generate(sample_request)
        assert "from playwright.sync_api import" in result.code
        assert "import pytest" in result.code

    def test_generate_includes_test_functions(self, generator, sample_request):
        """Test that generated code includes test functions"""
        result = generator.generate(sample_request)
        assert "def test_" in result.code

    def test_generate_returns_files(self, generator, sample_request):
        """Test that generate returns file dict"""
        result = generator.generate(sample_request)
        assert isinstance(result.files, dict)
        assert "test_main.py" in result.files

    def test_extract_code_with_markdown(self, generator):
        """Test code extraction from markdown"""
        response = '''
```python
def test():
    pass
```
'''
        code = generator._extract_code(response)
        assert "def test():" in code
        assert "```" not in code

    def test_extract_code_without_markdown(self, generator):
        """Test code extraction without markdown"""
        response = "def test():\n    pass\n"
        code = generator._extract_code(response)
        assert code == response

    def test_build_user_prompt(self, generator, sample_request):
        """Test user prompt building"""
        prompt = generator._build_user_prompt(sample_request)
        assert "测试任务" in prompt
        assert sample_request.base_url in prompt
        assert sample_request.test_cases[0]["title"] in prompt

    def test_split_into_files(self, generator):
        """Test code splitting into files"""
        code = "def test(): pass"
        files = generator._split_into_files(code)
        assert "test_main.py" in files
        assert files["test_main.py"] == code

    def test_get_conftest(self, generator):
        """Test conftest.py generation"""
        conftest = generator._get_conftest()
        assert "import pytest" in conftest
        assert "base_url" in conftest
