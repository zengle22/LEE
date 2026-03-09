from pathlib import Path

import yaml

from scripts.lint_l3_templates import validate_template


def test_reverse_epic_feat_template_supports_command_driven_skill_steps() -> None:
    path = Path("spec-global/core/workflows/templates/reverse-epic-feat-l3-template.yaml")

    assert validate_template(path) == []


def test_spec_governance_template_supports_gate_steps() -> None:
    path = Path("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")

    assert validate_template(path) == []


def test_skill_step_with_execution_steps_still_requires_skill_id(tmp_path: Path) -> None:
    template = {
        "kind": "l3_workflow_template",
        "version": "1.0",
        "id": "template.test.invalid_command_steps",
        "name": "Invalid Command Steps",
        "stages": [
            {
                "id": "build",
                "name": "Build",
                "kind": "stage",
                "steps": [
                    {
                        "id": "cmd_step",
                        "name": "Command Step",
                        "kind": "skill",
                        "mandatory": True,
                        "depends_on": [],
                        "config": {
                            "execution": {
                                "steps": [
                                    {"command": "echo hello"},
                                ]
                            }
                        },
                    }
                ],
            }
        ],
    }
    path = tmp_path / "invalid-template.yaml"
    path.write_text(yaml.safe_dump(template, allow_unicode=True), encoding="utf-8")

    errors = validate_template(path)

    assert any("skill_id" in error for error in errors)
