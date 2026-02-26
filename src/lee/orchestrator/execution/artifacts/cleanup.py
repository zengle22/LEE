"""
Artifact Cleanup Management

产出物清理管理 - 处理过期产出物的清理和归档。
支持引用保护机制，防止误删仍被引用的产出物。
"""

import logging
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

from .manager import ArtifactManager
from .manifest import ManifestManager
from .models import ArtifactMetadata, RunManifest
from .types import ArtifactStatus

logger = logging.getLogger(__name__)


class CleanupPolicy:
    """
    清理策略配置

    从 config.yaml 读取保留策略
    """

    # 默认保留天数
    DEFAULT_RETENTION_DAYS = {
        "draft": 7,
        "active": 30,
        "intermediate": 3,
        "archived": 365,
        "frozen": None,  # 永久保留
        "log": 90,
    }

    @classmethod
    def get_max_age_days(cls, status: str) -> Optional[int]:
        """获取指定状态的保留天数"""
        return cls.DEFAULT_RETENTION_DAYS.get(status)

    @classmethod
    def should_delete(
        cls,
        artifact: ArtifactMetadata,
        max_age_days: int,
    ) -> bool:
        """
        判断产出物是否应该删除

        Args:
            artifact: 产出物元数据
            max_age_days: 最大保留天数

        Returns:
            是否应该删除
        """
        # FROZEN 状态永远不删除
        if artifact.status == ArtifactStatus.FROZEN:
            return False

        if max_age_days is None:
            return False

        cutoff_date = datetime.now() - timedelta(days=max_age_days)
        return artifact.created_at < cutoff_date


