"""
LEE Orchestrator - Gate Engine

门禁规则引擎，负责评估门禁条件并做出通过/警告/失败判定。

核心功能：
1. 门禁规则评估：评估各类规则（mandatory, threshold, risk_acceptance）
2. 规则表达式解析：解析和评估规则表达式
3. 门禁判定：综合评估结果，给出 PASS/WARNING/FAIL 判定
4. 豁免策略：处理豁免请求
5. 签字要求：管理签字审批
"""

import json
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

from lee.orchestrator.ir.models import (
    GateIR,
    GateRuleIR,
    RuleType,
    RuleSeverity,
    ExemptionPolicyIR,
    SignoffRequirementIR,
)


class GateVerdict(Enum):
    """门禁判定结果"""

    PASS = "pass"  # 通过
    WARNING = "warning"  # 警告（可继续但需关注）
    FAIL = "fail"  # 失败（阻塞）
    EXEMPTED = "exempted"  # 豁免

    def __str__(self):
        return self.value


class RuleEvaluationResult:
    """规则评估结果"""

    def __init__(
        self,
        rule_id: str,
        rule_name: str,
        rule_type: RuleType,
        passed: bool,
        actual_value: Optional[Any] = None,
        expected_value: Optional[Any] = None,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.rule_id = rule_id
        self.rule_name = rule_name
        self.rule_type = rule_type
        self.passed = passed
        self.actual_value = actual_value
        self.expected_value = expected_value
        self.error_message = error_message
        self.metadata = metadata or {}
        self.evaluated_at = datetime.now()

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "rule_type": str(self.rule_type),
            "passed": self.passed,
            "actual_value": str(self.actual_value) if self.actual_value is not None else None,
            "expected_value": str(self.expected_value) if self.expected_value is not None else None,
            "error_message": self.error_message,
            "metadata": self.metadata,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class GateEvaluationResult:
    """门禁评估结果"""

    def __init__(
        self,
        gate_id: str,
        gate_name: str,
        verdict: GateVerdict,
        rule_results: List[RuleEvaluationResult],
        exemptions: Optional[List[str]] = None,
        signoffs: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.gate_id = gate_id
        self.gate_name = gate_name
        self.verdict = verdict
        self.rule_results = rule_results
        self.exemptions = exemptions or []
        self.signoffs = signoffs or []
        self.metadata = metadata or {}
        self.evaluated_at = datetime.now()

    @property
    def mandatory_passed(self) -> bool:
        """所有 mandatory 规则是否通过"""
        mandatory_results = [r for r in self.rule_results if r.rule_type == RuleType.MANDATORY]
        return all(r.passed for r in mandatory_results)

    @property
    def threshold_score(self) -> Optional[float]:
        """threshold 规则得分"""
        threshold_results = [r for r in self.rule_results if r.rule_type == RuleType.THRESHOLD]
        if not threshold_results:
            return None
        passed = sum(1 for r in threshold_results if r.passed)
        return passed / len(threshold_results)

    @property
    def failed_rules(self) -> List[str]:
        """失败的规则列表"""
        return [r.rule_id for r in self.rule_results if not r.passed]

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "gate_id": self.gate_id,
            "gate_name": self.gate_name,
            "verdict": str(self.verdict),
            "mandatory_passed": self.mandatory_passed,
            "threshold_score": self.threshold_score,
            "failed_rules": self.failed_rules,
            "exemptions": self.exemptions,
            "signoffs": self.signoffs,
            "rule_results": [r.to_dict() for r in self.rule_results],
            "metadata": self.metadata,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class GateEngine:
    """
    门禁规则引擎

    职责：
    1. 解析规则表达式
    2. 评估规则条件
    3. 综合门禁判定
    4. 处理豁免请求
    5. 管理签字要求
    """

    def __init__(self):
        """初始化门禁引擎"""
        # 上下文变量（用于规则评估）
        self.context: Dict[str, Any] = {}

        # 规则评估器注册
        self._evaluators: Dict[str, callable] = {
            # 默认评估器
            "default": self._evaluate_default,
            # 数值比较
            "numeric_compare": self._evaluate_numeric_compare,
            # 百分比
            "percentage": self._evaluate_percentage,
            # 布尔值
            "boolean": self._evaluate_boolean,
            # 列表包含
            "list_contains": self._evaluate_list_contains,
            # 文件存在
            "file_exists": self._evaluate_file_exists,
            # 架构一致性
            "architecture_consistency": self._evaluate_architecture_consistency,
        }

    # ========================================================================
    # 门禁评估
    # ========================================================================

    def evaluate_gate(
        self,
        gate: GateIR,
        context: Optional[Dict[str, Any]] = None,
        exemptions: Optional[List[str]] = None,
        signoffs: Optional[List[Dict[str, Any]]] = None,
    ) -> GateEvaluationResult:
        """
        评估门禁

        Args:
            gate: 门禁 IR
            context: 评估上下文
            exemptions: 申请豁免的规则 ID 列表
            signoffs: 签字记录

        Returns:
            门禁评估结果
        """
        if context:
            self.context.update(context)

        exemptions = exemptions or []
        signoffs = signoffs or []

        # 评估所有规则
        rule_results = []

        # 评估 mandatory 规则
        for rule in gate.mandatory_criteria:
            # 检查是否豁免
            if self._is_exempt(rule, gate.exemption_policy, exemptions):
                continue
            result = self._evaluate_rule(rule, context)
            rule_results.append(result)

        # 评估 threshold 规则
        for rule in gate.threshold_criteria:
            if self._is_exempt(rule, gate.exemption_policy, exemptions):
                continue
            result = self._evaluate_rule(rule, context)
            rule_results.append(result)

        # 评估 risk_acceptance 规则
        for rule in gate.risk_acceptance_criteria:
            if self._is_exempt(rule, gate.exemption_policy, exemptions):
                continue
            result = self._evaluate_rule(rule, context)
            rule_results.append(result)

        # 判定门禁结果
        verdict = self._determine_verdict(gate, rule_results, exemptions, signoffs)

        return GateEvaluationResult(
            gate_id=gate.gate_id,
            gate_name=gate.name,
            verdict=verdict,
            rule_results=rule_results,
            exemptions=exemptions,
            signoffs=signoffs,
        )

    # ========================================================================
    # 规则评估
    # ========================================================================

    def _evaluate_rule(
        self,
        rule: GateRuleIR,
        context: Optional[Dict[str, Any]] = None,
    ) -> RuleEvaluationResult:
        """
        评估单个规则

        Args:
            rule: 规则 IR
            context: 评估上下文

        Returns:
            规则评估结果
        """
        if context is None:
            context = self.context

        try:
            # 获取评估方法
            validation_method = rule.validation_method or "default"
            evaluator = self._evaluators.get(validation_method, self._evaluators["default"])

            # 执行评估
            passed, actual_value, expected_value, error_message = evaluator(
                rule.rule_expression,
                context,
            )

            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                passed=passed,
                actual_value=actual_value,
                expected_value=expected_value,
                error_message=error_message,
            )

        except Exception as e:
            return RuleEvaluationResult(
                rule_id=rule.rule_id,
                rule_name=rule.name,
                rule_type=rule.rule_type,
                passed=False,
                error_message=f"Evaluation error: {str(e)}",
            )

    # ========================================================================
    # 评估器实现
    # ========================================================================

    def _evaluate_default(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """默认评估器"""
        # 简单实现：检查上下文中是否有该键且值为 True
        if expression in context:
            value = context[expression]
            if isinstance(value, bool):
                return value, value, True, None
            return bool(value), value, True, None
        return False, None, True, f"Key '{expression}' not found in context"

    def _evaluate_numeric_compare(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """数值比较评估器"""
        # 表达式格式: "key >= value" 或 "key <= value"
        try:
            if ">=" in expression:
                key, value = expression.split(">=", 1)
                key = key.strip()
                value = float(value.strip())
                actual = context.get(key, 0)
                return actual >= value, actual, value, None
            elif "<=" in expression:
                key, value = expression.split("<=", 1)
                key = key.strip()
                value = float(value.strip())
                actual = context.get(key, 0)
                return actual <= value, actual, value, None
            elif ">" in expression:
                key, value = expression.split(">", 1)
                key = key.strip()
                value = float(value.strip())
                actual = context.get(key, 0)
                return actual > value, actual, value, None
            elif "<" in expression:
                key, value = expression.split("<", 1)
                key = key.strip()
                value = float(value.strip())
                actual = context.get(key, 0)
                return actual < value, actual, value, None
        except (ValueError, TypeError):
            return False, None, None, f"Invalid numeric expression: {expression}"
        return False, None, None, f"Invalid numeric expression: {expression}"

    def _evaluate_percentage(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """百分比评估器"""
        # 表达式格式: "key >= 80" （百分比）
        passed, actual, expected, error = self._evaluate_numeric_compare(expression, context)
        if actual is not None:
            actual = f"{actual}%"
        if expected is not None:
            expected = f"{expected}%"
        return passed, actual, expected, error

    def _evaluate_boolean(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """布尔值评估器"""
        value = context.get(expression, False)
        if isinstance(value, str):
            value = value.lower() in ("true", "yes", "1", "on")
        return bool(value), value, True, None

    def _evaluate_list_contains(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """列表包含评估器"""
        # 表达式格式: "key contains value"
        if " contains " in expression:
            key, value = expression.split(" contains ", 1)
            key = key.strip()
            value = value.strip()
            lst = context.get(key, [])
            passed = value in lst
            return passed, lst, value, None
        return False, None, None, f"Invalid list expression: {expression}"

    def _evaluate_file_exists(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """文件存在评估器"""
        from pathlib import Path

        path = Path(expression)
        exists = path.exists()
        return exists, str(path), "exists", None

    def _evaluate_architecture_consistency(
        self,
        expression: str,
        context: Dict[str, Any],
    ) -> tuple[bool, Any, Any, Optional[str]]:
        """架构一致性评估器"""
        # 从上下文获取一致性矩阵
        consistency_matrix = context.get("consistency_matrix", {})

        # 检查是否有冲突
        conflicts = consistency_matrix.get("conflicts", [])
        passed = len(conflicts) == 0

        return passed, len(conflicts), 0, f"Found {len(conflicts)} conflicts" if conflicts else None

    # ========================================================================
    # 判定逻辑
    # ========================================================================

    def _determine_verdict(
        self,
        gate: GateIR,
        rule_results: List[RuleEvaluationResult],
        exemptions: List[str],
        signoffs: List[Dict[str, Any]],
    ) -> GateVerdict:
        """判定门禁结果"""
        # 检查豁免情况
        if exemptions:
            # 验证豁免是否合法
            if self._validate_exemptions(gate, exemptions, signoffs):
                return GateVerdict.EXEMPTED

        # 检查 mandatory 规则
        mandatory_results = [r for r in rule_results if r.rule_type == RuleType.MANDATORY]
        mandatory_failed = [r for r in mandatory_results if not r.passed]

        if mandatory_failed:
            return GateVerdict.FAIL

        # 检查 threshold 规则
        threshold_results = [r for r in rule_results if r.rule_type == RuleType.THRESHOLD]
        if threshold_results:
            passed = sum(1 for r in threshold_results if r.passed)
            score = passed / len(threshold_results)

            # 阈值规则低于 60% 给 WARNING
            if score < 0.6:
                return GateVerdict.WARNING

        # 所有规则通过
        return GateVerdict.PASS

    def _is_exempt(
        self,
        rule: GateRuleIR,
        exemption_policy: Optional,
        exemptions: List[str],
    ) -> bool:
        """检查规则是否被豁免"""
        if not rule.exemption_allowed:
            return False
        return rule.rule_id in exemptions

    def _validate_exemptions(
        self,
        gate: GateIR,
        exemptions: List[str],
        signoffs: List[Dict[str, Any]],
    ) -> bool:
        """验证豁免是否合法"""
        if not gate.exemption_policy:
            return False

        # 检查禁止豁免的规则
        forbidden = gate.exemption_policy.forbidden_exemptions or []
        for exempt in exemptions:
            if exempt in forbidden:
                return False

        # 检查最大豁免数
        max_exemptions = gate.exemption_policy.max_exemptions or 0
        if len(exemptions) > max_exemptions:
            return False

        # 检查是否需要审批
        required_approvers = gate.exemption_policy.requires_approval or []
        if required_approvers:
            # 验证签字
            approvers = [s.get("approver") for s in signoffs]
            for required in required_approvers:
                if required not in approvers:
                    return False

        return True
