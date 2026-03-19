"""
Artifact Placement Reviewer Agent

Audits directory file placement against a placement manifest.
Supports both CLI and Python API invocation.
"""

import yaml
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


# =============================================================================
# Data Models
# =============================================================================

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
    timestamp: str
    manifest_path: str
    target_directory: str
    summary: Dict[str, int]
    blockers: List[AuditFinding]
    majors: List[AuditFinding]
    minors: List[AuditFinding]
    misplaced_files: List[AuditFinding]
    missing_required: List[str]
    decision: str  # pass, revise, reject


# =============================================================================
# Manifest Loader
# =============================================================================

class ManifestLoader:
    """Loads and validates placement manifest files"""

    def __init__(self, schema_path: Optional[Path] = None):
        self.schema_path = schema_path
        self.schema = self._load_schema(schema_path) if schema_path else None

    def _load_schema(self, schema_path: Path) -> Dict[str, Any]:
        """Load JSON schema for validation"""
        with open(schema_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)

    def load(self, path: Path) -> PlacementManifest:
        """Load manifest file and parse into structured object"""
        if not path.exists():
            raise FileNotFoundError(f"Manifest file not found: {path}")

        content = path.read_text(encoding='utf-8')
        data = yaml.safe_load(content)

        return self._parse_manifest(data)

    def _parse_manifest(self, data: Dict[str, Any]) -> PlacementManifest:
        """Parse raw data into PlacementManifest object"""
        # Validate required fields
        required_fields = ['manifest_id', 'run_scope', 'expected_artifacts', 'placement_rules']
        for field_name in required_fields:
            if field_name not in data:
                raise ValueError(f"Missing required field: {field_name}")

        # Parse run_scope
        run_scope_data = data['run_scope']
        run_scope = RunScope(
            workflow_instance_id=run_scope_data['workflow_instance_id'],
            workflow_id=run_scope_data['workflow_id'],
            run_id=run_scope_data['run_id'],
            step_workspace=run_scope_data.get('step_workspace')
        )

        # Parse expected_artifacts
        expected_artifacts = [
            ExpectedArtifact(
                artifact_id=artifact['artifact_id'],
                artifact_kind=artifact['artifact_kind'],
                identity_kind=artifact['identity_kind'],
                placement_key=artifact['placement_key'],
                expected_dir=artifact['expected_dir'],
                required=artifact.get('required', True),
                ssot_type=artifact.get('ssot_type'),
                source_refs=artifact.get('source_refs', [])
            )
            for artifact in data['expected_artifacts']
        ]

        # Parse placement_rules
        placement_rules = [
            PlacementRule(
                rule_id=rule['rule_id'],
                rule_kind=rule['rule_kind'],
                description=rule['description'],
                enforced=rule.get('enforced', True)
            )
            for rule in data['placement_rules']
        ]

        return PlacementManifest(
            manifest_id=data['manifest_id'],
            run_scope=run_scope,
            expected_artifacts=expected_artifacts,
            placement_rules=placement_rules,
            governing_adrs=data.get('governing_adrs', [])
        )


# =============================================================================
# Directory Scanner
# =============================================================================

class DirectoryScanner:
    """Scans directories and collects file metadata"""

    DEFAULT_IGNORE_PATTERNS = [
        '.git', '.gitignore', '__pycache__', '*.pyc', '*.pyo',
        '.workflow', '.claude', '*.log', '.DS_Store'
    ]

    def __init__(self, root_path: Path, ignore_patterns: Optional[List[str]] = None):
        self.root = root_path
        self.ignore_patterns = ignore_patterns or self.DEFAULT_IGNORE_PATTERNS.copy()

    def scan(self) -> List[FileEntry]:
        """Recursively scan directory and return list of file entries"""
        if not self.root.exists():
            raise FileNotFoundError(f"Target directory not found: {self.root}")

        files = []
        for file_path in self._rglob_files():
            if self._should_ignore(file_path):
                continue

            try:
                stat = file_path.stat()
                relative_path = str(file_path.relative_to(self.root)).replace('\\', '/')
                files.append(FileEntry(
                    file_path=file_path,
                    relative_path=relative_path,
                    size_bytes=stat.st_size,
                    modified_at=datetime.fromtimestamp(stat.st_mtime)
                ))
            except (PermissionError, OSError):
                # Skip files we can't access
                continue

        return files

    def _rglob_files(self) -> List[Path]:
        """Recursively glob all files, excluding directories"""
        return [p for p in self.root.rglob('*') if p.is_file()]

    def _should_ignore(self, path: Path) -> bool:
        """Check if path should be ignored"""
        path_str = str(path).replace('\\', '/')
        for pattern in self.ignore_patterns:
            if pattern.startswith('*'):
                if path_str.endswith(pattern[1:]):
                    return True
            elif pattern in path_str:
                return True
        return False


