from pathlib import Path
from types import SimpleNamespace

import pytest

from lee.orchestrator.execution.agent_context_builder import AgentContextBuilder
from lee.orchestrator.execution.agent_loader import AgentLoader


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
    assert "authoritative derived inputs" in prompt


@pytest.mark.asyncio
async def test_upstream_step_outputs_drop_executor_wrapper_noise(builder):
    step = SimpleNamespace(
        id="source_review",
        agent_id="agent.analysis.source_review",
        input=[{"source": "normalized_src", "required": True}],
        depends_on=["source_normalization"],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "step_outputs": {
                "source_normalization": {
                    "status": "success",
                    "generated_text": "very long prose",
                    "debug_log_path": "/tmp/debug.log",
                    "prompt_user_path": "/tmp/prompt.user.txt",
                    "business_output": {
                        "metadata": {"src_id": "SRC-001"},
                        "core_goal": {"primary_statement": "build requirement chain tests"},
                    },
                }
            }
        }
    }
    agent_spec = {"_raw_data": {"description": "Review normalized SRC only."}}

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "SRC-001" in prompt
    assert "generated_text" not in prompt
    assert "debug_log_path" not in prompt
    assert "prompt_user_path" not in prompt


def test_sanitize_prompt_payload_can_fall_back_to_generated_text_by_default(builder):
    sanitized = builder._sanitize_prompt_payload(
        {
            "status": "success",
            "generated_text": "ADR-011 raw analysis summary with requirement-chain testing focus",
            "structured_payload": {"status": "success"},
            "debug_log_path": "/tmp/debug.log",
        }
    )

    assert sanitized["generated_text"].startswith("ADR-011 raw analysis summary")
    assert "debug_log_path" not in sanitized


@pytest.mark.asyncio
async def test_upstream_step_outputs_skip_generated_text_only_payloads(builder):
    step = SimpleNamespace(
        id="task_planning",
        agent_id="agent.product.pm_planner",
        input=[{"source": "tech_specs", "required": True}],
        depends_on=["tech_design"],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "step_outputs": {
                "tech_design": {
                    "status": "success",
                    "generated_text": "SQLite plus cache layer summary that should not leak downstream",
                    "debug_log_path": "/tmp/debug.log",
                }
            }
        }
    }
    agent_spec = {"_raw_data": {"description": "Plan tasks from FEAT and TECH only."}}

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "## Upstream Step Outputs" not in prompt
    assert "SQLite plus cache layer" not in prompt


def test_collect_step_inputs_accepts_freeze_ref_alias(builder):
    step = SimpleNamespace(
        id="feat_boundary_design",
        inputs=[{"source": "epic_freeze", "required": True}],
        depends_on=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "epic_freeze_ref": {
                    "artifact_id": "EPIC-001",
                    "path": "spec/requirements/epics/EPIC-001__demo.md",
                }
            }
        }
    }

    resolved = builder._collect_step_inputs(step, workflow_context)

    assert resolved["epic_freeze"]["artifact_id"] == "EPIC-001"


def test_collect_step_inputs_sanitizes_gate_frozen_inputs(builder):
    step = SimpleNamespace(
        id="delivery_plan_validation",
        inputs=[{"source": "feat_freeze", "required": True}],
        depends_on=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "feat_freeze": {
                    "gate_approved": True,
                    "business_output": {
                        "epic_ref": "EPIC-030",
                    },
                    "frozen_inputs": {
                        "feat_specs": {
                            "ssot_materialized": {
                                "feat_001": {
                                    "path": "spec/requirements/features/FEAT-159__hexinceshiyinqing.md"
                                }
                            }
                        }
                    },
                }
            }
        }
    }

    resolved = builder._collect_step_inputs(step, workflow_context)

    assert resolved["feat_freeze"]["business_output"]["epic_ref"] == "EPIC-030"
    assert "frozen_inputs" not in resolved["feat_freeze"]


@pytest.mark.asyncio
async def test_build_user_prompt_hydrates_ref_path_content(tmp_path):
    epic_path = tmp_path / "spec" / "requirements" / "epics" / "EPIC-003__demo.md"
    epic_path.parent.mkdir(parents=True, exist_ok=True)
    epic_path.write_text("# Goal\n\nCLI workflow-first\n", encoding="utf-8")

    builder = AgentContextBuilder(agent_loader=None, project_root=str(tmp_path))
    step = SimpleNamespace(
        id="feat_boundary_design",
        agent_id="agent.product.requirement_decomposer",
        inputs=[{"source": "epic_freeze", "required": True}],
        depends_on=[],
        outputs=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "epic_freeze_ref": {
                    "artifact_id": "EPIC-003",
                    "path": "spec/requirements/epics/EPIC-003__demo.md",
                }
            }
        }
    }
    agent_spec = {
        "_raw_data": {
            "description": "Decompose EPIC into FEAT candidates.",
        }
    }

    prompt = await builder._build_user_prompt(
        agent_spec,
        context_files={},
        workflow_context=workflow_context,
        step=step,
    )

    assert "EPIC-003" in prompt
    assert "spec/requirements/epics/EPIC-003__demo.md" in prompt
    assert "CLI workflow-first" in prompt
    assert "authoritative truth source" in prompt


