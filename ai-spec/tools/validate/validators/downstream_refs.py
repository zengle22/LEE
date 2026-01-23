"""Downstream agent reference validator.

Checks that downstream agent references in agent specs point to existing agents.
This is an extension validator for future-proofing.
"""

from pathlib import Path
from typing import Any, List

from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationIssue, ValidationResult


@ValidatorRegistry.register
class DownstreamAgentRefValidator(BaseValidator):
    """Validates that downstream agent references exist."""

    name = "downstream_refs"
    description = "Validates downstream agent references"
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

        # Check downstream agents
        downstream = content.get("downstream", [])
        if not isinstance(downstream, list):
            return

        for item in downstream:
            if isinstance(item, dict):
                agent_id = item.get("agent_id")
                if agent_id and not self._agent_exists(agent_id):
                    result.add_issue(ValidationIssue(
                        message=f"downstream agent {agent_id}@v1 not found",
                        validator=self.name,
                        severity="error",
                    ))

    def _agent_exists(self, agent_id: str) -> bool:
        """Check if agent spec exists."""
        # Possible locations for agents
        possible_roots = [
            self.spec_root / "specs" / "common" / "agents",
            self.spec_root / "specs" / "agents",
        ]
        
        # Add org-specific agent paths
        org_dir = self.spec_root / "specs" / "org"
        if org_dir.is_dir():
            for org_path in org_dir.iterdir():
                if org_path.is_dir():
                    possible_roots.append(org_path / "agents")

        # Try both naming conventions
        names_to_try = [
            agent_id,
            agent_id.replace("-", "_"),
            agent_id.replace("_", "-"),
        ]

        for root in possible_roots:
            if not root.is_dir():
                continue
            for name in names_to_try:
                for version in ["v1", "v2"]:
                    for ext in [".yaml", ".yml"]:
                        agent_path = root / name / version / f"agent{ext}"
                        if agent_path.exists():
                            return True

        return False