# =============================================================================
# Placement Auditor
# =============================================================================

class PlacementAuditor:
    """Executes audit by comparing manifest against scanned directory"""

    def __init__(self, manifest: PlacementManifest, scanner: DirectoryScanner):
        self.manifest = manifest
        self.scanner = scanner

    def audit(self) -> AuditReport:
        """Execute audit and return report"""
        # Scan directory
        scanned_files = self.scanner.scan()

        # Track findings
        blockers: List[AuditFinding] = []
        majors: List[AuditFinding] = []
        minors: List[AuditFinding] = []
        misplaced_files: List[AuditFinding] = []
        missing_required: List[str] = []

        # Check each expected artifact
        for artifact in self.manifest.expected_artifacts:
            artifact_found = False

            for file_entry in scanned_files:
                # Check if file matches this artifact's expected location
                if self._file_matches_artifact(file_entry, artifact):
                    artifact_found = True
                    # Check placement compliance
                    finding = self._check_placement_compliance(file_entry, artifact)
                    if finding:
                        self._categorize_finding(finding, blockers, majors, minors)
                        if finding.severity in ('blocker', 'major'):
                            misplaced_files.append(finding)

            # Check for missing required artifacts
            if not artifact_found and artifact.required:
                missing_required.append(artifact.artifact_id)
                blockers.append(AuditFinding(
                    file_path=f"<missing:{artifact.artifact_id}>",
                    expected_dir=artifact.expected_dir,
                    actual_dir="<not found>",
                    severity="blocker",
                    reason=f"Required artifact '{artifact.artifact_id}' is missing",
                    artifact_id=artifact.artifact_id
                ))

        # Calculate summary
        total_files = len(scanned_files)
        non_compliant = len(blockers) + len(majors) + len(minors)
        compliant = total_files - non_compliant

        # Determine decision
        if blockers:
            decision = "reject"
        elif majors:
            decision = "revise"
        else:
            decision = "pass"

        return AuditReport(
            audit_id=str(uuid.uuid4())[:8],
            workflow_instance_id=self.manifest.run_scope.workflow_instance_id,
            timestamp=datetime.now().isoformat(),
            manifest_path=str(self.scanner.root / "manifest.yaml"),
            target_directory=str(self.scanner.root),
            summary={
                "total_files": total_files,
                "compliant_files": compliant,
                "non_compliant_files": non_compliant,
                "blockers": len(blockers),
                "majors": len(majors),
                "minors": len(minors),
                "missing_required": len(missing_required)
            },
            blockers=blockers,
            majors=majors,
            minors=minors,
            misplaced_files=misplaced_files,
            missing_required=missing_required,
            decision=decision
        )

    def _file_matches_artifact(self, file_entry: FileEntry, artifact: ExpectedArtifact) -> bool:
        """Check if a file matches an artifact's placement criteria.

        Uses strict path matching to ensure files are placed in the correct directory.
        """
        from pathlib import Path

        expected_dir = Path(artifact.expected_dir).as_posix()
        file_path = Path(file_entry.relative_path).as_posix()

        try:
            # Use relative_to for strict prefix matching
            # This ensures the file is actually under the expected directory
            Path(file_path).relative_to(expected_dir)
            return True
        except ValueError:
            # relative_to raises ValueError if expected_dir is not a prefix of file_path
            pass

        # Fallback: check if file_path starts with expected_dir as a path prefix
        # Normalize both paths to ensure consistent comparison
        if not expected_dir.endswith('/'):
            expected_dir += '/'
        return file_path.startswith(expected_dir) or file_path.startswith(expected_dir.rstrip('/') + '/')

    def _check_placement_compliance(self, file_entry: FileEntry, artifact: ExpectedArtifact) -> Optional[AuditFinding]:
        """Check if file is placed correctly according to artifact rules"""
        expected_dir = artifact.expected_dir.replace('\\', '/')
        actual_dir = str(Path(file_entry.relative_path).parent).replace('\\', '/') + '/'

        # Check if file is in expected directory
        if not (file_entry.relative_path.startswith(expected_dir) or expected_dir in file_entry.relative_path):
            return AuditFinding(
                file_path=file_entry.relative_path,
                expected_dir=expected_dir,
                actual_dir=actual_dir,
                severity="major",
                reason="File placed in wrong directory",
                artifact_id=artifact.artifact_id
            )

        return None

    def _categorize_finding(self, finding: AuditFinding,
                           blockers: List[AuditFinding],
                           majors: List[AuditFinding],
                           minors: List[AuditFinding]):
        """Categorize finding by severity"""
        if finding.severity == "blocker":
            blockers.append(finding)
        elif finding.severity == "major":
            majors.append(finding)
        else:
            minors.append(finding)


