from pathlib import Path


def test_integration_threshold_rules_define_quantified_completion():
    spec_path = Path("spec-global/departments/dev/docs/integration-threshold-rules.md")
    assert spec_path.exists(), "Integration threshold rules not found"

    content = spec_path.read_text(encoding="utf-8")

    assert "100%" in content
    assert ">=95%" in content
    assert ">=80%" in content
    assert "unresolved structural issue count: `0`" in content
