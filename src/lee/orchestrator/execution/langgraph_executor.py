"""
LangGraph Executor Adapter

将新的 LangGraph Executor 桥接到现有 Orchestrator 体系。

职责：
1. 接收 Orchestrator 的 input_data (Dict)
2. 转换为 ExecutorTaskSpec
3. 调用 LangGraph run_task()
4. 将 ExecutionResult 转换回 Dict 返回

支持的 task_type:
- l3.impl.coding: 代码实现任务
- l3.test.unit: 单元测试任务
"""

import asyncio
from typing import Dict, Any, Optional

from .executors import BaseExecutor

from lee.runtime.executor import (
    run_task,
    ExecutorTaskSpec,
    ExecutionResult,
    TaskStatus,
    list_registered_types,
)


class LangGraphExecutor(BaseExecutor):
    """
    LangGraph 执行器

    作为 Orchestrator 和 LangGraph Executor 之间的桥梁。

    使用方式:
        # 在 workflow YAML 中
        steps:
          - name: implement_code
            executor: langgraph
            execution_context:
              task_type: l3.impl.coding
              llm_profile: default
            inputs:
              design_spec: ${artifacts.design}
              repo_workspace: ${project.workspace}

    input_data 字段说明:
        - task_id: 任务 ID（可选，会自动生成）
        - task_type: 任务类型，必须是已注册的类型
        - inputs: 输入文件路径映射
        - outputs: 输出文件路径映射（可选）
        - workspace_root: 工作空间根目录
        - allowed_write_patterns: 允许写入的文件模式
        - llm_profile: LLM Profile 名称
        - llm_temperature: LLM 温度
        - llm_max_tokens: LLM 最大 token
        - params: 额外参数
    """

    def __init__(
        self,
        default_profile: str = "default",
        default_workspace: Optional[str] = None,
        **kwargs
    ):
        """
        初始化 LangGraph 执行器

        Args:
            default_profile: 默认 LLM Profile
            default_workspace: 默认工作空间根目录
            **kwargs: 其他参数（忽略）
        """
        self.default_profile = default_profile
        self.default_workspace = default_workspace

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 LangGraph 任务

        Args:
            input_data: 输入数据字典

        Returns:
            执行结果字典
        """
        # 验证 task_type
        task_type = input_data.get("task_type")
        if not task_type:
            return {
                "status": "failed",
                "error": "Missing required field: task_type",
                "available_types": list_registered_types(),
            }

        if task_type not in list_registered_types():
            return {
                "status": "failed",
                "error": f"Unknown task_type: {task_type}",
                "available_types": list_registered_types(),
            }

        # 构建 ExecutorTaskSpec
        try:
            task_spec = self._build_task_spec(input_data)
        except ValueError as e:
            return {
                "status": "failed",
                "error": f"Invalid input_data: {e}",
            }

        # 执行任务（同步调用，在线程池中执行以避免阻塞）
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, run_task, task_spec)

        # 转换结果
        return self._convert_result(result)

    def _build_task_spec(self, input_data: Dict[str, Any]) -> ExecutorTaskSpec:
        """
        从 input_data 构建 ExecutorTaskSpec

        Args:
            input_data: 输入数据字典

        Returns:
            ExecutorTaskSpec 实例
        """
        # 必需字段
        task_type = input_data["task_type"]

        # 可选字段，带默认值
        task_id = input_data.get("task_id", f"task-{task_type}-auto")

        return ExecutorTaskSpec(
            task_id=task_id,
            task_type=task_type,
            inputs=input_data.get("inputs", {}),
            outputs=input_data.get("outputs", {}),
            params=input_data.get("params", {}),
            workspace_root=input_data.get(
                "workspace_root",
                self.default_workspace
            ),
            allowed_write_patterns=input_data.get("allowed_write_patterns", []),
            llm_profile=input_data.get("llm_profile", self.default_profile),
            llm_temperature=input_data.get("llm_temperature"),
            llm_max_tokens=input_data.get("llm_max_tokens"),
            timeout_seconds=input_data.get("timeout_seconds"),
            max_retries=input_data.get("max_retries", 0),
        )

    def _convert_result(self, result: ExecutionResult) -> Dict[str, Any]:
        """
        将 ExecutionResult 转换为字典

        Args:
            result: ExecutionResult 实例

        Returns:
            结果字典
        """
        output = {
            "task_id": result.task_id,
            "status": result.status.value if result.status else "unknown",
            "message": result.message,
            "artifacts": result.artifacts or {},
            "logs": result.logs or [],
            "metrics": result.metrics or {},
            "tokens_used": result.tokens_used,
        }

        if result.error_details:
            output["error_details"] = result.error_details

        if result.completed_at:
            output["completed_at"] = result.completed_at.isoformat()

        return output


def register_langgraph_executor():
    """
    注册 LangGraph 执行器到 ExecutorFactory

    使用方式:
        from lee.orchestrator.execution.langgraph_executor import register_langgraph_executor
        register_langgraph_executor()
    """
    from .executors import ExecutorFactory
    ExecutorFactory.register("langgraph", LangGraphExecutor)
