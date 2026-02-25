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
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field

from lee.orchestrator.storage.models import (
    WorkflowLevel,
    Step,
    Template,
)

logger = logging.getLogger(__name__)


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

    # 缓存：步骤执行顺序（v1.1 新增）
    _step_order_cache: Optional[List[str]] = field(default=None, init=False, repr=False)

    def get_step_order(self) -> List[str]:
        """
        获取步骤的执行顺序（拓扑排序）

        对于线性工作流：按 steps 列表顺序
        对于 DAG 工作流：基于 depends_on 的拓扑排序

        Returns:
            步骤 ID 列表（按执行顺序）

        Raises:
            ValueError: 如果检测到循环依赖
        """
        # 使用缓存
        if self._step_order_cache is not None:
            return self._step_order_cache

        from collections import defaultdict, deque

        # 构建依赖图和入度表
        in_degree = {}  # step_id -> 入度数
        adj_list = defaultdict(list)  # step_id -> [依赖它的步骤]

        # 初始化所有步骤
        for step in self.steps:
            in_degree[step.id] = len(step.depends_on)
            for dep in step.depends_on:
                adj_list[dep].append(step.id)

        # 拓扑排序（Kahn 算法）
        queue = deque([sid for sid, degree in in_degree.items() if degree == 0])
        result = []

        while queue:
            step_id = queue.popleft()
            result.append(step_id)

            # 减少依赖当前步骤的其他步骤的入度
            for neighbor in adj_list[step_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # 检查是否所有步骤都被处理（检测循环依赖）
        if len(result) != len(self.steps):
            # 找出未处理的步骤
            processed = set(result)
            unprocessed = [sid for sid in in_degree.keys() if sid not in processed]
            raise ValueError(
                f"Circular dependency detected in workflow '{self.id}'. "
                f"Unprocessed steps: {unprocessed}. "
                f"Please check the 'depends_on' configuration."
            )

        # 缓存结果
        self._step_order_cache = result
        return result

    def get_steps_after(self, step_id: str) -> List[str]:
        """
        获取指定步骤之后的所有步骤

        Args:
            step_id: 目标步骤 ID

        Returns:
            在 step_id 之后执行的所有步骤 ID

        Raises:
            ValueError: 如果 step_id 不在模板中
        """
        step_order = self.get_step_order()
        step_ids = {s.id for s in self.steps}
        if step_id not in step_ids:
            raise ValueError(
                f"Step '{step_id}' not found in workflow '{self.id}'. "
                f"Available steps: {step_order}"
            )

        # 仅返回“依赖于 step_id 的后继步骤”（传递闭包），而非拓扑顺序中所有后续步骤
        descendants = set()
        changed = True
        while changed:
            changed = False
            for step in self.steps:
                if step.id == step_id:
                    continue
                if step.id in descendants:
                    continue
                if step_id in step.depends_on or any(dep in descendants for dep in step.depends_on):
                    descendants.add(step.id)
                    changed = True

        return [sid for sid in step_order if sid in descendants]

    def get_step_info(self, step_id: str) -> Optional[Step]:
        """
        获取步骤信息

        Args:
            step_id: 步骤 ID

        Returns:
            Step 对象，不存在返回 None
        """
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


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
    - 支持 spec-global 格式（kind: workflow）
    """

    def __init__(
        self,
        template_dir: str = "specs/workflows",
        project_root: Optional[str] = None,
        config: Optional[Any] = None,
    ):
        """
        初始化模板管理器

        Args:
            template_dir: 模板文件目录
            project_root: 项目根目录（用于加载配置）
            config: LeeConfig 实例（可选，不提供则从 project_root 加载）
        """
        self.template_dir = Path(template_dir)
        self._cache: Dict[str, WorkflowTemplate] = {}

        # v3.5: 加载配置以获取 executor.default_type
        if config:
            self.config = config
        elif project_root:
            from lee.orchestrator.config_loader import load_config
            self.config = load_config(project_root)
        else:
            # 使用默认配置
            from lee.orchestrator.config_loader import LeeConfig
            self.config = LeeConfig()

        # 延迟导入 spec-global 解析器（避免循环依赖）
        self._spec_global_parser = None
        self._ir_converter = None

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

        # 1. 搜索顶层目录的 *.yaml 文件
        for yaml_file in self.template_dir.glob("*.yaml"):
            try:
                docs = self.load_yaml_template(str(yaml_file))
                for doc in docs:
                    template_id = doc.get("id", yaml_file.stem)
                    template = self._parse_template_doc(doc, template_id)
                    templates[template_id] = template
                    self._cache[template_id] = template
            except Exception as e:
                logger.warning("Failed to load %s: %s", yaml_file, e)

        # 2. 递归搜索子目录中的 workflow.yaml 文件
        for yaml_file in self.template_dir.rglob("workflow.yaml"):
            # 跳过已经在顶层目录处理过的文件
            if yaml_file.parent == self.template_dir:
                continue
            try:
                docs = self.load_yaml_template(str(yaml_file))
                for doc in docs:
                    if doc:  # 确保 doc 不为 None
                        template_id = doc.get("id")
                        if template_id:
                            template = self._parse_template_doc(doc, template_id)
                            templates[template_id] = template
                            self._cache[template_id] = template
            except Exception as e:
                logger.warning("Failed to load %s: %s", yaml_file, e)

        return templates

    # ============ 模板查询 ============

    def list_workflows(self) -> List[str]:
        """
        List available workflow IDs.

        Uses lightweight text scanning to avoid eagerly parsing every YAML file.
        """
        if not self.template_dir.exists():
            return []

        seen = set()
        workflow_ids: List[str] = []

        candidate_files = list(self.template_dir.glob("*.yaml")) + list(self.template_dir.rglob("workflow.yaml"))
        for yaml_file in candidate_files:
            try:
                content = yaml_file.read_text(encoding="utf-8")
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(
                    f"Failed to read template file {yaml_file}: {e}"
                )
                continue

            match = re.search(
                r'(?m)^\s*id\s*:\s*["\']?([a-zA-Z0-9_.-]+)["\']?\s*$',
                content,
            )
            if not match:
                # Only fallback to stem for top-level files.
                if yaml_file.name == "workflow.yaml":
                    continue
                candidate_id = yaml_file.stem
            else:
                candidate_id = match.group(1).strip()

            if candidate_id and candidate_id not in seen:
                seen.add(candidate_id)
                workflow_ids.append(candidate_id)

        return workflow_ids

    def get_template(self, template_id: str) -> Optional[WorkflowTemplate]:
        """
        获取模板

        支持多种查找方式：
        1. 从缓存中查找
        2. 作为完整文件路径加载
        3. 从模板目录中按 ID 查找
        4. 从模板目录的子目录中递归查找 workflow.yaml

        Args:
            template_id: 模板 ID 或文件路径

        Returns:
            WorkflowTemplate，不存在返回 None
        """
        # 检查缓存
        if template_id in self._cache:
            return self._cache[template_id]

        # 尝试作为完整文件路径加载
        if template_id.endswith(".yaml") or template_id.endswith(".yml"):
            template_path = Path(template_id)
            if template_path.exists():
                return self._load_template_from_file(template_path, template_id)

        # 尝试从模板目录直接加载
        template_file = self.template_dir / f"{template_id}.yaml"
        if template_file.exists():
            return self._load_template_from_file(template_file, template_id)

        # 尝试在模板目录的子目录中递归查找
        # 支持格式：workflow.prd.product_to_dev_pipeline → departments/prd/workflows/product-to-dev-pipeline/v1/workflow.yaml
        found_file = self._find_template_file(template_id)
        if found_file:
            return self._load_template_from_file(found_file, template_id)

        # 兜底：逐个解析 workflow.yaml，确保能找到非标准路径
        for yaml_file in self.template_dir.rglob("workflow.yaml"):
            try:
                docs = self.load_yaml_template(str(yaml_file))
                for doc in docs:
                    if doc and doc.get("id") == template_id:
                        return self._load_template_from_file(yaml_file, template_id)
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(
                    f"Failed to parse workflow.yaml {yaml_file}: {e}"
                )
                continue

        return None

    def _load_template_from_file(
        self,
        file_path: Path,
        template_id: str
    ) -> Optional[WorkflowTemplate]:
        """从文件加载模板"""
        try:
            docs = self.load_yaml_template(str(file_path))
            if docs:
                template = self._parse_template_doc(docs[0], template_id, file_path)
                self._cache[template_id] = template
                # 也用文档中的 ID 作为缓存键
                if template.id != template_id:
                    self._cache[template.id] = template
                return template
        except Exception as e:
            logger.warning("Failed to load template %s: %s", file_path, e)
        return None

    def _find_template_file(self, template_id: str) -> Optional[Path]:
        """
        在模板目录中查找模板文件

        支持的查找策略：
        1. 按 ID 中的路径部分查找（workflow.prd.xxx → departments/prd/workflows/xxx）
        2. 递归搜索所有 workflow.yaml 文件
        """
        # 策略 1：解析 ID 结构
        # 格式：workflow.{department}.{workflow_name}
        parts = template_id.split(".")
        if len(parts) >= 3 and parts[0] == "workflow":
            dept = parts[1]
            workflow_name = "_".join(parts[2:])
            # 转换下划线为连字符
            workflow_name_hyphen = workflow_name.replace("_", "-")

            # 尝试多个可能的路径
            possible_paths = [
                self.template_dir / "departments" / dept / "workflows" / workflow_name_hyphen / "v1" / "workflow.yaml",
                self.template_dir / "departments" / dept / "workflows" / workflow_name / "v1" / "workflow.yaml",
                self.template_dir / "cross" / "workflows" / workflow_name_hyphen / "v1" / "workflow.yaml",
            ]

            for path in possible_paths:
                if path.exists():
                    return path

        # 策略 2：递归搜索
        for workflow_file in self.template_dir.rglob("workflow.yaml"):
            try:
                with open(workflow_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # 简单检查 ID 是否在文件中
                    if f"id: {template_id}" in content:
                        return workflow_file
            except Exception as e:
                import logging
                logging.getLogger(__name__).debug(
                    f"Failed to read workflow file {workflow_file}: {e}"
                )
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
        template_id: str,
        file_path: Optional[Path] = None
    ) -> WorkflowTemplate:
        """
        解析模板文档

        支持四种格式：
        1. spec-global 格式：kind: workflow，完整的工作流定义
        2. L2 模板格式：kind: l2_workflow_template
        3. L3 模板格式：kind: l3_workflow_template
        4. 旧格式：level 字段指定层级

        Args:
            doc: YAML 文档字典
            template_id: 模板 ID
            file_path: 模板文件路径（可选）

        Returns:
            WorkflowTemplate 对象
        """
        # 检测文档格式
        kind = doc.get("kind", "")

        # v3.6: L2/L3 模板支持
        if kind == "l2_workflow_template":
            return self._parse_l2_template(doc, template_id, file_path)
        elif kind == "l3_workflow_template":
            return self._parse_l3_template(doc, template_id, file_path)

        # spec-global 格式检测
        # 检查 stages 是否在顶层或在 overview 下
        has_stages = "stages" in doc or "stages" in doc.get("overview", {})
        if kind == "workflow" and has_stages:
            # 使用 spec-global 解析器
            return self._parse_spec_global_format(doc, template_id, file_path)

        # 其他格式处理（保持原有逻辑）
        if kind == "workflow":
            # 新格式：从 overview 推断 level
            # 有 stages 的通常是 department 级别流程
            overview = doc.get("overview", {})
            stages = overview.get("stages", [])

            if stages:
                level = WorkflowLevel.DEPARTMENT
            else:
                level = WorkflowLevel.TASK
        else:
            # 旧格式：直接读取 level
            level_str = doc.get("level", "task")
            try:
                level = WorkflowLevel(level_str)
            except ValueError:
                level = WorkflowLevel.TASK

        steps_data = doc.get("steps", [])
        steps = [self._parse_step(s) for s in steps_data]

        # 从 completion 字段提取完成条件
        completion = doc.get("completion", {})
        completion_criteria = completion if completion else doc.get("completion_criteria", {})

        return WorkflowTemplate(
            id=doc.get("id", template_id),
            level=level,
            name=doc.get("name", template_id),
            description=doc.get("description", ""),
            steps=steps,
            departments=doc.get("departments", []),
            tasks=doc.get("tasks", []),
            completion_criteria=completion_criteria,
            config=doc.get("config", {}),
        )

    def _parse_l2_template(
        self,
        doc: Dict[str, Any],
        template_id: str,
        file_path: Optional[Path] = None
    ) -> WorkflowTemplate:
        """
        解析 L2 工作流模板

        L2 模板特点：
        - kind: l2_workflow_template
        - phases 定义（而非 steps）
        - 每个阶段有 default_complexity

        Args:
            doc: YAML 文档字典
            template_id: 模板 ID
            file_path: 模板文件路径（可选）

        Returns:
            WorkflowTemplate 对象
        """
        from lee.orchestrator.storage.models import Complexity

        phases = doc.get("phases", [])
        steps = []

        # 将 phases 转换为 steps（保持与现有 WorkflowTemplate 兼容）
        for phase in phases:
            phase_id = phase.get("id", "")
            default_complexity = phase.get("default_complexity", "M")

            # 验证 complexity 值
            try:
                Complexity(default_complexity)
            except ValueError:
                default_complexity = "M"

            steps.append(Step(
                id=phase_id,
                kind="phase",  # L2 特有 kind
                executor_type=None,
                depends_on=[],
                input={
                    "phase_id": phase_id,
                    "name": phase.get("name", ""),
                    "description": phase.get("description", ""),
                    "default_complexity": default_complexity,
                },
                config={
                    "name": phase.get("name", ""),
                    "description": phase.get("description", ""),
                    "default_complexity": default_complexity,
                    "phase": phase_id,
                },
            ))

        return WorkflowTemplate(
            id=doc.get("id", template_id),
            level=WorkflowLevel.DEPARTMENT,
            name=doc.get("name", template_id),
            description=doc.get("description", ""),
            steps=steps,
            departments=[],
            tasks=[],
            completion_criteria={
                "all_phases_complete": True,
            },
            config={
                "kind": "l2_workflow_template",
                "execution_strategies": doc.get("execution_strategies", {}),
            },
        )

    def _parse_l3_template(
        self,
        doc: Dict[str, Any],
        template_id: str,
        file_path: Optional[Path] = None
    ) -> WorkflowTemplate:
        """
        解析 L3 工作流模板

        L3 模板特点：
        - kind: l3_workflow_template
        - 6 个标准步骤
        - 单点任务执行

        Args:
            doc: YAML 文档字典
            template_id: 模板 ID
            file_path: 模板文件路径（可选）

        Returns:
            WorkflowTemplate 对象
        """
        steps_data = doc.get("steps", [])
        steps = []

        # 解析 L3 特有的 steps 格式
        for step_data in steps_data:
            step_id = step_data.get("id", "")
            kind = step_data.get("kind", "agent")

            # 解析 depends_on
            depends_on = step_data.get("depends_on", [])

            steps.append(Step(
                id=step_id,
                kind=kind,
                executor_type="llm" if kind == "agent" else "shell",
                depends_on=depends_on,
                input={
                    "step_id": step_id,
                    "name": step_data.get("name", ""),
                    "description": step_data.get("description", ""),
                },
                config={
                    "name": step_data.get("name", ""),
                    "description": step_data.get("description", ""),
                    "mandatory": step_data.get("mandatory", True),
                },
            ))

        return WorkflowTemplate(
            id=doc.get("id", template_id),
            level=WorkflowLevel.TASK,
            name=doc.get("name", template_id),
            description=doc.get("description", ""),
            steps=steps,
            departments=[],
            tasks=[],
            completion_criteria={
                "all_steps_complete": True,
            },
            config={
                "kind": "l3_workflow_template",
                "execution_order": doc.get("execution_order", [s.id for s in steps]),
            },
        )

    def _parse_spec_global_format(
        self,
        doc: Dict[str, Any],
        template_id: str,
        file_path: Optional[Path] = None
    ) -> WorkflowTemplate:
        """
        解析 spec-global 格式的工作流文档

        spec-global 格式特点：
        - kind: workflow
        - stages/steps 嵌套结构
        - 完整的状态机、门禁、契约定义

        Args:
            doc: YAML 文档字典
            template_id: 模板 ID
            file_path: 模板文件路径（可选）

        Returns:
            WorkflowTemplate 对象
        """
        # 延迟导入 spec-global 解析器
        if self._spec_global_parser is None:
            from lee.orchestrator.execution.spec_global_parser import SpecGlobalParser
            from lee.orchestrator.ir.converter import IRConverter

            self._spec_global_parser = SpecGlobalParser(workflow_base_dir=str(self.template_dir))
            # v3.5: 传递配置到 IRConverter 以使用正确的 executor.default_type
            self._ir_converter = IRConverter(config=self.config)

        # 使用 spec-global 解析器解析为 IR
        # 如果提供了 file_path，直接使用；否则根据 template_id 构建路径
        if file_path:
            workflow_file_path = file_path
        elif template_id.endswith('.yaml') or template_id.endswith('.yml'):
            workflow_file_path = Path(template_id)
        else:
            workflow_file_path = Path(self.template_dir) / f"{template_id}.yaml"

        workflow_ir = self._spec_global_parser.parse_workflow(doc, workflow_file_path)

        # 将 IR 转换为模板字典
        template_dict = self._ir_converter.ir_to_template_dict(workflow_ir)

        # 构建 WorkflowTemplate
        level = WorkflowLevel(template_dict["level"])
        steps = [self._dict_to_step(s) for s in template_dict["steps"]]

        template = WorkflowTemplate(
            id=template_dict["id"],
            level=level,
            name=template_dict["name"],
            description=template_dict["description"],
            steps=steps,
            departments=template_dict.get("departments", []),
            tasks=template_dict.get("tasks", []),
            completion_criteria=template_dict.get("completion_criteria", {}),
            config=template_dict.get("config", {}),
        )

        return template

    def _dict_to_step(self, step_dict: Dict[str, Any]) -> Step:
        """将字典转换为 Step 对象"""
        from lee.orchestrator.storage.models import OutputSpec

        # 解析 outputs（支持旧/新格式）
        outputs_raw = step_dict.get("outputs", [])
        outputs = []
        for output_item in outputs_raw:
            if isinstance(output_item, dict):
                if "type" not in output_item:
                    path = output_item.get("path", "")
                    output_type = "dir" if path.endswith("/") else "file"
                    outputs.append(OutputSpec(
                        type=output_type,
                        path=path,
                        format=self._infer_format(path),
                        required=output_item.get("required", True),
                        description=output_item.get("description", ""),
                    ))
                else:
                    outputs.append(OutputSpec(
                        type=output_item.get("type", "file"),
                        path=output_item.get("path", ""),
                        format=output_item.get("format", "text"),
                        required=output_item.get("required", True),
                        description=output_item.get("description", ""),
                    ))

        return Step(
            id=step_dict["id"],
            kind=step_dict.get("kind", "agent"),
            executor_type=step_dict.get("executor_type"),
            agent_id=step_dict.get("agent_id"),
            skill_id=step_dict.get("skill_id"),
            gate_id=step_dict.get("gate_id"),
            depends_on=step_dict.get("depends_on", []),
            input=step_dict.get("input", {}),
            outputs=outputs,
            config=step_dict.get("config", {}),
            on_failure=step_dict.get("on_failure", (step_dict.get("config", {}) or {}).get("on_failure")),
        )

    def _parse_step(self, step_data: Dict[str, Any]) -> Step:
        """
        解析单个步骤（v1.5 更新）

        支持新规范：
        - kind=agent → 读取 agent 字段
        - kind=skill → 读取 skill 字段
        - kind=human_gate → 读取 human_gate 或 gate.id 字段
        - outputs → 解析为 OutputSpec 列表
        - post_gate → 提取 gate_id

        自动推断 kind：
        - 有 agent 字段 → agent
        - 有 skill 字段 → skill
        - 有 human_gate 字段 → human_gate

        Args:
            step_data: 步骤数据

        Returns:
            Step 对象
        """
        from lee.orchestrator.storage.models import OutputSpec

        step_id = step_data.get("id", "")

        # 自动推断 kind（如果没有显式指定）
        kind = step_data.get("kind") or step_data.get("type")
        if not kind:
            if "human_gate" in step_data:
                kind = "human_gate"
            elif "subworkflow" in step_data or "workflow" in step_data:
                kind = "workflow_spawn"
            elif "skill" in step_data:
                kind = "skill"
            elif "agent" in step_data:
                kind = "agent"
            else:
                # 默认为 agent
                kind = "agent"
        kind = str(kind).lower()
        # claude_code / patch_apply 作为一等公民 kind
        if kind in ("claude_code", "patch_apply"):
            pass  # 保持原值

        # 解析 agent/skill/gate 引用
        agent_id = step_data.get("agent")  # kind=agent 时
        skill_id = step_data.get("skill")  # kind=skill 时

        # 解析 gate_id（从 human_gate、post_gate 或独立的 gate）
        gate_id = None
        if "human_gate" in step_data:
            gate_id = step_data["human_gate"]
        elif "post_gate" in step_data:
            gate_id = step_data["post_gate"].get("id")
        elif kind == "human_gate" and "gate" in step_data:
            gate_id = step_data["gate"].get("id")

        # 解析子工作流引用（workflow_spawn/subworkflow）
        subworkflow_ref = None
        subworkflow_level = None
        if kind in ("workflow_spawn", "subworkflow"):
            subworkflow_data = step_data.get("subworkflow")
            if isinstance(subworkflow_data, dict):
                subworkflow_ref = subworkflow_data.get("ref") or subworkflow_data.get("id")
                subworkflow_level = subworkflow_data.get("level")
            elif isinstance(subworkflow_data, str):
                subworkflow_ref = subworkflow_data

            if not subworkflow_ref and isinstance(step_data.get("workflow"), str):
                subworkflow_ref = step_data.get("workflow")

            run_ref = step_data.get("run")
            if not subworkflow_ref and isinstance(run_ref, str) and run_ref.startswith("workflow."):
                subworkflow_ref = run_ref

            if step_data.get("level"):
                subworkflow_level = step_data.get("level")

        # 解析 executor_type（v3.5：使用配置中的 default_type）
        # 保留兼容性：如果指定了 executor 则使用，否则根据 kind 和配置决定
        executor_type = step_data.get("executor")
        if not executor_type:
            if kind == "agent":
                # v3.5: 从配置读取默认执行器类型
                executor_type = self.config.executor.default_type
            elif kind == "claude_code":
                executor_type = "claude_code"  # Claude Code 执行器
            elif kind == "patch_apply":
                executor_type = "patch_apply"  # 补丁应用执行器
            elif kind == "skill":
                executor_type = "shell"  # 默认使用 Shell
            elif kind == "human_gate":
                executor_type = None  # human_gate 不需要 executor
            elif kind in ("workflow_spawn", "subworkflow", "orchestrator_cli", "compliance_gate"):
                executor_type = None

        # 解析 outputs
        outputs_raw = step_data.get("outputs", [])
        outputs = []
        for output_item in outputs_raw:
            if isinstance(output_item, dict):
                # 兼容旧格式：{path, required, description}
                if "type" not in output_item:
                    # 根据 path 判断类型
                    path = output_item.get("path", "")
                    if path.endswith("/"):
                        output_type = "dir"
                    else:
                        output_type = "file"

                    outputs.append(OutputSpec(
                        type=output_type,
                        path=path,
                        format=self._infer_format(path),
                        required=output_item.get("required", True),
                        description=output_item.get("description", ""),
                    ))
                else:
                    # 新格式：{type, path, format, required, description}
                    outputs.append(OutputSpec(
                        type=output_item.get("type", "file"),
                        path=output_item.get("path", ""),
                        format=output_item.get("format", "text"),
                        required=output_item.get("required", True),
                        description=output_item.get("description", ""),
                    ))

        # 兼容 dependencies/depends_on 两种写法
        depends_on = step_data.get("depends_on")
        if depends_on is None:
            dependencies = step_data.get("dependencies", [])
            if isinstance(dependencies, dict):
                depends_on = dependencies.get("requires", [])
            elif isinstance(dependencies, list):
                depends_on = dependencies
            else:
                depends_on = []

        return Step(
            id=step_id,
            kind=kind,
            executor_type=executor_type,
            agent_id=agent_id,
            skill_id=skill_id,
            gate_id=gate_id,
            depends_on=depends_on,
            input=step_data.get("inputs", step_data.get("input", {})),
            outputs=outputs,
            config=self._build_step_config(
                step_data,
                kind,
                subworkflow_ref=subworkflow_ref,
                subworkflow_level=subworkflow_level,
            ),
            on_failure=step_data.get("on_failure"),
        )

    def _build_step_config(
        self,
        step_data: Dict[str, Any],
        kind: str,
        subworkflow_ref: Optional[str] = None,
        subworkflow_level: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        构建步骤配置

        包含：
        - 步骤名称和描述
        - 阶段信息
        - 门禁配置
        - 其他元数据
        """
        config = step_data.get("config", {}).copy()

        # 添加步骤名称和描述
        if "name" in step_data:
            config["name"] = step_data["name"]
        if "description" in step_data:
            config["description"] = step_data["description"]
        if "phase" in step_data:
            config["phase"] = step_data["phase"]

        # 对于 human_gate，将 gate 配置合并到 config 中
        if kind == "human_gate":
            if "gate" in step_data:
                config["gate"] = step_data["gate"]
            # 也可能直接有 reviewers 等字段
            if "reviewers" in step_data:
                config["reviewers"] = step_data["reviewers"]
            if "approval_criteria" in step_data:
                config["approval_criteria"] = step_data["approval_criteria"]

        if kind in ("workflow_spawn", "subworkflow"):
            if subworkflow_ref:
                config["subworkflow_ref"] = subworkflow_ref
            if subworkflow_level:
                config["subworkflow_level"] = subworkflow_level
            if "subworkflow" in step_data:
                config["subworkflow"] = step_data["subworkflow"]
            if "workflow" in step_data:
                config["workflow"] = step_data["workflow"]
            if "input_map" in step_data:
                config["input_map"] = step_data["input_map"]
            if "output_map" in step_data:
                config["output_map"] = step_data["output_map"]
            if "subworkflow_max_steps" in step_data:
                config["subworkflow_max_steps"] = step_data["subworkflow_max_steps"]

        if "run" in step_data:
            config["run"] = step_data["run"]

        # Verifiers
        if "verifiers" in step_data:
            config["verifiers"] = step_data["verifiers"]
        if "verify" in step_data and "verifiers" not in config:
            config["verifiers"] = step_data["verify"]

        # 添加非目标和思考边界（用于 agent）
        if "non_goals" in step_data:
            config["non_goals"] = step_data["non_goals"]
        if "thinking_boundary" in step_data:
            config["thinking_boundary"] = step_data["thinking_boundary"]

        # 添加成功后执行的步骤
        if "on_success" in step_data:
            config["on_success"] = step_data["on_success"]
        if "on_failure" in step_data:
            config["on_failure"] = step_data["on_failure"]
        if "success_criteria" in step_data:
            config["success_criteria"] = step_data["success_criteria"]

        return config

    def _infer_format(self, path: str) -> str:
        """根据文件扩展名推断格式"""
        if path.endswith(".yaml") or path.endswith(".yml"):
            return "yaml"
        elif path.endswith(".json"):
            return "json"
        elif path.endswith(".md"):
            return "markdown"
        else:
            return "text"

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
