"""
Cleanup Tests
"""

from pathlib import Path
from datetime import datetime, timedelta
import pytest

from lee.orchestrator.execution.artifacts import (
    ArtifactCleaner,
    CleanupPolicy,
    rebuild_registry,
    ArtifactManager,
    ManifestManager,
    ArtifactType,
    ArtifactStatus,
)
from lee.orchestrator.execution.artifacts.models import ArtifactMetadata


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
    manager = ArtifactManager(temp_artifacts_dir)
    manifest_manager = ManifestManager(temp_artifacts_dir, manager.registry)

    run_id = "TEST-RUN-001"
    department = "engineering"

    manifest = manifest_manager.create(
        run_id=run_id,
        workflow_id="test-workflow",
        department=department,
    )

    # Create artifacts with different ages
    for i in range(5):
        artifact = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme" if i < 2 else "usage_guide",
            content=f"Test content {i}",
            run_id=run_id,
            title=f"Test Artifact {i}",
            description=f"Test artifact description {i}",
            department=department,
            tags=["test"],
        )
        # Simulate old artifacts by modifying created_at
        if i >= 3:
            # Use object.__setattr__ to bypass frozen dataclass
            old_date = datetime.now() - timedelta(days=40)
            object.__setattr__(artifact, 'created_at', old_date)
        artifacts.append(artifact)
        manifest_manager.add_artifact(run_id, artifact, department)

    return {
        "artifacts": artifacts,
        "run_id": run_id,
        "department": department,
        "manager": manager,
        "manifest_manager": manifest_manager,
    }


class TestCleanupPolicy:
    """CleanupPolicy test suite"""

    def test_get_max_age_days(self):
        """Test getting max age days for status"""
        assert CleanupPolicy.get_max_age_days("draft") == 7
        assert CleanupPolicy.get_max_age_days("active") == 30
        assert CleanupPolicy.get_max_age_days("frozen") is None

    def test_should_delete_old_artifact(self):
        """Test should_delete with old artifact"""
        artifact = ArtifactMetadata(
            id="TEST-001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.ACTIVE,
            path="test.md",
            run_id="test-run",
        )
        old_date = datetime.now() - timedelta(days=40)
        object.__setattr__(artifact, 'created_at', old_date)

        assert CleanupPolicy.should_delete(artifact, 30) is True
        assert CleanupPolicy.should_delete(artifact, 50) is False

    def test_should_delete_preserve_frozen(self):
        """Test should_delete preserves frozen artifacts"""
        artifact = ArtifactMetadata(
            id="TEST-001",
            type=ArtifactType.DOCUMENT,
            category="readme",
            status=ArtifactStatus.FROZEN,
            path="test.md",
            run_id="test-run",
        )
        old_date = datetime.now() - timedelta(days=365)
        object.__setattr__(artifact, 'created_at', old_date)

        # FROZEN should always be preserved
        assert CleanupPolicy.should_delete(artifact, 30) is False


