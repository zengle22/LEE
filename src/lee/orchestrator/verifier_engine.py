"""Verifier engine."""

from __future__ import annotations

from typing import Dict, List, Any

from lee.orchestrator.verifiers.base import VerifyResult, VerifyStatus
from lee.orchestrator.verifiers.lint import LintVerifier
from lee.orchestrator.verifiers.coverage import CoverageVerifier
from lee.orchestrator.verifiers.commit_format import CommitFormatVerifier
from lee.orchestrator.verifiers.evidence import EvidenceExistsVerifier, EvidenceReferenceVerifier
from lee.orchestrator.verifiers.behavior_compliance import BehaviorComplianceVerifier


class VerifierEngine:
    def __init__(self, project_root: str):
        self.project_root = project_root
        self._registry = {
            "lint": LintVerifier,
            "coverage": CoverageVerifier,
            "commit_format": CommitFormatVerifier,
            # QA 测试执行相关验证器
            "evidence_exists": EvidenceExistsVerifier,
            "evidence_reference": EvidenceReferenceVerifier,
            "behavior_compliance": BehaviorComplianceVerifier,
        }

    def run(self, verifiers: List[Dict[str, Any]], context: Dict[str, Any]) -> List[VerifyResult]:
        results: List[VerifyResult] = []
        for item in verifiers or []:
            vtype = item.get("type")
            vconfig = item.get("config", {}) or {}
            verifier_cls = self._registry.get(vtype)
            if not verifier_cls:
                results.append(VerifyResult(
                    status=VerifyStatus.FAILED,
                    verifier_id=vtype or "unknown",
                    message=f"Unknown verifier type: {vtype}",
                ))
                continue

            verifier = verifier_cls()
            result = verifier.verify({
                **context,
                "project_root": self.project_root,
                "config": vconfig,
            })
            results.append(result)

        return results

    @staticmethod
    def all_passed(results: List[VerifyResult]) -> bool:
        return all(r.status == VerifyStatus.PASSED for r in results)