# =============================================================================
# Report Generator
# =============================================================================

class ReportGenerator:
    """Generates audit reports in various formats"""

    def generate_json(self, report: AuditReport) -> str:
        """Generate JSON format report"""
        data = {
            "audit_id": report.audit_id,
            "workflow_instance_id": report.workflow_instance_id,
            "timestamp": report.timestamp,
            "manifest_path": report.manifest_path,
            "target_directory": report.target_directory,
            "summary": report.summary,
            "blockers": [self._finding_to_dict(f) for f in report.blockers],
            "majors": [self._finding_to_dict(f) for f in report.majors],
            "minors": [self._finding_to_dict(f) for f in report.minors],
            "misplaced_files": [self._finding_to_dict(f) for f in report.misplaced_files],
            "missing_required": report.missing_required,
            "decision": report.decision
        }
        return json.dumps(data, indent=2, ensure_ascii=False)

    def generate_text(self, report: AuditReport, verbose: bool = False) -> str:
        """Generate human-readable text report"""
        lines = [
            "=" * 60,
            "ARTIFACT PLACEMENT AUDIT REPORT",
            "=" * 60,
            f"Audit ID: {report.audit_id}",
            f"Workflow: {report.workflow_instance_id}",
            f"Timestamp: {report.timestamp}",
            "",
            "SUMMARY",
            "-" * 40,
            f"Total Files: {report.summary['total_files']}",
            f"Compliant: {report.summary['compliant_files']}",
            f"Non-Compliant: {report.summary['non_compliant_files']}",
            f"Blockers: {report.summary['blockers']}",
            f"Majors: {report.summary['majors']}",
            f"Minors: {report.summary['minors']}",
            f"Missing Required: {report.summary['missing_required']}",
            "",
            f"DECISION: {report.decision.upper()}",
            ""
        ]

        if report.blockers:
            lines.extend(["BLOCKERS", "-" * 40])
            for finding in report.blockers:
                lines.append(f"  - {finding.file_path}: {finding.reason}")
            lines.append("")

        if report.majors:
            lines.extend(["MAJORS", "-" * 40])
            for finding in report.majors:
                lines.append(f"  - {finding.file_path}: {finding.reason}")
            lines.append("")

        if verbose and report.minors:
            lines.extend(["MINORS", "-" * 40])
            for finding in report.minors:
                lines.append(f"  - {finding.file_path}: {finding.reason}")
            lines.append("")

        lines.append("=" * 60)
        return "\n".join(lines)

    def save(self, report: AuditReport, output_path: Path, format: str = "json"):
        """Save report to file"""
        if format == "json":
            content = self.generate_json(report)
            output_path = output_path.with_suffix('.json')
        else:
            content = self.generate_text(report, verbose=True)
            output_path = output_path.with_suffix('.txt')

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(content, encoding='utf-8')

    def _finding_to_dict(self, finding: AuditFinding) -> Dict[str, Any]:
        """Convert AuditFinding to dictionary"""
        return {
            "file_path": finding.file_path,
            "expected_dir": finding.expected_dir,
            "actual_dir": finding.actual_dir,
            "severity": finding.severity,
            "reason": finding.reason,
            "artifact_id": finding.artifact_id
        }


