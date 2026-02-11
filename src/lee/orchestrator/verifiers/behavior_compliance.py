"""Behavior Compliance Verifier - AI 行为合规验证器

检查 AI 在测试执行过程中是否有违规行为：
- 使用 mock/模拟
- 捏造网络错误
- 工具缺失借口（未经 Orchestrator 确认）
"""

from __future__ import annotations

import re
from typing import Dict, List, Set

from lee.orchestrator.verifiers.base import BaseVerifier, VerifyResult, VerifyStatus


class BehaviorComplianceVerifier(BaseVerifier):
    """
    AI 行为合规验证器

    先约束 AI 行为，再评价产品质量。
    违规 → 本轮测试无效。
    """

    # 禁止的 mock 关键词
    MOCK_PATTERNS = [
        r"\bmock\b",
        r"模拟",
        r"假设返回",
        r"假定接口返回",
        r"\bsimulate\b",
        r"\bstub\b",
        r"假装",
        r"跳过执行",
        r"省略执行",
    ]

    # 合法的 runtime_error 来源
    VALID_ERROR_SOURCES = {"runner_cli", "orchestrator", "human_marked"}

    @property
    def verifier_id(self) -> str:
        return "behavior_compliance"

    def verify(self, context: Dict) -> VerifyResult:
        config = context.get("config", {})
        runner_output = context.get("runner_output", {})
        confirmed_env_errors = context.get("confirmed_env_errors", [])

        violations: List[Dict] = []

        case_results = runner_output.get("case_results", [])
        for case in case_results:
            case_id = case.get("case_id", "unknown")
            case_violations = self._check_case(case, confirmed_env_errors, config)
            for v in case_violations:
                v["case_id"] = case_id
                violations.append(v)

        if violations:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id=self.verifier_id,
                message=f"AI behavior violations detected: {len(violations)} issues",
                details={
                    "violations": violations,
                    "action": "mark_invalid_run",
                },
            )

        return VerifyResult(
            status=VerifyStatus.PASSED,
            verifier_id=self.verifier_id,
            message="AI behavior compliant",
        )

    def _check_case(
        self,
        case: Dict,
        confirmed_env_errors: List[str],
        config: Dict,
    ) -> List[Dict]:
        """检查单个用例的合规性"""
        violations = []

        # 1. 检查 mock 关键词
        result_text = case.get("result_text", "")
        allow_mock = case.get("meta", {}).get("allow_mock", False)

        if not allow_mock:
            for pattern in self.MOCK_PATTERNS:
                if re.search(pattern, result_text, re.IGNORECASE):
                    violations.append({
                        "rule_id": "no_mock_without_flag",
                        "severity": "critical",
                        "message": f"Found mock pattern: {pattern}",
                        "text_snippet": result_text[:200],
                    })
                    break  # 只报告第一个匹配

        # 2. 检查网络错误声明
        claimed_network_error = case.get("claimed_network_error", False)
        if claimed_network_error:
            runtime_errors = case.get("runtime_errors", {})
            source = runtime_errors.get("source")

            if source not in self.VALID_ERROR_SOURCES:
                # 检查是否在 confirmed_env_errors 中
                if "network" not in str(confirmed_env_errors).lower():
                    violations.append({
                        "rule_id": "no_network_error_without_runtime_error",
                        "severity": "critical",
                        "message": "Claimed network error without valid source",
                        "claimed_source": source,
                        "valid_sources": list(self.VALID_ERROR_SOURCES),
                    })

        # 3. 检查工具缺失声明
        claimed_tool_missing = case.get("claimed_tool_missing", False)
        if claimed_tool_missing:
            missing_tool = case.get("missing_tool", "")
            if missing_tool not in str(confirmed_env_errors):
                violations.append({
                    "rule_id": "no_tool_missing_without_check",
                    "severity": "critical",
                    "message": f"Claimed tool missing without Orchestrator confirmation: {missing_tool}",
                    "missing_tool": missing_tool,
                    "confirmed_errors": confirmed_env_errors,
                })

        # 4. 检查 P0/P1 用例是否有证据
        priority = case.get("priority", "")
        if priority in ("P0", "P1"):
            evidence_bundle = case.get("evidence_bundle")
            if not evidence_bundle:
                violations.append({
                    "rule_id": "evidence_required_for_p0_p1",
                    "severity": "critical",
                    "message": f"P0/P1 case missing evidence_bundle",
                    "priority": priority,
                })

        # 5. 检查无证据的 pass 结论
        status = case.get("status", "")
        if status == "pass":
            evidence_bundle = case.get("evidence_bundle", {})
            evidence_exempt = case.get("meta", {}).get("evidence_exempt", False)

            if not evidence_exempt:
                logs = evidence_bundle.get("logs")
                screenshots = evidence_bundle.get("screenshots", [])

                if not logs and not screenshots:
                    violations.append({
                        "rule_id": "no_fabricated_pass",
                        "severity": "high",
                        "message": "Pass conclusion without evidence",
                    })

        return violations
