from pathlib import Path

from lee.evidence.coverage_auditor import CoverageAuditor
from lee.evidence.validator import EvidenceValidator


def test_evidence_validator_accepts_minimal_payload():
    schema_path = Path("spec-global/departments/dev/contracts/evidence-pack/v1/schema.json")
    validator = EvidenceValidator(str(schema_path))
    payload = {
        "formal_ssot_id": "FEAT-SRC-009-001",
        "source_refs": ["FEAT-SRC-009-001#delivery"],
        "governing_adrs": ["ADR-008"],
        "delivery_outputs": [
            {"artifact_id": "ART-001", "artifact_type": "integration", "ref": "REPORT-001"},
        ],
        "verification_results": [
            {"result_type": "integration_report", "status": "passed", "ref": "REPORT-001"},
        ],
        "evidence_types": [
            "code_diff",
            "test_report",
            "review_record",
            "deployment_record",
            "integration_report",
        ],
    }

    errors = validator.validate(payload)
    assert errors == []


def test_coverage_auditor_reports_uncovered_acceptance_items():
    trace_matrix = CoverageAuditor.build_trace_matrix(
        ["AC-1", "AC-2"],
        {"AC-1": ["EVI-1"]},
    )

    assert CoverageAuditor.find_gaps(trace_matrix) == ["AC-2"]
