"""Agent contract reference validator.

Checks that schema_ref fields in agent specs point to existing contracts.
"""

import re
from pathlib import Path
from typing import Any, List, Tuple

from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationIssue, ValidationResult


@ValidatorRegistry.register
class AgentContractRefValidator(BaseValidator):
    """Validates that agent contract references (schema_ref) exist."""

    name = "agent_refs"
    description = "Validates agent contract references"
    applies_to = [SpecType.AGENT]

    def validate(
        self,
        path: Path,
        spec_type: SpecType,
        content: Any,
        result: ValidationResult,
    ) -> None:
        if not isinstance(content, dict):
            return

        # Collect all schema_ref values
        schema_refs = self._extract_schema_refs(content)

        # Check each reference
        for ref, location in schema_refs:
            if ref and not self._contract_exists(ref):
                result.add_issue(ValidationIssue(
                    message=f"contract {ref} not found (referenced in {location})",
                    validator=self.name,
                    severity="error",
                ))

    def _extract_schema_refs(self, content: dict) -> List[Tuple[str, str]]:
        """Extract all schema_ref values with their locations."""
        refs = []

        # Check inputs.schema_ref
        inputs = content.get("inputs", {})
        if isinstance(inputs, dict):
            ref = inputs.get("schema_ref")
            if ref and isinstance(ref, str):
                refs.append((ref, "inputs.schema_ref"))
            elif ref and isinstance(ref, list):
                for i, r in enumerate(ref):
                    if isinstance(r, str):
                        refs.append((r, f"inputs.schema_ref[{i}]"))

        # Check outputs.schema_ref
        outputs = content.get("outputs", {})
        if isinstance(outputs, dict):
            ref = outputs.get("schema_ref")
            if ref and isinstance(ref, str):
                refs.append((ref, "outputs.schema_ref"))
            elif ref and isinstance(ref, list):
                for i, r in enumerate(ref):
                    if isinstance(r, str):
                        refs.append((r, f"outputs.schema_ref[{i}]"))

        return refs

    def _contract_exists(self, schema_ref: str) -> bool:
        """Check if contract exists.

        schema_ref format: contracts/<name>/v1/schema.json
        We need to check for .yaml and .md variants too.
        """
        # Parse the reference path
        # Example: contracts/product-goal-contract/v1/schema.json
        parts = schema_ref.split("/")

        if len(parts) < 3:
            return False

        # Extract contract name and version
        # Handle both "contracts/name/v1/schema.json" and "name/v1/schema.json"
        if parts[0] == "contracts":
            contract_name = parts[1]
            version = parts[2] if len(parts) > 2 else "v1"
        else:
            contract_name = parts[0]
            version = parts[1] if len(parts) > 1 else "v1"

        # Possible locations for contracts
        possible_roots = [
            self.spec_root / "specs" / "common" / "contracts",
            self.spec_root / "specs" / "contracts",
        ]
        
        # Add org-specific contract paths
        org_dir = self.spec_root / "specs" / "org"
        if org_dir.is_dir():
            for org_path in org_dir.iterdir():
                if org_path.is_dir():
                    possible_roots.append(org_path / "contracts")

        # Check each possible root
        for root in possible_roots:
            contracts_dir = root / contract_name / version
            if not contracts_dir.is_dir():
                continue
                
            # Check for any schema file
            for ext in [".yaml", ".yml", ".json", ".md"]:
                schema_path = contracts_dir / f"schema{ext}"
                if schema_path.exists():
                    return True

        return False
