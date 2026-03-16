import json
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
    assert "product.raw-to-src" in workflows
    assert "product.src-to-epic" in workflows
    assert "product.epic-to-feat" in workflows
    assert "product.feat-to-delivery-prep" in workflows
    assert "product.requirement-chain-validation" in workflows

    assert workflows["product.main"]["path"] == (
        "spec-global/departments/product/workflows/templates/product-main-pipeline/v1/workflow.yaml"
    )
    assert workflows["product.main"]["kind"] == "l2_workflow_template"
    assert workflows["product.main"]["load_spec_as_params"] is True
    assert workflows["product.raw-to-src"]["path"] == (
        "spec-global/departments/product/workflows/templates/raw-to-src/v1/workflow.yaml"
    )
    assert workflows["product.raw-to-src"]["load_spec_as_params"] is True
    assert "adr" in workflows["product.main"]["optional_params"]
    assert "adr" in workflows["product.raw-to-src"]["optional_params"]
    assert "raw_requirement" in workflows["product.raw-to-src"]["optional_params"]
    assert "business_opportunity_freeze" in workflows["product.raw-to-src"]["optional_params"]
    assert workflows["product.src-to-epic"]["description"] == "Product L3 - frozen SRC to EPIC"
    assert "src" in workflows["product.src-to-epic"]["optional_params"]
    assert "source_freeze" in workflows["product.src-to-epic"]["optional_params"]
    assert "source_freeze_ref" in workflows["product.src-to-epic"]["optional_params"]
    assert workflows["product.epic-to-feat"]["load_spec_as_params"] is True
    assert workflows["product.feat-to-delivery-prep"]["load_spec_as_params"] is True
    assert workflows["product.requirement-chain-validation"]["load_spec_as_params"] is True
    assert workflows["product.epic-to-feat"]["required_params"] == ["epic_freeze"]
    assert workflows["product.feat-to-delivery-prep"]["required_params"] == ["feat_freeze"]
    assert "delivery_prep_bundle" in workflows["product.requirement-chain-validation"]["optional_params"]

def test_product_main_pipeline_template_uses_validation_stage_before_completion() -> None:
    template_path = (
        Path(__file__).resolve().parents[1]
        / "spec-global"
        / "departments"
        / "product"
        / "workflows"
        / "templates"
        / "product-main-pipeline"
        / "v1"
        / "workflow.yaml"
    )
    doc = yaml.safe_load(template_path.read_text(encoding="utf-8"))
    phases = doc["phases"]

    assert [phase["id"] for phase in phases] == [
        "raw_to_src",
        "src_to_epic",
        "epic_to_feat",
        "feat_to_delivery_prep",
        "requirement_chain_validation",
    ]
    assert phases[0]["workflow"] == "workflow.product.task.raw_to_src"
    assert phases[1]["depends_on"] == ["raw_to_src"]
    assert phases[-1]["workflow"] == "workflow.product.task.requirement_chain_validation"
    assert phases[-1]["depends_on"] == ["feat_to_delivery_prep"]


def test_product_pipeline_handoff_contracts_are_aligned() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    main_doc = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "product"
            / "workflows"
            / "templates"
            / "product-main-pipeline"
            / "v1"
            / "workflow.yaml"
        ).read_text(encoding="utf-8")
    )
    raw_doc = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "product"
            / "workflows"
            / "templates"
            / "raw-to-src"
            / "v1"
            / "workflow.yaml"
        ).read_text(encoding="utf-8")
    )
    src_doc = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "product"
            / "workflows"
            / "templates"
            / "src-to-epic"
            / "v1"
            / "workflow.yaml"
        ).read_text(encoding="utf-8")
    )

    main_input_types = {item["type"] for item in main_doc["overview"]["input_types"]}
    raw_input_types = {item["type"] for item in raw_doc["overview"]["input_types"]}
    raw_external_types = set(raw_doc["stages"][0]["steps"][0]["inputs"][0]["type"])
    src_input_types = {item["type"] for item in src_doc["overview"]["input_types"]}
    src_external_types = set(src_doc["stages"][0]["steps"][0]["inputs"][0]["type"])

    assert "adr" in main_input_types
    assert "adr" in raw_input_types
    assert "adr" in raw_external_types
    assert "business_opportunity_freeze" in main_input_types
    assert "business_opportunity_freeze" in raw_input_types
    assert "business_opportunity_freeze" in raw_external_types
    assert {"src", "source_freeze"}.issubset(src_input_types)
    assert {"src", "source_freeze"}.issubset(src_external_types)


