"""
LEE Orchestrator - Condition Engine

条件执行引擎，支持步骤的条件执行逻辑。

核心功能：
1. 条件表达式解析：解析条件表达式语法
2. 变量绑定：从上下文绑定变量值
3. 逻辑运算：AND, OR, NOT 支持
4. 比较运算：==, !=, <, >, <=, >=
5. 复杂条件：支持嵌套和分组
"""

import ast
import operator
import re
from typing import Any, Dict, List, Optional, Union
from enum import Enum


class ConditionOperator(Enum):
    """条件操作符"""

    # 逻辑运算
    AND = "and"
    OR = "or"
    NOT = "not"

    # 比较运算
    EQ = "=="
    NE = "!="
    LT = "<"
    LE = "<="
    GT = ">"
    GE = ">="

    # 成员运算
    IN = "in"
    NOT_IN = "not_in"

    # 存在运算
    EXISTS = "exists"
    NOT_EXISTS = "not_exists"

    # 正则匹配
    MATCHES = "matches"
    NOT_MATCHES = "not_matches"


class ConditionNode:
    """条件节点"""

    def __init__(
        self,
        operator: ConditionOperator,
        operands: List[Any],
        raw: Optional[str] = None,
    ):
        self.operator = operator
        self.operands = operands
        self.raw = raw

    def evaluate(self, context: Dict[str, Any]) -> bool:
        """评估条件节点"""
        if self.operator == ConditionOperator.AND:
            return all(self._eval_operand(op, context) for op in self.operands)
        elif self.operator == ConditionOperator.OR:
            return any(self._eval_operand(op, context) for op in self.operands)
        elif self.operator == ConditionOperator.NOT:
            return not self._eval_operand(self.operands[0], context)
        elif self.operator == ConditionOperator.EQ:
            return self._eval_operand(self.operands[0], context) == self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.NE:
            return self._eval_operand(self.operands[0], context) != self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.LT:
            return self._eval_operand(self.operands[0], context) < self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.LE:
            return self._eval_operand(self.operands[0], context) <= self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.GT:
            return self._eval_operand(self.operands[0], context) > self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.GE:
            return self._eval_operand(self.operands[0], context) >= self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.IN:
            return self._eval_operand(self.operands[0], context) in self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.NOT_IN:
            return self._eval_operand(self.operands[0], context) not in self._eval_operand(
                self.operands[1], context
            )
        elif self.operator == ConditionOperator.EXISTS:
            key = self.operands[0]
            return self._resolve_key(key, context, check_exists=True)
        elif self.operator == ConditionOperator.NOT_EXISTS:
            key = self.operands[0]
            return not self._resolve_key(key, context, check_exists=True)
        elif self.operator == ConditionOperator.MATCHES:
            import re
            value = str(self._eval_operand(self.operands[0], context))
            pattern = self._eval_operand(self.operands[1], context)
            return re.search(pattern, value) is not None
        elif self.operator == ConditionOperator.NOT_MATCHES:
            import re
            value = str(self._eval_operand(self.operands[0], context))
            pattern = self._eval_operand(self.operands[1], context)
            return re.search(pattern, value) is None
        else:
            raise ValueError(f"Unknown operator: {self.operator}")

    def _eval_operand(self, operand: Any, context: Dict[str, Any]) -> Any:
        """评估操作数"""
        if isinstance(operand, ConditionNode):
            return operand.evaluate(context)
        elif isinstance(operand, str):
            # 可能是变量引用
            if operand.startswith("$"):
                return self._resolve_variable(operand, context)
            return operand
        else:
            return operand

    def _resolve_variable(self, var_ref: str, context: Dict[str, Any]) -> Any:
        """解析变量引用"""
        # 移除 $ 前缀
        ref = var_ref[1:]

        # 解析路径
        parts = ref.split(".")
        value = context

        for part in parts:
            if isinstance(value, dict):
                value = value.get(part)
                if value is None:
                    return None
            else:
                return None

        return value

    def _resolve_key(self, key: str, context: Dict[str, Any], check_exists: bool = False) -> Any:
        """解析键路径"""
        if isinstance(key, str) and key.startswith("$"):
            value = self._resolve_variable(key, context)
            if check_exists:
                return value is not None
            return value
        return key

    def __str__(self) -> str:
        if self.raw:
            return self.raw
        return f"{self.operator.value}({', '.join(str(op) for op in self.operands)})"


