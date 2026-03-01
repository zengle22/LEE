"""
LEE Artifact Management System

产出物管理系统 - 统一管理 LEE 执行过程中的所有产出物。

版本: v2.1
"""

from .types import ArtifactType, ArtifactCategory, ArtifactStatus, AdoptMode, GovernanceKind
from .models import ArtifactMetadata, RunManifest, ArtifactReference
from .registry import ArtifactRegistry
from .manifest import ManifestManager
from .manager import ArtifactManager
from .integration import (
    ArtifactFileOutputHandler,
    GateArtifactHandler,
    create_artifact_handler,
)
from .handover import HandoverManager
from .cleanup import (
    ArtifactCleaner,
    CleanupPolicy,
    rebuild_registry,
)
from .context import TaskContextBundle, ContextBuilder

__all__ = [
    "ArtifactType",
    "ArtifactCategory",
    "ArtifactStatus",
    "AdoptMode",
    "GovernanceKind",
    "ArtifactMetadata",
    "RunManifest",
    "ArtifactReference",
    "ArtifactRegistry",
    "ManifestManager",
    "ArtifactManager",
    "ArtifactFileOutputHandler",
    "GateArtifactHandler",
    "create_artifact_handler",
    "HandoverManager",
    "ArtifactCleaner",
    "CleanupPolicy",
    "rebuild_registry",
    "TaskContextBundle",
    "ContextBuilder",
]

__version__ = "2.1.0"
