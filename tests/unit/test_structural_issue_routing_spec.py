from pathlib import Path


def test_structural_issue_routing_spec_declares_four_classes_and_escalation():
    spec_path = Path("spec-global/departments/dev/docs/structural-issue-routing-spec.md")
    assert spec_path.exists(), "Structural issue routing spec not found"

    content = spec_path.read_text(encoding="utf-8")

    assert "structural_contract" in content
    assert "structural_tech" in content
    assert "structural_feat" in content
    assert "impl_bug" in content
    assert "three consecutive times" in content
    assert "rollback_target" in content
