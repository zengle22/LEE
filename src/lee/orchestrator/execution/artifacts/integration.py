"""
Artifact Integration

将产出物系统与 LEE 工作流集成的桥接模块。

主要功能:
1. FileOutputHandler 桥接: 自动将工作流产出物注册到系统
2. Gate 集成: 门禁审批时自动冻结相关产出物
3. Run 完成处理: 自动归档 manifest
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .manager import ArtifactManager
from .manifest import ManifestManager
from .models import ArtifactMetadata
from .types import ArtifactType, ArtifactCategoryRegistry

logger = logging.getLogger(__name__)


class ArtifactFileOutputHandler:
    """
    文件输出处理器的产出物系统集成

    拦截 FileOutputHandler 的写入操作，自动创建产出物记录。
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        run_id: Optional[str] = None,
        workflow_id: Optional[str] = None,
        department: Optional[str] = None,
        enabled: bool = True,
    ):
        """
        初始化

        Args:
            project_root: 项目根目录
            run_id: 当前 run ID
            workflow_id: 当前 workflow ID
            department: 当前部门
            enabled: 是否启用自动注册
        """
        self.project_root = (project_root or Path.cwd()).resolve()
        self.run_id = run_id
        self.workflow_id = workflow_id
        self.department = department
        self.enabled = enabled

        # artifacts_root 是 .artifacts 目录的路径
        # 如果 project_root 本身就是 .artifacts，直接使用
        if self.project_root.name == ".artifacts":
            artifacts_root = self.project_root
        else:
            artifacts_root = self.project_root / ".artifacts"

        self.manager = ArtifactManager(artifacts_root)
        self.manifest_manager = ManifestManager(artifacts_root, self.manager.registry)

        # 确保 manifest 存在
        if run_id:
            self._ensure_manifest()

        # 已注册的文件路径 (避免重复)
        self._registered_paths: set[str] = set()

    def _ensure_manifest(self) -> None:
        """确保 manifest 存在"""
        manifest = self.manifest_manager.get(self.run_id, self.department)
        if not manifest:
            self.manifest_manager.create(
                run_id=self.run_id,
                workflow_id=self.workflow_id,
                department=self.department,
            )

    def _infer_artifact_type(self, file_path: str, content: str) -> ArtifactType:
        """
        从文件路径和内容推断产出物类型

        优先级检查顺序: PATCH > LOG > CONTRACT > TEST > DOCUMENT
        """
        path_lower = file_path.lower()

        # 补丁类文件 (最高优先级，因为有明确扩展名)
        if ".patch" in path_lower or ".diff" in path_lower:
            return ArtifactType.PATCH

        # 日志类文件
        if ".log" in path_lower or "/log/" in path_lower:
            return ArtifactType.LOG

        # 契约类文件
        contract_keywords = ["contract", "prd", "requirement", "api", "openapi", "swagger"]
        if any(kw in path_lower for kw in contract_keywords):
            return ArtifactType.CONTRACT

        # 测试类文件 (排除 test_plan 这种契约类)
        if "test" in path_lower and "test_plan" not in path_lower:
            return ArtifactType.TEST

        # 文档类文件 (默认)
        return ArtifactType.DOCUMENT

    def _infer_category(self, artifact_type: ArtifactType, file_path: str) -> str:
        """推断产出物类别"""
        filename = Path(file_path).name.lower()

        # 根据类型和文件名推断具体类别
        if artifact_type == ArtifactType.CONTRACT:
            if "prd" in filename or "requirement" in filename:
                return "frozen_prd"
            elif "api" in filename or "openapi" in filename or "swagger" in filename:
                return "api_contract"
            elif "test" in filename and "plan" in filename:
                return "test_plan"
            else:
                return "design_doc"

        elif artifact_type == ArtifactType.DOCUMENT:
            if "readme" in filename:
                return "readme"
            elif "guide" in filename or "manual" in filename:
                return "usage_guide"
            elif "investigation" in filename:
                return "investigation_report"
            elif "handover" in filename:
                return "handover_doc"
            else:
                return "readme"

        elif artifact_type == ArtifactType.TEST:
            if "report" in filename:
                return "test_report"
            elif "coverage" in filename:
                return "coverage_report"
            else:
                return "test_case"

        elif artifact_type == ArtifactType.PATCH:
            if "feature" in filename:
                return "feature_patch"
            elif "bugfix" in filename or "fix" in filename:
                return "bugfix_patch"
            else:
                return "refactor_patch"

        elif artifact_type == ArtifactType.LOG:
            if "error" in filename:
                return "error_log"
            elif "debug" in filename:
                return "debug_log"
            else:
                return "execution_log"

        # 默认类别
        return "readme"

    def register_file(
        self,
        file_path: str,
        content: Optional[str] = None,
        title: Optional[str] = None,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
    ) -> Optional[ArtifactMetadata]:
        """
        注册文件为产出物

        Args:
            file_path: 文件路径 (绝对或相对路径)
            content: 文件内容 (可选，如不提供则读取文件)
            title: 标题
            description: 描述
            tags: 标签

        Returns:
            创建的产出物元数据，如果未启用则返回 None
        """
        if not self.enabled or not self.run_id:
            return None

        # 标准化路径
        path = Path(file_path)
        if not path.is_absolute():
            path = self.project_root / path

        # 检查是否已注册
        path_str = str(path)
        if path_str in self._registered_paths:
            return None

        if not path.exists():
            return None

        # 读取内容 (如果未提供)
        if content is None:
            try:
                content = path.read_text(encoding="utf-8")
            except Exception:
                # 非文本文件，跳过
                return None

        # 推断类型和类别
        try:
            rel_path = path.relative_to(self.project_root)
        except ValueError:
            # 文件不在 project_root 下，使用文件名
            rel_path = path
        artifact_type = self._infer_artifact_type(str(rel_path), content)
        category = self._infer_category(artifact_type, str(rel_path))

        # 验证类别
        if not ArtifactCategoryRegistry.is_valid_category(artifact_type.value, category):
            category = list(ArtifactCategoryRegistry.get_categories(artifact_type.value))[0]

        # 获取文件名用于标题
        if isinstance(rel_path, Path):
            filename = rel_path.name
        else:
            filename = Path(rel_path).name

        # 创建产出物
        metadata = self.manager.create(
            artifact_type=artifact_type,
            category=category,
            content=content,
            run_id=self.run_id,
            title=title or filename,
            description=description,
            department=self.department,
            workflow_id=self.workflow_id,
            tags=tags or [],
        )

        # 添加到 manifest
        self.manifest_manager.add_artifact(self.run_id, metadata, self.department)

        # 记录已注册
        self._registered_paths.add(path_str)

        return metadata

    def register_files_from_output(
        self,
        written_files: List[str],
        titles: Optional[Dict[str, str]] = None,
        descriptions: Optional[Dict[str, str]] = None,
        tags: Optional[Dict[str, List[str]]] = None,
    ) -> List[ArtifactMetadata]:
        """
        批量注册已写入的文件

        Args:
            written_files: 已写入的文件路径列表
            titles: 文件路径到标题的映射
            descriptions: 文件路径到描述的映射
            tags: 文件路径到标签的映射

        Returns:
            创建的产出物元数据列表
        """
        if not self.enabled:
            return []

        artifacts = []
        for file_path in written_files:
            metadata = self.register_file(
                file_path=file_path,
                title=titles.get(file_path) if titles else None,
                description=descriptions.get(file_path) if descriptions else None,
                tags=tags.get(file_path) if tags else None,
            )
            if metadata:
                artifacts.append(metadata)

        return artifacts

    def complete_run(self, status: str = "completed") -> None:
        """
        完成 run

        更新 manifest 状态并可选地归档。

        Args:
            status: run 状态 (completed, failed, cancelled)
        """
        if not self.run_id:
            return

        self.manifest_manager.update_status(self.run_id, status, self.department)

    def get_run_artifacts(self) -> List[ArtifactMetadata]:
        """获取当前 run 的所有产出物"""
        if not self.run_id:
            return []

        return self.manager.registry.get_by_run(self.run_id)


