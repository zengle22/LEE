"""
Deliverables Reviewer Agent - Workflow Adapter

Adapts the deliverables checker for use in LEE workflow system.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional

from lee.agents.deliverables_reviewer import (
    DeliverablesChecker,
    DeliverablesReportGenerator,
)


class DeliverablesReviewerAgent:
    """
    Agent for reviewing deliverables completeness in workflow context.

    This agent validates that all deliverables defined in a FEAT specification
    are produced before allowing handoff to the next phase.
    """

    def __init__(self, project_root: str):
        self.project_root = Path(project_root)
        self.checker = DeliverablesChecker(project_root)
        self.report_generator = DeliverablesReportGenerator()

    def execute(
        self,
        feat_spec_ref: str,
        output_dir: str,
        search_dirs: Optional[List[str]] = None,
        fail_on_missing: bool = True,
    ) -> Dict[str, Any]:
        """
        Execute deliverables check.

        Args:
            feat_spec_ref: Path to FEAT specification file
            output_dir: Directory for output reports
            search_dirs: Directories to search for deliverables
            fail_on_missing: Whether to fail if deliverables are missing

        Returns:
            Dictionary with check results and gate decision
        """
        # Run check
        result = self.checker.check_deliverables(
            feat_spec_path=feat_spec_ref,
            search_dirs=search_dirs,
        )

        # Generate reports
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        json_report_path = self.report_generator.generate_json_report(
            result,
            str(output_path / 'deliverables-check.json')
        )

        md_report_path = self.report_generator.generate_markdown_report(
            result,
            str(output_path / 'deliverables-check.md')
        )

        # Build output
        output = {
            'feature_id': result.feature_id,
            'feature_title': result.feature_title,
            'status': result.status,
            'gate_decision': result.gate_decision,
            'completeness_percentage': result.completeness_percentage,
            'complete_count': result.complete_count,
            'missing_count': result.missing_count,
            'total_count': result.total_count,
            'deliverables_check_report_ref': json_report_path,
            'deliverables_report_md': md_report_path,
            'issues': result.issues,
        }

        # Add detailed deliverable info
        output['required_deliverables'] = [
            {
                'name': d.name,
                'description': d.description,
                'status': d.status,
                'path': d.path,
            }
            for d in result.required_deliverables
        ]

        return output

    def validate_and_return(
        self,
        feat_spec_ref: str,
        output_dir: str,
        search_dirs: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Execute check and return formatted result for workflow.

        This is the main entry point for workflow execution.
        """
        return self.execute(
            feat_spec_ref=feat_spec_ref,
            output_dir=output_dir,
            search_dirs=search_dirs,
            fail_on_missing=True,
        )


# =============================================================================
# Workflow Entry Point
# =============================================================================

def run_deliverables_check(
    *,
    feat_spec_ref: str,
    output_dir: str,
    search_dirs: Optional[List[str]] = None,
    project_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run deliverables check for workflow.

    This function is called by the LEE workflow orchestrator.

    Args:
        feat_spec_ref: Path to FEAT specification file (relative to project root)
        output_dir: Directory for output reports
        search_dirs: List of directories to search for deliverables
        project_root: Project root directory (defaults to current dir)

    Returns:
        Dictionary with:
        - deliverables_check_report_ref: Path to JSON report
        - deliverables_gate_result: 'pass' or 'fail'
        - completeness_percentage: 0-100
        - issues: List of missing deliverables
    """
    if project_root is None:
        project_root = '.'

    agent = DeliverablesReviewerAgent(project_root)
    result = agent.validate_and_return(
        feat_spec_ref=feat_spec_ref,
        output_dir=output_dir,
        search_dirs=search_dirs,
    )

    # Format for workflow output
    return {
        'deliverables_check_report_ref': result['deliverables_check_report_ref'],
        'deliverables_gate_result': result['gate_decision'],
        'completeness_percentage': result['completeness_percentage'],
        'complete_count': result['complete_count'],
        'missing_count': result['missing_count'],
        'total_count': result['total_count'],
        'issues': result['issues'],
        'required_deliverables': result['required_deliverables'],
    }


if __name__ == '__main__':
    # CLI usage for testing
    import sys

    if len(sys.argv) < 2:
        print("Usage: python deliverables_reviewer_agent.py <feat_spec_path> [output_dir]")
        sys.exit(1)

    feat_spec = sys.argv[1]
    output = sys.argv[2] if len(sys.argv) > 2 else 'output'

    result = run_deliverables_check(
        feat_spec_ref=feat_spec,
        output_dir=output,
    )

    print(f"\nDeliverables Check: {result.get('feature_id', 'Unknown')}")
    print(f"Status: {result.get('gate_decision', 'unknown').upper()}")
    print(f"Completeness: {result.get('completeness_percentage', 0):.1f}%")

    if result.get('missing_count', 0) > 0:
        print(f"\nMissing deliverables ({result['missing_count']}):")
        for issue in result.get('issues', []):
            print(f"  - {issue['file']}: {issue['title']}")
        sys.exit(1)

    print("\n✅ All deliverables complete!")
