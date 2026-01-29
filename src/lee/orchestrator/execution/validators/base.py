"""
Validator Base Classes - 验证器基类和结果数据结构
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod
from enum import Enum


class ValidationSeverity(Enum):
    """验证严重级别"""
    ERROR = "error"       # 阻塞性错误
    WARNING = "warning"   # 警告（不阻塞）


@dataclass
class ValidationError:
    """验证错误详情"""
    code: str                      # 错误码
    message: str                   # 错误消息
    path: Optional[str] = None     # 错误位置（JSON Path 等）
    severity: ValidationSeverity = ValidationSeverity.ERROR
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ValidationResult:
    """验证结果"""
    passed: bool                   # 是否通过验证
    validator: str                 # 验证器名称
    errors: List[ValidationError] = field(default_factory=list)
    warnings: List[ValidationError] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def has_errors(self) -> bool:
        """是否有错误"""
        return len(self.errors) > 0

    @property
    def has_warnings(self) -> bool:
        """是否有警告"""
        return len(self.warnings) > 0

    @property
    def is_blocking(self) -> bool:
        """是否阻塞（有错误）"""
        return self.has_errors

    def get_summary(self) -> str:
        """获取摘要"""
        parts = []
        if self.passed:
            parts.append("PASSED")
        else:
            parts.append("FAILED")

        if self.errors:
            parts.append(f"{len(self.errors)} errors")
        if self.warnings:
            parts.append(f"{len(self.warnings)} warnings")

        return " - ".join(parts)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "passed": self.passed,
            "validator": self.validator,
            "errors": [
                {
                    "code": e.code,
                    "message": e.message,
                    "path": e.path,
                    "severity": e.severity.value,
                    "details": e.details,
                }
                for e in self.errors
            ],
            "warnings": [
                {
                    "code": w.code,
                    "message": w.message,
                    "path": w.path,
                    "severity": w.severity.value,
                    "details": w.details,
                }
                for w in self.warnings
            ],
            "metadata": self.metadata,
        }


class ValidatorException(Exception):
    """验证器异常"""

    def __init__(self, validator: str, message: str, errors: List[ValidationError] = None):
        self.validator = validator
        self.message = message
        self.errors = errors or []
        super().__init__(f"[{validator}] {message}")


class Validator(ABC):
    """验证器基类"""

    validator_type: str = "base"
    validator_name: str = "base_validator"

    def __init__(self, project_dir: str = None):
        """
        初始化验证器

        Args:
            project_dir: 项目根目录（用于解析相对路径）
        """
        self.project_dir = project_dir

    @abstractmethod
    def validate(self, data: Any, config: Dict) -> ValidationResult:
        """
        执行验证

        Args:
            data: 待验证的数据
            config: 验证配置（从 workflow.yaml 的 validators 部分传入）

        Returns:
            ValidationResult 对象
        """
        pass

    def validate_file(self, file_path: str, config: Dict) -> ValidationResult:
        """
        验证文件（便捷方法）

        Args:
            file_path: 文件路径
            config: 验证配置

        Returns:
            ValidationResult 对象
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
                    )
                ],
            )

        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            return self.validate(content, config)
        except Exception as e:
            return ValidationResult(
                passed=False,
                validator=self.validator_name,
                errors=[
                    ValidationError(
                        code="FILE_READ_ERROR",
                        message=f"Failed to read file: {e}",
                        path=str(path),
                    )
                ],
            )

    def _resolve_path(self, path: str) -> str:
        """解析相对路径为绝对路径"""
        from pathlib import Path

        p = Path(path)
        if p.is_absolute():
            return str(p)
        if self.project_dir:
            return str(Path(self.project_dir) / p)
        return path


class ValidatorRegistry:
    """验证器注册表"""

    _validators: Dict[str, type] = {}

    @classmethod
    def register(cls, validator_class: type) -> type:
        """注册验证器"""
        cls._validators[validator_class.validator_name] = validator_class
        return validator_class

    @classmethod
    def get(cls, name: str) -> Optional[type]:
        """获取验证器类"""
        return cls._validators.get(name)

    @classmethod
    def list_validators(cls) -> List[str]:
        """列出所有已注册的验证器"""
        return list(cls._validators.keys())

    @classmethod
    def create(cls, name: str, project_dir: str = None) -> Optional[Validator]:
        """创建验证器实例"""
        validator_class = cls.get(name)
        if validator_class:
            return validator_class(project_dir)
        return None
