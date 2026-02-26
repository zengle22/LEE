"""
LEE Artifact Management System

产出物管理系统 - 统一管理 LEE 执行过程中的所有产出物。

版本: v2.1
"""

from .types import ArtifactType, ArtifactCategory, ArtifactStatus, AdoptMode
from .models import ArtifactMetadata, RunManifest, ArtifactReference
from .registry import ArtifactRegistry
from .manifest import ManifestManager
from .manager import ArtifactManager

__all__ = [
    "ArtifactType",
    "ArtifactCategory",
    "ArtifactStatus",
    "AdoptMode",
    "ArtifactMetadata",
    "RunManifest",
    "ArtifactReference",
    "ArtifactRegistry",
    "ManifestManager",
    "ArtifactManager",
]

__version__ = "2.1.0"
