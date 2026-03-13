from pathlib import Path

import yaml


def test_bugfix_granularity_checklist_covers_default_rule_and_five_same_dimensions():
    checklist_path = Path("spec-global/departments/dev/governance/bugfix-granularity-checklist.yaml")
    assert checklist_path.exists(), "Bugfix granularity checklist not found"

    with open(checklist_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    check_ids = [item["id"] for item in data["checks"]]
    assert check_ids[0] == "default_single_bug_rule"
    assert "same_module" in check_ids
    assert "same_root_cause_class" in check_ids
    assert "same_fix_strategy" in check_ids
    assert "same_verification_surface" in check_ids
    assert "same_release_window" in check_ids
    assert "exception_approval_record" in check_ids
    assert "rollback_strategy_defined" in check_ids
