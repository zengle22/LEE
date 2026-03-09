"""
LEE Artifact Management System

产出物管理系统 - 统一管理 LEE 执行过程中的所有产出物。

版本: v2.2 (SSOT v1.3 升级)
"""

from .types import (
    ArtifactType,
    ArtifactCategory,
    ArtifactStatus,
    AdoptMode,
    GovernanceKind,
    # SSOT v1.3 新增
    SSOTType,
    ObjectCategory,
    Department,
)
from .models import (
    ArtifactMetadata,
    RunManifest,
    ArtifactReference,
    # SSOT v1.3 新增
    SSOTMetadata,
)
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
from .context import TaskContextBundle, ContextBuilder, PromptSnapshot
from .task_brief import TaskBrief, TaskBriefGenerator
from .ssot_service import SSOTService, SSOTValidator, ValidationResult

# SSOT v1.3 新增
from .id_parser import (
    parse_parent,
    parse_scope,
    resolve_scope,
    parse_id,
    validate_id_format,
    validate_parent_consistency,
    IDParseResult,
)
from .id_generator import (
    SSOTIDGenerator,
    get_generator,
)
from .placement import SSOT_PLACEMENT_DIRS, resolve_ssot_relative_dir
from .ssot_contract import SSOTContractMaterializer, MaterializedOutput

__all__ = [
    # 类型枚举
    "ArtifactType",
    "ArtifactCategory",
    "ArtifactStatus",
    "AdoptMode",
    "GovernanceKind",
    "Department",
    # SSOT v1.3 新增
    "SSOTType",
    "ObjectCategory",
    # 数据模型
    "ArtifactMetadata",
    "RunManifest",
    "ArtifactReference",
    "SSOTMetadata",
    # 核心组件
    "ArtifactRegistry",
    "ManifestManager",
    "ArtifactManager",
    # 集成组件
    "ArtifactFileOutputHandler",
    "GateArtifactHandler",
    "create_artifact_handler",
    "HandoverManager",
    "ArtifactCleaner",
    "CleanupPolicy",
    "rebuild_registry",
    # 上下文组件
    "TaskContextBundle",
    "ContextBuilder",
    "PromptSnapshot",
    "TaskBrief",
    "TaskBriefGenerator",
    # SSOT 服务
    "SSOTService",
    "SSOTValidator",
    "ValidationResult",
    # SSOT v1.3 新增: ID 解析器
    "parse_parent",
    "parse_scope",
    "resolve_scope",
    "parse_id",
    "validate_id_format",
    "validate_parent_consistency",
    "IDParseResult",
    # SSOT v1.3 新增: ID 生成器
    "SSOTIDGenerator",
    "get_generator",
    "SSOT_PLACEMENT_DIRS",
    "resolve_ssot_relative_dir",
    "SSOTContractMaterializer",
    "MaterializedOutput",
]

__version__ = "2.2.0"
