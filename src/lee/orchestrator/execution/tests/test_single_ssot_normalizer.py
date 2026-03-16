from __future__ import annotations

from types import SimpleNamespace

import pytest

from lee.orchestrator.execution.runners.llm_runner import LLMRunner
from lee.orchestrator.execution.runners.normalization import SingleSSOTNormalizer


def test_single_ssot_normalizer_builds_src_contract():
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "title": "CLI 治理问题",
        "source_refs": ["ADR-006#decision"],
    }

    _, payload = SingleSSOTNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-src",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["key"] == "src"
    assert output["ssot_type"] == "src"


def test_single_ssot_normalizer_rewrites_generic_existing_src_contract_title():
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR-017 Gate 治理目标与价值分析",
        }
    }

    _, payload = SingleSSOTNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-src-existing",
        business_output=business_output,
        structured_payload={
            "ssot_output_contract": {
                "outputs": [
                    {
                        "key": "src",
                        "identity_kind": "ssot",
                        "ssot_type": "src",
                        "title": "SRC",
                    }
                ]
            }
        },
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["title"] == "ADR-017 Gate 治理目标与价值分析"


def test_single_ssot_normalizer_rejects_semantic_drift_title():
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR 原始输入归一化与合同复用前置目标分析",
        }
    }

    with pytest.raises(ValueError, match="semantic drift"):
        SingleSSOTNormalizer.normalize(
            runner_cls=LLMRunner,
            step=step,
            workflow_id="wf-src-drift",
            business_output=business_output,
            structured_payload={},
        )


def test_single_ssot_normalizer_rejects_multiple_src_outputs():
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR-017 Gate 治理目标与价值分析",
        }
    }

    with pytest.raises(ValueError, match="exactly one src output"):
        SingleSSOTNormalizer.normalize(
            runner_cls=LLMRunner,
            step=step,
            workflow_id="wf-src-multi",
            business_output=business_output,
            structured_payload={
                "ssot_output_contract": {
                    "outputs": [
                        {"key": "src", "identity_kind": "ssot", "ssot_type": "src", "title": "SRC"},
                        {"key": "src", "identity_kind": "ssot", "ssot_type": "src", "title": "SRC copy"},
                    ]
                }
            },
        )


def test_single_ssot_normalizer_allows_contextual_normalization_wording():
    step = SimpleNamespace(id="source_normalization", agent_id="agent.analysis.product_goal", config={})
    business_output = {
        "contract_info": {
            "title": "ADR-017 Gate 治理目标与价值分析",
        },
        "requirement_overview": {
            "description": "该对象会在 source normalization 阶段作为下游输入，并沿用既有复用策略。",
        },
    }

    _, payload = SingleSSOTNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-src-context",
        business_output=business_output,
        structured_payload={},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["title"] == "ADR-017 Gate 治理目标与价值分析"


def test_single_ssot_normalizer_backfills_tech_parent_from_feat_freeze_ref():
    step = SimpleNamespace(id="tech_design", name="TECH 设计", agent_id="agent.dev.tech_architect")
    business_output = {"title": "tech_design", "metadata": {}}

    _, payload = SingleSSOTNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-tech",
        business_output=business_output,
        structured_payload={"ssot_output_contract": {"outputs": [{"key": "tech_spec", "title": "tech_design"}]}},
        instance_data={"params": {"feat_freeze_ref": {"artifact_id": "FEAT-081"}}},
    )

    output = payload["ssot_output_contract"]["outputs"][0]
    assert output["parent"] == "FEAT-081"
    assert output["implements"] == ["FEAT-081"]


def test_single_ssot_normalizer_keeps_epic_design_on_src_parent_without_ssot_contract():
    step = SimpleNamespace(id="epic_design", agent_id="agent.product.epic_designer", config={})
    business_output = {
        "epic_id": "EPIC-045",
        "title": "EPIC 入口统一经 SRC",
        "goal": "建立 SRC 入口约束",
        "source_refs": ["ADR-019"],
        "ssot": {
            "identity_kind": "ssot",
            "ssot_type": "EPIC",
            "parent": "ADR-019",
            "derived_from": "ADR-019",
        },
    }

    normalized_business, payload = SingleSSOTNormalizer.normalize(
        runner_cls=LLMRunner,
        step=step,
        workflow_id="wf-epic",
        business_output=business_output,
        structured_payload={},
        instance_data={"params": {"source_freeze_ref": {"artifact_id": "SRC-045"}}},
    )

    assert normalized_business["ssot"]["parent"] == "SRC-045"
    assert normalized_business["ssot"]["derived_from"] == "SRC-045"
    assert normalized_business["source_refs"] == ["SRC-045#scope"]
    assert "ssot_output_contract" not in payload
