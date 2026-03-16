"""
目录策略定义 - SSOT

PathConfig 和 PathGuard 共用此策略定义
"""

from typing import FrozenSet


# 工具目录定义
TOOL_DIRECTORIES: FrozenSet[str] = frozenset({
    ".artifacts",
    ".workflow",
    ".project",
})

# 工作流子目录定义 (用于替换硬编码)
WORKFLOW_SUBDIRS = {
    "runs": ".workflow/runs",
    "cache": ".workflow/cache",
    "tokens": ".workflow/tokens",
    "events": ".workflow/events",
    "traces": ".workflow/traces",
    "evidence": ".workflow/evidence",
    "workspace_cleanup": ".workflow/workspace_cleanup",
    "db": ".workflow/db",
    "compliance": ".workflow/compliance",
    "env_check": ".workflow/env_check",
}

# Artifacts 子目录
ARTIFACTS_SUBDIRS = {
    "active": ".artifacts/active",
    "frozen": ".artifacts/frozen",
    "archive": ".artifacts/archive",
}

# 规格 SSOT 目录
SPEC_SUBDIRS = {
    "requirements": "spec/requirements",
    "api": "spec/api",
    "data": "spec/data",
    "ui": "spec/ui",
    "adr": "spec/adr",
}

# 允许写入的路径前缀集合 (统一使用正斜杠，兼容 Windows)
ALLOWED_WRITE_PREFIXES: FrozenSet[str] = frozenset({
    ".artifacts/",      # 产出物
    ".workflow/",       # 工作流运行态
    ".lee/",            # CLI 锁目录
    "tools/",          # 项目工具
    "deploy/",         # 部署配置
})

# 冻结目录前缀集合 (禁止写入/删除 - 业务核心)
FROZEN_PREFIXES: FrozenSet[str] = frozenset({
    "spec/",           # 规格 SSOT
    "src/",            # 源码
    "tests/",         # 测试
    "docs/",          # 文档
    "legacy/",         # 兼容旧版（只读）
})

# 项目配置目录（只读）
PROJECT_CONFIG_PREFIXES: FrozenSet[str] = frozenset({
    ".project/",       # 项目配置
})


def normalize_path(path: str) -> str:
    """
    规范化路径为 POSIX 格式（正斜杠）

    确保跨平台一致性：Windows 反斜杠 → 正斜杠
    """
    return path.replace("\\", "/")


def is_allowed_write_path(rel_path: str) -> bool:
    """
    判断相对路径是否允许写入

    判定逻辑:
    1. 先规范化路径（兼容 Windows）
    2. 检查是否匹配允许前缀（包括根目录本身）
    """
    # 规范化路径（兼容 Windows）
    normalized = normalize_path(rel_path)

    # 统一检查：前缀匹配 + 根目录本身匹配
    for prefix in ALLOWED_WRITE_PREFIXES:
        root = prefix.rstrip("/")  # 去掉末尾斜杠得到根目录名
        # 检查前缀匹配 或 根目录本身匹配
        if normalized.startswith(prefix) or normalized == root:
            return True

    return False


def is_frozen_path(rel_path: str) -> bool:
    """判断路径是否在冻结目录"""
    # 规范化路径（兼容 Windows）
    normalized = normalize_path(rel_path)

    # 统一检查：前缀匹配 + 根目录本身匹配
    for prefix in FROZEN_PREFIXES:
        root = prefix.rstrip("/")  # 去掉末尾斜杠得到根目录名
        # 检查前缀匹配 或 根目录本身匹配
        if normalized.startswith(prefix) or normalized == root:
            return True

    return False


def is_dev_mode() -> bool:
    """判断是否在 dev 模式"""
    import os
    value = os.getenv("LEE_DEV_MODE", "").lower()
    return value in ("1", "true")


def is_ci_mode() -> bool:
    """判断是否在 CI 模式"""
    import os
    value = os.getenv("CI", "").lower()
    return value in ("1", "true")


def is_path_guard_enabled() -> bool:
    """判断是否启用 PathGuard"""
    return is_dev_mode() or is_ci_mode()
