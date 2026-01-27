"""
Contract Validator - 契约验证器

验证产物契约的完整性，包括输入/输出契约、数据契约等。
"""

import json
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    Validator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidatorRegistry,
)


class ContractValidator(Validator):
    """
    契约验证器

    验证步骤产出的契约是否符合定义。

    配置格式:
        validators:
          - type: contract
            contract_path: contracts/output_contract.yaml
            # 或直接定义契约
            contract:
              inputs:
                - name: requirements.txt
                  required: true
              outputs:
                - name: design.md
                  required: true
                  schema: design.schema.json
    """

    validator_type = "contract"
    validator_name = "contract_validator"

    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """
        执行验证

        Args:
            data: 待验证的数据（在此验证器中未使用）
            config: 验证配置

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # 加载契约
        contract = self._load_contract(config)
        if contract is None:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="CONTRACT_NOT_FOUND",
                        message="Contract not found in config",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 验证输入契约
        inputs = contract.get("inputs", [])
        if inputs:
            input_errors, input_warnings = self._validate_artifacts(inputs, "input")
            errors.extend(input_errors)
            warnings.extend(input_warnings)

        # 验证输出契约
        outputs = contract.get("outputs", [])
        if outputs:
            output_errors, output_warnings = self._validate_artifacts(outputs, "output")
            errors.extend(output_errors)
            warnings.extend(output_warnings)

        # 验证数据契约（如果有）
        data_contracts = contract.get("data_contracts", [])
        if data_contracts:
            dc_errors, dc_warnings = self._validate_data_contracts(data_contracts)
            errors.extend(dc_errors)
            warnings.extend(dc_warnings)

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={
                "contract_validated": True,
                "inputs_checked": len(inputs),
                "outputs_checked": len(outputs),
            },
        )

    def _load_contract(self, config: Dict) -> Optional[Dict]:
        """加载契约配置"""
        # 优先使用内联契约
        if "contract" in config:
            return config["contract"]

        # 从文件加载
        contract_path = config.get("contract_path")
        if not contract_path:
            return None

        resolved_path = self._resolve_path(contract_path)
        path = Path(resolved_path)

        if not path.exists():
            return None

        try:
            with open(path, "r", encoding="utf-8") as f:
                if path.suffix in [".yaml", ".yml"]:
                    return yaml.safe_load(f)
                elif path.suffix == ".json":
                    return json.load(f)
        except Exception:
            return None

    def _validate_artifacts(
        self, artifacts: List[Dict], artifact_type: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证产物列表"""
        errors = []
        warnings = []

        for artifact in artifacts:
            path = artifact.get("path", "")
            required = artifact.get("required", True)

            if not path:
                warnings.append(
                    ValidationError(
                        code="ARTIFACT_NO_PATH",
                        message=f"Artifact missing path specification",
                        severity=ValidationSeverity.WARNING,
                    )
                )
                continue

            # 解析路径
            resolved_path = self._resolve_path(path)
            file_path = Path(resolved_path)

            # 检查存在性
            if not file_path.exists():
                if required:
                    errors.append(
                        ValidationError(
                            code="ARTIFACT_NOT_FOUND",
                            message=f"{artifact_type.capitalize()} not found: {path}",
                            path=str(file_path),
                            severity=ValidationSeverity.ERROR,
                        )
                    )
                else:
                    warnings.append(
                        ValidationError(
                            code="ARTIFACT_NOT_FOUND",
                            message=f"Optional {artifact_type} not found: {path}",
                            path=str(file_path),
                            severity=ValidationSeverity.WARNING,
                        )
                    )
                continue

            # 检查 schema（如果有定义）
            schema_path = artifact.get("schema")
            if schema_path:
                schema_errors, schema_warnings = self._validate_schema(
                    str(file_path), schema_path
                )
                errors.extend(schema_errors)
                warnings.extend(schema_warnings)

            # 检查内容要求（如果有定义）
            content_rules = artifact.get("content_rules")
            if content_rules:
                content_errors, content_warnings = self._validate_content_rules(
                    str(file_path), content_rules
                )
                errors.extend(content_errors)
                warnings.extend(content_warnings)

        return errors, warnings

    def _validate_schema(
        self, file_path: str, schema_path: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """根据 schema 验证文件"""
        errors = []
        warnings = []

        resolved_schema = self._resolve_path(schema_path)
        schema_file = Path(resolved_schema)

        if not schema_file.exists():
            errors.append(
                ValidationError(
                    code="SCHEMA_NOT_FOUND",
                    message=f"Schema file not found: {schema_path}",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                )
            )
            return errors, warnings

        # 使用 SchemaValidator 进行验证
        from .schema_validator import SchemaValidator

        validator = SchemaValidator(self.project_dir)
        result = validator.validate_file(
            file_path,
            {"schema_path": str(schema_file)},
        )

        errors.extend(result.errors)
        warnings.extend(result.warnings)

        return errors, warnings

    def _validate_content_rules(
        self, file_path: str, rules: Dict
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证内容规则"""
        errors = []
        warnings = []

        # 使用 ContentValidator 进行验证
        from .content_validator import ContentValidator

        validator = ContentValidator(self.project_dir)
        result = validator.validate(
            None,
            {
                "path": file_path,
                "rules": rules,
            },
        )

        errors.extend(result.errors)
        warnings.extend(result.warnings)

        return errors, warnings

    def _validate_data_contracts(
        self, data_contracts: List[Dict]
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证数据契约"""
        errors = []
        warnings = []

        for dc in data_contracts:
            dc_name = dc.get("name", "")
            dc_type = dc.get("type", "")
            dc_spec = dc.get("spec", {})

            if not dc_name:
                warnings.append(
                    ValidationError(
                        code="DATA_CONTRACT_NO_NAME",
                        message="Data contract missing name",
                        severity=ValidationSeverity.WARNING,
                    )
                )
                continue

            # 根据类型进行特定验证
            if dc_type == "json_schema":
                # JSON Schema 契约验证
                schema_path = dc_spec.get("schema_path")
                if schema_path:
                    schema_errors, schema_warnings = self._validate_schema(
                        dc_name, schema_path
                    )
                    errors.extend(schema_errors)
                    warnings.extend(schema_warnings)
            elif dc_type == "format":
                # 格式契约验证
                format_rules = dc_spec.get("rules", [])
                if format_rules:
                    from .content_validator import ContentValidator

                    validator = ContentValidator(self.project_dir)
                    result = validator.validate(
                        None,
                        {
                            "path": dc_name,
                            "rules": format_rules,
                        },
                    )
                    errors.extend(result.errors)
                    warnings.extend(result.warnings)
            else:
                warnings.append(
                    ValidationError(
                        code="UNKNOWN_CONTRACT_TYPE",
                        message=f"Unknown data contract type: {dc_type}",
                        severity=ValidationSeverity.WARNING,
                    )
                )

        return errors, warnings


class OutputContractValidator(Validator):
    """
    输出契约验证器（简化的契约验证）

    专门用于验证步骤输出契约。

    配置格式:
        validators:
          - type: output_contract
            outputs:
              - path: output/design.md
                required: true
              - path: output/schema.json
                required: true
                schema_path: schemas/design.schema.json
    """

    validator_type = "output_contract"
    validator_name = "output_contract_validator"

    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """执行验证"""
        errors = []
        warnings = []

        # 直接使用 ContractValidator 的核心逻辑
        outputs = config.get("outputs", [])
        if not outputs:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="CONFIG_ERROR",
                        message="No outputs specified",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 复用 ContractValidator 的验证逻辑
        output_errors, output_warnings = self._validate_artifacts(outputs, "output")
        errors.extend(output_errors)
        warnings.extend(output_warnings)

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={"outputs_checked": len(outputs)},
        )

    def _validate_artifacts(
        self, artifacts: List[Dict], artifact_type: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证产物列表（从 ContractValidator 复用）"""
        errors = []
        warnings = []

        for artifact in artifacts:
            path = artifact.get("path", "")
            required = artifact.get("required", True)

            if not path:
                warnings.append(
                    ValidationError(
                        code="ARTIFACT_NO_PATH",
                        message=f"Artifact missing path specification",
                        severity=ValidationSeverity.WARNING,
                    )
                )
                continue

            resolved_path = self._resolve_path(path)
            file_path = Path(resolved_path)

            if not file_path.exists():
                if required:
                    errors.append(
                        ValidationError(
                            code="ARTIFACT_NOT_FOUND",
                            message=f"{artifact_type.capitalize()} not found: {path}",
                            path=str(file_path),
                            severity=ValidationSeverity.ERROR,
                        )
                    )
                else:
                    warnings.append(
                        ValidationError(
                            code="ARTIFACT_NOT_FOUND",
                            message=f"Optional {artifact_type} not found: {path}",
                            path=str(file_path),
                            severity=ValidationSeverity.WARNING,
                        )
                    )
                continue

            # 检查 schema
            schema_path = artifact.get("schema_path")
            if schema_path:
                from .schema_validator import SchemaValidator

                validator = SchemaValidator(self.project_dir)
                result = validator.validate_file(path, {"schema_path": schema_path})
                errors.extend(result.errors)
                warnings.extend(result.warnings)

        return errors, warnings


# 注册验证器
ValidatorRegistry.register(ContractValidator)
ValidatorRegistry.register(OutputContractValidator)
