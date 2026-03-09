"""
P1 功能集成测试

测试三个 P1 功能:
1. ContractDiscovery 集成
2. ToolGuard 启用
3. Gate 下游检查
"""

import asyncio
import os
import json
import tempfile
import uuid
import shutil
import pytest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch, PropertyMock
from datetime import datetime


_WORKSPACE_TMP_ROOT = Path(__file__).resolve().parent.parent / "test-temp-p1"
_WORKSPACE_TMP_ROOT.mkdir(parents=True, exist_ok=True)


def _make_local_temp_dir(prefix: str) -> str:
    path = _WORKSPACE_TMP_ROOT / f"{prefix}{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return str(path)


# ========================================================================
# Feature 1: ContractDiscovery 单元测试
# ========================================================================

class TestContractDiscovery:
    """ContractDiscovery 模块单元测试"""

    def setup_method(self):
        self.temp_dir = _make_local_temp_dir("p1-contract-")
        # 创建 spec-global 目录结构
        spec_dir = Path(self.temp_dir) / "spec-global" / "departments" / "dev" / "contracts"
        spec_dir.mkdir(parents=True)

        # 创建一个测试契约文件
        contract = {
            "contract_type": "frozen-detailed-prd",
            "contract_version": "1.0.0",
            "metadata": {
                "contract_id": "FDPRD-20260213-001",
                "status": "frozen",
                "is_frozen": True,
                "product_name": "test-product",
                "created_date": "2026-02-13T00:00:00",
            },
            "product_overview": {"product_name": "test-product"},
            "functional_details": {"features": [{"name": "f1"}, {"name": "f2"}]},
        }
        contract_file = spec_dir / "prd-contract.json"
        with open(contract_file, 'w') as f:
            json.dump(contract, f)

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_discover_all_finds_contracts(self):
        """验证自动发现 spec-global 中的契约文件"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        index = discovery.discover_all()

        assert len(index.contracts) >= 1
        assert index.last_scan_time is not None

    def test_discover_all_caches_results(self):
        """验证缓存逻辑：第二次调用不会重新扫描"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        index1 = discovery.discover_all()
        scan_time_1 = index1.last_scan_time

        index2 = discovery.discover_all()
        assert index2.last_scan_time == scan_time_1  # 缓存，不重新扫描

    def test_discover_all_force_refresh(self):
        """验证强制刷新会重新扫描"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        discovery.discover_all()

        import time
        time.sleep(0.01)
        index2 = discovery.discover_all(force_refresh=True)
        assert index2.last_scan_time is not None

    def test_find_frozen_contracts(self):
        """验证查找冻结契约"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        discovery.discover_all()

        frozen = discovery.find_frozen_contracts()
        assert len(frozen) >= 1
        assert frozen[0].is_frozen is True

    def test_validate_workflow_inputs_unknown_workflow(self):
        """验证未知工作流返回空缺失列表"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        discovery.discover_all()

        is_complete, missing = discovery.validate_workflow_inputs("unknown_workflow")
        assert is_complete is True
        assert missing == []

    def test_find_contracts_by_product(self):
        """验证按产品查找契约"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        discovery.discover_all()

        result = discovery.find_contracts_by_product("test-product")
        assert len(result) >= 1
        assert result[0].product_name == "test-product"

    def test_contract_info_to_dict(self):
        """验证 ContractInfo 序列化"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        discovery = ContractDiscovery(self.temp_dir)
        discovery.discover_all()

        contracts = list(discovery.index.contracts.values())
        assert len(contracts) >= 1
        d = contracts[0].to_dict()
        assert "contract_id" in d
        assert "contract_type" in d
        assert "status" in d

    def test_empty_directory(self):
        """验证空目录不报错"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery

        empty_dir = _make_local_temp_dir("p1-empty-")
        try:
            discovery = ContractDiscovery(empty_dir)
            index = discovery.discover_all()
            assert len(index.contracts) == 0
        finally:
            shutil.rmtree(empty_dir, ignore_errors=True)


# ========================================================================
# Feature 2: ToolGuard 单元测试
# ========================================================================

