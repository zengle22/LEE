from pathlib import Path

from lee.orchestrator.execution.agent_loader import AgentLoader


def test_agent_loader_prefers_spec_global_for_department_agents():
    project_root = Path.cwd()
    loader = AgentLoader(project_root=str(project_root))

    spec = loader.load("agent.product.prd_writer")

    assert spec.id == "agent.product.prd_writer"
    assert spec.contracts.get("ssot_output_schema")
    assert spec.spec_path
    assert "spec-global" in spec.spec_path.replace("\\", "/")