class ArtifactCleaner:
    """
    产出物清理器

    带引用保护的清理机制：
    1. 扫描所有 RunManifest，构建被引用 artifact_id 集合
    2. 扫描所有 Handover，构建被交接 artifact_id 集合
    3. 候选删除集合中，排除被引用的 ID
    4. 只删除未被引用的产出物
    """

    def __init__(
        self,
        artifacts_root: Path,
        manager: Optional[ArtifactManager] = None,
    ):
        """
        初始化

        Args:
            artifacts_root: .artifacts/ 根目录
            manager: 可选的共享 ArtifactManager
        """
        self.artifacts_root = Path(artifacts_root)

        if manager:
            self.manager = manager
        else:
            self.manager = ArtifactManager(self.artifacts_root)

        self.manifest_manager = ManifestManager(self.artifacts_root, self.manager.registry)

    def find_cleanup_candidates(
        self,
        status: Optional[str] = None,
        max_age_days: Optional[int] = None,
        department: Optional[str] = None,
    ) -> List[ArtifactMetadata]:
        """
        查找清理候选产出物

        Args:
            status: 筛选状态
            max_age_days: 最大保留天数
            department: 筛选部门

        Returns:
            候选产出物列表
        """
        candidates = []

        # 获取所有产出物
        all_artifacts = self.manager.registry.list_all()

        for artifact in all_artifacts:
            # 状态筛选
            if status and artifact.status.value != status:
                continue

            # 部门筛选
            if department and artifact.department != department:
                continue

            # FROZEN 状态跳过
            if artifact.status == ArtifactStatus.FROZEN:
                continue

            # 年龄筛选
            if max_age_days:
                if not CleanupPolicy.should_delete(artifact, max_age_days):
                    continue
            else:
                # 使用默认策略
                status_name = artifact.status.value
                default_max = CleanupPolicy.get_max_age_days(status_name)
                if default_max and not CleanupPolicy.should_delete(artifact, default_max):
                    continue

            candidates.append(artifact)

        return candidates

    def build_reference_set(self) -> Set[str]:
        """
        构建被引用的 artifact_id 集合

        扫描所有 manifest，提取所有被引用的 artifact ID

        Returns:
            被引用的 ID 集合
        """
        referenced = set()

        # 扫描所有 manifest.yaml
        manifest_dir = self.artifacts_root / "active"
        if manifest_dir.exists():
            for manifest_path in manifest_dir.rglob("manifest.yaml"):
                try:
                    with open(manifest_path, 'r', encoding='utf-8') as f:
                        import yaml
                        data = yaml.safe_load(f)
                        if data and "artifacts" in data:
                            # artifacts 是一个 list，每个元素是一个 dict 包含 id
                            artifacts = data["artifacts"]
                            if isinstance(artifacts, list):
                                for artifact in artifacts:
                                    if isinstance(artifact, dict) and "id" in artifact:
                                        referenced.add(artifact["id"])
                            elif isinstance(artifacts, dict):
                                # 如果是 dict，使用 keys
                                for artifact_id in artifacts.keys():
                                    referenced.add(artifact_id)
                except Exception as e:
                    logger.warning(f"Failed to parse manifest {manifest_path}: {e}")

        return referenced

    def clean(
        self,
        status: Optional[str] = None,
        max_age_days: Optional[int] = None,
        department: Optional[str] = None,
        dry_run: bool = True,
        enable_reference_protection: bool = True,
    ) -> Dict[str, Any]:
        """
        清理过期产出物

        Args:
            status: 筛选状态
            max_age_days: 最大保留天数
            department: 筛选部门
            dry_run: 是否模拟运行
            enable_reference_protection: 是否启用引用保护

        Returns:
            清理结果统计
        """
        # 获取候选删除集合
        candidates = self.find_cleanup_candidates(status, max_age_days, department)

        # 引用保护
        protected_ids = set()
        if enable_reference_protection:
            protected_ids = self.build_reference_set()

        # 过滤被引用的产出物
        safe_to_delete = [
            a for a in candidates
            if a.id not in protected_ids
        ]

        protected = [
            a for a in candidates
            if a.id in protected_ids
        ]

        # 执行清理
        deleted = []
        if not dry_run:
            for artifact in safe_to_delete:
                try:
                    self._delete_artifact(artifact)
                    deleted.append(artifact.id)
                except Exception as e:
                    logger.error(f"Failed to delete {artifact.id}: {e}")

        return {
            "candidates": len(candidates),
            "protected": len(protected),
            "deleted": len(deleted) if not dry_run else len(safe_to_delete),
            "dry_run": dry_run,
            "candidate_ids": [a.id for a in candidates],
            "protected_ids": [a.id for a in protected],
            "deleted_ids": deleted,
        }

    def _delete_artifact(self, artifact: ArtifactMetadata) -> None:
        """
        删除产出物

        同时删除：
        1. 物理文件
        2. Registry 条目
        """
        # 删除物理文件
        if artifact.path:
            file_path = self.artifacts_root / artifact.path
            if file_path.exists():
                if file_path.is_file():
                    file_path.unlink()
                elif file_path.is_dir():
                    shutil.rmtree(file_path)

        # 从 registry 删除
        self.manager.registry.unregister(artifact.id)

        logger.info(f"Deleted artifact: {artifact.id}")

    def clean_intermediate(
        self,
        run_id: str,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        清理指定 run 的中间产物

        Args:
            run_id: Run ID
            dry_run: 是否模拟运行

        Returns:
            清理结果
        """
        # 查找该 run 的所有 INTERMEDIATE 产出物
        intermediate_artifacts = [
            a for a in self.manager.registry.get_by_run_id(run_id)
            if a.type.value == "INTERMEDIATE"
        ]

        deleted = []
        if not dry_run:
            for artifact in intermediate_artifacts:
                try:
                    self._delete_artifact(artifact)
                    deleted.append(artifact.id)
                except Exception as e:
                    logger.error(f"Failed to delete {artifact.id}: {e}")

        return {
            "run_id": run_id,
            "count": len(intermediate_artifacts),
            "deleted": len(deleted),
            "deleted_ids": deleted,
            "dry_run": dry_run,
        }

    def archive_old_runs(
        self,
        max_age_days: int = 30,
        dry_run: bool = True,
    ) -> Dict[str, Any]:
        """
        归档旧 run

        将旧 run 移动到 archive/ 目录

        Args:
            max_age_days: 最大保留天数
            dry_run: 是否模拟运行

        Returns:
            归档结果
        """
        archived_runs = []
        cutoff_date = datetime.now() - timedelta(days=max_age_days)

        # 扫描 active 目录
        active_dir = self.artifacts_root / "active"
        if not active_dir.exists():
            return {"archived": 0, "archived_runs": [], "dry_run": dry_run}

        for dept_dir in active_dir.iterdir():
            if not dept_dir.is_dir():
                continue

            for run_dir in dept_dir.iterdir():
                if not run_dir.is_dir():
                    continue

                # 检查 manifest 的完成时间
                manifest_path = run_dir / "manifest.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    import yaml
                    with open(manifest_path, 'r') as f:
                        data = yaml.safe_load(f)
                        completed_at = data.get("completed_at")
                        if not completed_at:
                            continue

                        # 解析日期
                        if isinstance(completed_at, str):
                            from datetime import datetime as dt
                            completed_dt = dt.fromisoformat(completed_at.replace('Z', '+00:00'))
                        else:
                            completed_dt = completed_at

                        if completed_dt < cutoff_date:
                            # 执行归档
                            if not dry_run:
                                archive_path = self.artifacts_root / "archive" / "by-department" / dept_dir.name / run_dir.name
                                archive_path.parent.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(run_dir), str(archive_path))

                            archived_runs.append(str(run_dir.relative_to(self.artifacts_root)))
                except Exception as e:
                    logger.warning(f"Failed to archive {run_dir}: {e}")

        return {
            "archived": len(archived_runs),
            "archived_runs": archived_runs,
            "dry_run": dry_run,
        }


def rebuild_registry(artifacts_root: Path) -> int:
    """
    重建 registry 索引

    从磁盘扫描 .artifacts/，重建 registry/index.json
    这是一种"救命/修复"工具

    Args:
        artifacts_root: .artifacts/ 根目录

    Returns:
        重建的 artifact 数量
    """
    from .manager import ArtifactManager

    manager = ArtifactManager(artifacts_root)
    count = manager.registry.rebuild_from_disk(artifacts_root)

    logger.info(f"Rebuilt registry: {count} artifacts")

    return count
