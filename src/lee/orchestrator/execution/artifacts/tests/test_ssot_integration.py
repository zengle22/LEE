"""
Tests for SSOT Integration - SSOT 集成测试
"""

import shutil
import tempfile
import yaml
from datetime import datetime
from pathlib import Path

import pytest

from lee.orchestrator.execution.artifacts import (
    ArtifactManager,
    ArtifactType,
    GovernanceKind,
)
from lee.orchestrator.execution.artifacts.integration import (
    GateArtifactHandler,
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
def gate_handler(temp_artifacts_dir):
    """创建 GateArtifactHandler 实例"""
    # 直接使用 temp_artifacts_dir 作为 project_root
    # GateArtifactHandler 会检测到这是 .artifacts 目录并直接使用
    return GateArtifactHandler(project_root=temp_artifacts_dir)


@pytest.fixture
def artifact_manager(gate_handler):
    """创建 ArtifactManager 实例 (与 gate_handler 共享同一个实例)"""
    yield gate_handler.manager


class TestGateSSOTIntegration:
    """测试 Gate 与 SSOT 的集成"""

    def test_approve_gate_artifacts_with_valid_ssot(self, gate_handler, artifact_manager):
        """测试 SSOT 校验通过时 Gate 审批成功"""
        run_id = "test-run-valid"

        # 创建完整的真理链
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        impl = artifact_manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
            implements=[api.id],
        )

        test = artifact_manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content="Test",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            verifies=[prd.id, api.id],
        )

        # Gate 审批应该成功
        result = gate_handler.approve_gate_artifacts(
            run_id=run_id,
            gate_id="GATE-001",
            enforce=True,  # 启用 enforce 模式
        )

        assert result["ssot_validated"] is True
        assert result["ssot_errors"] is None
        assert result["frozen_count"] > 0

    def test_approve_gate_artifacts_with_invalid_ssot_enforce_mode(self, gate_handler, artifact_manager):
        """测试 SSOT 校验失败时 Gate 审批失败 (enforce 模式)"""
        run_id = "test-run-invalid"

        # 创建无效的真理链：API 没有 derived_from
        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        # enforce 模式下应该抛出异常
        with pytest.raises(Exception, match="SSOT validation failed"):
            gate_handler.approve_gate_artifacts(
                run_id=run_id,
                gate_id="GATE-002",
                enforce=True,
            )

    def test_approve_gate_artifacts_with_invalid_ssot_warning_mode(self, gate_handler, artifact_manager):
        """测试 SSOT 校验失败时 Gate 审批仍成功 (warning 模式)"""
        run_id = "test-run-warning"

        # 创建无效的真理链：API 没有 derived_from
        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API content",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        # warning 模式下不应该抛出异常
        result = gate_handler.approve_gate_artifacts(
            run_id=run_id,
            gate_id="GATE-003",
            enforce=False,  # warning 模式
        )

        # 应该返回校验错误信息
        assert result["ssot_validated"] is False
        assert result["ssot_errors"] is not None
        assert any("missing derived_from" in err for err in result["ssot_errors"])

    def test_approve_gate_artifacts_updates_manifest(self, gate_handler, artifact_manager):
        """测试 Gate 审批更新 manifest"""
        run_id = "test-run-manifest"

        # 创建有效的真理链
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        # Gate 审批
        result = gate_handler.approve_gate_artifacts(
            run_id=run_id,
            gate_id="GATE-004",
            enforce=True,
        )

        # 验证 manifest 被更新
        manifest = gate_handler.manifest_manager.get(run_id)
        assert manifest is not None
        assert manifest.properties is not None
        assert "approved_gates" in manifest.properties

        gate_info = manifest.properties["approved_gates"][0]
        assert gate_info["gate_id"] == "GATE-004"
        assert gate_info["ssot_validated"] is True


class TestSSOTServiceWithGate:
    """测试 SSOT 服务与 Gate 的集成"""

    def test_ssot_service_detects_broken_chain(self, artifact_manager):
        """测试 SSOT 服务检测断链"""
        service = SSOTService(artifact_manager)
        run_id = "test-run-broken"

        # 创建断链：只有 API 没有 PRD
        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        valid, errors = service.validate(run_id=run_id)
        assert valid is False
        assert any("missing derived_from" in err for err in errors)

    def test_ssot_service_full_chain_passes(self, artifact_manager):
        """测试 SSOT 服务完整链条通过校验"""
        service = SSOTService(artifact_manager)
        run_id = "test-run-full"

        # 创建完整链条
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        impl = artifact_manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
            implements=[api.id],
        )

        test = artifact_manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content="Test",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            verifies=[prd.id, api.id],
        )

        valid, errors = service.validate(run_id=run_id)
        assert valid is True
        assert len(errors) == 0


