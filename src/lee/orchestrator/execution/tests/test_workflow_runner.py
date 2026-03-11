from pathlib import Path

import pytest

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
