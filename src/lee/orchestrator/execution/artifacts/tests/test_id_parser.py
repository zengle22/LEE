"""
Tests for SSOT ID Parser

测试 SSOT ID 解析器的核心功能。
"""

import pytest
from lee.orchestrator.execution.artifacts.id_parser import (
    parse_parent,
    parse_scope,
    resolve_scope,
    parse_id,
    validate_id_format,
    validate_parent_consistency,
    IDParseResult,
)
from lee.orchestrator.execution.artifacts.types import SSOTType, ObjectCategory


class TestParseParent:
    """测试 parse_parent 函数"""

    def test_independent_types_return_none(self):
        """独立型类型应返回 None"""
        assert parse_parent("SRC-001") is None
        assert parse_parent("EPIC-001") is None
        assert parse_parent("FEAT-001") is None
        assert parse_parent("ADR-001") is None

    def test_direct_parent_types(self):
        """直接父对象一致型应正确解析"""
        assert parse_parent("TECH-FEAT-001") == "FEAT-001"
        assert parse_parent("TESTSET-FEAT-001") == "FEAT-001"
        assert parse_parent("UI-FEAT-001-01") == "FEAT-001"
        assert parse_parent("TASK-FEAT-001-FE-01") == "FEAT-001"
        assert parse_parent("REPORT-FEAT-001-20260306") == "FEAT-001"

    def test_scope_bounded_types_return_none(self):
        """范围归属型应返回 None (应使用 parse_scope)"""
        assert parse_parent("TC-FEAT-001-001") is None
        assert parse_parent("BUG-FEAT-001-001") is None
        assert parse_parent("EVI-FEAT-001-001") is None

    def test_invalid_id(self):
        """无效 ID 应返回 None"""
        assert parse_parent("INVALID") is None
        assert parse_parent("") is None


class TestParseScope:
    """测试 parse_scope 函数"""

    def test_independent_types_return_none(self):
        """独立型应返回 None"""
        assert parse_scope("FEAT-001") is None

    def test_direct_parent_types_return_none(self):
        """直接父对象一致型应返回 None"""
        assert parse_scope("TECH-FEAT-001") is None

    def test_scope_bounded_types(self):
        """范围归属型应正确解析"""
        assert parse_scope("TC-FEAT-001-001") == "FEAT-001"
        assert parse_scope("BUG-FEAT-001-001") == "FEAT-001"
        assert parse_scope("EVI-FEAT-001-001") == "FEAT-001"

    def test_invalid_id(self):
        """无效 ID 应返回 None"""
        assert parse_scope("INVALID") is None
        assert parse_scope("") is None


class TestResolveScope:
    """测试 resolve_scope 函数"""

    def test_feats_direct(self):
        """FEAT 直接返回"""
        assert resolve_scope("FEAT-001") == "FEAT-001"

    def test_scope_bounded_types(self):
        """范围归属型应解析到 FEAT"""
        assert resolve_scope("TC-FEAT-001-001") == "FEAT-001"
        assert resolve_scope("BUG-FEAT-001-001") == "FEAT-001"
        assert resolve_scope("EVI-FEAT-001-001") == "FEAT-001"

    def test_direct_parent_types(self):
        """直接父对象一致型应解析到 FEAT"""
        assert resolve_scope("TECH-FEAT-001") == "FEAT-001"
        assert resolve_scope("TESTSET-FEAT-001") == "FEAT-001"
        assert resolve_scope("UI-FEAT-001-01") == "FEAT-001"
        assert resolve_scope("TASK-FEAT-001-FE-01") == "FEAT-001"
        assert resolve_scope("REPORT-FEAT-001-20260306") == "FEAT-001"

    def test_empty_returns_none(self):
        """空输入应返回 None"""
        assert resolve_scope("") is None
        assert resolve_scope(None) is None


class TestParseID:
    """测试 parse_id 函数"""

    def test_independent_type(self):
        """解析独立型 ID"""
        result = parse_id("FEAT-001")
        assert result.is_valid
        assert result.prefix == "FEAT"
        assert result.parent_scope is None
        assert result.sequence == "001"

    def test_direct_parent_type(self):
        """解析直接父对象一致型 ID"""
        result = parse_id("TECH-FEAT-001")
        assert result.is_valid
        assert result.prefix == "TECH"
        assert result.parent_scope == "FEAT-001"
        assert result.sequence == "001"

    def test_direct_parent_type_with_suffix(self):
        """解析带后缀的直接父对象一致型 ID"""
        result = parse_id("UI-FEAT-001-01")
        assert result.is_valid
        assert result.prefix == "UI"
        assert result.parent_scope == "FEAT-001"
        assert result.sequence == "001"
        assert result.suffix == "01"

    def test_scope_bounded_type(self):
        """解析范围归属型 ID"""
        result = parse_id("TC-FEAT-001-001")
        assert result.is_valid
        assert result.prefix == "TC"
        assert result.parent_scope == "FEAT-001"
        assert result.sequence == "001"

    def test_invalid_prefix(self):
        """无效前缀应返回错误"""
        result = parse_id("INVALID-001")
        assert not result.is_valid
        assert "Invalid prefix" in result.error

    def test_invalid_format(self):
        """无效格式应返回错误"""
        result = parse_id("FEAT")
        assert not result.is_valid


