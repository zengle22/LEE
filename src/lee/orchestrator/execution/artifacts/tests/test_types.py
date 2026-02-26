"""
Tests for artifact type definitions
"""

import pytest

from lee.orchestrator.execution.artifacts.types import (
    ArtifactType,
    ArtifactStatus,
    AdoptMode,
    ArtifactCategoryRegistry,
    Department,
)


class TestArtifactType:
    """测试 ArtifactType 枚举"""

    def test_all_types(self):
        """测试所有类型存在"""
        assert ArtifactType.CONTRACT.value == "CONTRACT"
        assert ArtifactType.DOCUMENT.value == "DOCUMENT"
        assert ArtifactType.CODE_REF.value == "CODE_REF"
        assert ArtifactType.PATCH.value == "PATCH"
        assert ArtifactType.TEST.value == "TEST"
        assert ArtifactType.HANDOVER.value == "HANDOVER"
        assert ArtifactType.LOG.value == "LOG"
        assert ArtifactType.INTERMEDIATE.value == "INTERMEDIATE"


class TestArtifactStatus:
    """测试 ArtifactStatus 枚举"""

    def test_all_statuses(self):
        """测试所有状态存在"""
        assert ArtifactStatus.DRAFT.value == "DRAFT"
        assert ArtifactStatus.ACTIVE.value == "ACTIVE"
        assert ArtifactStatus.FROZEN.value == "FROZEN"
        assert ArtifactStatus.ARCHIVED.value == "ARCHIVED"
        assert ArtifactStatus.DEPRECATED.value == "DEPRECATED"


class TestAdoptMode:
    """测试 AdoptMode 枚举"""

    def test_all_modes(self):
        """测试所有模式存在"""
        assert AdoptMode.COPY.value == "copy_mode"
        assert AdoptMode.REFERENCE.value == "reference_mode"


class TestArtifactCategoryRegistry:
    """测试 ArtifactCategoryRegistry"""

    def test_get_categories(self):
        """测试获取类型对应的类别"""
        contract_categories = ArtifactCategoryRegistry.get_categories("CONTRACT")
        assert "frozen_prd" in contract_categories
        assert "api_contract" in contract_categories

        document_categories = ArtifactCategoryRegistry.get_categories("DOCUMENT")
        assert "readme" in document_categories
        assert "usage_guide" in document_categories

    def test_is_valid_category(self):
        """测试类别验证"""
        assert ArtifactCategoryRegistry.is_valid_category("CONTRACT", "frozen_prd")
        assert ArtifactCategoryRegistry.is_valid_category("DOCUMENT", "readme")
        assert not ArtifactCategoryRegistry.is_valid_category("CONTRACT", "readme")
        assert not ArtifactCategoryRegistry.is_valid_category("INVALID", "test")

    def test_all_categories(self):
        """测试获取所有类别"""
        all_cats = ArtifactCategoryRegistry.all_categories()
        assert "frozen_prd" in all_cats
        assert "readme" in all_cats
        assert "implementation" in all_cats
        assert len(all_cats) > 0


class TestDepartment:
    """测试 Department 枚举"""

    def test_all_departments(self):
        """测试所有部门存在"""
        assert Department.PM.value == "pm"
        assert Department.BACKEND.value == "backend"
        assert Department.FRONTEND.value == "frontend"
        assert Department.QA.value == "qa"
        assert Department.DEVOPS.value == "devops"
        assert Department.DATA.value == "data"
        assert Department.DESIGN.value == "design"
