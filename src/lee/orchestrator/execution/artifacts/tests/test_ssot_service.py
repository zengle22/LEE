"""
Tests for SSOT Service - SSOT 真理链校验服务测试
"""

import shutil
import tempfile
from datetime import datetime
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)
from lee.orchestrator.execution.artifacts.ssot_service import SSOTService


@pytest.fixture
def temp_artifacts_dir():
    """创建临时 artifacts 目录"""
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def artifact_manager(temp_artifacts_dir):
    """创建 ArtifactManager 实例"""
    manager = ArtifactManager(root_path=temp_artifacts_dir)
    yield manager


@pytest.fixture
def ssot_service(artifact_manager):
    """创建 SSOTService 实例"""
    return SSOTService(artifact_manager)


class TestSSOTServiceValidate:
    """测试 SSOTService.validate() 方法"""

    def test_empty_artifacts_passes_validation(self, ssot_service):
        """测试空 artifacts 列表通过校验"""
        valid, errors = ssot_service.validate()
        assert valid is True
        assert len(errors) == 0

    def test_valid_truth_chain_passes(self, ssot_service):
        """测试完整的真理链通过校验: PRD → API → CODE → TEST"""
        manager = ssot_service.manager
        run_id = "test-run-001"

        # 创建 PRD contract
        prd = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        # 创建 API contract (derived_from PRD)
        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        # 创建 implementation (implements API)
        impl = manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code content",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
            implements=[api.id],
        )

        # 创建 test plan (verifies PRD and API)
        test = manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content="Test content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            verifies=[prd.id, api.id],
        )

        # 校验应该通过
        valid, errors = ssot_service.validate(run_id=run_id)
        assert valid is True, f"Validation should pass but got errors: {errors}"
        assert len(errors) == 0

    def test_api_without_derived_from_fails(self, ssot_service):
        """测试 Rule 1: API contract 缺少 derived_from 字段"""
        manager = ssot_service.manager
        run_id = "test-run-002"

        # 创建 API contract 但没有 derived_from
        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        valid, errors = ssot_service.validate(run_id=run_id)
        assert valid is False
        assert any("missing derived_from" in err for err in errors)
        assert any(api.id in err for err in errors)

    def test_implementation_without_implements_fails(self, ssot_service):
        """测试 Rule 2: implementation 缺少 implements 字段"""
        manager = ssot_service.manager
        run_id = "test-run-003"

        # 创建 implementation 但没有 implements
        impl = manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code content",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
        )

        valid, errors = ssot_service.validate(run_id=run_id)
        assert valid is False
        assert any("missing implements" in err for err in errors)
        assert any(impl.id in err for err in errors)

    def test_test_plan_without_verifies_fails(self, ssot_service):
        """测试 Rule 3: test_plan 缺少 verifies 字段"""
        manager = ssot_service.manager
        run_id = "test-run-004"

        # 创建 test plan 但没有 verifies
        test = manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content="Test content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        valid, errors = ssot_service.validate(run_id=run_id)
        assert valid is False
        assert any("missing verifies" in err for err in errors)
        assert any(test.id in err for err in errors)

    def test_api_derived_from_nonexistent_prd_fails(self, ssot_service):
        """测试 API 的 derived_from 指向不存在的 artifact"""
        manager = ssot_service.manager
        run_id = "test-run-005"

        # 创建 API contract 指向不存在的 PRD
        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from="NONEXISTENT-001",
        )

        valid, errors = ssot_service.validate(run_id=run_id)
        assert valid is False
        assert any("not found" in err for err in errors)
        assert any(api.id in err for err in errors)

    def test_implementation_implements_nonexistent_api_fails(self, ssot_service):
        """测试 implementation 的 implements 指向不存在的 API"""
        manager = ssot_service.manager
        run_id = "test-run-006"

        # 创建 implementation 指向不存在的 API
        impl = manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code content",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
            implements=["NONEXISTENT-API-001"],
        )

        valid, errors = ssot_service.validate(run_id=run_id)
        assert valid is False
        assert any("not found" in err for err in errors)
        assert any(impl.id in err for err in errors)


