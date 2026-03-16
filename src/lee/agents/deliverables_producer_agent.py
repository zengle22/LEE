"""
Deliverables Producer Agent - Workflow Adapter

将交付物生产功能集成到 LEE workflow 系统中。
"""

import os
from typing import Any, Dict, List, Optional

from .deliverables_producer import produce_deliverables, DeliverablesProducer


def run_deliverables_production(
    *,
    feat_spec_ref: str,
    missing_deliverables: List[str],
    output_base: str,
    search_dirs: Optional[List[str]] = None,
    project_root: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Run deliverables production for workflow.

    Args:
        feat_spec_ref: Path to FEAT specification file
        missing_deliverables: List of missing deliverable filenames
        output_base: Base directory for output files
        search_dirs: Directories to search for context
        project_root: Project root directory

    Returns:
        Dictionary containing:
        - produced_deliverables_package_ref: Path to production report
        - deliverables_production_result: "pass" or "fail"
        - produced_count: Number of deliverables produced
        - failed_count: Number of deliverables failed to produce
    """
    if project_root is None:
        project_root = os.getcwd()

    # Run production
    result = produce_deliverables(
        feat_spec_ref=feat_spec_ref,
        missing_deliverables=missing_deliverables,
        output_base=output_base,
        search_dirs=search_dirs,
        project_root=project_root,
    )

    # Calculate statistics
    produced_count = sum(
        1 for d in result.get('produced_deliverables', [])
        if d.get('status') == 'produced'
    )
    failed_count = len(missing_deliverables) - produced_count

    # Generate production report
    report_path = os.path.join(output_base, "deliverables-production-report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    import json
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return {
        "produced_deliverables_package_ref": report_path,
        "deliverables_production_result": result.get('deliverables_production_result', 'fail'),
        "produced_count": produced_count,
        "failed_count": failed_count,
        "feature_id": result.get('feature_id', 'UNKNOWN'),
    }
