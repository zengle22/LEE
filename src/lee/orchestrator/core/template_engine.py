"""
模板引擎 - 基于 Jinja2

用于渲染工作流模板，支持变量替换和简单逻辑
"""

import yaml
from jinja2 import Environment, BaseLoader
from typing import Dict, Any, List


class TemplateEngine:
    """模板引擎"""

    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader())

    def render_string(
        self,
        template_string: str,
        context: Dict[str, Any]
    ) -> str:
        """渲染字符串模板"""
        template = self.jinja_env.from_string(template_string)
        return template.render(**context)

    def render_yaml(
        self,
        yaml_string: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """渲染 YAML 模板"""
        rendered = self.render_string(yaml_string, context)
        return yaml.safe_load(rendered)

    def validate_workflow_template(
        self,
        template_dict: Dict[str, Any]
    ) -> List[str]:
        """验证工作流模板格式"""
        errors = []

        if "name" not in template_dict:
            errors.append("Missing required field: 'name'")

        if "steps" not in template_dict:
            errors.append("Missing required field: 'steps'")
        elif not isinstance(template_dict["steps"], list):
            errors.append("Field 'steps' must be a list")

        return errors

    def get_ready_steps(
        self,
        template_dict: Dict[str, Any],
        completed_steps: set
    ) -> List[str]:
        """获取当前可执行的步骤列表"""
        steps = template_dict.get("steps", [])
        ready_steps = []

        for step in steps:
            step_name = step.get("name")
            if step_name in completed_steps:
                continue

            dependencies = step.get("depends_on", [])
            if all(dep in completed_steps for dep in dependencies):
                ready_steps.append(step_name)

        return ready_steps
