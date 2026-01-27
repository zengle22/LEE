"""
Content Validator - 内容验证器

验证文件内容是否符合特定要求（如包含必需的字段、正则匹配等）。
"""

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Pattern
from datetime import datetime

from .base import (
    Validator,
    ValidationResult,
    ValidationError,
    ValidationSeverity,
    ValidatorRegistry,
)


class ContentValidator(Validator):
    """
    内容验证器

    验证文件内容是否符合指定的规则。

    配置格式:
        validators:
          - type: content
            files:
              - path: output/report.md
                rules:
                  - type: required_fields
                    fields: ["title", "date", "author"]
                  - type: contains
                    patterns: ["# Summary", "## Conclusion"]
                  - type: regex
                    pattern: "^#+ .+$"
                    description: "Must contain headers"
    """

    validator_type = "content"
    validator_name = "content_validator"

    # 内置规则类型
    RULE_REQUIRED_FIELDS = "required_fields"
    RULE_CONTAINS = "contains"
    RULE_REGEX = "regex"
    RULE_MIN_LENGTH = "min_length"
    RULE_MAX_LENGTH = "max_length"
   _rule_handlers = {}

    def __init__(self, project_dir: str = None):
        super().__init__(project_dir)
        # 注册规则处理器
        self._rule_handlers = {
            self.RULE_REQUIRED_FIELDS: self._validate_required_fields,
            self.RULE_CONTAINS: self._validate_contains,
            self.RULE_REGEX: self._validate_regex,
            self.RULE_MIN_LENGTH: self._validate_min_length,
            self.RULE_MAX_LENGTH: self._validate_max_length,
        }

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

        # 获取文件规则列表
        file_rules = config.get("files", [])
        if not file_rules:
            # 简化格式：直接在顶层定义 rules，应用到单个文件
            file_path = config.get("path", "")
            rules = config.get("rules", [])
            if file_path and rules:
                file_rules = [{"path": file_path, "rules": rules}]

        if not file_rules:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="CONFIG_ERROR",
                        message="No file rules specified in config",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 逐个验证文件
        for file_rule in file_rules:
            if isinstance(file_rule, str):
                # 简化格式：字符串路径，使用默认规则
                file_path = file_rule
                rules = config.get("rules", [])
            elif isinstance(file_rule, dict):
                file_path = file_rule.get("path", "")
                rules = file_rule.get("rules", [])
            else:
                errors.append(
                    ValidationError(
                        code="CONFIG_ERROR",
                        message=f"Invalid file rule: {file_rule}",
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            if not file_path:
                errors.append(
                    ValidationError(
                        code="CONFIG_ERROR",
                        message="File path not specified in rule",
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 解析路径
            resolved_path = self._resolve_path(file_path)
            path = Path(resolved_path)

            # 检查文件存在
            if not path.exists():
                errors.append(
                    ValidationError(
                        code="FILE_NOT_FOUND",
                        message=f"File not found: {file_path}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 读取文件内容
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                errors.append(
                    ValidationError(
                        code="FILE_READ_ERROR",
                        message=f"Failed to read file: {e}",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )
                continue

            # 应用所有规则
            for rule in rules:
                rule_type = rule.get("type", "")
                handler = self._rule_handlers.get(rule_type)

                if not handler:
                    warnings.append(
                        ValidationError(
                            code="UNKNOWN_RULE",
                            message=f"Unknown rule type: {rule_type}",
                            path=str(path),
                            severity=ValidationSeverity.WARNING,
                        )
                    )
                    continue

                # 执行规则验证
                rule_errors, rule_warnings = handler(content, rule, str(path))
                errors.extend(rule_errors)
                warnings.extend(rule_warnings)

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
            metadata={"files_validated": len(file_rules)},
        )

    def _validate_required_fields(
        self, content: str, rule: Dict, file_path: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证必需字段（用于 YAML/JSON 前置内容）"""
        errors = []
        warnings = []

        fields = rule.get("fields", [])
        if not fields:
            return errors, warnings

        # 解析前置内容（Markdown YAML front matter 或独立 YAML）
        yaml_content = self._extract_yaml_frontmatter(content)
        if not yaml_content:
            errors.append(
                ValidationError(
                    code="REQUIRED_FIELDS_MISSING",
                    message=f"YAML front matter not found",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                    details={"required_fields": fields},
                )
            )
            return errors, warnings

        try:
            import yaml
            data = yaml.safe_load(yaml_content) or {}
        except Exception:
            errors.append(
                ValidationError(
                    code="INVALID_YAML",
                    message="Failed to parse YAML front matter",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                )
            )
            return errors, warnings

        # 检查字段
        missing = []
        for field in fields:
            if field not in data or not data[field]:
                missing.append(field)

        if missing:
            errors.append(
                ValidationError(
                    code="REQUIRED_FIELDS_MISSING",
                    message=f"Missing required fields: {', '.join(missing)}",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                    details={"missing_fields": missing},
                )
            )

        return errors, warnings

    def _validate_contains(
        self, content: str, rule: Dict, file_path: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证内容是否包含指定的模式"""
        errors = []
        warnings = []

        patterns = rule.get("patterns", [])
        if not patterns:
            return errors, warnings

        case_sensitive = rule.get("case_sensitive", True)
        if not case_sensitive:
            content_lower = content.lower()
        else:
            content_lower = content

        missing = []
        for pattern in patterns:
            search_pattern = pattern if case_sensitive else pattern.lower()
            if search_pattern not in content_lower:
                missing.append(pattern)

        if missing:
            errors.append(
                ValidationError(
                    code="PATTERN_NOT_FOUND",
                    message=f"Content missing required patterns: {', '.join(missing)}",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                    details={"missing_patterns": missing},
                )
            )

        return errors, warnings

    def _validate_regex(
        self, content: str, rule: Dict, file_path: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证内容是否匹配正则表达式"""
        errors = []
        warnings = []

        pattern_str = rule.get("pattern", "")
        if not pattern_str:
            return errors, warnings

        flags = 0
        if not rule.get("case_sensitive", True):
            flags |= re.IGNORECASE
        if rule.get("multiline", False):
            flags |= re.MULTILINE

        try:
            pattern = re.compile(pattern_str, flags)
        except re.error as e:
            errors.append(
                ValidationError(
                    code="INVALID_REGEX",
                    message=f"Invalid regex pattern: {e}",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                )
            )
            return errors, warnings

        if not pattern.search(content):
            description = rule.get("description", "Pattern not found")
            errors.append(
                ValidationError(
                    code="REGEX_NOT_MATCHED",
                    message=f"{description}: {pattern_str}",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                )
            )

        return errors, warnings

    def _validate_min_length(
        self, content: str, rule: Dict, file_path: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证最小长度"""
        errors = []
        warnings = []

        min_length = rule.get("value", 0)
        actual_length = len(content)

        if actual_length < min_length:
            errors.append(
                ValidationError(
                    code="CONTENT_TOO_SHORT",
                    message=f"Content length ({actual_length}) below minimum ({min_length})",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                    details={"actual_length": actual_length, "min_length": min_length},
                )
            )

        return errors, warnings

    def _validate_max_length(
        self, content: str, rule: Dict, file_path: str
    ) -> tuple[List[ValidationError], List[ValidationError]]:
        """验证最大长度"""
        errors = []
        warnings = []

        max_length = rule.get("value", 0)
        actual_length = len(content)

        if actual_length > max_length:
            errors.append(
                ValidationError(
                    code="CONTENT_TOO_LONG",
                    message=f"Content length ({actual_length}) exceeds maximum ({max_length})",
                    path=file_path,
                    severity=ValidationSeverity.ERROR,
                    details={"actual_length": actual_length, "max_length": max_length},
                )
            )

        return errors, warnings

    def _extract_yaml_frontmatter(self, content: str) -> Optional[str]:
        """提取 YAML front matter"""
        # 检查是否以 --- 开头
        if not content.startswith("---"):
            return None

        # 查找结束的 ---
        end_pos = content.find("\n---", 4)
        if end_pos == -1:
            return None

        return content[4:end_pos].strip()


class MarkdownValidator(Validator):
    """
    Markdown 专用验证器

    验证 Markdown 文件的格式、结构等。

    配置格式:
        validators:
          - type: markdown
            file: output/report.md
            require_headers: true
            min_header_level: 1
            max_header_level: 6
    """

    validator_type = "markdown"
    validator_name = "markdown_validator"

    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """执行验证"""
        errors = []
        warnings = []

        file_path = config.get("file", "")
        if not file_path:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="CONFIG_ERROR",
                        message="No file specified",
                        severity=ValidationSeverity.ERROR,
                    )
                ],
            )

        # 解析路径
        resolved_path = self._resolve_path(file_path)
        path = Path(resolved_path)

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
                content = f.read()
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

        # 验证标题
        if config.get("require_headers", False):
            has_headers = bool(re.search(r"^#+\s+", content, re.MULTILINE))
            if not has_headers:
                errors.append(
                    ValidationError(
                        code="NO_HEADERS",
                        message="Markdown file has no headers",
                        path=str(path),
                        severity=ValidationSeverity.ERROR,
                    )
                )

        # 验证标题层级
        min_level = config.get("min_header_level", 1)
        max_level = config.get("max_header_level", 6)

        for match in re.finditer(r"^(#+)\s+", content, re.MULTILINE):
            level = len(match.group(1))
            if level < min_level or level > max_level:
                warnings.append(
                    ValidationError(
                        code="INVALID_HEADER_LEVEL",
                        message=f"Header level {level} outside allowed range ({min_level}-{max_level})",
                        path=str(path),
                        severity=ValidationSeverity.WARNING,
                        details={"level": level, "min": min_level, "max": max_level},
                    )
                )

        return ValidationResult(
            passed=len(errors) == 0,
            validator=self.validator_name,
            errors=errors,
            warnings=warnings,
        )


# 注册验证器
ValidatorRegistry.register(ContentValidator)
ValidatorRegistry.register(MarkdownValidator)
