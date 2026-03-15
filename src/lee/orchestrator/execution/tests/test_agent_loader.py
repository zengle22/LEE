from pathlib import Path

from lee.orchestrator.execution.agent_loader import AgentLoader
from lee.orchestrator.execution.runners.base import StepRunnerBase


def test_agent_loader_prefers_spec_global_for_department_agents():
    project_root = Path.cwd()
    loader = AgentLoader(project_root=str(project_root))

    spec = loader.load("agent.product.prd_writer")

    assert spec.id == "agent.product.prd_writer"
    assert spec.contracts.get("ssot_output_schema")
    assert spec.spec_path
    assert "spec-global" in spec.spec_path.replace("\\", "/")


def test_department_agent_ssot_output_schema_paths_resolve_to_existing_spec_global_contract():
    project_root = Path.cwd()
    loader = AgentLoader(project_root=str(project_root))

    for agent_ref in ("agent.design.ui_designer",):
        spec = loader.load(agent_ref)
        resolved = StepRunnerBase._resolve_contract_path(
            schema_ref=spec.contracts["ssot_output_schema"],
            spec_path=spec.spec_path,
            project_root=str(project_root),
        )
        resolved_path = Path(resolved)

        assert resolved_path.exists(), f"{agent_ref} resolved to missing path: {resolved_path}"
        assert (
            resolved_path.as_posix().endswith(
                "spec-global/core/contracts/ssot-agent-output/v1/schema.json"
            )
        ), resolved_path


def test_product_epic_designer_emits_business_contract_only():
    loader = AgentLoader(project_root=str(Path.cwd()))

    spec = loader.load("agent.product.epic_designer")

    assert spec.contracts.get("output_schema")
    assert "ssot_output_schema" not in spec.contracts
