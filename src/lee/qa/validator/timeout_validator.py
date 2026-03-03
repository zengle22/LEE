"""
QA Module - Timeout Validator (Layer 3)

Validates timeout configurations in test code.
Layer 3 of the validation pyramid.
"""

import re
from typing import Dict, List

from lee.qa.validator.result import ValidationResult


class TimeoutValidator:
    """
    Timeout configuration validator (Layer 3).

    Checks timeout values for reasonableness.
    """

    DEFAULT_TIMEOUT = 30000
    MAX_TIMEOUT = 120000
    MIN_TIMEOUT = 1000

    # Recommended timeout ranges
    RECOMMENDED_RANGES = {
        "default_timeout": (5000, 60000),
        "goto_timeout": (10000, 60000),
        "click_timeout": (0, 30000),
        "wait_timeout": (0, 30000),
    }

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """
        Validate timeout configurations.

        Args:
            code: Generated Python code

        Returns:
            ValidationResult with any issues found
        """
        result = ValidationResult()

        # Find timeout configurations
        timeouts = cls._extract_timeouts(code)

        # Check default timeout
        if "default_timeout" in timeouts:
            value = timeouts["default_timeout"]
            if value < cls.RECOMMENDED_RANGES["default_timeout"][0]:
                result.add_warning(
                    "timeout_too_short",
                    f"默认超时 {value}ms 可能太短（推荐 ≥ {cls.RECOMMENDED_RANGES['default_timeout'][0]}ms）"
                )
            elif value > cls.MAX_TIMEOUT:
                result.add_error(
                    "timeout_too_long",
                    f"默认超时 {value}ms 超过最大值 {cls.MAX_TIMEOUT}ms"
                )
        else:
            result.add_warning(
                "no_default_timeout",
                "未设置默认超时，建议使用 set_default_timeout()"
            )

        # Check goto timeout
        if "goto_timeout" in timeouts:
            value = timeouts["goto_timeout"]
            if value < cls.RECOMMENDED_RANGES["goto_timeout"][0]:
                result.add_warning(
                    "goto_timeout_short",
                    f"page.goto() 超时 {value}ms 可能太短（推荐 ≥ {cls.RECOMMENDED_RANGES['goto_timeout'][0]}ms，等待网络）"
                )

        # Check for hardcoded sleeps
        sleep_pattern = r"page\.wait_for_timeout\((\d+)\)"
        for match in re.finditer(sleep_pattern, code):
            duration = int(match.group(1))
            if duration > 5000:
                result.add_warning(
                    "long_sleep",
                    f"wait_for_timeout({duration}ms) 过长，建议用 wait_for_* 替代"
                )

        # Check for time.sleep
        if re.search(r"time\.sleep\(", code):
            result.add_error(
                "time_sleep",
                "禁止使用 time.sleep()，用 wait_for_* 替代"
            )

        return result

    @classmethod
    def _extract_timeouts(cls, code: str) -> Dict[str, int]:
        """
        Extract timeout values from code.

        Args:
            code: Generated Python code

        Returns:
            Dict mapping timeout type to value
        """
        timeouts = {}
        patterns = {
            "default_timeout": r'set_default_timeout\((\d+)\)',
            "goto_timeout": r'goto\([^,]+,\s*timeout=(\d+)\)',
            "click_timeout": r'click\([^,]+,\s*timeout=(\d+)\)',
            "wait_timeout": r'wait_for_[^(]+\([^,]+,\s*timeout=(\d+)\)',
        }

        for name, pattern in patterns.items():
            matches = re.findall(pattern, code)
            if matches:
                # Take the first match
                timeouts[name] = int(matches[0])

        return timeouts

    @classmethod
    def suggest_timeouts(cls, code: str) -> Dict[str, int]:
        """
        Suggest appropriate timeout values.

        Args:
            code: Generated Python code

        Returns:
            Dict with suggested timeout values
        """
        return {
            "default_timeout": cls.DEFAULT_TIMEOUT,
            "goto_timeout": 60000,
        }
