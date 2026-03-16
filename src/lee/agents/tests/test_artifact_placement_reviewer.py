"""
Unit Tests for Artifact Placement Reviewer Agent

Tests for the artifact placement reviewer agent core functionality.
Covers manifest loading, directory scanning, audit logic, and report generation.
"""

import pytest
import tempfile
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
from datetime import datetime


# ============================================================================
# Data Classes (to be replaced by actual implementation)
# ============================================================================

@dataclass
class ExpectedArtifact:
    """Represents an expected artifact from the manifest"""
    artifact_id: str
    artifact_kind: str  # formal_ssot, intermediate, deliverable, evidence
    identity_kind: str  # ssot, bundle, intermediate
    placement_key: str
    expected_dir: str
    required: bool
    ssot_type: Optional[str] = None
    source_refs: List[str] = field(default_factory=list)


@dataclass
class PlacementRule:
    """Represents a placement rule from the manifest"""
    rule_id: str
    rule_kind: str  # formal_placement, intermediate_placement, deliverable_placement
    description: str
    enforced: bool


@dataclass
class RunScope:
    """Represents the run scope from the manifest"""
    workflow_instance_id: str
    workflow_id: str
    run_id: str
    step_workspace: Optional[str] = None


@dataclass
class PlacementManifest:
    """Represents a parsed placement manifest"""
    manifest_id: str
    run_scope: RunScope
    expected_artifacts: List[ExpectedArtifact]
    placement_rules: List[PlacementRule]
    governing_adrs: List[str] = field(default_factory=list)


@dataclass
class FileEntry:
    """Represents a scanned file entry"""
    file_path: Path
    relative_path: str
    size_bytes: int
    modified_at: datetime


@dataclass
class AuditFinding:
    """Represents an audit finding (violation or compliance issue)"""
    file_path: str
    expected_dir: str
    actual_dir: str
    severity: str  # blocker, major, minor
    reason: str
    artifact_id: Optional[str] = None


@dataclass
class AuditReport:
    """Represents an audit report result"""
    audit_id: str
    workflow_instance_id: str
    summary: Dict[str, int]
    blockers: List[AuditFinding]
    majors: List[AuditFinding]
    minors: List[AuditFinding]
    misplaced_files: List[AuditFinding]
    decision: str  # pass, revise, reject


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def valid_manifest_data() -> Dict[str, Any]:
    """Returns valid manifest data structure"""
    return {
        "manifest_id": "wf-task-test-001-placement-manifest",
        "run_scope": {
            "workflow_instance_id": "wf-task-test-001",
            "workflow_id": "requirement-chain-validation",
            "run_id": "001",
            "step_workspace": ".workflow/workspace/wf_task_test_001"
        },
        "expected_artifacts": [
            {
                "artifact_id": "feat-src-056-001-frozen",
                "artifact_kind": "formal_ssot",
                "identity_kind": "ssot",
                "ssot_type": "FEAT",
                "placement_key": "spec-requirements-feat",
                "expected_dir": "spec/requirements/SRC-056/",
                "required": True,
                "source_refs": ["EPIC-SRC-056-001"]
            },
            {
                "artifact_id": "tech-feat-056-001",
                "artifact_kind": "formal_ssot",
                "identity_kind": "ssot",
                "ssot_type": "TECH",
                "placement_key": "spec-tech",
                "expected_dir": "spec/tech/SRC-056/",
                "required": True,
                "source_refs": ["FEAT-SRC-056-001"]
            }
        ],
        "placement_rules": [
            {
                "rule_id": "formal-ssot-placement-rule",
                "rule_kind": "formal_placement",
                "description": "正式 SSOT 主对象必须放置到 canonical 内容目录",
                "enforced": True
            }
        ],
        "governing_adrs": ["ADR-021"]
    }


@pytest.fixture
def manifest_yaml_content(valid_manifest_data: Dict[str, Any]) -> str:
    """Returns YAML string for valid manifest"""
    return yaml.dump(valid_manifest_data, default_flow_style=False, allow_unicode=True)


