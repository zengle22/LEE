"""Validation engine - orchestrates validators and produces reports."""

from pathlib import Path
from typing import Optional

from .base import ValidatorRegistry
from .models import (
    ResultStatus,
    SpecType,
    ValidationReport,
    ValidationResult,
)
from .parser import (
    detect_spec_type,
    extract_spec_id,
    find_spec_files,
    parse_file,
)

# Import validators to register them
from . import validators  # noqa: F401


class ValidationEngine:
    """Orchestrates spec validation."""

    def __init__(self, spec_root: Path):
        """Initialize engine.

        Args:
            spec_root: Root directory of ai-spec
        """
        self.spec_root = spec_root
        self.validators = ValidatorRegistry.get_validators(spec_root)

    def validate_file(self, path: Path) -> ValidationResult:
        """Validate a single spec file.

        Args:
            path: Path to the spec file

        Returns:
            ValidationResult with status and any issues
        """
        # Parse the file
        content, parse_error = parse_file(path)

        # Create initial result
        spec_type = SpecType.UNKNOWN
        spec_id = path.stem
        version = "v1"

        if content:
            spec_type = detect_spec_type(path, content)
            spec_id, version = extract_spec_id(path, content)

        result = ValidationResult(
            spec_type=spec_type,
            spec_id=spec_id,
            version=version,
            path=path,
            status=ResultStatus.PASS,
        )

        # Handle parse errors
        if parse_error:
            result.add_issue(parse_error)
            return result

        # Run all applicable validators
        for validator in self.validators:
            if validator.should_validate(spec_type):
                validator.validate(path, spec_type, content, result)

        return result

    def validate_directory(
        self,
        directory: Path,
        spec_type: Optional[SpecType] = None,
    ) -> ValidationReport:
        """Validate all spec files in a directory.

        Args:
            directory: Directory to search
            spec_type: Optional filter by spec type

        Returns:
            ValidationReport with all results
        """
        report = ValidationReport()

        # Find all spec files
        files = find_spec_files(directory, spec_type)

        for file_path in files:
            result = self.validate_file(file_path)
            report.add(result)

        return report

    def validate(
        self,
        target: Path,
        spec_type: Optional[SpecType] = None,
    ) -> ValidationReport:
        """Validate a file or directory.

        Args:
            target: File or directory path
            spec_type: Optional filter by spec type (for directories)

        Returns:
            ValidationReport with all results
        """
        if target.is_file():
            report = ValidationReport()
            report.add(self.validate_file(target))
            return report
        elif target.is_dir():
            return self.validate_directory(target, spec_type)
        else:
            raise FileNotFoundError(f"Target not found: {target}")
