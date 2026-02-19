
import pytest
import os
import time
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

# --- Runtime Tests ---

from unittest.mock import MagicMock, AsyncMock
from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime, ProgressReport
from lee.orchestrator.execution.orchestrator import Orchestrator

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