class TestTokenManagerAndToolGuard:
    """TokenManager + ToolGuard 单元测试"""

    def setup_method(self):
        self.temp_dir = _make_local_temp_dir("p1-token-")

    def teardown_method(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_issue_token(self):
        """验证令牌签发"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
            permissions=["read", "write"],
        )

        assert token.token_id.startswith("TKN-")
        assert token.run_id == "RUN-001"
        assert token.step_id == "step_1"
        assert token.agent_id == "agent.dev.coder"
        assert token.permissions == ["read", "write"]
        assert token.signature is not None
        assert not token.revoked

    def test_validate_token_success(self):
        """验证令牌验证成功"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
        )

        valid, reason = tm.validate_token(token.token_id)
        assert valid is True
        assert reason is None

    def test_validate_token_step_mismatch(self):
        """验证令牌步骤不匹配时拒绝"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
        )

        valid, reason = tm.validate_token(token.token_id, step_id="step_2")
        assert valid is False
        assert "step_1" in reason

    def test_validate_token_permission_denied(self):
        """验证令牌权限不足时拒绝"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
            permissions=["read"],
        )

        valid, reason = tm.validate_token(token.token_id, required_permission="execute")
        assert valid is False
        assert "execute" in reason

    def test_revoke_token(self):
        """验证令牌撤销"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
        )

        result = tm.revoke_token(token.token_id, reason="step_completed")
        assert result is True

        valid, reason = tm.validate_token(token.token_id)
        assert valid is False
        assert "revoked" in reason

    def test_load_token(self):
        """验证令牌加载"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
        )

        loaded = tm.load_token(token.token_id)
        assert loaded is not None
        assert loaded.token_id == token.token_id
        assert loaded.step_id == "step_1"

    def test_load_nonexistent_token(self):
        """验证加载不存在的令牌返回 None"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        result = tm.load_token("TKN-NONEXISTENT")
        assert result is None

    def test_encode_decode_token(self):
        """验证令牌编解码"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
        )

        encoded = tm.encode_token_for_context(token)
        assert encoded.startswith("WORKFLOW_TOKEN:")

        decoded_id = tm.decode_token_from_context(encoded)
        assert decoded_id == token.token_id

    def test_get_active_tokens(self):
        """验证获取活跃令牌"""
        from lee.orchestrator.core.token_manager import TokenManager

        tm = TokenManager(self.temp_dir)
        t1 = tm.issue_token(run_id="RUN-001", step_id="step_1", agent_id="a1")
        t2 = tm.issue_token(run_id="RUN-001", step_id="step_2", agent_id="a2")

        active = tm.get_active_tokens()
        assert len(active) == 2

        active_step1 = tm.get_active_tokens(step_id="step_1")
        assert len(active_step1) == 1
        assert active_step1[0].token_id == t1.token_id

    def test_tool_guard_check_read_access(self):
        """验证 ToolGuard 读权限检查"""
        from lee.orchestrator.core.token_manager import TokenManager, ToolGuard

        tm = TokenManager(self.temp_dir)
        guard = ToolGuard(tm)

        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
            permissions=["read"],
        )

        # 读操作应该允许
        allowed, reason = guard.check_tool_access(token.token_id, "Read")
        assert allowed is True

        # 写操作应该拒绝
        allowed, reason = guard.check_tool_access(token.token_id, "Write")
        assert allowed is False

    def test_tool_guard_check_execute_access(self):
        """验证 ToolGuard 执行权限检查"""
        from lee.orchestrator.core.token_manager import TokenManager, ToolGuard

        tm = TokenManager(self.temp_dir)
        guard = ToolGuard(tm)

        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
            permissions=["read", "write", "execute"],
        )

        allowed, reason = guard.check_tool_access(token.token_id, "Bash")
        assert allowed is True

    def test_tool_guard_get_allowed_tools(self):
        """验证 ToolGuard 获取允许的工具列表"""
        from lee.orchestrator.core.token_manager import TokenManager, ToolGuard

        tm = TokenManager(self.temp_dir)
        guard = ToolGuard(tm)

        token = tm.issue_token(
            run_id="RUN-001",
            step_id="step_1",
            agent_id="agent.dev.coder",
            permissions=["read", "write"],
        )

        allowed = guard.get_allowed_tools(token.token_id)
        assert "Read" in allowed
        assert "Write" in allowed
        assert "Bash" not in allowed

    def test_tool_guard_nonexistent_token(self):
        """验证 ToolGuard 对不存在令牌的处理"""
        from lee.orchestrator.core.token_manager import TokenManager, ToolGuard

        tm = TokenManager(self.temp_dir)
        guard = ToolGuard(tm)

        allowed, reason = guard.check_tool_access("TKN-FAKE", "Read")
        assert allowed is False
        assert "not found" in reason


# ========================================================================
# Feature 3: GateEngine 单元测试
# ========================================================================

