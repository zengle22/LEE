"""
Context Bundle v0.9 - LLM 调用上下文快照

记录 LLM 调用的 prompt 快照，用于审计、复盘和减少幻觉。
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from .manager import ArtifactManager
from .types import ArtifactType, GovernanceKind


@dataclass
class TaskContextBundle:
    """
    Task Context Bundle v0.9 (简化版)

    仅记录 LLM 最终 prompt 文本 + run_id + step_id
    用于 debug 和审计，不建议大于几十 KB
    """

    id: str
    run_id: str
    step_id: str
    llm_call_id: str
    prompt_text: str  # system + user 合并后的最终 prompt
    created_at: datetime = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()


class ContextBuilder:
    """
    构建 Task Context Bundle (v0.9 简化版)

    在 LLM 调用成功后，记录 Bundle 为 artifact。
    """

    def __init__(self, artifact_manager: ArtifactManager):
        """
        初始化

        Args:
            artifact_manager: ArtifactManager 实例
        """
        self.manager = artifact_manager

    def build_v0_9(
        self,
        run_id: str,
        step_id: str,
        prompt_text: str,
        llm_call_id: Optional[str] = None,
    ) -> TaskContextBundle:
        """
        创建简化版 Context Bundle

        Args:
            run_id: run ID
            step_id: step ID
            prompt_text: LLM 最终 prompt 文本 (system + user 合并)
            llm_call_id: LLM call ID (可选，自动生成)

        Returns:
            TaskContextBundle 实例
        """
        if llm_call_id is None:
            llm_call_id = f"CALL-{datetime.now().strftime('%H%M%S')}"

        bundle_id = f"TCTX-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        return TaskContextBundle(
            id=bundle_id,
            run_id=run_id,
            step_id=step_id,
            llm_call_id=llm_call_id,
            prompt_text=prompt_text,
            created_at=datetime.now(),
        )

    def save_bundle(
        self,
        bundle: TaskContextBundle,
        department: Optional[str] = None,
        workflow_id: Optional[str] = None,
    ) -> ArtifactMetadata:
        """
        保存 Bundle 为 artifact

        Args:
            bundle: TaskContextBundle 实例
            department: 部门
            workflow_id: workflow ID

        Returns:
            创建的 ArtifactMetadata
        """
        import yaml

        content = yaml.dump(
            {
                "id": bundle.id,
                "run_id": bundle.run_id,
                "step_id": bundle.step_id,
                "llm_call_id": bundle.llm_call_id,
                "prompt_text": bundle.prompt_text,
                "created_at": bundle.created_at.isoformat(),
            },
            allow_unicode=True,
            sort_keys=False,
        )

        return self.manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="task_context_bundle",
            content=content,
            run_id=bundle.run_id,
            governance_kind=GovernanceKind.EVIDENCE,
            title=f"Context Bundle for {bundle.step_id}",
            department=department,
            workflow_id=workflow_id,
            tags=["context_bundle", "llm_snapshot"],
        )

    def record_llm_call(
        self,
        run_id: str,
        step_id: str,
        prompt_text: str,
        department: Optional[str] = None,
        workflow_id: Optional[str] = None,
        llm_call_id: Optional[str] = None,
    ) -> ArtifactMetadata:
        """
        记录 LLM 调用为 Context Bundle (便捷方法)

        Args:
            run_id: run ID
            step_id: step ID
            prompt_text: LLM 最终 prompt 文本
            department: 部门
            workflow_id: workflow ID
            llm_call_id: LLM call ID

        Returns:
            创建的 ArtifactMetadata
        """
        bundle = self.build_v0_9(run_id, step_id, prompt_text, llm_call_id)
        return self.save_bundle(bundle, department, workflow_id)
