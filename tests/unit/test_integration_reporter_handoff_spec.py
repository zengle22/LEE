from pathlib import Path


def test_integration_reporter_handoff_spec_declares_four_required_refs():
    spec_path = Path("spec-global/departments/dev/docs/integration-reporter-handoff-spec.md")
    assert spec_path.exists(), "Integration reporter handoff spec not found"

    content = spec_path.read_text(encoding="utf-8")

    assert "integration_report_ref" in content
    assert "integration_test_result_ref" in content
    assert "issue_resolution_ref" in content
    assert "structural_issue_ref" in content
    assert "unresolved structural issue count is `0`" in content
