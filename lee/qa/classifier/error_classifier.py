"""
QA Module - Error Classifier

Classifies test errors into code_issue vs system_issue.
Distinguishes false failures (test code bugs) from true failures (system bugs).
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Optional, List, Tuple


class ErrorType(Enum):
    """Error type categories"""
    # Code issues (false failures)
    CODE_SYNTAX = "code_syntax"
    CODE_IMPORT = "code_import"
    CODE_API = "code_api"
    CODE_TIMEOUT = "code_timeout"
    CODE_SELECTOR = "code_selector"

    # System issues (true failures)
    SYSTEM_ASSERTION = "system_assertion"
    SYSTEM_NETWORK = "system_network"
    SYSTEM_SERVER = "system_server"
    SYSTEM_DATA = "system_data"

    # Uncertain
    UNCERTAIN = "uncertain"


@dataclass
class ErrorClassification:
    """Result of error classification"""
    type: str  # code_issue / system_issue / uncertain
    category: str  # Specific category from ErrorType
    confidence: float  # 0-1
    is_false_fail: Optional[bool]  # True if code issue, False if system issue
    suggested_action: str  # auto_fix / file_bug / manual_review / retry
    explanation: str
    details: Dict = None

    def __post_init__(self):
        if self.details is None:
            self.details = {}


class ErrorClassifier:
    """
    Error classifier for distinguishing test code issues from system bugs.

    Uses pattern matching and context analysis to classify errors.
    """

    # Code issue patterns (false failures)
    CODE_PATTERNS: List[Tuple[str, ErrorType]] = [
        # Syntax/Import errors
        (r"SyntaxError", ErrorType.CODE_SYNTAX),
        (r"IndentationError", ErrorType.CODE_SYNTAX),
        (r"TabError", ErrorType.CODE_SYNTAX),
        (r"ModuleNotFoundError: no module named", ErrorType.CODE_IMPORT),
        (r"ImportError", ErrorType.CODE_IMPORT),
        (r"NameError: name '(\w+)' is not defined", ErrorType.CODE_API),

        # API usage errors
        (r"AttributeError:.*'Page' object has no attribute", ErrorType.CODE_API),
        (r"AttributeError:.*'Locator' object has no attribute", ErrorType.CODE_API),
        (r"TypeError:.*missing \d+ required positional argument", ErrorType.CODE_API),
        (r"TypeError:.*takes \d+ positional argument but \d+ were given", ErrorType.CODE_API),

        # Selector errors (code issue - wrong selector in test)
        (r"Timeout.*waiting for selector.*strict mode violation", ErrorType.CODE_SELECTOR),
        (r"Timeout.*waiting for selector.*waiting for hidden", ErrorType.CODE_SELECTOR),
        (r"Timeout.*\d+ms exceeded while waiting for element", ErrorType.CODE_SELECTOR),
        (r"playwright\.sync_api\.errors\.TimeoutError.*waiting for", ErrorType.CODE_SELECTOR),
        (r"Element.*not found.*waiting for", ErrorType.CODE_SELECTOR),
        (r"locator\(\):.*didn't match any elements", ErrorType.CODE_SELECTOR),
        (r"No element found", ErrorType.CODE_SELECTOR),

        # Timeout configuration issues
        (r"Timeout.*exceeded.*\d+ms", ErrorType.CODE_TIMEOUT),
    ]

    # System issue patterns (true failures)
    SYSTEM_PATTERNS: List[Tuple[str, ErrorType]] = [
        # Assertion failures (expected behavior didn't match)
        (r"AssertionError", ErrorType.SYSTEM_ASSERTION),
        (r"assert .*failed", ErrorType.SYSTEM_ASSERTION),
        (r"Expected .+ but found", ErrorType.SYSTEM_ASSERTION),
        (r"Expected value .+ to be", ErrorType.SYSTEM_ASSERTION),

        # Network errors (system connectivity)
        (r"NET::ERR_CONNECTION_REFUSED", ErrorType.SYSTEM_NETWORK),
        (r"NET::ERR_TIMED_OUT", ErrorType.SYSTEM_NETWORK),
        (r"ERR_NAME_NOT_RESOLVED", ErrorType.SYSTEM_NETWORK),
        (r"Network error", ErrorType.SYSTEM_NETWORK),

        # Server errors
        (r"Status.*5\d\d", ErrorType.SYSTEM_SERVER),
        (r"Internal Server Error", ErrorType.SYSTEM_SERVER),
        (r"502 Bad Gateway", ErrorType.SYSTEM_SERVER),
        (r"503 Service Unavailable", ErrorType.SYSTEM_SERVER),

        # Data issues (application behavior)
        (r"expected .+ but got .+", ErrorType.SYSTEM_DATA),
        (r"should be .+ but was .+", ErrorType.SYSTEM_DATA),
    ]

    @classmethod
    def classify(
        cls,
        error_message: str,
        context: Optional[Dict] = None
    ) -> ErrorClassification:
        """
        Classify an error into code_issue vs system_issue.

        Args:
            error_message: The error message or traceback
            context: Optional runtime context (page state, selectors, etc.)

        Returns:
            ErrorClassification with type and action suggestion
        """
        error_lower = error_message.lower()

        # 1. Check code issue patterns (highest priority for test code bugs)
        for pattern, error_type in cls.CODE_PATTERNS:
            if re.search(pattern, error_message, re.IGNORECASE):
                return cls._create_code_classification(
                    error_type, error_message, context
                )

        # 2. Check system issue patterns
        for pattern, error_type in cls.SYSTEM_PATTERNS:
            if re.search(pattern, error_message, re.IGNORECASE):
                return cls._create_system_classification(
                    error_type, error_message, context
                )

        # 3. Check for mixed patterns (could be either)
        if "timeout" in error_lower:
            # Timeout could be code (selector wrong) or system (slow load)
            return cls._classify_timeout_error(error_message, context)

        # 4. Unknown error - use context if available
        return cls._classify_uncertain(error_message, context)

    @classmethod
    def _create_code_classification(
        cls,
        error_type: ErrorType,
        error_message: str,
        context: Dict
    ) -> ErrorClassification:
        """Create classification for code issues (false failures)"""
        action_map = {
            ErrorType.CODE_SYNTAX: "auto_fix",
            ErrorType.CODE_IMPORT: "auto_fix",
            ErrorType.CODE_API: "auto_fix",
            ErrorType.CODE_SELECTOR: "verify_selector",
            ErrorType.CODE_TIMEOUT: "adjust_timeout",
        }

        explanation_map = {
            ErrorType.CODE_SYNTAX: "测试代码有语法错误，需要修复",
            ErrorType.CODE_IMPORT: "测试代码缺少必需的导入",
            ErrorType.CODE_API: "测试代码使用了错误的 API",
            ErrorType.CODE_SELECTOR: "选择器错误，元素可能不存在或选择器不匹配",
            ErrorType.CODE_TIMEOUT: "超时配置不当，可能需要增加超时时间",
        }

        return ErrorClassification(
            type="code_issue",
            category=error_type.value,
            confidence=0.85,
            is_false_fail=True,
            suggested_action=action_map.get(error_type, "auto_fix"),
            explanation=explanation_map.get(error_type, "这是测试代码的问题"),
            details={"error_message": error_message},
        )

    @classmethod
    def _create_system_classification(
        cls,
        error_type: ErrorType,
        error_message: str,
        context: Dict
    ) -> ErrorClassification:
        """Create classification for system issues (true failures)"""
        action_map = {
            ErrorType.SYSTEM_ASSERTION: "file_bug",
            ErrorType.SYSTEM_NETWORK: "check_env_or_file_bug",
            ErrorType.SYSTEM_SERVER: "file_bug",
            ErrorType.SYSTEM_DATA: "file_bug",
        }

        explanation_map = {
            ErrorType.SYSTEM_ASSERTION: "断言失败，系统行为与预期不符",
            ErrorType.SYSTEM_NETWORK: "网络错误，可能是环境问题或系统问题",
            ErrorType.SYSTEM_SERVER: "服务器返回错误，需要修复",
            ErrorType.SYSTEM_DATA: "数据问题，系统返回了错误的数据",
        }

        return ErrorClassification(
            type="system_issue",
            category=error_type.value,
            confidence=0.85,
            is_false_fail=False,
            suggested_action=action_map.get(error_type, "file_bug"),
            explanation=explanation_map.get(error_type, "这是被测系统的问题"),
            details={"error_message": error_message},
        )

    @classmethod
    def _classify_timeout_error(
        cls,
        error_message: str,
        context: Optional[Dict]
    ) -> ErrorClassification:
        """Classify timeout errors with context"""
        # Check if selector exists in context
        if context:
            selector = context.get("selector", "")
            page_elements = context.get("page_elements", {})

            if selector and selector in page_elements:
                # Selector exists but timed out - likely system slowness
                return ErrorClassification(
                    type="uncertain",
                    category="timing",
                    confidence=0.6,
                    is_false_fail=False,
                    suggested_action="retry_or_increase_timeout",
                    explanation="元素存在但超时，可能是系统加载延迟",
                    details={"selector": selector},
                )
            elif selector:
                # Selector not found in page elements
                return ErrorClassification(
                    type="code_issue",
                    category="selector_not_found",
                    confidence=0.7,
                    is_false_fail=True,
                    suggested_action="verify_selector",
                    explanation="选择器在页面中未找到，可能是选择器错误",
                    details={"selector": selector},
                )

        # Default timeout classification
        return ErrorClassification(
            type="uncertain",
            category="timeout",
            confidence=0.5,
            is_false_fail=None,
            suggested_action="manual_review",
            explanation="超时错误，无法确定是代码问题还是系统问题",
            details={"error_message": error_message},
        )

    @classmethod
    def _classify_uncertain(
        cls,
        error_message: str,
        context: Optional[Dict]
    ) -> ErrorClassification:
        """Classify uncertain errors"""
        return ErrorClassification(
            type="uncertain",
            category="unknown",
            confidence=0.0,
            is_false_fail=None,
            suggested_action="manual_review",
            explanation="无法自动判断，需要人工审查",
            details={"error_message": error_message},
        )

    @classmethod
    def classify_batch(
        cls,
        errors: List[str],
        context: Optional[Dict] = None
    ) -> List[ErrorClassification]:
        """
        Classify multiple errors.

        Args:
            errors: List of error messages
            context: Optional shared context

        Returns:
            List of ErrorClassification results
        """
        return [cls classify(error, context) for error in errors]

    @classmethod
    def get_statistics(
        cls,
        classifications: List[ErrorClassification]
    ) -> Dict:
        """
        Get statistics from a list of classifications.

        Args:
            classifications: List of ErrorClassification results

        Returns:
            Dict with statistics
        """
        stats = {
            "total": len(classifications),
            "code_issue": 0,
            "system_issue": 0,
            "uncertain": 0,
            "false_fail_rate": 0.0,
            "by_category": {},
        }

        for c in classifications:
            stats[c.type] = stats.get(c.type, 0) + 1
            stats["by_category"][c.category] = stats["by_category"].get(c.category, 0) + 1

        if stats["total"] > 0:
            stats["false_fail_rate"] = stats["code_issue"] / stats["total"]

        return stats
