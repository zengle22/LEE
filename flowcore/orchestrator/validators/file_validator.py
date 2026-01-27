"""
File Validator - 文件验证器

验证文件的存在性、大小、权限等。
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from .base import (
    Validator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidatorRegistry,
)


class FileValidator(Validator):
    """
    文件验证器

    验证配置中指定的文件是否存在、可读等。

    配置格式:
        validators:
          - type: file
            files:
              - output/result.json
              - output/report.md
            check_readable: true
            check_not_empty: true
            min_size: 0
            max_size: 10485760  # 10MB
    """

    validator_type = "file"
    validator_name = "file_validator"

    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """
        执行验证

        Args:
            data: 待验证的数据（在此验证器中未使用，保持接口一致性）
            config: 验证配置

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # 获取文件列表
        files = config.get("files", [])
        if not files:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="CONFIG_ERROR",
                        message="No files specified in config",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 验证选项
        check_readable = config.get("check_readable", True)
        check_not_empty = config.get("check_not_empty", False)
        min_size = config.get("min_size", 0)
        max_size = config.get("max_size", None)

        # 逐个验证文件
        for file_spec in files:
            if isinstance(file_spec, str):
                file_path = file_spec
                file_required = True
            elif isinstance(file_spec, dict):
                file_path = file_spec.get("path", "")
                file_required = file_spec.get("required", True)
            else:
                errors.append(
                    ValidationError(
                        code="CONFIG_ERROR",
                        message=f"Invalid file spec: {file_spec}",
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 解析路径
            resolved_path = self._resolve_path(file_path)
            path = Path(resolved_path)

            # 检查存在性
            if not path.exists():
                if file_required:
                    errors.append(
                        ValidationError(
                            code="FILE_NOT_FOUND",
                            message=f"Required file not found: {file_path}",
                            path=str(path),
                            severity=ValidationSeverity.ERROR,
                        )
                    )
                else:
                    warnings.append(
                        ValidationError(
                            code="FILE_NOT_FOUND",
                            message=f"Optional file not found: {file_path}",
                            path=str(path),
                            severity=ValidationSeverity.WARNING,
                        )
                    )
                continue

            # 检查是否为文件（而非目录）
            if path.is_dir():
                errors.append(
                    ValidationError(
                        code="NOT_A_FILE",
                        message=f"Path is a directory, not a file: {file_path}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 检查可读性
            if check_readable and not os.access(path, os.R_OK):
                errors.append(
                    ValidationError(
                        code="FILE_NOT_READABLE",
                        message=f"File is not readable: {file_path}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )

            # 检查文件大小
            try:
                file_size = path.stat().st_size

                if file_size == 0 and check_not_empty:
                    errors.append(
                        ValidationError(
                            code="FILE_EMPTY",
                            message=f"File is empty: {file_path}",
                            path=str(path),
                            severity=ValidationSeverity.ERROR,
                        )
                    )

                if file_size < min_size:
                    errors.append(
                        ValidationError(
                            code="FILE_TOO_SMALL",
                            message=f"File size ({file_size}) below minimum ({min_size}): {file_path}",
                            path=str(path),
                            severity=ValidationSeverity.ERROR,
                            details={"actual_size": file_size, "min_size": min_size},
                        )
                    )

                if max_size is not None and file_size > max_size:
                    errors.append(
                        ValidationError(
                            code="FILE_TOO_LARGE",
                            message=f"File size ({file_size}) exceeds maximum ({max_size}): {file_path}",
                            path=str(path),
                            severity=ValidationSeverity.ERROR,
                            details={"actual_size": file_size, "max_size": max_size},
                        )
                    )
            except OSError as e:
                errors.append(
                    ValidationError(
                        code="FILE_STAT_ERROR",
                        message=f"Failed to get file info: {e}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={
                "files_checked": len(files),
                "files_found": len(files) - len([e for e in errors if e.code == "FILE_NOT_FOUND"]),
            },
        )


class DirectoryValidator(Validator):
    """
    目录验证器

    验证目录是否存在、可写等。

    配置格式:
        validators:
          - type: directory
            directories:
              - output
              - logs
            check_writable: true
            create_if_missing: false
    """

    validator_type = "directory"
    validator_name = "directory_validator"

    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """
        执行验证

        Args:
            data: 待验证的数据（未使用）
            config: 验证配置

        Returns:
            ValidationResult
        """
        errors = []
        warnings = []

        # 获取目录列表
        directories = config.get("directories", [])
        if not directories:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="CONFIG_ERROR",
                        message="No directories specified in config",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 验证选项
        check_writable = config.get("check_writable", False)
        create_if_missing = config.get("create_if_missing", False)

        # 逐个验证目录
        for dir_spec in directories:
            if isinstance(dir_spec, str):
                dir_path = dir_spec
                dir_required = True
            elif isinstance(dir_spec, dict):
                dir_path = dir_spec.get("path", "")
                dir_required = dir_spec.get("required", True)
            else:
                errors.append(
                    ValidationError(
                        code="CONFIG_ERROR",
                        message=f"Invalid directory spec: {dir_spec}",
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 解析路径
            resolved_path = self._resolve_path(dir_path)
            path = Path(resolved_path)

            # 检查存在性
            if not path.exists():
                if create_if_missing:
                    try:
                        path.mkdir(parents=True, exist_ok=True)
                        warnings.append(
                            ValidationError(
                                code="DIRECTORY_CREATED",
                                message=f"Directory created: {dir_path}",
                                path=str(path),
                                severity=ValidationSeverity.WARNING,
                            )
                        )
                    except OSError as e:
                        errors.append(
                            ValidationError(
                                code="DIRECTORY_CREATE_FAILED",
                                message=f"Failed to create directory: {e}",
                                path=str(path),
                                severity=ValidationSeverity.ERROR,
                            )
                        )
                        continue
                elif dir_required:
                    errors.append(
                        ValidationError(
                            code="DIRECTORY_NOT_FOUND",
                            message=f"Required directory not found: {dir_path}",
                            path=str(path),
                            severity=ValidationSeverity.ERROR,
                        )
                    )
                    continue
                else:
                    warnings.append(
                        ValidationError(
                            code="DIRECTORY_NOT_FOUND",
                            message=f"Optional directory not found: {dir_path}",
                            path=str(path),
                            severity=ValidationSeverity.WARNING,
                        )
                    )
                    continue

            # 检查是否为目录
            if not path.is_dir():
                errors.append(
                    ValidationError(
                        code="NOT_A_DIRECTORY",
                        message=f"Path is not a directory: {dir_path}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 检查可写性
            if check_writable:
                if not os.access(path, os.W_OK):
                    errors.append(
                        ValidationError(
                            code="DIRECTORY_NOT_WRITABLE",
                            message=f"Directory is not writable: {dir_path}",
                            path=str(path),
                            severity=ValidationSeverity.ERROR,
                        )
                    )

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={
                "directories_checked": len(directories),
                "directories_found": len(directories) - len([e for e in errors if e.code == "DIRECTORY_NOT_FOUND"]),
            },
        )


# 注册验证器
ValidatorRegistry.register(FileValidator)
ValidatorRegistry.register(DirectoryValidator)
