"""
QA Module - Selector Validator (Layer 3)

Validates CSS selector quality and stability.
Layer 3 of the validation pyramid.
"""

import re
from typing import Dict, List

from lee.qa.validator.result import ValidationResult


class SelectorValidator:
    """
    Selector quality validator (Layer 3).

    Analyzes CSS selectors for stability and maintainability.
    """

    # Selector stability scores (higher = more stable)
    STABILITY_SCORES = {
        r'\[data-testid[=\s]?["\']?\w+["\']?\]': 1.0,  # Best: data-testid
        r'\[id[\s]*=[\s]*["\']?\w+["\']?\]': 0.9,       # Very good: id
        r'\[role=[\s]*["\']?\w+["\']?\]': 0.8,          # Good: ARIA role
        r'\.[\w-]+': 0.5,                               # Fair: class
        r'text[\s]*=[\s]*["\'][^"\']+["\']': 0.4,       # Poor: text selector
    }

    # Unstable patterns to avoid
    UNSTABLE_PATTERNS = [
        (r':nth-child\(\d+\)', "硬编码位置，元素变化会失效"),
        (r':first-child', "相对位置，不推荐"),
        (r':last-child', "相对位置，不推荐"),
        (r'\.class-\w+', "动态类名，不稳定"),
        (r'\w+\.\w+\.\w+', "复杂 CSS 路径，不稳定"),
        (r'>>', "CSS 组合器，可能不稳定"),
    ]

    @classmethod
    def validate_selector(cls, selector: str) -> Dict:
        """
        Validate a single selector.

        Args:
            selector: CSS selector string

        Returns:
            Dict with score, issues, and recommendations
        """
        result = {
            "selector": selector,
            "score": 0.0,
            "issues": [],
            "recommendations": [],
        }

        # 1. Check unstable patterns
        for pattern, message in cls.UNSTABLE_PATTERNS:
            if re.search(pattern, selector):
                result["issues"].append(message)
                result["score"] -= 0.3

        # 2. Calculate stability score
        max_score = 0.0
        for pattern, score in cls.STABILITY_SCORES.items():
            if re.search(pattern, selector):
                max_score = max(max_score, score)

        result["score"] = max(0.0, min(1.0, max_score + result["score"]))

        # 3. Generate recommendations
        if result["score"] < 0.7:
            result["recommendations"].append(
                "建议使用 data-testid 属性，并添加到页面元素上"
            )

        return result

    @classmethod
    def validate_selectors_in_code(cls, code: str) -> Dict:
        """
        Validate all selectors in the code.

        Args:
            code: Generated Python code

        Returns:
            Dict with validation summary
        """
        # Extract selectors from code
        # Matches: locator("selector"), page.locator("selector")
        selectors = re.findall(r'locator\(["\']([^"\']+)["\']\)', code)

        results = {
            "total": len(selectors),
            "avg_score": 0.0,
            "low_score_selectors": [],
            "by_score": {
                "excellent": 0,  # 1.0
                "good": 0,       # 0.8-0.99
                "fair": 0,       # 0.5-0.79
                "poor": 0,       # < 0.5
            },
        }

        if len(selectors) == 0:
            return results

        scores = []
        for selector in selectors:
            selector_result = cls.validate_selector(selector)
            scores.append(selector_result["score"])

            # Categorize by score
            if selector_result["score"] >= 1.0:
                results["by_score"]["excellent"] += 1
            elif selector_result["score"] >= 0.8:
                results["by_score"]["good"] += 1
            elif selector_result["score"] >= 0.5:
                results["by_score"]["fair"] += 1
            else:
                results["by_score"]["poor"] += 1

            if selector_result["score"] < 0.7:
                results["low_score_selectors"].append(selector_result)

        if scores:
            results["avg_score"] = sum(scores) / len(scores)

        return results

    @classmethod
    def validate(cls, code: str) -> ValidationResult:
        """
        Validate selectors in code and return ValidationResult.

        Args:
            code: Generated Python code

        Returns:
            ValidationResult
        """
        result = ValidationResult()
        summary = cls.validate_selectors_in_code(code)

        if summary["total"] == 0:
            result.add_warning("no_selectors", "没有找到选择器")
            return result

        if summary["avg_score"] < 0.7:
            result.add_warning(
                "low_selector_quality",
                f"平均选择器稳定性评分: {summary['avg_score']:.2f} < 0.7"
            )

        if summary["by_score"]["poor"] > 0:
            result.add_warning(
                "poor_selectors",
                f"发现 {summary['by_score']['poor']} 个低质量选择器"
            )

        return result
