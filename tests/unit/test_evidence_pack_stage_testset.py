from pathlib import Path


def test_evidence_pack_stage_testset_covers_schema_runtime_and_handoff():
    testset_path = Path("spec/testing/testsets/TESTSET-FEAT-SRC-009-009-001__evidence-pack-stage-testset.md")
    assert testset_path.exists(), "Evidence pack stage TestSet not found"

    content = testset_path.read_text(encoding="utf-8")

    assert "TC-EVI-001" in content
    assert "TC-EVI-002" in content
    assert "TC-EVI-003" in content
    assert "TC-EVI-004" in content
    assert "src/lee/evidence/collector.py" in content
    assert "src/lee/evidence/validator.py" in content
    assert "src/lee/evidence/coverage_auditor.py" in content
