from pathlib import Path

import pytest
import yaml

from lee.cli.commands.workflow_registry import (
    get_workflow_registry_path,
    resolve_workflow_template_path,
)
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


def test_workflow_registry_contains_product_templates() -> None:
    registry = _load_registry()
    workflows = registry["workflows"]

    assert "product.main" in workflows
    assert "product.src-to-epic" in workflows
    assert "product.epic-to-feat" in workflows
    assert "product.feat-to-delivery-prep" in workflows

    assert workflows["product.main"]["path"] == (
        "spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml"
    )
    assert workflows["product.main"]["kind"] == "l2_workflow_template"
    assert workflows["product.main"]["load_spec_as_params"] is True
    assert workflows["product.epic-to-feat"]["load_spec_as_params"] is True
    assert workflows["product.feat-to-delivery-prep"]["load_spec_as_params"] is True
    assert workflows["product.epic-to-feat"]["required_params"] == ["epic_freeze"]
    assert workflows["product.feat-to-delivery-prep"]["required_params"] == ["feat_freeze"]


def test_workflow_registry_updates_qa_test_set_production_inputs() -> None:
    registry = _load_registry()
    entry = registry["workflows"]["qa.test-set-production"]

    assert entry["path"] == "spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml"
    assert entry["load_spec_as_params"] is True
    assert "feat_freeze" in entry["required_params"]
    assert "requirement_doc" in entry["optional_params"]
    assert "delivery_prep_bundle" in entry["optional_params"]


def test_workflow_registry_is_resolved_from_framework_root(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.chdir(tmp_path)

    registry_path = get_workflow_registry_path()
    registry = _load_registry()

    assert registry_path == Path(__file__).resolve().parents[1] / "config" / "workflow-registry.yaml"
    assert "core.spec-governance" in registry["workflows"]


def test_workflow_template_path_is_resolved_relative_to_framework_registry(tmp_path: Path) -> None:
    template_path = resolve_workflow_template_path("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")

    assert template_path == (
        Path(__file__).resolve().parents[1]
        / "spec-global"
        / "core"
        / "workflows"
        / "templates"
        / "spec-governance-l3-template.yaml"
    ).resolve()
    assert template_path.exists()


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


def test_render_workflow_template_injects_params_at_top_level(tmp_path: Path) -> None:
    template_path = tmp_path / "demo-template.yaml"
    template_path.write_text(
        'outputs:\n  - path: "{{ module }}/{{ params.module }}/report.md"\n',
        encoding="utf-8",
    )

    rendered_path = _render_workflow_template(
        template_path,
        {"module": "demo-module"},
        tmp_path,
    )
    rendered = rendered_path.read_text(encoding="utf-8")

    assert "demo-module/demo-module/report.md" in rendered


def test_workflow_registry_respects_explicit_env_path(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "config" / "workflow-registry.yaml"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("workflows: {}\n", encoding="utf-8")

    monkeypatch.setenv("LEE_WORKFLOW_REGISTRY", str(registry_path))
    monkeypatch.delenv("LEE_FRAMEWORK_ROOT", raising=False)

    assert get_workflow_registry_path() == registry_path.resolve()
    assert _load_registry() == {"workflows": {}}


def test_workflow_template_path_supports_packaged_data_layout(monkeypatch, tmp_path: Path) -> None:
    registry_path = tmp_path / "lee" / "config" / "workflow-registry.yaml"
    template_path = tmp_path / "lee" / "data" / "spec-global" / "core" / "workflows" / "templates" / "spec-governance-l3-template.yaml"

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    template_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text("workflows: {}\n", encoding="utf-8")
    template_path.write_text("steps: []\n", encoding="utf-8")

    monkeypatch.setenv("LEE_WORKFLOW_REGISTRY", str(registry_path))
    monkeypatch.delenv("LEE_FRAMEWORK_ROOT", raising=False)

    resolved = resolve_workflow_template_path("spec-global/core/workflows/templates/spec-governance-l3-template.yaml")

    assert resolved == template_path.resolve()
