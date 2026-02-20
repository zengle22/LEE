from pathlib import Path
import re

import yaml


JINJA_CONTROL_TAG = re.compile(r"\{%\s*.*?%\}")


def test_office_agent_yaml_parseable_and_no_jinja_control_tags() -> None:
    root = Path("spec-global/departments/office/agents")
    agent_files = sorted(root.rglob("agent.yaml"))
    assert agent_files, "No office agent specs found"

    for agent_file in agent_files:
        text = agent_file.read_text(encoding="utf-8")
        assert not JINJA_CONTROL_TAG.search(text), (
            f"Found unrendered Jinja control tag in {agent_file}"
        )
        yaml.safe_load(text)

