"""
Schema Validator - JSON Schema 验证器

根据 JSON Schema 验证数据结构的正确性。
"""

import json
from pathlib import Path
from typing import Any, Dict, Optional, List

try:
    import jsonschema
    from jsonschema import validate as jsonschema_validate
    from jsonschema.exceptions import ValidationError as JSONSchemaValidationError
    JSONSCHEMA_AVAILABLE = True
except ImportError:
    JSONSCHEMA_AVAILABLE = False
    JSONSchemaValidationError = Exception
    jsonschema_validate = None

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
        schema = self._load_schema(config)
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

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={"schema_type": type(schema).__name__},
        )

    def _load_schema(self, config: Dict) -> Optional[Dict]:
        """
        加载 schema

        Args:
            config: 验证配置

        Returns:
            Schema 字典，如果加载失败返回 None
        """
        # 优先使用内联 schema
        if "schema" in config:
            return config["schema"]

        # 从文件加载
        schema_path = config.get("schema_path")
        if not schema_path:
            return None

        # 解析路径
        resolved_path = self._resolve_path(schema_path)
        path = Path(resolved_path)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            return None

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
                data = json.load(f)
            return self.validate(data, config)
        except json.JSONDecodeError as e:
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
