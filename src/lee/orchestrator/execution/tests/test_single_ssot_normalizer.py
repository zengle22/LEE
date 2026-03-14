from __future__ import annotations

from types import SimpleNamespace

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
