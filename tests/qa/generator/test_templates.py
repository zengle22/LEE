"""
Unit tests for Jinja2 templates
"""

import pytest
from lee.qa.generator.playwright_gen import PlaywrightGenerator


class TestTemplates:
    """Tests for code generation templates"""

    @pytest.fixture
    def generator(self):
        """PlaywrightGenerator instance"""
        return PlaywrightGenerator()

    def test_base_template_structure(self, generator):
        """Test base template has required structure"""
        template = generator._get_base_template()

        assert "import pytest" in template
        assert "playwright.sync_api" in template
        assert "browser_context" in template
        assert "{% for test in tests %}" in template
        assert "{% endfor %}" in template

    def test_template_variables(self, generator):
        """Test template uses correct variables"""
        template = generator._get_base_template()

        assert "{{ base_url }}" in template
        assert "{{ test.name }}" in template
        assert "{{ test.title }}" in template
        assert "{{ test.expected }}" in template

    def test_conftest_template(self, generator):
        """Test conftest.py template"""
        conftest = generator._get_conftest()

        assert "import pytest" in conftest
        assert "base_url" in conftest
        assert "os.getenv" in conftest

    def test_template_fixture_code(self, generator):
        """Test generated fixture code"""
        template = generator._get_base_template()

        assert "@pytest.fixture(scope=\"module\")" in template
        assert "sync_playwright()" in template
        assert "chromium.launch" in template
        assert "new_context" in template
        assert "yield page" in template
        assert "browser.close()" in template

    def test_template_test_function_structure(self, generator):
        """Test test function structure in template"""
        template = generator._get_base_template()

        assert "def test_{{ test.name }}(page):" in template
        assert '"""' in template  # docstring support

    def test_conftest_fixture_signature(self, generator):
        """Test conftest fixture has correct signature"""
        conftest = generator._get_conftest()

        assert "@pytest.fixture(scope=\"session\")" in conftest
        assert "def base_url():" in conftest
