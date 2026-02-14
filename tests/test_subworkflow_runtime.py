import asyncio
import os
import sys
import tempfile

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
src_dir = os.path.join(project_root, "src")
sys.path.insert(0, src_dir)

from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.template_manager import TemplateManager
from lee.orchestrator.storage.models import WorkflowLevel, WorkflowStatus
from lee.orchestrator.storage.sqlite_store import SQLiteStore


def test_template_manager_parses_subworkflow_kind() -> None:
    tm = TemplateManager()

    template = tm._parse_template_doc(
        {
            "kind": "workflow",
            "id": "workflow.parent.spec",
            "name": "Parent Spec",
            "stages": [
                {
                    "id": "s1",
                    "steps": [
                        {
                            "id": "spawn_child",
                            "type": "subworkflow",
                            "subworkflow": {"ref": "workflow.child.spec", "level": "task"},
                            "dependencies": {"requires": ["prepare"]},
                        },
                        {
                            "id": "prepare",
                            "type": "skill",
                            "run": "skill.git.checkout",
                        },
                    ],
                }
            ],
        },
        "workflow.parent.spec",
    )

    spawn_step = next(step for step in template.steps if step.id == "spawn_child")
    assert spawn_step.kind == "workflow_spawn"
    assert spawn_step.depends_on == ["prepare"]
    assert spawn_step.config.get("subworkflow_ref") == "workflow.child.spec"
    assert spawn_step.config.get("subworkflow_level") == "task"


def test_subworkflow_spawn_backfills_parent_output() -> None:
    asyncio.run(_run_subworkflow_spawn_backfill_case())


async def _run_subworkflow_spawn_backfill_case() -> None:
    # Enable demo mode so skill steps in the child workflow return mock success
    old_demo = os.environ.get("LEE_DEMO_MODE")
    os.environ["LEE_DEMO_MODE"] = "1"
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "orchestrator.db")
            store = SQLiteStore(db_path)
            await store.connect()

            tm = TemplateManager()
            tm._cache["workflow.child"] = tm._parse_template_doc(
                {
                    "id": "workflow.child",
                    "level": "task",
                    "name": "Child Workflow",
                    "steps": [
                        {
                            "id": "child_impl",
                            "kind": "skill",
                            "outputs": [{"path": "output/child-result.json"}],
                        }
                    ],
                },
                "workflow.child",
            )
            tm._cache["workflow.parent"] = tm._parse_template_doc(
                {
                    "id": "workflow.parent",
                    "level": "task",
                    "name": "Parent Workflow",
                    "steps": [
                        {
                            "id": "spawn_child",
                            "kind": "workflow_spawn",
                            "workflow": "workflow.child",
                            "input_map": {
                                "source_spec": "$inputs.spec",
                                "source_branch": "$inputs.branch",
                                "literal_tag": "feature-l2",
                            },
                            "output_map": {
                                "child_id": "$child.child_workflow_id",
                                "child_status": "$child.child_status",
                                "child_run_id": "$child.child_run_id",
                                "child_completed_steps": "$child.completed_steps",
                            },
                        }
                    ],
                },
                "workflow.parent",
            )

            orchestrator = Orchestrator(store, tm, project_root=temp_dir)

            parent = await orchestrator.create_workflow(
                level=WorkflowLevel.TASK,
                template_id="workflow.parent",
                data={"params": {"spec": "feature.yaml", "branch": "main"}},
            )

            result = await orchestrator.run_step(parent.id)
            assert result.status == "success"

            parent_state = await orchestrator.get_state(parent.id)
            assert parent_state.status == WorkflowStatus.COMPLETED

            subworkflow_outputs = parent_state.data.get("subworkflow_outputs", {})
            assert "spawn_child" in subworkflow_outputs

            backfill = subworkflow_outputs["spawn_child"]
            assert backfill["child_template_id"] == "workflow.child"
            assert backfill["child_status"] == "completed"
            assert backfill["evidence_refs"]

            child_ids = parent_state.data.get("subworkflow_children", {})
            child_workflow_id = child_ids.get("spawn_child")
            assert child_workflow_id
            child = await store.get_workflow(child_workflow_id)
            assert child is not None
            assert child.data.get("params", {}).get("source_spec") == "feature.yaml"
            assert child.data.get("params", {}).get("source_branch") == "main"
            assert child.data.get("params", {}).get("literal_tag") == "feature-l2"

            artifacts = parent_state.data.get("artifacts", {})
            assert artifacts.get("child_id") == child_workflow_id
            assert artifacts.get("child_status") == "completed"
            assert isinstance(artifacts.get("child_completed_steps"), list)

            await store.close()
    finally:
        if old_demo is None:
            os.environ.pop("LEE_DEMO_MODE", None)
        else:
            os.environ["LEE_DEMO_MODE"] = old_demo


def test_human_gate_global_blocks_workflow() -> None:
    asyncio.run(_run_human_gate_global_block_case())


async def _run_human_gate_global_block_case() -> None:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".db") as temp_file:
        db_path = temp_file.name

    try:
        store = SQLiteStore(db_path)
        await store.connect()

        tm = TemplateManager()
        tm._cache["workflow.gate_global_block"] = tm._parse_template_doc(
            {
                "id": "workflow.gate_global_block",
                "level": "task",
                "name": "Gate Global Block Workflow",
                "steps": [
                    {
                        "id": "manual_gate",
                        "kind": "human_gate",
                        "gate": {"id": "gate.manual"},
                    },
                    {
                        "id": "independent_step",
                        "kind": "skill",
                    },
                ],
            },
            "workflow.gate_global_block",
        )

        orchestrator = Orchestrator(store, tm)
        workflow = await orchestrator.create_workflow(
            level=WorkflowLevel.TASK,
            template_id="workflow.gate_global_block",
        )

        gate_result = await orchestrator.run_step(workflow.id)
        assert gate_result.status == "blocked"

        state = await orchestrator.get_state(workflow.id)
        assert state.status == WorkflowStatus.PAUSED

        ready_steps = await orchestrator.get_ready_steps(workflow.id)
        assert ready_steps == []

        await store.close()
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
