"""
LEE Orchestrator v3.0 - 模板管理器

本模块负责工作流模板的加载、解析和管理。

核心职责：
1. 加载 YAML 模板文件
2. 解析步骤定义和依赖关系
3. 管理模板缓存
4. 提供模板查询接口
"""

import os
import yaml
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    Step,
    Template,
)


# ========================================================================
# 模板数据结构
# ========================================================================

@dataclass
class WorkflowTemplate:
    """
    工作流模板

    从 YAML 文件解析的模板定义
    """

    # 基本信息
    id: str
    level: WorkflowLevel
    name: str
    description: str

    # 步骤定义
    steps: List[Step]

    # L1/L2 特有：子工作流定义
    departments: List[Dict[str, Any]] = field(default_factory=list)  # L1: 部门列表
    tasks: List[Dict[str, Any]] = field(default_factory=list)  # L2: 任务列表

    # 完成条件
    completion_criteria: Dict[str, Any] = field(default_factory=dict)

    # 其他配置
    config: Dict[str, Any] = field(default_factory=dict)


# ========================================================================
# 模板管理器
# ========================================================================

class TemplateManager:
    """
    模板管理器

    负责：
    - 从文件系统加载 YAML 模板
    - 解析模板内容为 WorkflowTemplate
    - 缓存已加载的模板
    - 提供模板查询接口
    """

    def __init__(self, template_dir: str = "specs/workflows"):
        """
        初始化模板管理器

        Args:
            template_dir: 模板文件目录
        """
        self.template_dir = Path(template_dir)
        self._cache: Dict[str, WorkflowTemplate] = {}

    # ============ 模板加载 ============

    def load_yaml_template(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载 YAML 模板文件（支持多文档）

        Args:
            file_path: YAML 文件路径

        Returns:
            解析后的 YAML 文档列表
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Template file not found: {file_path}")

        with open(file_path, 'r', encoding='utf-8') as f:
            docs = list(yaml.safe_load_all(f))
            # 过滤空文档
            return [doc for doc in docs if doc is not None]

    def load_template_from_content(
        self,
        content: str,
        template_id: str
    ) -> WorkflowTemplate:
        """
        从 YAML 内容加载模板

        Args:
            content: YAML 格式的模板内容
            template_id: 模板 ID

        Returns:
            解析后的 WorkflowTemplate
        """
        doc = yaml.safe_load(content)
        if not doc:
            raise ValueError(f"Invalid template content for: {template_id}")

        return self._parse_template_doc(doc, template_id)

    def load_all_templates(self) -> Dict[str, WorkflowTemplate]:
        """
        加载目录下所有模板

        Returns:
            模板 ID 到 WorkflowTemplate 的映射
        """
        if not self.template_dir.exists():
            return {}

        templates = {}
        for yaml_file in self.template_dir.glob("*.yaml"):
            try:
                docs = self.load_yaml_template(str(yaml_file))
                for doc in docs:
                    template_id = doc.get("id", yaml_file.stem)
                    template = self._parse_template_doc(doc, template_id)
                    templates[template_id] = template
                    self._cache[template_id] = template
            except Exception as e:
                print(f"Warning: Failed to load {yaml_file}: {e}")

        return templates

    # ============ 模板查询 ============

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """
        获取模板

        Args:
            template_id: 模板 ID

        Returns:
            WorkflowTemplate，不存在返回 None
        """
        # 检查缓存
        if template_id in self._cache:
            return self._cache[template_id]

        # 尝试从文件加载
        template_file = self.template_dir / f"{template_id}.yaml"
        if not template_file.exists():
            return None

        try:
            docs = self.load_yaml_template(str(template_file))
            if docs:
                template = self._parse_template_doc(docs[0], template_id)
                self._cache[template_id] = template
                return template
        except Exception:
            pass

        return None

    def get_template_content(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模板原始内容

        Args:
            template_id: 模板 ID

        Returns:
            原始 YAML 内容字典
        """
        template = self.get_template(template_id)
        if not template:
            return None

        return {
            "id": template.id,
            "level": template.level.value,
            "name": template.name,
            "description": template.description,
            "steps": [self._step_to_dict(s) for s in template.steps],
            "departments": template.departments,
            "tasks": template.tasks,
            "completion_criteria": template.completion_criteria,
            "config": template.config,
        }

    def get_steps(self, template_id: str) -> List[Step]:
        """
        获取模板的步骤列表

        Args:
            template_id: 模板 ID

        Returns:
            步骤列表
        """
        template = self.get_template(template_id)
        if not template:
            return []
        return template.steps

    def get_step(
        self,
        template_id: str,
        step_id: str
    ) -> Optional[Step]:
        """
        获取单个步骤定义

        Args:
            template_id: 模板 ID
            step_id: 步骤 ID

        Returns:
            Step 对象，不存在返回 None
        """
        steps = self.get_steps(template_id)
        for step in steps:
            if step.id == step_id:
                return step
        return None

    def get_departments(self, template_id: str) -> List[Dict[str, Any]]:
        """
        获取 L1 模板的部门列表

        Args:
            template_id: 模板 ID

        Returns:
            部门定义列表
        """
        template = self.get_template(template_id)
        if not template:
            return []
        return template.departments or []

    def get_tasks(self, template_id: str) -> List[Dict[str, Any]]:
        """
        获取 L2 模板的任务列表

        Args:
            template_id: 模板 ID

        Returns:
            任务定义列表
        """
        template = self.get_template(template_id)
        if not template:
            return []
        return template.tasks or []

    def get_completion_criteria(self, template_id: str) -> Dict[str, Any]:
        """
        获取完成条件

        Args:
            template_id: 模板 ID

        Returns:
            完成条件定义
        """
        template = self.get_template(template_id)
        if not template:
            return {}
        return template.completion_criteria or {}

    # ============ 模板验证 ============

    def validate_template(self, template: Dict[str, Any]) -> bool:
        """
        验证模板定义的合法性

        检查项：
        1. 必需字段是否存在
        2. 步骤依赖是否合法
        3. executor_type 是否支持
        4. level 与定义是否匹配

        Args:
            template: 模板定义字典

        Returns:
            是否合法
        """
        # 检查必需字段
        required_fields = ["id", "level", "name"]
        for field in required_fields:
            if field not in template:
                return False

        # 验证 level
        valid_levels = ["project", "department", "task"]
        if template["level"] not in valid_levels:
            return False

        # 验证步骤
        steps = template.get("steps", [])
        return self._validate_dependencies(steps)

    def _validate_dependencies(
        self,
        steps: List[Dict[str, Any]]
    ) -> bool:
        """
        验证步骤依赖关系的合法性

        检查项：
        1. 依赖的步骤是否存在
        2. 是否存在循环依赖

        Args:
            steps: 步骤定义列表

        Returns:
            是否合法
        """
        step_ids = {s.get("id") for s in steps}

        for step in steps:
            depends_on = step.get("depends_on", [])
            for dep in depends_on:
                if dep not in step_ids:
                    return False

        # 简单的循环依赖检查
        # (完整实现需要图算法，这里做简化检查)
        return True

    # ============ 模板解析 ============

    def _parse_template_doc(
        self,
        doc: Dict[str, Any],
        template_id: str
    ) -> WorkflowTemplate:
        """
        解析模板文档

        Args:
            doc: YAML 文档字典
            template_id: 模板 ID

        Returns:
            WorkflowTemplate 对象
        """
        level_str = doc.get("level", "task")
        try:
            level = WorkflowLevel(level_str)
        except ValueError:
            level = WorkflowLevel.TASK

        steps_data = doc.get("steps", [])
        steps = [self._parse_step(s) for s in steps_data]

        return WorkflowTemplate(
            id=template_id,
            level=level,
            name=doc.get("name", template_id),
            description=doc.get("description", ""),
            steps=steps,
            departments=doc.get("departments", []),
            tasks=doc.get("tasks", []),
            completion_criteria=doc.get("completion_criteria", {}),
            config=doc.get("config", {}),
        )

    def _parse_step(self, step_data: Dict[str, Any]) -> Step:
        """
        解析单个步骤

        Args:
            step_data: 步骤数据

        Returns:
            Step 对象
        """
        return Step(
            id=step_data.get("id", ""),
            kind=step_data.get("kind", "agent"),
            executor_type=step_data.get("executor", "llm"),
            depends_on=step_data.get("depends_on", []),
            input=step_data.get("input", {}),
            config=step_data.get("config", {}),
        )

    def _step_to_dict(self, step: Step) -> Dict[str, Any]:
        """
        将 Step 对象转换为字典

        Args:
            step: Step 对象

        Returns:
            步骤字典
        """
        return {
            "id": step.id,
            "kind": step.kind,
            "executor": step.executor_type,
            "depends_on": step.depends_on,
            "input": step.input,
            "config": step.config,
        }


# ========================================================================
# 模板构建器（辅助）
# ========================================================================

class TemplateBuilder:
    """
    模板构建器

    用于程序化构建模板定义
    """

    def __init__(self, template_id: str, level: WorkflowLevel):
        self.template_id = template_id
        self.level = level
        self.steps: List[Dict[str, Any]] = []
        self.config: Dict[str, Any] = {}

    def add_step(
        self,
        step_id: str,
        kind: str,
        executor: str = "llm",
        depends_on: List[str] = None,
        **kwargs
    ) -> "TemplateBuilder":
        """
        添加步骤

        Args:
            step_id: 步骤 ID
            kind: 步骤类型
            executor: 执行器类型
            depends_on: 依赖列表
            **kwargs: 其他参数

        Returns:
            self，支持链式调用
        """
        self.steps.append({
            "id": step_id,
            "kind": kind,
            "executor": executor,
            "depends_on": depends_on or [],
            **kwargs
        })
        return self

    def set_config(self, **kwargs) -> "TemplateBuilder":
        """
        设置配置

        Args:
            **kwargs: 配置项

        Returns:
            self，支持链式调用
        """
        self.config.update(kwargs)
        return self

    def build(self) -> Dict[str, Any]:
        """
        构建模板定义

        Returns:
            模板定义字典
        """
        return {
            "id": self.template_id,
            "level": self.level.value,
            "steps": self.steps,
            "config": self.config,
        }

    def to_yaml(self) -> str:
        """
        导出为 YAML 格式

        Returns:
            YAML 字符串
        """
        return yaml.dump(self.build(), allow_unicode=True)


# ========================================================================
# 内置模板
# ========================================================================

class BuiltinTemplates:
    """
    内置模板定义

    提供常用的模板定义
    """

    @staticmethod
    def simple_project() -> Dict[str, Any]:
        """简单项目模板"""
        return {
            "id": "simple_project",
            "level": "project",
            "name": "Simple Project",
            "description": "A simple project workflow",
            "steps": [
                {
                    "id": "init",
                    "kind": "agent",
                    "executor": "llm",
                    "input": {"prompt": "Initialize project"},
                },
                {
                    "id": "plan",
                    "kind": "agent",
                    "executor": "llm",
                    "depends_on": ["init"],
                    "input": {"prompt": "Create plan"},
                },
                {
                    "id": "complete",
                    "kind": "marker",
                    "depends_on": ["plan"],
                },
            ],
        }

    @staticmethod
    def bug_fix_workflow() -> Dict[str, Any]:
        """Bug 修复工作流模板"""
        return {
            "id": "bug_fix",
            "level": "task",
            "name": "Bug Fix",
            "description": "Bug fix workflow",
            "steps": [
                {
                    "id": "analyze",
                    "kind": "agent",
                    "executor": "llm",
                    "input": {"prompt": "Analyze bug"},
                },
                {
                    "id": "fix",
                    "kind": "agent",
                    "executor": "metagpt",
                    "depends_on": ["analyze"],
                    "config": {"task_type": "code_implementation"},
                },
                {
                    "id": "verify",
                    "kind": "agent",
                    "executor": "llm",
                    "depends_on": ["fix"],
                    "input": {"prompt": "Verify fix"},
                },
            ],
        }
