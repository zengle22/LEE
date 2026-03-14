from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner
from lee.orchestrator.execution.runners.normalization import PrdWriterFeatNormalizer


def test_prd_writer_feat_normalizer_synthesizes_outputs_via_runner_helpers():
    step = SimpleNamespace(id="feat_spec_generation", agent_id="agent.product.prd_writer")
    business_output = {
        "epic_ref": "EPIC-001",
        "feat_specs": [
            {
                "feat_id": "FEAT-001",
                "title": "CLI 治理入口",
                "goal": "规范 CLI 主入口",
                "user_value": "用户不再绕过治理链",
                "inputs": ["源需求"],
                "processing": ["校验", "路由"],
                "outputs": ["正式 FEAT 文档"],
                "acceptance_criteria": ["只能通过 workflow 创建"],
                "acceptance_checks": [
                    {
                        "id": "AC-001",
                        "scenario": "workflow 创建",
                        "given": "输入合法",
                        "when": "运行 workflow",
                        "then": "生成正式 FEAT",
                        "trace_hints": ["TASK", "TESTSET"],
                    }
                ],
                "dependencies": [],
                "non_goals": ["不修改旧 registry"],
                "source_refs": ["EPIC-001#scope"],
                "ssot": {
                    "identity_kind": "ssot",
                    "ssot_type": "FEAT",
                    "parent": "EPIC-001",
                },
            }
        ],
    }

    normalized_business, normalized_structured = PrdWriterFeatNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-test",
        business_output=business_output,
        structured_payload={"business_output": business_output, "ssot_output_contract": {}},
    )

    assert normalized_business["epic_ref"] == "EPIC-001"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["parent"] == "EPIC-001"
    assert normalized_structured["ssot_output_contract"]["outputs"][0]["properties"]["feat_id"] == "FEAT-001"
