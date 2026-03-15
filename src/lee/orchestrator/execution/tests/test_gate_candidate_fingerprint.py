from __future__ import annotations

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
