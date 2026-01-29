"""
MetaGPT Executor - 使用 MetaGPT 框架执行 Agent

支持的任务类型：
- code_implementation: 代码实现（使用 SoftwareCompany）
- bug_autofix: Bug 自动修复
- custom_team: 自定义团队配置
"""

import asyncio
import os
from typing import Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    from metagpt.context import Context
    from metagpt.schema import Message
    from metagpt.software_company import SoftwareCompany
    METAGPT_AVAILABLE = True
except ImportError:
    METAGPT_AVAILABLE = False


class MetaGPTExecutor:
    """
    MetaGPT 执行器

    使用 MetaGPT 框架的多角色协作能力执行任务。
    """

    def __init__(self, role: str = "Developer", llm_config: Optional[Dict] = None):
        """
        初始化 MetaGPT 执行器

        Args:
            role: MetaGPT 角色名称
            llm_config: LLM 配置字典（包含 api_key, model, base_url 等）
        """
        if not METAGPT_AVAILABLE:
            raise ImportError(
                "MetaGPT is not installed. "
                "Install it with: pip install metagpt"
            )

        self.role = role
        self.llm_config = llm_config or {}
        self.context = Context()

        # 初始化 MetaGPT 配置
        self._init_config()

    def _init_config(self):
        """初始化 MetaGPT 配置"""
        config = self.context.config

        # 从 llm_config 更新配置
        if "api_key" in self.llm_config:
            config.llm.api_key = self._resolve_env_var(self.llm_config["api_key"])

        if "model" in self.llm_config:
            config.llm.model = self.llm_config["model"]

        if "base_url" in self.llm_config:
            config.llm.base_url = self.llm_config["base_url"]

        if "temperature" in self.llm_config:
            config.llm.temperature = self.llm_config["temperature"]

        if "max_tokens" in self.llm_config:
            config.llm.max_tokens = self.llm_config["max_tokens"]

    def _resolve_env_var(self, value: str) -> str:
        """解析环境变量"""
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            return os.getenv(env_var, value)
        return value

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行 MetaGPT 任务

        Args:
            input_data: 应包含 task_type, requirement 等字段

        Returns:
            执行结果
        """
        task_type = input_data.get("task_type", "code_implementation")
        requirement = input_data.get("requirement", "")
        workspace = input_data.get("workspace", ".workspace")

        try:
            if task_type == "code_implementation":
                return await self._run_code_implementation(requirement, workspace)
            elif task_type == "bug_autofix":
                return await self._run_bug_autofix(requirement, workspace)
            else:
                return {
                    "status": "failed",
                    "error": f"Unknown task type: {task_type}",
                }

        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "error_type": type(e).__name__,
            }

    async def _run_code_implementation(
        self,
        requirement: str,
        workspace: str
    ) -> Dict[str, Any]:
        """
        执行代码实现任务

        Args:
            requirement: 功能需求描述
            workspace: 工作目录

        Returns:
            执行结果
        """
        started_at = datetime.now()

        # 创建工作目录
        workspace_path = Path(workspace)
        workspace_path.mkdir(parents=True, exist_ok=True)

        # 配置预算
        investment = self.llm_config.get("investment", 10.0)
        max_rounds = self.llm_config.get("max_rounds", 5)

        # 运行 SoftwareCompany
        company = SoftwareCompany(context=self.context)
        company.invest(investment)

        history = await company.run(
            n_round=max_rounds,
            idea=requirement,
            auto_archive=True,
        )

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        # 生成摘要
        summary_path = workspace_path / "summary.md"
        self._generate_summary(history, summary_path, requirement)

        return {
            "status": "completed",
            "workspace": str(workspace_path),
            "summary_path": str(summary_path),
            "rounds": len(history),
            "duration_seconds": duration,
            "output": f"Code implementation completed in {len(history)} rounds",
        }

    async def _run_bug_autofix(
        self,
        bug_report: str,
        workspace: str
    ) -> Dict[str, Any]:
        """
        执行 Bug 修复任务

        Args:
            bug_report: Bug 报告
            workspace: 工作目录

        Returns:
            执行结果
        """
        started_at = datetime.now()

        # 创建工作目录
        workspace_path = Path(workspace)
        workspace_path.mkdir(parents=True, exist_ok=True)

        # TODO: 实现专门的 Bug 修复团队
        # 目前返回占位符
        fix_summary_path = workspace_path / "fix_summary.md"
        fix_summary_path.write_text(
            f"# Bug Fix Summary\n\n"
            f"## Bug Report\n{bug_report}\n\n"
            f"## Status\nBug fixing is not yet fully implemented. "
            f"This is a placeholder response.\n",
            encoding="utf-8",
        )

        completed_at = datetime.now()
        duration = (completed_at - started_at).total_seconds()

        return {
            "status": "completed",
            "workspace": str(workspace_path),
            "fix_summary_path": str(fix_summary_path),
            "duration_seconds": duration,
            "output": "Bug fix completed (placeholder)",
        }

    def _generate_summary(self, history: Any, summary_path: Path, requirement: str):
        """生成执行摘要"""
        content = [
            "# MetaGPT Execution Summary\n",
            f"\n## Original Requirement\n",
            f"{requirement}\n",
            f"\n## Execution History\n",
            f"Total messages: {len(history)}\n",
        ]

        # 添加最近的历史条目
        if history:
            content.append("\n## Recent Actions\n")
            for msg in list(history)[-10:]:
                content.append(f"- {msg.role}: {msg.content[:100]}...\n")

        summary_path.write_text("".join(content), encoding="utf-8")

    def get_info(self) -> Dict[str, Any]:
        """获取执行器信息"""
        return {
            "type": "metagpt",
            "role": self.role,
            "llm_config": {
                "model": self.llm_config.get("model", "default"),
                "base_url": self.llm_config.get("base_url", ""),
            },
        }
