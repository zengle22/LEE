import copy
import json
from pathlib import Path

import pytest
from jsonschema import ValidationError, validate as jsonschema_validate


def _load_schema():
    schema_path = Path("spec/contracts/shared-input-schema/v1/schema.json")
    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)


def _valid_payload():
    return {
        "formal_ssot_id": "FEAT-SRC-009-011",
        "source_refs": ["FEAT-SRC-009-011#delivery", "TECH-FEAT-SRC-009-011-001"],
        "governing_adrs": ["ADR-008"],
        "repo_context": {
            "repo_id": "lee",
            "branch": "codex/src009-execution",
            "module": "spec-global/departments/dev",
        },
    }


def test_shared_input_schema_accepts_canonical_payload():
    jsonschema_validate(instance=_valid_payload(), schema=_load_schema())


@pytest.mark.parametrize(
    ("mutation", "expected_fragment"),
    [
        (lambda payload: payload.pop("formal_ssot_id"), "'formal_ssot_id' is a required property"),
        (lambda payload: payload.__setitem__("formal_ssot_id", "feat-src-009-011"), "'feat-src-009-011'"),
        (lambda payload: payload.__setitem__("source_refs", []), "[] should be non-empty"),
        (
            lambda payload: payload.__setitem__("source_refs", ["delivery-ref"]),
            "'delivery-ref' does not match",
        ),
        (lambda payload: payload.__setitem__("governing_adrs", []), "[] should be non-empty"),
        (
            lambda payload: payload.__setitem__("governing_adrs", ["adr-008"]),
            "'adr-008' does not match",
        ),
        (lambda payload: payload.pop("repo_context"), "'repo_context' is a required property"),
        (
            lambda payload: payload["repo_context"].__setitem__("branch", "hotfix/unsafe"),
            "'hotfix/unsafe' does not match",
        ),
    ],
)
def test_shared_input_schema_rejects_invalid_payloads(mutation, expected_fragment):
    payload = copy.deepcopy(_valid_payload())
    mutation(payload)

    with pytest.raises(ValidationError) as excinfo:
        jsonschema_validate(instance=payload, schema=_load_schema())

    assert expected_fragment in str(excinfo.value)
