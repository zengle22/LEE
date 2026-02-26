"""
模板引擎 - 基于 Jinja2

用于渲染工作流模板，支持变量替换和简单逻辑
"""

import yaml
from datetime import datetime
import random
import string
from jinja2 import Environment, BaseLoader, Undefined
from typing import Dict, Any, List


class SilentUndefined(Undefined):
    """静默未定义变量 - 访问未定义变量时返回空字符串而不是报错"""
    def __getitem__(self, item):
        return ""
    def __getattr__(self, item):
        return ""


def _date_filter(value, format_string):
    """日期格式化过滤器"""
    if isinstance(value, str):
        # 尝试解析字符串
        try:
            value = datetime.fromisoformat(value)
        except ValueError:
            return value
    if isinstance(value, datetime):
        return value.strftime(format_string)
    return value


def _now():
    """获取当前时间"""
    return datetime.now()


def _random_suffix(length=4):
    """生成随机后缀"""
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))


def _slugify(value):
    """将字符串转换为 slug 格式（用于文件名）"""
    if not isinstance(value, str):
        value = str(value)
    # 替换空格和特殊字符为下划线
    import re
    # 替换非字母数字为下划线
    slug = re.sub(r'[^a-zA-Z0-9\-_\.]', '_', value)
    # 多个连续下划线合并为一个
    slug = re.sub(r'_+', '_', slug)
    # 移除首尾下划线
    slug = slug.strip('_')
    return slug


class TemplateEngine:
    """模板引擎"""

    def __init__(self):
        self.jinja_env = Environment(loader=BaseLoader(), undefined=SilentUndefined)
        # 添加自定义过滤器
        self.jinja_env.filters['date'] = _date_filter
        self.jinja_env.filters['slugify'] = _slugify
        # 添加自定义全局函数
        self.jinja_env.globals['now'] = _now
        self.jinja_env.globals['random_suffix'] = _random_suffix

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
