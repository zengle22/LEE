"""
SSOT ID Parser

SSOT ID 解析器 - 提供 ID 结构解析、格式校验功能。

ID 格式规范 (v1.3):
- 独立顺序型: SRC-001, EPIC-001, FEAT-001, ADR-001
- 单父唯一型: TECH-FEAT-001, TESTSET-FEAT-001
- 单父多实例型: UI-FEAT-001-01, TASK-FEAT-001-FE-01
- 时态/运行型: REPORT-FEAT-001-20260306
- 范围归属型: TC-FEAT-001-001, BUG-FEAT-001-001, EVI-FEAT-001-001
"""

from dataclasses import dataclass
from typing import Dict, List, Optional

from .types import SSOTType, ObjectCategory


@dataclass
class IDParseResult:
    """ID 解析结果"""

    id: str
    prefix: str  # 类型前缀 (如 FEAT, TC)
    parent_scope: Optional[str]  # 父对象范围 (如 FEAT-001)
    sequence: Optional[str]  # 序号部分
    suffix: Optional[str]  # 后缀 (如 FE, 01, 日期)
    is_valid: bool
    error: Optional[str] = None


def parse_parent(id: str) -> Optional[str]:
    """
    从 ID 中解析直接父对象

    适用于：直接父对象一致型 (TECH, TESTSET, UI, TASK, REPORT)

    规则:
    - TECH-FEAT-001 → FEAT-001
    - TESTSET-FEAT-001 → FEAT-001
    - UI-FEAT-001-01 → FEAT-001
    - TASK-FEAT-001-FE-01 → FEAT-001
    - REPORT-FEAT-001-20260306 → FEAT-001

    Args:
        id: SSOT ID

    Returns:
        父对象 ID，如 FEAT-001，或 None (独立型)
    """
    parts = id.split("-")

    if len(parts) < 2:
        return None

    prefix = parts[0].upper()

    # 独立型：无 parent
    if prefix in ("SRC", "EPIC", "FEAT", "ADR"):
        return None

    # 范围归属型：不应使用此函数
    if prefix in ("TC", "BUG", "EVI"):
        # 使用 parse_scope 代替
        return None

    # 直接父对象一致型: TYPE-FEAT-XXX 或 TYPE-FEAT-XXX-SUFFIX
    if prefix in ("TECH", "TESTSET", "UI", "TASK", "REPORT"):
        # 查找 FEAT- 前缀的位置
        try:
            feat_idx = parts.index("FEAT")
            if feat_idx + 1 < len(parts):
                return f"FEAT-{parts[feat_idx + 1]}"
        except ValueError:
            pass

    return None


def parse_scope(id: str) -> Optional[str]:
    """
    从 ID 中解析归属范围 (FEAT)

    适用于：范围归属型 (TC, BUG, EVI)

    规则:
    - TC-FEAT-001-001 → FEAT-001
    - BUG-FEAT-001-001 → FEAT-001
    - EVI-FEAT-001-001 → FEAT-001

    Args:
        id: SSOT ID

    Returns:
        归属范围 FEAT ID，如 FEAT-001，或 None
    """
    parts = id.split("-")

    if len(parts) < 3:
        return None

    prefix = parts[0].upper()

    # 范围归属型: TYPE-FEAT-XXX-SEQ
    if prefix in ("TC", "BUG", "EVI"):
        try:
            feat_idx = parts.index("FEAT")
            if feat_idx + 1 < len(parts):
                return f"FEAT-{parts[feat_idx + 1]}"
        except ValueError:
            pass

    return None


