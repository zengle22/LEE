"""
HandoverManager Tests
"""

from pathlib import Path
import pytest

from lee.orchestrator.execution.artifacts import (
    HandoverManager,
    ArtifactManager,
    ManifestManager,
    ArtifactType,
    ArtifactStatus,
)


@pytest.fixture
def temp_artifacts_dir(tmp_path):
    """Create temporary artifacts directory"""
    artifacts_dir = tmp_path / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    return artifacts_dir


@pytest.fixture
def sample_artifacts(temp_artifacts_dir):
    """Create sample artifacts for testing"""
    artifacts = []

    # Create a manifest first
    manager = ArtifactManager(temp_artifacts_dir)
    manifest_manager = ManifestManager(temp_artifacts_dir, manager.registry)

    run_id = "TEST-RUN-001"
    department = "engineering"

    manifest = manifest_manager.create(
        run_id=run_id,
        workflow_id="test-workflow",
        department=department,
    )

    # Create sample artifacts (use valid categories for DOCUMENT type)
    valid_categories = ["readme", "usage_guide", "investigation_report"]
    for i in range(3):
        artifact = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category=valid_categories[i],
            content=f"Test content {i}",
            run_id=run_id,
            title=f"Test Artifact {i}",
            description=f"Test artifact description {i}",
            department=department,
            tags=["test"],
        )
        artifacts.append(artifact)
        manifest_manager.add_artifact(run_id, artifact, department)

    return {
        "artifacts": artifacts,
        "run_id": run_id,
        "department": department,
        "manager": manager,
        "manifest_manager": manifest_manager,
    }


@pytest.fixture
def handover_manager(sample_artifacts, temp_artifacts_dir):
    """Create HandoverManager instance with shared manager"""
    return HandoverManager(
        project_root=temp_artifacts_dir.parent,
        artifacts_root=temp_artifacts_dir,
        manager=sample_artifacts["manager"],
    )


