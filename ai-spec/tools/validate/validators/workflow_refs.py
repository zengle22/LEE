"""Workflow agent reference validator.

Checks that all agents referenced in workflow files exist in specs/agents/.
"""

import re
from pathlib import Path
from typing import Any, Set

from ..base import BaseValidator, ValidatorRegistry
from ..models import SpecType, ValidationIssue, ValidationResult


@ValidatorRegistry.register
class WorkflowAgentRefValidator(BaseValidator):
    """Validates that workflow agent references exist."""

    name = "workflow_refs"
    description = "Validates workflow agent references"
    applies_to = [SpecType.WORKFLOW]

    def validate(
        self,
        path: Path,
        spec_type: SpecType,
        content: Any,
        result: ValidationResult,
    ) -> None:
        if not isinstance(content, dict):
            return

        # Collect all agent references from workflow
        agent_refs = self._extract_agent_refs(content)

        # Check each reference
        for agent_name in agent_refs:
            if not self._agent_exists(agent_name):
                result.add_issue(ValidationIssue(
                    message=f"agent {agent_name}@v1 not found",
                    validator=self.name,
                    severity="error",
                ))

    def _extract_agent_refs(self, content: dict) -> Set[str]:
        """Extract all agent names referenced in workflow."""
        agents = set()

        # Check stages -> agents -> name pattern
        stages = content.get("stages", [])
        if isinstance(stages, list):
            for stage in stages:
                if isinstance(stage, dict):
                    stage_agents = stage.get("agents", [])
                    if isinstance(stage_agents, list):
                        for agent in stage_agents:
                            if isinstance(agent, dict):
                                name = agent.get("name")
                                if name:
                                    agents.add(self._normalize_agent_name(name))

        # Also check top-level agents list if present
        top_agents = content.get("agents", [])
        if isinstance(top_agents, list):
            for agent in top_agents:
                if isinstance(agent, dict):
                    name = agent.get("name") or agent.get("agent_id")
                    if name:
                        agents.add(self._normalize_agent_name(name))
                elif isinstance(agent, str):
                    agents.add(self._normalize_agent_name(agent))

        return agents

    def _normalize_agent_name(self, name: str) -> str:
        """Normalize agent name to match directory naming.

        Converts:
        - requirement_alignment_agent -> requirement-alignment-agent
        - product_goal_analyzer -> product-goal-analyzer
        """
        # Replace underscores with hyphens for directory lookup
        return name.replace("_", "-")

    def _agent_exists(self, agent_name: str) -> bool:
        """Check if agent spec exists.

        Looks for:
        - specs/agents/<name>/v1/agent.yaml
        - specs/agents/<name>/v1/agent.yml
        """
        specs_dir = self.spec_root / "specs" / "agents"

        # Try both naming conventions (hyphen and underscore)
        names_to_try = [
            agent_name,
            agent_name.replace("-", "_"),
            agent_name.replace("_", "-"),
        ]

        for name in names_to_try:
            for version in ["v1", "v2"]:  # Check common versions
                for ext in [".yaml", ".yml"]:
                    agent_path = specs_dir / name / version / f"agent{ext}"
                    if agent_path.exists():
                        return True

        return False
