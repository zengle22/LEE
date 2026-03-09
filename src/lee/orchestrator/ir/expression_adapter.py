from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


class ExpressionAdapterError(Exception):
    """Raised when a normalized expression cannot be evaluated."""


@dataclass
class EvaluationResult:
    passed: bool
    error_message: Optional[str] = None


class ExpressionAdapter:
    """Normalizes expression syntax and safely evaluates the supported subset."""

    def evaluate_condition(self, expression: str, context: Dict[str, Any]) -> bool:
        if not expression:
            return True

        normalized = self._normalize_expression(expression)
        normalized_context = self._normalize_context(context)
        try:
            tree = ast.parse(normalized, mode="eval")
            return bool(self._eval_node(tree.body, normalized_context))
        except Exception as exc:
            raise ExpressionAdapterError(str(exc)) from exc

    def evaluate_gate_rule(
        self,
        expression: str,
        context: Dict[str, Any],
        validation_method: Optional[str],
    ) -> EvaluationResult:
        normalized = self._normalize_expression(expression)
        normalized_context = self._normalize_context(context)

        try:
            if not validation_method or validation_method == "default":
                return EvaluationResult(self.evaluate_condition(normalized, normalized_context))

            evaluators = {
                "numeric_compare": self._evaluate_numeric_compare,
                "percentage": self._evaluate_percentage,
                "boolean": self._evaluate_boolean,
                "list_contains": self._evaluate_list_contains,
                "file_exists": self._evaluate_file_exists,
                "architecture_consistency": self._evaluate_architecture_consistency,
                "pattern_not_contains": self._evaluate_pattern_not_contains,
                "error_source_valid": self._evaluate_error_source_valid,
                "evidence_exists": self._evaluate_evidence_exists,
            }
            evaluator = evaluators.get(validation_method)
            if evaluator is None:
                raise ExpressionAdapterError(f"Unsupported validation method: {validation_method}")

            passed, error = evaluator(normalized, normalized_context)
            return EvaluationResult(passed=passed, error_message=error)
        except ExpressionAdapterError:
            raise
        except Exception as exc:
            raise ExpressionAdapterError(str(exc)) from exc

    def _normalize_expression(self, expression: str) -> str:
        normalized = expression.strip()
        if not normalized:
            return normalized

        normalized = re.sub(
            r"(?P<lhs>[A-Za-z0-9_.$]+)\s+CONTAINS\s+(?P<rhs>'[^']*'|\"[^\"]*\"|[A-Za-z0-9_.$]+)",
            lambda match: f"{match.group('rhs')} in {match.group('lhs')}",
            normalized,
            flags=re.IGNORECASE,
        )

        segments = []
        buffer = []
        quote_char: Optional[str] = None

        for char in normalized:
            if quote_char:
                buffer.append(char)
                if char == quote_char:
                    segments.append((True, "".join(buffer)))
                    buffer = []
                    quote_char = None
                continue

            if char in ("'", '"'):
                if buffer:
                    segments.append((False, "".join(buffer)))
                    buffer = []
                buffer.append(char)
                quote_char = char
                continue

            buffer.append(char)

        if buffer:
            segments.append((quote_char is not None, "".join(buffer)))

        processed = []
        replacements = {
            r"\$([A-Za-z_][\w.]*)": r"\1",
            r"\bAND\b": "and",
            r"\bOR\b": "or",
            r"\bNOT\b": "not",
            r"\btrue\b": "True",
            r"\bfalse\b": "False",
            r"\bnull\b": "None",
        }
        for is_quoted, segment in segments:
            if is_quoted:
                processed.append(segment)
                continue
            updated = segment
            for pattern, replacement in replacements.items():
                updated = re.sub(pattern, replacement, updated, flags=re.IGNORECASE)
            processed.append(updated)
        return "".join(processed)

    def _normalize_context(self, value: Any) -> Any:
        if isinstance(value, dict):
            return {key: self._normalize_context(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self._normalize_context(item) for item in value]
        if isinstance(value, tuple):
            return tuple(self._normalize_context(item) for item in value)
        if isinstance(value, set):
            return {self._normalize_context(item) for item in value}
        if hasattr(value, "__dataclass_fields__"):
            return {
                field_name: self._normalize_context(getattr(value, field_name))
                for field_name in value.__dataclass_fields__
            }
        if hasattr(value, "__dict__") and not isinstance(value, type):
            public_items = {
                key: self._normalize_context(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
            if public_items:
                return public_items

            derived_items = {}
            for key in dir(value):
                if key.startswith("_"):
                    continue
                try:
                    item = getattr(value, key)
                except Exception:
                    continue
                if callable(item):
                    continue
                derived_items[key] = self._normalize_context(item)
            if derived_items:
                return derived_items
        return value

    def _eval_node(self, node: ast.AST, context: Dict[str, Any]) -> Any:
        if isinstance(node, ast.BoolOp):
            values = [self._eval_node(value, context) for value in node.values]
            if isinstance(node.op, ast.And):
                return all(values)
            if isinstance(node.op, ast.Or):
                return any(values)
            raise ExpressionAdapterError(f"Unsupported boolean operator: {type(node.op).__name__}")

        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not self._eval_node(node.operand, context)

        if isinstance(node, ast.Compare):
            left = self._eval_node(node.left, context)
            for operator_node, comparator in zip(node.ops, node.comparators):
                right = self._eval_node(comparator, context)
                if isinstance(operator_node, ast.Eq):
                    ok = left == right
                elif isinstance(operator_node, ast.NotEq):
                    ok = left != right
                elif isinstance(operator_node, ast.Lt):
                    ok = left < right
                elif isinstance(operator_node, ast.LtE):
                    ok = left <= right
                elif isinstance(operator_node, ast.Gt):
                    ok = left > right
                elif isinstance(operator_node, ast.GtE):
                    ok = left >= right
                elif isinstance(operator_node, ast.In):
                    ok = left in right
                elif isinstance(operator_node, ast.NotIn):
                    ok = left not in right
                else:
                    raise ExpressionAdapterError(
                        f"Unsupported comparison operator: {type(operator_node).__name__}"
                    )
                if not ok:
                    return False
                left = right
            return True

        if isinstance(node, ast.Name):
            return context.get(node.id)

        if isinstance(node, ast.Attribute):
            parent = self._eval_node(node.value, context)
            if isinstance(parent, dict):
                return parent.get(node.attr)
            if hasattr(parent, node.attr):
                return getattr(parent, node.attr)
            return None

        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.List):
            return [self._eval_node(element, context) for element in node.elts]

        if isinstance(node, ast.Tuple):
            return tuple(self._eval_node(element, context) for element in node.elts)

        raise ExpressionAdapterError(f"Unsupported AST node: {type(node).__name__}")

    def _evaluate_numeric_compare(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        for operator_text in (">=", "<=", ">", "<"):
            if operator_text in expression:
                key, expected = expression.split(operator_text, 1)
                actual = self._get_nested_value(context, key.strip())
                if actual is None:
                    return False, f"Key '{key.strip()}' not found in context"
                expected_value = float(expected.strip())
                if operator_text == ">=":
                    return actual >= expected_value, None
                if operator_text == "<=":
                    return actual <= expected_value, None
                if operator_text == ">":
                    return actual > expected_value, None
                return actual < expected_value, None
        return False, f"Invalid numeric expression: {expression}"

    def _evaluate_percentage(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return self._evaluate_numeric_compare(expression, context)

    def _evaluate_boolean(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        value = self._get_nested_value(context, expression.strip())
        if isinstance(value, str):
            value = value.lower() in ("true", "yes", "1", "on")
        return bool(value), None

    def _evaluate_list_contains(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if " contains " not in expression.lower():
            return False, f"Invalid list expression: {expression}"
        key, expected = re.split(r"\s+contains\s+", expression, maxsplit=1, flags=re.IGNORECASE)
        actual = self._get_nested_value(context, key.strip())
        if actual is None:
            return False, f"Key '{key.strip()}' not found in context"
        target = expected.strip().strip("\"'")
        return target in actual, None

    def _evaluate_file_exists(self, expression: str, _context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        return Path(expression).exists(), None

    def _evaluate_architecture_consistency(self, _expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        conflicts = self._get_nested_value(context, "consistency_matrix.conflicts") or []
        passed = len(conflicts) == 0
        return passed, None if passed else f"Found {len(conflicts)} conflicts"

    def _evaluate_pattern_not_contains(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        if " NOT_CONTAINS " not in expression:
            return False, f"Invalid expression: {expression}"
        field_path, patterns_str = expression.split(" NOT_CONTAINS ", 1)
        text = self._get_nested_value(context, field_path.strip())
        if text is None:
            return True, None
        for pattern in [item.strip() for item in patterns_str.split(",")]:
            if re.search(pattern, str(text), re.IGNORECASE):
                return False, f"Text contains forbidden pattern: {pattern}"
        return True, None

    def _evaluate_error_source_valid(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        source = self._get_nested_value(context, expression.strip())
        if source is None:
            return True, None
        valid_sources = {"runner_cli", "orchestrator", "human_marked"}
        if source in valid_sources:
            return True, None
        return False, f"Invalid error source: {source}"

    def _evaluate_evidence_exists(self, expression: str, context: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        value = self._get_nested_value(context, expression.strip())
        return value is not None, None if value is not None else f"Evidence missing: {expression}"

    def _get_nested_value(self, data: Any, path: str) -> Any:
        current = data
        for part in path.split("."):
            if isinstance(current, dict):
                current = current.get(part)
            elif hasattr(current, part):
                current = getattr(current, part)
            else:
                return None
            if current is None:
                return None
        return current


_ADAPTER: Optional[ExpressionAdapter] = None


def get_expression_adapter() -> ExpressionAdapter:
    global _ADAPTER
    if _ADAPTER is None:
        _ADAPTER = ExpressionAdapter()
    return _ADAPTER
