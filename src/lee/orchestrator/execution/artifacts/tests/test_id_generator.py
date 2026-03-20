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

    def _create_src_epic_feat_chain(self, generator):
        src_id = generator.generate_id(SSOTType.SRC)
        epic_id = generator.generate_id(SSOTType.EPIC, parent_id=src_id)
        feat_id = generator.generate_id(SSOTType.FEAT, parent_id=epic_id)
        return src_id, epic_id, feat_id

    def test_init(self, generator):
        """测试初始化"""
        assert generator.root_path is not None
        assert generator._sequences is not None

    def test_generate_independent_id(self, generator):
        """测试生成 SRC 作用域独立型 ID"""
        src_id = generator.generate_id(SSOTType.SRC)
        assert src_id == "SRC-001"

        id1 = generator.generate_id(SSOTType.EPIC, parent_id=src_id)
        assert id1 == "EPIC-SRC-001-001"

        id2 = generator.generate_id(SSOTType.EPIC, parent_id=src_id)
        assert id2 == "EPIC-SRC-001-002"

    def test_generate_independent_id_different_types(self, generator):
        """测试不同独立型 ID 在同一 SRC 下独立计数"""
        src_id = generator.generate_id(SSOTType.SRC)
        epic_id = generator.generate_id(SSOTType.EPIC, parent_id=src_id)
        feat_id = generator.generate_id(SSOTType.FEAT, parent_id=epic_id)
        adr_id = generator.generate_id(SSOTType.ADR)

        assert src_id == "SRC-001"
        assert epic_id == "EPIC-SRC-001-001"
        assert feat_id == "FEAT-SRC-001-001"
        assert adr_id == "ADR-001"

    def test_generate_direct_parent_id(self, generator):
        """测试生成直接父对象一致型 ID"""
        _, _, feat_id = self._create_src_epic_feat_chain(generator)
        assert feat_id == "FEAT-SRC-001-001"

        # 生成 TECH
        tech_id = generator.generate_id(SSOTType.TECH, parent_id=feat_id)
        assert tech_id == "TECH-FEAT-SRC-001-001"

    def test_generate_direct_parent_with_suffix(self, generator):
        """测试生成带后缀的直接父对象 ID"""
        _, _, feat_id = self._create_src_epic_feat_chain(generator)
        assert feat_id == "FEAT-SRC-001-001"

        # 生成 UI (带后缀)
        ui_id = generator.generate_id(SSOTType.UI, parent_id=feat_id, suffix="01")
        assert ui_id == "UI-FEAT-SRC-001-001-01"

        task_id = generator.generate_id(SSOTType.TASK, parent_id=feat_id, suffix="01")
        assert task_id == "TASK-FEAT-SRC-001-001-01"

    def test_generate_scope_bounded_id(self, generator):
        """测试生成范围归属型 ID"""
        _, _, feat_id = self._create_src_epic_feat_chain(generator)
        testset_id = generator.generate_id(SSOTType.TESTSET, parent_id=feat_id)

        # 生成 TC (parent_id 为 TESTSET)
        tc_id = generator.generate_id(SSOTType.TC, parent_id=testset_id)
        assert tc_id == "TC-FEAT-SRC-001-001-001"

    def test_generate_multiple_scope_bounded(self, generator):
        """测试生成多个范围归属型 ID"""
        _, _, feat_id = self._create_src_epic_feat_chain(generator)
        testset_id = generator.generate_id(SSOTType.TESTSET, parent_id=feat_id)

        # 多次生成 TC
        tc1 = generator.generate_id(SSOTType.TC, parent_id=testset_id)
        tc2 = generator.generate_id(SSOTType.TC, parent_id=testset_id)
        tc3 = generator.generate_id(SSOTType.TC, parent_id=testset_id)

        assert tc1 == "TC-FEAT-SRC-001-001-001"
        assert tc2 == "TC-FEAT-SRC-001-001-002"
        assert tc3 == "TC-FEAT-SRC-001-001-003"

    def test_generate_report_id(self, generator):
        """测试生成 REPORT ID"""
        _, _, feat_id = self._create_src_epic_feat_chain(generator)

        # 生成 REPORT
        report_id = generator.generate_report_id(feat_id)
        assert report_id.startswith("REPORT-FEAT-SRC-001-001-")
        assert len(report_id) == len("REPORT-FEAT-SRC-001-001-20260101")  # YYYYMMDD

    def test_generate_without_parent_raises_error(self, generator):
        """测试缺少 parent_id 应抛出错误"""
        with pytest.raises(ValueError, match="需要 parent_id"):
            generator.generate_id(SSOTType.TECH)

    def test_generate_slug_english(self, generator):
        """测试英文 slug 生成"""
        slug = generator.generate_slug("Generate Weekly Plan")
        assert slug == "generate-weekly-plan"

    def test_generate_slug_chinese(self, generator):
        """测试中文 slug 生成保留中文"""
        slug = generator.generate_slug("生成周计划")
        assert slug == "生成周计划"

    def test_generate_slug_mixed_title_preserves_chinese(self, generator):
        """测试中英混合标题保留中文并规范分隔符"""
        slug = generator.generate_slug("完成条件：防腐层 / Fitness Function")
        assert slug == "完成条件-防腐层-fitness-function"

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
        src_id = generator.generate_id(SSOTType.SRC)
        epic_id = generator.generate_id(SSOTType.EPIC, parent_id=src_id)
        filename = generator.generate_filename(
            ssot_type=SSOTType.FEAT,
            title="Generate Weekly Plan",
            parent_id=epic_id,
            ext="md"
        )
        assert filename == "FEAT-SRC-001-001__generate-weekly-plan.md"

    def test_generate_filename_with_chinese_slug(self, generator):
        """测试中文标题生成中文文件名"""
        filename = generator.generate_filename(
            ssot_type=SSOTType.ADR,
            title="完成条件防腐层",
            ext="md",
        )
        assert filename == "ADR-001__完成条件防腐层.md"

    def test_generate_filename_with_parent(self, generator):
        """测试带 parent_id 生成文件名"""
        _, _, feat_id = self._create_src_epic_feat_chain(generator)

        filename = generator.generate_filename(
            ssot_type=SSOTType.TECH,
            title="Technical Design",
            parent_id=feat_id,
            ext="md"
        )
        assert filename.startswith("TECH-FEAT-SRC-001-001__")


class TestGetGenerator:
    """测试 get_generator 函数"""

    def test_get_generator_returns_singleton(self):
        """测试返回单例"""
        from lee.orchestrator.execution.artifacts.id_generator import get_generator

        gen1 = get_generator()
        gen2 = get_generator()

        assert gen1 is gen2