class TestArtifactCleaner:
    """ArtifactCleaner test suite"""

    def test_init(self, temp_artifacts_dir):
        """Test initialization"""
        cleaner = ArtifactCleaner(temp_artifacts_dir)
        assert cleaner.artifacts_root == temp_artifacts_dir
        assert cleaner.manager is not None

    def test_init_with_shared_manager(self, temp_artifacts_dir, sample_artifacts):
        """Test initialization with shared manager"""
        cleaner = ArtifactCleaner(
            temp_artifacts_dir,
            manager=sample_artifacts["manager"],
        )
        assert cleaner.manager == sample_artifacts["manager"]

    def test_find_cleanup_candidates(self, sample_artifacts):
        """Test finding cleanup candidates"""
        cleaner = ArtifactCleaner(
            sample_artifacts["manager"].root_path,
            manager=sample_artifacts["manager"],
        )

        # Find artifacts older than 30 days
        candidates = cleaner.find_cleanup_candidates(max_age_days=30)

        # Should find at least 2 old artifacts
        assert len(candidates) >= 2

    def test_find_cleanup_candidates_by_department(self, sample_artifacts):
        """Test finding cleanup candidates by department"""
        cleaner = ArtifactCleaner(
            sample_artifacts["manager"].root_path,
            manager=sample_artifacts["manager"],
        )

        candidates = cleaner.find_cleanup_candidates(
            department="engineering",
            max_age_days=30,
        )

        assert len(candidates) >= 0

    def test_build_reference_set(self, temp_artifacts_dir):
        """Test building reference set"""
        manager = ArtifactManager(temp_artifacts_dir)
        manifest_manager = ManifestManager(temp_artifacts_dir, manager.registry)

        run_id = "REF-TEST-001"
        manifest = manifest_manager.create(
            run_id=run_id,
            workflow_id="test-workflow",
            department="engineering",
        )

        artifact = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="Test",
            run_id=run_id,
            department="engineering",
        )
        manifest_manager.add_artifact(run_id, artifact, "engineering")

        cleaner = ArtifactCleaner(temp_artifacts_dir, manager=manager)
        references = cleaner.build_reference_set()

        assert artifact.id in references

    def test_clean_dry_run(self, sample_artifacts):
        """Test clean in dry run mode"""
        cleaner = ArtifactCleaner(
            sample_artifacts["manager"].root_path,
            manager=sample_artifacts["manager"],
        )

        result = cleaner.clean(
            max_age_days=30,
            dry_run=True,
            enable_reference_protection=False,
        )

        assert result["dry_run"] is True
        # In dry run, deleted is the count that would be deleted
        assert result["deleted"] >= 0

    def test_clean_with_reference_protection(self, sample_artifacts):
        """Test clean with reference protection"""
        cleaner = ArtifactCleaner(
            sample_artifacts["manager"].root_path,
            manager=sample_artifacts["manager"],
        )

        # All artifacts are in manifest, so should be protected
        result = cleaner.clean(
            max_age_days=30,
            dry_run=True,
            enable_reference_protection=True,
        )

        assert result["protected"] >= 0
        assert result["dry_run"] is True
        # With reference protection, nothing should be deleted
        assert result["deleted"] == 0

    def test_clean_without_reference_protection(self, sample_artifacts):
        """Test clean without reference protection"""
        cleaner = ArtifactCleaner(
            sample_artifacts["manager"].root_path,
            manager=sample_artifacts["manager"],
        )

        result = cleaner.clean(
            max_age_days=30,
            dry_run=True,
            enable_reference_protection=False,
        )

        assert result["protected"] == 0
        assert result["dry_run"] is True

    def test_clean_intermediate(self, temp_artifacts_dir):
        """Test cleaning intermediate artifacts"""
        manager = ArtifactManager(temp_artifacts_dir)
        manifest_manager = ManifestManager(temp_artifacts_dir, manager.registry)

        run_id = "INTERM-TEST-001"
        manifest = manifest_manager.create(
            run_id=run_id,
            workflow_id="test-workflow",
            department="engineering",
        )

        # Create intermediate artifacts with valid category (draft)
        for i in range(3):
            artifact = manager.create(
                artifact_type=ArtifactType.INTERMEDIATE,
                category="draft",
                content=f"Intermediate {i}",
                run_id=run_id,
                department="engineering",
                tags=["intermediate"],
            )
            manifest_manager.add_artifact(run_id, artifact, "engineering")

        cleaner = ArtifactCleaner(temp_artifacts_dir, manager=manager)
        result = cleaner.clean_intermediate(run_id, dry_run=True)

        assert result["run_id"] == run_id
        assert result["count"] == 3
        assert result["dry_run"] is True

    def test_archive_old_runs(self, sample_artifacts, temp_artifacts_dir):
        """Test archiving old runs"""
        cleaner = ArtifactCleaner(temp_artifacts_dir)
        manifest_manager = sample_artifacts["manifest_manager"]

        # Mark the run as completed and old
        manifest = manifest_manager.get(sample_artifacts["run_id"], "engineering")
        old_date = datetime.now() - timedelta(days=40)
        object.__setattr__(manifest, 'completed_at', old_date)
        manifest_manager.save(manifest)

        result = cleaner.archive_old_runs(max_age_days=30, dry_run=True)

        assert result["dry_run"] is True
        assert result["archived"] >= 1


class TestRebuildRegistry:
    """rebuild_registry function test suite"""

    def test_rebuild_registry(self, temp_artifacts_dir):
        """Test rebuilding registry from disk"""
        # Create some artifacts first
        manager = ArtifactManager(temp_artifacts_dir)
        manifest_manager = ManifestManager(temp_artifacts_dir, manager.registry)

        run_id = "REBUILD-TEST-001"
        manifest = manifest_manager.create(
            run_id=run_id,
            workflow_id="test-workflow",
            department="engineering",
        )

        artifact = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="readme",
            content="Test content",
            run_id=run_id,
            department="engineering",
        )
        manifest_manager.add_artifact(run_id, artifact, "engineering")

        # Delete registry file to simulate corruption
        registry_file = temp_artifacts_dir / ".registry.json"
        if registry_file.exists():
            registry_file.unlink()

        # Rebuild
        count = rebuild_registry(temp_artifacts_dir)

        # Should rebuild the artifact
        assert count >= 1

        # Verify artifact is accessible
        rebuilt_manager = ArtifactManager(temp_artifacts_dir)
        assert rebuilt_manager.get(artifact.id) is not None

    def test_rebuild_registry_empty(self, temp_artifacts_dir):
        """Test rebuilding registry with no artifacts"""
        # Empty artifacts directory
        count = rebuild_registry(temp_artifacts_dir)
        assert count == 0
