from pathlib import Path

import yaml

from lee.policy.granularity_evaluator import GranularityPolicyEvaluator
from lee.state.bugfix_state_machine import BugfixStateMachine


def _load_bugfix_template():
    template_path = Path("spec-global/departments/dev/workflows/templates/bugfix-delivery-l2-template.yaml")
    with open(template_path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def test_bugfix_delivery_l2_template_structure():
    data = _load_bugfix_template()

    assert data["id"] == "template.dev.bugfix_delivery_l2"
    assert [phase["id"] for phase in data["phases"]] == [
        "triage",
        "root_cause",
        "fix_design",
        "fix_implementation",
        "verification",
        "evidence_pack",
        "merge_or_reject",
    ]


def test_bugfix_delivery_l2_input_contract():
    data = _load_bugfix_template()
    assert data["shared_input_contract"]["required_fields"] == [
        "bug_ssot_id",
        "severity",
        "reproduction_evidence",
    ]
    assert "batch_approval_record" in data["shared_input_contract"]["optional_fields"]


def test_bugfix_delivery_l2_granularity_policy():
    evaluator = GranularityPolicyEvaluator()

    single = evaluator.evaluate(bug_ids=["BUG-1"], batch_mode=False)
    assert single.allowed is True

    batch = evaluator.evaluate(
        bug_ids=["BUG-1", "BUG-2"],
        batch_mode=True,
        batch_context={
            "same_module": True,
            "same_root_cause_class": True,
            "same_fix_strategy": True,
            "same_verification_surface": True,
            "same_release_window": True,
        },
    )
    assert batch.allowed is True

    exception_batch = evaluator.evaluate(
        bug_ids=["BUG-1", "BUG-2"],
        batch_mode=True,
        batch_context={
            "same_module": True,
            "same_root_cause_class": False,
            "same_fix_strategy": True,
            "same_verification_surface": True,
            "same_release_window": True,
        },
        batch_approval_record={"decision": "approved", "request_id": "BAR-001"},
    )
    assert exception_batch.allowed is True
    assert exception_batch.approval_record_used is True


def test_bugfix_delivery_l2_state_machine_flow():
    machine = BugfixStateMachine()
    state = machine.INITIAL_STATE
    for event in (
        "triage_completed",
        "root_cause_started",
        "fix_design_started",
        "fix_impl_started",
        "verification_started",
        "evidence_pack_started",
        "merge_decision_started",
        "merge_completed",
    ):
        state = machine.next_state(state, event)

    assert state == "COMPLETED"


def test_bugfix_delivery_l2_contract_interfaces():
    data = _load_bugfix_template()
    handoffs = data["phase_data_flow"]["handoffs"]

    first = handoffs[0]
    second = handoffs[1]
    last = handoffs[-1]
    assert first["from"] == "triage"
    assert first["to"] == "root_cause"
    assert "granularity_decision_ref" in first["outputs"]
    assert "batch_approval_record" in second["outputs"]
    assert last["from"] == "evidence_pack"
    assert last["to"] == "merge_or_reject"
