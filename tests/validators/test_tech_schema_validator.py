from pathlib import Path

import pytest

from tests.validators.tech_schema_validator import parse_tech_markdown, validate_tech_file


def test_parse_tech_markdown_extracts_required_sections():
    tech_path = Path("spec/tech/TECH-FEAT-SRC-009-003-001__tech-qiaojieduixiangsheji-frozenjizhujiagou.md")
    parsed = parse_tech_markdown(tech_path)

    assert parsed["id"] == "TECH-FEAT-SRC-009-003-001"
    assert parsed["feat_mapping"]["feat_id"] == "FEAT-SRC-009-003"
    assert len(parsed["architecture_decisions"]) >= 1
    assert len(parsed["validation_rules"]) >= 1


def test_validate_tech_file_passes_for_example():
    validate_tech_file(
        "spec/tech/TECH-FEAT-SRC-009-003-001__tech-qiaojieduixiangsheji-frozenjizhujiagou.md",
        "spec/contracts/tech-contract/v1/schema.json",
    )


def test_validate_tech_file_fails_when_parent_ref_missing(tmp_path):
    sample = Path("spec/tech/TECH-FEAT-SRC-009-003-001__tech-qiaojieduixiangsheji-frozenjizhujiagou.md").read_text(encoding="utf-8")
    broken = sample.replace("parent_id: FEAT-SRC-009-003", "parent_id: BUG-001")
    broken_path = tmp_path / "broken-tech.md"
    broken_path.write_text(broken, encoding="utf-8")

    with pytest.raises(Exception):
        validate_tech_file(broken_path, "spec/contracts/tech-contract/v1/schema.json")
