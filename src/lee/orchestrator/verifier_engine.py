"""Verifier engine."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
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
        config = context.get("config", {}) or {}
        schema_path = config.get("schema_path")
        if not schema_path:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message="schema_path is required",
            )

        schema_file = self._resolve_schema_path(schema_path, context.get("project_root", "."))
        if not schema_file:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=f"Schema file not found: {schema_path}",
            )

        try:
            import jsonschema
            from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
        except ImportError:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message="jsonschema dependency is required for schema verifier",
            )

        payload, payload_desc = self._resolve_payload(config, context.get("project_root", "."))
        if payload_desc is None:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=(
                    "schema verifier needs one of config.file_path/config.output_path/"
                    "config.data to validate payload"
                ),
            )
        if isinstance(payload_desc, str) and payload_desc.startswith("payload file not found:"):
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=payload_desc,
            )
        if isinstance(payload_desc, str) and payload_desc.startswith("failed to load payload file"):
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=payload_desc,
            )
        if payload is None:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message="Resolved schema payload is empty",
            )

        try:
            raw_schema = self._load_data_file(schema_file)
        except Exception as exc:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=f"Failed to load schema file '{schema_file}': {exc}",
            )

        schema_doc = raw_schema.get("schema") if isinstance(raw_schema, dict) and isinstance(raw_schema.get("schema"), dict) else raw_schema
        if not isinstance(schema_doc, dict):
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=f"Invalid schema structure in '{schema_file}'",
            )

        try:
            jsonschema.validate(instance=payload, schema=schema_doc)
        except JSONSchemaValidationError as exc:
            path = ".".join(str(p) for p in exc.path) if exc.path else "$"
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=f"Schema validation failed at {path}: {exc.message}",
            )
        except Exception as exc:
            return VerifyResult(
                status=VerifyStatus.FAILED,
                verifier_id="schema",
                message=f"Schema validation error: {exc}",
            )

        return VerifyResult(
            status=VerifyStatus.PASSED,
            verifier_id="schema",
            message=f"Schema validation passed: {payload_desc} against {schema_file}",
        )

    @staticmethod
    def _load_data_file(path: Path) -> Any:
        with open(path, "r", encoding="utf-8") as f:
            if path.suffix.lower() == ".json":
                return json.load(f)
            return yaml.safe_load(f)

    def _resolve_schema_path(self, schema_path: str, project_root: str) -> Optional[Path]:
        possible_paths: List[Path] = []
        spec_global = _get_spec_global_path()
        project_root_path = Path(project_root)
        schema_ref = Path(schema_path)

        if schema_ref.is_absolute():
            possible_paths.append(schema_ref)
        else:
            possible_paths.append(project_root_path / schema_path)

            if spec_global:
                possible_paths.append(spec_global.parent / schema_path)

            if spec_global and schema_path.startswith("../"):
                basename = schema_path.split("/")[-1]
                try:
                    possible_paths.extend(spec_global.rglob(basename))
                except Exception:
                    pass

        for candidate in possible_paths:
            if candidate.exists() and candidate.is_file():
                return candidate
        return None

    def _resolve_payload(self, config: Dict[str, Any], project_root: str) -> Tuple[Any, Optional[str]]:
        if "data" in config:
            return config.get("data"), "inline config.data"

        payload_path = config.get("file_path") or config.get("output_path")
        if not payload_path:
            return None, None

        candidate = Path(payload_path)
        if not candidate.is_absolute():
            candidate = Path(project_root) / payload_path
        if not candidate.exists() or not candidate.is_file():
            return None, f"payload file not found: {candidate}"

        try:
            return self._load_data_file(candidate), str(candidate)
        except Exception as exc:
            return None, f"failed to load payload file '{candidate}': {exc}"


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