def test_requirement_chain_validation_template_requires_delivery_outputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    validation_doc = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "product"
            / "workflows"
            / "templates"
            / "requirement-chain-validation"
            / "v1"
            / "workflow.yaml"
        ).read_text(encoding="utf-8")
    )
    steps = validation_doc["stages"][0]["steps"]

    assert validation_doc["id"] == "workflow.product.task.requirement_chain_validation"
    assert [step["id"] for step in steps] == [
        "requirement_chain_test_execution",
        "requirement_chain_review",
        "requirement_chain_validation_gate",
    ]
    execution_inputs = {item["source"] for item in steps[0]["inputs"]}
    assert {"source_freeze", "epic_freeze_bundle", "feat_freeze_bundle", "delivery_prep_bundle"} == execution_inputs


def test_source_freeze_contract_supports_governance_bridge_src() -> None:
    contract_path = (
        Path(__file__).resolve().parents[1]
        / "spec-global"
        / "departments"
        / "product"
        / "contracts"
        / "source-freeze-contract"
        / "v1"
        / "schema.json"
    )
    doc = json.loads(contract_path.read_text(encoding="utf-8"))

    assert "source_kind" in doc["properties"]
    assert "bridge_context" in doc["properties"]
    assert "governance_bridge_src" in doc["properties"]["source_kind"]["enum"]
    assert "bridge_context" in doc["allOf"][0]["then"]["required"]


def test_workflow_registry_updates_qa_test_set_production_inputs() -> None:
    registry = _load_registry()
    entry = registry["workflows"]["qa.test-set-production"]

    assert entry["path"] == "spec-global/departments/qa/workflows/templates/test-set-production-l3-template.yaml"
    assert entry["load_spec_as_params"] is True
    assert "feat_freeze" in entry["required_params"]
    assert "requirement_doc" in entry["optional_params"]
    assert "delivery_prep_bundle" in entry["optional_params"]


def test_workflow_registry_updates_qa_test_plan_execution_inputs() -> None:
    registry = _load_registry()
    entry = registry["workflows"]["qa.test-plan-execution"]

    assert entry["path"] == "spec-global/departments/qa/workflows/templates/test-plan-l2-template.yaml"
    assert entry["required_params"] == ["test_plan_id", "build_version", "build_commit"]
    assert "release_ref" in entry["optional_params"]
    assert "task_ref" in entry["optional_params"]
    assert "base_url" in entry["optional_params"]


def test_qa_test_plan_template_declares_canonical_delivery_context() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    template_doc = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "workflows"
            / "templates"
            / "test-plan-l2-template.yaml"
        ).read_text(encoding="utf-8")
    )

    context_fields = template_doc["instance_schema"]["context_fields"]
    metrics = {metric["name"]: metric["labels"] for metric in template_doc["observability"]["metrics"]}

    assert "release_ref" in context_fields
    assert "task_ref" in context_fields
    assert metrics["l2_execution_duration"][:2] == ["release_ref", "test_plan_id"]
    assert metrics["test_set_execution_duration"] == ["release_ref", "test_plan_id"]


def test_qa_test_set_execution_template_declares_delivery_trace_context() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    template_doc = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "workflows"
            / "templates"
            / "test-set-execute-l3-template.yaml"
        ).read_text(encoding="utf-8")
    )

    context_fields = template_doc["instance_schema"]["context_fields"]
    output_fields = template_doc["instance_schema"]["output_fields"]
    metrics = {metric["name"]: metric["labels"] for metric in template_doc["observability"]["metrics"]}
    steps = {
        step["id"]: step
        for stage in template_doc["stages"]
        for step in stage["steps"]
    }

    assert "release_ref" in context_fields
    assert "test_plan_id" in context_fields
    assert "task_ref" in context_fields
    assert "testset_ref" in context_fields
    assert output_fields[:3] == ["release_ref", "test_plan_id", "task_ref"]
    assert metrics["l3_execution_duration"][:4] == ["release_ref", "test_plan_id", "task_ref", "test_set_id"]
    assert steps["case_generation"]["outputs"][0]["path"] == "spec/testing/evidence/{{ test_run_id }}/cases.yaml"
    assert steps["script_translation"]["outputs"][0]["path"] == "spec/testing/evidence/{{ test_run_id }}/scripts/"
    assert steps["script_execution"]["outputs"][0]["path"] == "spec/testing/evidence/{{ test_run_id }}/runner-output.json"
    assert steps["script_execution"]["outputs"][1]["path"] == "spec/testing/evidence/{{ test_run_id }}/bundle/"
    assert steps["behavior_compliance"]["outputs"][0]["path"] == "spec/testing/evidence/{{ test_run_id }}/compliance-result.json"
    assert steps["result_judgment"]["outputs"][0]["path"] == "spec/testing/evidence/{{ test_run_id }}/results.yaml"
    assert steps["tse_assembly"]["outputs"][0]["path"] == "spec/testing/evidence/{{ test_run_id }}/tse.yaml"
    assert steps["bug_drafting"]["outputs"][0]["path"] == "spec/testing/bugs/{{ test_run_id }}/"


