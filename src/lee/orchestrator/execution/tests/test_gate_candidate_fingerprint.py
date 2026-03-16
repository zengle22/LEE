from __future__ import annotations

from types import SimpleNamespace

from lee.orchestrator.execution.gate_operations import GateOperationsMixin


class _GateHarness(GateOperationsMixin):
    pass


def test_collect_publishable_ssot_candidates_dedupes_nested_epic_payloads():
    harness = _GateHarness()
    candidate = {
        "title": "ADR 到业务主链桥接规则",
        "goal": "建立 EPIC 入口统一经 SRC 的规则",
        "scope": ["桥接 SRC", "EPIC 校验"],
        "non_goals": ["历史回补"],
        "success_metrics": ["100% EPIC 经过 SRC"],
        "source_refs": ["SRC-048"],
        "ssot": {
            "identity_kind": "ssot",
            "ssot_type": "EPIC",
            "parent": "SRC-048",
            "derived_from": "SRC-048",
        },
    }

    payload = {
        "business_output": candidate,
        "structured_payload": {
            "business_output": candidate,
            "structured_payload": {"business_output": candidate},
        },
        "frozen_inputs": {
            "epic_candidate": {
                "business_output": candidate,
            }
        },
    }

    collected = harness._collect_publishable_ssot_candidates(payload)

    assert len(collected) == 1
    assert collected[0]["title"] == "ADR 到业务主链桥接规则"


def test_collect_gate_freeze_payloads_prefers_gate_aliases_before_full_fallback():
    harness = _GateHarness()
    harness.state_machine = SimpleNamespace(
        _resolve_step_inputs_for_freeze=lambda gate_step_id, instance: []
    )

    epic_payload = {
        "business_output": {
            "title": "ADR 到业务主链桥接规则",
            "goal": "建立 EPIC 入口统一经 SRC 的规则",
            "source_refs": ["SRC-051"],
            "ssot": {
                "identity_kind": "ssot",
                "ssot_type": "EPIC",
                "parent": "SRC-051",
                "derived_from": "SRC-051",
            },
        }
    }
    review_payload = {
        "business_output": {
            "review_id": "RVW-001",
            "review_type": "epic_review",
            "subject_refs": ["EPIC-051"],
        }
    }
    instance = SimpleNamespace(
        data={
            "step_outputs": {
                "epic_design": epic_payload,
                "epic_candidate": epic_payload,
                "epic_identity_prepare": epic_payload,
                "epic_scoped_candidate": epic_payload,
                "epic_review": review_payload,
                "epic_review_report": review_payload,
                "epic_identity_formalize": epic_payload,
                "epic_formalized_candidate": epic_payload,
            },
            "params": {},
        }
    )

    payloads = harness._collect_gate_freeze_payloads(instance, "epic_freeze")

    assert payloads == [epic_payload, review_payload]


def test_collect_publishable_ssot_candidates_recognizes_ssot_output_contract_entries():
    harness = _GateHarness()
    payload = {
        "structured_payload": {
            "ssot_output_contract": {
                "contract_version": "1.0",
                "run_id": "wf-task-001",
                "outputs": [
                    {
                        "key": "src",
                        "identity_kind": "ssot",
                        "ssot_type": "src",
                        "title": "ADR 桥接薄 SRC 规则",
                        "content": "# ADR 桥接薄 SRC 规则\n",
                        "source_refs": ["ADR-019", "ADR-003"],
                        "source_kind": "governance_bridge_src",
                    }
                ],
            }
        }
    }

    collected = harness._collect_publishable_ssot_candidates(payload)

    assert len(collected) == 1
    assert collected[0]["title"] == "ADR 桥接薄 SRC 规则"
    assert collected[0]["ssot_type"] == "src"
