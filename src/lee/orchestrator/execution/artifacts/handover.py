"""
Handover Management

部门间移交管理 - 处理产出物在部门/阶段间的移交。
"""

import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .manager import ArtifactManager
from .manifest import ManifestManager
from .models import ArtifactMetadata, RunManifest
from .types import ArtifactType

logger = logging.getLogger(__name__)


class HandoverManager:
    """
    移交管理器

    处理产出物在部门/阶段间的移交。
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        artifacts_root: Optional[Path] = None,
        manager: Optional[ArtifactManager] = None,
    ):
        """
        初始化

        Args:
            project_root: 项目根目录
            artifacts_root: .artifacts/ 根目录
            manager: 共享的 ArtifactManager 实例 (可选)
        """
        self.project_root = (project_root or Path.cwd()).resolve()

        if artifacts_root:
            self.artifacts_root = artifacts_root
        elif self.project_root.name == ".artifacts":
            self.artifacts_root = self.project_root
        else:
            self.artifacts_root = self.project_root / ".artifacts"

        if manager:
            self.manager = manager
        else:
            self.manager = ArtifactManager(self.artifacts_root)

        self.manifest_manager = ManifestManager(self.artifacts_root, self.manager.registry)

    def create_handover(
        self,
        from_run_id: str,
        to_department: str,
        artifact_ids: List[str],
        handover_title: str,
        handover_description: str = "",
        from_department: Optional[str] = None,
    ) -> RunManifest:
        """
        创建移交记录

        Args:
            from_run_id: 源 run ID
            to_department: 目标部门
            artifact_ids: 要移交的产出物 ID 列表
            handover_title: 移交标题
            handover_description: 移交描述
            from_department: 源部门

        Returns:
            更新后的 run manifest
        """
        # 获取源 manifest
        manifest = self.manifest_manager.get(from_run_id, from_department)
        if not manifest:
            raise ValueError(f"Source manifest not found: {from_run_id}")

        # 验证所有产出物存在
        valid_artifacts = []
        for artifact_id in artifact_ids:
            artifact = self.manager.get(artifact_id)
            if not artifact:
                logger.warning(f"Artifact {artifact_id} not found, skipping")
                continue
            valid_artifacts.append(artifact)

        if not valid_artifacts:
            raise ValueError("No valid artifacts to handover")

        # 创建移交产出物
        handover_artifact = self.manager.create(
            artifact_type=ArtifactType.HANDOVER,
            category=f"to_{to_department}",
            content=self._format_handover_content(
                from_run_id, to_department, valid_artifacts,
                handover_title, handover_description
            ),
            run_id=from_run_id,
            title=handover_title,
            description=handover_description,
            department=from_department,
            tags=["handover", f"to-{to_department}"],
        )

        # 更新产出物的 consumed_by
        for artifact in valid_artifacts:
            if to_department not in artifact.consumed_by:
                artifact.consumed_by.append(to_department)
                self.manager.registry.update(artifact)

        # 更新 manifest 的移交信息
        manifest.handover_to = to_department
        manifest.handover_artifacts = [a.id for a in valid_artifacts]
        self.manifest_manager.save(manifest)

        logger.info(
            f"Created handover from {from_run_id} to {to_department}: "
            f"{len(valid_artifacts)} artifacts, handover artifact: {handover_artifact.id}"
        )

        return manifest

    def consume_handover(
        self,
        handover_artifact_id: str,
        to_run_id: str,
        to_department: str,
    ) -> List[ArtifactMetadata]:
        """
        消费移交，将移交的产出物关联到新 run

        Args:
            handover_artifact_id: 移交产出物 ID
            to_run_id: 目标 run ID
            to_department: 目标部门

        Returns:
            被消费的产出物列表
        """
        # 获取移交产出物
        handover = self.manager.get(handover_artifact_id)
        if not handover:
            raise ValueError(f"Handover artifact not found: {handover_artifact_id}")

        if handover.type != ArtifactType.HANDOVER:
            raise ValueError(f"Artifact {handover_artifact_id} is not a handover")

        # 解析移交内容获取 artifact IDs
        artifact_ids = self._parse_handover_content(handover)

        # 验证并获取产出物
        consumed = []
        for artifact_id in artifact_ids:
            artifact = self.manager.get(artifact_id)
            if not artifact:
                logger.warning(f"Artifact {artifact_id} not found, skipping")
                continue

            # 记录消费关系
            if to_run_id not in artifact.consumed_by:
                artifact.consumed_by.append(to_run_id)
                self.manager.registry.update(artifact)

            consumed.append(artifact)

        logger.info(
            f"Consumed handover {handover_artifact_id} for run {to_run_id}: "
            f"{len(consumed)} artifacts"
        )

        return consumed

    def get_pending_handovers(
        self,
        department: str,
    ) -> List[Dict[str, Any]]:
        """
        获取待处理的移交 (指向指定部门的)

        Args:
            department: 目标部门

        Returns:
            待处理的移交列表，每项包含 handover_artifact 和源 run 信息
        """
        pending = []

        # 查找所有 HANDOVER 类型产出物
        handovers = self.manager.registry.get_by_type("HANDOVER")

        for handover in handovers:
            # 检查是否是目标部门的移交
            if handover.category == f"to_{department}":
                # 检查是否已被消费
                if department not in handover.consumed_by:
                    # 获取源 manifest 信息
                    source_manifest = self.manifest_manager.get(handover.run_id, handover.department)
                    pending.append({
                        "handover_artifact": handover,
                        "source_run_id": handover.run_id,
                        "source_department": handover.department,
                        "source_manifest": source_manifest,
                    })

        return pending

    def transfer_artifact(
        self,
        artifact_id: str,
        to_department: str,
        transfer_reason: str = "",
    ) -> ArtifactMetadata:
        """
        转移产出物到另一个部门

        通过创建引用并更新 consumed_by 来实现软转移。

        Args:
            artifact_id: 产出物 ID
            to_department: 目标部门
            transfer_reason: 转移原因

        Returns:
            更新后的产出物元数据
        """
        artifact = self.manager.get(artifact_id)
        if not artifact:
            raise ValueError(f"Artifact not found: {artifact_id}")

        # 添加目标部门到 consumers
        if to_department not in artifact.consumed_by:
            artifact.consumed_by.append(to_department)

        # 添加转移记录
        if "transfers" not in artifact.properties:
            artifact.properties["transfers"] = []

        artifact.properties["transfers"].append({
            "to_department": to_department,
            "reason": transfer_reason,
            "timestamp": datetime.now().isoformat(),
        })

        self.manager.registry.update(artifact)

        logger.info(
            f"Transferred artifact {artifact_id} to {to_department}: {transfer_reason}"
        )

        return artifact

    def get_department_summary(
        self,
        department: str,
    ) -> Dict[str, Any]:
        """
        获取部门的产出物汇总

        Args:
            department: 部门名称

        Returns:
            部门汇总信息
        """
        # 获取部门的所有产出物
        department_artifacts = self.manager.registry.get_by_department(department)

        # 按类型统计
        by_type = {}
        for artifact in department_artifacts:
            type_key = artifact.type.value
            by_type[type_key] = by_type.get(type_key, 0) + 1

        # 获取待处理的移交
        pending_handovers = self.get_pending_handovers(department)

        # 计算产出物总大小
        total_size = sum(
            a.size_bytes for a in department_artifacts
            if a.size_bytes is not None
        )

        return {
            "department": department,
            "total_artifacts": len(department_artifacts),
            "by_type": by_type,
            "total_size_bytes": total_size,
            "pending_handovers": len(pending_handovers),
            "pending_handover_details": [
                {
                    "from_run": h["source_run_id"],
                    "from_department": h["source_department"],
                    "handover_artifact_id": h["handover_artifact"].id,
                    "title": h["handover_artifact"].title,
                }
                for h in pending_handovers
            ],
        }

    def _format_handover_content(
        self,
        from_run_id: str,
        to_department: str,
        artifacts: List[ArtifactMetadata],
        title: str,
        description: str,
    ) -> str:
        """格式化移交内容"""
        lines = [
            f"# {title}",
            "",
            f"**From:** {from_run_id}",
            f"**To:** {to_department}",
            f"**Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
            f"## Description",
            description or "",
            "",
            "## Artifacts",
            "",
        ]

        for artifact in artifacts:
            lines.append(f"- **{artifact.id}** ({artifact.category})")
            if artifact.title:
                lines.append(f"  - {artifact.title}")
            if artifact.description:
                lines.append(f"  - {artifact.description}")

        lines.extend([
            "",
            "---",
            "*This handover was created automatically by LEE Artifact Management System*",
        ])

        return "\n".join(lines)

    def _parse_handover_content(self, handover: ArtifactMetadata) -> List[str]:
        """从移交产出物内容解析 artifact IDs"""
        content = self.manager.get_content(handover.id)
        if not content:
            return []

        # 简单解析：查找 **ART-XXXXX** 模式
        pattern = r"\*\*ART-(\d+)\*\*"
        matches = re.findall(pattern, content)
        return [f"ART-{m}" for m in matches]
