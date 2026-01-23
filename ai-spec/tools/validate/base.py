"""Base validator interface and registry."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional

from .models import SpecType, ValidationResult


class BaseValidator(ABC):
    """Base class for all validators.

    Validators are responsible for checking specific aspects of spec files.
    Each validator should focus on ONE concern (single responsibility).
    """

    name: str = "base"
    description: str = "Base validator"

    # Which spec types this validator applies to
    applies_to: list[SpecType] = []

    def __init__(self, spec_root: Path):
        """Initialize validator with spec root directory.

        Args:
            spec_root: Root directory of ai-spec (contains specs/, cli/, etc.)
        """
        self.spec_root = spec_root

    @abstractmethod
    def validate(
        self,
        path: Path,
        spec_type: SpecType,
        content: Any,
        result: ValidationResult,
    ) -> None:
        """Validate a spec file.

        Args:
            path: Path to the spec file
            spec_type: Type of the spec (workflow, agent, contract)
            content: Parsed content of the file (dict for YAML/JSON)
            result: ValidationResult to add issues to
        """
        pass

    def should_validate(self, spec_type: SpecType) -> bool:
        """Check if this validator should run for the given spec type."""
        if not self.applies_to:
            return True  # Empty list means validate all
        return spec_type in self.applies_to


class ValidatorRegistry:
    """Registry for validator plugins."""

    _validators: list[type[BaseValidator]] = []

    @classmethod
    def register(cls, validator_class: type[BaseValidator]) -> type[BaseValidator]:
        """Register a validator class (can be used as decorator)."""
        cls._validators.append(validator_class)
        return validator_class

    @classmethod
    def get_validators(cls, spec_root: Path) -> list[BaseValidator]:
        """Get all registered validator instances."""
        return [v(spec_root) for v in cls._validators]

    @classmethod
    def clear(cls) -> None:
        """Clear all registered validators (for testing)."""
        cls._validators = []
