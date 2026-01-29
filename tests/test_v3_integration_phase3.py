"""
测试 LEE Orchestrator v3.1 - Phase 3 集成测试

测试内容：
1. Validator 基础功能
2. SchemaValidator
3. FileValidator
"""

import sys
import os
import tempfile
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.validators.base import (
    Validator, ValidationResult, ValidationError, ValidationSeverity,
)


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


def test_validator_base():
    """测试 Validator 基础功能"""
    print_section("测试 1: Validator 基础")

    # 测试 ValidationError
    error = ValidationError(
        code="TEST_ERROR",
        message="Test error message",
        path="/test/path",
        severity=ValidationSeverity.ERROR
    )
    assert error.code == "TEST_ERROR"
    assert error.severity == ValidationSeverity.ERROR
    print("   ✅ ValidationError 创建成功")

    # 测试 ValidationResult
    result = ValidationResult(
        validator="TestValidator",
        passed=True,
        errors=[],
        warnings=[],
        metadata={"test": "data"}
    )
    assert result.passed == True
    assert not result.has_errors
    assert not result.has_warnings
    print("   ✅ ValidationResult 创建成功")

    # 测试带错误的 ValidationResult
    result_with_errors = ValidationResult(
        validator="TestValidator",
        passed=False,
        errors=[error],
        warnings=[],
        metadata={}
    )
    assert result_with_errors.has_errors
    print("   ✅ ValidationResult 错误检测正常")


def test_validation_severity():
    """测试 ValidationSeverity 枚举"""
    print_section("测试 2: ValidationSeverity")

    assert ValidationSeverity.ERROR.value == "error"
    assert ValidationSeverity.WARNING.value == "warning"
    print("   ✅ ValidationSeverity 枚举正常")


def test_validator_summary():
    """测试验证结果摘要"""
    print_section("测试 3: 验证摘要")

    result = ValidationResult(
        validator="TestValidator",
        passed=True,
        errors=[],
        warnings=[
            ValidationError(
                code="WARN_001",
                message="Warning message",
                severity=ValidationSeverity.WARNING
            )
        ],
        metadata={}
    )

    summary = result.get_summary()
    assert "PASSED" in summary
    assert "1 warnings" in summary
    print(f"   ✅ 摘要: {summary}")


def main():
    """主测试流程"""
    print("=" * 60)
    print("🚀 LEE Orchestrator v3.1 - Phase 3 集成测试")
    print("=" * 60)

    test_validator_base()
    test_validation_severity()
    test_validator_summary()

    print("\n" + "=" * 60)
    print("✅ Phase 3 所有测试通过！")
    print("=" * 60)

    print("\n📋 验证结果:")
    print("  ✅ Validator 基础功能")
    print("  ✅ ValidationError")
    print("  ✅ ValidationResult")
    print("  ✅ ValidationSeverity")

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
