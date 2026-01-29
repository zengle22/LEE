"""
Template Resolver - 模板变量解析器
支持 {bug_id}, {round_num} 等动态变量
"""

import re
from typing import Dict, Any, List, Union
from pathlib import Path


class TemplateResolver:
    """模板变量解析器"""

    def __init__(self, context: Dict[str, Any]):
        """初始化

        Args:
            context: 变量上下文，如 {"bug_id": "BUG-2026-0001", "round_num": 3}
        """
        self.context = context

    def resolve(self, template: str) -> str:
        """解析模板字符串

        Examples:
            resolve("bugs/{bug_id}.yaml") -> "bugs/BUG-2026-0001.yaml"
            resolve("round-{round_num}/report.md") -> "round-003/report.md"
            resolve("output/{bug_id}/debug.json") -> "output/BUG-2026-0001/debug.json"

        Args:
            template: 模板字符串

        Returns:
            解析后的字符串

        Raises:
            ValueError: 如果模板变量未在context中找到
        """
        pattern = r'\{(\w+)\}'

        def replacer(match):
            var_name = match.group(1)
            value = self.context.get(var_name)

            if value is None:
                raise ValueError(
                    f"Template variable '{var_name}' not found in context. "
                    f"Available variables: {list(self.context.keys())}"
                )

            # 数字格式化 (如 round_num -> 003)
            if isinstance(value, int) and var_name.endswith("_num"):
                return f"{value:03d}"

            return str(value)

        return re.sub(pattern, replacer, template)

    def resolve_dict(self, template_dict: Dict) -> Dict:
        """递归解析字典中的所有模板字符串

        Args:
            template_dict: 包含模板字符串的字典

        Returns:
            解析后的字典
        """
        result = {}
        for key, value in template_dict.items():
            if isinstance(value, str):
                result[key] = self.resolve(value)
            elif isinstance(value, dict):
                result[key] = self.resolve_dict(value)
            elif isinstance(value, list):
                result[key] = self._resolve_list(value)
            else:
                result[key] = value
        return result

    def _resolve_list(self, template_list: List) -> List:
        """解析列表中的模板字符串"""
        result = []
        for item in template_list:
            if isinstance(item, str):
                result.append(self.resolve(item))
            elif isinstance(item, dict):
                result.append(self.resolve_dict(item))
            elif isinstance(item, list):
                result.append(self._resolve_list(item))
            else:
                result.append(item)
        return result

    def resolve_path(self, template: Union[str, Path]) -> Path:
        """解析路径模板

        Args:
            template: 路径模板字符串或Path对象

        Returns:
            解析后的Path对象
        """
        template_str = str(template)
        resolved_str = self.resolve(template_str)
        return Path(resolved_str)

    def add_context(self, **kwargs):
        """添加上下文变量

        Example:
            resolver.add_context(bug_id="BUG-001", round_num=2)
        """
        self.context.update(kwargs)

    def remove_context(self, *keys):
        """移除上下文变量

        Example:
            resolver.remove_context("bug_id", "round_num")
        """
        for key in keys:
            self.context.pop(key, None)


def create_resolver_from_workflow_state(workflow_state: Dict) -> TemplateResolver:
    """从工作流状态创建模板解析器

    Args:
        workflow_state: 工作流状态字典

    Returns:
        TemplateResolver实例
    """
    context = {
        "run_id": workflow_state.get("run_id", ""),
        "workflow_id": workflow_state.get("workflow_id", ""),
        "current_step": workflow_state.get("current_step", ""),
    }

    # 添加循环上下文
    if "loop_context" in workflow_state:
        loop_ctx = workflow_state["loop_context"]
        context["round_num"] = loop_ctx.get("current_iteration", 1)
        context["loop_iteration"] = loop_ctx.get("current_iteration", 1)

    return TemplateResolver(context)
