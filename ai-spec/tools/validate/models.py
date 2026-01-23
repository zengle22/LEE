"""Data models for validation results."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional
import json


class SpecType(Enum):
    """Types of specs that can be validated."""
    WORKFLOW = "workflow"
    AGENT = "agent"
    CONTRACT = "contract"
    PROJECT = "project"
    UNKNOWN = "unknown"


class ResultStatus(Enum):
    """Validation result status."""
    PASS = "PASS"
    FAIL = "FAIL"
    WARN = "WARN"
    SKIP = "SKIP"


@dataclass
class ValidationIssue:
    """A single validation issue."""
    message: str
    validator: str
    severity: str = "error"  # error, warning, info
    line: Optional[int] = None
    column: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "message": self.message,
            "validator": self.validator,
            "severity": self.severity,
            "line": self.line,
            "column": self.column,
        }


@dataclass
class ValidationResult:
    """Result of validating a single spec file."""
    spec_type: SpecType
    spec_id: str
    version: str
    path: Path
    status: ResultStatus
    issues: list[ValidationIssue] = field(default_factory=list)

    def add_issue(self, issue: ValidationIssue) -> None:
        self.issues.append(issue)
        if issue.severity == "error":
            self.status = ResultStatus.FAIL

    def to_dict(self) -> dict:
        return {
            "spec_type": self.spec_type.value,
            "spec_id": self.spec_id,
            "version": self.version,
            "path": str(self.path),
            "status": self.status.value,
            "issues": [i.to_dict() for i in self.issues],
        }

    def format_cli(self) -> str:
        """Format result for CLI output."""
        status_str = f"[{self.status.value}]"
        spec_str = f"{self.spec_type.value} {self.spec_id}@{self.version}"

        lines = [f"{status_str} {spec_str}"]
        for issue in self.issues:
            prefix = "  - " if issue.severity == "error" else "  ~ "
            lines.append(f"{prefix}{issue.message}")

        return "\n".join(lines)


@dataclass
class ValidationReport:
    """Aggregated validation report."""
    results: list[ValidationResult] = field(default_factory=list)

    @property
    def passed(self) -> int:
        return sum(1 for r in self.results if r.status == ResultStatus.PASS)

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == ResultStatus.FAIL)

    @property
    def warned(self) -> int:
        return sum(1 for r in self.results if r.status == ResultStatus.WARN)

    @property
    def total(self) -> int:
        return len(self.results)

    @property
    def success(self) -> bool:
        return self.failed == 0

    def add(self, result: ValidationResult) -> None:
        self.results.append(result)

    def to_dict(self) -> dict:
        return {
            "summary": {
                "total": self.total,
                "passed": self.passed,
                "failed": self.failed,
                "warned": self.warned,
                "success": self.success,
            },
            "results": [r.to_dict() for r in self.results],
        }

    def to_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)

    def format_cli(self) -> str:
        """Format report for CLI output."""
        lines = []

        # Group by status for cleaner output
        for result in sorted(self.results, key=lambda r: (r.status.value, r.spec_type.value)):
            lines.append(result.format_cli())

        # Summary
        lines.append("")
        lines.append("-" * 40)
        lines.append(f"Total: {self.total} | Pass: {self.passed} | Fail: {self.failed} | Warn: {self.warned}")

        return "\n".join(lines)
