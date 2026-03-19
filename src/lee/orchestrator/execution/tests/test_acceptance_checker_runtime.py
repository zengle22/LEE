from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.runners.llm_runner import LLMRunner


def _build_instance_data(*, include_refs: bool = True):
    src_output = {
        "key": "src",
        "identity_kind": "ssot",
        "ssot_type": "src",
        "title": "CLI ADR Update 入口补齐 - 治理链连续性恢复",
        "content": "# CLI ADR Update 入口补齐 - 治理链连续性恢复\n\n## 问题陈述\n\n补齐治理链 CLI 入口。",
        "bridge_context": {
            "governed_by_adrs": ["ADR-024"] if include_refs else [],
        },
    }
    if include_refs:
        src_output["source_refs"] = ["ADR-024"]

    business_output = {
        "contract_info": {"status": "DRAFT"},
        "key_designs": {
            "risks_and_boundaries": {
                "confirmation": {
                    "status": "pending",
                    "questions": [
                        {"question": "Q1", "answered": False},
                        {"question": "Q2", "answered": False},
                    ],
                }
            }
        },
    }
    return {
        "step_outputs": {
            "normalized_src": {
                "business_output": business_output,
                "structured_payload": {
                    "business_output": business_output,
                    "ssot_output_contract": {
                        "contract_version": "1.0",
                        "run_id": "wf-task-001",
                        "outputs": [src_output],
                    },
                },
            }
        }
    }


def test_acceptance_checker_prefers_deterministic_src_validation_for_false_negative():
    step = SimpleNamespace(id="src_acceptance_auto_check", agent_id="agent.governance.acceptance_checker")
    business_output = {
        "status": "fail",
        "check_type": "auto",
        "dimensions": {
            "schema_validation": "fail",
            "contract_validation": "pass",
            "completeness_check": "fail",
            "dependency_resolution": "pass",
        },
        "errors": [
            "File missing 'business_output' wrapper key - product-goal-contract is at root level instead",
            "File missing 'structured_payload' key - expected by input specification",
            "File missing 'ssot_output_contract' - no SRC output generated",
            "No SRC file found in workspace - expected at .workflow/workspace/wf_task_22520181/",
        ],
        "warnings": [],
    }

    fixed, _ = LLMRunner._prevalidate_fix_acceptance_checker_payload(
        step=step,
        business_output=business_output,
        structured_payload={},
        instance_data=_build_instance_data(),
    )

    assert fixed["status"] == "pass"
    assert fixed["dimensions"] == {
        "schema_validation": "pass",
        "contract_validation": "pass",
        "completeness_check": "pass",
        "dependency_resolution": "pass",
    }
    assert "Contract status is 'DRAFT' - not yet confirmed" in fixed["warnings"]
    assert "Confirmation status is 'pending' with 2 unanswered questions" in fixed["warnings"]


def test_acceptance_checker_keeps_failure_when_dependencies_are_missing():
    result = LLMRunner._derive_acceptance_checker_result_from_inputs(
        _build_instance_data(include_refs=False)
    )

    assert result is not None
    assert result["status"] == "fail"
    assert result["dimensions"]["dependency_resolution"] == "fail"
    assert result["errors"] == [
        "normalized_src 的 src 输出缺少可解析的 source_refs 或 governed_by_adrs。"
    ]
