"""
test_variable_resolver.py — VariableResolver + ExpressionEvaluator 单元测试

覆盖范围：
  - parse_reference(): $inputs.xxx、$sX_yyy 格式解析
  - resolve_reference(): inputs/step/context 引用
  - resolve_all_in_dict(): 嵌套字典递归解析
  - extract_step_dependencies(): 依赖提取
  - ExpressionEvaluator.evaluate(): 比较表达式求值
"""

import pytest

from lee.orchestrator.execution.variable_resolver import (
    VariableResolver,
    ExpressionEvaluator,
)
from lee.orchestrator.ir.models import VariableIR


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def resolver():
    return VariableResolver()


@pytest.fixture
def context():
    return {
        "inputs": {
            "prd": "/path/to/prd.md",
            "repo": "example-repo",
            "nested": {"key1": "val1", "key2": {"deep": "deep_val"}},
        },
        "step_outputs": {
            "s1_1": {"generated_text": "hello", "status": "done"},
            "s2_1": {
                "consistency_matrix": {"conflicts": 3, "items": ["a", "b"]},
                "output": "some output",
            },
        },
        "workflow_id": "wf-123",
    }


@pytest.fixture
def evaluator(resolver):
    return ExpressionEvaluator(resolver)


# ============================================================================
# VariableResolver — parse_reference
# ============================================================================

class TestParseReference:

    def test_inputs_simple(self, resolver):
        var = resolver.parse_reference("$inputs.prd")
        assert var.source_type == "inputs"
        assert var.path == ["prd"]
        assert var.step_id is None

    def test_inputs_nested(self, resolver):
        var = resolver.parse_reference("$inputs.nested.key1")
        assert var.source_type == "inputs"
        assert var.path == ["nested", "key1"]

    def test_step_output_basic(self, resolver):
        var = resolver.parse_reference("$s1_1")
        assert var.source_type == "step"
        assert var.step_id == "s1_1"
        assert var.path == []

    def test_step_output_with_path(self, resolver):
        var = resolver.parse_reference("$s2_1_output")
        assert var.source_type == "step"
        assert var.step_id == "s2_1"
        assert var.path == ["output"]

    def test_context_reference(self, resolver):
        var = resolver.parse_reference("$workflow_id")
        assert var.source_type == "context"
        assert var.path == ["workflow_id"]

    def test_invalid_empty(self, resolver):
        with pytest.raises(ValueError, match="Invalid variable reference"):
            resolver.parse_reference("")

    def test_invalid_no_dollar(self, resolver):
        with pytest.raises(ValueError, match="must start with"):
            resolver.parse_reference("inputs.prd")

    def test_invalid_none(self, resolver):
        with pytest.raises(ValueError, match="Invalid variable reference"):
            resolver.parse_reference(None)


# ============================================================================
# VariableResolver — resolve_reference
# ============================================================================

class TestResolveReference:

    def test_resolve_inputs_simple(self, resolver, context):
        val = resolver.resolve_reference("$inputs.prd", context)
        assert val == "/path/to/prd.md"

    def test_resolve_inputs_nested(self, resolver, context):
        val = resolver.resolve_reference("$inputs.nested.key2.deep", context)
        assert val == "deep_val"

    def test_resolve_step_output(self, resolver, context):
        val = resolver.resolve_reference("$s1_1", context)
        assert val == {"generated_text": "hello", "status": "done"}

    def test_resolve_step_output_with_path(self, resolver, context):
        val = resolver.resolve_reference("$s2_1_output", context)
        assert val == "some output"

    def test_resolve_context(self, resolver, context):
        val = resolver.resolve_reference("$workflow_id", context)
        assert val == "wf-123"

    def test_resolve_missing_input(self, resolver, context):
        with pytest.raises(ValueError, match="Cannot access key"):
            resolver.resolve_reference("$inputs.nonexistent", context)

    def test_resolve_missing_step(self, resolver, context):
        with pytest.raises(ValueError, match="Step output not found"):
            resolver.resolve_reference("$s9_9", context)

    def test_resolve_missing_step_key_returns_none(self, resolver, context):
        """当 step output 是 dict 但 key 不存在时，返回 None"""
        val = resolver.resolve_reference("$s1_1_missing_key", context)
        assert val is None

    def test_resolve_from_variable_ir(self, resolver, context):
        """直接传入 VariableIR 对象"""
        var_ir = VariableIR(
            reference="$inputs.repo",
            source_type="inputs",
            path=["repo"],
        )
        val = resolver.resolve_reference(var_ir, context)
        assert val == "example-repo"


# ============================================================================
# VariableResolver — resolve_all_in_dict
# ============================================================================

