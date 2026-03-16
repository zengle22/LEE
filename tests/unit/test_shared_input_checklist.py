from pathlib import Path

import yaml


def test_shared_input_validation_checklist_covers_all_four_input_areas():
    checklist_path = Path("spec/contracts/shared-input-schema/v1/checklist/input_validation_checklist.yaml")
    assert checklist_path.exists(), "Shared input validation checklist not found"

    with open(checklist_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    check_ids = [item["id"] for item in data["checks"]]
    assert "formal_ssot_id_format" in check_ids
    assert "source_refs_format" in check_ids
    assert "governing_adrs_format" in check_ids
    assert "repo_context_branch_rule" in check_ids
