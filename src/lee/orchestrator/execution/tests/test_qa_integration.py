"""
QA Test Plan Execution 集成测试

验证 Bug 修复：
1. BUG-2026-0037: auto_check 门禁自动通过
2. BUG-2026-0038: task_execution 状态正确更新
3. BUG-2026-0039: 步骤不会重复执行
4. BUG-2026-0040: status 命令显示正确
"""

import asyncio
import pytest
import yaml
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from lee.orchestrator.storage.models import (
    WorkflowInstance,
    WorkflowStatus,
    TaskExecution,
    TaskExecutionStatus,
    OutputSpec,
)
from lee.orchestrator.execution.state_machine import WorkflowStateMachine
from lee.orchestrator.execution.runners.auto_check_gate_runner import AutoCheckGateRunner


class TestBugFixes:
    """Bug 修复集成测试套件"""

    def setup_method(self):
        """测试前设置"""
        # 创建 mock 依赖
        self.mock_store = AsyncMock()
        self.mock_state_machine = AsyncMock()
        self.mock_event_log = MagicMock()

        # 创建 StateMachine 实例
        self.state_machine = WorkflowStateMachine(self.mock_store)

    # ========================================================================
    # BUG-2026-0037: auto_check 门禁自动通过
    # ========================================================================

    @pytest.mark.asyncio
    async def test_bug_2026_0037_auto_check_gate_passes(self):
        """
        验证 auto_check 门禁能够自动通过

        场景：
        - 门禁配置为 type: auto_check
        - check 条件满足

        预期结果：
        - 门禁自动通过，不需要人工审批
        """
        runner = AutoCheckGateRunner()

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {
                "health_check": {"status": "healthy", "version": "1.0.0"}
            }
        }
        self.mock_store.get_workflow.return_value = mock_instance
        self.mock_store.get_task_executions.return_value = []

        # 模拟步骤（kind: gate, type: auto_check）
        mock_step = MagicMock()
        mock_step.id = "p2_s2_health_check"
        mock_step.config = {
            "gate": {
                "check": "status == 'healthy'",
                "on_fail": {"action": "fail_step"}
            }
        }

        # 模拟 complete_step 返回成功
        mock_result = MagicMock()
        mock_result.status = "success"
        self.mock_state_machine.complete_step.return_value = mock_result

        # 创建 RunnerContext
        mock_ctx = MagicMock()
        mock_ctx.store = self.mock_store
        mock_ctx.state_machine = self.mock_state_machine

        # 执行
        result = await runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证
        assert result.status == "success", "auto_check 门禁应该自动通过"
        assert result.output["auto_check_passed"] is True
        self.mock_state_machine.complete_step.assert_called_once()

    @pytest.mark.asyncio
    async def test_bug_2026_0037_auto_check_gate_fails(self):
        """
        验证 auto_check 门禁失败时正确处理

        场景：
        - 门禁配置为 type: auto_check
        - check 条件不满足

        预期结果：
        - 门禁失败，调用 fail_step
        """
        runner = AutoCheckGateRunner()

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {
                "health_check": {"status": "unhealthy"}
            }
        }
        self.mock_store.get_workflow.return_value = mock_instance
        self.mock_store.get_task_executions.return_value = []

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.id = "p2_s2_health_check"
        mock_step.config = {
            "gate": {
                "check": "status == 'healthy'",
                "on_fail": {"action": "fail_step"}
            }
        }

        # 创建 RunnerContext
        mock_ctx = MagicMock()
        mock_ctx.store = self.mock_store
        mock_ctx.state_machine = self.mock_state_machine

        # 执行
        result = await runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证
        assert result.status == "failed", "auto_check 门禁应该失败"
        assert result.output["auto_check_passed"] is False
        self.mock_state_machine.fail_step.assert_called_once()

    # ========================================================================
    # BUG-2026-0038: task_execution 状态正确更新
    # ========================================================================

    @pytest.mark.asyncio
    async def test_bug_2026_0038_task_execution_status_updated(self):
        """
        验证 task_execution 状态正确更新为 COMPLETED

        场景：
        - 步骤执行完成
        - task_execution 存在且状态为 RUNNING

        预期结果：
        - task_execution 状态更新为 COMPLETED
        """
        runner = AutoCheckGateRunner()

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {"step1": {"status": "healthy"}}
        }
        self.mock_store.get_workflow.return_value = mock_instance

        # 模拟运行中的 task_execution
        mock_execution = MagicMock()
        mock_execution.id = "exec-123"
        mock_execution.step_name = "test_gate"
        mock_execution.status = TaskExecutionStatus.RUNNING
        self.mock_store.get_task_executions.return_value = [mock_execution]

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.id = "test_gate"
        mock_step.config = {"gate": {"check": "status == 'healthy'"}}

        # 模拟 complete_step
        mock_result = MagicMock()
        self.mock_state_machine.complete_step.return_value = mock_result

        # 创建 RunnerContext
        mock_ctx = MagicMock()
        mock_ctx.store = self.mock_store
        mock_ctx.state_machine = self.mock_state_machine

        # 执行
        result = await runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证
        assert result.status == "success"
        self.mock_store.update_task_execution.assert_called_once()

        # 验证更新参数
        call_args = self.mock_store.update_task_execution.call_args
        assert call_args[0][0] == "exec-123"
        assert call_args[0][1] == TaskExecutionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_bug_2026_0038_task_execution_updated_on_failure(self):
        """
        验证 task_execution 在步骤失败时更新为 FAILED

        场景：
        - 步骤执行失败
        - task_execution 存在且状态为 RUNNING

        预期结果：
        - task_execution 状态更新为 FAILED
        """
        runner = AutoCheckGateRunner()

        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.data = {
            "step_outputs": {"step1": {"status": "unhealthy"}}
        }
        self.mock_store.get_workflow.return_value = mock_instance

        # 模拟运行中的 task_execution
        mock_execution = MagicMock()
        mock_execution.id = "exec-123"
        mock_execution.step_name = "test_gate"
        mock_execution.status = TaskExecutionStatus.RUNNING
        self.mock_store.get_task_executions.return_value = [mock_execution]

        # 模拟步骤
        mock_step = MagicMock()
        mock_step.id = "test_gate"
        mock_step.config = {
            "gate": {
                "check": "status == 'healthy'",
                "on_fail": {"action": "fail_step"}
            }
        }

        # 创建 RunnerContext
        mock_ctx = MagicMock()
        mock_ctx.store = self.mock_store
        mock_ctx.state_machine = self.mock_state_machine

        # 执行
        result = await runner.execute("workflow-123", mock_step, mock_ctx)

        # 验证
        assert result.status == "failed"
        self.mock_store.update_task_execution.assert_called_once()

        # 验证更新参数
        call_args = self.mock_store.update_task_execution.call_args
        assert call_args[0][0] == "exec-123"
        assert call_args[0][1] == TaskExecutionStatus.FAILED

    # ========================================================================
    # BUG-2026-0039: 步骤不会重复执行
    # ========================================================================

    @pytest.mark.asyncio
    async def test_bug_2026_0039_no_duplicate_execution(self):
        """
        验证正在执行的步骤不会被重复获取

        场景：
        - 步骤 A 正在执行（task_execution 状态为 RUNNING）
        - 调用 get_ready_steps

        预期结果：
        - 步骤 A 不在就绪步骤列表中
        """
        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": [],  # 没有完成的步骤
        }
        self.mock_store.get_workflow.return_value = mock_instance

        # 模拟运行中的 task_execution
        mock_execution = MagicMock()
        mock_execution.step_name = "step_A"
        mock_execution.status = TaskExecutionStatus.RUNNING
        self.mock_store.get_task_executions.return_value = [mock_execution]

        # 模拟所有步骤
        mock_step_a = MagicMock()
        mock_step_a.id = "step_A"
        mock_step_a.depends_on = []

        mock_step_b = MagicMock()
        mock_step_b.id = "step_B"
        mock_step_b.depends_on = []

        all_steps = [mock_step_a, mock_step_b]

        # 调用 get_ready_steps
        ready_steps = await self.state_machine.get_ready_steps("workflow-123", all_steps)

        # 验证
        ready_step_ids = [step.id for step in ready_steps]
        assert "step_A" not in ready_step_ids, "正在执行的步骤不应该在就绪列表中"
        assert "step_B" in ready_step_ids, "未执行的步骤应该在就绪列表中"

    @pytest.mark.asyncio
    async def test_bug_2026_0039_completed_steps_not_returned(self):
        """
        验证已完成的步骤不会被重复获取

        场景：
        - 步骤 A 已完成（在 completed_steps 中）
        - 调用 get_ready_steps

        预期结果：
        - 步骤 A 不在就绪步骤列表中
        """
        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": ["step_A"],  # 步骤 A 已完成
        }
        self.mock_store.get_workflow.return_value = mock_instance
        self.mock_store.get_task_executions.return_value = []

        # 模拟所有步骤
        mock_step_a = MagicMock()
        mock_step_a.id = "step_A"
        mock_step_a.depends_on = []

        mock_step_b = MagicMock()
        mock_step_b.id = "step_B"
        mock_step_b.depends_on = []

        all_steps = [mock_step_a, mock_step_b]

        # 调用 get_ready_steps
        ready_steps = await self.state_machine.get_ready_steps("workflow-123", all_steps)

        # 验证
        ready_step_ids = [step.id for step in ready_steps]
        assert "step_A" not in ready_step_ids, "已完成的步骤不应该在就绪列表中"
        assert "step_B" in ready_step_ids, "未完成的步骤应该在就绪列表中"

    # ========================================================================
    # BUG-2026-0040: status 命令显示正确
    # ========================================================================

    @pytest.mark.asyncio
    async def test_bug_2026_0040_current_step_cleared_atomically(self):
        """
        验证 complete_step 原子性更新 data 和清除 current_step

        场景：
        - 步骤完成
        - 调用 complete_step

        预期结果：
        - completed_steps 更新
        - current_step 清除
        - 两个操作原子性执行
        """
        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": ["step_A"],
            "step_outputs": {},
        }
        self.mock_store.get_workflow.return_value = mock_instance

        # 调用 complete_step
        result = await self.state_machine.complete_step(
            "workflow-123",
            "step_B",
            {"result": "success"}
        )

        # 验证调用了原子性更新方法
        self.mock_store.update_workflow_data_and_clear_current_step.assert_called_once()

        # 验证更新参数
        call_args = self.mock_store.update_workflow_data_and_clear_current_step.call_args
        data = call_args[0][1]

        assert "step_B" in data["completed_steps"], "新步骤应该添加到 completed_steps"
        assert len(data["completed_steps"]) == 2, "completed_steps 应该包含两个步骤"

    @pytest.mark.asyncio
    async def test_bug_2026_0040_step_outputs_updated(self):
        """
        验证 step_outputs 正确更新

        场景：
        - 步骤完成时有 step_outputs
        - 调用 complete_step

        预期结果：
        - step_outputs 映射正确更新
        """
        # 模拟工作流实例
        mock_instance = MagicMock()
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": [],
            "step_outputs": {},
        }
        self.mock_store.get_workflow.return_value = mock_instance

        # 模拟 step_outputs
        mock_output = MagicMock()
        mock_output.path = "/tmp/output.txt"

        # 调用 complete_step
        result = await self.state_machine.complete_step(
            "workflow-123",
            "step_B",
            {"result": "success"},
            step_outputs=[mock_output]
        )

        # 验证调用了原子性更新方法
        self.mock_store.update_workflow_data_and_clear_current_step.assert_called_once()

        # 验证更新参数
        call_args = self.mock_store.update_workflow_data_and_clear_current_step.call_args
        data = call_args[0][1]

        assert "step_B" in data["step_outputs"], "步骤 ID 应该在 step_outputs 中"
        assert "/tmp/output.txt" in data["step_outputs"]["step_B"]["paths"], "输出路径应该被记录"

    @pytest.mark.asyncio
    async def test_fail_step_clears_current_step_for_retry(self):
        """
        验证 fail_step 会清除 current_step，避免失败后的 step 被永久卡住

        场景：
        - 步骤执行失败
        - 工作流后续被切回 RUNNING 重新调度

        预期结果：
        - update_workflow_status 带 clear_current_step=True
        """
        await self.state_machine.fail_step(
            "workflow-123",
            "step_B",
            "boom",
        )

        self.mock_store.update_workflow_status.assert_called_once_with(
            "workflow-123",
            WorkflowStatus.FAILED,
            clear_current_step=True,
        )

    @pytest.mark.asyncio
    async def test_complete_step_materializes_declared_gate_output_file(self, tmp_path):
        rendered_dir = tmp_path / ".workflow" / "rendered"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        template_path = rendered_dir / "workflow-test.yaml"
        template_path.write_text("id: dummy\n", encoding="utf-8")

        mock_instance = MagicMock()
        mock_instance.template_id = str(template_path)
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": ["feat_spec_generation", "feat_review"],
            "step_outputs": {
                "feat_spec_generation": {"business_output": {"epic_ref": "EPIC-001"}},
                "feat_review": {"decision": "pass"},
            },
            "params": {"project": "demo"},
        }
        self.mock_store.get_workflow.return_value = mock_instance

        step_info = MagicMock()
        step_info.outputs = [OutputSpec(type="file", path="output/design-frozen/{project}-feat-freeze.yaml", format="yaml")]
        step_info.input = [{"source": "feat_spec_generation"}, {"source": "feat_review"}]

        template = MagicMock()
        template.get_step_info.return_value = step_info
        template_manager = MagicMock()
        template_manager.get_template.return_value = template

        state_machine = WorkflowStateMachine(self.mock_store, template_manager=template_manager)
        await state_machine.complete_step(
            "workflow-123",
            "feat_freeze",
            {"gate_approved": True, "comments": "ok"},
        )

        frozen_path = tmp_path / "output" / "design-frozen" / "demo-feat-freeze.yaml"
        assert frozen_path.exists()
        content = frozen_path.read_text(encoding="utf-8")
        assert "gate_approved: true" in content
        assert "feat_spec_generation:" in content

    @pytest.mark.asyncio
    async def test_complete_step_preserves_existing_shell_generated_output_file(self, tmp_path):
        rendered_dir = tmp_path / ".workflow" / "rendered"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        template_path = rendered_dir / "workflow-test.yaml"
        template_path.write_text("id: dummy\n", encoding="utf-8")

        output_path = tmp_path / "docs" / "reports" / "repo-summary.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            '{"repository_summary":{"name":"LEE","modules":[{"id":"core","path_prefix":"src/","summary":"x"}]}}',
            encoding="utf-8",
        )

        mock_instance = MagicMock()
        mock_instance.template_id = str(template_path)
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": [],
            "step_outputs": {},
            "params": {},
        }
        self.mock_store.get_workflow.return_value = mock_instance

        step_info = MagicMock()
        step_info.outputs = [OutputSpec(type="file", path="docs/reports/repo-summary.json", format="json")]
        step_info.input = []

        template = MagicMock()
        template.get_step_info.return_value = step_info
        template_manager = MagicMock()
        template_manager.get_template.return_value = template

        state_machine = WorkflowStateMachine(self.mock_store, template_manager=template_manager)
        await state_machine.complete_step(
            "workflow-123",
            "repo_evidence_scan",
            {"stdout": '{"repo_file_count": 10}\n', "stderr": "", "return_code": 0, "status": "completed"},
        )

        payload = yaml.safe_load(output_path.read_text(encoding="utf-8"))
        assert "repository_summary" in payload
        assert "gate_output" not in payload

    @pytest.mark.asyncio
    async def test_complete_step_materializes_freeze_ref_alias_inputs(self, tmp_path):
        rendered_dir = tmp_path / ".workflow" / "rendered"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        template_path = rendered_dir / "workflow-test.yaml"
        template_path.write_text("id: dummy\n", encoding="utf-8")

        mock_instance = MagicMock()
        mock_instance.template_id = str(template_path)
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": ["feat_review"],
            "step_outputs": {
                "feat_review": {"decision": "pass"},
            },
            "params": {
                "project": "demo",
                "epic_freeze_ref": {
                    "artifact_id": "EPIC-001",
                    "path": "spec/requirements/epics/EPIC-001__demo.md",
                },
            },
        }
        self.mock_store.get_workflow.return_value = mock_instance

        step_info = MagicMock()
        step_info.outputs = [OutputSpec(type="file", path="output/design-frozen/{project}-feat-freeze.yaml", format="yaml")]
        step_info.input = [{"source": "epic_freeze"}, {"source": "feat_review"}]

        template = MagicMock()
        template.get_step_info.return_value = step_info
        template_manager = MagicMock()
        template_manager.get_template.return_value = template

        state_machine = WorkflowStateMachine(self.mock_store, template_manager=template_manager)
        await state_machine.complete_step(
            "workflow-456",
            "feat_freeze",
            {"gate_approved": True},
        )

        frozen_path = tmp_path / "output" / "design-frozen" / "demo-feat-freeze.yaml"
        payload = yaml.safe_load(frozen_path.read_text(encoding="utf-8"))
        assert payload["frozen_inputs"]["epic_freeze_ref"]["artifact_id"] == "EPIC-001"
        assert payload["frozen_inputs"]["feat_review"]["decision"] == "pass"

    @pytest.mark.asyncio
    async def test_complete_step_materializes_outputs_under_store_project_root_for_absolute_templates(self, tmp_path):
        canonical_root = tmp_path.parent / f"{tmp_path.name}-canonical"
        template_path = canonical_root / "spec-global" / "departments" / "product" / "workflows" / "templates" / "feat-to-release" / "v1" / "workflow.yaml"
        template_path.parent.mkdir(parents=True, exist_ok=True)
        template_path.write_text("id: workflow.product.task.feat_to_release\n", encoding="utf-8")

        self.mock_store.db_path = str(tmp_path / ".workflow" / "orchestrator.db")

        mock_instance = MagicMock()
        mock_instance.template_id = str(template_path)
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": [],
            "step_outputs": {},
            "params": {"project": "demo"},
        }
        self.mock_store.get_workflow.return_value = mock_instance

        step_info = MagicMock()
        step_info.outputs = [OutputSpec(type="file", path="spec/releases/{project}-release.yaml", format="yaml")]
        step_info.input = []

        template = MagicMock()
        template.get_step_info.return_value = step_info
        template_manager = MagicMock()
        template_manager.get_template.return_value = template

        state_machine = WorkflowStateMachine(self.mock_store, template_manager=template_manager)
        await state_machine.complete_step(
            "workflow-789",
            "release_output",
            {"business_output": {"release_id": "REL-001"}},
        )

        assert (tmp_path / "spec" / "releases" / "demo-release.yaml").exists()
        assert not (template_path.parent / "spec" / "releases" / "demo-release.yaml").exists()

    @pytest.mark.asyncio
    async def test_complete_step_registers_symbol_output_aliases(self, tmp_path):
        rendered_dir = tmp_path / ".workflow" / "rendered"
        rendered_dir.mkdir(parents=True, exist_ok=True)
        template_path = rendered_dir / "workflow-test.yaml"
        template_path.write_text("id: dummy\n", encoding="utf-8")

        mock_instance = MagicMock()
        mock_instance.template_id = str(template_path)
        mock_instance.status = WorkflowStatus.RUNNING
        mock_instance.data = {
            "completed_steps": [],
            "step_outputs": {},
            "params": {"project": "demo"},
        }
        self.mock_store.get_workflow.return_value = mock_instance

        step_info = MagicMock()
        step_info.outputs = [
            OutputSpec(
                type="symbol",
                path="feat_scoped_specs",
                format="yaml",
                symbol="feat_scoped_specs",
            )
        ]
        step_info.input = [{"source": "feat_specs"}]

        template = MagicMock()
        template.get_step_info.return_value = step_info
        template_manager = MagicMock()
        template_manager.get_template.return_value = template

        state_machine = WorkflowStateMachine(self.mock_store, template_manager=template_manager)
        payload = {"ssot_materialized": {"feat": {"id": "FEAT-SRC-001-001"}}}
        await state_machine.complete_step("workflow-789", "feat_identity_prepare", payload)

        updated_data = self.mock_store.update_workflow_data_and_clear_current_step.await_args.args[1]
        assert updated_data["step_outputs"]["feat_identity_prepare"] == payload
        assert updated_data["step_outputs"]["feat_scoped_specs"] == payload
        assert not (tmp_path / "feat_scoped_specs").exists()
