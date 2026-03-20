"""
Artifact Data Models

定义产出物管理系统的核心数据模型。
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .types import ArtifactType, ArtifactStatus, AdoptMode, GovernanceKind, SSOTType
from lee.orchestrator.core.path_policy import ARTIFACTS_SUBDIRS
from .id_generator import SSOTIDGenerator


@dataclass
class ArtifactMetadata:
    """
    产出物元数据

    路径规范 (v2.2):
    - path_root: path 的基准目录；默认是 .artifacts，也可以是项目根 "."
    - path: 相对于 path_root 的路径
    - external_path: 外部文件系统的原始路径 (adopt 时记录)
    - absolute_path: 运行时计算的绝对路径
    """

    # 基础标识
    id: str  # 格式: ART-{sequence}
    type: ArtifactType
    category: str  # 从配置生成的具体类别
    status: ArtifactStatus

    # 路径信息
    path: str  # 相对路径 (相对于 path_root)
    path_root: str = ".artifacts"  # path 的基准目录；"." 表示项目根
    external_path: Optional[str] = None  # 原始外部路径
    adopt_mode: Optional[AdoptMode] = None  # adopt 模式

    # 所属信息
    run_id: str = ""
    workflow_id: Optional[str] = None
    department: Optional[str] = None  # 用于 active/{department}/{run_id}/ 组织

    # 关系信息 (SSOT 真理链相关)
    depends_on: List[str] = field(default_factory=list)  # 依赖的 artifact IDs (辅助依赖)
    derived_from: Optional[str] = None  # 派生自哪个 artifact (设计链：API ← PRD)
    consumed_by: List[str] = field(default_factory=list)  # 被哪些 run/handover 消费

    # SSOT 真理链字段 (v1.0 新增)
    implements: List[str] = field(default_factory=list)  # 实现哪些契约 (CODE_REF → API)
    verifies: List[str] = field(default_factory=list)  # 验证哪些契约 (TEST → PRD/API)
    supersedes: Optional[str] = None  # 替代哪个旧真理 (版本演进)

    # 治理类别 (v1.0 新增)
    governance_kind: GovernanceKind = GovernanceKind.TRANSFER

    # Git 引用信息 (reference_mode)
    git_sha: Optional[str] = None
    git_repo_path: Optional[str] = None  # git repo 相对路径

    # 元数据
    title: str = ""
    description: str = ""
    tags: List[str] = field(default_factory=list)
    size_bytes: Optional[int] = None
    content_hash: Optional[str] = None  # SHA256

    # 时间戳
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    frozen_at: Optional[datetime] = None
    archived_at: Optional[datetime] = None

    # 扩展属性
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def absolute_path(self) -> Path:
        """计算绝对路径"""
        base_path = Path(self.path_root or ".artifacts")
        if not base_path.is_absolute():
            base_path = Path.cwd() / base_path
        return base_path / self.path

    @property
    def exists(self) -> bool:
        """检查文件是否存在"""
        if self.adopt_mode == AdoptMode.REFERENCE:
            # reference_mode 检查 git 引用是否有效
            return self._validate_git_reference()
        return self.absolute_path.exists()

    def _validate_git_reference(self) -> bool:
        """验证 git 引用是否有效"""
        if not self.git_sha:
            return False
        import subprocess

        try:
            repo_path = Path.cwd() / (self.git_repo_path or ".")
            result = subprocess.run(
                ["git", "cat-file", "-e", self.git_sha],
                cwd=repo_path,
                capture_output=True,
            )
            return result.returncode == 0
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "category": self.category,
            "status": self.status.value,
            "path": self.path,
            "path_root": self.path_root,
            "external_path": self.external_path,
            "adopt_mode": self.adopt_mode.value if self.adopt_mode else None,
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "department": self.department,
            "depends_on": self.depends_on,
            "derived_from": self.derived_from,
            "consumed_by": self.consumed_by,
            "implements": self.implements,
            "verifies": self.verifies,
            "supersedes": self.supersedes,
            "governance_kind": self.governance_kind.value,
            "git_sha": self.git_sha,
            "git_repo_path": self.git_repo_path,
            "title": self.title,
            "description": self.description,
            "tags": self.tags,
            "size_bytes": self.size_bytes,
            "content_hash": self.content_hash,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "frozen_at": self.frozen_at.isoformat() if self.frozen_at else None,
            "archived_at": self.archived_at.isoformat() if self.archived_at else None,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ArtifactMetadata":
        """从字典反序列化"""
        # 处理时间戳
        def parse_dt(s: Optional[str]) -> Optional[datetime]:
            return datetime.fromisoformat(s) if s else None

        return cls(
            id=data["id"],
            type=ArtifactType(data["type"]),
            category=data["category"],
            status=ArtifactStatus(data["status"]),
            path=data["path"],
            path_root=data.get("path_root", ".artifacts"),
            external_path=data.get("external_path"),
            adopt_mode=AdoptMode(data["adopt_mode"]) if data.get("adopt_mode") else None,
            run_id=data.get("run_id", ""),
            workflow_id=data.get("workflow_id"),
            department=data.get("department"),
            depends_on=data.get("depends_on", []),
            derived_from=data.get("derived_from"),
            consumed_by=data.get("consumed_by", []),
            implements=data.get("implements", []),
            verifies=data.get("verifies", []),
            supersedes=data.get("supersedes"),
            governance_kind=GovernanceKind(data["governance_kind"]) if data.get("governance_kind") else GovernanceKind.TRANSFER,
            git_sha=data.get("git_sha"),
            git_repo_path=data.get("git_repo_path"),
            title=data.get("title", ""),
            description=data.get("description", ""),
            tags=data.get("tags", []),
            size_bytes=data.get("size_bytes"),
            content_hash=data.get("content_hash"),
            created_at=parse_dt(data.get("created_at")) or datetime.now(),
            updated_at=parse_dt(data.get("updated_at")) or datetime.now(),
            frozen_at=parse_dt(data.get("frozen_at")),
            archived_at=parse_dt(data.get("archived_at")),
            properties=data.get("properties", {}),
        )


@dataclass
class ArtifactReference:
    """
    产出物引用

    用于在其他产出物中引用另一个产出物。
    """

    artifact_id: str
    ref_type: str  # "depends_on", "derived_from", "consumed_by", etc.
    title: Optional[str] = None
    category: Optional[str] = None


# ============================================================================
# SSOT v1.3 新增：SSOT 元数据模型
# ============================================================================

@dataclass
class SSOTMetadata:
    """
    SSOT 元数据 (v1.3 新增)

    新系统对象的主元数据，替代旧的 ArtifactMetadata 用于 SSOT 对象。
    文件命名: [ID]__[slug].[ext]
    """

    # 基础标识
    id: str  # SSOT ID，如 FEAT-001, TC-FEAT-001-001
    type: SSOTType  # 对象类型
    title: str  # 标题
    status: ArtifactStatus  # 状态

    # 版本信息
    version: str = "v1"  # 版本号

    # 结构归属关系
    parent_id: Optional[str] = None  # 结构父对象 ID (部分类型必填)

    # 派生与关联关系
    derived_from: List[str] = field(default_factory=list)  # 派生来源 (多值)
    source_refs: List[str] = field(default_factory=list)  # 源文档锚点，如 SRC-001#3.2
    related_ids: List[str] = field(default_factory=list)  # 横向关联对象

    # 验证与实现关系
    verifies: List[str] = field(default_factory=list)  # 验证哪些对象
    implements: List[str] = field(default_factory=list)  # 实现哪些对象

    # 治理信息
    owner: Optional[str] = None  # 负责人
    tags: List[str] = field(default_factory=list)  # 标签

    # 时间戳
    last_updated: Optional[datetime] = None

    # 路径信息 (运行时计算)
    _path: Optional[str] = None  # 相对路径

    # 扩展属性
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def path(self) -> str:
        """获取相对路径"""
        if self._path:
            return self._path
        # 默认路径：ssot/{type}/{id}.md
        return f"ssot/{self.type.value}/{self.id}.md"

    @path.setter
    def path(self, value: str) -> None:
        """设置路径"""
        self._path = value

    @property
    def slug(self) -> str:
        """从标题提取 slug"""
        return SSOTIDGenerator().generate_slug(self.title)

    @property
    def filename(self) -> str:
        """获取文件名"""
        return f"{self.id}__{self.slug}.md"

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "id": self.id,
            "type": self.type.value,
            "title": self.title,
            "status": self.status.value,
            "version": self.version,
            "parent_id": self.parent_id,
            "derived_from": self.derived_from,
            "source_refs": self.source_refs,
            "related_ids": self.related_ids,
            "verifies": self.verifies,
            "implements": self.implements,
            "owner": self.owner,
            "tags": self.tags,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
            "path": self.path,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SSOTMetadata":
        """从字典反序列化"""
        def parse_dt(s: Optional[str]) -> Optional[datetime]:
            return datetime.fromisoformat(s) if s else None

        return cls(
            id=data["id"],
            type=SSOTType(data["type"]),
            title=data["title"],
            status=ArtifactStatus(data.get("status", "ACTIVE")),
            version=data.get("version", "v1"),
            parent_id=data.get("parent_id"),
            derived_from=data.get("derived_from", []),
            source_refs=data.get("source_refs", []),
            related_ids=data.get("related_ids", []),
            verifies=data.get("verifies", []),
            implements=data.get("implements", []),
            owner=data.get("owner"),
            tags=data.get("tags", []),
            last_updated=parse_dt(data.get("last_updated")),
            _path=data.get("path"),
            properties=data.get("properties", {}),
        )


@dataclass
class RunManifest:
    """
    Run 级 Manifest

    每个 run_id 对应一个 manifest.yaml，记录该 run 产生的所有产出物。
    这是权威数据源，Registry 可以从此重建。

    路径: .artifacts/active/{department}/{run_id}/manifest.yaml
    """

    run_id: str
    workflow_id: Optional[str] = None
    department: Optional[str] = None
    status: str = "running"  # running, completed, failed, cancelled

    # 产出物列表
    artifacts: List[ArtifactMetadata] = field(default_factory=list)

    # 时间信息
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None

    # 执行信息
    executor: Optional[str] = None  # 执行器类型 (claude, amp, etc.)
    executor_version: Optional[str] = None

    # 上下文信息
    parent_run_id: Optional[str] = None  # 父 run (用于重试/子流程)
    root_run_id: Optional[str] = None  # 根 run (用于追踪完整链路)

    # 输入引用
    input_artifacts: List[str] = field(
        default_factory=list
    )  # 输入的 artifact IDs

    # SSOT Root 信息 (新增)
    ssot_root: Optional[Dict[str, Any]] = field(default_factory=dict)  # SSOT Root 信息

    # 输出移交
    handover_to: Optional[str] = None  # 移交目标 (department or phase)
    handover_artifacts: List[str] = field(
        default_factory=list
    )  # 移交的 artifact IDs

    # 扩展属性
    properties: Dict[str, Any] = field(default_factory=dict)

    @property
    def manifest_path(self) -> Path:
        """获取 manifest 文件路径"""
        # 返回相对路径，与原始代码保持一致
        # 使用 path_policy 中的常量构建路径
        if self.department:
            return Path(ARTIFACTS_SUBDIRS["active"]) / self.department / self.run_id / "manifest.yaml"
        return Path(ARTIFACTS_SUBDIRS["active"]) / self.run_id / "manifest.yaml"

    @property
    def artifacts_dir(self) -> Path:
        """获取产出物目录路径"""
        # 返回相对路径，与原始代码保持一致
        # 使用 path_policy 中的常量构建路径
        if self.department:
            return Path(ARTIFACTS_SUBDIRS["active"]) / self.department / self.run_id
        return Path(ARTIFACTS_SUBDIRS["active"]) / self.run_id

    def add_artifact(self, artifact: ArtifactMetadata) -> None:
        """添加产出物"""
        # 确保 ID 唯一
        existing_ids = {a.id for a in self.artifacts}
        if artifact.id in existing_ids:
            raise ValueError(f"Artifact ID {artifact.id} already exists in manifest")
        self.artifacts.append(artifact)

    def get_artifact(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """获取产出物"""
        for artifact in self.artifacts:
            if artifact.id == artifact_id:
                return artifact
        return None

    def get_artifacts_by_type(
        self, artifact_type: ArtifactType
    ) -> List[ArtifactMetadata]:
        """按类型获取产出物"""
        return [a for a in self.artifacts if a.type == artifact_type]

    def get_artifacts_by_category(self, category: str) -> List[ArtifactMetadata]:
        """按类别获取产出物"""
        return [a for a in self.artifacts if a.category == category]

    def to_dict(self) -> Dict[str, Any]:
        """序列化为字典"""
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "department": self.department,
            "status": self.status,
            "artifacts": [a.to_dict() for a in self.artifacts],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "executor": self.executor,
            "executor_version": self.executor_version,
            "parent_run_id": self.parent_run_id,
            "root_run_id": self.root_run_id,
            "input_artifacts": self.input_artifacts,
            "ssot_root": self.ssot_root,
            "handover_to": self.handover_to,
            "handover_artifacts": self.handover_artifacts,
            "properties": self.properties,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RunManifest":
        """从字典反序列化"""
        def parse_dt(s: Optional[str]) -> Optional[datetime]:
            return datetime.fromisoformat(s) if s else None

        artifacts = [
            ArtifactMetadata.from_dict(a) for a in data.get("artifacts", [])
        ]

        return cls(
            run_id=data["run_id"],
            workflow_id=data.get("workflow_id"),
            department=data.get("department"),
            status=data.get("status", "running"),
            artifacts=artifacts,
            started_at=parse_dt(data.get("started_at")) or datetime.now(),
            completed_at=parse_dt(data.get("completed_at")),
            executor=data.get("executor"),
            executor_version=data.get("executor_version"),
            parent_run_id=data.get("parent_run_id"),
            root_run_id=data.get("root_run_id"),
            input_artifacts=data.get("input_artifacts", []),
            ssot_root=data.get("ssot_root"),
            handover_to=data.get("handover_to"),
            handover_artifacts=data.get("handover_artifacts", []),
            properties=data.get("properties", {}),
        )

    def to_yaml(self) -> str:
        """导出为 YAML 格式"""
        import yaml

        return yaml.dump(self.to_dict(), allow_unicode=True, sort_keys=False)

    @classmethod
    def from_yaml(cls, yaml_content: str) -> "RunManifest":
        """从 YAML 内容加载"""
        import yaml

        data = yaml.safe_load(yaml_content)
        return cls.from_dict(data)

    def save(self, path: Optional[Path] = None) -> None:
        """保存到文件"""
        target_path = path or self.manifest_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(self.to_yaml(), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "RunManifest":
        """从文件加载"""
        content = path.read_text(encoding="utf-8")
        return cls.from_yaml(content)
