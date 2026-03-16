"""Canonical evidence collection interfaces."""

from .collector import EvidenceCollector, EvidenceEntry
from .manifest import EvidenceManifestBuilder
from .validator import EvidenceValidator
from .coverage_auditor import CoverageAuditor

__all__ = [
    "EvidenceCollector",
    "EvidenceEntry",
    "EvidenceManifestBuilder",
    "EvidenceValidator",
    "CoverageAuditor",
]
