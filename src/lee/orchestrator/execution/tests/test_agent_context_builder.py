from pathlib import Path
from types import SimpleNamespace

import pytest

from lee.orchestrator.execution.agent_context_builder import AgentContextBuilder
from lee.orchestrator.ir.models import VariableIR


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


@pytest.mark.asyncio
async def test_default_prompt_includes_step_inputs_from_inputs_field(builder):
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        input={
            "step_id": "feat_boundary_design",
            "name": "FEAT 边界拆解",
        },
        inputs=[{"source": "epic_freeze", "required": True}],
        depends_on=[],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "epic_freeze": {
                    "epic_id": "EPIC-DEMO-001",
                    "title": "智能备赛计划生成",
                    "goal": "帮助用户基于比赛目标和训练约束快速生成可执行的备赛计划",
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Decompose EPIC into FEAT candidates only.",
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

    assert "## Input Data" in prompt
    assert "step_id" in prompt
    assert "epic_freeze" in prompt
    assert "EPIC-DEMO-001" in prompt
    assert "智能备赛计划生成" in prompt


@pytest.mark.asyncio
async def test_default_prompt_resolves_variable_input_references(builder):
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        input={
            "step_id": "feat_boundary_design",
            "source": VariableIR(
                reference="$inputs.epic_freeze",
                source_type="inputs",
                path=["epic_freeze"],
            ),
        },
        depends_on=[],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "epic_freeze": {
                    "epic_id": "EPIC-DEMO-001",
                    "title": "智能备赛计划生成",
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Decompose EPIC into FEAT candidates only.",
        }
    }

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "epic_freeze" in prompt
    assert "EPIC-DEMO-001" in prompt
    assert "智能备赛计划生成" in prompt


@pytest.mark.asyncio
async def test_default_prompt_reads_nested_inputs_from_step_input_metadata(builder):
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        input={
            "step_id": "feat_boundary_design",
            "name": "FEAT 边界拆解",
            "inputs": [{"source": "epic_freeze", "required": True}],
        },
        depends_on=[],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "epic_freeze": {
                    "epic_id": "EPIC-DEMO-001",
                    "title": "智能备赛计划生成",
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Decompose EPIC into FEAT candidates only.",
        }
    }

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "epic_freeze" in prompt
    assert "EPIC-DEMO-001" in prompt


@pytest.mark.asyncio
async def test_default_prompt_resolves_symbol_input_from_declared_upstream_output(builder):
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        input={
            "step_id": "feat_spec_generation",
            "inputs": [{"source": "feat_breakdown", "required": True}],
        },
        depends_on=["feat_boundary_design"],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "step_outputs": {
                "feat_boundary_design": {
                    "feat_breakdown": {
                        "breakdown_id": "FEAT-BREAKDOWN-001",
                        "epic_ref": "EPIC-DEMO-001",
                    },
                    "business_output": {
                        "breakdown_id": "IGNORED-BY-INPUT-RESOLVER",
                        "epic_ref": "EPIC-OTHER-001",
                    }
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Generate FEAT spec objects.",
        }
    }

    resolved_inputs = builder._collect_step_inputs(step, workflow_context)

    assert resolved_inputs["feat_breakdown"]["breakdown_id"] == "FEAT-BREAKDOWN-001"
    assert resolved_inputs["feat_breakdown"]["epic_ref"] == "EPIC-DEMO-001"


@pytest.mark.asyncio
async def test_default_prompt_does_not_backfill_unresolved_input_from_upstream_business_output(builder):
    step = SimpleNamespace(
        id="feat_spec_generation",
        agent_id="agent.product.prd_writer",
        input={
            "step_id": "feat_spec_generation",
            "inputs": [{"source": "feat_breakdown", "required": True}],
        },
        depends_on=["feat_boundary_design"],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "step_outputs": {
                "feat_boundary_design": {
                    "business_output": {
                        "breakdown_id": "FEAT-BREAKDOWN-001",
                        "epic_ref": "EPIC-DEMO-001",
                    }
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Generate FEAT spec objects.",
        }
    }

    resolved_inputs = builder._collect_step_inputs(step, workflow_context)

    assert resolved_inputs["feat_breakdown"] == {"source": "feat_breakdown", "required": True}


@pytest.mark.asyncio
async def test_default_prompt_reads_workflow_inputs_from_step_config(builder):
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        input={
            "step_id": "feat_boundary_design",
            "name": "FEAT 边界拆解",
        },
        config={
            "workflow_inputs": [{"source": "epic_freeze", "required": True}],
        },
        depends_on=[],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "epic_freeze": {
                    "epic_id": "EPIC-DEMO-001",
                    "title": "智能备赛计划生成",
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Decompose EPIC into FEAT candidates only.",
        }
    }

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "epic_freeze" in prompt
    assert "EPIC-DEMO-001" in prompt
