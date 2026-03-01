"""
Context Bundle v1.0 - LLM 调用上下文快照

记录 LLM 调用的完整上下文，包括 artifacts 引用列表和结构化 prompt 快照。
用于审计、复盘和减少幻觉。

版本演进:
- v0.9: 仅记录 prompt_text (简化版)
- v1.0: 增加 artifacts 列表和 structured prompt_snapshot (system/user 分离)
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, List, Dict, Any

from .manager import ArtifactManager
from .types import ArtifactType, GovernanceKind


@dataclass
class PromptSnapshot:
    """
    结构化的 Prompt 快照 (v1.0)

    将 system 和 user prompt 分离，便于审计和分析
    """
    system: str = ""
    user: str = ""

    def to_dict(self) -> Dict[str, str]:
        return {"system": self.system, "user": self.user}


@dataclass
class TaskContextBundle:
    """
    Task Context Bundle v1.0 (完整版)

    包含:
    - artifacts: 本次调用用到的所有 Artifact 引用列表
    - prompt_snapshot: 结构化的 system/user prompt
    - 元数据：run_id, step_id, llm_call_id 等

    用于 debug、审计和 LLM 调用复盘。
    文件大小建议控制在几十 KB 以内。
    """

    id: str
    run_id: str
    step_id: str
    llm_call_id: str

    # v1.0 新增：Artifacts 引用列表
    artifacts: Dict[str, List[str]] = field(default_factory=dict)
    # 示例：{"prd": ["FDPRD-001"], "api_contracts": ["API-001"], "code_snippets": ["ART-123"]}

    # v1.0 新增：结构化 prompt 快照
    prompt_snapshot: Optional[PromptSnapshot] = None

    # 兼容 v0.9: 合并后的 prompt_text (如果 prompt_snapshot 存在，此项可为空)
    prompt_text: str = ""

    created_at: datetime = None

    # 配置信息
    config: Dict[str, Any] = field(default_factory=dict)
    # 示例：{"max_artifacts": 50, "max_tokens": 10000}

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.prompt_snapshot is None and self.prompt_text:
            # 从 v0.9 格式升级：如果没有 prompt_snapshot，尝试从 prompt_text 推断
            self.prompt_snapshot = PromptSnapshot(system="", user=self.prompt_text)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，用于 YAML 序列化"""
        result = {
            "id": self.id,
            "run_id": self.run_id,
            "step_id": self.step_id,
            "llm_call_id": self.llm_call_id,
            "created_at": self.created_at.isoformat(),
        }

        if self.artifacts:
            result["artifacts"] = self.artifacts

        if self.prompt_snapshot:
            result["prompt_snapshot"] = self.prompt_snapshot.to_dict()
        elif self.prompt_text:
            result["prompt_text"] = self.prompt_text

        if self.config:
            result["config"] = self.config

        return result


class ContextBuilder:
    """
    构建 Task Context Bundle

    v1.0: 支持完整的 artifacts 列表和结构化 prompt_snapshot
    v0.9: 仅记录 prompt_text (向后兼容)
    """

    def __init__(self, artifact_manager: ArtifactManager):
        """
        初始化

        Args:
            artifact_manager: ArtifactManager 实例
        """
        self.manager = artifact_manager

    def build_v1_0(
        self,
        run_id: str,
        step_id: str,
        system_prompt: str,
        user_prompt: str,
        artifacts: Optional[Dict[str, List[str]]] = None,
        llm_call_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> TaskContextBundle:
        """
        创建完整版 Context Bundle (v1.0)

        Args:
            run_id: run ID
            step_id: step ID
            system_prompt: LLM system prompt
            user_prompt: LLM user prompt
            artifacts: Artifact 引用字典，如 {"prd": ["FDPRD-001"], "api_contracts": ["API-001"]}
            llm_call_id: LLM call ID (可选，自动生成)
            config: 配置信息，如 {"max_artifacts": 50, "max_tokens": 10000}

        Returns:
            TaskContextBundle 实例
        """
        if llm_call_id is None:
            llm_call_id = f"CALL-{datetime.now().strftime('%H%M%S')}"

        bundle_id = f"TCTX-{datetime.now().strftime('%Y%m%d-%H%M%S')}"

        prompt_snapshot = PromptSnapshot(system=system_prompt, user=user_prompt)

        return TaskContextBundle(
            id=bundle_id,
            run_id=run_id,
            step_id=step_id,
            llm_call_id=llm_call_id,
            artifacts=artifacts or {},
            prompt_snapshot=prompt_snapshot,
            config=config or {},
            created_at=datetime.now(),
        )

    def build_v0_9(
        self,
        run_id: str,
        step_id: str,
        prompt_text: str,
        llm_call_id: Optional[str] = None,
    ) -> TaskContextBundle:
        """
        创建简化版 Context Bundle (v0.9, 向后兼容)

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
            bundle.to_dict(),
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
        记录 LLM 调用为 Context Bundle (便捷方法，v0.9 兼容)

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

    def record_llm_call_v1_0(
        self,
        run_id: str,
        step_id: str,
        system_prompt: str,
        user_prompt: str,
        artifacts: Optional[Dict[str, List[str]]] = None,
        department: Optional[str] = None,
        workflow_id: Optional[str] = None,
        llm_call_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> ArtifactMetadata:
        """
        记录 LLM 调用为 Context Bundle (v1.0 完整版)

        Args:
            run_id: run ID
            step_id: step ID
            system_prompt: LLM system prompt
            user_prompt: LLM user prompt
            artifacts: Artifact 引用字典
            department: 部门
            workflow_id: workflow ID
            llm_call_id: LLM call ID
            config: 配置信息

        Returns:
            创建的 ArtifactMetadata
        """
        bundle = self.build_v1_0(
            run_id=run_id,
            step_id=step_id,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            artifacts=artifacts,
            llm_call_id=llm_call_id,
            config=config,
        )
        return self.save_bundle(bundle, department, workflow_id)
