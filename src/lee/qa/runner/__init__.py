"""
LEE QA Runner Module

提供测试执行器基础设施。
"""

# Base classes
from lee.qa.runner.base import (
    TestConfig,
    CaseResult,
    TestResult,
    BaseRunner,
)

# SUT configuration
from lee.qa.runner.sut import (
    SUTType,
    SUTConfig,
    URLResolver,
    SUTConfigLoader,
    resolve_sut_url,
)

# Runners
from lee.qa.runner.local import LocalRunner

__all__ = [
    # Base classes
    "TestConfig",
    "CaseResult",
    "TestResult",
    "BaseRunner",
    # SUT
    "SUTType",
    "SUTConfig",
    "URLResolver",
    "SUTConfigLoader",
    "resolve_sut_url",
    # Runners
    "LocalRunner",
]
