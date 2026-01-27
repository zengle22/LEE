"""
Agent Spec Loader

加载和解析 Agent YAML 规范文件。
"""

import os
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any

from .agent_resolver import AgentResolver, AgentSpecNotFound


@dataclass
class AgentSpec:
    """Agent 规范数据结构"""

    # 基础信息
    id: str
    name: str
    version: str
    description: str = ""

    # 角色定义
    persona: Dict[str, Any] = field(default_factory=dict)  # role, style, tone

    # 提示工程
    prompting: Dict[str, Any] = field(default_factory=dict)  # system, instructions

    # 策略
    policy: Dict[str, Any] = field(default_factory=dict)  # decision_rules, quality_bar

    # 职责边界
    responsibility: Dict[str, Any] = field(default_factory=dict)  # in_scope, out_of_scope

    # 契约
    contracts: Dict[str, str] = field(default_factory=dict)  # input_schema, output_schema

    # 禁止行为
    forbidden_behaviors: List[str] = field(default_factory=list)

    # 知识库访问
    knowledge_access: Optional[Dict[str, Any]] = None

    # 人类确认点
    human_confirmation: Optional[Dict[str, Any]] = None

    # 技能引用
    skills: List[str] = field(default_factory=list)

    # 原始数据
    raw_data: Dict[str, Any] = field(default_factory=dict)

    # spec 文件路径
    spec_path: Optional[str] = None

    def get_system_prompt(self) -> str:
        """获取 system prompt"""
        return self.prompting.get("system", "")

    def get_instructions(self) -> List[str]:
        """获取指令列表"""
        return self.prompting.get("instructions", [])

    def get_quality_bar(self) -> List[str]:
        """获取质量标准"""
        return self.policy.get("quality_bar", {}).get("must_have", [])

    def get_decision_rules(self) -> List[Dict]:
        """获取决策规则"""
        return self.policy.get("decision_rules", [])

    def get_forbidden_behaviors_text(self) -> str:
        """获取禁止行为的文本描述"""
        if not self.forbidden_behaviors:
            return ""

        lines = ["禁止行为:"]
        for i, behavior in enumerate(self.forbidden_behaviors, 1):
            if isinstance(behavior, dict):
                lines.append(f"  {i}. {behavior.get('name', behavior.get('id', 'Unknown'))}")
                if behavior.get('violation_example'):
                    lines.append(f"     违规示例: {behavior['violation_example']}")
            else:
                lines.append(f"  {i}. {behavior}")

        return "\n".join(lines)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "persona": self.persona,
            "prompting": {
                "system": self.get_system_prompt(),
                "instructions": self.get_instructions(),
            },
            "policy": {
                "quality_bar": self.get_quality_bar(),
                "decision_rules": self.get_decision_rules(),
            },
            "responsibility": self.responsibility,
            "contracts": self.contracts,
            "forbidden_behaviors": self.forbidden_behaviors,
            "knowledge_access": self.knowledge_access,
            "human_confirmation": self.human_confirmation,
            "skills": self.skills,
        }

    @classmethod
    def default(cls) -> 'AgentSpec':
        """创建默认 Agent (通用 AI 助手)"""
        return cls(
            id="agent.default",
            name="Default AI Assistant",
            version="1.0",
            description="通用 AI 助手，无特定角色约束",
            persona={
                "role": "AI 助手",
                "style": "helpful, accurate, concise",
                "tone": "professional",
            },
            prompting={
                "system": "You are a helpful AI assistant.",
                "instructions": [],
            },
        )


class AgentSpecInvalid(Exception):
    """Agent spec 格式无效"""

    def __init__(self, path: str, errors: List[str]):
        self.path = path
        self.errors = errors
        super().__init__(
            f"Invalid agent spec at '{path}':\n  " + "\n  ".join(errors)
        )


