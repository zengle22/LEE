"""Validator plugins.

Import validators here to auto-register them.
"""

from .syntax import SyntaxValidator
from .workflow_refs import WorkflowAgentRefValidator
from .agent_refs import AgentContractRefValidator
from .schema_strict import SchemaStrictModeValidator
from .downstream_refs import DownstreamAgentRefValidator
from .project_config import ProjectConfigValidator

__all__ = [
    "SyntaxValidator",
    "WorkflowAgentRefValidator",
    "AgentContractRefValidator",
    "SchemaStrictModeValidator",
    "DownstreamAgentRefValidator",
    "ProjectConfigValidator",
]
