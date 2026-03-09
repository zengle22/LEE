from __future__ import annotations

import importlib.util
from pathlib import Path


def load_pre_push_module():
    module_path = Path(__file__).resolve().parents[3] / "scripts" / "git-pre-push-hook.py"
    spec = importlib.util.spec_from_file_location("git_pre_push_hook", module_path)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_github_actions_workflow_is_not_treated_as_l3_template() -> None:
    module = load_pre_push_module()

    assert module.is_l3_template_related(".github/workflows/tag-release.yml") is False


def test_spec_global_workflow_template_is_treated_as_l3_template() -> None:
    module = load_pre_push_module()

    assert (
        module.is_l3_template_related(
            "spec-global/departments/product/workflows/templates/epic-to-feat/v1/workflow.yaml"
        )
        is True
    )


def test_lint_scripts_still_trigger_l3_validation() -> None:
    module = load_pre_push_module()

    assert module.is_l3_template_related("scripts/lint_l3_templates.py") is True
