"""
Artifact Registry

产出物注册表 - 所有产出物的索引缓存。

权威源说明:
- Manifest 是权威数据源 (每个 run 一个 manifest.yaml)
- Registry 是从 Manifest 重建的缓存索引
- Registry 损坏可以重建，但 Manifest 损坏则数据丢失

SSOT v1.3 扩展:
- 支持 SSOT 对象 (新 ID 格式) 和 Legacy ART 对象分开索引
- 新增 parent_index, path_index, relation_index
"""

import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import ArtifactMetadata, RunManifest

# Windows 兼容性：fcntl 不可用
if sys.platform != "win32":
    import fcntl


# SSOT ID 前缀 (新系统)
SSOT_PREFIXES = {"SRC", "EPIC", "FEAT", "UI", "TECH", "TASK", "TESTSET", "TC", "BUG", "REPORT", "ADR", "EVI"}

# Legacy ART 前缀 (旧系统)
LEGACY_PREFIX = "ART"


class ArtifactRegistry:
    """
    产出物注册表

    维护所有产出物的索引，提供快速查询功能。
    Registry 可以从所有 manifest.yaml 重建。

    SSOT v1.3 扩展:
    - 支持 SSOT 对象和 Legacy ART 对象分开索引
    - 新增 parent_index, path_index, relation_index
    """

    def __init__(self, root_path: Optional[Path] = None):
        """
        初始化注册表

        Args:
            root_path: .artifacts/ 根目录，默认为当前工作目录下的 .artifacts/
        """
        self.root_path = root_path or (Path.cwd() / ".artifacts")
        self.registry_file = self.root_path / ".registry.json"
        self.lock_file = self.root_path / ".registry.lock"

        # 内存索引
        self._artifacts: Dict[str, ArtifactMetadata] = {}  # id -> metadata
        self._by_run: Dict[str, Set[str]] = {}  # run_id -> artifact ids
        self._by_type: Dict[str, Set[str]] = {}  # type -> artifact ids
        self._by_category: Dict[str, Set[str]] = {}  # category -> artifact ids
        self._by_status: Dict[str, Set[str]] = {}  # status -> artifact ids
        self._by_department: Dict[str, Set[str]] = {}  # department -> artifact ids

        # SSOT v1.3 新增索引
        # 分开索引：SSOT vs Legacy
        self._ssot_artifacts: Dict[str, ArtifactMetadata] = {}  # SSOT 对象
        self._legacy_artifacts: Dict[str, ArtifactMetadata] = {}  # Legacy ART 对象

        # parent_id 索引
        self._by_parent: Dict[str, Set[str]] = {}  # parent_id -> artifact ids

        # path 索引
        self._by_path: Dict[str, str] = {}  # path -> artifact_id

        # 关系索引 (简化版：合并 derived_from, related_ids, verifies, implements)
        self._relations: Dict[str, Set[str]] = {}  # artifact_id -> related_ids

        # 元数据
        self._last_rebuilt: Optional[datetime] = None
        self._manifest_version: Optional[str] = None

    def _is_ssot_id(self, artifact_id: str) -> bool:
        """判断是否为 SSOT ID"""
        prefix = artifact_id.split("-")[0].upper()
        return prefix in SSOT_PREFIXES

    def _is_legacy_id(self, artifact_id: str) -> bool:
        """判断是否为 Legacy ART ID"""
        return artifact_id.startswith(LEGACY_PREFIX + "-")

    def acquire_lock(self) -> bool:
        """获取文件锁"""
        try:
            # 确保父目录存在
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_fd = open(self.lock_file, "w")
            # Windows 不支持 fcntl，跳过文件锁
            if sys.platform != "win32":
                fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
            return True
        except Exception:
            return False

    def release_lock(self) -> None:
        """释放文件锁"""
        try:
            if hasattr(self, "lock_fd"):
                # Windows 不支持 fcntl，跳过文件锁
                if sys.platform != "win32":
                    fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_UN)
                self.lock_fd.close()
        except Exception:
            pass

    def rebuild(self) -> None:
        """
        从所有 manifest.yaml 重建注册表

        这是权威的重建方法，扫描所有 manifest 文件并重建索引。
        """
        if not self.acquire_lock():
            raise RuntimeError("Failed to acquire registry lock")

        try:
            # 清空当前索引
            self._artifacts.clear()
            self._by_run.clear()
            self._by_type.clear()
            self._by_category.clear()
            self._by_status.clear()
            self._by_department.clear()

            # 清空 SSOT v1.3 新增索引
            self._ssot_artifacts.clear()
            self._legacy_artifacts.clear()
            self._by_parent.clear()
            self._by_path.clear()
            self._relations.clear()

            # 扫描所有 manifest 文件
            active_dir = self.root_path / "active"
            if active_dir.exists():
                self._scan_manifests(active_dir)

            frozen_dir = self.root_path / "frozen"
            if frozen_dir.exists():
                self._scan_manifests(frozen_dir)

            archive_dir = self.root_path / "archive"
            if archive_dir.exists():
                self._scan_manifests(archive_dir)

            self._last_rebuilt = datetime.now()
            self._save()
        finally:
            self.release_lock()

    def _scan_manifests(self, scan_dir: Path) -> None:
        """扫描目录下的所有 manifest 文件"""
        for manifest_file in scan_dir.rglob("manifest.yaml"):
            try:
                manifest = RunManifest.load(manifest_file)
                self._index_manifest(manifest)
            except Exception as e:
                # 记录错误但继续扫描
                print(f"Warning: Failed to load manifest {manifest_file}: {e}")

    def _index_manifest(self, manifest: RunManifest) -> None:
        """将 manifest 中的产出物加入索引"""
        for artifact in manifest.artifacts:
            self._add_to_index(artifact)

    def _add_to_index(self, artifact: ArtifactMetadata) -> None:
        """添加产出物到索引"""
        # 主索引
        self._artifacts[artifact.id] = artifact

        # SSOT v1.3: 分开索引 SSOT/Legacy
        if self._is_ssot_id(artifact.id):
            self._ssot_artifacts[artifact.id] = artifact
        elif self._is_legacy_id(artifact.id):
            self._legacy_artifacts[artifact.id] = artifact
        else:
            # 未知类型，也放入主索引
            pass

        # 按run索引
        if artifact.run_id not in self._by_run:
            self._by_run[artifact.run_id] = set()
        self._by_run[artifact.run_id].add(artifact.id)

        # 按类型索引
        type_key = artifact.type.value
        if type_key not in self._by_type:
            self._by_type[type_key] = set()
        self._by_type[type_key].add(artifact.id)

        # 按类别索引
        if artifact.category not in self._by_category:
            self._by_category[artifact.category] = set()
        self._by_category[artifact.category].add(artifact.id)

        # 按状态索引
        status_key = artifact.status.value
        if status_key not in self._by_status:
            self._by_status[status_key] = set()
        self._by_status[status_key].add(artifact.id)

        # 按部门索引
        if artifact.department:
            if artifact.department not in self._by_department:
                self._by_department[artifact.department] = set()
            self._by_department[artifact.department].add(artifact.id)

        # SSOT v1.3 新增索引
        # parent_id 索引 (SSOT 记录存储在 properties 中)
        parent_id = artifact.properties.get("parent_id")
        if parent_id:
            if parent_id not in self._by_parent:
                self._by_parent[parent_id] = set()
            self._by_parent[parent_id].add(artifact.id)

        # path 索引
        if artifact.path:
            self._by_path[artifact.path] = artifact.id

        # 关系索引 (简化版：合并 derived_from, related_ids, verifies, implements)
        related_ids = set()
        if artifact.derived_from:
            related_ids.add(artifact.derived_from)
        related_ids.update(artifact.properties.get("derived_from_ids", []))
        related_ids.update(artifact.properties.get("related_ids", []))
        if artifact.verifies:
            related_ids.update(artifact.verifies)
        if artifact.implements:
            related_ids.update(artifact.implements)

        if related_ids:
            self._relations[artifact.id] = related_ids

    def register(self, artifact: ArtifactMetadata) -> None:
        """
        注册新的产出物

        通常由 ArtifactManager.create() 调用。
        """
        if not self.acquire_lock():
            raise RuntimeError("Failed to acquire registry lock")

        try:
            self._add_to_index(artifact)
            self._save()
        finally:
            self.release_lock()

    def update(self, artifact: ArtifactMetadata) -> None:
        """更新产出物元数据"""
        if not self.acquire_lock():
            raise RuntimeError("Failed to acquire registry lock")

        try:
            if artifact.id not in self._artifacts:
                raise KeyError(f"Artifact {artifact.id} not found in registry")

            # 移除旧索引
            self._remove_from_index(artifact.id)
            # 添加新索引
            self._add_to_index(artifact)
            self._save()
        finally:
            self.release_lock()

    def _remove_from_index(self, artifact_id: str) -> None:
        """从索引中移除产出物"""
        if artifact_id not in self._artifacts:
            return

        artifact = self._artifacts[artifact_id]

        if artifact_id in self._ssot_artifacts:
            del self._ssot_artifacts[artifact_id]
        if artifact_id in self._legacy_artifacts:
            del self._legacy_artifacts[artifact_id]

        # 从各索引中移除
        if artifact.run_id in self._by_run:
            self._by_run[artifact.run_id].discard(artifact_id)

        type_key = artifact.type.value
        if type_key in self._by_type:
            self._by_type[type_key].discard(artifact_id)

        if artifact.category in self._by_category:
            self._by_category[artifact.category].discard(artifact_id)

        status_key = artifact.status.value
        if status_key in self._by_status:
            self._by_status[status_key].discard(artifact_id)

        if artifact.department and artifact.department in self._by_department:
            self._by_department[artifact.department].discard(artifact_id)

        parent_id = artifact.properties.get("parent_id")
        if parent_id in self._by_parent:
            self._by_parent[parent_id].discard(artifact_id)
            if not self._by_parent[parent_id]:
                del self._by_parent[parent_id]

        if artifact.path and self._by_path.get(artifact.path) == artifact_id:
            del self._by_path[artifact.path]

        self._relations.pop(artifact_id, None)

        del self._artifacts[artifact_id]

    def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """获取产出物元数据"""
        return self._artifacts.get(artifact_id)

    def get_by_run(self, run_id: str) -> List[ArtifactMetadata]:
        """获取指定 run 的所有产出物"""
        ids = self._by_run.get(run_id, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

    def get_by_run_id(self, run_id: str) -> List[ArtifactMetadata]:
        """获取指定 run 的所有产出物（别名方法）"""
        return self.get_by_run(run_id)

    def list_all(self) -> List[ArtifactMetadata]:
        """获取所有产出物"""
        return list(self._artifacts.values())

    def unregister(self, artifact_id: str) -> bool:
        """
        从注册表中注销产出物

        Args:
            artifact_id: 产出物 ID

        Returns:
            是否成功注销
        """
        if not self.acquire_lock():
            raise RuntimeError("Failed to acquire registry lock")

        try:
            if artifact_id not in self._artifacts:
                return False

            self._remove_from_index(artifact_id)
            self._save()
            return True
        finally:
            self.release_lock()

    def rebuild_from_disk(self, artifacts_root: Path) -> int:
        """
        从磁盘重建注册表

        扫描所有 manifest.yaml 文件，重建完整索引。
        这是"救命/修复"工具，当 registry 损坏时使用。

        Args:
            artifacts_root: .artifacts/ 根目录

        Returns:
            重建的 artifact 数量
        """
        self.root_path = artifacts_root
        self.registry_file = artifacts_root / ".registry.json"
        self.lock_file = artifacts_root / ".registry.lock"

        self.rebuild()
        return len(self._artifacts)

    def get_by_type(self, artifact_type: str) -> List[ArtifactMetadata]:
        """获取指定类型的所有产出物"""
        ids = self._by_type.get(artifact_type, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

    def get_by_category(self, category: str) -> List[ArtifactMetadata]:
        """获取指定类别的所有产出物"""
        ids = self._by_category.get(category, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

    def get_by_status(self, status: str) -> List[ArtifactMetadata]:
        """获取指定状态的所有产出物"""
        ids = self._by_status.get(status, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

    def get_by_department(self, department: str) -> List[ArtifactMetadata]:
        """获取指定部门的所有产出物"""
        ids = self._by_department.get(department, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

    def find_references_to(self, artifact_id: str) -> List[ArtifactMetadata]:
        """
        查找引用指定产出物的其他产出物

        用于引用保护机制。
        """
        references = []
        for artifact in self._artifacts.values():
            if (
                artifact_id in artifact.depends_on
                or artifact.derived_from == artifact_id
                or artifact_id in artifact.consumed_by
            ):
                references.append(artifact)
        return references

    # =========================================================================
    # SSOT v1.3 新增查询方法
    # =========================================================================

    def get_ssot_artifacts(self) -> List[ArtifactMetadata]:
        """获取所有 SSOT 对象"""
        return list(self._ssot_artifacts.values())

    def get_legacy_artifacts(self) -> List[ArtifactMetadata]:
        """获取所有 Legacy ART 对象"""
        return list(self._legacy_artifacts.values())

    def is_ssot_id(self, artifact_id: str) -> bool:
        """判断 ID 是否为 SSOT 对象"""
        return artifact_id in self._ssot_artifacts

    def is_legacy_id(self, artifact_id: str) -> bool:
        """判断 ID 是否为 Legacy ART 对象"""
        return artifact_id in self._legacy_artifacts

    def get_by_parent(self, parent_id: str) -> List[ArtifactMetadata]:
        """获取指定 parent_id 的所有子对象"""
        ids = self._by_parent.get(parent_id, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

    def get_by_path(self, path: str) -> Optional[ArtifactMetadata]:
        """根据路径获取产出物"""
        artifact_id = self._by_path.get(path)
        if artifact_id:
            return self._artifacts.get(artifact_id)
        return None

    def get_related(self, artifact_id: str) -> List[ArtifactMetadata]:
        """获取与指定对象相关的所有对象"""
        related_ids = self._relations.get(artifact_id, set())
        result = []
        for rid in related_ids:
            artifact = self._artifacts.get(rid)
            if artifact:
                result.append(artifact)
        return result

    def exists(self, artifact_id: str) -> bool:
        """检查 artifact 是否存在"""
        return artifact_id in self._artifacts

    def _save(self) -> None:
        """保存注册表到磁盘"""
        data = {
            "version": "2.1.0",
            "last_rebuilt": self._last_rebuilt.isoformat() if self._last_rebuilt else None,
            "artifacts": {id: artifact.to_dict() for id, artifact in self._artifacts.items()},
        }

        # 原子写入
        temp_file = self.registry_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_file.replace(self.registry_file)

    def load(self) -> None:
        """从磁盘加载注册表"""
        if not self.registry_file.exists():
            self.rebuild()
            return

        data = json.loads(self.registry_file.read_text(encoding="utf-8"))

        self._artifacts.clear()
        self._by_run.clear()
        self._by_type.clear()
        self._by_category.clear()
        self._by_status.clear()
        self._by_department.clear()

        for artifact_data in data.get("artifacts", {}).values():
            artifact = ArtifactMetadata.from_dict(artifact_data)
            self._add_to_index(artifact)

        self._last_rebuilt = (
            datetime.fromisoformat(data["last_rebuilt"]) if data.get("last_rebuilt") else None
        )

    def validate_integrity(self) -> bool:
        """
        验证注册表完整性

        检查所有产出物文件是否存在。
        """
        for artifact in self._artifacts.values():
            if not artifact.exists:
                print(f"Missing artifact: {artifact.id} at {artifact.path}")
                return False
        return True

    def get_statistics(self) -> Dict:
        """获取统计信息"""
        return {
            "total_artifacts": len(self._artifacts),
            "by_type": {k: len(v) for k, v in self._by_type.items()},
            "by_status": {k: len(v) for k, v in self._by_status.items()},
            "by_category": {k: len(v) for k, v in self._by_category.items()},
            "by_department": {k: len(v) for k, v in self._by_department.items()},
            "total_runs": len(self._by_run),
            "last_rebuilt": self._last_rebuilt.isoformat() if self._last_rebuilt else None,
        }
