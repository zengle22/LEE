"""
Unit tests for Generator base classes
"""

import pytest
from lee.qa.generator.base import GenerationRequest, GenerationResult


class TestGenerationRequest:
    """Tests for GenerationRequest"""

    def test_default_options(self, sample_test_case):
        """Test that default options are initialized"""
        request = GenerationRequest(
            test_cases=[sample_test_case],
            base_url="http://localhost:3000"
        )
        assert request.options is not None
        assert request.framework == "playwright"

    def test_custom_options(self, sample_test_case):
        """Test custom options"""
        custom_options = {"timeout": 60000}
        request = GenerationRequest(
            test_cases=[sample_test_case],
            base_url="http://localhost:3000",
            options=custom_options
        )
        assert request.options == custom_options


class TestGenerationResult:
    """Tests for GenerationResult"""

    def test_result_creation(self):
        """Test creating a generation result"""
        from lee.qa.validator.result import ValidationResult

        validation = ValidationResult()
        result = GenerationResult(
            code="def test(): pass",
            files={"test.py": "def test(): pass"},
            validation=validation,
            retries=0
        )
        assert result.code == "def test(): pass"
        assert result.retries == 0
        assert result.validation.is_valid


class TestValidationResultMerge:
    """Tests for ValidationResult.merge"""

    def test_merge_valid_results(self):
        """Test merging valid results"""
        from lee.qa.validator.result import ValidationResult

        r1 = ValidationResult()
        r2 = ValidationResult()
        merged = ValidationResult.merge(r1, r2)
        assert merged.is_valid

    def test_merge_with_invalid(self):
        """Test merging with invalid result"""
        from lee.qa.validator.result import ValidationResult

        r1 = ValidationResult()
        r2 = ValidationResult()
        r2.add_error("test", "test error")
        merged = ValidationResult.merge(r1, r2)
        assert not merged.is_valid
        assert len(merged.errors) == 1

    def test_merge_collects_all_issues(self):
        """Test that merge collects all issues"""
        from lee.qa.validator.result import ValidationResult

        r1 = ValidationResult()
        r1.add_warning("w1", "warning 1")
        r1.add_info("i1", "info 1")

        r2 = ValidationResult()
        r2.add_warning("w2", "warning 2")
        r2.add_error("e1", "error 1")

        merged = ValidationResult.merge(r1, r2)
        assert len(merged.warnings) == 2
        assert len(merged.errors) == 1
        assert len(merged.info) == 1
