from pathlib import Path

from lee.orchestrator.execution.agent_loader import AgentLoader


def test_loads_spec_global_department_agent_layout(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    spec_root = project_root / "spec-global"
    agent_file = (
        spec_root
        / "departments"
        / "office"
        / "agents"
        / "file-value-analyzer"
        / "v1"
        / "agent.yaml"
    )
    agent_file.parent.mkdir(parents=True, exist_ok=True)
    agent_file.write_text(
        "\n".join(
            [
                "id: agent.office.file_value_analyzer",
                "name: File Value Analyzer",
                "version: 1.0",
                "persona:",
                '  role: "文件价值分析专家"',
            ]
        ),
        encoding="utf-8",
    )

    loader = AgentLoader(str(project_root), spec_root=str(spec_root))
    spec = loader.load("agent.office.file_value_analyzer")

    assert spec is not None
    assert spec.id == "agent.office.file_value_analyzer"
    assert spec.name == "File Value Analyzer"
    assert spec.persona.get("role") == "文件价值分析专家"
