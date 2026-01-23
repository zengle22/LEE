"""
统一执行协议 - Engine 接口定义

定义了 Orchestrator 与 Engine 之间的统一接口，
确保 Orchestrator 不需要知道具体 Engine 的实现细节。
"""

from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Literal, Protocol
from pathlib import Path
from datetime import datetime


@dataclass
class ArtifactReference:
    """产物引用 - 输入/输出的文件或逻辑产物"""
    id: str                              # 产物标识
    path: Optional[str] = None           # 文件路径（如果是文件产物）
    summary: Optional[str] = None        # 内容摘要
    content_type: Optional[str] = None   # 内容类型（text/json/yaml等）
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ContractReference:
    """契约引用 - 输入/输出的 Schema 或验收标准"""
    schema_type: str                     # "json_schema", "yaml", "custom"
    schema: Dict[str, Any]              # Schema 定义
    validation_rules: List[str] = field(default_factory=list)


@dataclass
class StepExecutionRequest:
    """步骤执行请求 - Orchestrator 发送给 Engine 的标准化请求"""

    # 基本信息
    project_dir: str                     # 项目目录
    step_id: str                         # 步骤 ID
    run_id: str                          # 运行 ID

    # Agent 规范（包含 engine 配置、system_prompt 等）
    agent_spec: Dict[str, Any]           # 完整的 agent.yaml 内容

    # 执行上下文（由 Orchestrator 构建）
    context: Dict[str, Any] = field(default_factory=dict)

    # 上下文中的标准字段：
    # - step_description: str           # 步骤描述
    # - inputs: List[ArtifactReference]  # 上游产物
    # - contracts: Dict[str, ContractReference]  # 输入输出契约
    # - project_meta: Dict              # 项目元信息
    # - workflow_info: Dict              # 工作流信息

    # Token 信息（用于权限控制）
    token_id: Optional[str] = None       # Step Token ID
    token_expires_at: Optional[str] = None

    # 工作目录（Engine 应在此目录下工作）
    working_dir: Optional[str] = None

    # 超时设置
    timeout_seconds: int = 3600          # 默认 1 小时

    def get_inputs(self) -> List[ArtifactReference]:
        """获取输入产物列表"""
        inputs = self.context.get("inputs", [])
        return [ArtifactReference(**inp) if isinstance(inp, dict) else inp for inp in inputs]

    def get_contracts(self) -> Dict[str, ContractReference]:
        """获取契约"""
        contracts = self.context.get("contracts", {})
        return {
            key: ContractReference(**value) if isinstance(value, dict) else value
            for key, value in contracts.items()
        }

    def get_working_dir(self) -> Path:
        """获取工作目录（创建如果不存在）"""
        if self.working_dir:
            wd = Path(self.working_dir)
        else:
            # 默认：project_dir / .workflow / workspace / {step_id}
            wd = Path(self.project_dir) / ".workflow" / "workspace" / self.step_id

        wd.mkdir(parents=True, exist_ok=True)
        return wd

    def get_engine_config(self) -> Dict[str, Any]:
        """获取 Engine 配置"""
        return self.agent_spec.get("engine", {})

    def get_system_prompt(self) -> str:
        """获取 System Prompt"""
        return self.agent_spec.get("system_prompt", "")

    def get_instructions(self) -> List[str]:
        """获取 Instructions"""
        return self.agent_spec.get("instructions", [])


@dataclass
class StepExecutionResult:
    """步骤执行结果 - Engine 返回给 Orchestrator 的标准化结果"""

    # 执行状态
    status: Literal["completed", "failed", "skipped", "timeout"]

    # 产物列表（生成的文件或逻辑产物）
    outputs: List[ArtifactReference] = field(default_factory=list)

    # 执行日志（用于审计和调试）
    messages: List[Dict[str, Any]] = field(default_factory=list)

    # 原始结果（用于 debug，可选）
    raw: Optional[Any] = None

    # 错误信息（如果失败）
    error: Optional[str] = None
    error_details: Optional[Dict[str, Any]] = None

    # 元信息
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    engine_type: Optional[str] = None      # Engine 类型（如 "metagpt", "llm"）

    # Token 使用统计（如果适用）
    tokens_used: Optional[int] = None
    cost_usd: Optional[float] = None

    def get_output_paths(self) -> List[str]:
        """获取所有输出文件路径"""
        return [out.path for out in self.outputs if out.path]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于序列化）"""
        return {
            "status": self.status,
            "outputs": [
                {
                    "id": out.id,
                    "path": out.path,
                    "summary": out.summary,
                    "content_type": out.content_type,
                    "metadata": out.metadata
                }
                for out in self.outputs
            ],
            "messages": self.messages,
            "error": self.error,
            "error_details": self.error_details,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "engine_type": self.engine_type,
            "tokens_used": self.tokens_used,
            "cost_usd": self.cost_usd
        }


class BaseExecutor(Protocol):
    """Executor 接口 - 所有 Engine 必须实现此接口"""

    async def execute(self, request: StepExecutionRequest) -> StepExecutionResult:
        """
        执行步骤

        Args:
            request: 标准化的执行请求

        Returns:
            标准化的执行结果
        """
        ...

    def get_engine_type(self) -> str:
        """获取 Engine 类型标识"""
        ...

    def validate_request(self, request: StepExecutionRequest) -> tuple[bool, Optional[str]]:
        """
        验证请求是否有效

        Returns:
            (是否有效, 错误信息)
        """
        ...