# =============================================================================
# Public API
# =============================================================================

def audit_directory(
    manifest_path: str,
    target_path: str,
    output_path: Optional[str] = None,
    format: str = "json",
    verbose: bool = False,
    fail_on_violation: bool = False,
    fail_on_missing: bool = False
) -> AuditReport:
    """
    Execute directory audit against a placement manifest.

    Args:
        manifest_path: Path to the placement manifest YAML file
        target_path: Path to the directory to audit
        output_path: Optional path to save the report
        format: Output format ('json' or 'text')
        verbose: Include detailed output in text format
        fail_on_violation: Return non-zero exit code on violations
        fail_on_missing: Return non-zero exit code on missing required files

    Returns:
        AuditReport object with audit results
    """
    # Load manifest
    loader = ManifestLoader()
    manifest = loader.load(Path(manifest_path))

    # Scan directory
    scanner = DirectoryScanner(Path(target_path))

    # Execute audit
    auditor = PlacementAuditor(manifest, scanner)
    report = auditor.audit()

    # Generate and save report
    if output_path:
        generator = ReportGenerator()
        generator.save(report, Path(output_path), format=format)

    return report


# =============================================================================
# CLI Interface
# =============================================================================

def create_cli():
    """Create and return the CLI application"""
    try:
        import click
    except ImportError:
        raise ImportError("click is required for CLI. Install with: pip install click")

    @click.group()
    def cli():
        """LEE Artifact Placement Reviewer"""
        pass

    @cli.command()
    @click.option('--manifest', required=True, help='Path to placement manifest YAML file')
    @click.option('--target', required=True, help='Target directory to audit')
    @click.option('--output', default='./audit_report.json', help='Output report path')
    @click.option('--format', type=click.Choice(['json', 'text']), default='json', help='Output format')
    @click.option('--verbose', is_flag=True, help='Verbose output')
    @click.option('--fail-on-violation', is_flag=True, help='Exit with code 1 on violations')
    @click.option('--fail-on-missing', is_flag=True, help='Exit with code 2 on missing required files')
    def audit(manifest, target, output, format, verbose, fail_on_violation, fail_on_missing):
        """Audit directory file placement against manifest"""
        try:
            report = audit_directory(
                manifest_path=manifest,
                target_path=target,
                output_path=output,
                format=format,
                verbose=verbose,
                fail_on_violation=fail_on_violation,
                fail_on_missing=fail_on_missing
            )

            # Print summary
            if format == 'text':
                click.echo(ReportGenerator().generate_text(report, verbose=verbose))
            else:
                click.echo(f"Audit completed: {report.summary['total_files']} files scanned")
                click.echo(f"Decision: {report.decision.upper()}")
                click.echo(f"Report saved to: {output}")

            # Determine exit code
            if fail_on_violation and report.summary['non_compliant_files'] > 0:
                return 1
            if fail_on_missing and report.summary['missing_required'] > 0:
                return 2
            return 0

        except FileNotFoundError as e:
            click.echo(f"Error: {e}", err=True)
            return 3
        except Exception as e:
            click.echo(f"Error: {e}", err=True)
            return 3

    return cli


# CLI entry point
if __name__ == '__main__':
    cli = create_cli()
    cli()