class ConditionEngine:
    """
    条件执行引擎

    职责：
    1. 解析条件表达式
    2. 评估条件
    3. 变量绑定
    """

    # 操作符映射
    OPERATORS = {
        # 逻辑运算
        "&&": ConditionOperator.AND,
        "and": ConditionOperator.AND,
        "||": ConditionOperator.OR,
        "or": ConditionOperator.OR,
        "!": ConditionOperator.NOT,
        "not": ConditionOperator.NOT,
        # 比较运算
        "==": ConditionOperator.EQ,
        "!=": ConditionOperator.NE,
        "<": ConditionOperator.LT,
        "<=": ConditionOperator.LE,
        ">": ConditionOperator.GT,
        ">=": ConditionOperator.GE,
        # 成员运算
        "in": ConditionOperator.IN,
        "not_in": ConditionOperator.NOT_IN,
        "not in": ConditionOperator.NOT_IN,
        # 存在运算
        "exists": ConditionOperator.EXISTS,
        "not_exists": ConditionOperator.NOT_EXISTS,
        "not exists": ConditionOperator.NOT_EXISTS,
        # 正则匹配
        "matches": ConditionOperator.MATCHES,
        "not_matches": ConditionOperator.NOT_MATCHES,
        "not matches": ConditionOperator.NOT_MATCHES,
    }

    def __init__(self):
        """初始化条件引擎"""
        pass

    def parse(self, condition: str) -> ConditionNode:
        """
        解析条件表达式

        Args:
            condition: 条件表达式字符串

        Returns:
            ConditionNode
        """
        # 尝试使用 Python AST 解析
        try:
            return self._parse_python_ast(condition)
        except Exception:
            # 回退到自定义解析
            return self._parse_custom(condition)

    def evaluate(self, condition: Union[str, ConditionNode], context: Dict[str, Any]) -> bool:
        """
        评估条件

        Args:
            condition: 条件表达式或节点
            context: 评估上下文

        Returns:
            布尔结果
        """
        if isinstance(condition, str):
            node = self.parse(condition)
        else:
            node = condition

        return node.evaluate(context)

    def _parse_python_ast(self, condition: str) -> ConditionNode:
        """使用 Python AST 解析条件"""
        # 清理条件字符串
        condition = condition.strip()
        if not condition:
            raise ValueError("Empty condition")

        # 替换自定义操作符为 Python 操作符
        for custom_op, py_op in {
            "&&": "and",
            "||": "or",
            "exists": "True",  # 占位
            "not exists": "False",  # 占位
        }.items():
            condition = condition.replace(custom_op, py_op)

        # 解析 AST
        tree = ast.parse(condition, mode="eval")
        return self._ast_to_node(tree.body)

    def _ast_to_node(self, node: ast.AST) -> ConditionNode:
        """将 AST 节点转换为 ConditionNode"""
        if isinstance(node, ast.BoolOp):
            op = ConditionOperator.AND if isinstance(node.op, ast.And) else ConditionOperator.OR
            return ConditionNode(
                operator=op,
                operands=[self._ast_to_node(v) for v in node.values],
            )
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return ConditionNode(
                operator=ConditionOperator.NOT,
                operands=[self._ast_to_node(node.operand)],
            )
        elif isinstance(node, ast.Compare):
            # 处理比较运算
            left = self._ast_to_literal(node.left)
            operators = []
            comparators = []

            for op, comparator in zip(node.ops, node.comparators):
                if isinstance(op, ast.Eq):
                    operators.append(ConditionOperator.EQ)
                elif isinstance(op, ast.NotEq):
                    operators.append(ConditionOperator.NE)
                elif isinstance(op, ast.Lt):
                    operators.append(ConditionOperator.LT)
                elif isinstance(op, ast.LtE):
                    operators.append(ConditionOperator.LE)
                elif isinstance(op, ast.Gt):
                    operators.append(ConditionOperator.GT)
                elif isinstance(op, ast.GtE):
                    operators.append(ConditionOperator.GE)
                else:
                    raise ValueError(f"Unsupported comparison operator: {op}")

                comparators.append(self._ast_to_literal(comparator))

            # 简化：只处理第一个比较
            return ConditionNode(
                operator=operators[0],
                operands=[left, comparators[0]],
            )
        elif isinstance(node, ast.Name):
            # 变量引用
            return f"${node.id}"
        elif isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Attribute):
            # 属性访问: obj.attr
            obj = self._ast_to_literal(node.value)
            return f"${obj}.{node.attr}"
        else:
            raise ValueError(f"Unsupported AST node: {type(node)}")

    def _ast_to_literal(self, node: ast.AST) -> Any:
        """将 AST 节点转换为字面量或变量引用"""
        if isinstance(node, ast.Constant):
            return node.value
        elif isinstance(node, ast.Name):
            return f"${node.id}"
        elif isinstance(node, ast.Attribute):
            obj = self._ast_to_literal(node.value)
            return f"${obj}.{node.attr}"
        elif isinstance(node, ast.UnaryOp):
            # 处理负数
            if isinstance(node.op, ast.USub):
                value = self._ast_to_literal(node.operand)
                if isinstance(value, (int, float)):
                    return -value
        raise ValueError(f"Cannot convert to literal: {type(node)}")

    def _parse_custom(self, condition: str) -> ConditionNode:
        """自定义解析器（简化版）"""
        # 简单实现：解析二元操作
        for op_str, op in [
            ("&&", ConditionOperator.AND),
            ("||", ConditionOperator.OR),
        ]:
            if op_str in condition:
                parts = condition.split(op_str)
                return ConditionNode(
                    operator=op,
                    operands=[self.parse(p.strip()) for p in parts],
                    raw=condition,
                )

        # 尝试解析比较操作
        for op_str, op in [
            ("==", ConditionOperator.EQ),
            ("!=", ConditionOperator.NE),
            ("<=", ConditionOperator.LE),
            (">=", ConditionOperator.GE),
            ("<", ConditionOperator.LT),
            (">", ConditionOperator.GT),
        ]:
            if op_str in condition:
                parts = condition.split(op_str)
                left, right = parts[0].strip(), parts[1].strip()
                # 转换字面量
                left_val = self._parse_literal(left)
                right_val = self._parse_literal(right)
                return ConditionNode(
                    operator=op,
                    operands=[left_val, right_val],
                    raw=condition,
                )

        # 简单变量引用
        if condition.startswith("$"):
            # 变量存在性检查
            return ConditionNode(
                operator=ConditionOperator.EXISTS,
                operands=[condition],
                raw=condition,
            )

        # 尝试解析为字面量
        return self._parse_literal(condition)

    def _parse_literal(self, value: str) -> Any:
        """解析字面量"""
        value = value.strip()

        # 变量引用
        if value.startswith("$"):
            return value

        # 布尔值
        if value == "True":
            return True
        if value == "False":
            return False

        # None/null
        if value in ("None", "null"):
            return None

        # 数字
        try:
            if "." in value:
                return float(value)
            return int(value)
        except ValueError:
            pass

        # 字符串（去除引号）
        if (value.startswith('"') and value.endswith('"')) or \
           (value.startswith("'") and value.endswith("'")):
            return value[1:-1]

        # 默认作为字符串返回
        return value

    def evaluate_batch(
        self,
        conditions: List[Union[str, ConditionNode]],
        context: Dict[str, Any],
        logic: str = "all",
    ) -> bool:
        """
        批量评估条件

        Args:
            conditions: 条件列表
            context: 评估上下文
            logic: 逻辑运算方式 ("all" 或 "any")

        Returns:
            布尔结果
        """
        results = [self.evaluate(cond, context) for cond in conditions]

        if logic == "all":
            return all(results)
        elif logic == "any":
            return any(results)
        else:
            raise ValueError(f"Invalid logic: {logic}")
