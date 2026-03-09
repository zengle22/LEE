from pathlib import Path
from types import SimpleNamespace

import pytest

from lee.orchestrator.execution.agent_context_builder import AgentContextBuilder


@pytest.fixture
def builder():
    return AgentContextBuilder(agent_loader=None, project_root=str(Path.cwd()))


def test_build_output_contract_guidance_for_ssot_envelope(builder):
    agent_spec = {
        "_spec_path": str(
            Path.cwd()
            / "spec-global"
            / "departments"
            / "product"
            / "agents"
            / "prd-writer"
            / "v1"
            / "agent.yaml"
        ),
        "_raw_data": {
            "contracts": {
                "output_schema": "../../../../departments/product/contracts/feat-contract/v1/schema.json",
                "ssot_output_schema": "../../../../core/contracts/ssot-agent-output/v1/schema.json",
            },
            "ssot_output_contract": {
                "example": {
                    "business_output": {"feat_id": "FEAT-001"},
                    "ssot_output_contract": {
                        "contract_version": "1.0",
                        "run_id": "run-001",
                        "outputs": [
                            {
                                "key": "feat",
                                "identity_kind": "ssot",
                                "ssot_type": "feat",
                                "title": "demo",
                            }
                        ],
                    },
                }
            },
        },
    }
    step = SimpleNamespace(outputs=[SimpleNamespace(path="feat_specs", type="symbol")])

    guidance = builder._build_output_contract_guidance(agent_spec, step)
    rendered = "\n".join(guidance)

    assert "business_output" in rendered
    assert "ssot_output_contract" in rendered
    assert "wrapper keys" in rendered or "Do not invent wrapper keys" in rendered
    assert "feat_id" in rendered


def test_build_output_contract_guidance_for_file_plus_ssot(builder):
    agent_spec = {
        "_spec_path": str(
            Path.cwd()
            / "spec-global"
            / "departments"
            / "qa"
            / "agents"
            / "test-set-generator"
            / "v1"
            / "agent.yaml"
        ),
        "_raw_data": {
            "contracts": {
                "output_schema": "../../../contracts/test-set/v1/schema.yaml",
                "ssot_output_schema": "../../../../core/contracts/ssot-agent-output/v1/schema.json",
            },
        },
    }
    step = SimpleNamespace(
        outputs=[
            SimpleNamespace(path="spec/qa/test-sets/ts-demo-module.yaml", type="file"),
        ]
    )

    guidance = builder._build_output_contract_guidance(agent_spec, step)
    rendered = "\n".join(guidance)

    assert "file section" in rendered
    assert "`ssot_output_contract`" in rendered
    assert "test_set_id" in rendered


@pytest.mark.asyncio
async def test_default_prompt_includes_upstream_step_outputs(builder):
    step = SimpleNamespace(
        id="feat_review",
        agent_id="agent.product.feat_reviewer",
        input=[{"source": "feat_specs", "required": True}],
        depends_on=["feat_spec_generation"],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "feat_id": "FEAT-042",
                        "title": "训练计划智能调整",
                    }
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Review FEAT objects only.",
            "prompting": {
                "instructions": [
                    "Return JSON only.",
                ]
            },
        }
    }

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "## Upstream Step Outputs" in prompt
    assert "feat_spec_generation" in prompt
    assert "FEAT-042" in prompt
