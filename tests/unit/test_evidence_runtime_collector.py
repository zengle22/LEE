from pathlib import Path

from lee.evidence.collector import EvidenceCollector


def test_evidence_collector_dedupes_and_writes_manifest(tmp_path):
    project_root = tmp_path
    artifact = project_root / "artifact.txt"
    artifact.write_text("evidence", encoding="utf-8")

    collector = EvidenceCollector(str(project_root))
    copied = collector.collect_from_context(
        run_id="RUN-TEST-001",
        step_id="collect_evidence",
        artifact_refs=[str(artifact), str(artifact)],
        filesystem_paths=[],
        workflow_context_refs=[],
    )

    assert len(copied) == 1
    manifest = collector.manifest_entries("RUN-TEST-001")
    assert len(manifest) == 1
    assert manifest[0]["step_id"] == "collect_evidence"
    assert len(manifest[0]["artifacts"]) == 1