class TestGateEngine:
    """GateEngine 门禁规则引擎单元测试"""

    def _make_gate_ir(self, mandatory_rules=None, threshold_rules=None):
        """构造 GateIR 测试数据"""
        from lee.orchestrator.ir.models import GateIR, GateRuleIR, RuleType, RuleSeverity

        mandatory = []
        if mandatory_rules:
            for rule in mandatory_rules:
                mandatory.append(GateRuleIR(
                    rule_id=rule["id"],
                    name=rule.get("name", rule["id"]),
                    rule_type=RuleType.MANDATORY,
                    rule_expression=rule["expression"],
                    severity=RuleSeverity.BLOCKER,
                    exemption_allowed=False,
                    validation_method=rule.get("method", "default"),
                ))

        threshold = []
        if threshold_rules:
            for rule in threshold_rules:
                threshold.append(GateRuleIR(
                    rule_id=rule["id"],
                    name=rule.get("name", rule["id"]),
                    rule_type=RuleType.THRESHOLD,
                    rule_expression=rule["expression"],
                    severity=RuleSeverity.MAJOR,
                    exemption_allowed=True,
                    validation_method=rule.get("method", "default"),
                ))

        return GateIR(
            gate_id="test_gate",
            name="Test Gate",
            description="Test gate for unit tests",
            mandatory_criteria=mandatory,
            threshold_criteria=threshold,
        )

    def test_evaluate_gate_all_pass(self):
        """验证所有规则通过时判定 PASS"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": "tests_passed"},
            ]
        )

        result = engine.evaluate_gate(gate_ir, {"tests_passed": True})
        assert result.verdict == GateVerdict.PASS
        assert result.mandatory_passed is True

    def test_evaluate_gate_mandatory_fail(self):
        """验证 mandatory 规则失败时判定 FAIL"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": "tests_passed"},
                {"id": "r2", "expression": "code_reviewed"},
            ]
        )

        result = engine.evaluate_gate(
            gate_ir,
            {"tests_passed": True, "code_reviewed": False}
        )
        assert result.verdict == GateVerdict.FAIL
        assert result.mandatory_passed is False
        assert "r2" in result.failed_rules

    def test_evaluate_gate_numeric_compare(self):
        """验证数值比较评估器"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": "coverage >= 80", "method": "numeric_compare"},
            ]
        )

        # 覆盖率 85 >= 80 → 通过
        result = engine.evaluate_gate(gate_ir, {"coverage": 85})
        assert result.verdict == GateVerdict.PASS

        # 覆盖率 70 < 80 → 失败
        result = engine.evaluate_gate(gate_ir, {"coverage": 70})
        assert result.verdict == GateVerdict.FAIL

    def test_evaluate_gate_file_exists(self):
        """验证文件存在评估器"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()

        # 使用一个一定存在的文件路径
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": __file__, "method": "file_exists"},
            ]
        )

        result = engine.evaluate_gate(gate_ir, {})
        assert result.verdict == GateVerdict.PASS

    def test_evaluate_gate_boolean(self):
        """验证布尔值评估器"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": "approved", "method": "boolean"},
            ]
        )

        result = engine.evaluate_gate(gate_ir, {"approved": "yes"})
        assert result.verdict == GateVerdict.PASS

        result = engine.evaluate_gate(gate_ir, {"approved": "false"})
        assert result.verdict == GateVerdict.FAIL

    def test_evaluate_gate_result_serialization(self):
        """验证评估结果可序列化"""
        from lee.orchestrator.execution.gate_engine import GateEngine

        engine = GateEngine()
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": "ok"},
            ]
        )

        result = engine.evaluate_gate(gate_ir, {"ok": True})
        d = result.to_dict()

        assert "gate_id" in d
        assert "verdict" in d
        assert "mandatory_passed" in d
        assert "rule_results" in d
        assert isinstance(d["rule_results"], list)

    def test_evaluate_gate_empty_rules(self):
        """验证没有规则时判定 PASS"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()
        gate_ir = self._make_gate_ir()

        result = engine.evaluate_gate(gate_ir, {})
        assert result.verdict == GateVerdict.PASS

    def test_evaluate_gate_pattern_not_contains(self):
        """验证 pattern_not_contains 评估器"""
        from lee.orchestrator.execution.gate_engine import GateEngine, GateVerdict

        engine = GateEngine()
        gate_ir = self._make_gate_ir(
            mandatory_rules=[
                {"id": "r1", "expression": "output NOT_CONTAINS mock,fake", "method": "pattern_not_contains"},
            ]
        )

        # 不包含禁止词 → 通过
        result = engine.evaluate_gate(gate_ir, {"output": "real implementation code"})
        assert result.verdict == GateVerdict.PASS

        # 包含禁止词 → 失败
        result = engine.evaluate_gate(gate_ir, {"output": "using mock data"})
        assert result.verdict == GateVerdict.FAIL


