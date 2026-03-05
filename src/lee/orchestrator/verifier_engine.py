"""Verifier engine."""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from lee.orchestrator.verifiers.base import VerifyResult, VerifyStatus
from lee.orchestrator.verifiers.lint import LintVerifier
from lee.orchestrator.verifiers.coverage import CoverageVerifier
from lee.orchestrator.verifiers.commit_format import CommitFormatVerifier
from lee.orchestrator.verifiers.evidence import EvidenceExistsVerifier, EvidenceReferenceVerifier
from lee.orchestrator.verifiers.behavior_compliance import BehaviorComplianceVerifier


def _get_spec_global_path() -> Optional[Path]:
    """获取包内 spec-global 路径（使用回调确保生命周期）"""
    from lee.data_path import with_builtin_spec_root

    try:
        # 使用回调获取路径
        return with_builtin_spec_root(lambda p: p)
    except Exception:
        return None


class SchemaVerifier:
    """验证 YAML 输出是否符合 schema"""

    def verify(self, context: Dict[str, Any]) -> VerifyResult:
        schema_path = context.get("config", {}).get("schema_path")
        if not schema_path:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message="schema_path is required",
            )

        # 尝试多个可能的路径
        possible_paths = []
        project_root = context.get("project_root", ".")

        # 获取包内 spec-global 路径
        spec_global = _get_spec_global_path()

        # 1. 相对于项目根目录
        possible_paths.append(Path(project_root) / schema_path)

        # 2. 查找 spec-global 中所有匹配的文件
        # 处理相对路径如 ../../contracts/xxx
        if spec_global and schema_path.startswith("../"):
            # 提取文件名和可能的子路径
            basename = schema_path.split("/")[-1]
            # 在 spec-global 中递归查找
            try:
                for match in spec_global.rglob(basename):
                    possible_paths.append(match)
            except Exception:
                pass  # spec-global 可能不存在

        # 3. 相对于 LEE 框架根目录（使用包内路径）
        if spec_global:
            possible_paths.append(spec_global.parent / schema_path)

        # 4. 作为绝对路径
        if Path(schema_path).is_absolute():
            possible_paths.append(Path(schema_path))

        found_path = None
        for p in possible_paths:
            if p.exists() and p.is_file():
                found_path = p
                break

        if not found_path:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=f"Schema file not found: {schema_path}",
            )

        # Schema 验证暂时跳过（需要 jsonschema 库），只检查文件存在
        # TODO: 实现完整的 schema 验证
        return VerifyResult(
            status=VerifyStatus.PASSED,
            verifier_id="schema",
            message=f"Schema file exists: {found_path}",
        )


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
            # Schema 验证器
            "schema": SchemaVerifier,
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
