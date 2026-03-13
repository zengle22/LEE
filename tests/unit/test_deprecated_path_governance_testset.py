from pathlib import Path


def test_deprecated_path_governance_testset_covers_all_acceptance_targets():
    testset_path = Path("spec/testing/testsets/TESTSET-FEAT-SRC-009-010-001__deprecated-path-governance-testset.md")
    assert testset_path.exists(), "Deprecated path governance TestSet not found"

    content = testset_path.read_text(encoding="utf-8")

    assert "TC-DEP-001" in content
    assert "TC-DEP-002" in content
    assert "TC-DEP-003" in content
    assert "TC-DEP-004" in content
