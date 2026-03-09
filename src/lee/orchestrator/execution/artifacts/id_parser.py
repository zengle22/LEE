"""
SSOT ID Parser.

ID 格式规范 (v1.4):
- 独立顺序型: SRC-001, EPIC-001, FEAT-001, ADR-001
- Release 型: REL-1.4.0
- 单父唯一型: TECH-FEAT-001, TESTSET-FEAT-001, DEVPLAN-REL-1.4.0
- 单父多实例型:
  - UI-FEAT-001-01
  - TASK-FEAT-001-FE-01
  - TASK-DEVPLAN-REL-1.4.0-001
  - TASK-TESTPLAN-REL-1.4.0-001
- 运行/报告型:
  - REPORT-FEAT-001-20260306
  - REPORT-REL-1.4.0-TEST-001
- 范围归属型: TC-FEAT-001-001, BUG-FEAT-001-001, EVI-FEAT-001-001
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional

from .types import ObjectCategory, SSOTType


REL_VERSION_PATTERN = r"(\d+\.\d+\.\d+)"
INDEPENDENT_PATTERN = re.compile(r"^(SRC|EPIC|FEAT|ADR)-(\d{3})$")
RELEASE_PATTERN = re.compile(rf"^(REL-{REL_VERSION_PATTERN})$")
DEVPLAN_PATTERN = re.compile(rf"^(DEVPLAN)-(REL-{REL_VERSION_PATTERN})$")
TESTPLAN_PATTERN = re.compile(rf"^(TESTPLAN)-(REL-{REL_VERSION_PATTERN})$")
TASK_PLAN_PATTERN = re.compile(rf"^(TASK)-((DEVPLAN|TESTPLAN)-(REL-{REL_VERSION_PATTERN}))-(.+)$")
TASK_FEAT_PATTERN = re.compile(r"^(TASK)-(FEAT-\d{3})-(.+)$")
DIRECT_FEAT_PATTERN = re.compile(r"^(UI|TECH|TESTSET|REPORT)-(FEAT-\d{3})(?:-(.+))?$")
REPORT_REL_PATTERN = re.compile(rf"^(REPORT)-(REL-{REL_VERSION_PATTERN})-([A-Z0-9_]+)-(.+)$")
SCOPE_PATTERN = re.compile(r"^(TC|BUG|EVI)-(FEAT-\d{3})-(.+)$")


@dataclass
class IDParseResult:
    """ID 解析结果"""

    id: str
    prefix: str
    parent_scope: Optional[str]
    sequence: Optional[str]
    suffix: Optional[str]
    is_valid: bool
    error: Optional[str] = None


def _release_id_from_match(match: re.Match, group: int = 1) -> str:
    return match.group(group)


def parse_parent(id: str) -> Optional[str]:
    """从 ID 中解析直接父对象。"""
    if not id:
        return None

    if RELEASE_PATTERN.match(id) or INDEPENDENT_PATTERN.match(id):
        return None

    match = DEVPLAN_PATTERN.match(id)
    if match:
        return match.group(2)

    match = TESTPLAN_PATTERN.match(id)
    if match:
        return match.group(2)

    match = TASK_PLAN_PATTERN.match(id)
    if match:
        return match.group(2)

    match = TASK_FEAT_PATTERN.match(id)
    if match:
        return match.group(2)

    match = REPORT_REL_PATTERN.match(id)
    if match:
        return match.group(2)

    match = DIRECT_FEAT_PATTERN.match(id)
    if match:
        return match.group(2)

    return None


def parse_scope(id: str) -> Optional[str]:
    """从 ID 中解析范围归属对象。"""
    if not id:
        return None

    match = SCOPE_PATTERN.match(id)
    if match:
        return match.group(2)

    return None


def resolve_scope(parent_id: str) -> Optional[str]:
    """
    从 parent_id 解析归属范围。

    P0 阶段仍只要求范围归属型对象落在 FEAT scope 上。
    """
    if not parent_id:
        return None

    if re.match(r"^FEAT-\d{3}$", parent_id):
        return parent_id

    if re.match(r"^(TC|BUG|EVI)-(FEAT-\d{3})-", parent_id):
        return parse_scope(parent_id)

    parent = parse_parent(parent_id)
    if parent and re.match(r"^FEAT-\d{3}$", parent):
        return parent

    return None


def parse_id(id: str) -> IDParseResult:
    """解析 ID 结构。"""
    if not id:
        return IDParseResult("", "", None, None, None, False, "ID cannot be empty")

    independent_match = INDEPENDENT_PATTERN.match(id)
    if independent_match:
        prefix, sequence = independent_match.groups()
        return IDParseResult(id, prefix, None, sequence, None, True)

    release_match = RELEASE_PATTERN.match(id)
    if release_match:
        release_id = _release_id_from_match(release_match)
        return IDParseResult(id, "REL", None, release_id.split("-", 1)[1], None, True)

    match = DEVPLAN_PATTERN.match(id)
    if match:
        return IDParseResult(id, "DEVPLAN", match.group(2), match.group(3), None, True)

    match = TESTPLAN_PATTERN.match(id)
    if match:
        return IDParseResult(id, "TESTPLAN", match.group(2), match.group(3), None, True)

    match = TASK_PLAN_PATTERN.match(id)
    if match:
        return IDParseResult(id, "TASK", match.group(2), match.group(4), match.group(5), True)

    match = TASK_FEAT_PATTERN.match(id)
    if match:
        return IDParseResult(id, "TASK", match.group(2), match.group(2).split("-")[1], match.group(3), True)

    match = REPORT_REL_PATTERN.match(id)
    if match:
        return IDParseResult(id, "REPORT", match.group(2), match.group(3), f"{match.group(4)}-{match.group(5)}", True)

    match = DIRECT_FEAT_PATTERN.match(id)
    if match:
        prefix, parent_scope, suffix = match.groups()
        sequence = parent_scope.split("-")[1]
        return IDParseResult(id, prefix, parent_scope, sequence, suffix, True)

    match = SCOPE_PATTERN.match(id)
    if match:
        prefix, parent_scope, suffix = match.groups()
        sequence = parent_scope.split("-")[1]
        return IDParseResult(id, prefix, parent_scope, sequence, suffix, True)

    prefix = id.split("-", 1)[0].upper()
    return IDParseResult(
        id=id,
        prefix=prefix,
        parent_scope=None,
        sequence=None,
        suffix=None,
        is_valid=False,
        error=f"Unsupported SSOT ID format: {id}",
    )


def validate_id_format(id: str, ssot_type: Optional[SSOTType] = None) -> bool:
    """验证 ID 格式是否符合类型规范。"""
    result = parse_id(id)
    if not result.is_valid:
        return False

    if ssot_type is None:
        return True

    expected = "REL" if ssot_type == SSOTType.RELEASE else ssot_type.value.upper()
    return result.prefix == expected


def validate_parent_consistency(
    id: str,
    parent_id: Optional[str],
    ssot_type: SSOTType,
) -> Optional[str]:
    """根据对象类型校验 parent_id 一致性。"""
    category = ObjectCategory.for_type(ssot_type)

    if category == ObjectCategory.INDEPENDENT:
        if parent_id:
            return f"类型 {ssot_type.value} 不应设置 parent_id，当前为 {parent_id}"
        return None

    needs_parent = SSOTType.requires_parent(ssot_type)

    if needs_parent and not parent_id:
        return f"类型 {ssot_type.value} 需要 parent_id"

    if category == ObjectCategory.DIRECT_PARENT:
        parsed_parent = parse_parent(id)
        if parsed_parent != parent_id:
            return f"ID {id} 解析出 parent {parsed_parent}，但 parent_id 设置为 {parent_id}"
        return None

    parsed_scope = parse_scope(id)
    if parent_id:
        resolved_scope = resolve_scope(parent_id)
        if parsed_scope != resolved_scope:
            return f"ID {id} 归属范围 {parsed_scope}，但 parent_id {parent_id} 归属范围 {resolved_scope}"

    return None