def test_qa_l2_template_declares_canonical_l3_output_trace() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    template_path = (
        repo_root
        / "spec-global"
        / "departments"
        / "qa"
        / "workflows"
        / "templates"
        / "test-plan-l2-template.yaml"
    )
    template_text = template_path.read_text(encoding="utf-8")
    template_doc = yaml.safe_load(template_text)

    l3_output_schema = template_doc["l3_output_schema"]
    required_fields = l3_output_schema["required_fields"]
    optional_fields = l3_output_schema["optional_fields"]

    assert required_fields[:3] == ["release_ref", "test_plan_id", "task_ref"]
    assert "Canonical execution artifacts must be materialized under `spec/testing/*`" in template_text
    assert "tse_path  # Canonical TSE evidence path under spec/testing/evidence/" in template_text
    assert "bug_drafts  # Canonical bug artifact paths under spec/testing/bugs/" in template_text
    assert "compliance_result_path  # Canonical evidence path under spec/testing/evidence/" in template_text
    assert optional_fields == ["skip_reason", "failure_reason", "invalid_run_reason", "compliance_result_path"]


def test_qa_tse_and_bug_agents_require_delivery_trace_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    tse_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "tse-assembler"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )
    bug_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "bug-drafter"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )

    tse_input_names = [item["name"] for item in tse_agent["inputs"]]
    bug_properties = bug_agent["contracts"]["input_schema"]["properties"]

    assert tse_input_names[:3] == ["release_ref", "test_plan_id", "task_ref"]
    assert "release_ref" in bug_properties
    assert "test_plan_id" in bug_properties
    assert "task_ref" in bug_properties


def test_qa_bug_summary_and_report_agents_require_canonical_delivery_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    bug_summary_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "bug-summarizer"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )
    report_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "report-generator"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )
    bug_summary_contract = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "contracts"
            / "bug-summary"
            / "v1"
            / "schema.yaml"
        ).read_text(encoding="utf-8")
    )

    bug_required = bug_summary_agent["contracts"]["input_schema"]["required"]
    report_required = report_agent["contracts"]["input_schema"]["required"]
    bug_summary_required = bug_summary_contract["schema"]["required"]
    instructions = bug_summary_agent["prompting"]["instructions"]

    assert bug_required[:3] == ["release_ref", "test_plan_id", "task_ref"]
    assert report_required[:2] == ["release_ref", "task_refs"]
    assert bug_summary_required[:3] == ["release_ref", "test_plan_id", "task_refs"]
    assert any("spec/testing/bugs/" in instruction for instruction in instructions)


def test_qa_report_generator_declares_canonical_report_outputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    report_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "report-generator"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )

    output_formats = report_agent["prompting"]["output_format"]
    instructions = report_agent["prompting"]["instructions"]

    assert output_formats[0]["yaml"] == "spec/testing/reports/{release_ref}-test-report.yaml"
    assert output_formats[1]["markdown"] == "spec/testing/reports/{release_ref}-test-report.md"
    assert any("spec/testing/reports/" in instruction for instruction in instructions)


def test_qa_exit_and_retrospective_agents_require_delivery_trace_inputs() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    exit_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "exit-evaluator"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )
    retrospective_agent = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "retrospective-generator"
            / "v1"
            / "agent.yaml"
        ).read_text(encoding="utf-8")
    )
    retrospective_contract = yaml.safe_load(
        (
            repo_root
            / "spec-global"
            / "departments"
            / "qa"
            / "contracts"
            / "retrospective"
            / "v1"
            / "schema.yaml"
        ).read_text(encoding="utf-8")
    )

    exit_required = exit_agent["contracts"]["input_schema"]["required"]
    retrospective_required = retrospective_agent["contracts"]["input_schema"]["required"]
    retrospective_schema_required = retrospective_contract["schema"]["required"]
    retrospective_output_format = retrospective_agent["prompting"]["output_format"]

    assert exit_required[:3] == ["release_ref", "test_plan_id", "task_refs"]
    assert retrospective_required[:3] == ["release_ref", "test_plan_id", "task_refs"]
    assert retrospective_schema_required[:3] == ["release_ref", "test_plan_id", "task_refs"]
    assert retrospective_output_format[0]["yaml"] == "spec/testing/reports/{release_ref}-retrospective.yaml"
    assert retrospective_output_format[1]["markdown"] == "spec/testing/reports/{release_ref}-retrospective.md"


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