def resolve_scope(parent_id: str) -> Optional[str]:
    """
    从 parent_id 解析归属范围

    P0 阶段规则:
    - 只支持已知类型的单跳解析，不支持无限递归链
    - 若 parent_id 是 FEAT，直接返回
    - 若 parent_id 是 TC/BUG/TECH/TASK/TESTSET/UI/REPORT，按已知规则解析到 FEAT

    Args:
        parent_id: 父对象 ID

    Returns:
        归属范围 FEAT ID，或 None
    """
    if not parent_id:
        return None

    parts = parent_id.split("-")
    prefix = parts[0].upper()

    # 直接是 FEAT
    if prefix == "FEAT":
        if len(parts) >= 3:
            return f"FEAT-{parts[1]}"
        return parent_id

    # 已知类型：单跳解析到 FEAT
    if prefix in ("TC", "BUG", "EVI"):
        # TC-FEAT-001-001 → FEAT-001
        try:
            feat_idx = parts.index("FEAT")
            if feat_idx + 1 < len(parts):
                return f"FEAT-{parts[feat_idx + 1]}"
        except ValueError:
            pass

    if prefix in ("TECH", "TESTSET", "UI", "TASK", "REPORT"):
        # TECH-FEAT-001 → FEAT-001
        try:
            feat_idx = parts.index("FEAT")
            if feat_idx + 1 < len(parts):
                return f"FEAT-{parts[feat_idx + 1]}"
        except ValueError:
            pass

    # P0 阶段：未知类型不支持，返回 None
    return None


def parse_id(id: str) -> IDParseResult:
    """
    解析 ID 结构

    Args:
        id: SSOT ID

    Returns:
        IDParseResult 包含解析后的各个部分
    """
    if not id:
        return IDParseResult(
            id=id,
            prefix="",
            parent_scope=None,
            sequence=None,
            suffix=None,
            is_valid=False,
            error="ID cannot be empty"
        )

    parts = id.split("-")

    if len(parts) < 2:
        return IDParseResult(
            id=id,
            prefix=parts[0] if parts else "",
            parent_scope=None,
            sequence=None,
            suffix=None,
            is_valid=False,
            error="ID must have at least prefix and sequence"
        )

    prefix = parts[0].upper()

    # 验证前缀是否合法
    valid_prefixes = [t.value.upper() for t in SSOTType]
    if prefix not in valid_prefixes:
        return IDParseResult(
            id=id,
            prefix=prefix,
            parent_scope=None,
            sequence=None,
            suffix=None,
            is_valid=False,
            error=f"Invalid prefix: {prefix}. Must be one of {valid_prefixes}"
        )

    # 根据类型解析
    try:
        ssot_type = SSOTType(prefix.lower())
    except ValueError:
        return IDParseResult(
            id=id,
            prefix=prefix,
            parent_scope=None,
            sequence=None,
            suffix=None,
            is_valid=False,
            error=f"Unknown SSOTType: {prefix}"
        )

    category = ObjectCategory.for_type(ssot_type)

    if category == ObjectCategory.INDEPENDENT:
        # 独立型: TYPE-001
        sequence = parts[1] if len(parts) > 1 else None
        suffix = parts[2] if len(parts) > 2 else None
        return IDParseResult(
            id=id,
            prefix=prefix,
            parent_scope=None,
            sequence=sequence,
            suffix=suffix,
            is_valid=True
        )

    elif category == ObjectCategory.DIRECT_PARENT:
        # 直接父对象一致型: TYPE-FEAT-001 或 TYPE-FEAT-001-SUFFIX
        try:
            feat_idx = parts.index("FEAT")
            parent_scope = f"FEAT-{parts[feat_idx + 1]}"
            # TYPE-FEAT-001: sequence 在 feat_idx+1 位置，suffix 为 None
            # TYPE-FEAT-001-SUFFIX: sequence 在 feat_idx+1 位置，suffix 在 feat_idx+2
            sequence = parts[feat_idx + 1] if feat_idx + 1 < len(parts) else None
            suffix = "-".join(parts[feat_idx + 2:]) if feat_idx + 2 < len(parts) else None
            return IDParseResult(
                id=id,
                prefix=prefix,
                parent_scope=parent_scope,
                sequence=sequence,
                suffix=suffix,
                is_valid=True
            )
        except (ValueError, IndexError):
            return IDParseResult(
                id=id,
                prefix=prefix,
                parent_scope=None,
                sequence=None,
                suffix=None,
                is_valid=False,
                error=f"Direct parent type ID must contain FEAT-XXX: {id}"
            )

    elif category == ObjectCategory.SCOPE_BOUNDED:
        # 范围归属型: TYPE-FEAT-001-SEQ
        try:
            feat_idx = parts.index("FEAT")
            parent_scope = f"FEAT-{parts[feat_idx + 1]}"
            # TYPE-FEAT-001-SEQ: sequence 在 feat_idx+1 位置，suffix 在 feat_idx+2
            sequence = parts[feat_idx + 1] if feat_idx + 1 < len(parts) else None
            suffix = "-".join(parts[feat_idx + 2:]) if feat_idx + 2 < len(parts) else None
            return IDParseResult(
                id=id,
                prefix=prefix,
                parent_scope=parent_scope,
                sequence=sequence,
                suffix=suffix,
                is_valid=True
            )
        except (ValueError, IndexError):
            return IDParseResult(
                id=id,
                prefix=prefix,
                parent_scope=None,
                sequence=None,
                suffix=None,
                is_valid=False,
                error=f"Scope bounded type ID must contain FEAT-XXX-SEQ: {id}"
            )

    return IDParseResult(
        id=id,
        prefix=prefix,
        parent_scope=None,
        sequence=None,
        suffix=None,
        is_valid=False,
        error=f"Unknown category for type: {ssot_type}"
    )


