"""
Executors - 纯执行器模块

⚠️ EXECUTOR 宪法 ⚠️

本模块内的所有 Executor 必须遵守以下绝对规则：

1. 不得直接访问 SQLite
   - ❌ 禁止: from lee.storage.sqlite_store import db; await db.update(...)
   - ✅ 正确: 只通过 Orchestrator 传递的数据执行

2. 不得直接调用 Orchestrator
   - ❌ 禁止: from lee.execution.orchestrator import orch; await orch.create_workflow(...)
   - ✅ 正确: 只接收输入参数，返回执行结果

3. 职责边界
   - ✅ 接收: input_data (dict)
   - ✅ 执行: 业务逻辑（LLM 调用 / Shell 命令 / 数据处理）
   - ✅ 返回: output_data (dict)
   - ❌ 越界: 状态持久化、事件发布、workflow 创建

违反者将被视为架构叛徒，未来重构时优先清除。
"""

from abc import ABC, abstractmethod
from typing import Dict, Any
import os
import subprocess
import json
import asyncio


class BaseExecutor(ABC):
    """执行器基类"""

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行任务

        Args:
            input_data: 输入数据

        Returns:
            output_data: 输出数据
        """
        pass


# 导入实际的执行器实现
from lee.orchestrator.execution.llm_executor import LLMExecutor as RealLLMExecutor
from lee.orchestrator.execution.mock_executor import MockLLMExecutor
from lee.orchestrator.execution.metagpt_executor import MetaGPTExecutor as RealMetaGPTExecutor
from lee.orchestrator.execution.claude_code_executor import ClaudeCodeExecutor
from lee.orchestrator.execution.codex_executor import CodexExecutor
from lee.orchestrator.execution.llm_executor import LLMConfig


class LLMExecutor(BaseExecutor):
    """
    LLM 执行器（代理类）

    实际实现见: llm_executor.py

    支持多种 Provider：
    - OpenAI (GPT-4, GPT-3.5)
    - Anthropic (Claude)
    - Azure OpenAI
    - 其他兼容 OpenAI API 的服务
    - Fallback: 支持多 Provider 自动切换

    配置文件: flowcore/engines/llm/config.yaml
    """

    def __init__(self, profile: str = "antigravity", config_path: str = None,
                 fallback_providers: list = None, **kwargs):
        self._executor = RealLLMExecutor(
            profile=profile,
            config_path=config_path,
            fallback_providers=fallback_providers
        )

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 LLM 任务"""
        return await self._executor.execute(input_data)


class ShellExecutor(BaseExecutor):
    """
    Shell 命令执行器

    执行 Shell 命令（如构建、测试、部署脚本等）
    """

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 Shell 命令

        Args:
            input_data: 应包含 command 字段

        Returns:
            包含 stdout, stderr, return_code 等字段
        """
        command = input_data.get("command", "")
        working_dir = input_data.get("working_dir", None)
        timeout = input_data.get("timeout", 30)

        if not command:
            raise ValueError("Input data must contain 'command' field")

        try:
            env = os.environ.copy()
            env["CLAUDE_CODE_ENTRYPOINT"] = "lee-executor"

            completed = await asyncio.to_thread(
                subprocess.run,
                command,
                shell=True,
                cwd=working_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout,
                encoding="utf-8",
                errors="replace",
            )

            return {
                "stdout": completed.stdout,
                "stderr": completed.stderr,
                "return_code": completed.returncode,
                "status": "completed" if completed.returncode == 0 else "failed",
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "return_code": -1,
                "status": "timeout",
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "status": "error",
            }


class MetaGPTExecutor(BaseExecutor):
    """
    MetaGPT 执行器（代理类）

    实际实现见: metagpt_executor.py

    支持的任务类型：
    - code_implementation: 代码实现（使用 SoftwareCompany）
    - bug_autofix: Bug 自动修复
    - custom_team: 自定义团队配置
    """

    def __init__(self, role: str = "Developer", llm_config: Dict = None, **kwargs):
        self._executor = RealMetaGPTExecutor(role=role, llm_config=llm_config)

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 MetaGPT 任务"""
        return await self._executor.execute(input_data)


# 导入 asyncio（ShellExecutor 需要）
import asyncio


class ExecutorFactory:
    """
    执行器工厂

    根据 executor_type 创建对应的执行器实例

    支持的执行器类型：
    - llm: LLM 执行器（支持 OpenAI/Claude/自定义等）
    - shell: Shell 命令执行器
    - metagpt: MetaGPT 执行器
    """

    _executors = {
        "llm": LLMExecutor,
        "shell": ShellExecutor,
        "metagpt": MetaGPTExecutor,
        "claude_code": ClaudeCodeExecutor,
        "codex": CodexExecutor,
    }

    @classmethod
    def create(cls, executor_type: str, **kwargs) -> BaseExecutor:
        """
        创建执行器实例

        Args:
            executor_type: 执行器类型（llm/shell/metagpt）
            **kwargs: 传递给执行器的额外参数

                对于 llm:
                    profile: 配置文件名称（default, antigravity, zhipu, agent.prd, agent.dev）
                    config_path: 配置文件路径（可选）

                对于 metagpt:
                    role: MetaGPT 角色名称（默认: Developer）
                    llm_config: LLM 配置字典

        Returns:
            执行器实例
        """
        executor_class = cls._executors.get(executor_type)
        if executor_class is None:
            raise ValueError(f"Unknown executor type: {executor_type}")

        if executor_type == "llm":
            use_mock = os.getenv("LEE_LLM_MOCK", "").lower() in ("1", "true", "yes") \
                or os.getenv("LEE_DEMO_MODE", "").lower() in ("1", "true", "yes")
            if use_mock:
                return MockLLMExecutor(agent_id=kwargs.get("agent_id", ""))

            if "profile" not in kwargs:
                default_profile = LLMConfig(kwargs.get("config_path")).get_default_profile()
                kwargs["profile"] = os.getenv("LLM_PROFILE", default_profile)

            try:
                return executor_class(**kwargs)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(
                    f"Failed to create executor {executor_type}, trying mock fallback: {e}"
                )
                # Optional fallback to mock in demo mode
                if use_mock:
                    return MockLLMExecutor(agent_id=kwargs.get("agent_id", ""))
                raise

        return executor_class(**kwargs)

    @classmethod
    def register(cls, executor_type: str, executor_class: type):
        """
        注册自定义执行器

        Args:
            executor_type: 执行器类型名称
            executor_class: 执行器类（必须继承 BaseExecutor）
        """
        if not issubclass(executor_class, BaseExecutor):
            raise ValueError("Executor must inherit from BaseExecutor")

        cls._executors[executor_type] = executor_class
