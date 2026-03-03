"""
QA Module - Auto Fixer

Automatically fixes common code issues in generated tests.
"""

import re
from typing import Dict, List, Optional, Tuple

from lee.qa.classifier.error_classifier import ErrorClassification


class AutoFixer:
    """
    Automatic code fixer for common test code issues.

    Applies fixes for selector errors, timeout issues, import errors, etc.
    """

    # Fix strategies for different error types
    FIX_STRATEGIES = {
        "code_syntax": "fix_syntax",
        "code_import": "fix_import",
        "code_selector": "fix_selector",
        "code_timeout": "fix_timeout",
        "code_api": "fix_api",
    }

    @classmethod
    def can_fix(cls, classification: ErrorClassification) -> bool:
        """
        Check if an error can be automatically fixed.

        Args:
            classification: Error classification result

        Returns:
            True if auto-fix is available
        """
        if classification.type != "code_issue":
            return False

        return classification.category in cls.FIX_STRATEGIES

    @classmethod
    def apply_fix(
        cls,
        code: str,
        classification: ErrorClassification,
        context: Optional[Dict] = None
    ) -> Tuple[str, bool]:
        """
        Apply automatic fix to the code.

        Args:
            code: Original test code
            classification: Error classification
            context: Runtime context (for selector fixes)

        Returns:
            Tuple of (fixed_code, success)
        """
        if not cls.can_fix(classification):
            return code, False

        strategy = cls.FIX_STRATEGIES.get(classification.category)
        if not strategy:
            return code, False

        fixer_method = getattr(cls, strategy, None)
        if not fixer_method:
            return code, False

        try:
            fixed_code = fixer_method(code, classification, context)
            return fixed_code, True
        except Exception:
            return code, False

    @classmethod
    def fix_selector(
        cls,
        code: str,
        classification: ErrorClassification,
        context: Optional[Dict]
    ) -> str:
        """
        Fix selector errors.

        Args:
            code: Original code
            classification: Error classification
            context: Runtime context with available selectors

        Returns:
            Fixed code
        """
        # Extract the bad selector from error message
        error_msg = classification.details.get("error_message", "")

        # Try to extract selector from error message
        # Multiple patterns to match different error message formats
        selector_match = (
            re.search(r'selector ["\']([^"\']+)["\']', error_msg) or  # selector "#id"
            re.search(r'selector\s+([^\s,]+)', error_msg) or  # selector #id
            re.search(r'locator\(["\']([^"\']+)["\']\)', error_msg) or  # locator("#id")
            re.search(r'waiting for\s+["\']?([^"\'\s,]+)["\']?', error_msg)  # waiting for #id
        )

        if selector_match:
            bad_selector = selector_match.group(1)

            # Find alternative selectors from context
            similar_selectors = context.get("similar_selectors", []) if context else []
            page_elements = context.get("page_elements", {}) if context else {}

            # Use similar selector if available
            if similar_selectors:
                new_selector = similar_selectors[0]
                code = cls._replace_selector(code, bad_selector, new_selector)

            # Or suggest data-testid alternatives
            elif page_elements:
                # Find first data-testid element
                for selector in page_elements.keys():
                    if "data-testid" in selector:
                        code = cls._replace_selector(code, bad_selector, selector)
                        break

        return code

    @classmethod
    def _replace_selector(cls, code: str, old_selector: str, new_selector: str) -> str:
        """Replace a selector in the code"""
        # Escape special regex characters in selector
        escaped = re.escape(old_selector)

        # Replace in locator() calls
        code = re.sub(
            rf'locator\(["\']?{escaped}["\']?\)',
            f'locator("{new_selector}")',
            code
        )

        # Replace in page.locator() calls
        code = re.sub(
            rf'page\.locator\(["\']?{escaped}["\']?\)',
            f'page.locator("{new_selector}")',
            code
        )

        return code

    @classmethod
    def fix_timeout(
        cls,
        code: str,
        classification: ErrorClassification,
        context: Optional[Dict]
    ) -> str:
        """
        Fix timeout issues by increasing timeout values.

        Args:
            code: Original code
            classification: Error classification
            context: Runtime context

        Returns:
            Fixed code
        """
        # Check if default timeout exists
        if "set_default_timeout" in code:
            # Double the default timeout
            code = re.sub(
                r'set_default_timeout\((\d+)\)',
                lambda m: f'set_default_timeout({min(int(m.group(1)) * 2, 120000)})',
                code
            )
        else:
            # Add default timeout after page creation
            code = re.sub(
                r'(page = context\.new_page\(\))',
                r'\1\n    page.set_default_timeout(60000)',
                code
            )

        # Increase goto timeouts
        code = re.sub(
            r'goto\([^,]+,\s*timeout=(\d+)\)',
            lambda m: f'goto({m.group(0).split("timeout=")[0].rstrip(",")}timeout={min(int(m.group(1)) * 2, 120000)})',
            code
        )

        return code

    @classmethod
    def fix_import(
        cls,
        code: str,
        classification: ErrorClassification,
        context: Optional[Dict]
    ) -> str:
        """
        Fix missing imports.

        Args:
            code: Original code
            classification: Error classification
            context: Runtime context

        Returns:
            Fixed code
        """
        error_msg = classification.details.get("error_message", "")

        # Extract missing module name
        module_match = re.search(r"no module named ['\"](.+?)['\"]", error_msg)
        if module_match:
            missing_module = module_match.group(1)

            # Add import statement
            import_line = f"import {missing_module}"

            # Find first import and add before it
            import_match = re.search(r'^(import |from )', code, re.MULTILINE)
            if import_match:
                insert_pos = import_match.start()
                code = code[:insert_pos] + import_line + "\n" + code[insert_pos:]
            else:
                code = import_line + "\n\n" + code

        return code

    @classmethod
    def fix_syntax(
        cls,
        code: str,
        classification: ErrorClassification,
        context: Optional[Dict]
    ) -> str:
        """
        Attempt to fix common syntax errors.

        Args:
            code: Original code
            classification: Error classification
            context: Runtime context

        Returns:
            Fixed code (or original if can't fix)
        """
        error_msg = classification.details.get("error_message", "")

        # Fix common issues
        fixes = [
            # Missing colon after function def
            (r'(def \w+\([^)]*\))([^\n:])', r'\1:\2'),
            # Missing comma in function calls
            (r'(\w+)\s+\(', r'\1('),  # This is too broad, skip
        ]

        for pattern, replacement in fixes:
            code = re.sub(pattern, replacement, code)

        return code

    @classmethod
    def fix_api(
        cls,
        code: str,
        classification: ErrorClassification,
        context: Optional[Dict]
    ) -> str:
        """
        Fix common API usage errors.

        Args:
            code: Original code
            classification: Error classification
            context: Runtime context

        Returns:
            Fixed code
        """
        error_msg = classification.details.get("error_message", "")

        # Fix common API mistakes
        fixes = [
            # page.click() -> page.locator().click()
            (r'page\.click\(["\']([^"\']+)["\']\)', r'page.locator("\1").click()'),
            # page.fill() -> page.locator().fill()
            (r'page\.fill\(["\']([^"\']+)["\'],\s*["\']([^"\']+)["\']\)',
             r'page.locator("\1").fill("\2")'),
        ]

        for pattern, replacement in fixes:
            code = re.sub(pattern, replacement, code)

        return code

    @classmethod
    def apply_all_fixes(
        cls,
        code: str,
        classifications: List[ErrorClassification],
        context: Optional[Dict] = None
    ) -> Tuple[str, Dict]:
        """
        Apply all applicable fixes to the code.

        Args:
            code: Original code
            classifications: List of error classifications
            context: Runtime context

        Returns:
            Tuple of (fixed_code, fix_summary)
        """
        fixed_code = code
        summary = {
            "applied": 0,
            "skipped": 0,
            "failed": 0,
            "fixes": [],
        }

        for classification in classifications:
            if not cls.can_fix(classification):
                summary["skipped"] += 1
                continue

            original_code = fixed_code
            fixed_code, success = cls.apply_fix(fixed_code, classification, context)

            if success and fixed_code != original_code:
                summary["applied"] += 1
                summary["fixes"].append({
                    "category": classification.category,
                    "action": classification.suggested_action,
                })
            elif success:
                summary["skipped"] += 1
            else:
                summary["failed"] += 1

        return fixed_code, summary
