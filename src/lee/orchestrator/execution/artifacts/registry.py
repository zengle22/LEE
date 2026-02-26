"""
Artifact Registry

产出物注册表 - 所有产出物的索引缓存。

权威源说明:
- Manifest 是权威数据源 (每个 run 一个 manifest.yaml)
- Registry 是从 Manifest 重建的缓存索引
- Registry 损坏可以重建，但 Manifest 损坏则数据丢失
"""

import fcntl
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Set

from .models import ArtifactMetadata, RunManifest


class ArtifactRegistry:
    """
    产出物注册表

    维护所有产出物的索引，提供快速查询功能。
    Registry 可以从所有 manifest.yaml 重建。
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

        # 元数据
        self._last_rebuilt: Optional[datetime] = None
        self._manifest_version: Optional[str] = None

    def acquire_lock(self) -> bool:
        """获取文件锁"""
        try:
            # 确保父目录存在
            self.lock_file.parent.mkdir(parents=True, exist_ok=True)
            self.lock_fd = open(self.lock_file, "w")
            fcntl.flock(self.lock_fd.fileno(), fcntl.LOCK_EX)
            return True
        except Exception:
            return False

    def release_lock(self) -> None:
        """释放文件锁"""
        try:
            if hasattr(self, "lock_fd"):
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

        del self._artifacts[artifact_id]

    def get(self, artifact_id: str) -> Optional[ArtifactMetadata]:
        """获取产出物元数据"""
        return self._artifacts.get(artifact_id)

    def get_by_run(self, run_id: str) -> List[ArtifactMetadata]:
        """获取指定 run 的所有产出物"""
        ids = self._by_run.get(run_id, set())
        return [self._artifacts[id] for id in ids if id in self._artifacts]

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
