"""YAML/JSON syntax validator.

This validator is special - it runs BEFORE parsing, so it handles
parse errors directly in the engine. This file exists for completeness
but syntax validation is handled in parser.py.
"""

from pathlib import Path
from typing import Any

from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationResult


@ValidatorRegistry.register
class SyntaxValidator(BaseValidator):
    """Validates YAML/JSON syntax.

    Note: Actual syntax validation happens during parsing.
    This validator exists as a placeholder and for documentation.
    """

    name = "syntax"
    description = "Validates YAML/JSON syntax"
    applies_to = []  # Applies to all types

    def validate(
        self,
        path: Path,
        spec_type: SpecType,
        content: Any,
        result: ValidationResult,
    ) -> None:
        # Syntax is already validated during parsing
        # If we get here, syntax is valid
        pass
