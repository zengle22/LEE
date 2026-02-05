"""
模板管理器 - 加载和解析工作流模板

支持 YAML 格式的模板定义，支持多文档文件
"""

import yaml
import os
from typing import Dict, Any, List, Optional
from pathlib import Path
from types import SimpleNamespace

from lee.orchestrator.storage.models import Template, WorkflowLevel


class TemplateManager:
    """模板管理器"""

    def __init__(self, template_dir: str = "examples"):
        self.template_dir = Path(template_dir)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def load_yaml_template(self, file_path: str) -> List[Dict[str, Any]]:
        """
        加载 YAML 模板文件（支持多文档）

        Args:
            file_path: 模板文件路径

        Returns:
            模板字典列表
        """
        if not os.path.isabs(file_path):
            file_path = os.path.join(self.template_dir, file_path)

        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # YAML 文件可能包含多个文档（用 --- 分隔）
        templates = []
        for doc in yaml.safe_load_all(content):
            if doc:
                templates.append(doc)

        return templates

    def get_template_content(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        获取模板内容

        Args:
            template_id: 模板 ID 或名称

        Returns:
            模板内容字典
        """
        if template_id in self._cache:
            return self._cache[template_id]

        # 尝试加载 templates.yaml 文件
        template_file = self.template_dir / "templates.yaml"
        if template_file.exists():
            templates = self.load_yaml_template(template_file)
            for template in templates:
                if template.get("name") == template_id or template.get("id") == template_id:
                    self._cache[template_id] = template
                    return template

        return None

    def get_template(self, template_id: str) -> Optional[Any]:
        """
        获取模板（返回兼容 Orchestrator 的对象）

        Args:
            template_id: 模板 ID 或名称

        Returns:
            模板对象（带有 departments, tasks 等属性），不存在返回 None
        """
        content = self.get_template_content(template_id)
        if not content:
            return None

        # 转换为具有属性的对象（兼容 Orchestrator）
        return SimpleNamespace(
            id=content.get("id") or content.get("name", ""),
            name=content.get("name", ""),
            description=content.get("description", ""),
            steps=content.get("steps", []),
            departments=content.get("departments", []),
            tasks=content.get("tasks", []),
            completion_criteria=content.get("completion_criteria", {}),
        )

    def get_steps(self, template_id: str) -> List[Dict[str, Any]]:
        """获取模板的步骤列表"""
        template = self.get_template_content(template_id)
        if not template:
            return []
        return template.get("steps", [])

    def get_departments(self, template_id: str) -> List[Dict[str, Any]]:
        """获取 L2 部门列表"""
        template = self.get_template_content(template_id)
        if not template:
            return []
        return template.get("departments", [])

    def get_completion_criteria(self, template_id: str) -> Dict[str, Any]:
        """获取完成条件"""
        template = self.get_template_content(template_id)
        if not template:
            return {}
        return template.get("completion_criteria", {})