# ========================================================================
# 集成测试: Orchestrator 初始化
# ========================================================================

class TestOrchestratorP1Init:
    """验证 Orchestrator 初始化时创建了 P1 组件"""

    def test_orchestrator_has_contract_discovery(self):
        """验证 Orchestrator 有 contract_discovery 属性"""
        from lee.orchestrator.core.contract_discovery import ContractDiscovery
        from lee.orchestrator.core.token_manager import TokenManager, ToolGuard
        from lee.orchestrator.execution.gate_engine import GateEngine

        # 用 mock store 创建 Orchestrator
        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        assert hasattr(orch, 'contract_discovery')
        assert isinstance(orch.contract_discovery, ContractDiscovery)

    def test_orchestrator_has_token_manager(self):
        """验证 Orchestrator 有 token_manager 和 tool_guard 属性"""
        from lee.orchestrator.core.token_manager import TokenManager, ToolGuard

        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        assert hasattr(orch, 'token_manager')
        assert isinstance(orch.token_manager, TokenManager)
        assert hasattr(orch, 'tool_guard')
        assert isinstance(orch.tool_guard, ToolGuard)

    def test_orchestrator_has_gate_engine(self):
        """验证 Orchestrator 有 gate_engine 属性"""
        from lee.orchestrator.execution.gate_engine import GateEngine

        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        assert hasattr(orch, 'gate_engine')
        assert isinstance(orch.gate_engine, GateEngine)


# ========================================================================
# 集成测试: _find_gate_ir
# ========================================================================

class TestFindGateIR:
    """验证 _find_gate_ir 辅助方法"""

    def test_find_gate_ir_returns_none_when_no_template(self):
        """验证没有 template 时返回 None"""
        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        result = orch._find_gate_ir(None, "gate_1")
        assert result is None

    def test_find_gate_ir_returns_none_when_no_match(self):
        """验证没有匹配 gate_id 时返回 None"""
        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        # 模拟 template
        mock_template = MagicMock()
        mock_step = MagicMock()
        mock_step.gate_id = "OTHER_GATE"
        mock_step.gate = None
        mock_template.steps = [mock_step]

        result = orch._find_gate_ir(mock_template, "gate_1")
        assert result is None

    def test_find_gate_ir_returns_gate_when_match(self):
        """验证匹配 gate_id 时返回 gate"""
        mock_store = MagicMock()
        from lee.orchestrator.execution.orchestrator import Orchestrator
        orch = Orchestrator(store=mock_store, project_root="/tmp/test_project")

        mock_gate = MagicMock()
        mock_step = MagicMock()
        mock_step.gate_id = "gate_1"
        mock_step.gate = mock_gate
        mock_template = MagicMock()
        mock_template.steps = [mock_step]

        result = orch._find_gate_ir(mock_template, "gate_1")
        assert result == mock_gate


# ========================================================================
# Feature 4: v3.6 ArtifactManager 集成测试
# ========================================================================

