"""
Agent Reference Resolver

解析 Agent 引用到 spec 文件路径。支持多种命名约定和路径格式。

命名格式:
- agent.dev.tech_lead -> specs/org/development/agents/tech-lead/v1/agent.yaml
- agent.research.fact_collector -> specs/common/agents/fact-collector/v1/agent.yaml
- agent.dev.tech_lead@v2 -> specs/org/development/agents/tech-lead/v2/agent.yaml
- ./custom-agent.yaml -> 相对路径直接使用
"""

import os
import re
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Tuple, List


@dataclass
class AgentReference:
    """Agent 引用"""
    raw_ref: str              # 原始引用字符串
    domain: str               # 域 (dev, research, analysis, ...)
    name: str                 # Agent 名称 (snake_case)
    version: str              # 版本 (default: v1)
    is_path: bool             # 是否为直接路径引用

    @property
    def kebab_name(self) -> str:
        """转换为 kebab-case 名称 (用于文件路径)"""
        return self.name.replace("_", "-")


class AgentResolver:
    """Agent 引用解析器

    将 agent 引用 (如 agent.dev.tech_lead) 解析为 spec 文件路径。
    """

    # 域到路径的映射
    DOMAIN_PATHS = {
        # 研发类 -> org/development
        "dev": "specs/org/development/agents",

        # 其他域 -> common
        "research": "specs/common/agents",
        "analysis": "specs/common/agents",
        "product": "specs/common/agents",
        "review": "specs/common/agents",
        "governance": "specs/common/agents",
        "freeze": "specs/common/agents",
        "orchestration": "specs/common/agents",
        "planning": "specs/common/agents",
        "design": "specs/common/agents",  # UI/图标设计类
    }

    # 默认查找路径 (当域对应路径找不到时)
    FALLBACK_PATHS = [
        "specs/common/agents",
        "specs/org/development/agents",
    ]

    def __init__(self, project_root: str, spec_root: str = None):
        """初始化解析器

        Args:
            project_root: 项目根目录
            spec_root: spec 根目录 (默认为 project_root/ai-spec)
        """
        self.project_root = Path(project_root)
        self.spec_root = Path(spec_root) if spec_root else self.project_root / "ai-spec"

    def parse_reference(self, ref: str) -> AgentReference:
        """解析 agent 引用字符串

        Args:
            ref: agent 引用 (如 agent.dev.tech_lead, agent.dev.tech_lead@v2, ./path.yaml)

        Returns:
            AgentReference 对象

        Raises:
            ValueError: 引用格式错误
        """
        ref = ref.strip()

        # 检查是否为直接路径引用
        if ref.startswith("./") or ref.startswith("../") or ref.endswith(".yaml") or ref.endswith(".yml"):
            return AgentReference(
                raw_ref=ref,
                domain="",
                name="",
                version="",
                is_path=True
            )

        # 解析版本后缀 (如 @v2)
        version = "v1"
        if "@" in ref:
            ref, version = ref.rsplit("@", 1)

        # 解析 agent.domain.name 格式
        parts = ref.split(".")

        if len(parts) == 3 and parts[0] == "agent":
            domain = parts[1]
            name = parts[2]
        elif len(parts) == 2:
            # 简写格式: domain.name (假设 agent 前缀)
            domain = parts[0]
            name = parts[1]
        elif len(parts) == 1:
            # 只有名称，尝试自动推断域
            domain = ""
            name = parts[0]
        else:
            raise ValueError(
                f"Invalid agent reference format: '{ref}'. "
                f"Expected: agent.<domain>.<name> or <domain>.<name> or <name>"
            )

        return AgentReference(
            raw_ref=ref,
            domain=domain,
            name=name,
            version=version,
            is_path=False
        )

    def resolve(self, ref: str) -> Optional[Path]:
        """解析 agent 引用到 spec 文件路径

        Args:
            ref: agent 引用

        Returns:
            spec 文件的绝对路径，如果找不到返回 None
        """
        agent_ref = self.parse_reference(ref)

        if agent_ref.is_path:
            # 直接路径引用
            path = Path(agent_ref.raw_ref)
            if not path.is_absolute():
                path = self.project_root / path
            return path if path.exists() else None

        # 尝试按域查找
        paths_to_try = self._get_search_paths(agent_ref)

        for search_path in paths_to_try:
            spec_path = search_path / agent_ref.kebab_name / agent_ref.version / "agent.yaml"
            if spec_path.exists():
                return spec_path

        return None

    def resolve_or_raise(self, ref: str) -> Path:
        """解析 agent 引用，找不到时抛出异常

        Args:
            ref: agent 引用

        Returns:
            spec 文件的绝对路径

        Raises:
            AgentSpecNotFound: spec 文件不存在
        """
        path = self.resolve(ref)
        if path is None:
            agent_ref = self.parse_reference(ref)
            paths_tried = self._get_search_paths(agent_ref)
            raise AgentSpecNotFound(
                ref,
                [str(p / agent_ref.kebab_name / agent_ref.version / "agent.yaml")
                 for p in paths_tried]
            )
        return path

    def _get_search_paths(self, agent_ref: AgentReference) -> List[Path]:
        """获取搜索路径列表"""
        paths = []

        # 如果指定了域，先尝试域对应路径
        if agent_ref.domain and agent_ref.domain in self.DOMAIN_PATHS:
            domain_path = self.spec_root / self.DOMAIN_PATHS[agent_ref.domain]
            paths.append(domain_path)

        # 添加 fallback 路径
        for fallback in self.FALLBACK_PATHS:
            fallback_path = self.spec_root / fallback
            if fallback_path not in paths:
                paths.append(fallback_path)

        return paths

    def list_available_agents(self) -> List[Tuple[str, Path]]:
        """列出所有可用的 agent specs

        Returns:
            (agent_id, spec_path) 列表
        """
        agents = []

        for domain, rel_path in self.DOMAIN_PATHS.items():
            agents_dir = self.spec_root / rel_path
            if not agents_dir.exists():
                continue

            for agent_dir in agents_dir.iterdir():
                if not agent_dir.is_dir():
                    continue

                # 查找最新版本
                versions = sorted([d.name for d in agent_dir.iterdir()
                                   if d.is_dir() and d.name.startswith("v")],
                                  reverse=True)

                if versions:
                    spec_path = agent_dir / versions[0] / "agent.yaml"
                    if spec_path.exists():
                        # 转换目录名回 snake_case
                        agent_name = agent_dir.name.replace("-", "_")
                        agent_id = f"agent.{domain}.{agent_name}"
                        agents.append((agent_id, spec_path))

        return agents

    def validate_workflow_agents(self, workflow_data: dict) -> List[Tuple[str, str, bool, Optional[str]]]:
        """验证 workflow 中所有 agent 引用

        Args:
            workflow_data: 解析后的 workflow 数据

        Returns:
            [(step_id, agent_ref, is_valid, error_message), ...]
        """
        results = []

        steps = workflow_data.get("steps", [])
        for step in steps:
            step_id = step.get("id", "unknown")
            agent_ref = step.get("run", "")

            if not agent_ref:
                results.append((step_id, "", True, None))
                continue

            try:
                path = self.resolve(agent_ref)
                if path:
                    results.append((step_id, agent_ref, True, None))
                else:
                    results.append((step_id, agent_ref, False, "Spec file not found"))
            except ValueError as e:
                results.append((step_id, agent_ref, False, str(e)))

        return results


class AgentSpecNotFound(Exception):
    """Agent spec 文件未找到"""

    def __init__(self, ref: str, paths_tried: List[str]):
        self.ref = ref
        self.paths_tried = paths_tried
        super().__init__(
            f"Agent spec not found: '{ref}'. "
            f"Searched paths:\n  " + "\n  ".join(paths_tried)
        )
