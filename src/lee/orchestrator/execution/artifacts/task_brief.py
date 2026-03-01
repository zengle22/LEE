"""
Task Brief Generator - Task Brief 自动生成器

Task Brief 是给人和高层 Agent 看的任务摘要，包含：
- 任务元信息 (task_type, related_ssot)
- 范围 (scope: include/exclude)
- 验收标准 (acceptance)
- 风险 (risks)
- Markdown 正文说明

定位：TRANSFER 类型的中间产物，用于跨部门/跨 run 流转。
"""

import yaml
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from .manager import ArtifactManager
from .models import ArtifactMetadata
from .types import ArtifactType, GovernanceKind


@dataclass
class TaskBrief:
    """
    Task Brief v1.0

    任务摘要视图，用于快速了解任务范围和目标。
    """

    id: str
    run_id: str
    department: str

    # 任务基本信息
    title: str = ""
    description: str = ""

    # 任务类型
    task_type: str = "feature"  # feature, bugfix, incident, refactor

    # 关联的 SSOT 产物
    related_ssot: Dict[str, Any] = field(default_factory=dict)
    # 示例：{"prd": "FDPRD-001", "api_contracts": ["API-001"], "bug_report": "BUG-001"}

    # 范围
    scope: Dict[str, List[str]] = field(default_factory=dict)
    # 示例：{"include": ["修复 xxx"], "exclude": ["不做性能优化"]}

    # 验收标准
    acceptance: List[str] = field(default_factory=list)

    # 风险
    risks: List[str] = field(default_factory=list)

    # Markdown 正文
    body_markdown: str = ""

    # 元信息
    created_at: datetime = None
    created_by: str = "system"  # system, pm, agent

    # 状态
    status: str = "draft"  # draft, confirmed, completed

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于 YAML 序列化"""
        return {
            "id": self.id,
            "run_id": self.run_id,
            "department": self.department,
            "title": self.title,
            "description": self.description,
            "task_type": self.task_type,
            "related_ssot": self.related_ssot,
            "scope": self.scope,
            "acceptance": self.acceptance,
            "risks": self.risks,
            "body_markdown": self.body_markdown,
            "created_at": self.created_at.isoformat(),
            "created_by": self.created_by,
            "status": self.status,
        }

    def to_yaml(self) -> str:
        """转换为 YAML 字符串"""
        return yaml.dump(self.to_dict(), allow_unicode=True, sort_keys=False)


class TaskBriefGenerator:
    """
    Task Brief 生成器

    支持：
    1. 从 Task Card 生成
    2. 从 PRD 生成
    3. 从 Bug Report 生成
    4. 手动创建
    """

    def __init__(self, artifact_manager: ArtifactManager):
        """
        初始化

        Args:
            artifact_manager: ArtifactManager 实例
        """
        self.manager = artifact_manager

    def generate_id(self) -> str:
        """生成 Task Brief ID"""
        import random
        now = datetime.now()
        # 添加微秒和随机后缀确保唯一性
        return f"TB-{now.strftime('%Y%m%d-%H%M%S')}-{now.microsecond:06d}-{random.randint(100, 999)}"

    def create_from_task_card(
        self,
        task_card_id: str,
        run_id: str,
        department: str,
        task_type: str = "bugfix",
    ) -> TaskBrief:
        """
        从 Task Card 生成 Task Brief

        Args:
            task_card_id: Task Card artifact ID
            run_id: run ID
            department: 部门
            task_type: 任务类型

        Returns:
            TaskBrief 实例
        """
        # 获取 Task Card
        task_card = self.manager.get(task_card_id)
        if not task_card:
            raise ValueError(f"Task Card not found: {task_card_id}")

        # 读取 Task Card 内容
        content_path = self.manager.root_path / task_card.path
        task_card_content = {}
        if content_path.exists():
            try:
                task_card_content = yaml.safe_load(content_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                pass

        # 提取信息
        title = task_card_content.get("title", task_card.title or task_card_id)
        description = task_card_content.get("description", task_card.description or "")
        related_prd = task_card_content.get("related_prd")
        bug_report = task_card_content.get("bug_report")

        # 构建 related_ssot
        related_ssot = {}
        if related_prd:
            related_ssot["prd"] = related_prd
        if bug_report:
            related_ssot["bug_report"] = bug_report

        # 创建 Task Brief
        brief = TaskBrief(
            id=self.generate_id(),
            run_id=run_id,
            department=department,
            task_type=task_type,
            related_ssot=related_ssot,
            scope={
                "include": [f"完成 Task Card: {title}"],
                "exclude": [],
            },
            acceptance=["任务执行完成"],
            risks=[],
            body_markdown=f"## 任务说明\n\n{description}",
            created_by="system",
            status="draft",
        )

        return brief

    def create_from_prd(
        self,
        prd_id: str,
        run_id: str,
        department: str,
        task_type: str = "feature",
    ) -> TaskBrief:
        """
        从 PRD 生成 Task Brief

        Args:
            prd_id: PRD artifact ID
            run_id: run ID
            department: 部门
            task_type: 任务类型

        Returns:
            TaskBrief 实例
        """
        # 获取 PRD
        prd = self.manager.get(prd_id)
        if not prd:
            raise ValueError(f"PRD not found: {prd_id}")

        # 读取 PRD 内容
        content_path = self.manager.root_path / prd.path
        prd_content = {}
        if content_path.exists():
            try:
                prd_content = yaml.safe_load(content_path.read_text(encoding="utf-8")) or {}
            except yaml.YAMLError:
                pass

        # 提取信息
        title = prd_content.get("title", prd.title or prd_id)
        description = prd_content.get("description", prd.description or "")
        acceptance_criteria = prd_content.get("acceptance_criteria", [])

        # 创建 Task Brief
        brief = TaskBrief(
            id=self.generate_id(),
            run_id=run_id,
            department=department,
            task_type=task_type,
            related_ssot={"prd": prd_id},
            scope={
                "include": [f"实现 PRD: {title}"],
                "exclude": [],
            },
            acceptance=acceptance_criteria if acceptance_criteria else ["PRD 要求的功能实现完成"],
            risks=[],
            body_markdown=f"## PRD 说明\n\n{description}",
            created_by="system",
            status="draft",
        )

        return brief

    def create_manual(
        self,
        run_id: str,
        department: str,
        title: str,
        description: str,
        task_type: str = "feature",
        related_ssot: Optional[Dict[str, Any]] = None,
        scope_include: Optional[List[str]] = None,
        scope_exclude: Optional[List[str]] = None,
        acceptance: Optional[List[str]] = None,
        risks: Optional[List[str]] = None,
    ) -> TaskBrief:
        """
        手动创建 Task Brief

        Args:
            run_id: run ID
            department: 部门
            title: 标题
            description: 描述
            task_type: 任务类型
            related_ssot: 关联的 SSOT 产物
            scope_include: 包含范围
            scope_exclude: 排除范围
            acceptance: 验收标准
            risks: 风险

        Returns:
            TaskBrief 实例
        """
        brief = TaskBrief(
            id=self.generate_id(),
            run_id=run_id,
            department=department,
            title=title,
            description=description,
            task_type=task_type,
            related_ssot=related_ssot or {},
            scope={
                "include": scope_include or [],
                "exclude": scope_exclude or [],
            },
            acceptance=acceptance or [],
            risks=risks or [],
            body_markdown=f"## 任务说明\n\n{description}",
            created_by="user",
            status="draft",
        )

        return brief

    def save_brief(
        self,
        brief: TaskBrief,
        workflow_id: Optional[str] = None,
    ) -> ArtifactMetadata:
        """
        保存 Task Brief 为 artifact

        Args:
            brief: TaskBrief 实例
            workflow_id: workflow ID

        Returns:
            创建的 ArtifactMetadata
        """
        return self.manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="task_brief",
            content=brief.to_yaml(),
            run_id=brief.run_id,
            governance_kind=GovernanceKind.TRANSFER,
            title=f"Task Brief: {brief.id}",
            department=brief.department,
            workflow_id=workflow_id,
            tags=["task_brief", brief.task_type],
        )

    def create_and_save(
        self,
        run_id: str,
        department: str,
        title: str,
        description: str,
        task_type: str = "feature",
        related_ssot: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
    ) -> ArtifactMetadata:
        """
        快捷方法：创建并保存 Task Brief

        Args:
            run_id: run ID
            department: 部门
            title: 标题
            description: 描述
            task_type: 任务类型
            related_ssot: 关联的 SSOT 产物
            workflow_id: workflow ID

        Returns:
            创建的 ArtifactMetadata
        """
        brief = self.create_manual(
            run_id=run_id,
            department=department,
            title=title,
            description=description,
            task_type=task_type,
            related_ssot=related_ssot,
        )
        return self.save_brief(brief, workflow_id)
