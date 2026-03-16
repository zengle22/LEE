"""
Deliverables Reviewer Agent

Validates that all deliverables defined in a FEAT specification are produced.
Ensures completeness of workflow outputs before handoff.
"""

import yaml
import json
import click
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from datetime import datetime


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class DeliverableRequirement:
    """Represents a required deliverable from FEAT spec"""
    name: str
    description: str
    status: str  # complete, missing
    path: Optional[str] = None
    expected_location: Optional[str] = None


@dataclass
class DeliverablesCheckResult:
    """Represents the result of deliverables validation"""
    feature_id: str
    feature_title: str
    check_timestamp: str
    feat_spec_path: str

    required_deliverables: List[DeliverableRequirement] = field(default_factory=list)
    optional_deliverables: List[DeliverableRequirement] = field(default_factory=list)

    complete_count: int = 0
    missing_count: int = 0
    total_count: int = 0

    completeness_percentage: float = 0.0

    status: str = "pending"  # pass, fail, partial_pass
    issues: List[Dict[str, Any]] = field(default_factory=list)

    gate_decision: str = "pending"  # pass, fail


# =============================================================================
# Deliverables Checker
# =============================================================================

class DeliverablesChecker:
    """Checks deliverables completeness against FEAT specification"""

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)

    def load_feat_spec(self, feat_spec_path: str) -> Dict[str, Any]:
        """Load and parse FEAT specification"""
        path = self.project_root / feat_spec_path
        if not path.exists():
            raise FileNotFoundError(f"FEAT spec not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse YAML frontmatter
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 2:
                yaml_content = parts[1].strip()
                return yaml.safe_load(yaml_content)

        return {}

    def extract_required_outputs(self, feat_spec: Dict[str, Any]) -> List[str]:
        """Extract required outputs from FEAT spec

        Looks for outputs in two locations:
        1. Root level 'outputs' key (standard location)
        2. 'properties.outputs' key (alternative location for FEAT specs)
        """
        # Try root level first
        outputs = feat_spec.get('outputs', [])
        if isinstance(outputs, list) and outputs:
            return [str(o) for o in outputs if o]

        # Fall back to properties.outputs for FEAT specs
        properties = feat_spec.get('properties', {})
        if isinstance(properties, dict):
            outputs = properties.get('outputs', [])
            if isinstance(outputs, list):
                return [str(o) for o in outputs if o]

        return []

    def find_deliverable_path(
        self,
        deliverable_name: str,
        search_dirs: List[str]
    ) -> Optional[str]:
        """Find the path of a deliverable file"""
        # Extract file name from deliverable description
        # e.g., "artifact_placement_reviewer.py agent 核心模块" -> "artifact_placement_reviewer.py"
        parts = deliverable_name.split()
        file_name = parts[0] if parts else deliverable_name

        for search_dir in search_dirs:
            search_path = self.project_root / search_dir
            if not search_path.exists():
                continue

            # Search for the file
            for found in search_path.rglob(file_name):
                return str(found.relative_to(self.project_root))

        return None

    def check_deliverables(
        self,
        feat_spec_path: str,
        search_dirs: Optional[List[str]] = None
    ) -> DeliverablesCheckResult:
        """Check if all deliverables are present"""

        if search_dirs is None:
            search_dirs = [
                'src',
                'spec',
                'docs',
                'examples',
                'output',
            ]

        # Load FEAT spec
        feat_spec = self.load_feat_spec(feat_spec_path)

        # Extract metadata
        feature_id = feat_spec.get('id', 'UNKNOWN')
        feature_title = feat_spec.get('title', 'Unknown Feature')

        # Get required outputs
        required_outputs = self.extract_required_outputs(feat_spec)

        # Check each deliverable
        result = DeliverablesCheckResult(
            feature_id=feature_id,
            feature_title=feature_title,
            check_timestamp=datetime.now().isoformat(),
            feat_spec_path=feat_spec_path,
        )

        for output in required_outputs:
            # Parse output description
            parts = output.split(' ', 1)
            file_name = parts[0]
            description = parts[1] if len(parts) > 1 else ''

            # Find the file
            found_path = self.find_deliverable_path(file_name, search_dirs)

            deliverable = DeliverableRequirement(
                name=file_name,
                description=description,
                status='complete' if found_path else 'missing',
                path=found_path,
                expected_location=f'**/{file_name}',
            )

            if deliverable.status == 'complete':
                result.complete_count += 1
            else:
                result.missing_count += 1
                result.issues.append({
                    'id': f'DELIVERABLE-GAP-{len(result.issues) + 1:03d}',
                    'severity': 'medium',
                    'title': f'Missing deliverable: {file_name}',
                    'file': file_name,
                    'description': description,
                })

            result.required_deliverables.append(deliverable)

        # Calculate statistics
        result.total_count = len(required_outputs)
        if result.total_count > 0:
            result.completeness_percentage = (
                result.complete_count / result.total_count * 100
            )

        # Determine status
        if result.missing_count == 0:
            result.status = 'pass'
            result.gate_decision = 'pass'
        elif result.complete_count == 0:
            result.status = 'fail'
            result.gate_decision = 'fail'
        else:
            result.status = 'partial_pass'
            result.gate_decision = 'fail'  # Still fail the gate if incomplete

        return result


# =============================================================================
# Report Generator
# =============================================================================

class DeliverablesReportGenerator:
    """Generates deliverables check reports"""

    def generate_json_report(
        self,
        result: DeliverablesCheckResult,
        output_path: str
    ) -> str:
        """Generate JSON report"""
        report = {
            'feature_id': result.feature_id,
            'feature_title': result.feature_title,
            'check_timestamp': result.check_timestamp,
            'feat_spec_path': result.feat_spec_path,
            'status': result.status,
            'gate_decision': result.gate_decision,
            'completeness': {
                'complete_count': result.complete_count,
                'missing_count': result.missing_count,
                'total_count': result.total_count,
                'percentage': round(result.completeness_percentage, 2),
            },
            'required_deliverables': [
                {
                    'name': d.name,
                    'description': d.description,
                    'status': d.status,
                    'path': d.path,
                    'expected_location': d.expected_location,
                }
                for d in result.required_deliverables
            ],
            'issues': result.issues,
        }

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        return str(path)

    def generate_markdown_report(
        self,
        result: DeliverablesCheckResult,
        output_path: str
    ) -> str:
        """Generate Markdown report"""
        status_emoji = {
            'pass': '✅',
            'fail': '❌',
            'partial_pass': '⚠️',
        }

        lines = [
            "# Deliverables Check Report",
            "",
            f"**Feature**: {result.feature_id} - {result.feature_title}",
            f"**Check Date**: {result.check_timestamp}",
            f"**Status**: {status_emoji.get(result.status, '❓')} {result.status.upper()}",
            f"**Gate Decision**: {result.gate_decision.upper()}",
            "",
            "---",
            "",
            "## Completeness Summary",
            "",
            "| Metric | Value |",
            "|--------|-------|",
            f"| Total Deliverables | {result.total_count} |",
            f"| Complete | {result.complete_count} ✅ |",
            f"| Missing | {result.missing_count} ❌ |",
            f"| Completeness | {result.completeness_percentage:.1f}% |",
            "",
            "---",
            "",
            "## Required Deliverables Status",
            "",
            "| Deliverable | Description | Status | Path |",
            "|-------------|-------------|--------|------|",
        ]

        for d in result.required_deliverables:
            emoji = '✅' if d.status == 'complete' else '❌'
            path_display = d.path if d.path else 'N/A'
            lines.append(
                f"| `{d.name}` | {d.description} | {emoji} {d.status} | {path_display} |"
            )

        if result.issues:
            lines.extend([
                "",
                "---",
                "",
                "## Issues",
                "",
            ])

            for issue in result.issues:
                lines.extend([
                    f"### {issue['id']}: {issue['title']}",
                    "",
                    f"- **Severity**: {issue['severity']}",
                    f"- **File**: `{issue['file']}`",
                    f"- **Description**: {issue.get('description', 'N/A')}",
                    "",
                ])

        lines.extend([
            "",
            "---",
            "",
            "## Recommendation",
            "",
        ])

        if result.gate_decision == 'pass':
            lines.append("✅ All deliverables complete. Ready for handoff.")
        else:
            lines.append(
                f"❌ {result.missing_count} deliverable(s) missing. "
                f"Complete missing files before proceeding."
            )

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

        return str(path)


# =============================================================================
# Public API
# =============================================================================

def check_deliverables(
    feat_spec_path: str,
    project_root: Optional[str] = None,
    output_dir: Optional[str] = None,
    search_dirs: Optional[List[str]] = None,
) -> DeliverablesCheckResult:
    """
    Check deliverables completeness for a feature.

    Args:
        feat_spec_path: Path to FEAT specification file
        project_root: Project root directory (defaults to current dir)
        output_dir: Directory for output reports (optional)
        search_dirs: Directories to search for deliverables

    Returns:
        DeliverablesCheckResult with validation results
    """
    if project_root is None:
        project_root = '.'

    checker = DeliverablesChecker(project_root)
    result = checker.check_deliverables(feat_spec_path, search_dirs)

    # Generate reports if output_dir specified
    if output_dir:
        report_gen = DeliverablesReportGenerator()
        report_gen.generate_json_report(
            result,
            Path(output_dir) / 'deliverables-check.json'
        )
        report_gen.generate_markdown_report(
            result,
            Path(output_dir) / 'deliverables-check.md'
        )

    return result


# =============================================================================
# CLI Interface
# =============================================================================

@click.group()
def cli():
    """Deliverables Reviewer CLI"""
    pass


@cli.command('check')
@click.option(
    '--feat-spec', 'feat_spec_path',
    required=True,
    help='Path to FEAT specification file'
)
@click.option(
    '--project-root',
    default='.',
    help='Project root directory'
)
@click.option(
    '--output-dir',
    default=None,
    help='Output directory for reports'
)
@click.option(
    '--search-dirs',
    default=None,
    help='Comma-separated list of directories to search'
)
@click.option(
    '--fail-on-missing/--no-fail-on-missing',
    default=True,
    help='Exit with error code if deliverables are missing'
)
def check_command(
    feat_spec_path: str,
    project_root: str,
    output_dir: str,
    search_dirs: str,
    fail_on_missing: bool
):
    """Check deliverables completeness"""

    search_dirs_list = None
    if search_dirs:
        search_dirs_list = [d.strip() for d in search_dirs.split(',')]

    result = check_deliverables(
        feat_spec_path=feat_spec_path,
        project_root=project_root,
        output_dir=output_dir,
        search_dirs=search_dirs_list,
    )

    # Print summary
    click.echo(f"\nDeliverables Check: {result.feature_id}")
    click.echo(f"Status: {result.status.upper()}")
    click.echo(f"Complete: {result.complete_count}/{result.total_count} ({result.completeness_percentage:.1f}%)")

    if result.missing_count > 0:
        click.echo(f"\nMissing deliverables ({result.missing_count}):")
        for issue in result.issues:
            click.echo(f"  - {issue['file']}: {issue['title']}")

    if fail_on_missing and result.gate_decision == 'fail':
        click.echo("\n❌ Gate: FAILED")
        raise click.Exit(1)
    else:
        click.echo(f"\nGate: {result.gate_decision.upper()}")


if __name__ == '__main__':
    cli()
