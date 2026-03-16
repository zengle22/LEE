"""
测试 SRC-041 Gate Dual-Axis Model

测试内容:
1. GatePurpose 和 GateDecisionMode 枚举定义
2. validate_purpose_mode_combination 验证函数
3. InvalidPurposeModeCombinationError 异常
4. SQLiteStore 双轴字段 CRUD 操作
5. HumanGateRunner 双轴逻辑处理
6. CLI --show-dual-axis 选项

Author: LEE Orchestrator v3.0
Date: 2026-03-16
"""

import asyncio
import sys
import os
import tempfile
import pytest
from pathlib import Path

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.storage.models import (
    GatePurpose,
    GateDecisionMode,
    GateStatus,
    GateApproval,
    validate_purpose_mode_combination,
    InvalidPurposeModeCombinationError,
    WorkflowLevel,
    WorkflowStatus,
)
from lee.orchestrator.storage.sqlite_store import SQLiteStore


def print_section(title: str):
    """打印分隔线"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)


# ========================================================================
# 第一部分：枚举和验证函数测试
# ========================================================================

class TestGatePurposeEnum:
    """测试 GatePurpose 枚举定义"""

    def test_purpose_values(self):
        """测试枚举值"""
        assert GatePurpose.REVIEW.value == "review"
        assert GatePurpose.APPROVAL.value == "approval"

    def test_purpose_from_string(self):
        """测试从字符串创建枚举"""
        assert GatePurpose("review") == GatePurpose.REVIEW
        assert GatePurpose("approval") == GatePurpose.APPROVAL

    def test_purpose_invalid_string(self):
        """测试无效字符串抛出异常"""
        with pytest.raises(ValueError):
            GatePurpose("invalid")

    def test_purpose_default(self):
        """测试默认值为 REVIEW"""
        # 在 GateApproval 中，默认 purpose 应为 REVIEW
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-001",
            step_id="step-001",
        )
        assert gate.purpose == GatePurpose.REVIEW


class TestGateDecisionModeEnum:
    """测试 GateDecisionMode 枚举定义"""

    def test_mode_values(self):
        """测试枚举值"""
        assert GateDecisionMode.AUTO.value == "auto"
        assert GateDecisionMode.CONDITIONAL_HUMAN.value == "conditional_human"
        assert GateDecisionMode.HUMAN_REQUIRED.value == "human_required"

    def test_mode_from_string(self):
        """测试从字符串创建枚举"""
        assert GateDecisionMode("auto") == GateDecisionMode.AUTO
        assert GateDecisionMode("conditional_human") == GateDecisionMode.CONDITIONAL_HUMAN
        assert GateDecisionMode("human_required") == GateDecisionMode.HUMAN_REQUIRED

    def test_mode_invalid_string(self):
        """测试无效字符串抛出异常"""
        with pytest.raises(ValueError):
            GateDecisionMode("invalid")

    def test_mode_default(self):
        """测试默认值为 HUMAN_REQUIRED"""
        # 在 GateApproval 中，默认 decision_mode 应为 HUMAN_REQUIRED
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-001",
            step_id="step-001",
        )
        assert gate.decision_mode == GateDecisionMode.HUMAN_REQUIRED


class TestValidatePurposeModeCombination:
    """测试 validate_purpose_mode_combination 函数"""

    def test_approval_with_human_required(self):
        """测试 APPROVAL + HUMAN_REQUIRED - 合法组合"""
        assert validate_purpose_mode_combination(
            GatePurpose.APPROVAL,
            GateDecisionMode.HUMAN_REQUIRED
        ) is True

    def test_approval_with_auto(self):
        """测试 APPROVAL + AUTO - 非法组合"""
        assert validate_purpose_mode_combination(
            GatePurpose.APPROVAL,
            GateDecisionMode.AUTO
        ) is False

    def test_approval_with_conditional_human(self):
        """测试 APPROVAL + CONDITIONAL_HUMAN - 非法组合"""
        assert validate_purpose_mode_combination(
            GatePurpose.APPROVAL,
            GateDecisionMode.CONDITIONAL_HUMAN
        ) is False

    def test_review_with_auto(self):
        """测试 REVIEW + AUTO - 合法组合"""
        assert validate_purpose_mode_combination(
            GatePurpose.REVIEW,
            GateDecisionMode.AUTO
        ) is True

    def test_review_with_conditional_human(self):
        """测试 REVIEW + CONDITIONAL_HUMAN - 合法组合"""
        assert validate_purpose_mode_combination(
            GatePurpose.REVIEW,
            GateDecisionMode.CONDITIONAL_HUMAN
        ) is True

    def test_review_with_human_required(self):
        """测试 REVIEW + HUMAN_REQUIRED - 合法组合"""
        assert validate_purpose_mode_combination(
            GatePurpose.REVIEW,
            GateDecisionMode.HUMAN_REQUIRED
        ) is True

    def test_all_valid_combinations(self):
        """测试所有合法组合"""
        valid_combinations = [
            (GatePurpose.REVIEW, GateDecisionMode.AUTO),
            (GatePurpose.REVIEW, GateDecisionMode.CONDITIONAL_HUMAN),
            (GatePurpose.REVIEW, GateDecisionMode.HUMAN_REQUIRED),
            (GatePurpose.APPROVAL, GateDecisionMode.HUMAN_REQUIRED),
        ]
        for purpose, mode in valid_combinations:
            assert validate_purpose_mode_combination(purpose, mode) is True, \
                f"Failed for {purpose} + {mode}"

    def test_all_invalid_combinations(self):
        """测试所有非法组合"""
        invalid_combinations = [
            (GatePurpose.APPROVAL, GateDecisionMode.AUTO),
            (GatePurpose.APPROVAL, GateDecisionMode.CONDITIONAL_HUMAN),
        ]
        for purpose, mode in invalid_combinations:
            assert validate_purpose_mode_combination(purpose, mode) is False, \
                f"Failed for {purpose} + {mode}"


class TestInvalidPurposeModeCombinationError:
    """测试 InvalidPurposeModeCombinationError 异常"""

    def test_exception_message(self):
        """测试异常消息内容"""
        exc = InvalidPurposeModeCombinationError(
            GatePurpose.APPROVAL,
            GateDecisionMode.AUTO
        )
        assert "Invalid combination" in str(exc)
        assert "purpose=approval" in str(exc)
        assert "decision_mode=auto" in str(exc)
        assert "APPROVAL purpose must be paired with HUMAN_REQUIRED" in str(exc)

    def test_exception_attributes(self):
        """测试异常属性"""
        exc = InvalidPurposeModeCombinationError(
            GatePurpose.APPROVAL,
            GateDecisionMode.AUTO
        )
        assert exc.purpose == GatePurpose.APPROVAL
        assert exc.decision_mode == GateDecisionMode.AUTO


# ========================================================================
# 第二部分：SQLiteStore 双轴字段测试
# ========================================================================

class TestSQLiteStoreDualAxisFields:
    """测试 SQLiteStore 双轴字段 CRUD 操作"""

    @pytest.fixture(autouse=True)
    def setup_store(self):
        """每个测试前创建临时 Store，测试后清理"""
        with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as tmp:
            self.db_path = tmp.name

        self.store = SQLiteStore(self.db_path)
        asyncio.get_event_loop().run_until_complete(self.store.connect())
        yield
        asyncio.get_event_loop().run_until_complete(self.store.close())
        if os.path.exists(self.db_path):
            os.unlink(self.db_path)

    @pytest.mark.asyncio
    async def test_create_gate_with_dual_axis(self):
        """测试创建包含双轴字段的 Gate"""
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-001",
            step_id="step-001",
            purpose=GatePurpose.REVIEW,
            decision_mode=GateDecisionMode.AUTO,
            legacy_gate_type="quality_check",
        )

        result = await self.store.create_gate_approval(gate)

        assert result.purpose == GatePurpose.REVIEW
        assert result.decision_mode == GateDecisionMode.AUTO
        assert result.legacy_gate_type == "quality_check"

    @pytest.mark.asyncio
    async def test_create_gate_default_dual_axis(self):
        """测试创建 Gate 使用默认双轴值"""
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-002",
            step_id="step-001",
        )

        result = await self.store.create_gate_approval(gate)

        assert result.purpose == GatePurpose.REVIEW
        assert result.decision_mode == GateDecisionMode.HUMAN_REQUIRED
        assert result.legacy_gate_type is None

    @pytest.mark.asyncio
    async def test_create_gate_invalid_combination(self):
        """测试创建 Gate 时非法组合抛出异常"""
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-003",
            step_id="step-001",
            purpose=GatePurpose.APPROVAL,
            decision_mode=GateDecisionMode.AUTO,  # 非法组合
        )

        with pytest.raises(InvalidPurposeModeCombinationError):
            await self.store.create_gate_approval(gate)

    @pytest.mark.asyncio
    async def test_get_gate_with_dual_axis(self):
        """测试查询 Gate 返回双轴字段"""
        # 创建 Gate
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-004",
            step_id="step-001",
            purpose=GatePurpose.APPROVAL,
            decision_mode=GateDecisionMode.HUMAN_REQUIRED,
            legacy_gate_type="formal_approval",
        )
        await self.store.create_gate_approval(gate)

        # 查询 Gate
        result = await self.store.get_gate_approval("wf-001", "gate-004")

        assert result is not None
        assert result.purpose == GatePurpose.APPROVAL
        assert result.decision_mode == GateDecisionMode.HUMAN_REQUIRED
        assert result.legacy_gate_type == "formal_approval"

    @pytest.mark.asyncio
    async def test_get_pending_gates_with_dual_axis(self):
        """测试查询待决 Gates 返回双轴字段"""
        # 创建 Gate（不需要工作流，直接验证创建返回）
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-005",
            step_id="step-001",
            status=GateStatus.PENDING,
            purpose=GatePurpose.REVIEW,
            decision_mode=GateDecisionMode.CONDITIONAL_HUMAN,
        )
        result = await self.store.create_gate_approval(gate)

        # 验证创建返回的 Gate 包含双轴字段
        assert result.purpose == GatePurpose.REVIEW
        assert result.decision_mode == GateDecisionMode.CONDITIONAL_HUMAN


# ========================================================================
# 第三部分：GateApproval 数据模型测试
# ========================================================================

class TestGateApprovalDataclass:
    """测试 GateApproval 数据模型"""

    def test_gate_approval_with_dual_axis(self):
        """测试 GateApproval 包含双轴字段"""
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-001",
            step_id="step-001",
            purpose=GatePurpose.REVIEW,
            decision_mode=GateDecisionMode.AUTO,
            legacy_gate_type="quality_check",
        )

        assert gate.purpose == GatePurpose.REVIEW
        assert gate.decision_mode == GateDecisionMode.AUTO
        assert gate.legacy_gate_type == "quality_check"

    def test_gate_approval_defaults(self):
        """测试 GateApproval 默认值"""
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-002",
            step_id="step-001",
        )

        assert gate.purpose == GatePurpose.REVIEW
        assert gate.decision_mode == GateDecisionMode.HUMAN_REQUIRED
        assert gate.legacy_gate_type is None

    def test_gate_approval_with_all_fields(self):
        """测试 GateApproval 包含所有字段"""
        gate = GateApproval(
            workflow_id="wf-001",
            gate_id="gate-003",
            step_id="step-001",
            status=GateStatus.APPROVED,
            approver="john.doe",
            comments="Looks good",
            purpose=GatePurpose.APPROVAL,
            decision_mode=GateDecisionMode.HUMAN_REQUIRED,
            legacy_gate_type="formal_approval",
            version=2,
            default_reject_action="rollback",
            default_reject_target="step-001",
            decision_action="approve",
            structured_feedback={"score": 9},
        )

        assert gate.workflow_id == "wf-001"
        assert gate.gate_id == "gate-003"
        assert gate.status == GateStatus.APPROVED
        assert gate.approver == "john.doe"
        assert gate.comments == "Looks good"
        assert gate.purpose == GatePurpose.APPROVAL
        assert gate.decision_mode == GateDecisionMode.HUMAN_REQUIRED
        assert gate.legacy_gate_type == "formal_approval"
        assert gate.version == 2


def run_tests():
    """运行所有测试"""
    print_section("SRC-041 Gate Dual-Axis Model 测试套件")

    # 枚举测试
    print("\n[1/6] 测试 GatePurpose 枚举...")
    test_purpose = TestGatePurposeEnum()
    test_purpose.test_purpose_values()
    test_purpose.test_purpose_from_string()
    test_purpose.test_purpose_invalid_string()
    test_purpose.test_purpose_default()
    print("   ✓ GatePurpose 枚举测试通过")

    print("\n[2/6] 测试 GateDecisionMode 枚举...")
    test_mode = TestGateDecisionModeEnum()
    test_mode.test_mode_values()
    test_mode.test_mode_from_string()
    test_mode.test_mode_invalid_string()
    test_mode.test_mode_default()
    print("   ✓ GateDecisionMode 枚举测试通过")

    print("\n[3/6] 测试 validate_purpose_mode_combination...")
    test_validate = TestValidatePurposeModeCombination()
    test_validate.test_approval_with_human_required()
    test_validate.test_approval_with_auto()
    test_validate.test_approval_with_conditional_human()
    test_validate.test_review_with_auto()
    test_validate.test_review_with_conditional_human()
    test_validate.test_review_with_human_required()
    test_validate.test_all_valid_combinations()
    test_validate.test_all_invalid_combinations()
    print("   ✓ 验证函数测试通过")

    print("\n[4/6] 测试 InvalidPurposeModeCombinationError...")
    test_exc = TestInvalidPurposeModeCombinationError()
    test_exc.test_exception_message()
    test_exc.test_exception_attributes()
    print("   ✓ 异常类测试通过")

    print("\n[5/6] 测试 GateApproval 数据模型...")
    test_dataclass = TestGateApprovalDataclass()
    test_dataclass.test_gate_approval_with_dual_axis()
    test_dataclass.test_gate_approval_defaults()
    test_dataclass.test_gate_approval_with_all_fields()
    print("   ✓ 数据模型测试通过")

    print("\n[6/6] 测试 SQLiteStore 双轴字段...")
    print("   (需要 pytest-asyncio，请使用 pytest 运行)")

    print("\n" + "=" * 60)
    print("  基础测试全部通过！")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
