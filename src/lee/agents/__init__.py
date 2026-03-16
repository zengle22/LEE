"""
LEE Agents Package

Provides reusable agent modules for workflow automation.
"""

from lee.agents.artifact_placement_reviewer import (
    audit_directory,
    ManifestLoader,
    DirectoryScanner,
    PlacementAuditor,
    ReportGenerator,
    AuditReport,
    AuditFinding,
    PlacementManifest,
    ExpectedArtifact,
)

from lee.agents.deliverables_reviewer import (
    check_deliverables,
    DeliverablesChecker,
    DeliverablesCheckResult,
    DeliverablesReportGenerator,
    DeliverableRequirement,
)

from lee.agents.deliverables_producer import (
    produce_deliverables,
    DeliverablesProducer,
    DeliverableProductionResult,
)

__all__ = [
    # Artifact Placement Reviewer
    "audit_directory",
    "ManifestLoader",
    "DirectoryScanner",
    "PlacementAuditor",
    "ReportGenerator",
    "AuditReport",
    "AuditFinding",
    "PlacementManifest",
    "ExpectedArtifact",
    # Deliverables Reviewer
    "check_deliverables",
    "DeliverablesChecker",
    "DeliverablesCheckResult",
    "DeliverablesReportGenerator",
    "DeliverableRequirement",
    # Deliverables Producer
    "produce_deliverables",
    "DeliverablesProducer",
    "DeliverableProductionResult",
]
