from pathlib import Path

import pytest
import yaml

from lee.cli.commands.run import (
    _load_directory_context,
    _load_registry,
    _load_spec_option_as_params,
    _render_workflow_template,
)


def test_workflow_registry_contains_spec_governance() -> None:
    registry = _load_registry()
    workflows = registry["workflows"]

    assert "core.spec-governance" in workflows
    entry = workflows["core.spec-governance"]
    assert entry["path"] == "spec-global/core/workflows/templates/spec-governance-l3-template.yaml"
    assert entry["load_spec_as_params"] is True
    assert "strict_review_gate" in entry["optional_params"]
    assert "human_gate_reviewers" in entry["optional_params"]
    assert "human_gate_required" in entry["optional_params"]


def test_load_spec_option_as_params_reads_yaml(tmp_path: Path) -> None:
    spec_file = tmp_path / "spec-request.yaml"
    spec_file.write_text(
        "\n".join(
            [
                "request_id: spec-agent-login",
                "spec_kind: agent",
                "action: create",
                "change_request: add login repair agent",
            ]
        ),
        encoding="utf-8",
    )

    data = _load_spec_option_as_params(str(spec_file))

    assert data["request_id"] == "spec-agent-login"
    assert data["spec_kind"] == "agent"


def test_load_spec_option_as_params_rejects_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with pytest.raises(Exception):
        _load_spec_option_as_params(str(missing))


def test_load_directory_context_reads_dirs_yaml(tmp_path: Path) -> None:
    dirs_path = tmp_path / ".project" / "dirs.yaml"
    dirs_path.parent.mkdir(parents=True, exist_ok=True)
    dirs_path.write_text(
        yaml.safe_dump(
            {
                "directories": {
                    "docs_dir": {"path": "docs"},
                    "knowledge_dir": {"path": "knowledge"},
                    "tests_dir": {"path": "tests"},
                }
            },
            allow_unicode=True,
        ),
        encoding="utf-8",
    )

    context = _load_directory_context(tmp_path)

    assert context["docs_dir"] == "docs"
    assert context["knowledge_dir"] == "knowledge"
    assert context["tests_dir"] == "tests"


def test_render_workflow_template_injects_directory_context(tmp_path: Path) -> None:
    template_path = tmp_path / "demo-template.yaml"
    template_path.write_text(
        'outputs:\n  - path: "{{ docs_dir }}/reports/demo.md"\n',
        encoding="utf-8",
    )
    dirs_path = tmp_path / ".project" / "dirs.yaml"
    dirs_path.parent.mkdir(parents=True, exist_ok=True)
    dirs_path.write_text(
        yaml.safe_dump({"directories": {"docs_dir": {"path": "docs"}}}, allow_unicode=True),
        encoding="utf-8",
    )

    rendered_path = _render_workflow_template(template_path, {}, tmp_path)
    rendered = rendered_path.read_text(encoding="utf-8")

    assert "docs/reports/demo.md" in rendered
