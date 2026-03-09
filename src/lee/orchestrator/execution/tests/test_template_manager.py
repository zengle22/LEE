from pathlib import Path

from lee.orchestrator.execution.template_manager import TemplateManager


def test_load_template_from_content_keeps_workflow_inputs_out_of_step_input():
    manager = TemplateManager(project_root=str(Path.cwd()))
    template = manager.load_template_from_content(
        """
kind: l3_workflow_template
id: workflow.product.task.demo
name: Demo
stages:
  - id: stage_1
    steps:
      - id: feat_boundary_design
        kind: agent
        agent_id: agent.product.requirement_decomposer
        description: Demo step
        inputs:
          - source: epic_freeze
            required: true
        outputs:
          - symbol: feat_breakdown
            contract: departments/product/contracts/feat-breakdown-contract/v1/schema.json
""",
        template_id="workflow.product.task.demo",
    )

    step = template.steps[0]

    assert step.input == {
        "step_id": "feat_boundary_design",
        "name": "",
        "description": "Demo step",
    }
    assert step.config["workflow_inputs"] == [{"source": "epic_freeze", "required": True}]


def test_load_template_from_content_maps_symbol_outputs_to_symbol_specs():
    manager = TemplateManager(project_root=str(Path.cwd()))
    template = manager.load_template_from_content(
        """
kind: l3_workflow_template
id: workflow.product.task.demo
name: Demo
stages:
  - id: stage_1
    steps:
      - id: feat_boundary_design
        kind: agent
        agent_id: agent.product.requirement_decomposer
        outputs:
          - symbol: feat_breakdown
            contract: departments/product/contracts/feat-breakdown-contract/v1/schema.json
""",
        template_id="workflow.product.task.demo",
    )

    output = template.steps[0].outputs[0]

    assert output.type == "symbol"
    assert output.path == "feat_breakdown"
