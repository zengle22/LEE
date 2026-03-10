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
