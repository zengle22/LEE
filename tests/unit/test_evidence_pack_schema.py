import json
from pathlib import Path


def test_evidence_pack_schema_requires_all_evidence_types():
    schema_path = Path("spec-global/departments/dev/contracts/evidence-pack/v1/schema.json")
    with open(schema_path, encoding="utf-8") as f:
        data = json.load(f)

    required = data["required"]
    assert "formal_ssot_id" in required
    assert "delivery_outputs" in required
    assert "verification_results" in required
    evidence_types = data["properties"]["evidence_types"]["items"]["enum"]
    assert evidence_types == [
        "code_diff",
        "test_report",
        "review_record",
        "deployment_record",
        "integration_report",
    ]