def test_collect_step_inputs_resolves_external_input_types(builder):
    step = SimpleNamespace(
        id="raw_input_intake",
        inputs=[
            {
                "source": "external",
                "type": ["raw_requirement", "business_opportunity"],
                "required": True,
            }
        ],
        depends_on=[],
    )
    workflow_context = {
        "data": {
            "params": {
                "raw_requirement": "Gate 三分类治理模型重构需求",
            }
        }
    }

    resolved = builder._collect_step_inputs(step, workflow_context)

    assert resolved["external"] == "Gate 三分类治理模型重构需求"


def test_get_step_input_definition_prefers_structured_inputs_over_runtime_input(builder):
    step = SimpleNamespace(
        id="raw_input_intake",
        input={
            "step_id": "raw_input_intake",
            "name": "原始输入接入",
            "description": "runtime metadata shell",
        },
        inputs=[
            {
                "source": "external",
                "type": ["business_opportunity"],
                "required": True,
            }
        ],
    )

    resolved = builder._get_step_input_definition(step)

    assert isinstance(resolved, list)
    assert resolved[0]["source"] == "external"


def test_collect_step_inputs_resolves_specs_from_declared_output_symbols(tmp_path):
    rendered_workflow = tmp_path / ".workflow" / "rendered" / "workflow-symbols.yaml"
    rendered_workflow.parent.mkdir(parents=True, exist_ok=True)
    rendered_workflow.write_text(
        """
stages:
  - id: flow
    steps:
      - id: ui_design
        outputs:
          - symbol: ui_specs
      - id: tech_design
        outputs:
          - symbol: tech_specs
      - id: task_planning
        depends_on: [ui_design, tech_design]
        inputs:
          - source: ui_specs
          - source: tech_specs
""".strip(),
        encoding="utf-8",
    )

    builder = AgentContextBuilder(agent_loader=None, project_root=str(tmp_path))
    step = SimpleNamespace(
        id="task_planning",
        inputs=[
            {"source": "ui_specs", "required": False},
            {"source": "tech_specs", "required": True},
        ],
        depends_on=["ui_design", "tech_design"],
    )
    workflow_context = {
        "template_id": str(rendered_workflow),
        "data": {
            "step_outputs": {
                "ui_design": {
                    "business_output": {
                        "applicable": False,
                        "skip_reason": "ui not needed",
                    }
                },
                "tech_design": {
                    "business_output": {
                        "metadata": {"tech_id": "TECH-SRC-009"},
                        "system_overview": {"description": "dev workflow architecture"},
                    }
                },
            }
        },
    }

    resolved = builder._collect_step_inputs(step, workflow_context)

    assert resolved["ui_specs"]["skip_reason"] == "ui not needed"
    assert resolved["tech_specs"]["metadata"]["tech_id"] == "TECH-SRC-009"


def test_collect_step_inputs_resolves_specs_from_structured_payload_symbols(tmp_path):
    rendered_workflow = tmp_path / ".workflow" / "rendered" / "workflow-symbols.yaml"
    rendered_workflow.parent.mkdir(parents=True, exist_ok=True)
    rendered_workflow.write_text(
        """
stages:
  - id: flow
    steps:
      - id: tech_design
        outputs:
          - symbol: tech_specs
      - id: task_planning
        depends_on: [tech_design]
        inputs:
          - source: tech_specs
""".strip(),
        encoding="utf-8",
    )

    builder = AgentContextBuilder(agent_loader=None, project_root=str(tmp_path))
    step = SimpleNamespace(
        id="task_planning",
        inputs=[{"source": "tech_specs", "required": True}],
        depends_on=["tech_design"],
    )
    workflow_context = {
        "template_id": str(rendered_workflow),
        "data": {
            "step_outputs": {
                "tech_design": {
                    "status": "success",
                    "generated_text": "noisy summary mentioning unrelated infra",
                    "structured_payload": {
                        "metadata": {"feat_id": "FEAT-143", "tech_id": "TECH-FEAT-143-001"},
                        "system_overview": {"description": "entry routing and validation"},
                    },
                }
            }
        },
    }

    resolved = builder._collect_step_inputs(step, workflow_context)

    assert resolved["tech_specs"]["metadata"]["feat_id"] == "FEAT-143"
    assert "generated_text" not in resolved["tech_specs"]


def test_agent_loader_scans_spec_global_by_agent_id(tmp_path):
    spec_root = tmp_path / "spec-global"
    agent_dir = spec_root / "departments" / "product" / "agents" / "product-goal-analyzer" / "v1"
    agent_dir.mkdir(parents=True, exist_ok=True)
    (agent_dir / "agent.yaml").write_text(
        """
kind: agent
version: 1.0
id: agent.analysis.product_goal
name: Product Goal Analyzer
""".strip(),
        encoding="utf-8",
    )

    loader = AgentLoader(str(tmp_path), spec_root=str(spec_root))
    spec = loader.load("agent.analysis.product_goal")

    assert spec.id == "agent.analysis.product_goal"
    assert spec.spec_path == str((agent_dir / "agent.yaml"))