class TestEndToEndTruthChain:
    """端到端真理链测试"""

    def test_full_truth_chain_workflow(self, gate_handler, artifact_manager):
        """测试完整的工作流真理链：PRD → API → CODE → TEST"""
        run_id = "test-run-e2e"
        service = SSOTService(artifact_manager)

        # Step 1: PM 创建 PRD
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content=yaml.dump({"title": "Feature PRD", "description": "PRD description"}),
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            title="Feature PRD",
        )

        # Step 2: Backend 创建 API (derived_from PRD)
        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content=yaml.dump({"title": "Feature API", "paths": ["/api/v1/feature"]}),
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
            title="Feature API",
        )

        # Step 3: Dev 创建实现 (implements API)
        impl = artifact_manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="def feature(): pass",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
            implements=[api.id],
            title="Feature Implementation",
        )

        # Step 4: QA 创建测试计划 (verifies PRD and API)
        test = artifact_manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content=yaml.dump({"test_cases": ["test_feature_basic", "test_feature_edge_cases"]}),
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            verifies=[prd.id, api.id],
            title="Feature Test Plan",
        )

        # 验证真理链完整性
        valid, errors = service.validate(run_id=run_id)
        assert valid is True, f"真理链校验应该通过，错误：{errors}"

        # Gate 审批应该成功
        result = gate_handler.approve_gate_artifacts(
            run_id=run_id,
            gate_id="GATE-E2E",
            enforce=True,
        )

        assert result["ssot_validated"] is True
        assert result["frozen_count"] == 4  # 所有 4 个 artifacts 都被冻结

    def test_broken_chain_workflow_api_missing_prd(self, gate_handler, artifact_manager):
        """测试断链工作流：API 缺少 PRD"""
        run_id = "test-run-broken-api"
        service = SSOTService(artifact_manager)

        # 只创建 API，没有 PRD
        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        # 校验应该失败
        valid, errors = service.validate(run_id=run_id)
        assert valid is False

        # Gate 审批应该失败 (enforce 模式)
        with pytest.raises(Exception, match="SSOT validation failed"):
            gate_handler.approve_gate_artifacts(
                run_id=run_id,
                gate_id="GATE-BROKEN",
                enforce=True,
            )

    def test_broken_chain_workflow_code_missing_api(self, gate_handler, artifact_manager):
        """测试断链工作流：代码实现缺少 API"""
        run_id = "test-run-broken-code"
        service = SSOTService(artifact_manager)

        # 创建 PRD 和 API
        prd = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="prd_contract",
            content="PRD",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
        )

        api = artifact_manager.create(
            artifact_type=ArtifactType.CONTRACT,
            category="api_contract",
            content="API",
            run_id=run_id,
            governance_kind=GovernanceKind.TRANSFER,
            derived_from=prd.id,
        )

        # 创建代码实现但没有 implements
        impl = artifact_manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
        )

        # 校验应该失败 (缺少 implements)
        valid, errors = service.validate(run_id=run_id)
        assert valid is False
        assert any("missing implements" in err for err in errors)


class TestGateEnforceVsWarning:
    """测试 Gate enforce 模式与 warning 模式的区别"""

    def test_enforce_mode_blocks_invalid_ssot(self, gate_handler, artifact_manager):
        """测试 enforce 模式阻断无效 SSOT"""
        run_id = "test-enforce"

        # 创建无效的 artifact
        artifact_manager.create(
            artifact_type=ArtifactType.CODE_REF,
            category="implementation",
            content="Code without implements",
            run_id=run_id,
            governance_kind=GovernanceKind.DELIVERABLE,
        )

        # enforce 模式应该抛出异常
        with pytest.raises(Exception) as exc_info:
            gate_handler.approve_gate_artifacts(
                run_id=run_id,
                gate_id="GATE-ENFORCE",
                enforce=True,
            )

        assert "SSOT validation failed" in str(exc_info.value)

    def test_warning_mode_allows_invalid_ssot(self, gate_handler, artifact_manager):
        """测试 warning 模式允许无效 SSOT 通过"""
        run_id = "test-warning"

        # 创建无效的 artifact
        artifact_manager.create(
            artifact_type=ArtifactType.TEST,
            category="test_plan",
            content="Test without verifies",
            run_id=run_id,
            governance_kind=GovernanceKind.EVIDENCE,
        )

        # warning 模式不应该抛出异常
        result = gate_handler.approve_gate_artifacts(
            run_id=run_id,
            gate_id="GATE-WARNING",
            enforce=False,
        )

        # 应该返回错误信息但不阻断
        assert result["ssot_validated"] is False
        assert result["ssot_errors"] is not None
        # 但没有抛出异常
