"""Evidence Verifiers - 证据验证器

验证测试执行的证据是否存在且有效。
"""

from __future__ import annotations

import glob
from pathlib import Path
from typing import Dict, List

from lee.orchestrator.verifiers.base import BaseVerifier, VerifyResult, VerifyStatus


class EvidenceExistsVerifier(BaseVerifier):
    """
    证据存在验证器

    检查 evidence_bundle 中引用的文件是否真实存在。
    没有证据 = 没有执行 = invalid_run
    """

    @property
    def verifier_id(self) -> str:
        return "evidence_exists"

    def verify(self, context: Dict) -> VerifyResult:
        config = context.get("config", {})
        project_root = Path(context.get("project_root", "."))

        evidence_dir = config.get("evidence_dir")
        if not evidence_dir:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id=self.verifier_id,
                message="evidence_dir not configured",
            )

        evidence_path = project_root / evidence_dir
        if not evidence_path.exists():
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id=self.verifier_id,
                message=f"Evidence directory not found: {evidence_dir}",
                details={"error_status": config.get("error_status", "invalid_run")},
            )

        # 检查必需文件
        required_files = config.get("required_files", [])
        missing = []

        for req in required_files:
            pattern = req.get("pattern")
            description = req.get("description", pattern)
            optional_if = req.get("optional_if")

            # 检查是否满足可选条件
            if optional_if:
                # 简单的条件评估（可扩展）
                if self._eval_condition(optional_if, context):
                    continue

            # 检查文件是否存在
            matches = list(evidence_path.glob(pattern))
            if not matches:
                missing.append(description)

        if missing:
            fail_on_missing = config.get("fail_on_missing", True)
            status = VerifyStatus.FAILED if fail_on_missing else VerifyStatus.PASSED
            return VerifyResult(
                status=status,
                verifier_id=self.verifier_id,
                message=f"Missing evidence files: {', '.join(missing)}",
                details={
                    "missing": missing,
                    "evidence_dir": str(evidence_path),
                    "error_status": config.get("error_status", "invalid_run"),
                },
            )

        return VerifyResult(
            status=VerifyStatus.PASSED,
            verifier_id=self.verifier_id,
            message="All required evidence files exist",
            details={"evidence_dir": str(evidence_path)},
        )

    def _eval_condition(self, condition: str, context: Dict) -> bool:
        """简单条件评估"""
        # 支持格式: "case.meta.headless == true"
        try:
            parts = condition.split("==")
            if len(parts) == 2:
                key_path = parts[0].strip()
                expected = parts[1].strip().lower() == "true"
                actual = self._get_nested(context, key_path)
                return actual == expected
        except Exception:
            pass
        return False

    def _get_nested(self, d: Dict, path: str):
        """获取嵌套字典值"""
        keys = path.split(".")
        for k in keys:
            if isinstance(d, dict):
                d = d.get(k)
            else:
                return None
        return d


class EvidenceReferenceVerifier(BaseVerifier):
    """
    证据引用验证器

    检查每个用例结果是否正确引用了 evidence_bundle。
    防止 AI 伪造无证据的结论。
    """

    @property
    def verifier_id(self) -> str:
        return "evidence_reference"

    def verify(self, context: Dict) -> VerifyResult:
        config = context.get("config", {})
        execution_results = context.get("execution_results", {})

        cases = execution_results.get("cases", [])
        if not cases:
            return VerifyResult(
                status=VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message="No cases to verify",
            )

        missing_refs = []
        for case in cases:
            case_id = case.get("case_id", "unknown")
            evidence_bundle = case.get("evidence_bundle")

            if not evidence_bundle:
                missing_refs.append(case_id)
                continue

            # 检查 evidence_bundle 必填字段
            if not evidence_bundle.get("logs"):
                missing_refs.append(f"{case_id} (missing logs)")
            if not evidence_bundle.get("runner_result_ref"):
                missing_refs.append(f"{case_id} (missing runner_result_ref)")

        if missing_refs:
            fail_on_error = config.get("fail_on_error", True)
            status = VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED
            return VerifyResult(
                status=status,
                verifier_id=self.verifier_id,
                message=f"Cases missing evidence_bundle: {', '.join(missing_refs)}",
                details={"missing_cases": missing_refs},
            )

        return VerifyResult(
            status=VerifyStatus.PASSED,
            verifier_id=self.verifier_id,
            message="All cases have valid evidence_bundle references",
        )
