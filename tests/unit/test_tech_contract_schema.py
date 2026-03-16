import json
from pathlib import Path


def test_tech_contract_schema_has_required_bridge_fields():
    schema_path = Path("spec/contracts/tech-contract/v1/schema.json")
    with open(schema_path, encoding="utf-8") as f:
        data = json.load(f)

    assert data["properties"]["id"]["pattern"] == "^TECH-[A-Z0-9-]+$"
    assert data["properties"]["ssot_type"]["const"] == "tech"
    assert "architecture_decisions" in data["required"]
    assert "feat_mapping" in data["required"]
    assert "implementation_rules" in data["required"]
