"""Schema strict mode validator.

Ensures all contract schemas have additionalProperties: false to prevent output drift.
"""

from pathlib import Path
from typing import Any, List, Tuple

from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationIssue, ValidationResult


@ValidatorRegistry.register
class SchemaStrictModeValidator(BaseValidator):
    """Validates that schemas have additionalProperties: false."""

    name = "schema_strict"
    description = "Validates additionalProperties: false in schemas"
    applies_to = [SpecType.CONTRACT]

    def validate(
        self,
        path: Path,
        spec_type: SpecType,
        content: Any,
        result: ValidationResult,
    ) -> None:
        if not isinstance(content, dict):
            return

        # Find all object definitions that should have additionalProperties: false
        missing_locations = self._find_missing_additional_properties(content)

        for location in missing_locations:
            result.add_issue(ValidationIssue(
                message=f"missing 'additionalProperties: false' at {location}",
                validator=self.name,
                severity="error",
            ))

    def _find_missing_additional_properties(
        self,
        content: dict,
        path: str = "root",
    ) -> List[str]:
        """Recursively find object schemas missing additionalProperties: false."""
        missing = []

        # Check if this is an object schema
        if self._is_object_schema(content):
            if content.get("additionalProperties") is not False:
                # Only flag if it has properties defined (actual object schema)
                if "properties" in content:
                    missing.append(path)

        # Recurse into nested structures
        if isinstance(content, dict):
            # Check properties
            props = content.get("properties", {})
            if isinstance(props, dict):
                for key, value in props.items():
                    if isinstance(value, dict):
                        missing.extend(
                            self._find_missing_additional_properties(
                                value, f"{path}.properties.{key}"
                            )
                        )

            # Check items (for arrays)
            items = content.get("items")
            if isinstance(items, dict):
                missing.extend(
                    self._find_missing_additional_properties(
                        items, f"{path}.items"
                    )
                )

            # Check allOf, anyOf, oneOf
            for combiner in ["allOf", "anyOf", "oneOf"]:
                combined = content.get(combiner)
                if isinstance(combined, list):
                    for i, item in enumerate(combined):
                        if isinstance(item, dict):
                            missing.extend(
                                self._find_missing_additional_properties(
                                    item, f"{path}.{combiner}[{i}]"
                                )
                            )

            # Check definitions / $defs
            for defs_key in ["definitions", "$defs"]:
                defs = content.get(defs_key, {})
                if isinstance(defs, dict):
                    for key, value in defs.items():
                        if isinstance(value, dict):
                            missing.extend(
                                self._find_missing_additional_properties(
                                    value, f"{path}.{defs_key}.{key}"
                                )
                            )

        return missing

    def _is_object_schema(self, content: dict) -> bool:
        """Check if content represents an object schema."""
        if not isinstance(content, dict):
            return False

        # Explicit type: object
        if content.get("type") == "object":
            return True

        # Has properties but no explicit type (implicit object)
        if "properties" in content and "type" not in content:
            return True

        return False
