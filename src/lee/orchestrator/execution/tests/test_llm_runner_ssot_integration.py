import shutil
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from lee.orchestrator.execution.runners.base import RunnerContext
from lee.orchestrator.execution.runners.llm_runner import LLMRunner


@pytest.fixture
def temp_project_root():
    temp_dir = Path(tempfile.mkdtemp())
    yield temp_dir
    if temp_dir.exists():
        shutil.rmtree(temp_dir)


@pytest.fixture
def runner():
    return LLMRunner()


@pytest.fixture
def ctx(temp_project_root):
    agent_spec = SimpleNamespace(
        contracts={
            "ssot_output_schema": str(
                (Path.cwd() / "spec-global" / "core" / "contracts" / "ssot-agent-output" / "v1" / "schema.json").resolve()
            )
        },
        spec_path=str((Path.cwd() / "spec-global" / "departments" / "prd" / "agents" / "prd-writer" / "v1" / "agent.yaml").resolve()),
    )
    agent_loader = MagicMock()
    agent_loader.load.return_value = agent_spec
    agent_context_builder = SimpleNamespace(agent_loader=agent_loader)

    return RunnerContext(
        store=MagicMock(),
        state_machine=MagicMock(),
        event_log=MagicMock(),
        evidence_collector=MagicMock(),
        verifier_engine=MagicMock(),
        executor_factory=MagicMock(),
        agent_context_builder=agent_context_builder,
        contract_discovery=MagicMock(),
        file_output_handler=SimpleNamespace(project_root=temp_project_root),
        token_manager=MagicMock(),
        project_root=str(temp_project_root),
    )


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_from_agent_contract(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "contract_version": "1.0",
  "run_id": "run-ssot-001",
  "outputs": [
    {
      "key": "epic",
      "identity_kind": "ssot",
      "ssot_type": "epic",
      "title": "增长基础设施",
      "source_refs": ["SRC-001#1.2"]
    },
    {
      "key": "feat",
      "identity_kind": "ssot",
      "ssot_type": "feat",
      "title": "用户注册",
      "parent": "epic",
      "source_refs": ["epic#scope"]
    }
  ]
}
""".strip()

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
    )

    assert result is not None
    assert result["outputs"]["epic"]["id"] == "EPIC-001"
    assert result["outputs"]["feat"]["parent_id"] == "EPIC-001"
    assert len(result["materialized_files"]) == 2
    assert (temp_project_root / "spec" / "requirements" / "epics").exists()
    assert (temp_project_root / "spec" / "requirements" / "features").exists()


@pytest.mark.asyncio
async def test_materialize_ssot_outputs_from_envelope_payload(runner, ctx, temp_project_root):
    step = SimpleNamespace(
        id="write_prd",
        agent_id="agent.product.prd_writer",
        config={},
    )

    generated_text = """
{
  "business_output": {
    "metadata": {
      "is_frozen": true
    }
  },
  "ssot_output_contract": {
    "contract_version": "1.0",
    "run_id": "run-ssot-002",
    "outputs": [
      {
        "key": "feat",
        "identity_kind": "ssot",
        "ssot_type": "feat",
        "title": "用户注册"
      }
    ]
  }
}
""".strip()

    structured_payload = runner._parse_structured_output_if_possible(generated_text)
    business_output = runner._extract_business_output_payload(structured_payload, generated_text)

    assert business_output == {"metadata": {"is_frozen": True}}

    result = await runner._materialize_ssot_outputs(
        ctx=ctx,
        step=step,
        workflow_id="wf-001",
        generated_text=generated_text,
        structured_payload=structured_payload,
    )

    assert result is not None
    assert result["outputs"]["feat"]["id"] == "FEAT-001"
    assert len(result["materialized_files"]) == 1
    assert (temp_project_root / "spec" / "requirements" / "features").exists()
