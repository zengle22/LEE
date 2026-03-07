"""
AutoCheckGateRunner 单元测试

测试覆盖：
1. 表达式评估（==, !=, >, <, and, or, not）
2. 安全过滤（拒绝危险模式）
3. 上下文变量替换
4. 扁平化嵌套字典
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from lee.orchestrator.execution.runners.auto_check_gate_runner import AutoCheckGateRunner
from lee.orchestrator.storage.models import StepResult, TaskExecutionStatus


class TestAutoCheckGateRunner:
    """AutoCheckGateRunner 测试套件"""

    def setup_method(self):
        """测试前设置"""
        self.runner = AutoCheckGateRunner()

    # ========================================================================
    # can_handle 测试
    # ========================================================================

    def test_can_handle_auto_check(self):
        """测试识别 auto_check 类型"""
        assert self.runner.can_handle("auto_check") is True
        assert self.runner.can_handle("auto_check_gate") is True

    def test_can_handle_other_types(self):
        """测试拒绝其他类型"""
        assert self.runner.can_handle("human_gate") is False
        assert self.runner.can_handle("compliance_gate") is False
        assert self.runner.can_handle("agent") is False
        assert self.runner.can_handle("skill") is False

    # ========================================================================
    # _build_eval_context 测试
    # ========================================================================

    def test_build_eval_context_empty(self):
        """测试构建空上下文"""
        result = self.runner._build_eval_context({})
        assert result == {}

    def test_build_eval_context_flat_dict(self):
        """测试构建扁平字典上下文"""
        step_outputs = {
            "step1": {"status": "healthy", "count": 5},
            "step2": {"result": "passed"},
        }
        result = self.runner._build_eval_context(step_outputs)

        # 顶层键应该存在
        assert result["status"] == "healthy"
        assert result["count"] == 5
        assert result["result"] == "passed"

        # 完整的步骤输出也应该存在
        assert result["_step1"]["status"] == "healthy"
        assert result["_step2"]["result"] == "passed"

    def test_build_eval_context_nested_dict(self):
        """测试构建嵌套字典上下文"""
        step_outputs = {
            "step1": {
                "environment_info": {
                    "status": "healthy",
                    "version": "1.0.0",
                }
            }
        }
        result = self.runner._build_eval_context(step_outputs)

        # 扁平化后的路径应该存在
        assert result["environment_info.status"] == "healthy"
        assert result["environment_info.version"] == "1.0.0"

        # 完整的步骤输出也应该存在
        assert result["_step1"]["environment_info"]["status"] == "healthy"

    # ========================================================================
    # _flatten_dict 测试
    # ========================================================================

    def test_flatten_dict_empty(self):
        """测试扁平化空字典"""
        context = {}
        self.runner._flatten_dict({}, context)
        assert context == {}

    def test_flatten_dict_single_level(self):
        """测试扁平化单层字典"""
        d = {"a": 1, "b": 2}
        context = {}
        self.runner._flatten_dict(d, context, prefix="test")

        assert context["test.a"] == 1
        assert context["test.b"] == 2

    def test_flatten_dict_multi_level(self):
        """测试扁平化多层字典"""
        d = {
            "level1": {
                "level2": {
                    "value": "deep"
                },
                "other": "shallow"
            }
        }
        context = {}
        self.runner._flatten_dict(d, context)

        assert context["level1.level2.value"] == "deep"
        assert context["level1.other"] == "shallow"

    def test_flatten_dict_with_list(self):
        """测试扁平化包含列表的字典"""
        d = {"items": [1, 2, 3], "name": "test"}
        context = {}
        self.runner._flatten_dict(d, context)

        assert context["items"] == [1, 2, 3]
        assert context["name"] == "test"

    # ========================================================================
    # _get_context_value 测试
    # ========================================================================

    def test_get_context_value_flat(self):
        """测试获取扁平值"""
        context = {"status": "healthy", "count": 5}

        assert self.runner._get_context_value(context, "status") == "healthy"
        assert self.runner._get_context_value(context, "count") == 5

    def test_get_context_value_nested(self):
        """测试获取嵌套值"""
        context = {
            "environment_info.status": "healthy",
            "environment_info.version": "1.0.0",
        }

        assert self.runner._get_context_value(context, "environment_info.status") == "healthy"
        assert self.runner._get_context_value(context, "environment_info.version") == "1.0.0"

    def test_get_context_value_missing(self):
        """测试获取不存在的值"""
        context = {"status": "healthy"}

        assert self.runner._get_context_value(context, "nonexistent") is None
        assert self.runner._get_context_value(context, "status.extra") is None

    def test_get_context_value_path_not_dict(self):
        """测试路径中间值不是字典"""
        context = {"status.value": "healthy"}  # status 的值是字符串，不是字典

        assert self.runner._get_context_value(context, "status.value") == "healthy"
        assert self.runner._get_context_value(context, "status.value.extra") is None

    # ========================================================================
    # _substitute_variables 测试
    # ========================================================================

    def test_substitute_simple_variable(self):
        """测试替换简单变量"""
        context = {"status": "healthy"}
        expression = "status"

        result = self.runner._substitute_variables(expression, context)
        assert result == "'healthy'"

    def test_substitute_variable_in_expression(self):
        """测试替换表达式中的变量"""
        context = {"status": "healthy"}
        expression = "status == 'healthy'"

        result = self.runner._substitute_variables(expression, context)
        assert result == "'healthy' == 'healthy'"

    def test_substitute_numeric_variable(self):
        """测试替换数字变量"""
        context = {"count": 5}
        expression = "count > 3"

        result = self.runner._substitute_variables(expression, context)
        assert result == "5 > 3"

    def test_substitute_boolean_variable(self):
        """测试替换布尔变量"""
        context = {"passed": True}
        expression = "passed"

        result = self.runner._substitute_variables(expression, context)
        assert result == "True"

    def test_substitute_none_variable(self):
        """测试替换 None 变量"""
        context = {"value": None}
        expression = "value"

        result = self.runner._substitute_variables(expression, context)
        assert result == "None"

    def test_substitute_missing_variable(self):
        """测试替换不存在的变量"""
        context = {"other": "value"}
        expression = "nonexistent"

        result = self.runner._substitute_variables(expression, context)
        assert result == "None"

    def test_substitute_nested_variable(self):
        """测试替换嵌套变量"""
        context = {"environment_info.status": "healthy"}
        expression = "environment_info.status == 'healthy'"

        result = self.runner._substitute_variables(expression, context)
        assert result == "'healthy' == 'healthy'"

    def test_substitute_preserves_strings(self):
        """测试保留字符串字面量"""
        context = {"status": "healthy"}
        expression = "status == 'healthy'"

        result = self.runner._substitute_variables(expression, context)
        # 字符串字面量应该保持不变
        assert "'healthy'" in result

    # ========================================================================
    # _safe_eval 测试
    # ========================================================================

    def test_safe_eval_simple_comparison(self):
        """测试简单比较"""
        assert self.runner._safe_eval("5 > 3") is True
        assert self.runner._safe_eval("5 < 3") is False
        assert self.runner._safe_eval("5 == 5") is True

    def test_safe_eval_string_comparison(self):
        """测试字符串比较"""
        assert self.runner._safe_eval("'healthy' == 'healthy'") is True
        assert self.runner._safe_eval("'healthy' == 'unhealthy'") is False

    def test_safe_eval_boolean(self):
        """测试布尔值"""
        assert self.runner._safe_eval("True") is True
        assert self.runner._safe_eval("False") is False

    def test_safe_eval_and(self):
        """测试 AND 运算"""
        assert self.runner._safe_eval("True and True") is True
        assert self.runner._safe_eval("True and False") is False

    def test_safe_eval_or(self):
        """测试 OR 运算"""
        assert self.runner._safe_eval("True or False") is True
        assert self.runner._safe_eval("False or False") is False

    def test_safe_eval_not(self):
        """测试 NOT 运算"""
        assert self.runner._safe_eval("not False") is True
        assert self.runner._safe_eval("not True") is False

    def test_safe_eval_complex_expression(self):
        """测试复杂表达式"""
        assert self.runner._safe_eval("5 > 3 and 10 < 20") is True
        assert self.runner._safe_eval("5 > 3 or 10 > 20") is True

    def test_safe_eval_dangerous_patterns(self):
        """测试拒绝危险模式"""
        assert self.runner._safe_eval("__import__('os')") is False
        assert self.runner._safe_eval("exec('code')") is False
        assert self.runner._safe_eval("eval('code')") is False
        assert self.runner._safe_eval("import os") is False
        assert self.runner._safe_eval("lambda x: x") is False
        assert self.runner._safe_eval("def func(): pass") is False

    def test_safe_eval_invalid_syntax(self):
        """测试无效语法"""
        assert self.runner._safe_eval("5 > > 3") is False
        assert self.runner._safe_eval("invalid syntax here") is False

    def test_safe_eval_empty_string(self):
        """测试空字符串"""
        assert self.runner._safe_eval("") is False

    # ========================================================================
    # _evaluate_check 测试
    # ========================================================================

    def test_evaluate_check_empty_expression(self):
        """测试空表达式返回 True"""
        assert self.runner._evaluate_check("", {}) is True
        assert self.runner._evaluate_check("   ", {}) is True

    def test_evaluate_check_simple_variable(self):
        """测试简单变量检查"""
        context = {"status": "healthy"}
        assert self.runner._evaluate_check("status", context) is True

        context = {"status": ""}
        assert self.runner._evaluate_check("status", context) is False

    def test_evaluate_check_equality(self):
        """测试相等性检查"""
        context = {"status": "healthy"}
        assert self.runner._evaluate_check("status == 'healthy'", context) is True
        assert self.runner._evaluate_check("status == 'unhealthy'", context) is False

    def test_evaluate_check_inequality(self):
        """测试不等性检查"""
        context = {"status": "healthy"}
        assert self.runner._evaluate_check("status != 'unhealthy'", context) is True
        assert self.runner._evaluate_check("status != 'healthy'", context) is False

    def test_evaluate_check_numeric(self):
        """测试数字比较"""
        context = {"count": 5, "threshold": 3}
        assert self.runner._evaluate_check("count > threshold", context) is True
        assert self.runner._evaluate_check("count < threshold", context) is False
        assert self.runner._evaluate_check("count >= 5", context) is True
        assert self.runner._evaluate_check("count <= 5", context) is True

    def test_evaluate_check_logical(self):
        """测试逻辑运算"""
        context = {"a": True, "b": False}
        assert self.runner._evaluate_check("a and b", context) is False
        assert self.runner._evaluate_check("a or b", context) is True
        assert self.runner._evaluate_check("not b", context) is True

    def test_evaluate_check_nested_path(self):
        """测试嵌套路径"""
        context = {"environment_info.status": "healthy"}
        assert self.runner._evaluate_check("environment_info.status == 'healthy'", context) is True

    def test_evaluate_check_missing_variable(self):
        """测试缺失变量"""
        context = {"other": "value"}
        # 缺失的变量会被替换为 None
        assert self.runner._evaluate_check("nonexistent", context) is False

    def test_evaluate_check_invalid_expression(self):
        """测试无效表达式"""
        context = {"status": "healthy"}
        # 无效表达式应该返回 False
        assert self.runner._evaluate_check("status === 'healthy'", context) is False

    # ========================================================================
    # execute 集成测试
    # ========================================================================

    @pytest.mark.asyncio
    async def test_execute_check_passed(self):
        """测试执行通过检查"""
        # 准备 mock 对象
        mock_store = AsyncMock()
        mock_state_machine = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.store = mock_store
        mock_ctx.state_machine = mock_state_machine

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {"step1": {"status": "healthy"}}
        }
        mock_store.get_workflow.return_value = mock_instance

        # 模拟 task_executions（无运行中的记录）
        mock_store.get_task_executions.return_value = []

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.id = "test_gate"
        mock_step.config = {
            "gate": {
                "check": "status == 'healthy'",
                "on_fail": {"action": "fail_step"}
            }
        }

        # 执行
        result = await self.runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证
        assert result.status == "success"
        assert result.output["auto_check_passed"] is True
        mock_state_machine.complete_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_check_failed(self):
        """测试执行失败检查"""
        # 准备 mock 对象
        mock_store = AsyncMock()
        mock_state_machine = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.store = mock_store
        mock_ctx.state_machine = mock_state_machine

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {"step1": {"status": "unhealthy"}}
        }
        mock_store.get_workflow.return_value = mock_instance

        # 模拟 task_executions
        mock_store.get_task_executions.return_value = []

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.id = "test_gate"
        mock_step.config = {
            "gate": {
                "check": "status == 'healthy'",
                "on_fail": {"action": "fail_step"}
            }
        }

        # 执行
        result = await self.runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证
        assert result.status == "failed"
        assert result.output["auto_check_passed"] is False
        mock_state_machine.fail_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_check_failed_blocks_for_human_gate(self):
        """测试失败后进入人工门禁分支而不是直接失败"""
        mock_store = AsyncMock()
        mock_state_machine = AsyncMock()
        mock_event_log = MagicMock()
        mock_ctx = MagicMock()
        mock_ctx.store = mock_store
        mock_ctx.state_machine = mock_state_machine
        mock_ctx.event_log = mock_event_log

        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {"spec_review": {"blocker_count": 1, "major_count": 2}}
        }
        mock_store.get_workflow.return_value = mock_instance
        mock_store.get_task_executions.return_value = []
        mock_store.get_gate_approval.return_value = None

        mock_step = MagicMock()
        mock_step.id = "review_gate"
        mock_step.gate_id = "spec_review_gate"
        mock_step.config = {
            "gate": {
                "check": "blocker_count == 0",
                "reviewers": '[{"name": "owner", "role": "reviewer"}]',
                "approval_criteria": ["Blocking review findings are resolved"],
                "on_fail": {"action": "human_gate"},
                "on_revise": {"target_step": "spec_maintenance"},
            }
        }

        result = await self.runner.execute("workflow-123", mock_step, mock_ctx)

        assert result.status == "blocked"
        assert result.blocked_reason == "human_gate"
        mock_store.update_workflow_status.assert_called()
        mock_store.create_gate_approval.assert_called_once()
        gate_approval = mock_store.create_gate_approval.call_args[0][0]
        assert gate_approval.gate_id == "spec_review_gate"
        assert gate_approval.default_revise_target == "spec_maintenance"
        assert gate_approval.reviewers == [{"name": "owner", "role": "reviewer"}]
        mock_state_machine.fail_step.assert_not_called()

    @pytest.mark.asyncio
    async def test_execute_updates_task_execution(self):
        """测试执行更新 task_execution"""
        # 准备 mock 对象
        mock_store = AsyncMock()
        mock_state_machine = AsyncMock()
        mock_ctx = MagicMock()
        mock_ctx.store = mock_store
        mock_ctx.state_machine = mock_state_machine

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {"step1": {"status": "healthy"}}
        }
        mock_store.get_workflow.return_value = mock_instance

        # 模拟运行中的 task_execution
        mock_execution = MagicMock()
        mock_execution.id = "exec-123"
        mock_execution.step_name = "test_gate"
        mock_execution.status = TaskExecutionStatus.RUNNING
        mock_store.get_task_executions.return_value = [mock_execution]

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.id = "test_gate"
        mock_step.config = {
            "gate": {
                "check": "status == 'healthy'",
            }
        }

        # 执行
        result = await self.runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证 task_execution 被更新
        mock_store.update_task_execution.assert_called_once()
        call_args = mock_store.update_task_execution.call_args
        assert call_args[0][0] == "exec-123"
        assert call_args[0][1] == TaskExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_workflow_not_found(self):
        """测试工作流不存在时抛出异常"""
        # 准备 mock 对象
        mock_store = AsyncMock()
        mock_store.get_workflow.return_value = None
        mock_ctx = MagicMock()
        mock_ctx.store = mock_store

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.config = {}

        # 执行应该抛出异常
        with pytest.raises(ValueError, match="Workflow not found"):
            await self.runner.execute("workflow-123", mock_step, mock_ctx)
