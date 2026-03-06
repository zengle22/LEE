"""
Tests for SSOT ID Generator

测试 SSOT ID 生成器的核心功能。
"""

import pytest
import tempfile
import shutil
from pathlib import Path

from lee.orchestrator.execution.artifacts.id_generator import SSOTIDGenerator
from lee.orchestrator.execution.artifacts.types import SSOTType


@pytest.fixture
def temp_root():
    """创建临时根目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def generator(temp_root):
    """创建 ID 生成器实例"""
    return SSOTIDGenerator(temp_root)


class TestSSOTIDGenerator:
    """测试 SSOTIDGenerator 类"""

    def test_init(self, generator):
        """测试初始化"""
        assert generator.root_path is not None
        assert generator._sequences is not None

    def test_generate_independent_id(self, generator):
        """测试生成独立型 ID"""
        # 首次生成
        id1 = generator.generate_id(SSOTType.FEAT)
        assert id1 == "FEAT-001"

        # 再次生成应该递增
        id2 = generator.generate_id(SSOTType.FEAT)
        assert id2 == "FEAT-002"

    def test_generate_independent_id_different_types(self, generator):
        """测试不同独立型 ID 独立计数"""
        feat_id = generator.generate_id(SSOTType.FEAT)
        epic_id = generator.generate_id(SSOTType.EPIC)
        src_id = generator.generate_id(SSOTType.SRC)
        adr_id = generator.generate_id(SSOTType.ADR)

        assert feat_id == "FEAT-001"
        assert epic_id == "EPIC-001"
        assert src_id == "SRC-001"
        assert adr_id == "ADR-001"

    def test_generate_direct_parent_id(self, generator):
        """测试生成直接父对象一致型 ID"""
        # 需要先有 FEAT
        feat_id = generator.generate_id(SSOTType.FEAT)
        assert feat_id == "FEAT-001"

        # 生成 TECH
        tech_id = generator.generate_id(SSOTType.TECH, parent_id="FEAT-001")
        assert tech_id == "TECH-FEAT-001-001"

    def test_generate_direct_parent_with_suffix(self, generator):
        """测试生成带后缀的直接父对象 ID"""
        feat_id = generator.generate_id(SSOTType.FEAT)
        assert feat_id == "FEAT-001"

        # 生成 UI (带后缀)
        ui_id = generator.generate_id(SSOTType.UI, parent_id="FEAT-001", suffix="01")
        assert ui_id == "UI-FEAT-001-01"

        # 生成 TASK (带 FE 后缀)
        task_id = generator.generate_id(SSOTType.TASK, parent_id="FEAT-001", suffix="FE-01")
        assert task_id == "TASK-FEAT-001-FE-01"

    def test_generate_scope_bounded_id(self, generator):
        """测试生成范围归属型 ID"""
        # 需要先有 FEAT 和 TESTSET
        feat_id = generator.generate_id(SSOTType.FEAT)
        testset_id = generator.generate_id(SSOTType.TESTSET, parent_id="FEAT-001")

        # 生成 TC (parent_id 为 TESTSET)
        tc_id = generator.generate_id(SSOTType.TC, parent_id="TESTSET-FEAT-001")
        assert tc_id == "TC-FEAT-001-001"

    def test_generate_multiple_scope_bounded(self, generator):
        """测试生成多个范围归属型 ID"""
        feat_id = generator.generate_id(SSOTType.FEAT)
        testset_id = generator.generate_id(SSOTType.TESTSET, parent_id="FEAT-001")

        # 多次生成 TC
        tc1 = generator.generate_id(SSOTType.TC, parent_id="TESTSET-FEAT-001")
        tc2 = generator.generate_id(SSOTType.TC, parent_id="TESTSET-FEAT-001")
        tc3 = generator.generate_id(SSOTType.TC, parent_id="TESTSET-FEAT-001")

        assert tc1 == "TC-FEAT-001-001"
        assert tc2 == "TC-FEAT-001-002"
        assert tc3 == "TC-FEAT-001-003"

    def test_generate_report_id(self, generator):
        """测试生成 REPORT ID"""
        feat_id = generator.generate_id(SSOTType.FEAT)

        # 生成 REPORT
        report_id = generator.generate_report_id("FEAT-001")
        assert report_id.startswith("REPORT-FEAT-001-")
        assert len(report_id) == len("REPORT-FEAT-001-20260101")  # YYYYMMDD

    def test_generate_without_parent_raises_error(self, generator):
        """测试缺少 parent_id 应抛出错误"""
        with pytest.raises(ValueError, match="需要 parent_id"):
            generator.generate_id(SSOTType.TECH)

    def test_generate_slug_english(self, generator):
        """测试英文 slug 生成"""
        slug = generator.generate_slug("Generate Weekly Plan")
        assert slug == "generate-weekly-plan"

    def test_generate_slug_chinese(self, generator):
        """测试中文 slug 生成 (如果 pinyin 库可用)"""
        slug = generator.generate_slug("生成周计划")
        assert slug
        assert slug == slug.lower()
        assert all(c.isalnum() or c == "-" for c in slug)

    def test_generate_slug_truncation(self, generator):
        """测试 slug 截断"""
        long_title = "a" * 60
        slug = generator.generate_slug(long_title)
        assert len(slug) <= 50

    def test_generate_slug_explicit(self, generator):
        """测试显式 slug"""
        slug = generator.generate_slug("Title", explicit_slug="custom-slug")
        assert slug == "custom-slug"

    def test_generate_slug_fallback(self, generator):
        """测试空标题回退"""
        slug = generator.generate_slug("")
        assert slug == "untitled"

    def test_generate_filename(self, generator):
        """测试生成完整文件名"""
        filename = generator.generate_filename(
            ssot_type=SSOTType.FEAT,
            title="Generate Weekly Plan",
            ext="md"
        )
        assert filename == "FEAT-001__generate-weekly-plan.md"

    def test_generate_filename_with_parent(self, generator):
        """测试带 parent_id 生成文件名"""
        # 先创建 FEAT
        generator.generate_id(SSOTType.FEAT)

        filename = generator.generate_filename(
            ssot_type=SSOTType.TECH,
            title="Technical Design",
            parent_id="FEAT-001",
            ext="md"
        )
        assert filename.startswith("TECH-FEAT-001-001__")


class TestGetGenerator:
    """测试 get_generator 函数"""

    def test_get_generator_returns_singleton(self):
        """测试返回单例"""
        from lee.orchestrator.execution.artifacts.id_generator import get_generator

        gen1 = get_generator()
        gen2 = get_generator()

        assert gen1 is gen2