class AgentLoader:
    """Agent Spec 加载器

    加载和解析 Agent YAML 规范文件。

    P2-01 改进: 添加内存缓存，避免重复加载相同的 agent spec。
    """

    # 必填字段
    REQUIRED_FIELDS = ["id", "name"]

    # 建议字段 (缺失时警告)
    RECOMMENDED_FIELDS = ["persona", "prompting", "responsibility"]

    # 类级别缓存 (所有实例共享)
    _cache: Dict[str, AgentSpec] = {}

    def __init__(self, project_root: str, spec_root: str = None):
        """初始化加载器

        Args:
            project_root: 项目根目录
            spec_root: spec 根目录 (默认为 project_root/ai-spec)
        """
        self.project_root = Path(project_root)
        self.resolver = AgentResolver(project_root, spec_root)
        self._debug = os.environ.get("ORCHESTRATOR_DEBUG_AGENT") == "1"
        self._strict = os.environ.get("ORCHESTRATOR_STRICT_AGENT") == "1"

        # 环境变量控制是否启用缓存
        self._cache_enabled = os.environ.get("ORCHESTRATOR_AGENT_CACHE_ENABLED", "1") == "1"

    @classmethod
    def invalidate_cache(cls, agent_ref: str = None) -> None:
        """清除缓存

        Args:
            agent_ref: 要清除的 agent 引用，如果为 None 则清除所有缓存
        """
        if agent_ref is None:
            cls._cache.clear()
            if os.environ.get("ORCHESTRATOR_DEBUG_AGENT") == "1":
                print(f"[DEBUG] Cleared all agent cache")
        else:
            if agent_ref in cls._cache:
                del cls._cache[agent_ref]
                if os.environ.get("ORCHESTRATOR_DEBUG_AGENT") == "1":
                    print(f"[DEBUG] Cleared cache for: {agent_ref}")

    @classmethod
    def get_cache_stats(cls) -> Dict[str, Any]:
        """获取缓存统计信息"""
        return {
            "cache_size": len(cls._cache),
            "cached_agents": list(cls._cache.keys()),
        }

    def _get_cache_key(self, agent_ref: str) -> str:
        """生成缓存键

        Args:
            agent_ref: agent 引用

        Returns:
            缓存键 (结合项目路径和 agent ref 确保唯一性)
        """
        project_key = str(self.project_root.resolve())
        return f"{project_key}:{agent_ref}"

    def _is_cached(self, cache_key: str) -> bool:
        """检查是否已缓存"""
        return cache_key in self._cache

    def _get_from_cache(self, cache_key: str) -> Optional[AgentSpec]:
        """从缓存获取"""
        return self._cache.get(cache_key)

    def _set_cache(self, cache_key: str, spec: AgentSpec) -> None:
        """设置缓存"""
        if self._cache_enabled:
            self._cache[cache_key] = spec

    def load(self, agent_ref: str) -> AgentSpec:
        """加载 Agent 规范

        P2-01 改进: 先检查缓存，命中则直接返回，否则从文件加载并缓存。

        Args:
            agent_ref: agent 引用 (如 agent.dev.tech_lead)

        Returns:
            AgentSpec 对象

        Raises:
            AgentSpecNotFound: spec 文件不存在 (严格模式)
            AgentSpecInvalid: spec 格式无效
        """
        # P2-01: 检查缓存
        cache_key = self._get_cache_key(agent_ref)
        if self._cache_enabled and self._is_cached(cache_key):
            if self._debug:
                print(f"[DEBUG] Agent spec cache hit: {agent_ref}")
            return self._get_from_cache(cache_key)

        # 解析引用到路径
        spec_path = self.resolver.resolve(agent_ref)

        if spec_path is None:
            if self._strict:
                raise AgentSpecNotFound(agent_ref, [])
            if self._debug:
                print(f"[DEBUG] Agent spec not found: {agent_ref}, using default")
            return AgentSpec.default()

        spec = self.load_from_path(spec_path)

        # P2-01: 缓存结果
        if spec is not None:
            self._set_cache(cache_key, spec)
            if self._debug and self._cache_enabled:
                print(f"[DEBUG] Agent spec cached: {agent_ref}")

        return spec

    def load_from_path(self, spec_path: Path) -> AgentSpec:
        """从文件路径加载 Agent 规范

        Args:
            spec_path: spec 文件路径

        Returns:
            AgentSpec 对象

        Raises:
            AgentSpecInvalid: spec 格式无效
        """
        if self._debug:
            print(f"[DEBUG] Loading agent spec from: {spec_path}")

        try:
            with open(spec_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise AgentSpecInvalid(str(spec_path), [f"YAML parse error: {e}"])
        except IOError as e:
            raise AgentSpecInvalid(str(spec_path), [f"IO error: {e}"])

        return self._parse_spec(data, str(spec_path))

    def _parse_spec(self, data: Dict[str, Any], spec_path: str) -> AgentSpec:
        """解析 spec 数据

        支持两种格式:
        1. 顶层格式: id, name 在根级别
        2. metadata 格式: id, name 在 metadata 对象中 (v2.x agent spec)
        """
        errors = []
        warnings = []

        # 提取 metadata (v2.x 格式支持)
        metadata = data.get("metadata", {})

        # 验证必填字段 (支持顶层或 metadata 中)
        for field_name in self.REQUIRED_FIELDS:
            if field_name not in data and field_name not in metadata:
                errors.append(f"Missing required field: {field_name}")

        if errors:
            raise AgentSpecInvalid(spec_path, errors)

        # 检查建议字段
        for field_name in self.RECOMMENDED_FIELDS:
            if field_name not in data:
                warnings.append(f"Missing recommended field: {field_name}")

        if self._debug and warnings:
            for warning in warnings:
                print(f"[DEBUG] Warning: {warning}")

        # 提取禁止行为
        forbidden = data.get("forbidden_behaviors", [])
        if isinstance(forbidden, list):
            forbidden_behaviors = forbidden
        else:
            forbidden_behaviors = []

        # 提取技能引用
        skills_data = data.get("skills", [])
        skills = []
        for skill in skills_data:
            if isinstance(skill, dict):
                skills.append(skill.get("ref", ""))
            else:
                skills.append(str(skill))

        # 提取字段 (优先顶层，回退到 metadata)
        def get_field(field_name: str, default=""):
            return data.get(field_name) or metadata.get(field_name) or default

        # 提取 persona (支持 role 对象格式)
        persona = data.get("persona", {})
        role_data = data.get("role", {})
        if role_data and not persona:
            persona = role_data

        return AgentSpec(
            id=get_field("id"),
            name=get_field("name"),
            version=str(get_field("version", "1.0")),
            description=get_field("description"),
            persona=persona,
            prompting=data.get("prompting", {}),
            policy=data.get("policy", {}),
            responsibility=data.get("responsibility", {}),
            contracts=data.get("contracts", {}),
            forbidden_behaviors=forbidden_behaviors,
            knowledge_access=data.get("knowledge_access"),
            human_confirmation=data.get("human_confirmation"),
            skills=skills,
            raw_data=data,
            spec_path=spec_path,
        )

    def load_safe(self, agent_ref: str) -> Optional[AgentSpec]:
        """安全加载 Agent 规范，出错时返回 None

        Args:
            agent_ref: agent 引用

        Returns:
            AgentSpec 对象或 None
        """
        try:
            return self.load(agent_ref)
        except (AgentSpecNotFound, AgentSpecInvalid) as e:
            if self._debug:
                print(f"[DEBUG] Failed to load agent: {e}")
            return None
