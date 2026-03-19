from pathlib import Path

from lee.orchestrator.execution.template_manager import TemplateManager


def test_l3_template_uses_project_default_executor(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    template_root = project_root / "spec-global"
    template_root.mkdir(parents=True)
    (project_root / ".lee").mkdir()
    (project_root / ".lee" / "config.yaml").write_text(
        "executor:\n"
        "  default_type: claude_code\n",
        encoding="utf-8",
    )

    template_path = template_root / "workflow.yaml"
    template_path.write_text(
        "kind: l3_workflow_template\n"
        "id: workflow.product.task.src_to_epic\n"
        "name: Product SRC to EPIC\n"
        "description: test\n"
        "stages:\n"
        "  - id: flow\n"
        "    steps:\n"
        "      - id: raw_input_intake\n"
        "        kind: agent\n"
        "        agent_id: agent.analysis.product_goal\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root), project_root=str(project_root))
    template = manager.get_template(str(template_path))

    assert template is not None
    assert template.steps[0].executor_type == "claude_code"


def test_l3_template_preserves_step_inputs(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    template_root = project_root / "spec-global"
    template_root.mkdir(parents=True)
    (project_root / ".lee").mkdir()
    (project_root / ".lee" / "config.yaml").write_text(
        "executor:\n"
        "  default_type: claude_code\n",
        encoding="utf-8",
    )

    template_path = template_root / "workflow.yaml"
    template_path.write_text(
        "kind: l3_workflow_template\n"
        "id: workflow.product.task.src_to_epic\n"
        "name: Product SRC to EPIC\n"
        "description: test\n"
        "stages:\n"
        "  - id: flow\n"
        "    steps:\n"
        "      - id: raw_input_intake\n"
        "        kind: agent\n"
        "        agent_id: agent.analysis.product_goal\n"
        "        inputs:\n"
        "          - source: external\n"
        "            type: [business_opportunity]\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root), project_root=str(project_root))
    template = manager.get_template(str(template_path))

    assert template is not None
    assert getattr(template.steps[0], "inputs", []) == [
        {"source": "external", "type": ["business_opportunity"]}
    ]


def test_l3_template_parses_symbol_outputs(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    template_root = project_root / "spec-global"
    template_root.mkdir(parents=True)
    (project_root / ".lee").mkdir()
    (project_root / ".lee" / "config.yaml").write_text(
        "executor:\n"
        "  default_type: claude_code\n",
        encoding="utf-8",
    )

    template_path = template_root / "workflow.yaml"
    template_path.write_text(
        "kind: l3_workflow_template\n"
        "id: workflow.product.task.epic_to_feat\n"
        "name: Product EPIC to FEAT\n"
        "description: test\n"
        "stages:\n"
        "  - id: flow\n"
        "    steps:\n"
        "      - id: feat_identity_prepare\n"
        "        kind: agent\n"
        "        agent_id: agent.governance.approval_reviewer\n"
        "        outputs:\n"
        "          - symbol: feat_scoped_specs\n"
        "            contract: departments/product/contracts/feat-bundle-contract/v1/schema.json\n"
        "            freeze: false\n"
        "            ssot:\n"
        "              identity_kind: ssot\n"
        "              ssot_type: FEAT\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root), project_root=str(project_root))
    template = manager.get_template(str(template_path))

    assert template is not None
    output_spec = template.steps[0].outputs[0]
    assert output_spec.type == "symbol"
    assert output_spec.path == "feat_scoped_specs"
    assert output_spec.symbol == "feat_scoped_specs"
    assert output_spec.contract == "departments/product/contracts/feat-bundle-contract/v1/schema.json"
    assert output_spec.freeze is False
    assert output_spec.ssot == {"identity_kind": "ssot", "ssot_type": "FEAT"}


def test_l3_template_supports_phase_based_bridge_format(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    template_root = project_root / "spec-global"
    template_root.mkdir(parents=True)
    (project_root / ".lee").mkdir()
    (project_root / ".lee" / "config.yaml").write_text(
        "executor:\n"
        "  default_type: claude_code\n",
        encoding="utf-8",
    )

    template_path = template_root / "workflow.yaml"
    template_path.write_text(
        "kind: l3_workflow_template\n"
        "id: workflow.product.task.feat_to_release\n"
        "name: Product FEAT to RELEASE\n"
        "description: test\n"
        "phases:\n"
        "  - id: release_init\n"
        "    name: Release Init\n"
        "    depends_on: []\n"
        "  - id: release_validate\n"
        "    name: Release Validate\n"
        "    depends_on: [release_init]\n"
        "    gate:\n"
        "      type: auto_check\n"
        "      gate_id: gate.product.release_validate_gate\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root), project_root=str(project_root))
    template = manager.get_template(str(template_path))

    assert template is not None
    assert [step.id for step in template.steps] == ["release_init", "release_validate"]
    assert template.steps[0].kind == "phase"
    assert template.steps[1].kind == "gate"
    assert template.steps[1].gate_id == "gate.product.release_validate_gate"


def test_l3_template_supports_stage_based_bridge_format(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    template_root = project_root / "spec-global"
    template_root.mkdir(parents=True)
    (project_root / ".lee").mkdir()
    (project_root / ".lee" / "config.yaml").write_text(
        "executor:\n"
        "  default_type: claude_code\n",
        encoding="utf-8",
    )

    template_path = template_root / "workflow.yaml"
    template_path.write_text(
        "kind: l3_workflow_template\n"
        "id: workflow.dev.task.release_to_devplan\n"
        "name: Release to DEVPLAN\n"
        "description: test\n"
        "stages:\n"
        "  - id: devplan_init\n"
        "    name: DEVPLAN Init\n"
        "    depends_on: []\n"
        "  - id: task_validate\n"
        "    name: Task Validate\n"
        "    depends_on: [devplan_init]\n"
        "    gate:\n"
        "      type: auto_check\n"
        "      gate_id: gate.dev.task_validate_gate\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root), project_root=str(project_root))
    template = manager.get_template(str(template_path))

    assert template is not None
    assert [step.id for step in template.steps] == ["devplan_init", "task_validate"]
    assert template.steps[0].kind == "phase"
    assert template.steps[1].kind == "gate"
    assert template.steps[1].gate_id == "gate.dev.task_validate_gate"


def test_flat_template_preserves_agent_and_executor_aliases(tmp_path: Path) -> None:
    template_root = tmp_path / "templates"
    template_root.mkdir(parents=True)

    template_path = template_root / "legacy_task.yaml"
    template_path.write_text(
        "id: legacy_task\n"
        "level: task\n"
        "name: Legacy Task\n"
        "description: test\n"
        "steps:\n"
        "  - id: feat_boundary_design\n"
        "    kind: agent\n"
        "    agent_id: agent.product.prd_writer\n"
        "    executor_type: llm\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root))
    template = manager.get_template("legacy_task")

    assert template is not None
    assert template.steps[0].agent_id == "agent.product.prd_writer"
    assert template.steps[0].executor_type == "llm"


def test_spec_global_template_preserves_freeze_and_ssot_output_metadata(tmp_path: Path) -> None:
    project_root = tmp_path / "project"
    template_root = project_root / "spec-global"
    template_root.mkdir(parents=True)
    (project_root / ".lee").mkdir()
    (project_root / ".lee" / "config.yaml").write_text(
        "executor:\n"
        "  default_type: claude_code\n",
        encoding="utf-8",
    )

    template_path = template_root / "workflow.yaml"
    template_path.write_text(
        "kind: workflow\n"
        "id: workflow.product.task.src_to_epic\n"
        "version: '1.0'\n"
        "name: Product SRC to EPIC\n"
        "description: test\n"
        "stages:\n"
        "  - id: flow\n"
        "    name: flow\n"
        "    steps:\n"
        "      - id: epic_design\n"
        "        kind: agent\n"
        "        agent_id: agent.product.epic_designer\n"
        "        outputs:\n"
        "          - symbol: epic_candidate\n"
        "            contract: departments/product/contracts/epic-contract/v1/schema.json\n"
        "            freeze: false\n"
        "            ssot:\n"
        "              identity_kind: ssot\n"
        "              ssot_type: EPIC\n"
        "      - id: epic_freeze\n"
        "        kind: gate\n"
        "        outputs:\n"
        "          - path: output/design-frozen/{project}-epic-freeze.yaml\n"
        "            required: true\n"
        "            freeze: true\n"
        "            ssot:\n"
        "              identity_kind: ssot\n"
        "              ssot_type: EPIC\n",
        encoding="utf-8",
    )

    manager = TemplateManager(template_dir=str(template_root), project_root=str(project_root))
    template = manager.get_template(str(template_path))

    assert template is not None
    design_output = template.get_step_info("epic_design").outputs[0]
    freeze_output = template.get_step_info("epic_freeze").outputs[0]
    assert design_output.symbol == "epic_candidate"
    assert design_output.freeze is False
    assert design_output.ssot == {"identity_kind": "ssot", "ssot_type": "EPIC"}
    assert freeze_output.path == "output/design-frozen/{project}-epic-freeze.yaml"
    assert freeze_output.freeze is True
    assert freeze_output.ssot == {"identity_kind": "ssot", "ssot_type": "EPIC"}