class TestResolveAllInDict:

    def test_flat_dict(self, resolver, context):
        data = {"prd_path": "$inputs.prd", "repo_name": "$inputs.repo"}
        result = resolver.resolve_all_in_dict(data, context)
        assert result["prd_path"] == "/path/to/prd.md"
        assert result["repo_name"] == "example-repo"

    def test_nested_dict(self, resolver, context):
        data = {"outer": {"inner": "$inputs.prd"}}
        result = resolver.resolve_all_in_dict(data, context)
        assert result["outer"]["inner"] == "/path/to/prd.md"

    def test_non_reference_preserved(self, resolver, context):
        data = {"label": "hello", "count": 42}
        result = resolver.resolve_all_in_dict(data, context)
        assert result == {"label": "hello", "count": 42}

    def test_unresolvable_reference_preserved(self, resolver, context):
        """无法解析的引用保留原值"""
        data = {"missing": "$inputs.nonexistent"}
        result = resolver.resolve_all_in_dict(data, context)
        assert result["missing"] == "$inputs.nonexistent"

    def test_list_in_dict(self, resolver, context):
        data = {"items": [{"a": "$inputs.prd"}, {"b": "static"}]}
        result = resolver.resolve_all_in_dict(data, context)
        assert result["items"][0]["a"] == "/path/to/prd.md"
        assert result["items"][1]["b"] == "static"


# ============================================================================
# VariableResolver — extract_step_dependencies
# ============================================================================

class TestExtractStepDependencies:

    def test_single_dependency(self, resolver):
        inputs = [{"source": "$s1_1"}]
        deps = resolver.extract_step_dependencies(inputs)
        assert deps == ["s1_1"]

    def test_multiple_dependencies(self, resolver):
        inputs = [{"a": "$s1_1"}, {"b": "$s2_1_output"}]
        deps = sorted(resolver.extract_step_dependencies(inputs))
        assert deps == ["s1_1", "s2_1"]

    def test_no_dependencies(self, resolver):
        inputs = [{"label": "static"}]
        deps = resolver.extract_step_dependencies(inputs)
        assert deps == []

    def test_nested_dependency(self, resolver):
        inputs = [{"nested": {"deep": "$s1_1"}}]
        deps = resolver.extract_step_dependencies(inputs)
        assert deps == ["s1_1"]


# ============================================================================
# VariableResolver — validate_context / get_missing_variables
# ============================================================================

class TestValidateContext:

    def test_validate_all_present(self, resolver, context):
        required = [
            VariableIR(reference="$inputs.prd", source_type="inputs", path=["prd"]),
        ]
        errors = resolver.validate_context(required, context)
        assert errors == []

    def test_validate_missing(self, resolver, context):
        required = [
            VariableIR(reference="$inputs.nonexistent", source_type="inputs", path=["nonexistent"]),
        ]
        errors = resolver.validate_context(required, context)
        assert len(errors) == 1

    def test_get_missing_variables(self, resolver, context):
        data = {"a": "$inputs.prd", "b": "$inputs.nonexistent"}
        missing = resolver.get_missing_variables(data, context)
        assert "$inputs.nonexistent" in missing
        assert "$inputs.prd" not in missing


# ============================================================================
# ExpressionEvaluator
# ============================================================================

class TestExpressionEvaluator:

    def test_greater_than_true(self, evaluator):
        ctx = {"conflicts": 5}
        assert evaluator.evaluate("conflicts > 0", ctx) is True

    def test_greater_than_false(self, evaluator):
        ctx = {"conflicts": 0}
        assert evaluator.evaluate("conflicts > 0", ctx) is False

    def test_equals_true(self, evaluator):
        ctx = {"status": "rejected"}
        assert evaluator.evaluate("status == 'rejected'", ctx) is True

    def test_equals_false(self, evaluator):
        ctx = {"status": "approved"}
        assert evaluator.evaluate("status == 'rejected'", ctx) is False

    def test_step_output_path(self, evaluator, context):
        """s2.1.consistency_matrix.conflicts > 0"""
        assert evaluator.evaluate("s2.1.consistency_matrix.conflicts > 0", context) is True

    def test_unknown_expression_defaults_true(self, evaluator):
        """无法解析的表达式默认返回 True"""
        assert evaluator.evaluate("something_unknown", {}) is True

    def test_missing_key_defaults_true(self, evaluator):
        """缺失键的比较默认返回 True（允许执行）"""
        assert evaluator.evaluate("missing_key > 10", {}) is True

    def test_compare_values_less_than(self, evaluator):
        assert evaluator._compare_values(3, "<", 5) is True
        assert evaluator._compare_values(5, "<", 3) is False

    def test_compare_values_equals(self, evaluator):
        assert evaluator._compare_values(5, "==", 5) is True
        assert evaluator._compare_values(5, "==", 3) is False

    def test_compare_values_not_equals(self, evaluator):
        assert evaluator._compare_values(5, "!=", 3) is True
        assert evaluator._compare_values(5, "!=", 5) is False

    def test_compare_values_none(self, evaluator):
        assert evaluator._compare_values(None, ">", 0) is False

    def test_unknown_operator(self, evaluator):
        with pytest.raises(ValueError, match="Unknown operator"):
            evaluator._compare_values(5, "?", 3)
