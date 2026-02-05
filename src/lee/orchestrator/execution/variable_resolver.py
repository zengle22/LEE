"""
LEE Orchestrator - Variable Resolver

解析 spec-global 工作流中的变量引用。

支持的引用格式：
- $inputs.xxx: 工作流输入引用
- $sX_yyy: 步骤输出引用（如 $s2_1.output）
- 嵌套路径访问: $s2_1.consistency_matrix.conflicts
"""

import re
from typing import Dict, Any, Optional, List, Union

from lee.orchestrator.ir.models import VariableIR


class VariableResolver:
    """
    变量引用解析器

    职责：
    1. 解析变量引用字符串为 VariableIR
    2. 根据上下文解析变量值
    3. 递归解析字典中的所有变量引用
    4. 提供清晰的错误信息
    """

    # 正则表达式
    STEP_OUTPUT_PATTERN = re.compile(r'\$s(\d+)_(\d+)(?:_(.+))?')
    INPUTS_PATTERN = re.compile(r'\$inputs\.([a-zA-Z_][a-zA-Z0-9_.]*)')

    def __init__(self):
        self.variables: Dict[str, Any] = {}

    # ========================================================================
    # 引用解析
    # ========================================================================

    def parse_reference(self, reference: str) -> VariableIR:
        """
        解析变量引用字符串为 VariableIR

        Args:
            reference: 变量引用字符串，如 "$inputs.prd" 或 "$s2_1.output"

        Returns:
            VariableIR 对象

        Raises:
            ValueError: 如果引用格式无效
        """
        if not reference or not isinstance(reference, str):
            raise ValueError(f"Invalid variable reference: {reference}")

        if not reference.startswith("$"):
            raise ValueError(f"Variable reference must start with $: {reference}")

        # 尝试匹配步骤输出引用：$sX_yyy 或 $sX_yyy_zzz
        step_match = self.STEP_OUTPUT_PATTERN.match(reference)
        if step_match:
            stage_num = step_match.group(1)
            step_num = step_match.group(2)
            output_name = step_match.group(3)
            step_id = f"s{stage_num}_{step_num}"

            # 构建路径
            path = [output_name] if output_name else []

            return VariableIR(
                reference=reference,
                source_type="step",
                path=path,
                step_id=step_id,
            )

        # 尝试匹配输入引用：$inputs.xxx
        inputs_match = self.INPUTS_PATTERN.match(reference)
        if inputs_match:
            path = inputs_match.group(1).split(".")
            return VariableIR(
                reference=reference,
                source_type="inputs",
                path=path,
            )

        # 默认为上下文引用（去掉 $ 前缀）
        ref_without_dollar = reference[1:]
        path = ref_without_dollar.split(".")
        return VariableIR(
            reference=reference,
            source_type="context",
            path=path,
        )

    # ========================================================================
    # 值解析
    # ========================================================================

    def resolve_reference(self, reference: Union[str, VariableIR], context: Dict[str, Any]) -> Any:
        """
        解析变量引用的值

        Args:
            reference: 变量引用字符串或 VariableIR
            context: 上下文数据，包含 inputs, step_outputs 等

        Returns:
            解析后的值

        Raises:
            ValueError: 如果变量未定义
        """
        # 如果是字符串，先解析为 VariableIR
        if isinstance(reference, str):
            var_ir = self.parse_reference(reference)
        else:
            var_ir = reference

        # 根据类型获取值
        if var_ir.source_type == "inputs":
            return self._get_from_inputs(var_ir.path, context.get("inputs", {}))
        elif var_ir.source_type == "step":
            return self._get_from_step(var_ir, context)
        elif var_ir.source_type == "context":
            return self._get_from_context(var_ir.path, context)

        raise ValueError(f"Unknown variable source type: {var_ir.source_type}")

    def _get_from_inputs(self, path: List[str], inputs: Dict[str, Any]) -> Any:
        """
        从 inputs 获取值

        Args:
            path: 变量路径
            inputs: 输入数据字典

        Returns:
            变量值

        Raises:
            ValueError: 如果变量未定义
        """
        value = inputs
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ValueError(f"Cannot access key '{key}' on inputs (path: {'.'.join(path)})")

        return value

    def _get_from_step(self, var_ir: VariableIR, context: Dict[str, Any]) -> Any:
        """
        从步骤输出获取值

        Args:
            var_ir: VariableIR 对象
            context: 上下文数据

        Returns:
            变量值

        Raises:
            ValueError: 如果变量未定义
        """
        step_outputs = context.get("step_outputs", {})
        step_output = step_outputs.get(var_ir.step_id)

        if step_output is None:
            raise ValueError(f"Step output not found: {var_ir.step_id} (reference: {var_ir.reference})")

        value = step_output
        for key in var_ir.path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            elif isinstance(value, dict):
                # 键不存在，返回 None
                return None
            else:
                raise ValueError(f"Cannot access key '{key}' on non-dict value (path: {'.'.join(var_ir.path)})")

        return value

    def _get_from_context(self, path: List[str], context: Dict[str, Any]) -> Any:
        """
        从上下文获取值

        Args:
            path: 变量路径
            context: 上下文数据

        Returns:
            变量值

        Raises:
            ValueError: 如果变量未定义
        """
        value = context
        for key in path:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise ValueError(f"Cannot access key '{key}' in context (path: {'.'.join(path)})")

        return value

    # ========================================================================
    # 批量解析
    # ========================================================================

    def resolve_all_in_dict(self, data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        递归解析字典中的所有变量引用

        Args:
            data: 输入数据
            context: 解析上下文

        Returns:
            解析后的数据
        """
        result = {}
        for key, value in data.items():
            if isinstance(value, str):
                if value.startswith("$"):
                    try:
                        result[key] = self.resolve_reference(value, context)
                    except ValueError as e:
                        # 保留原始引用，让调用者决定如何处理
                        result[key] = value
                else:
                    result[key] = value
            elif isinstance(value, dict):
                result[key] = self.resolve_all_in_dict(value, context)
            elif isinstance(value, list):
                result[key] = [
                    self.resolve_all_in_dict(item, context) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                result[key] = value

        return result

    def resolve_all_in_list(self, data: List[Any], context: Dict[str, Any]) -> List[Any]:
        """
        递归解析列表中的所有变量引用

        Args:
            data: 输入列表
            context: 解析上下文

        Returns:
            解析后的列表
        """
        result = []
        for item in data:
            if isinstance(item, dict):
                result.append(self.resolve_all_in_dict(item, context))
            elif isinstance(item, list):
                result.append(self.resolve_all_in_list(item, context))
            elif isinstance(item, str) and item.startswith("$"):
                try:
                    result.append(self.resolve_reference(item, context))
                except ValueError:
                    result.append(item)
            else:
                result.append(item)

        return result

    # ========================================================================
    # 依赖关系推断
    # ========================================================================

    def extract_step_dependencies(self, step_inputs: List[Dict[str, Any]]) -> List[str]:
        """
        从步骤输入中提取依赖的步骤 ID

        Args:
            step_inputs: 步骤输入列表

        Returns:
            依赖的步骤 ID 列表
        """
        dependencies = set()

        for input_item in step_inputs:
            for value in input_item.values():
                deps = self._extract_dependencies_from_value(value)
                dependencies.update(deps)

        return list(dependencies)

    def _extract_dependencies_from_value(self, value: Any) -> List[str]:
        """从值中提取依赖的步骤 ID"""
        if isinstance(value, str) and value.startswith("$s"):
            try:
                var_ir = self.parse_reference(value)
                if var_ir.source_type == "step" and var_ir.step_id:
                    return [var_ir.step_id]
            except ValueError:
                pass

        elif isinstance(value, dict):
            deps = []
            for v in value.values():
                deps.extend(self._extract_dependencies_from_value(v))
            return deps

        elif isinstance(value, list):
            deps = []
            for item in value:
                deps.extend(self._extract_dependencies_from_value(item))
            return deps

        return []

    # ========================================================================
    # 验证和错误报告
    # ========================================================================

    def validate_context(self, required_vars: List[VariableIR], context: Dict[str, Any]) -> List[str]:
        """
        验证上下文是否包含所有必需的变量

        Args:
            required_vars: 必需的变量列表
            context: 上下文数据

        Returns:
            错误信息列表（空列表表示全部通过）
        """
        errors = []

        for var in required_vars:
            try:
                self.resolve_reference(var, context)
            except ValueError as e:
                errors.append(f"Variable '{var.reference}' not found: {e}")

        return errors

    def get_missing_variables(self, data: Dict[str, Any], context: Dict[str, Any]) -> List[str]:
        """
        获取数据中所有缺失的变量引用

        Args:
            data: 输入数据
            context: 上下文数据

        Returns:
            缺失的变量引用列表
        """
        missing = []

        # 收集所有变量引用
        refs = self._extract_all_references(data)

        # 验证每个引用
        for ref in refs:
            try:
                self.resolve_reference(ref, context)
            except ValueError:
                missing.append(ref.reference)

        return missing

    def _extract_all_references(self, data: Any) -> List[VariableIR]:
        """从数据中提取所有变量引用"""
        refs = []

        if isinstance(data, str):
            if data.startswith("$"):
                try:
                    refs.append(self.parse_reference(data))
                except ValueError:
                    pass
        elif isinstance(data, dict):
            for value in data.values():
                refs.extend(self._extract_all_references(value))
        elif isinstance(data, list):
            for item in data:
                refs.extend(self._extract_all_references(item))

        return refs


class ExpressionEvaluator:
    """
    表达式求值器

    支持 spec-global 工作流中的条件表达式求值。
    P0 阶段实现基础版本，P1 阶段扩展。

    支持的操作符：
    - 比较: >, <, >=, <=, ==, !=
    - 逻辑: AND, OR
    - 存在性检查: EXISTS, COUNT
    """

    def __init__(self, variable_resolver: VariableResolver):
        self.variable_resolver = variable_resolver

    def evaluate(self, expression: str, context: Dict[str, Any]) -> bool:
        """
        评估条件表达式

        Args:
            expression: 条件表达式，如 "consistency_matrix.conflicts > 0"
            context: 上下文数据

        Returns:
            条件是否为真

        Note:
            P0 阶段实现简化版本，支持基本的比较表达式
        """
        # 简化版本：检查是否包含特定模式
        # TODO: P1 阶段实现完整的表达式解析

        # 处理 "xxx > 0" 形式的表达式
        if " > " in expression:
            parts = expression.split(" > ")
            if len(parts) == 2:
                path = parts[0].strip()
                threshold = int(parts[1].strip())

                try:
                    value = self._get_value_by_path(path, context)
                    return self._compare_values(value, ">", threshold)
                except (ValueError, KeyError):
                    # 无法求值，返回 True（允许执行）
                    return True

        # 处理 "xxx == 'rejected'" 形式的表达式
        if " == " in expression:
            parts = expression.split(" == ")
            if len(parts) == 2:
                path = parts[0].strip()
                expected = parts[1].strip().strip("'\"")

                try:
                    value = self._get_value_by_path(path, context)
                    return str(value) == expected
                except (ValueError, KeyError):
                    return True

        # 默认返回 True（允许执行）
        return True

    def _get_value_by_path(self, path: str, context: Dict[str, Any]) -> Any:
        """
        根据路径获取值

        支持：
        - context.var
        - step_output.var
        """
        parts = path.split(".")

        # 尝试从 step_outputs 获取
        if len(parts) >= 2:
            # 可能是 s2_1.consistency_matrix.conflicts
            step_id = f"{parts[0]}_{parts[1]}"
            value_path = parts[2:]

            step_outputs = context.get("step_outputs", {})
            if step_id in step_outputs:
                value = step_outputs[step_id]
                for key in value_path:
                    if isinstance(value, dict) and key in value:
                        value = value[key]
                    else:
                        raise KeyError(f"Key not found: {key}")
                return value

        # 从 context 直接获取
        value = context
        for key in parts:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                raise KeyError(f"Key not found: {key}")

        return value

    def _compare_values(self, value: Any, operator: str, threshold: Any) -> bool:
        """比较值"""
        if operator == ">":
            return value is not None and value > threshold
        elif operator == "<":
            return value is not None and value < threshold
        elif operator == ">=":
            return value is not None and value >= threshold
        elif operator == "<=":
            return value is not None and value <= threshold
        elif operator == "==":
            return value == threshold
        elif operator == "!=":
            return value != threshold
        else:
            raise ValueError(f"Unknown operator: {operator}")
