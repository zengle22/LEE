from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner
from lee.orchestrator.execution.runners.normalization import ProductReviewNormalizer


def test_product_review_normalizer_maps_status_to_decision():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-001",
        "review_type": "feat_review",
        "status": "pass",
        "subject_refs": ["FEAT-001"],
        "summary": "ok",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_structured["business_output"]["decision"] == "pass"


def test_product_review_normalizer_fills_missing_feat_subject_refs_from_instance_data():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-002",
        "review_type": "feat_review",
        "decision": "pass",
        "subject_refs": [],
        "summary": "ok",
        "findings": [],
        "risks": [],
        "recommendations": [],
    }

    normalized_business, _ = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "ssot_materialized": {
                        "feat": {"id": "FEAT-001"},
                    },
                }
            }
        },
    )

    assert normalized_business["subject_refs"] == ["FEAT-001"]


def test_product_review_normalizer_sanitizes_soft_feat_review_revise_when_bundle_is_structured():
    step = SimpleNamespace(agent_id="agent.product.feat_reviewer")
    business_output = {
        "review_id": "RVW-003",
        "review_type": "feat_review",
        "decision": "revise",
        "subject_refs": ["FEAT-001"],
        "summary": "still too abstract",
        "findings": [
            "FEAT-SRC-041-016-004 引用了 list、show、decide 三条 CLI 链路，但未冻结每条链路的输出字段契约、字段来源优先级、缺失时阻断规则以及 repo_context 在摘要判断中的作用，尚不足以直接派生 UI/TASK/TESTSET。",
            "全部 FEAT 的 acceptance_checks 均包含 id、scenario、given、when、then、trace_hints，但 trace_hints 仅停留在 UI/TECH/TASK/TESTSET 标签级别，缺少可直接派生下游对象的具体追踪锚点，未满足“可支撑下游派生”的要求。",
        ],
        "risks": ["CLI、runtime、审计在缺少统一字段级契约时会产生不同输出结构，后续回补 SSOT 与测试集的成本会显著上升。"],
        "recommendations": [],
    }

    normalized_business, normalized_structured = ProductReviewNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        business_output=business_output,
        structured_payload={"business_output": dict(business_output)},
        instance_data={
            "step_outputs": {
                "feat_spec_generation": {
                    "business_output": {
                        "epic_ref": "EPIC-001",
                        "feat_specs": [
                            {
                                "feat_id": "FEAT-001",
                                "title": "Gate Result Contract",
                                "goal": "Freeze gate result semantics",
                                "user_value": "Downstream workflows can rely on stable gate outputs",
                                "inputs": ["gate definition", "review evidence"],
                                "processing": ["normalize decision", "validate subject refs"],
                                "outputs": ["gate_result", "workflow transition"],
                                "acceptance_criteria": ["gate_result schema is stable"],
                                "input_contract": {
                                    "required_artifacts": ["gate.yaml"],
                                    "required_fields": ["purpose", "decision_mode"],
                                    "consumption_rules": ["human review consumes human_gate_context"],
                                },
                                "acceptance_checks": [
                                    {
                                        "id": "AC-001",
                                        "scenario": "approval handoff",
                                        "given": "a running workflow pauses at gate",
                                        "when": "human approves the gate",
                                        "then": "workflow resumes with deterministic transition",
                                        "trace_hints": ["gate_result.decision", "workflow.status"],
                                    }
                                ],
                                "ssot": {
                                    "parent": "EPIC-001",
                                    "derived_from": "EPIC-001#breakdown",
                                },
                            }
                        ],
                    }
                }
            }
        },
    )

    assert normalized_business["decision"] == "pass"
    assert normalized_business["findings"] == []
    assert normalized_business["risks"] == []
    assert normalized_business["summary"].startswith(
        "All reviewed FEATs satisfy the minimum structural requirements"
    )
    assert normalized_structured["business_output"]["decision"] == "pass"
