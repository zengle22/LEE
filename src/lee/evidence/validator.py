from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from jsonschema import Draft7Validator


class EvidenceValidator:
    """Validate evidence-pack payloads against the canonical schema."""

    def __init__(self, schema_path: str):
        self.schema_path = Path(schema_path)
        self.schema = json.loads(self.schema_path.read_text(encoding="utf-8"))
        self.validator = Draft7Validator(self.schema)

    def validate(self, payload: Dict[str, Any]) -> List[str]:
        return [error.message for error in self.validator.iter_errors(payload)]
