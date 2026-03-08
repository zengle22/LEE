import pytest

from lee.orchestrator.ir.expression_adapter import ExpressionAdapter
from lee.orchestrator.ir.models import GateIR, GateRuleIR, RuleSeverity, RuleType, StepIR, StepKind


class MockPRD:
    is_frozen = True
    version = "1.0"


class TestExpressionAdapter:
    def setup_method(self):
        self.adapter = ExpressionAdapter()

    def test_normalizes_uppercase_logic(self):
        context = {"status": "active", "enabled": True}
        assert self.adapter.evaluate_condition("status == 'active' AND enabled == true", context) is True

    def test_supports_contains(self):
        context = {"analysis": {"risk_area": ["reversible", "irreversible"]}}
        assert self.adapter.evaluate_condition("analysis.risk_area CONTAINS 'irreversible'", context) is True

    def test_supports_object_attributes(self):
        assert self.adapter.evaluate_condition("prd.is_frozen == true", {"prd": MockPRD()}) is True

    def test_supports_dollar_paths(self):
        context = {"qa_test": {"exit_decision": "fail", "retry_count": 2}}
        assert self.adapter.evaluate_condition("$qa_test.exit_decision == 'fail' and $qa_test.retry_count > 1", context) is True


class TestGateRuleIRExpressionEvaluation:
    def test_default_expression_passes(self):
        rule = GateRuleIR(
            rule_id="RULE-001",
            name="PRD 冻结检查",
            rule_type=RuleType.MANDATORY,
            rule_expression="prd.is_frozen == true",
            severity=RuleSeverity.BLOCKER,
            exemption_allowed=False,
        )

        passed, error = rule.evaluate({"prd": MockPRD()})
        assert passed is True
        assert error is None

    def test_default_expression_fails(self):
        rule = GateRuleIR(
            rule_id="RULE-002",
            name="版本检查",
            rule_type=RuleType.MANDATORY,
            rule_expression="prd.version == '2.0'",
            severity=RuleSeverity.BLOCKER,
            exemption_allowed=False,
            error_message="版本不匹配",
        )

        passed, error = rule.evaluate({"prd": MockPRD()})
        assert passed is False
        assert error == "版本不匹配"

    def test_validation_method_still_works(self):
        rule = GateRuleIR(
            rule_id="RULE-003",
            name="覆盖率",
            rule_type=RuleType.MANDATORY,
            rule_expression="coverage >= 80",
            severity=RuleSeverity.BLOCKER,
            exemption_allowed=False,
            validation_method="numeric_compare",
        )

        passed, error = rule.evaluate({"coverage": 85})
        assert passed is True
        assert error is None

    def test_expression_error_returns_false(self):
        rule = GateRuleIR(
            rule_id="RULE-004",
            name="非法表达式",
            rule_type=RuleType.MANDATORY,
            rule_expression="invalid ++ expression",
            severity=RuleSeverity.BLOCKER,
            exemption_allowed=False,
        )

        passed, error = rule.evaluate({})
        assert passed is False
        assert "表达式求值失败" in error


class TestGateIRMandatoryEvaluation:
    def test_mandatory_failure_blocks_even_when_non_blocker(self):
        gate = GateIR(
            gate_id="gate-1",
            name="测试 Gate",
            description="mandatory should always block",
            mandatory_criteria=[
                GateRuleIR(
                    rule_id="RULE-005",
                    name="非 blocker 规则",
                    rule_type=RuleType.MANDATORY,
                    rule_expression="approved == true",
                    severity=RuleSeverity.INFO,
                    exemption_allowed=False,
                )
            ],
        )

        passed, issues = gate.evaluate({"approved": False})
        assert passed is False
        assert len(issues) == 1
        assert "非 blocker 规则" in issues[0]


class TestStepIRConditionEvaluation:
    def test_condition_true(self):
        step = StepIR(id="STEP-001", kind=StepKind.CONDITIONAL, name="测试步骤", description="", condition="count > 0")
        assert step._evaluate_condition({"count": 3}) is True

    def test_condition_false(self):
        step = StepIR(id="STEP-002", kind=StepKind.CONDITIONAL, name="测试步骤", description="", condition="count > 100")
        assert step._evaluate_condition({"count": 3}) is False

    def test_condition_supports_uppercase_logic(self):
        step = StepIR(
            id="STEP-003",
            kind=StepKind.CONDITIONAL,
            name="测试步骤",
            description="",
            condition="status == 'active' AND count > 1",
        )
        assert step._evaluate_condition({"status": "active", "count": 3}) is True

    def test_condition_error_fails_closed(self):
        step = StepIR(id="STEP-004", kind=StepKind.CONDITIONAL, name="测试步骤", description="", condition="invalid ++ expression")
        assert step._evaluate_condition({}) is False


class TestSimpleVariableExpressions:
    def test_bare_variable_condition(self):
        adapter = ExpressionAdapter()
        assert adapter.evaluate_condition("tests_passed", {"tests_passed": True}) is True
        assert adapter.evaluate_condition("tests_passed", {"tests_passed": False}) is False
