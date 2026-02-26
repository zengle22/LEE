"""
Manifest Manager

Run 级 Manifest 管理 - 每个 run 的权威产出物记录。
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

from .models import ArtifactMetadata, RunManifest
from .registry import ArtifactRegistry
from .types import ArtifactStatus


class ManifestManager:
    """
    Manifest 管理器

    管理每个 run 的 manifest.yaml 文件。
    Manifest 是权威数据源，Registry 从 Manifest 重建。
    """

    def __init__(self, root_path: Optional[Path] = None, registry: Optional[ArtifactRegistry] = None):
        """
        初始化管理器

        Args:
            root_path: .artifacts/ 根目录
            registry: ArtifactRegistry 实例
        """
        self.root_path = root_path or (Path.cwd() / ".artifacts")
        self.registry = registry or ArtifactRegistry(self.root_path)

    def create(
        self,
        run_id: str,
        workflow_id: Optional[str] = None,
        department: Optional[str] = None,
        executor: Optional[str] = None,
        executor_version: Optional[str] = None,
        parent_run_id: Optional[str] = None,
        root_run_id: Optional[str] = None,
    ) -> RunManifest:
        """
        创建新的 run manifest

        Args:
            run_id: run ID
            workflow_id: workflow ID
            department: 所属部门
            executor: 执行器类型
            executor_version: 执行器版本
            parent_run_id: 父 run ID
            root_run_id: 根 run ID

        Returns:
            创建的 RunManifest 对象
        """
        manifest = RunManifest(
            run_id=run_id,
            workflow_id=workflow_id,
            department=department,
            status="running",
            started_at=datetime.now(),
            executor=executor,
            executor_version=executor_version,
            parent_run_id=parent_run_id,
            root_run_id=root_run_id,
        )

        self.save(manifest)
        return manifest

    def get(self, run_id: str, department: Optional[str] = None) -> Optional[RunManifest]:
        """
        获取 run manifest

        Args:
            run_id: run ID
            department: 部门 (可选，用于定位)

        Returns:
            RunManifest 对象，不存在则返回 None
        """
        # 尝试多个路径
        candidates = []

        if department:
            candidates.append(self.root_path / "active" / department / run_id / "manifest.yaml")

        candidates.append(self.root_path / "active" / run_id / "manifest.yaml")
        candidates.append(self.root_path / "frozen" / f"{run_id}.yaml")

        for path in candidates:
            if path.exists():
                return RunManifest.load(path)

        return None

    def save(self, manifest: RunManifest) -> None:
        """保存 manifest"""
        # manifest.manifest_path 返回的是 ".artifacts/active/..."
        # root_path 是 ".artifacts" 目录
        # 需要去掉 manifest_path 中的 ".artifacts" 前缀
        manifest_rel_path = manifest.manifest_path
        if manifest_rel_path.parts[0] == ".artifacts":
            # 去掉 ".artifacts" 前缀
            manifest_rel_path = Path(*manifest_rel_path.parts[1:])
        target_path = self.root_path / manifest_rel_path
        target_path.parent.mkdir(parents=True, exist_ok=True)
        target_path.write_text(manifest.to_yaml(), encoding="utf-8")

    def add_artifact(self, run_id: str, artifact: ArtifactMetadata, department: Optional[str] = None) -> None:
        """
        向 manifest 添加产出物

        Args:
            run_id: run ID
            artifact: 产出物元数据
            department: 部门
        """
        manifest = self.get(run_id, department)
        if manifest is None:
            # 自动创建 manifest
            manifest = self.create(
                run_id=run_id,
                department=department or artifact.department,
            )

        manifest.add_artifact(artifact)
        self.save(manifest)

    def update_status(self, run_id: str, status: str, department: Optional[str] = None) -> None:
        """
        更新 run 状态

        Args:
            run_id: run ID
            status: 新状态 (running, completed, failed, cancelled)
            department: 部门
        """
        manifest = self.get(run_id, department)
        if manifest is None:
            raise ValueError(f"Manifest not found for run: {run_id}")

        manifest.status = status
        if status in ("completed", "failed", "cancelled"):
            manifest.completed_at = datetime.now()

        self.save(manifest)

    def complete(self, run_id: str, department: Optional[str] = None) -> None:
        """标记 run 完成"""
        self.update_status(run_id, "completed", department)

    def fail(self, run_id: str, department: Optional[str] = None) -> None:
        """标记 run 失败"""
        self.update_status(run_id, "failed", department)

    def cancel(self, run_id: str, department: Optional[str] = None) -> None:
        """标记 run 取消"""
        self.update_status(run_id, "cancelled", department)

    def list_runs(
        self,
        status: Optional[str] = None,
        department: Optional[str] = None,
        limit: int = 50,
    ) -> List[RunManifest]:
        """
        列出 run manifest

        Args:
            status: 按状态筛选
            department: 按部门筛选
            limit: 最大返回数量

        Returns:
            RunManifest 列表
        """
        manifests = []
        active_dir = self.root_path / "active"

        if not active_dir.exists():
            return manifests

        # 扫描目录
        scan_dirs = [active_dir]
        if department:
            scan_dirs = [active_dir / department]

        for scan_dir in scan_dirs:
            if not scan_dir.exists():
                continue

            for manifest_file in scan_dir.rglob("manifest.yaml"):
                try:
                    manifest = RunManifest.load(manifest_file)

                    # 状态筛选
                    if status and manifest.status != status:
                        continue

                    # 部门筛选
                    if department and manifest.department != department:
                        continue

                    manifests.append(manifest)
                except Exception:
                    pass

                if len(manifests) >= limit:
                    break

        # 按开始时间倒序排序
        manifests.sort(key=lambda m: m.started_at, reverse=True)
        return manifests

    def freeze_run(self, run_id: str, department: Optional[str] = None) -> RunManifest:
        """
        冻结 run 及其所有产出物

        将 manifest 和所有关联产出物移动到 frozen/ 目录。
        """
        manifest = self.get(run_id, department)
        if manifest is None:
            raise ValueError(f"Manifest not found for run: {run_id}")

        # 更新状态
        manifest.status = "frozen"

        # 冻结所有产出物
        for artifact in manifest.artifacts:
            if artifact.status != ArtifactStatus.FROZEN:
                artifact.status = ArtifactStatus.FROZEN
                artifact.frozen_at = datetime.now()

        # 保存到 frozen/
        frozen_path = self.root_path / "frozen" / f"{run_id}.yaml"
        frozen_path.parent.mkdir(parents=True, exist_ok=True)
        frozen_path.write_text(manifest.to_yaml(), encoding="utf-8")

        # 删除原 manifest (去掉 ".artifacts" 前缀)
        manifest_rel_path = manifest.manifest_path
        if manifest_rel_path.parts[0] == ".artifacts":
            manifest_rel_path = Path(*manifest_rel_path.parts[1:])
        old_manifest_path = self.root_path / manifest_rel_path
        if old_manifest_path.exists():
            old_manifest_path.unlink()

        return manifest

    def get_handover_artifacts(self, run_id: str, department: Optional[str] = None) -> List[ArtifactMetadata]:
        """
        获取 run 的移交产出物

        Returns:
            标记为移交的产出物列表
        """
        manifest = self.get(run_id, department)
        if manifest is None:
            return []

        handover_ids = set(manifest.handover_artifacts)
        return [a for a in manifest.artifacts if a.id in handover_ids]

    def set_handover(
        self,
        run_id: str,
        handover_to: str,
        artifact_ids: List[str],
        department: Optional[str] = None,
    ) -> None:
        """
        设置 run 的移交信息

        Args:
            run_id: run ID
            handover_to: 移交目标 (部门或阶段)
            artifact_ids: 移交的产出物 ID 列表
            department: 部门
        """
        manifest = self.get(run_id, department)
        if manifest is None:
            raise ValueError(f"Manifest not found for run: {run_id}")

        manifest.handover_to = handover_to
        manifest.handover_artifacts = artifact_ids

        # 更新产出物的 consumed_by
        for artifact in manifest.artifacts:
            if artifact.id in artifact_ids:
                if handover_to not in artifact.consumed_by:
                    artifact.consumed_by.append(handover_to)

        self.save(manifest)

    def get_statistics(self, run_id: str, department: Optional[str] = None) -> Dict:
        """
        获取 run 的统计信息

        Returns:
            统计信息字典
        """
        manifest = self.get(run_id, department)
        if manifest is None:
            return {}

        artifacts = manifest.artifacts

        stats = {
            "run_id": run_id,
            "status": manifest.status,
            "total_artifacts": len(artifacts),
            "by_type": {},
            "by_status": {},
            "by_category": {},
            "total_size_bytes": 0,
        }

        for artifact in artifacts:
            # 按类型统计
            type_key = artifact.type.value
            stats["by_type"][type_key] = stats["by_type"].get(type_key, 0) + 1

            # 按状态统计
            status_key = artifact.status.value
            stats["by_status"][status_key] = stats["by_status"].get(status_key, 0) + 1

            # 按类别统计
            stats["by_category"][artifact.category] = (
                stats["by_category"].get(artifact.category, 0) + 1
            )

            # 总大小
            if artifact.size_bytes:
                stats["total_size_bytes"] += artifact.size_bytes

        return stats

    def cleanup_old_runs(
        self,
        max_age_days: int = 90,
        status: str = "completed",
        department: Optional[str] = None,
        dry_run: bool = False,
    ) -> List[str]:
        """
        清理旧的 run manifest

        Args:
            max_age_days: 最大保留天数
            status: 只清理指定状态的 run
            department: 部门筛选
            dry_run: 仅报告不实际删除

        Returns:
            被清理的 run_id 列表
        """
        import time

        cutoff_time = time.time() - (max_age_days * 86400)
        cleaned_runs = []

        runs = self.list_runs(status=status, department=department, limit=1000)

        for run in runs:
            run_timestamp = run.started_at.timestamp()
            if run_timestamp < cutoff_time:
                if dry_run:
                    print(f"Would cleanup run: {run.run_id}")
                else:
                    # 删除 manifest 文件 (去掉 ".artifacts" 前缀)
                    manifest_rel_path = run.manifest_path
                    if manifest_rel_path.parts[0] == ".artifacts":
                        manifest_rel_path = Path(*manifest_rel_path.parts[1:])
                    manifest_path = self.root_path / manifest_rel_path
                    if manifest_path.exists():
                        manifest_path.unlink()

                    # 删除产出物目录 (去掉 ".artifacts" 前缀)
                    artifacts_rel_path = run.artifacts_dir
                    if artifacts_rel_path.parts[0] == ".artifacts":
                        artifacts_rel_path = Path(*artifacts_rel_path.parts[1:])
                    artifacts_dir = self.root_path / artifacts_rel_path
                    if artifacts_dir.exists():
                        import shutil
                        shutil.rmtree(artifacts_dir)

                cleaned_runs.append(run.run_id)

        return cleaned_runs