class TestOrchestratorArtifactRecording:
    """v3.6: 验证 Orchestrator 产出物记录功能"""

    def setup_method(self):
        """创建临时目录和测试文件"""
        import os
        self.temp_dir = _make_local_temp_dir("p1-artifact-")
        self.test_files = []

        # 创建测试文件
        self.test_patch_file = Path(self.temp_dir) / "test.patch"
        self.test_patch_file.write_text("@@ test patch @@")
        self.test_files.append(self.test_patch_file)

        self.test_report_file = Path(self.temp_dir) / "test_report.json"
        self.test_report_file.write_text('{"passed": 10, "failed": 0}')
        self.test_files.append(self.test_report_file)

        self.test_coverage_file = Path(self.temp_dir) / "coverage.xml"
        self.test_coverage_file.write_text("<coverage>80%</coverage>")
        self.test_files.append(self.test_coverage_file)

        self.test_review_file = Path(self.temp_dir) / "review.md"
        self.test_review_file.write_text("# Code Review\nLGTM")
        self.test_files.append(self.test_review_file)

    def teardown_method(self):
        """清理临时目录"""
        import shutil
        if Path(self.temp_dir).exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_orchestrator_has_artifact_manager(self):
        """验证 Orchestrator 初始化时创建了 artifact_manager 和 manifest_manager"""
        from lee.orchestrator.execution.artifacts.manager import ArtifactManager
        from lee.orchestrator.execution.artifacts.manifest import ManifestManager
        from lee.orchestrator.execution.orchestrator import Orchestrator

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        assert hasattr(orch, 'artifact_manager')
        assert isinstance(orch.artifact_manager, ArtifactManager)

        assert hasattr(orch, 'manifest_manager')
        assert isinstance(orch.manifest_manager, ManifestManager)

    def test_record_step_artifacts_with_patch_file(self):
        """验证记录 patch 文件产出物"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        workflow_id = "test-workflow-001"
        step_id = "implement"

        # 模拟包含 patch_file 的输出
        output = {
            "patch_file": str(self.test_patch_file),
            "status": "completed"
        }

        # Mock artifact_manager.adopt 以避免实际文件操作
        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts(workflow_id, step_id, output)

            # 验证 adopt 被调用
            mock_adopt.assert_called_once()
            call_args = mock_adopt.call_args

            # 验证参数
            assert call_args.kwargs['run_id'] == workflow_id
            assert call_args.kwargs['file_path'] == str(self.test_patch_file)
            assert call_args.kwargs['category'] == f"step_{step_id}"
            assert 'step_id' in call_args.kwargs['metadata']
            assert 'output_key' in call_args.kwargs['metadata']

    def test_record_step_artifacts_with_test_report(self):
        """验证记录测试报告产出物 (识别为 TEST 类型)"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        workflow_id = "test-workflow-001"
        step_id = "run_tests"

        output = {
            "test_report": str(self.test_report_file),
            "coverage_report": str(self.test_coverage_file),
            "status": "completed"
        }

        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts(workflow_id, step_id, output)

            # 验证 adopt 被调用 2 次 (test_report + coverage_report)
            assert mock_adopt.call_count == 2

    def test_record_step_artifacts_with_review_report(self):
        """验证记录 code review 产出物 (识别为 DOCUMENT 类型)"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        workflow_id = "test-workflow-001"
        step_id = "code_review"

        output = {
            "review_report": str(self.test_review_file),
            "status": "approved"
        }

        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts(workflow_id, step_id, output)

            mock_adopt.assert_called_once()

    def test_record_step_artifacts_with_file_suffixes(self):
        """验证识别 *_file 和 *_path 后缀的产出物"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        workflow_id = "test-workflow-001"
        step_id = "step_1"

        # 创建临时文件
        output_file = Path(self.temp_dir) / "output.txt"
        output_file.write_text("output content")

        output = {
            "output_file": str(output_file),
            "log_path": str(self.test_coverage_file)
        }

        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts(workflow_id, step_id, output)

            # 验证识别了两个文件
            assert mock_adopt.call_count == 2

    def test_record_step_artifacts_with_non_dict_output(self):
        """验证非 dict 输出时不报错"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        # 非字典输出不应报错
        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts("wf-001", "step_1", "string output")
            orch._record_step_artifacts("wf-001", "step_1", None)
            orch._record_step_artifacts("wf-001", "step_1", 123)

            # adopt 不应被调用
            mock_adopt.assert_not_called()

    def test_record_step_artifacts_with_invalid_file_path(self):
        """验证无效文件路径时静默处理"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        output = {
            "patch_file": "/nonexistent/path/to/file.patch",
            "status": "completed"
        }

        # 不应抛出异常
        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts("wf-001", "step_1", output)

            # adopt 仍会被调用，但内部会处理文件不存在的情况
            mock_adopt.assert_called_once()

    def test_record_step_artifacts_empty_output(self):
        """验证空输出时不报错"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        with patch.object(orch.artifact_manager, 'adopt') as mock_adopt:
            orch._record_step_artifacts("wf-001", "step_1", {})
            orch._record_step_artifacts("wf-001", "step_1", {"status": "completed"})

            mock_adopt.assert_not_called()

    def test_manifest_created_on_workflow_creation(self):
        """验证工作流创建时创建 Manifest"""
        from lee.orchestrator.execution.orchestrator import Orchestrator
        from unittest.mock import patch

        mock_store = MagicMock()
        orch = Orchestrator(store=mock_store, project_root=self.temp_dir)

        # Mock manifest_manager.create
        with patch.object(orch.manifest_manager, 'create') as mock_create:
            # 模拟 create_workflow 内部逻辑
            run_id = "test-run-001"
            workflow_id = "test-workflow"

            orch.manifest_manager.create(
                run_id=run_id,
                workflow_id=workflow_id,
                department="dev",
                executor="claude_code",
                parent_run_id=None,
                root_run_id=run_id
            )

            mock_create.assert_called_once()