class TestSSOTServiceImpact:
    """测试 SSOTService.impact() 方法"""

    def test_impact_analysis_with_dependents(self, ssot_service):
        """测试影响分析：有依赖者的情况"""
        manager = ssot_service.manager
        run_id = "test-run-impact"

        # 创建 PRD
        prd = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        # 创建 API derived_from PRD
        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        # 分析 PRD 的影响范围
        impact = ssot_service.impact(prd.id)

        assert "direct_dependents" in impact
        assert "indirect_dependents" in impact
        assert "verifiers" in impact

        # API 应该是 PRD 的直接依赖者
        assert api.id in impact["direct_dependents"]

    def test_impact_analysis_no_dependents(self, ssot_service):
        """测试影响分析：没有依赖者的情况"""
        manager = ssot_service.manager
        run_id = "test-run-impact-2"

        # 创建孤立的 artifact
        isolated = manager.create(
            artifact_type=ArtifactType.DOCUMENT,
            category="note",
            content="Isolated note",
            run_id=run_id,
            governance_kind=GovernanceKind.KNOWLEDGE,
        )

        # 分析影响范围
        impact = ssot_service.impact(isolated.id)

        assert impact["direct_dependents"] == []
        assert impact["indirect_dependents"] == []
        assert impact["verifiers"] == []

    def test_impact_analysis_nonexistent_artifact(self, ssot_service):
        """测试分析不存在的 artifact"""
        impact = ssot_service.impact("NONEXISTENT-001")

        assert impact["direct_dependents"] == []
        assert impact["indirect_dependents"] == []
        assert impact["verifiers"] == []


class TestSSOTServiceShowChain:
    """测试 SSOTService.show_chain() 方法"""

    def test_show_chain_with_derived_from(self, ssot_service):
        """测试显示真理链：derived_from 链"""
        manager = ssot_service.manager
        run_id = "test-run-chain"

        # 创建 PRD → API 链
        prd = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        # 显示 API 的真理链
        chain = ssot_service.show_chain(api.id)

        assert len(chain) == 2
        # 链应该从 PRD 到 API
        assert chain[0]["id"] == prd.id
        assert chain[1]["id"] == api.id

    def test_show_chain_nonexistent_artifact(self, ssot_service):
        """测试显示不存在的 artifact 的真理链"""
        chain = ssot_service.show_chain("NONEXISTENT-001")
        assert chain == []


class TestSSOTServiceReleaseFilter:
    """测试按 release tag 过滤的校验"""

    def test_validate_with_release_tag(self, ssot_service):
        """测试按 release tag 校验"""
        manager = ssot_service.manager

        # 创建带 release tag 的 artifacts
        prd = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD content",
            run_id="run-v1",
            governance_kind=GovernanceKind.TRANSFER,
            tags=["release:v1.0"],
        )

        api = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id="run-v1",
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
            tags=["release:v1.0"],
        )

        # 按 release tag 校验应该通过
        valid, errors = ssot_service.validate(release="release:v1.0")
        assert valid is True
        assert len(errors) == 0

    def test_validate_with_release_tag_filters_correctly(self, ssot_service):
        """测试 release tag 正确过滤"""
        manager = ssot_service.manager

        # 创建不同 release 的 artifacts
        prd_v1 = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD v1",
            run_id="run-v1",
            governance_kind=GovernanceKind.TRANSFER,
            tags=["release:v1.0"],
        )

        # v2 的 API 没有 derived_from，应该触发校验失败
        api_v2 = manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API v2",
            run_id="run-v2",
            governance_kind=GovernanceKind.TRANSFER,
            tags=["release:v2.0"],
        )

        # 只校验 v1.0 应该通过 (不包含 v2 的 API)
        valid_v1, errors_v1 = ssot_service.validate(release="release:v1.0")
        assert valid_v1 is True

        # 只校验 v2.0 应该失败 (API 没有 derived_from)
        valid_v2, errors_v2 = ssot_service.validate(release="release:v2.0")
        assert valid_v2 is False
        assert any(api_v2.id in err for err in errors_v2)
