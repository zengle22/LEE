"""
QA Module - Validator Result

Validation result dataclass for all validators.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class ValidationIssue:
    """Single validation issue"""
    type: str  # error, warning, info
    category: str  # missing_import, syntax_error, etc.
    message: str
    line_number: Optional[int] = None
    severity: str = "medium"  # low, medium, high, critical


@dataclass
class ValidationResult:
    """Validation result for generated code"""
    is_valid: bool = True
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    info: List[Dict[str, Any]] = field(default_factory=list)

    def add_error(self, category: str, message: str, line_number: int = None):
        """Add an error"""
        self.errors.append({
            "type": "error",
            "category": category,
            "message": message,
            "line_number": line_number,
        })
        self.is_valid = False

    def add_warning(self, category: str, message: str, line_number: int = None):
        """Add a warning"""
        self.warnings.append({
            "type": "warning",
            "category": category,
            "message": message,
            "line_number": line_number,
        })

    def add_info(self, category: str, message: str):
        """Add an info message"""
        self.info.append({
            "type": "info",
            "category": category,
            "message": message,
        })

    def has_blocking_errors(self) -> bool:
        """Check if there are blocking errors"""
        return len(self.errors) > 0

    def get_summary(self) -> Dict[str, int]:
        """Get summary of issues"""
        return {
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "info": len(self.info),
        }

    @classmethod
    def merge(cls, *results: 'ValidationResult') -> 'ValidationResult':
        """Merge multiple validation results"""
        merged = cls()
        for result in results:
            if not result.is_valid:
                merged.is_valid = False
            merged.errors.extend(result.errors)
            merged.warnings.extend(result.warnings)
            merged.info.extend(result.info)
        return merged


class CodeGenerationError(Exception):
    """Exception raised when code generation fails"""

    def __init__(self, message: str, last_validation: ValidationResult = None):
        super().__init__(message)
        self.last_validation = last_validation
