"""
Schema Validator - JSON Schema 验证器

根据 JSON Schema 验证数据结构的正确性。
"""

import json
import re
import copy
from pathlib import Path
from typing import Any, Dict, Optional, List, Tuple
import yaml

try:
    import jsonschema
    from jsonschema import validate as jsonschema_validate
    from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
    from jsonschema.validators import (
        Draft4Validator,
        Draft6Validator,
        Draft7Validator,
        Draft201909Validator,
        Draft202012Validator,
        validator_for,
    )
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT4, DRAFT6, DRAFT7, DRAFT201909, DRAFT202012
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    JSONSchemaValidationError = Exception
    jsonschema_validate = None
    Registry = None
    Resource = None
    Draft4Validator = None
    Draft6Validator = None
    Draft7Validator = None
    Draft201909Validator = None
    Draft202012Validator = None
    DRAFT4 = None
    DRAFT6 = None
    DRAFT7 = None
    DRAFT201909 = None
    DRAFT202012 = None

from .base import (
    Validator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidatorRegistry,
)


class SchemaValidator(Validator):
    """
    JSON Schema 验证器

    验证数据是否符合指定的 JSON Schema。

    配置格式:
        validators:
          - type: schema
            schema_path: schemas/output.schema.json
            # 或直接内联 schema
            schema:
              type: object
              properties:
                name:
                  type: string
                version:
                  type: string
    """

    validator_type = "schema"
    validator_name = "schema_validator"

    _SUPPORTED_RULES = {
        "must_have_test_focus",
        "p0_must_have_positive",
        "single_feat_trace_required",
        "ac_coverage_required",
    }

    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """
        执行验证

        Args:
            data: 待验证的数据（可以是 JSON 字符串或已解析的对象）
            config: 验证配置，包含 schema_path 或 schema

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # 检查依赖
        if not JSONSCHEMA_AVAILABLE:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="DEPENDENCY_MISSING",
                        message="jsonschema library not installed. Install with: pip install jsonschema",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 解析数据
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError as e:
                try:
                    data = yaml.safe_load(data)
                except yaml.YAMLError:
                    return ValidationResult(
                        passed=False,
                        validator=self.validator_name,
                        errors=[
                            ValidationError(
                                code="INVALID_JSON",
                                message=f"Invalid JSON: {e}",
                                severity=ValidationSeverity.ERROR,
                            )
                        ],
                    )

        # 加载 schema
        schema, validation_rules, schema_base_uri, schema_store = self._load_schema_with_rules(config)
        if schema is None:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="SCHEMA_MISSING",
                        message="Schema not found in config. Provide 'schema_path' or 'schema'.",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 执行验证
        try:
            if schema_base_uri:
                schema_for_validation = schema
                if isinstance(schema, dict) and "$id" not in schema:
                    schema_for_validation = copy.deepcopy(schema)
                    schema_for_validation["$id"] = schema_base_uri
                validator_cls = validator_for(schema_for_validation)
                validator_kwargs = {}
                if Registry is not None and Resource is not None:
                    validator_kwargs["registry"] = self._build_schema_registry(schema_store)
                validator = validator_cls(schema_for_validation, **validator_kwargs)
                validator.validate(data)
            else:
                jsonschema_validate(instance=data, schema=schema)
        except JSONSchemaValidationError as e:
            # 转换为 ValidationError
            path = "$." + ".".join(str(p) for p in e.path) if e.path else "$"
            errors.append(
                ValidationError(
                    code="SCHEMA_VALIDATION_FAILED",
                    message=e.message,
                    path=path,
                    severity=ValidationSeverity.ERROR,
                    details={
                        "validator": e.validator,
                        "failed_value": e.instance,
                    },
                )
            )
        except Exception as e:
            errors.append(
                ValidationError(
                    code="VALIDATION_ERROR",
                    message=f"Unexpected error during validation: {e}",
                    severity=ValidationSeverity.ERROR,
                )
            )

        if not errors and validation_rules:
            errors.extend(self._evaluate_validation_rules(data, validation_rules))

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={
                "schema_type": type(schema).__name__,
                "validation_rule_count": len(validation_rules),
            },
        )

    def _load_schema(self, config: Dict) -> Optional[Dict]:
        schema, _, _, _ = self._load_schema_with_rules(config)
        return schema

    def _load_schema_with_rules(
        self,
        config: Dict,
    ) -> Tuple[Optional[Dict], List[Dict[str, Any]], Optional[str], Dict[str, Dict[str, Any]]]:
        """
        加载 schema 和附加 validation_rules

        Args:
            config: 验证配置

        Returns:
            (schema, validation_rules) 元组
        """
        # 优先使用内联 schema
        if "schema" in config:
            return config["schema"], config.get("validation_rules", []), None, {}

        # 从文件加载
        schema_path = config.get("schema_path")
        if not schema_path:
            return None, [], None, {}

        # 解析路径
        resolved_path = self._resolve_path(schema_path)
        path = Path(resolved_path)

        if not path.exists() and not Path(schema_path).is_absolute():
            base = Path(self.project_dir or Path.cwd())
            spec_global_candidate = (base / "spec-global" / schema_path).resolve()
            if spec_global_candidate.exists():
                path = spec_global_candidate

        if not path.exists():
            return None, [], None, {}

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() in {".yaml", ".yml"}:
                    loaded = yaml.safe_load(f)
                else:
                    loaded = json.load(f)
        except (json.JSONDecodeError, yaml.YAMLError, IOError):
            return None, [], None, {}

        schema_base_uri = path.resolve().as_uri()
        schema_store = self._build_schema_store(path, loaded)

        if isinstance(loaded, dict) and isinstance(loaded.get("schema"), dict):
            wrapped_schema = loaded["schema"]
            wrapped_store = self._build_schema_store(path, wrapped_schema)
            return wrapped_schema, loaded.get("validation_rules", []), schema_base_uri, wrapped_store

        if isinstance(loaded, dict):
            return loaded, [], schema_base_uri, schema_store

        return None, [], None, {}

    def _build_schema_store(self, path: Path, schema: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
        store: Dict[str, Dict[str, Any]] = {}
        visited: set[Path] = set()

        def load_into_store(schema_path: Path, schema_obj: Dict[str, Any]) -> None:
            resolved_path = schema_path.resolve()
            if resolved_path in visited:
                return
            visited.add(resolved_path)

            file_uri = resolved_path.as_uri()
            store[file_uri] = schema_obj
            schema_id = schema_obj.get("$id") if isinstance(schema_obj, dict) else None
            if isinstance(schema_id, str) and schema_id.strip():
                store[schema_id] = schema_obj

            for ref in self._collect_schema_refs(schema_obj):
                if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", ref):
                    continue
                target_path = (resolved_path.parent / ref).resolve()
                if not target_path.exists():
                    continue
                try:
                    with open(target_path, "r", encoding="utf-8") as f:
                        target_schema = yaml.safe_load(f) if target_path.suffix.lower() in {".yaml", ".yml"} else json.load(f)
                except (json.JSONDecodeError, yaml.YAMLError, IOError):
                    continue
                if isinstance(target_schema, dict) and isinstance(target_schema.get("schema"), dict):
                    target_schema = target_schema["schema"]
                if isinstance(target_schema, dict):
                    load_into_store(target_path, target_schema)

        load_into_store(path, schema)
        return store

    @staticmethod
    def _build_schema_registry(schema_store: Dict[str, Dict[str, Any]]) -> "Registry":
        registry = Registry()
        for uri, schema_obj in schema_store.items():
            if not isinstance(uri, str) or not uri.strip():
                continue
            if not isinstance(schema_obj, dict):
                continue
            validator_cls = validator_for(schema_obj)
            specification = SchemaValidator._specification_for_validator(validator_cls)
            if specification is None:
                registry = registry.with_resource(uri, Resource.from_contents(schema_obj))
            else:
                registry = registry.with_resource(uri, Resource(contents=schema_obj, specification=specification))
        return registry

    @staticmethod
    def _specification_for_validator(validator_cls: Any) -> Any:
        mapping = {
            Draft202012Validator: DRAFT202012,
            Draft201909Validator: DRAFT201909,
            Draft7Validator: DRAFT7,
            Draft6Validator: DRAFT6,
            Draft4Validator: DRAFT4,
        }
        return mapping.get(validator_cls)

    @staticmethod
    def _collect_schema_refs(schema: Any) -> List[str]:
        refs: List[str] = []
        if isinstance(schema, dict):
            for key, value in schema.items():
                if key == "$ref" and isinstance(value, str):
                    refs.append(value)
                else:
                    refs.extend(SchemaValidator._collect_schema_refs(value))
        elif isinstance(schema, list):
            for item in schema:
                refs.extend(SchemaValidator._collect_schema_refs(item))
        return refs

    def _evaluate_validation_rules(
        self,
        data: Any,
        validation_rules: List[Dict[str, Any]],
    ) -> List[ValidationError]:
        errors: List[ValidationError] = []
        if not isinstance(data, dict):
            return errors

        for rule in validation_rules:
            rule_id = rule.get("rule")
            if rule_id not in self._SUPPORTED_RULES:
                continue

            passed = True
            details: Dict[str, Any] = {}

            if rule_id == "must_have_test_focus":
                test_focus = data.get("test_focus") or {}
                focus_keys = ("positive", "negative", "boundary", "exception")
                passed = any(bool(test_focus.get(key)) for key in focus_keys)
                details["checked_keys"] = list(focus_keys)

            elif rule_id == "p0_must_have_positive":
                priority = ((data.get("strategy") or {}).get("priority"))
                if priority == "P0":
                    positive = ((data.get("test_focus") or {}).get("positive")) or []
                    passed = len(positive) > 0
                    details["priority"] = priority

            elif rule_id == "single_feat_trace_required":
                feature_ids = ((data.get("traceability") or {}).get("feature_ids")) or []
                passed = len(feature_ids) == 1
                details["feature_ids"] = feature_ids

            elif rule_id == "ac_coverage_required":
                ac_refs = ((data.get("traceability") or {}).get("acceptance_criteria_refs")) or []
                passed = len(ac_refs) > 0
                details["acceptance_criteria_refs"] = ac_refs

            if not passed:
                errors.append(
                    ValidationError(
                        code=f"RULE_{rule_id.upper()}",
                        message=rule.get("error_message", f"Validation rule failed: {rule_id}"),
                        severity=ValidationSeverity.ERROR,
                        details=details,
                    )
                )

        return errors

    def validate_file(self, file_path: str, config: Dict) -> ValidationResult:
        """
        验证文件

        Args:
            file_path: 文件路径
            config: 验证配置

        Returns:
            ValidationResult
        """
        from pathlib import Path

        path = Path(file_path)
        if not path.is_absolute() and self.project_dir:
            path = Path(self.project_dir) / path

        if not path.exists():
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="FILE_NOT_FOUND",
                        message=f"File not found: {file_path}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix.lower() in {".yaml", ".yml"}:
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)
            return self.validate(data, config)
        except (json.JSONDecodeError, yaml.YAMLError) as e:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="INVALID_JSON",
                        message=f"Invalid JSON in file: {e}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )
        except Exception as e:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="FILE_READ_ERROR",
                        message=f"Failed to read file: {e}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )


# 注册验证器
ValidatorRegistry.register(SchemaValidator)
