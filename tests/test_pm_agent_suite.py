
import pytest
import os
import time
import json
from lee.orchestrator.execution.pm_agent_session import PMAgentSession, SessionState

def test_session_persistence(tmp_path):
    session = PMAgentSession(str(tmp_path))
    state = SessionState("sess1", "run1", time.time(), "history", {})
    
    session.save("sess1", state)
    loaded = session.restore("sess1")
    
    assert loaded
    assert loaded.session_id == "sess1"
    assert loaded.run_id == "run1"
    
def test_list_active(tmp_path):
    session = PMAgentSession(str(tmp_path))
    now = time.time()
    
    # Active
    s1 = SessionState("sess1", "run1", now, "", {})
    session.save("sess1", s1)
    
    # Old
    s2 = SessionState("sess2", "run2", now - 10000, "", {})
    session.save("sess2", s2)
    
    active = session.list_active(max_age_seconds=5000)
    assert len(active) == 1
    assert active[0].session_id == "sess1"


def test_session_saved_under_workflow_runtime_dir(tmp_path):
    session = PMAgentSession(str(tmp_path))
    state = SessionState("sess_runtime", "run_runtime", time.time(), "history", {})
    session.save("sess_runtime", state)

    saved_path = tmp_path / ".workflow" / "runtime" / "pm_agent_sessions" / "sess_runtime.json"
    assert saved_path.exists()


def test_restore_falls_back_to_legacy_pm_agent_sessions_dir(tmp_path):
    legacy_dir = tmp_path / ".lee" / "pm_agent_sessions"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_path = legacy_dir / "legacy_sess.json"

    payload = {
        "session_id": "legacy_sess",
        "run_id": "wf_legacy",
        "last_active_timestamp": time.time(),
        "history_summary": "legacy",
        "metadata": {"source": "legacy"},
    }
    legacy_path.write_text(json.dumps(payload), encoding="utf-8")

    session = PMAgentSession(str(tmp_path))
    restored = session.restore("legacy_sess")

    assert restored is not None
    assert restored.session_id == "legacy_sess"
    assert restored.run_id == "wf_legacy"

# --- Runtime Tests ---

from unittest.mock import MagicMock, AsyncMock
from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime, ProgressReport, CompiledParams
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.execution.pm_agent.models import APIResponse

@pytest.fixture
def runtime_env():
    # Mock data store
    store = MagicMock()
    # Mock orchestrator
    orchestrator = MagicMock(spec=Orchestrator)
    orchestrator.store = store
    
    llm = MagicMock()
    
    runtime = PMAgentRuntime(orchestrator, llm, store)
    return runtime, store

@pytest.mark.asyncio
async def test_progress_report(runtime_env):
    runtime, store = runtime_env
    
    # Mock workflow retrieval
    wf = MagicMock()
    wf.status.value = "running"
    wf.current_step = "step1"
    wf.data = {"completed_steps": ["step0"]}
    store.get_workflow = AsyncMock(return_value=wf)
    
    report = await runtime.get_progress_report("run1")
    
    assert report.run_id == "run1"
    assert report.status == "running"
    assert report.current_step == "step1"
    assert len(report.completed_steps) == 1
    assert "Steps completed: 1" in report.patch_summary

@pytest.mark.asyncio
async def test_completion_summary_not_found(runtime_env):
    runtime, store = runtime_env
    store.get_workflow = AsyncMock(return_value=None)
    
    summary = await runtime.generate_completion_summary("run2")
    assert summary.status == "not_found"

@pytest.mark.asyncio
async def test_amend_workflow(runtime_env):
    runtime, store = runtime_env
    
    wf = MagicMock()
    wf.status.value = "running"
    wf.data = {"params": {"a": 1}}
    store.get_workflow = AsyncMock(return_value=wf)
    store.update_workflow_data = AsyncMock()
    
    success = await runtime.amend_workflow("run1", {"params": {"b": 2}})
    
    assert success
    store.update_workflow_data.assert_awaited_once()
    assert wf.data["params"] == {"a": 1, "b": 2}


@pytest.mark.asyncio
async def test_process_input_persists_template_resolution_history(tmp_path):
    store = MagicMock()
    orchestrator = MagicMock(spec=Orchestrator)
    orchestrator.store = store
    runtime = PMAgentRuntime(
        orchestrator=orchestrator,
        llm_executor=None,
        store=store,
        project_dir=str(tmp_path),
        enable_decision_engine=False,
    )

    runtime.compile_prompt = AsyncMock(return_value=CompiledParams(
        workflow_ref="workflow.office.workspace_cleanup",
        params={
            "action": "run_workflow",
            "template_id": "workflow.office.workspace_cleanup",
            "template_input": "workspace_cleanup",
            "template_resolved": "workflow.office.workspace_cleanup",
        },
        confidence=0.95,
        reasoning="test",
        action="run_workflow",
        allowed=True,
        denial_reason=None,
    ))
    runtime.execute_decision = AsyncMock(return_value=APIResponse(
        status="success",
        data={
            "workflow_id": "wf_task_123",
            "template_id": "workflow.office.workspace_cleanup",
            "template_input": "workspace_cleanup",
            "template_resolved": "workflow.office.workspace_cleanup",
        },
        error=None,
        action="run_workflow",
    ))

    await runtime.process_input("全新运行工作流workspace_cleanup", session_id="sess_template")
    state = runtime.session_manager.restore("sess_template")

    assert state is not None
    assert state.run_id == "wf_task_123"
    assert state.history_summary == "1 turns"
    assert state.metadata.get("last_template_resolution") == {
        "input": "workspace_cleanup",
        "resolved": "workflow.office.workspace_cleanup",
    }
    history = state.metadata.get("interaction_history", [])
    assert len(history) == 1
    assert history[0]["action"] == "run_workflow"
    assert history[0]["template_resolution"]["resolved"] == "workflow.office.workspace_cleanup"


@pytest.mark.asyncio
async def test_get_or_create_context_loads_interaction_history(tmp_path):
    store = MagicMock()
    orchestrator = MagicMock(spec=Orchestrator)
    orchestrator.store = store
    runtime = PMAgentRuntime(
        orchestrator=orchestrator,
        llm_executor=None,
        store=store,
        project_dir=str(tmp_path),
        enable_decision_engine=False,
    )

    state = SessionState(
        session_id="sess_restore",
        run_id="wf_task_9",
        last_active_timestamp=time.time(),
        history_summary="2 turns",
        metadata={
            "department": "office",
            "user_permissions": ["lee.workflow.run"],
            "interaction_history": [
                {"user_input": "a", "action": "get_state", "status": "success"},
                {"user_input": "b", "action": "run_workflow", "status": "success"},
            ],
        },
    )
    runtime.session_manager.save("sess_restore", state)

    context = await runtime._get_or_create_context("sess_restore")
    assert context.current_workflow_id == "wf_task_9"
    assert context.department == "office"
    assert len(context.history) == 2
    assert context.history[-1]["action"] == "run_workflow"