class GateArtifactHandler:
    """
    门禁产出物处理器

    在门禁审批时自动冻结相关产出物。
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        初始化

        Args:
            project_root: 项目根目录
        """
        self.project_root = (project_root or Path.cwd()).resolve()

        # 处理 artifacts 路径
        if self.project_root.name == ".artifacts":
            artifacts_root = self.project_root
        else:
            artifacts_root = self.project_root / ".artifacts"

        self.manager = ArtifactManager(artifacts_root)
        self.manifest_manager = ManifestManager(artifacts_root, self.manager.registry)

    def freeze_run_artifacts(self, run_id: str, department: Optional[str] = None) -> List[ArtifactMetadata]:
        """
        冻结指定 run 的所有产出物

        Args:
            run_id: run ID
            department: 部门

        Returns:
            被冻结的产出物列表
        """
        artifacts = self.manager.registry.get_by_run(run_id)

        frozen = []
        for artifact in artifacts:
            if artifact.status.value != "FROZEN":
                try:
                    frozen_artifact = self.manager.freeze(artifact.id)
                    frozen.append(frozen_artifact)
                except Exception as e:
                    # 记录错误但继续处理其他产出物
                    logger.warning(f"Failed to freeze {artifact.id}: {e}")

        return frozen

    def approve_gate_artifacts(
        self,
        run_id: str,
        gate_id: str,
        department: Optional[str] = None,
        enforce: bool = True,  # v1.5: 默认启用强制模式
    ) -> Dict[str, Any]:
        """
        处理门禁通过时的产出物操作

        Args:
            run_id: run ID
            gate_id: 门禁 ID
            department: 部门
            enforce: 是否启用强制模式 (v1.5 默认为 True)

        Returns:
            操作结果
        """
        # SSOT 校验
        from .ssot_service import SSOTService

        service = SSOTService(self.manager)
        valid, errors = service.validate(run_id=run_id)

        if not valid:
            if enforce:
                # v1.5 enforce 模式：强制失败
                logger.error(f"SSOT validation failed for run {run_id}:")
                for err in errors:
                    logger.error(f"  - {err}")
                raise Exception(f"SSOT validation failed: {errors}")
            else:
                # v1 warning 模式：只打印警告，不失败 (向后兼容)
                logger.warning(f"SSOT validation warnings for run {run_id}:")
                for err in errors:
                    logger.warning(f"  - {err}")

        # 冻结当前 run 的产出物
        frozen_artifacts = self.freeze_run_artifacts(run_id, department)

        # 更新 manifest
        manifest = self.manifest_manager.get(run_id, department)
        if manifest:
            # 添加门禁信息到 properties
            if not manifest.properties:
                manifest.properties = {}
            manifest.properties["approved_gates"] = manifest.properties.get("approved_gates", [])
            manifest.properties["approved_gates"].append({
                "gate_id": gate_id,
                "timestamp": datetime.now().isoformat(),
                "ssot_validated": valid,
            })
            self.manifest_manager.save(manifest)

        return {
            "frozen_count": len(frozen_artifacts),
            "frozen_artifacts": [a.id for a in frozen_artifacts],
            "ssot_validated": valid,
            "ssot_errors": errors if not valid else None,
        }


def create_artifact_handler(
    run_id: str,
    workflow_id: Optional[str] = None,
    department: Optional[str] = None,
    project_root: Optional[Path] = None,
) -> ArtifactFileOutputHandler:
    """
    创建产出物处理器的工厂函数

    Args:
        run_id: run ID
        workflow_id: workflow ID
        department: 部门
        project_root: 项目根目录

    Returns:
        ArtifactFileOutputHandler 实例
    """
    return ArtifactFileOutputHandler(
        project_root=project_root,
        run_id=run_id,
        workflow_id=workflow_id,
        department=department,
    )
