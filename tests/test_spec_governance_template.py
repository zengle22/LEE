from pathlib import Path

import yaml

from lee.orchestrator.execution.template_manager import TemplateManager


def test_spec_governance_template_is_valid_yaml() -> None:
    path = Path("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    assert data["kind"] == "l3_workflow_template"
    assert data["id"] == "template.core.spec_governance"
    assert data["supported_spec_kinds"] == ["agent", "workflow", "contract"]
    assert [stage["id"] for stage in data["stages"]] == [
        "spec_maintenance",
        "spec_review",
        "review_gate",
        "final_output",
    ]


def test_spec_governance_template_routes_supported_maintainers() -> None:
    path = Path("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    route_map = data["maintainer_route_map"]
    assert route_map["agent"] == "agent.governance.spec_maintainer"
    assert route_map["workflow"] == "agent.governance.workflow_spec_maintainer"
    assert route_map["contract"] == "agent.governance.contracts_spec_maintainer"

    review_step = data["stages"][1]["steps"][0]
    assert review_step["agent_id"] == "agent.review.spec_review"

    gate_step = data["stages"][2]["steps"][0]
    assert gate_step["kind"] == "gate"
    assert gate_step["config"]["gate"]["type"] == "auto_check"
    assert "blocker_count == 0" in gate_step["config"]["gate"]["check"]
    assert gate_step["config"]["gate"]["on_fail"]["action"] == "{{ 'human_gate' if params.human_gate_required | default(true) else 'fail_step' }}"
    assert gate_step["config"]["gate"]["on_revise"]["target_step"] == "spec_maintenance"


def test_spec_governance_template_preserves_gate_config_when_parsed() -> None:
    manager = TemplateManager(template_dir="spec-global")
    template = manager.get_template("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")

    assert template is not None
    gate_step = next(step for step in template.steps if step.id == "review_gate")
    assert gate_step.config["gate"]["type"] == "auto_check"
    assert "blocker_count == 0" in gate_step.config["gate"]["check"]
    assert gate_step.config["gate"]["on_revise"]["target_step"] == "spec_maintenance"


def test_spec_governance_template_enables_spec_writeback() -> None:
    path = Path("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))

    maintenance_step = data["stages"][0]["steps"][0]
    assert maintenance_step["config"]["spec_writeback"]["enabled"] is True
    assert maintenance_step["config"]["spec_writeback"]["diff_report_path"].endswith("-spec.diff")
    assert any(
        item["path"] == "{{ params.target_path | default('') }}"
        for item in maintenance_step["outputs"]
        if isinstance(item, dict)
    )

    review_inputs = data["stages"][1]["steps"][0]["inputs"]["context_files"]
    assert any(item["path"] == "{{ params.target_path | default('') }}" for item in review_inputs)
    assert any(item["path"].endswith("-spec.diff") for item in review_inputs)
