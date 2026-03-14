from pathlib import Path

import yaml


def test_bugfix_granularity_control_spec_freezes_default_rule_and_five_same():
    spec_path = Path("spec-global/departments/dev/governance/bugfix-granularity-control-spec.yaml")
    assert spec_path.exists(), "Bugfix granularity control spec not found"

    with open(spec_path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    assert data["status"] == "frozen"
    assert data["default_rule"]["statement"] == "1 bug -> 1 bugfix workflow instance"
    dimensions = [item["id"] for item in data["five_same_rule"]["dimensions"]]
    assert dimensions == [
        "same_module",
        "same_root_cause_class",
        "same_fix_strategy",
        "same_verification_surface",
        "same_release_window",
    ]
