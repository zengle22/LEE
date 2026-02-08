"""Coverage verifier."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Any

from lee.orchestrator.verifiers.base import BaseVerifier, VerifyResult, VerifyStatus


class CoverageVerifier(BaseVerifier):
    @property
    def verifier_id(self) -> str:
        return "coverage"

    def verify(self, context: Dict) -> VerifyResult:
        config = context.get("config", {}) or {}
        min_coverage = config.get("min_coverage", 0)
        fail_on_error = config.get("fail_on_error", True)
        report_path = config.get("report_path")
        project_root = context.get("project_root", ".")

        if not report_path:
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message="coverage report_path not provided",
            )

        report_file = Path(project_root) / report_path
        if not report_file.exists():
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message=f"coverage report not found: {report_file}",
            )

        try:
            data = json.loads(report_file.read_text(encoding="utf-8"))
            coverage = self._extract_coverage(data)
            if coverage is None:
                raise ValueError("coverage not found in report")

            if coverage < float(min_coverage):
                return VerifyResult(
                    status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                    verifier_id=self.verifier_id,
                    message=f"coverage {coverage} < {min_coverage}",
                    details={"coverage": coverage, "min_coverage": min_coverage},
                )

            return VerifyResult(
                status=VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message=f"coverage {coverage} >= {min_coverage}",
                details={"coverage": coverage},
            )
        except Exception as e:
            return VerifyResult(
                status=VerifyStatus.FAILED if fail_on_error else VerifyStatus.PASSED,
                verifier_id=self.verifier_id,
                message=f"coverage verification error: {e}",
            )

    def _extract_coverage(self, data: Dict[str, Any]) -> float | None:
        # Common formats
        if isinstance(data, dict):
            if "coverage" in data:
                return float(data["coverage"])
            if "total" in data and isinstance(data["total"], dict):
                total = data["total"]
                for key in ("percent", "coverage", "line_rate"):
                    if key in total:
                        return float(total[key])
            if "summary" in data and isinstance(data["summary"], dict):
                summary = data["summary"]
                for key in ("percent", "coverage", "line_rate"):
                    if key in summary:
                        return float(summary[key])
        return None
