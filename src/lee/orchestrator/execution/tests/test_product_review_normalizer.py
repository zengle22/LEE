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
