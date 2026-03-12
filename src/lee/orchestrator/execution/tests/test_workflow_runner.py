from pathlib import Path

import pytest

from lee.orchestrator.core.instance_generator import InstanceMetadata
from lee.orchestrator.execution.workflow_runner import WorkflowRunner, WorkflowRunConfig


@pytest.mark.asyncio
async def test_workflow_runner_create_workflow_includes_concurrency_metadata(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")

    captured = {}

    def fake_pm_workflow(action: str, **kwargs):
        captured["action"] = action
        captured["kwargs"] = kwargs
        return {"workflow_id": "wf_task_demo_001"}

    config = WorkflowRunConfig(
        workflow_key="product.epic-to-feat",
        template_path=template,
        params={"epic_freeze": {"artifact_id": "EPIC-321"}},
        project_root=tmp_path,
        skip_plan=True,
    )
    runner = WorkflowRunner(config)
    monkeypatch.setattr("lee.orchestrator.execution.workflow_runner._get_pm_workflow", lambda: fake_pm_workflow)

    workflow_id = await runner._create_workflow(template)

    assert workflow_id == "wf_task_demo_001"
    assert captured["action"] == "create"
    data = captured["kwargs"]["data"]
    assert data["concurrency_scope"] == "epic:EPIC-321"
    assert data["concurrency_key"] == "product.epic-to-feat::epic:EPIC-321"
    assert data["scope_source"] == "params.epic_freeze.artifact_id"


@pytest.mark.asyncio
async def test_workflow_runner_create_workflow_forwards_executor_override_and_ssot_root(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")

    captured = {}

    def fake_pm_workflow(action: str, **kwargs):
        captured["action"] = action
        captured["kwargs"] = kwargs
        return {"workflow_id": "wf_task_demo_003"}

    config = WorkflowRunConfig(
        workflow_key="product.main",
        template_path=template,
        params={"raw_requirement": "ADR-015"},
        project_root=tmp_path,
        skip_plan=False,
        ssot_root_id="TASK-123",
        executor_override="kimi",
    )
    runner = WorkflowRunner(config)
    monkeypatch.setattr("lee.orchestrator.execution.workflow_runner._get_pm_workflow", lambda: fake_pm_workflow)

    workflow_id = await runner._create_workflow(template)

    assert workflow_id == "wf_task_demo_003"
    data = captured["kwargs"]["data"]
    assert data["executor_override"] == "kimi"
    assert data["ssot_root_id"] == "TASK-123"


@pytest.mark.asyncio
async def test_workflow_runner_create_workflow_uses_feat_scoped_concurrency_metadata(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\n", encoding="utf-8")

    captured = {}

    def fake_pm_workflow(action: str, **kwargs):
        captured["action"] = action
        captured["kwargs"] = kwargs
        return {"workflow_id": "wf_task_demo_002"}

    config = WorkflowRunConfig(
        workflow_key="product.feat-to-delivery-prep",
        template_path=template,
        params={
            "feat_freeze": "FEAT-106",
            "feat_freeze_ref": {"artifact_id": "FEAT-106"},
        },
        project_root=tmp_path,
        skip_plan=True,
    )
    runner = WorkflowRunner(config)
    monkeypatch.setattr("lee.orchestrator.execution.workflow_runner._get_pm_workflow", lambda: fake_pm_workflow)

    workflow_id = await runner._create_workflow(template)

    assert workflow_id == "wf_task_demo_002"
    assert captured["action"] == "create"
    data = captured["kwargs"]["data"]
    assert data["concurrency_scope"] == "feat:FEAT-106"
    assert data["concurrency_key"] == "product.feat-to-delivery-prep::feat:FEAT-106"
    assert data["scope_source"] == "params.feat_freeze_ref.artifact_id"


@pytest.mark.asyncio
async def test_workflow_runner_create_workflow_bootstraps_l2_instance(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "product-main.yaml"
    template.write_text(
        "\n".join(
            [
                "kind: l2_workflow_template",
                "version: '1.0'",
                "phases:",
                "  - id: src_to_epic",
                "    name: SRC to EPIC",
                "    workflow: workflow.product.task.src_to_epic",
                "    level: task",
                "    depends_on: []",
                "    default_complexity: M",
            ]
        ),
        encoding="utf-8",
    )

    captured = {}

    def fake_pm_workflow(action: str, **kwargs):
        captured["action"] = action
        captured["kwargs"] = kwargs
        return {"workflow_id": "wf_department_demo_001"}

    config = WorkflowRunConfig(
        workflow_key="product.main",
        template_path=template,
        params={"raw_requirement": "ADR-011"},
        project_root=tmp_path,
        skip_plan=True,
    )
    runner = WorkflowRunner(config)
    monkeypatch.setattr("lee.orchestrator.execution.workflow_runner._get_pm_workflow", lambda: fake_pm_workflow)

    workflow_id = await runner._create_workflow(template)

    assert workflow_id == "wf_department_demo_001"
    assert captured["action"] == "create"
    assert captured["kwargs"]["level"] == "department"
    data = captured["kwargs"]["data"]
    assert data["kind"] == "l2_workflow_instance"
    assert data["phases"] == [
        {
            "id": "src_to_epic",
            "name": "SRC to EPIC",
            "description": "",
            "complexity": "M",
            "status": "pending",
            "depends_on": [],
            "workflow": "workflow.product.task.src_to_epic",
            "level": "task",
            "l3_instance_ids": [],
        }
    ]


@pytest.mark.asyncio
async def test_workflow_runner_plan_mode_uses_generated_instance_path(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "workflow.yaml"
    template.write_text("kind: workflow\nversion: '1.0'\nsteps: []\n", encoding="utf-8")

    config = WorkflowRunConfig(
        workflow_key="product.main",
        template_path=template,
        params={"raw_requirement": "ADR-015"},
        project_root=tmp_path,
        plan_mode="suggest",
        auto_approve=True,
    )
    runner = WorkflowRunner(config)

    async def fake_load_template():
        return {"kind": "workflow", "version": "1.0", "steps": []}

    async def fake_create_plan(**kwargs):
        class _PlanResult:
            instance = {"id": "wf_plan_demo_001", "plan": {"mode": "simple", "needs_review": False}, "steps": []}
            summary = "plan summary"
        return _PlanResult()

    captured = {}

    class FakeGenerator:
        def __init__(self, workspace_root):
            self.instances_dir = Path(workspace_root) / ".workflow" / "instances"

        def generate(self, plan_result, phase_id, tier="l2"):
            target = self.instances_dir / tier
            target.mkdir(parents=True, exist_ok=True)
            path = target / "wf_plan_demo_001-v1.yaml"
            path.write_text("kind: workflow\nversion: 1\n", encoding="utf-8")
            return InstanceMetadata(
                workflow_id="wf_plan_demo_001",
                version=1,
                phase_id=phase_id,
                template_ref="workflow.yaml",
                template_version="1.0",
                created_at="2026-03-13T00:00:00",
            )

    async def fake_create_workflow(path: Path):
        captured["instance_path"] = path
        return "wf_created_001"

    monkeypatch.setattr(runner, "_load_template", fake_load_template)
    monkeypatch.setattr("lee.orchestrator.execution.workflow_runner.create_plan", fake_create_plan)
    monkeypatch.setattr("lee.orchestrator.execution.workflow_runner.InstanceGenerator", FakeGenerator)
    monkeypatch.setattr(runner, "_create_workflow", fake_create_workflow)

    result = await runner._run_with_plan()

    assert result.success is True
    assert result.workflow_id == "wf_created_001"
    assert result.instance_path == tmp_path / ".workflow" / "instances" / "l2" / "wf_plan_demo_001-v1.yaml"
    assert captured["instance_path"] == result.instance_path


@pytest.mark.asyncio
async def test_workflow_runner_bypasses_plan_for_phase_based_l2_template(tmp_path: Path, monkeypatch) -> None:
    template = tmp_path / "product-main.yaml"
    template.write_text(
        "\n".join(
            [
                "kind: l2_workflow_template",
                "version: '1.0'",
                "phases:",
                "  - id: raw_to_src",
                "    name: Raw to SRC",
                "    workflow: workflow.product.task.raw_to_src",
                "    level: task",
            ]
        ),
        encoding="utf-8",
    )

    config = WorkflowRunConfig(
        workflow_key="product.main",
        template_path=template,
        params={"raw_requirement": "ADR-015"},
        project_root=tmp_path,
        plan_mode="suggest",
    )
    runner = WorkflowRunner(config)

    async def fake_load_template():
        return {
            "kind": "l2_workflow_template",
            "version": "1.0",
            "phases": [{"id": "raw_to_src", "workflow": "workflow.product.task.raw_to_src"}],
        }

    async def fake_create_workflow(path: Path):
        return "wf_department_demo_999"

    monkeypatch.setattr(runner, "_load_template", fake_load_template)
    monkeypatch.setattr(runner, "_create_workflow", fake_create_workflow)

    result = await runner._run_with_plan()

    assert result.success is True
    assert result.workflow_id == "wf_department_demo_999"
    assert result.instance_path == template
    assert "Bypassed PlanAgent" in (result.plan_summary or "")
