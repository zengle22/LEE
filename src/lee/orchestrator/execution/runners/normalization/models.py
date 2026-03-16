from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ExtractionResult:
    raw_output: Any
    generated_text: str
    structured_payload: Optional[Any]
    business_output: Any
    source_kind: str
    written_files: List[str] = field(default_factory=list)


@dataclass
class NormalizationContext:
    step_id: str
    agent_id: str
    workflow_id: str
    project_root: str
    instance_data: Optional[Dict[str, Any]] = None


@dataclass
class NormalizedPayload:
    business_output: Any
    structured_payload: Optional[Dict[str, Any]]
    ssot_contract: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