class TestValidateIDFormat:
    """测试 validate_id_format 函数"""

    def test_valid_id_without_type(self):
        """验证有效 ID (不指定类型)"""
        assert validate_id_format("FEAT-001")
        assert validate_id_format("TC-FEAT-001-001")

    def test_valid_id_with_type(self):
        """验证有效 ID (指定类型)"""
        assert validate_id_format("FEAT-001", SSOTType.FEAT)
        assert validate_id_format("TC-FEAT-001-001", SSOTType.TC)

    def test_invalid_type_mismatch(self):
        """类型不匹配应返回 False"""
        assert not validate_id_format("FEAT-001", SSOTType.TC)

    def test_invalid_format(self):
        """无效格式应返回 False"""
        assert not validate_id_format("INVALID")
        assert not validate_id_format("")


class TestValidateParentConsistency:
    """测试 validate_parent_consistency 函数"""

    def test_independent_type_no_parent(self):
        """独立型无需 parent_id"""
        result = validate_parent_consistency("FEAT-001", None, SSOTType.FEAT)
        assert result is None

    def test_feat_parent_allows_epic(self):
        """FEAT 可选挂到 EPIC"""
        result = validate_parent_consistency("FEAT-001", "EPIC-001", SSOTType.FEAT)
        assert result is None

    def test_feat_parent_rejects_non_epic(self):
        """FEAT parent_id 若提供必须为 EPIC"""
        result = validate_parent_consistency("FEAT-001", "ADR-001", SSOTType.FEAT)
        assert result is not None
        assert "必须为 EPIC" in result

    def test_direct_parent_consistent(self):
        """直接父对象一致型应一致"""
        result = validate_parent_consistency(
            "TECH-FEAT-001", "FEAT-001", SSOTType.TECH
        )
        assert result is None

    def test_direct_parent_inconsistent(self):
        """直接父对象不一致应返回错误"""
        result = validate_parent_consistency(
            "TECH-FEAT-001", "FEAT-002", SSOTType.TECH
        )
        assert result is not None
        assert "FEAT-001" in result

    def test_scope_bounded_consistent(self):
        """范围归属型应一致"""
        result = validate_parent_consistency(
            "TC-FEAT-001-001", "TESTSET-FEAT-001", SSOTType.TC
        )
        assert result is None

    def test_scope_bounded_inconsistent(self):
        """范围归属型不一致应返回错误"""
        result = validate_parent_consistency(
            "TC-FEAT-001-001", "TESTSET-FEAT-002", SSOTType.TC
        )
        assert result is not None

    def test_requires_parent_but_missing(self):
        """需要 parent_id 但缺失应返回错误"""
        result = validate_parent_consistency("TECH-FEAT-001", None, SSOTType.TECH)
        assert result is not None
        assert "需要 parent_id" in result


class TestObjectCategory:
    """测试 ObjectCategory 分类"""

    def test_independent_types(self):
        """独立型分类"""
        assert ObjectCategory.for_type(SSOTType.SRC) == ObjectCategory.INDEPENDENT
        assert ObjectCategory.for_type(SSOTType.EPIC) == ObjectCategory.INDEPENDENT
        assert ObjectCategory.for_type(SSOTType.FEAT) == ObjectCategory.INDEPENDENT
        assert ObjectCategory.for_type(SSOTType.ADR) == ObjectCategory.INDEPENDENT

    def test_direct_parent_types(self):
        """直接父对象一致型分类"""
        assert ObjectCategory.for_type(SSOTType.TECH) == ObjectCategory.DIRECT_PARENT
        assert ObjectCategory.for_type(SSOTType.TESTSET) == ObjectCategory.DIRECT_PARENT
        assert ObjectCategory.for_type(SSOTType.UI) == ObjectCategory.DIRECT_PARENT
        assert ObjectCategory.for_type(SSOTType.TASK) == ObjectCategory.DIRECT_PARENT
        assert ObjectCategory.for_type(SSOTType.REPORT) == ObjectCategory.DIRECT_PARENT

    def test_scope_bounded_types(self):
        """范围归属型分类"""
        assert ObjectCategory.for_type(SSOTType.TC) == ObjectCategory.SCOPE_BOUNDED
        assert ObjectCategory.for_type(SSOTType.BUG) == ObjectCategory.SCOPE_BOUNDED
        assert ObjectCategory.for_type(SSOTType.EVI) == ObjectCategory.SCOPE_BOUNDED

    def test_requires_parent(self):
        """测试 requires_parent 方法"""
        # 独立型不需要
        assert not SSOTType.requires_parent(SSOTType.FEAT)
        assert not SSOTType.requires_parent(SSOTType.ADR)

        # 其他类型需要
        assert SSOTType.requires_parent(SSOTType.TECH)
        assert SSOTType.requires_parent(SSOTType.TC)
        assert SSOTType.requires_parent(SSOTType.BUG)
