"""
测试 api_approve_gate 的 auto_continue 功能

验证 Gate 批准后工作流是否自动继续执行。
"""

import asyncio
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch, MagicMock

import pytest

# 设置项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, 'src')
sys.path.insert(0, src_dir)

from lee.orchestrator.api import api_approve_gate, api_run_until_blocked
from lee.orchestrator.storage.models import StepResult, GateStatus


class TestApiApproveGateAutoContinue:
    """测试 api_approve_gate 的 auto_continue 功能"""

    @pytest.fixture
    def mock_orchestrator(self):
        """创建模拟的 orchestrator"""
        mock = AsyncMock()
        mock.approve_gate = AsyncMock(return_value=StepResult(
            status="success",
            step_id="gate_001",
            workflow_id="wf_001",
            message="Gate approved",
        ))
        return mock

    @pytest.fixture
    def mock_store(self):
        """创建模拟的 store"""
        mock = AsyncMock()
        mock.connect = AsyncMock()
        mock.close = AsyncMock()
        return mock

    @pytest.mark.asyncio
    async def test_approve_gate_with_auto_continue_default(self, mock_orchestrator, mock_store):
        """测试默认情况下 auto_continue=True"""
        with patch('lee.orchestrator.api._get_orchestrator', AsyncMock(return_value=mock_orchestrator)):
            with patch('lee.orchestrator.api._release_orchestrator', AsyncMock()):
                with patch('lee.orchestrator.api.api_run_until_blocked', AsyncMock(return_value={
                    "status": "blocked",
                    "workflow_id": "wf_001",
                    "blocked_at": "step_002",
                })) as mock_run:

                    result = await api_approve_gate(
                        project_dir=".",
                        workflow_id="wf_001",
                        gate_id="gate_001",
                        approver="test_user",
                        comments="Approved",
                        # 不传 auto_continue，使用默认值 True
                    )

                    # 验证审批成功
                    assert result["status"] == "success"
                    assert result["auto_continued"] is True
                    assert "run_result" in result

                    # 验证调用了 run_until_blocked
                    mock_run.assert_called_once_with(".", "wf_001", 10)

    @pytest.mark.asyncio
    async def test_approve_gate_with_auto_continue_explicit_true(self, mock_orchestrator, mock_store):
        """测试显式设置 auto_continue=True"""
        with patch('lee.orchestrator.api._get_orchestrator', AsyncMock(return_value=mock_orchestrator)):
            with patch('lee.orchestrator.api._release_orchestrator', AsyncMock()):
                with patch('lee.orchestrator.api.api_run_until_blocked', AsyncMock(return_value={
                    "status": "completed",
                    "workflow_id": "wf_001",
                })) as mock_run:

                    result = await api_approve_gate(
                        project_dir=".",
                        workflow_id="wf_001",
                        gate_id="gate_001",
                        approver="test_user",
                        comments="Approved",
                        auto_continue=True,
                        max_steps=20,
                    )

                    assert result["status"] == "success"
                    assert result["auto_continued"] is True
                    assert "run_result" in result

                    # 验证使用了自定义 max_steps
                    mock_run.assert_called_once_with(".", "wf_001", 20)

    @pytest.mark.asyncio
    async def test_approve_gate_with_auto_continue_false(self, mock_orchestrator, mock_store):
        """测试设置 auto_continue=False 时不自动继续"""
        with patch('lee.orchestrator.api._get_orchestrator', AsyncMock(return_value=mock_orchestrator)):
            with patch('lee.orchestrator.api._release_orchestrator', AsyncMock()):
                with patch('lee.orchestrator.api.api_run_until_blocked') as mock_run:

                    result = await api_approve_gate(
                        project_dir=".",
                        workflow_id="wf_001",
                        gate_id="gate_001",
                        approver="test_user",
                        comments="Approved",
                        auto_continue=False,
                    )

                    assert result["status"] == "success"
                    # 验证没有 auto_continued 字段或为 False
                    assert result.get("auto_continued") is None

                    # 验证没有调用 run_until_blocked
                    mock_run.assert_not_called()

    @pytest.mark.asyncio
    async def test_approve_gate_auto_continue_exception_handled(self, mock_orchestrator, mock_store):
        """测试 auto_continue 异常被捕获，不影响审批结果"""
        with patch('lee.orchestrator.api._get_orchestrator', AsyncMock(return_value=mock_orchestrator)):
            with patch('lee.orchestrator.api._release_orchestrator', AsyncMock()):
                with patch('lee.orchestrator.api.api_run_until_blocked', AsyncMock(side_effect=Exception("Run failed"))):

                    result = await api_approve_gate(
                        project_dir=".",
                        workflow_id="wf_001",
                        gate_id="gate_001",
                        approver="test_user",
                        comments="Approved",
                        auto_continue=True,
                    )

                    # 审批仍然成功
                    assert result["status"] == "success"
                    assert result["auto_continued"] is True
                    # 但包含错误信息
                    assert "run_error" in result
                    assert "Run failed" in result["run_error"]

    @pytest.mark.asyncio
    async def test_approve_gate_returns_base_result(self, mock_orchestrator, mock_store):
        """测试返回基础审批结果"""
        with patch('lee.orchestrator.api._get_orchestrator', AsyncMock(return_value=mock_orchestrator)):
            with patch('lee.orchestrator.api._release_orchestrator', AsyncMock()):

                result = await api_approve_gate(
                    project_dir=".",
                    workflow_id="wf_001",
                    gate_id="gate_001",
                    approver="test_user",
                    comments="Approved",
                    auto_continue=False,
                )

                assert result["status"] == "success"
                assert result["step_id"] == "gate_001"
                assert result["workflow_id"] == "wf_001"
                assert result["message"] == "Gate approved"
                assert "timestamp" in result


class TestApiApproveGateIntegration:
    """集成测试 - 验证完整的 Gate 批准流程"""

    @pytest.mark.asyncio
    async def test_approve_gate_workflow_resumes(self):
        """
        集成测试：Gate 批准后工作流恢复执行

        这是一个简化测试，验证 api_approve_gate 的正确调用链。
        完整的端到端测试在 test_orchestrator_e2e.py 中。
        """
        # 验证函数签名包含 auto_continue 参数
        import inspect
        sig = inspect.signature(api_approve_gate)
        params = list(sig.parameters.keys())

        assert "auto_continue" in params
        assert "max_steps" in params

        # 验证默认值
        assert sig.parameters["auto_continue"].default is True
        assert sig.parameters["max_steps"].default == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
