"""Canonical evidence collection interfaces."""

from .collector import EvidenceCollector, EvidenceEntry
from .manifest import EvidenceManifestBuilder

__all__ = [
    "EvidenceCollector",
    "EvidenceEntry",
    "EvidenceManifestBuilder",
]