class TestHandoverManager:
    """HandoverManager test suite"""

    def test_init(self, handover_manager):
        """Test initialization"""
        assert handover_manager.artifacts_root.name == "artifacts"
        assert handover_manager.manager is not None
        assert handover_manager.manifest_manager is not None

    def test_create_handover(self, handover_manager, sample_artifacts):
        """Test creating a handover"""
        artifacts = sample_artifacts["artifacts"]
        from_run_id = sample_artifacts["run_id"]
        from_department = sample_artifacts["department"]

        artifact_ids = [a.id for a in artifacts]

        manifest = handover_manager.create_handover(
            from_run_id=from_run_id,
            to_department="qa",
            artifact_ids=artifact_ids,
            handover_title="Test Handover",
            handover_description="This is a test handover",
            from_department=from_department,
        )

        assert manifest is not None
        assert manifest.handover_to == "qa"
        assert set(manifest.handover_artifacts) == set(artifact_ids)

        # Check that artifacts were updated with consumed_by
        for artifact_id in artifact_ids:
            artifact = handover_manager.manager.get(artifact_id)
            assert "qa" in artifact.consumed_by

        # Check that handover artifact was created
        handovers = handover_manager.manager.registry.get_by_type("HANDOVER")
        assert len(handovers) > 0

    def test_create_handover_with_invalid_artifacts(self, handover_manager, sample_artifacts):
        """Test creating handover with some invalid artifact IDs"""
        from_run_id = sample_artifacts["run_id"]
        from_department = sample_artifacts["department"]
        valid_artifact = sample_artifacts["artifacts"][0]

        # Mix valid and invalid IDs
        artifact_ids = [valid_artifact.id, "ART-INVALID", "ART-ALSO-INVALID"]

        manifest = handover_manager.create_handover(
            from_run_id=from_run_id,
            to_department="qa",
            artifact_ids=artifact_ids,
            handover_title="Test Handover",
            from_department=from_department,
        )

        # Should succeed with only valid artifacts
        assert manifest is not None
        assert len(manifest.handover_artifacts) == 1

    def test_create_handover_all_invalid(self, handover_manager):
        """Test creating handover with all invalid artifact IDs"""
        # Use the existing run_id but with invalid artifact IDs
        with pytest.raises(ValueError, match="No valid artifacts"):
            handover_manager.create_handover(
                from_run_id="TEST-RUN-001",
                to_department="qa",
                artifact_ids=["ART-INVALID-1", "ART-INVALID-2"],
                handover_title="Test Handover",
                from_department="engineering",
            )

    def test_consume_handover(self, handover_manager, sample_artifacts):
        """Test consuming a handover"""
        # First create a handover
        artifacts = sample_artifacts["artifacts"]
        from_run_id = sample_artifacts["run_id"]
        from_department = sample_artifacts["department"]

        artifact_ids = [a.id for a in artifacts]

        handover_manager.create_handover(
            from_run_id=from_run_id,
            to_department="qa",
            artifact_ids=artifact_ids,
            handover_title="Test Handover",
            from_department=from_department,
        )

        # Get the handover artifact
        handovers = handover_manager.manager.registry.get_by_type("HANDOVER")
        handover_id = handovers[0].id

        # Consume the handover
        to_run_id = "QA-RUN-001"
        to_department = "qa"

        consumed = handover_manager.consume_handover(
            handover_artifact_id=handover_id,
            to_run_id=to_run_id,
            to_department=to_department,
        )

        assert len(consumed) == len(artifacts)

        # Check that run_id was added to consumed_by
        for artifact in consumed:
            assert to_run_id in artifact.consumed_by

    def test_consume_handover_invalid_id(self, handover_manager):
        """Test consuming handover with invalid ID"""
        with pytest.raises(ValueError, match="Handover artifact not found"):
            handover_manager.consume_handover(
                handover_artifact_id="ART-INVALID",
                to_run_id="SOME-RUN",
                to_department="qa",
            )

    def test_get_pending_handovers(self, handover_manager, sample_artifacts):
        """Test getting pending handovers"""
        # Create a handover
        artifacts = sample_artifacts["artifacts"]
        from_run_id = sample_artifacts["run_id"]
        from_department = sample_artifacts["department"]

        artifact_ids = [a.id for a in artifacts]

        handover_manager.create_handover(
            from_run_id=from_run_id,
            to_department="qa",
            artifact_ids=artifact_ids,
            handover_title="Test Handover",
            from_department=from_department,
        )

        # Get pending handovers for qa department
        pending = handover_manager.get_pending_handovers("qa")

        assert len(pending) == 1
        assert pending[0]["source_run_id"] == from_run_id
        assert pending[0]["source_department"] == from_department
        assert pending[0]["handover_artifact"] is not None

    def test_get_pending_handovers_empty(self, handover_manager):
        """Test getting pending handovers when none exist"""
        pending = handover_manager.get_pending_handovers("nonexistent")
        assert len(pending) == 0

    def test_transfer_artifact(self, handover_manager, sample_artifacts):
        """Test transferring an artifact to another department"""
        artifact = sample_artifacts["artifacts"][0]

        updated = handover_manager.transfer_artifact(
            artifact_id=artifact.id,
            to_department="qa",
            transfer_reason="Transfer for testing",
        )

        assert "qa" in updated.consumed_by
        assert "transfers" in updated.properties
        assert len(updated.properties["transfers"]) == 1
        assert updated.properties["transfers"][0]["to_department"] == "qa"
        assert updated.properties["transfers"][0]["reason"] == "Transfer for testing"

    def test_transfer_artifact_multiple_times(self, handover_manager, sample_artifacts):
        """Test transferring artifact multiple times"""
        artifact = sample_artifacts["artifacts"][0]

        # First transfer
        handover_manager.transfer_artifact(
            artifact_id=artifact.id,
            to_department="qa",
            transfer_reason="First transfer",
        )

        # Second transfer
        handover_manager.transfer_artifact(
            artifact_id=artifact.id,
            to_department="operations",
            transfer_reason="Second transfer",
        )

        updated = handover_manager.manager.get(artifact.id)
        assert "qa" in updated.consumed_by
        assert "operations" in updated.consumed_by
        assert len(updated.properties["transfers"]) == 2

    def test_transfer_artifact_invalid_id(self, handover_manager):
        """Test transferring with invalid artifact ID"""
        with pytest.raises(ValueError, match="Artifact not found"):
            handover_manager.transfer_artifact(
                artifact_id="ART-INVALID",
                to_department="qa",
            )

    def test_get_department_summary(self, handover_manager, sample_artifacts):
        """Test getting department summary"""
        department = sample_artifacts["department"]

        summary = handover_manager.get_department_summary(department)

        assert summary["department"] == department
        assert summary["total_artifacts"] >= 3  # At least our sample artifacts
        assert "DOCUMENT" in summary["by_type"]
        assert "pending_handovers" in summary
        assert summary["total_size_bytes"] >= 0

    def test_get_department_summary_with_pending_handovers(self, handover_manager, sample_artifacts):
        """Test department summary includes pending handovers"""
        artifacts = sample_artifacts["artifacts"]
        from_run_id = sample_artifacts["run_id"]
        from_department = sample_artifacts["department"]

        # Create a handover to qa
        handover_manager.create_handover(
            from_run_id=from_run_id,
            to_department="qa",
            artifact_ids=[a.id for a in artifacts],
            handover_title="Test Handover",
            from_department=from_department,
        )

        # Get summary for qa (should show pending handover)
        qa_summary = handover_manager.get_department_summary("qa")

        assert qa_summary["pending_handovers"] == 1
        assert len(qa_summary["pending_handover_details"]) == 1
        assert qa_summary["pending_handover_details"][0]["from_run"] == from_run_id

    def test_format_handover_content(self, handover_manager, sample_artifacts):
        """Test handover content formatting"""
        artifacts = sample_artifacts["artifacts"]
        from_run_id = sample_artifacts["run_id"]

        content = handover_manager._format_handover_content(
            from_run_id=from_run_id,
            to_department="qa",
            artifacts=artifacts,
            title="Test Handover",
            description="Test description",
        )

        assert "Test Handover" in content
        assert from_run_id in content
        assert "qa" in content
        assert "Test description" in content
        assert "## Artifacts" in content

    def test_parse_handover_content(self, handover_manager, sample_artifacts):
        """Test parsing artifact IDs from handover content"""
        artifacts = sample_artifacts["artifacts"]
        from_run_id = sample_artifacts["run_id"]

        content = handover_manager._format_handover_content(
            from_run_id=from_run_id,
            to_department="qa",
            artifacts=artifacts,
            title="Test Handover",
            description="Test description",
        )

        # Create a real handover artifact in the manager
        handover = handover_manager.manager.create(
            artifact_type=ArtifactType.HANDOVER,
            category="to_qa",
            content=content,
            run_id=from_run_id,
            title="Test Handover",
            department=sample_artifacts["department"],
        )

        # Parse artifact IDs
        parsed_ids = handover_manager._parse_handover_content(handover)

        assert len(parsed_ids) == len(artifacts)
        for artifact in artifacts:
            assert artifact.id in parsed_ids

    def test_parse_handover_content_empty(self, handover_manager):
        """Test parsing handover with no content"""
        # Create a handover with empty content
        from lee.orchestrator.execution.artifacts.models import ArtifactMetadata
        handover = ArtifactMetadata(
            id="HANDOVER-001",
            type=ArtifactType.HANDOVER,
            category="to_qa",
            status=ArtifactStatus.ACTIVE,
            run_id="TEST-RUN",
            title="Empty Handover",
            department="engineering",
            path="active/engineering/TEST-RUN/artifacts/HANDOVER-001.md",
        )

        # When artifact doesn't exist in manager, get_content returns None
        parsed = handover_manager._parse_handover_content(handover)
        assert parsed == []
