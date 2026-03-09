"""
Unit tests for Playwright TypeScript templates
"""

import pytest
from lee.qa.generator.playwright_gen import PlaywrightGenerator


class TestTemplates:
    @pytest.fixture
    def generator(self):
        return PlaywrightGenerator()

    def test_base_template_structure(self, generator):
        template = generator._get_base_template()
        assert "import { test, expect } from '@playwright/test';" in template
        assert "test.describe(" in template
        assert "{% for test in tests %}" in template
        assert "{% endfor %}" in template

    def test_template_variables(self, generator):
        template = generator._get_base_template()
        assert "{{ test.name }}" in template
        assert "{{ test.title }}" in template
        assert "{{ test.expected }}" in template
        assert "{{ test.code }}" in template

    def test_template_fixture_code(self, generator):
        template = generator._get_base_template()
        assert "async ({ page }) =>" in template
        assert "// {{ test.title }}" in template
        assert "// Expected: {{ test.expected }}" in template

    def test_template_test_function_structure(self, generator):
        template = generator._get_base_template()
        assert "test('{{ test.name }}'" in template
        assert "{{ test.code }}" in template
