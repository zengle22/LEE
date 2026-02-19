from lee.orchestrator.execution.agent_context_builder import AgentContextBuilder
from lee.orchestrator.execution.agent_loader import AgentSpec


def test_agent_spec_to_dict_handles_object_output_schema() -> None:
    builder = AgentContextBuilder(agent_loader=None)
    spec = AgentSpec(
        id="agent.office.file_value_analyzer",
        name="File Value Analyzer",
        version="1.0",
        contracts={
            "output_schema": {
                "type": "object",
                "properties": {
                    "analysis_result": {"type": "object"},
                },
            }
        },
        persona={"role": "文件价值分析专家"},
    )

    data = builder._agent_spec_to_dict(spec)
    assert isinstance(data["system_prompt"], str)
    assert "文件价值分析专家" in data["system_prompt"]