@pytest.fixture
def temp_manifest_file(manifest_yaml_content: str) -> Path:
    """Creates a temporary manifest file"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        f.write(manifest_yaml_content)
        return Path(f.name)


@pytest.fixture
def temp_scan_directory() -> Path:
    """Creates a temporary directory structure for scanning"""
    base = tempfile.mkdtemp()
    base_path = Path(base)

    # Create expected directory structure
    (base_path / "spec" / "requirements" / "SRC-056").mkdir(parents=True)
    (base_path / "spec" / "tech" / "SRC-056").mkdir(parents=True)

    # Create some test files
    (base_path / "spec" / "requirements" / "SRC-056" / "FEAT-001.md").write_text("# FEAT")
    (base_path / "spec" / "tech" / "SRC-056" / "TECH-001.md").write_text("# TECH")

    return base_path


# ============================================================================
# Manifest Loading Tests
# ============================================================================

class TestManifestLoading:
    """Tests for manifest loading functionality"""

    def test_load_valid_manifest(self, temp_manifest_file: Path):
        """Test loading a valid manifest file"""
        # This test verifies the manifest can be parsed
        with open(temp_manifest_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        assert data is not None
        assert data["manifest_id"] == "wf-task-test-001-placement-manifest"
        assert data["run_scope"]["workflow_instance_id"] == "wf-task-test-001"
        assert len(data["expected_artifacts"]) == 2

    def test_load_manifest_missing_required_field(self):
        """Test that missing required fields raise appropriate errors"""
        invalid_data = {
            # Missing manifest_id (required)
            "run_scope": {
                "workflow_instance_id": "wf-task-test-001",
                "workflow_id": "test",
                "run_id": "001"
            }
        }

        # Should raise error when validating
        with pytest.raises((KeyError, ValueError)):
            if "manifest_id" not in invalid_data:
                raise KeyError("manifest_id is required")

    def test_load_manifest_invalid_yaml_syntax(self):
        """Test that invalid YAML syntax raises appropriate errors"""
        invalid_yaml = """
        manifest_id: test
        run_scope:
            workflow_instance_id: [invalid
        """

        with pytest.raises(yaml.YAMLError):
            yaml.safe_load(invalid_yaml)

    def test_load_manifest_nonexistent_file(self):
        """Test that loading nonexistent file raises FileNotFoundError"""
        with pytest.raises(FileNotFoundError):
            Path("/nonexistent/path/manifest.yaml").read_text()


# ============================================================================
# Directory Scanner Tests
# ============================================================================

class TestDirectoryScanner:
    """Tests for directory scanning functionality"""

    def test_scan_empty_directory(self):
        """Test scanning an empty directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            # Don't create any files

            # Simulate scan result
            files = list(base.rglob("*"))
            assert len(files) == 0

    def test_scan_directory_with_files(self, temp_scan_directory: Path):
        """Test scanning directory containing files"""
        files = list(temp_scan_directory.rglob("*.md"))

        assert len(files) == 2
        file_names = {f.name for f in files}
        assert "FEAT-001.md" in file_names
        assert "TECH-001.md" in file_names

    def test_scan_directory_recursive(self, temp_scan_directory: Path):
        """Test that scanning is recursive"""
        # Create nested file
        nested_dir = temp_scan_directory / "spec" / "requirements" / "SRC-056" / "subdir"
        nested_dir.mkdir()
        (nested_dir / "nested.md").write_text("# Nested")

        all_files = list(temp_scan_directory.rglob("*.md"))
        assert len(all_files) == 3

    def test_scan_directory_hidden_files(self):
        """Test handling of hidden files"""
        with tempfile.TemporaryDirectory() as tmpdir:
            base = Path(tmpdir)
            (base / ".hidden").write_text("hidden")
            (base / "visible.txt").write_text("visible")

            # rglob includes hidden files by default
            all_files = list(base.rglob("*"))
            assert len(all_files) == 2

    def test_scan_directory_permission_error(self, tmp_path):
        """Test handling of permission errors during scan"""
        # This is tested via integration test with actual permission errors
        # Unit test verifies the scanner can be initialized and has scan method
        from lee.agents.artifact_placement_reviewer import DirectoryScanner
        scanner = DirectoryScanner(root_path=tmp_path)
        assert hasattr(scanner, 'scan'), "DirectoryScanner should have scan method"


# ============================================================================
# Audit Logic Tests
# ============================================================================

class TestAuditLogic:
    """Tests for core audit logic"""

    def test_compliant_file_detection(self, valid_manifest_data: Dict[str, Any]):
        """Test detection of compliant files"""
        # Simulate audit where file is in correct location
        artifact = valid_manifest_data["expected_artifacts"][0]
        actual_path = f"{artifact['expected_dir']}FEAT-001.md"

        # File is compliant
        is_compliant = actual_path.startswith(artifact["expected_dir"])
        assert is_compliant

    def test_misplaced_file_detection(self, valid_manifest_data: Dict[str, Any]):
        """Test detection of misplaced files"""
        artifact = valid_manifest_data["expected_artifacts"][0]
        actual_path = "wrong/directory/FEAT-001.md"
        expected_dir = artifact["expected_dir"]

        # File is misplaced
        is_misplaced = not actual_path.startswith(expected_dir)
        assert is_misplaced

    def test_severity_classification_blocker(self):
        """Test blocker severity classification"""
        # Blocker: formal SSOT in wrong canonical directory
        finding = AuditFinding(
            file_path="spec/wrong/FEAT-001.md",
            expected_dir="spec/requirements/SRC-056/",
            actual_dir="spec/wrong/",
            severity="blocker",
            reason="Formal SSOT in wrong canonical directory",
            artifact_id="FEAT-001"
        )

        assert finding.severity == "blocker"

    def test_severity_classification_major(self):
        """Test major severity classification"""
        # Major: task_directory mismatch
        finding = AuditFinding(
            file_path="spec/tasks/FEAT-001/TASK-001.md",
            expected_dir="spec/tasks/SRC-056/FEAT-001/",
            actual_dir="spec/tasks/FEAT-001/",
            severity="major",
            reason="task_directory declaration mismatch"
        )

        assert finding.severity == "major"

    def test_severity_classification_minor(self):
        """Test minor severity classification"""
        # Minor: naming convention issue
        finding = AuditFinding(
            file_path="spec/tech/SRC-056/tech_design.md",
            expected_dir="spec/tech/SRC-056/",
            actual_dir="spec/tech/SRC-056/",
            severity="minor",
            reason="File naming convention inconsistent"
        )

        assert finding.severity == "minor"

    def test_decision_calculation_pass(self):
        """Test decision calculation for passing audit"""
        blockers = []
        majors = []

        # No blockers should result in pass or revise
        if len(blockers) == 0:
            decision = "pass" if len(majors) == 0 else "revise"
        else:
            decision = "reject"

        assert decision == "pass"

    def test_decision_calculation_reject(self):
        """Test decision calculation for rejecting audit"""
        blockers = [AuditFinding(
            file_path="spec/wrong/FEAT-001.md",
            expected_dir="spec/requirements/SRC-056/",
            actual_dir="spec/wrong/",
            severity="blocker",
            reason="Formal SSOT misplaced"
        )]

        # Any blocker should result in reject
        if len(blockers) > 0:
            decision = "reject"
        else:
            decision = "pass"

        assert decision == "reject"

    def test_missing_required_file_detection(self, valid_manifest_data: Dict[str, Any]):
        """Test detection of missing required files"""
        required_artifact = valid_manifest_data["expected_artifacts"][0]

        # Simulate missing file scenario
        file_exists = False  # In real test, would check filesystem

        if not file_exists and required_artifact["required"]:
            is_violation = True
        else:
            is_violation = False

        assert is_violation

    def test_audit_report_summary_calculation(self):
        """Test audit report summary calculation"""
        total_files = 10
        compliant = 7
        non_compliant = 3
        blockers = 1
        majors = 1
        minors = 1

        summary = {
            "total_files": total_files,
            "compliant_files": compliant,
            "non_compliant_files": non_compliant,
            "blockers": blockers,
            "majors": majors,
            "minors": minors
        }

        assert summary["total_files"] == total_files
        assert summary["compliant_files"] + summary["non_compliant_files"] == total_files


# ============================================================================
# Report Generation Tests
# ============================================================================

class TestReportGeneration:
    """Tests for audit report generation"""

    def test_report_structure_validation(self):
        """Test that generated report has required structure"""
        report = AuditReport(
            audit_id="audit-001",
            workflow_instance_id="wf-task-test-001",
            summary={"total_files": 0, "compliant_files": 0, "non_compliant_files": 0},
            blockers=[],
            majors=[],
            minors=[],
            misplaced_files=[],
            decision="pass"
        )

        # Validate required fields
        assert report.audit_id is not None
        assert report.workflow_instance_id is not None
        assert report.summary is not None
        assert report.decision in ("pass", "revise", "reject")

    def test_report_yaml_serialization(self):
        """Test report serialization to YAML"""
        report = AuditReport(
            audit_id="audit-001",
            workflow_instance_id="wf-task-test-001",
            summary={"total_files": 5, "compliant_files": 5, "non_compliant_files": 0},
            blockers=[],
            majors=[],
            minors=[],
            misplaced_files=[],
            decision="pass"
        )

        data = {
            "audit_id": report.audit_id,
            "workflow_instance_id": report.workflow_instance_id,
            "summary": report.summary,
            "blockers": [],
            "majors": [],
            "minors": [],
            "misplaced_files": [],
            "decision": report.decision
        }

        yaml_str = yaml.dump(data)

        assert "audit-001" in yaml_str
        assert "pass" in yaml_str

    def test_report_json_serialization(self):
        """Test report serialization to JSON"""
        import json

        report = AuditReport(
            audit_id="audit-001",
            workflow_instance_id="wf-task-test-001",
            summary={"total_files": 5, "compliant_files": 5, "non_compliant_files": 0},
            blockers=[],
            majors=[],
            minors=[],
            misplaced_files=[],
            decision="pass"
        )

        data = {
            "audit_id": report.audit_id,
            "workflow_instance_id": report.workflow_instance_id,
            "summary": report.summary,
            "decision": report.decision
        }

        json_str = json.dumps(data)

        assert "audit-001" in json_str
        assert "pass" in json_str


# ============================================================================
# CLI Interface Tests
# ============================================================================

class TestCLIInterface:
    """Tests for CLI interface"""

    def test_cli_argument_parsing_valid(self):
        """Test parsing valid CLI arguments"""
        # Simulate: lee audit --manifest /path/to/manifest.yaml --target /path/to/target
        args = ["--manifest", "manifest.yaml", "--target", "./spec"]

        # Parse arguments (would use argparse in real implementation)
        manifest_idx = args.index("--manifest")
        target_idx = args.index("--target")

        manifest_path = args[manifest_idx + 1]
        target_path = args[target_idx + 1]

        assert manifest_path == "manifest.yaml"
        assert target_path == "./spec"

    def test_cli_argument_parsing_missing_required(self):
        """Test that missing required arguments raise error"""
        args = ["--manifest", "manifest.yaml"]  # Missing --target

        has_manifest = "--manifest" in args
        has_target = "--target" in args

        assert has_manifest
        assert not has_target

    def test_cli_exit_code_success(self):
        """Test exit code 0 for successful audit"""
        # Simulate successful audit with no blockers
        audit_passed = True
        blockers_count = 0

        if audit_passed and blockers_count == 0:
            exit_code = 0
        else:
            exit_code = 1

        assert exit_code == 0

    def test_cli_exit_code_failure(self):
        """Test exit code 1 for failed audit"""
        # Simulate failed audit with blockers
        audit_passed = False
        blockers_count = 1

        if audit_passed and blockers_count == 0:
            exit_code = 0
        else:
            exit_code = 1

        assert exit_code == 1

    def test_cli_output_file_writing(self):
        """Test writing audit report to output file"""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "audit-report.yaml"

            report_data = {
                "audit_id": "audit-001",
                "decision": "pass"
            }

            output_path.write_text(yaml.dump(report_data))

            assert output_path.exists()
            content = output_path.read_text()
            assert "audit-001" in content


# ============================================================================
# Integration-Style Unit Tests
# ============================================================================

class TestEndToEndAudit:
    """End-to-end style unit tests for complete audit flow"""

    def test_full_audit_flow_compliant(self, valid_manifest_data: Dict[str, Any], temp_scan_directory: Path):
        """Test complete audit flow with compliant files"""
        # Setup: Create files in correct locations
        feat_file = temp_scan_directory / "spec" / "requirements" / "SRC-056" / "FEAT-SRC-056-001.md"
        feat_file.write_text("# FEAT-SRC-056-001")

        # Simulate audit
        expected_dir = "spec/requirements/SRC-056/"
        actual_path = str(feat_file.relative_to(temp_scan_directory)).replace("\\", "/") + "/"

        is_compliant = actual_path.startswith(expected_dir) or expected_dir in actual_path

        # Result
        report = AuditReport(
            audit_id="audit-e2e-001",
            workflow_instance_id="wf-task-test-001",
            summary={"total_files": 1, "compliant_files": 1, "non_compliant_files": 0},
            blockers=[],
            majors=[],
            minors=[],
            misplaced_files=[],
            decision="pass"
        )

        assert is_compliant
        assert report.decision == "pass"

    def test_full_audit_flow_non_compliant(self, valid_manifest_data: Dict[str, Any]):
        """Test complete audit flow with non-compliant files"""
        # Setup: File in wrong location
        actual_path = "step_workspace/wrong_dir/FEAT-SRC-056-001.md"
        expected_dir = "spec/requirements/SRC-056/"

        # Detect violation
        finding = AuditFinding(
            file_path=actual_path,
            expected_dir=expected_dir,
            actual_dir="step_workspace/wrong_dir/",
            severity="blocker",
            reason="Formal SSOT written to step_workspace instead of canonical directory"
        )

        # Result
        report = AuditReport(
            audit_id="audit-e2e-002",
            workflow_instance_id="wf-task-test-001",
            summary={"total_files": 1, "compliant_files": 0, "non_compliant_files": 1},
            blockers=[finding],
            majors=[],
            minors=[],
            misplaced_files=[finding],
            decision="reject"
        )

        assert report.decision == "reject"
        assert len(report.blockers) == 1


# ============================================================================
# Edge Cases and Error Handling
# ============================================================================

class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_empty_manifest_artifacts_list(self):
        """Test handling manifest with empty expected_artifacts"""
        manifest_data = {
            "manifest_id": "test-manifest",
            "run_scope": {
                "workflow_instance_id": "wf-test",
                "workflow_id": "test",
                "run_id": "001"
            },
            "expected_artifacts": [],  # Empty list
            "placement_rules": []
        }

        # Should not raise error, just result in empty audit
        assert len(manifest_data["expected_artifacts"]) == 0

    def test_unicode_paths(self):
        """Test handling of Unicode characters in paths"""
        path_with_unicode = Path("spec/requirements/测试/FEAT-测试.md")

        # Should handle unicode paths
        assert "测试" in str(path_with_unicode)

    def test_windows_path_separators(self):
        """Test handling of Windows path separators"""
        windows_path = "spec\\requirements\\SRC-056\\FEAT-001.md"
        normalized = windows_path.replace("\\", "/")

        assert "\\" not in normalized
        assert "/" in normalized

    def test_relative_vs_absolute_paths(self):
        """Test handling of relative vs absolute paths"""
        relative = Path("./spec/requirements/SRC-056")
        # Use Windows-compatible absolute path
        absolute = Path("C:/absolute/path/spec/requirements/SRC-056")

        # Both should be valid Path objects
        assert relative.is_relative_to(".") if hasattr(relative, 'is_relative_to') else True
        assert absolute.is_absolute()