def validate_id_format(id: str, ssot_type: Optional[SSOTType] = None) -> bool:
    """
    验证 ID 格式是否符合类型规范

    Args:
        id: SSOT ID
        ssot_type: 预期的类型，如果为 None 则只验证格式不验证类型匹配

    Returns:
        是否合法
    """
    result = parse_id(id)

    if not result.is_valid:
        return False

    if ssot_type is not None:
        # 验证类型匹配
        try:
            expected_prefix = ssot_type.value.upper()
            if result.prefix != expected_prefix:
                return False
        except ValueError:
            return False

    return True


def validate_parent_consistency(
    id: str,
    parent_id: Optional[str],
    ssot_type: SSOTType
) -> Optional[str]:
    """
    校验 parent_id 一致性

    根据对象类型使用不同规则：
    - 直接父对象一致型：parse_parent(id) == parent_id
    - 范围归属型：parse_scope(id) == resolve_scope(parent_id)

    Args:
        id: 对象 ID
        parent_id: metadata 中的 parent_id
        ssot_type: 对象类型

    Returns:
        错误信息，如果合法返回 None
    """
    category = ObjectCategory.for_type(ssot_type)

    if category == ObjectCategory.INDEPENDENT:
        # 独立型：无需校验
        return None

    # 检查是否需要 parent_id
    needs_parent = SSOTType.requires_parent(ssot_type)

    if category == ObjectCategory.DIRECT_PARENT:
        # 直接父对象一致型
        parsed_parent = parse_parent(id)

        # 如果 parent_id 为空但类型需要 parent
        if needs_parent and not parent_id:
            return f"类型 {ssot_type.value} 需要 parent_id"

        if parsed_parent != parent_id:
            return f"ID {id} 解析出 parent {parsed_parent}，但 parent_id 设置为 {parent_id}"

    elif category == ObjectCategory.SCOPE_BOUNDED:
        # 范围归属型
        parsed_scope = parse_scope(id)

        # 如果 parent_id 为空但类型需要 parent
        if needs_parent and not parent_id:
            return f"类型 {ssot_type.value} 需要 parent_id"

        if parent_id:
            resolved_scope = resolve_scope(parent_id)
            if parsed_scope != resolved_scope:
                return f"ID {id} 归属范围 {parsed_scope}，但 parent_id {parent_id} 归属范围 {resolved_scope}"

    return None
