"""
QA Module - Schema Validator (Layer 1)

Validates code structure against required patterns.
Layer 1 of the validation pyramid.
"""

import re
from typing import List, Dict

from lee.qa.validator.result import ValidationResult


class SchemaValidator:
    """
    Schema validator (Layer 1).

    Checks code structure for required imports, functions,
    and forbidden patterns.
    """

    # Required imports
    REQUIRED_IMPORTS = [
        "from playwright.sync_api import",
        "import pytest",
    ]

    # Required pytest fixtures
    REQUIRED_FIXTURES = [
        "browser_context",
    ]

    # Forbidden patterns (anti-patterns)
    FORBIDDEN_PATTERNS = [
        (r"page\.wait_for_timeout\(\d+\)", "使用硬编码超时，用 wait_for_* 替代"),
        (r"time\.sleep\(", "禁止使用 time.sleep"),
        (r"\.click\(\)", "使用 locator.click() 而非 page.click()"),
    ]

    # Recommended patterns (best practices)
    RECOMMENDED_PATTERNS = [
        (r"page\.locator\(", "使用 page.locator() 定位元素"),
        (r"expect\(", "使用 expect() 进行断言"),
        (r"data-testid[\s]*=", "使用 data-testid 选择器"),
    ]

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """
        Validate code structure.

        Args:
            code: Generated Python code

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult()

        # 1. Check required imports
        for imp in cls.REQUIRED_IMPORTS:
            if imp not in code:
                result.add_error("missing_import", f"缺少必需导入: {imp}")

        # 2. Check forbidden patterns
        for pattern, message in cls.FORBIDDEN_PATTERNS:
            if re.search(pattern, code):
                result.add_error("forbidden_pattern", message)

        # 3. Check recommended patterns (info only)
        for pattern, message in cls.RECOMMENDED_PATTERNS:
            if re.search(pattern, code):
                result.add_info("best_practice", message)

        # 4. Check test functions exist
        test_functions = re.findall(r"def (test_\w+)\(", code)
        if not test_functions:
            result.add_error("no_test_functions", "没有找到测试函数")

        # 5. Check fixtures
        fixtures = re.findall(r"@pytest\.fixture\((.*?)\)", code)
        fixture_names = []
        for f in fixtures:
            # Extract fixture name from parameters
            name_match = re.search(r'name\s*=\s*["\'](\w+)["\']', f)
            if name_match:
                fixture_names.append(name_match.group(1))
            else:
                # Function name after decorator
                func_match = re.search(r'def (\w+)\(', code[code.find(f):code.find(f) + 100])
                if func_match:
                    fixture_names.append(func_match.group(1))

        for req_fixture in cls.REQUIRED_FIXTURES:
            if req_fixture not in fixture_names:
                result.add_warning("missing_fixture", f"缺少 fixture: {req_fixture}")

        return result

    @classmethod
    def validate_test_function(cls, code: str, func_name: str) -> ValidationResult:
        """
        Validate a specific test function.

        Args:
            code: Full code string
            func_name: Name of the test function

        Returns:
            ValidationResult for the function
        """
        result = ValidationResult()

        # Extract function definition
        pattern = rf"def {func_name}\([^)]*\):(.*?)(?=\ndef |\Z)"
        match = re.search(pattern, code, re.DOTALL)

        if not match:
            result.add_error("function_not_found", f"未找到函数: {func_name}")
            return result

        func_body = match.group(1)

        # Check for assertions
        if "assert" not in func_body and "expect" not in func_body:
            result.add_warning("no_assertion", f"函数 {func_name} 没有断言")

        return result
