from pathlib import Path

import yaml


def test_all_agent_specs_are_valid_yaml() -> None:
    root = Path("spec-global")
    agent_files = sorted(root.rglob("agent.yaml"))
    assert agent_files, "No agent.yaml files found under spec-global"

    for agent_file in agent_files:
        text = agent_file.read_text(encoding="utf-8")
        yaml.safe_load(text)

