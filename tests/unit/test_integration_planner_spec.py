from pathlib import Path


def test_integration_planner_and_verifier_spec_declares_dual_modes_and_thresholds():
    spec_path = Path("spec-global/departments/dev/docs/integration-planner-and-verifier-spec.md")
    assert spec_path.exists(), "Integration planner/verifier spec not found"

    content = spec_path.read_text(encoding="utf-8")

    assert "contract_mock_mode" in content
    assert "environment_backed_mode" in content
    assert "100%" in content
    assert ">=95%" in content
    assert ">=80%" in content
    assert "integration_matrix_ref" in content
