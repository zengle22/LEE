"""
Unit tests for Runner base classes
"""

import pytest
from pathlib import Path
from lee.qa.runner.base import TestConfig, TestResult, CaseResult


class TestTestConfig:
    """Tests for TestConfig"""

    def test_default_values(self, tmp_path):
        """Test default configuration values"""
        config = TestConfig(
            scripts=[tmp_path / "test.py"],
            base_url="http://localhost:3000",
        )
        assert config.base_url == "http://localhost:3000"
        assert config.headless is True
        assert config.timeout == 30000
        assert config.environment == "local"

    def test_output_dir_creation(self, tmp_path):
        """Test that output directories are created"""
        output_dir = tmp_path / "output"
        config = TestConfig(
            scripts=[tmp_path / "test.py"],
            base_url="http://localhost:3000",
            output_dir=output_dir,
        )
        # Directories should exist after __post_init__
        assert config.output_dir.exists()
        assert config.screenshot_dir.exists()
        assert config.trace_dir.exists()
        assert config.video_dir.exists()

    def test_custom_subdirectories(self, tmp_path):
        """Test custom subdirectory paths"""
        config = TestConfig(
            scripts=[tmp_path / "test.py"],
            base_url="http://localhost:3000",
            output_dir=tmp_path / "output",
            screenshot_dir=tmp_path / "screenshots",
        )
        assert config.screenshot_dir == tmp_path / "screenshots"


class TestCaseResult:
    """Tests for CaseResult"""

    def test_passed_result(self):
        """Test passed case result"""
        result = CaseResult(
            case_id="test_001",
            status="passed",
            exit_code=0,
            duration_ms=1000,
        )
        assert result.case_id == "test_001"
        assert result.status == "passed"
        assert result.exit_code == 0

    def test_failed_result(self):
        """Test failed case result"""
        result = CaseResult(
            case_id="test_002",
            status="failed",
            error="AssertionError: Expected True but got False",
            exit_code=1,
            error_type="system_issue",
            is_code_issue=False,
        )
        assert result.status == "failed"
        assert result.error_type == "system_issue"
        assert result.is_code_issue is False

    def test_invalid_run_result(self):
        """Test invalid_run (code issue) result"""
        result = CaseResult(
            case_id="test_003",
            status="invalid_run",
            error="SyntaxError: invalid syntax",
            exit_code=2,
            error_type="code_issue",
            is_code_issue=True,
        )
        assert result.status == "invalid_run"
        assert result.error_type == "code_issue"
        assert result.is_code_issue is True


class TestTestResult:
    """Tests for TestResult"""

    def test_success_result(self):
        """Test successful test result"""
        result = TestResult(
            exit_code=0,
            total=5,
            passed=5,
            failed=0,
            duration_ms=5000,
        )
        assert result.exit_code == 0
        assert result.total == 5
        assert result.passed == 5
        assert result.failed == 0

    def test_failure_result(self):
        """Test failed test result"""
        result = TestResult(
            exit_code=1,
            total=5,
            passed=3,
            failed=2,
            duration_ms=5000,
        )
        assert result.exit_code == 1
        assert result.failed == 2

    def test_with_case_results(self):
        """Test result with individual case results"""
        cases = [
            CaseResult(case_id="test_1", status="passed", exit_code=0),
            CaseResult(case_id="test_2", status="failed", exit_code=1, error="Failed"),
            CaseResult(case_id="test_3", status="skipped", exit_code=0),
        ]
        result = TestResult(
            exit_code=1,
            total=3,
            passed=1,
            failed=1,
            skipped=1,
            cases=cases,
        )
        assert len(result.cases) == 3
        assert result.cases[0].status == "passed"
        assert result.cases[1].error == "Failed"
